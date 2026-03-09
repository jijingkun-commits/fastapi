"""RunControlService 单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models.chat_run import ChatRun, ChatRunStatus
from app.services.run_control_service import (
    RunControlService,
    RunPermissionDeniedError,
)


def _build_service() -> RunControlService:
    """构造启用 run_control 的隔离实例。"""

    return RunControlService(
        enable_override=True,
        stopped_event_override=True,
        orphan_timeout_seconds=3,
    )


def test_create_run_and_get_active_run() -> None:
    """创建 run 后应可通过 active_run 取回。"""

    svc = _build_service()

    created = svc.create_run(thread_id="thread-loan", user_id=101)
    active = svc.get_active_run(thread_id="thread-loan", user_id=101)

    assert created.run_id.startswith("run_")
    assert created.status == ChatRunStatus.RUNNING.value
    assert active is not None
    assert active.run_id == created.run_id


def test_cancel_run_idempotent_semantics() -> None:
    """取消接口应支持幂等语义。"""

    svc = _build_service()
    created = svc.create_run(thread_id="thread-deposit", user_id=202)

    first = svc.cancel_run(
        run_id=created.run_id,
        requester_user_id=202,
        reason="user_cancelled",
    )
    second = svc.cancel_run(
        run_id=created.run_id,
        requester_user_id=202,
        reason="user_cancelled",
    )

    assert first.accepted is True
    assert first.idempotent is False
    assert first.status == ChatRunStatus.STOPPING.value

    assert second.accepted is True
    assert second.idempotent is True
    assert second.status == ChatRunStatus.STOPPING.value


def test_cancel_run_permission_denied_for_other_user() -> None:
    """非管理员且非归属用户取消应被拒绝。"""

    svc = _build_service()
    created = svc.create_run(thread_id="thread-branch", user_id=301)

    with pytest.raises(RunPermissionDeniedError):
        svc.cancel_run(
            run_id=created.run_id,
            requester_user_id=999,
            is_admin=False,
        )


def test_mark_stopped_blocks_resume() -> None:
    """run 进入 stopped 后必须阻断 resume。"""

    svc = _build_service()
    created = svc.create_run(thread_id="thread-retail", user_id=401)

    svc.cancel_run(run_id=created.run_id, requester_user_id=401, reason="user_cancelled")
    stopped = svc.mark_stopped(run_id=created.run_id, reason="user_cancelled")

    assert stopped is not None
    assert stopped.status == ChatRunStatus.STOPPED.value
    assert svc.can_resume_run(created.run_id) is False


def test_recover_active_runs_cleanup_orphan() -> None:
    """超时 active_run 应在恢复阶段清理为 orphan/stopped。"""

    svc = _build_service()
    created = svc.create_run(thread_id="thread-corp", user_id=501)

    snapshot = svc.get_run(created.run_id)
    assert snapshot is not None
    # 强制回拨更新时间，模拟孤儿 run
    snapshot.updated_at = datetime.now() - timedelta(seconds=30)
    svc._sync_memory(snapshot)  # noqa: SLF001 - 测试场景需要直接注入状态

    cleaned = svc.recover_active_runs(now=datetime.now())

    assert len(cleaned) == 1
    assert cleaned[0].run_id == created.run_id
    assert cleaned[0].status == ChatRunStatus.STOPPED.value
    assert cleaned[0].cancel_reason in {"orphan_cleanup", "cancel_timeout"}


def test_run_control_active_query_gate_rejects_same_thread_conflict(db_session) -> None:
    """同一 thread 存在 active run 时必须返回结构化冲突。"""

    svc = _build_service()
    first = svc.create_run(thread_id="thread-same", user_id=601, db=db_session)

    with pytest.raises(Exception) as exc_info:
        svc.create_run(thread_id="thread-same", user_id=601, db=db_session)

    assert exc_info.value.active_run_id == first.run_id
    assert exc_info.value.thread_id == "thread-same"


def test_run_control_active_query_gate_rejects_parallel_limit(db_session) -> None:
    """单用户 active run 超过 3 时必须拒绝新建。"""

    svc = _build_service()
    for index in range(3):
        svc.create_run(thread_id=f"thread-limit-{index}", user_id=701, db=db_session)

    with pytest.raises(Exception) as exc_info:
        svc.create_run(thread_id="thread-limit-overflow", user_id=701, db=db_session)

    assert exc_info.value.active_count == 3
    assert exc_info.value.limit == 3


def test_last_activity_persistence_and_sort_prefers_last_activity_at(db_session) -> None:
    """active 列表必须优先按 last_activity_at 排序。"""

    svc = _build_service()
    first = svc.create_run(thread_id="thread-a", user_id=801, run_id="run-a", db=db_session)
    second = svc.create_run(thread_id="thread-b", user_id=801, run_id="run-b", db=db_session)
    third = svc.create_run(thread_id="thread-c", user_id=801, run_id="run-c", db=db_session)

    rows = {row.run_id: row for row in db_session.query(ChatRun).filter(ChatRun.user_id == 801).all()}
    rows[first.run_id].updated_at = datetime(2026, 3, 8, 10, 0, 0)
    rows[first.run_id].last_activity_at = datetime(2026, 3, 8, 10, 5, 0)
    rows[second.run_id].updated_at = datetime(2026, 3, 8, 10, 10, 0)
    rows[second.run_id].last_activity_at = None
    rows[third.run_id].updated_at = datetime(2026, 3, 8, 10, 2, 0)
    rows[third.run_id].last_activity_at = datetime(2026, 3, 8, 10, 6, 0)
    db_session.commit()

    active_runs = svc.list_active_runs_by_user(user_id=801, db=db_session)

    assert [run.run_id for run in active_runs] == ["run-c", "run-a", "run-b"]
    assert active_runs[2].last_activity_at is None


def test_last_activity_persistence_and_sort_filters_terminal_runs(db_session) -> None:
    """active 查询只允许返回 running/stopping。"""

    svc = _build_service()
    running = svc.create_run(thread_id="thread-running", user_id=901, run_id="run-running", db=db_session)
    stopped = svc.create_run(thread_id="thread-stopped", user_id=901, run_id="run-stopped", db=db_session)
    svc.mark_stopped(run_id=stopped.run_id, reason="user_cancelled", db=db_session)

    active_runs = svc.list_active_runs_by_user(user_id=901, db=db_session)

    assert [run.run_id for run in active_runs] == [running.run_id]
    assert all(run.status in {ChatRunStatus.RUNNING.value, ChatRunStatus.STOPPING.value} for run in active_runs)
