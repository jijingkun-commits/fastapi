"""用户记忆意图 Worker 服务测试。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import app.services.memory_intent_worker_service as worker_service
from app.models.user_memory_intent_job import (
    MEMORY_INTENT_STATUS_DEAD_LETTER,
    MEMORY_INTENT_STATUS_FAILED,
    MEMORY_INTENT_STATUS_PENDING,
    MEMORY_INTENT_STATUS_PROCESSING,
    MEMORY_INTENT_STATUS_SUCCEEDED,
)
from app.repositories import user_memory_intent_job_repo


@dataclass
class _Job:
    id: int
    status: str = MEMORY_INTENT_STATUS_PENDING
    attempt_count: int = 0
    next_retry_time: datetime | None = None
    lease_until: datetime | None = None
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    error_message: str | None = None
    update_time: datetime | None = None


class _ClaimQuery:
    def __init__(self, job: _Job | None):
        self.job = job
        self.lock_kwargs: dict[str, object] = {}

    def filter(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def order_by(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def with_for_update(self, **kwargs):  # noqa: ANN003
        self.lock_kwargs = dict(kwargs)
        return self

    def first(self):
        return self.job


class _Session:
    def __init__(self, query_obj):
        self.query_obj = query_obj
        self.commit_called = 0
        self.rollback_called = 0

    def query(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self.query_obj

    def commit(self):
        self.commit_called += 1

    def rollback(self):
        self.rollback_called += 1


class _NoJobRepo:
    @staticmethod
    def promote_retryable_failed(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    @staticmethod
    def claim_pending(*args, **kwargs):  # noqa: ANN002, ANN003
        return None


def test_claim_pending_should_use_skip_locked_and_mark_processing() -> None:
    """抢占任务应使用 SKIP LOCKED 并写入 processing 租约信息。"""

    now = datetime(2026, 3, 4, 10, 0, 0)
    job = _Job(id=101, status=MEMORY_INTENT_STATUS_PENDING, next_retry_time=now - timedelta(seconds=1))
    query = _ClaimQuery(job)
    db = _Session(query)

    claimed = user_memory_intent_job_repo.claim_pending(
        db,
        worker_id="worker-1",
        lease_seconds=90,
        now=now,
    )

    assert claimed is job
    assert query.lock_kwargs.get("skip_locked") is True
    assert job.status == MEMORY_INTENT_STATUS_PROCESSING
    assert job.claimed_by == "worker-1"
    assert job.claimed_at == now
    assert job.lease_until == now + timedelta(seconds=90)


def test_mark_failed_should_apply_backoff_and_keep_failed_status() -> None:
    """失败未耗尽时应退避并维持 failed，等待下次回捞。"""

    now = datetime(2026, 3, 4, 10, 5, 0)
    job = _Job(
        id=201,
        status=MEMORY_INTENT_STATUS_PROCESSING,
        attempt_count=1,
        claimed_by="worker-1",
    )
    db = _Session(_ClaimQuery(job))

    updated = user_memory_intent_job_repo.mark_failed(
        db,
        job_id=201,
        worker_id="worker-1",
        error_message="llm timeout",
        max_attempts=4,
        base_retry_seconds=30,
        now=now,
    )

    assert updated is job
    assert job.attempt_count == 2
    assert job.status == MEMORY_INTENT_STATUS_FAILED
    assert job.next_retry_time == now + timedelta(seconds=60)
    assert job.claimed_by is None
    assert job.lease_until is None


def test_mark_failed_should_move_to_dead_letter_when_retry_exhausted() -> None:
    """失败达到上限后应进入 dead_letter。"""

    now = datetime(2026, 3, 4, 10, 8, 0)
    job = _Job(
        id=301,
        status=MEMORY_INTENT_STATUS_PROCESSING,
        attempt_count=2,
        claimed_by="worker-2",
    )
    db = _Session(_ClaimQuery(job))

    updated = user_memory_intent_job_repo.mark_failed(
        db,
        job_id=301,
        worker_id="worker-2",
        error_message="parser error",
        max_attempts=3,
        base_retry_seconds=30,
        now=now,
    )

    assert updated is job
    assert job.attempt_count == 3
    assert job.status == MEMORY_INTENT_STATUS_DEAD_LETTER
    assert job.next_retry_time == now


def test_run_once_should_return_idle_when_no_job(monkeypatch) -> None:  # noqa: ANN001
    """队列为空时 run_once 应返回 idle。"""

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _NoJobRepo)
    db = _Session(_ClaimQuery(None))

    result = worker_service.run_once(
        db,
        worker_id="worker-idle",
        process_job=lambda job: None,
    )

    assert result["status"] == "idle"
    assert result["job_id"] is None
    assert db.commit_called == 0


def test_run_once_should_reuse_observability_snapshot_within_sample_window(monkeypatch) -> None:  # noqa: ANN001
    """同一 worker 的短窗口空轮询应复用观测快照，避免重复统计整表。"""

    now = datetime(2026, 3, 12, 10, 0, 0)
    observed = {"calls": 0}

    def _fake_collect(db):  # noqa: ANN001
        observed["calls"] += 1
        return {
            "queue_len": observed["calls"],
            "dead_letter_rate": 0.0,
            "latency_p95_ms": None,
        }

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _NoJobRepo)
    monkeypatch.setattr(worker_service, "collect_memory_intent_observability", _fake_collect)
    worker_service._OBSERVABILITY_CACHE_BY_WORKER.clear()
    db = _Session(_ClaimQuery(None))

    first = worker_service.run_once(
        db,
        worker_id="worker-cache",
        process_job=lambda job: None,
        now=now,
    )
    second = worker_service.run_once(
        db,
        worker_id="worker-cache",
        process_job=lambda job: None,
        now=now + timedelta(seconds=5),
    )

    assert observed["calls"] == 1
    assert first["backpressure"]["queue_len"] == 1
    assert second["backpressure"]["queue_len"] == 1


def test_run_once_should_refresh_observability_snapshot_after_sample_window(monkeypatch) -> None:  # noqa: ANN001
    """超出采样窗口后，应重新采集一次背压观测。"""

    now = datetime(2026, 3, 12, 10, 10, 0)
    observed = {"calls": 0}

    def _fake_collect(db):  # noqa: ANN001
        observed["calls"] += 1
        return {
            "queue_len": observed["calls"],
            "dead_letter_rate": 0.0,
            "latency_p95_ms": None,
        }

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _NoJobRepo)
    monkeypatch.setattr(worker_service, "collect_memory_intent_observability", _fake_collect)
    worker_service._OBSERVABILITY_CACHE_BY_WORKER.clear()
    db = _Session(_ClaimQuery(None))

    worker_service.run_once(
        db,
        worker_id="worker-cache",
        process_job=lambda job: None,
        now=now,
    )
    refreshed = worker_service.run_once(
        db,
        worker_id="worker-cache",
        process_job=lambda job: None,
        now=now + timedelta(seconds=35),
    )

    assert observed["calls"] == 2
    assert refreshed["backpressure"]["queue_len"] == 2


def test_run_once_should_mark_succeeded_when_handler_ok(monkeypatch) -> None:  # noqa: ANN001
    """任务处理成功后应流转到 succeeded 并提交事务。"""

    now = datetime(2026, 3, 4, 11, 0, 0)
    job = _Job(id=401, status=MEMORY_INTENT_STATUS_PROCESSING)
    captured = {"processed": []}

    class _Repo:
        @staticmethod
        def promote_retryable_failed(*args, **kwargs):  # noqa: ANN002, ANN003
            return 1

        @staticmethod
        def claim_pending(*args, **kwargs):  # noqa: ANN002, ANN003
            return job

        @staticmethod
        def mark_succeeded(*args, **kwargs):  # noqa: ANN002, ANN003
            job.status = MEMORY_INTENT_STATUS_SUCCEEDED
            return job

        @staticmethod
        def mark_failed(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("成功路径不应触发 mark_failed")

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _Repo)
    db = _Session(_ClaimQuery(job))

    result = worker_service.run_once(
        db,
        worker_id="worker-ok",
        process_job=lambda current: captured["processed"].append(current.id),
        now=now,
    )

    assert captured["processed"] == [401]
    assert result["status"] == MEMORY_INTENT_STATUS_SUCCEEDED
    assert result["job_id"] == 401
    assert result["recovered_count"] == 1
    assert db.commit_called == 1


def test_run_once_should_mark_failed_when_handler_raises(monkeypatch) -> None:  # noqa: ANN001
    """任务处理失败后应走失败状态机并提交失败结果。"""

    now = datetime(2026, 3, 4, 11, 10, 0)
    job = _Job(id=501, status=MEMORY_INTENT_STATUS_PROCESSING)
    captured: dict[str, object] = {}

    class _Repo:
        @staticmethod
        def promote_retryable_failed(*args, **kwargs):  # noqa: ANN002, ANN003
            return 0

        @staticmethod
        def claim_pending(*args, **kwargs):  # noqa: ANN002, ANN003
            return job

        @staticmethod
        def mark_succeeded(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("失败路径不应触发 mark_succeeded")

        @staticmethod
        def mark_failed(*args, **kwargs):  # noqa: ANN002, ANN003
            captured.update(kwargs)
            job.status = MEMORY_INTENT_STATUS_FAILED
            return job

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _Repo)
    db = _Session(_ClaimQuery(job))

    def _raise_error(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("llm unavailable")

    result = worker_service.run_once(
        db,
        worker_id="worker-fail",
        process_job=_raise_error,
        max_attempts=5,
        retry_base_seconds=15,
        now=now,
    )

    assert result["status"] == MEMORY_INTENT_STATUS_FAILED
    assert result["job_id"] == 501
    assert "llm unavailable" in str(captured.get("error_message"))
    assert captured.get("max_attempts") == 5
    assert captured.get("base_retry_seconds") == 15
    assert db.commit_called == 1
