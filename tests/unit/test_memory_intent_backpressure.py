"""用户记忆异步任务背压与门禁测试。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import app.services.memory_intent_worker_service as worker_service
from app.core.config_contract import MEMORY_INTENT_BACKPRESSURE_THRESHOLDS


@dataclass
class _Job:
    id: int
    status: str = "processing"


class _Session:
    def __init__(self) -> None:
        self.commit_called = 0
        self.rollback_called = 0

    def commit(self) -> None:
        self.commit_called += 1

    def rollback(self) -> None:
        self.rollback_called += 1


def test_backpressure_threshold_contract_should_match_design_baseline() -> None:
    """阈值契约应与设计文档约定一致。"""

    assert MEMORY_INTENT_BACKPRESSURE_THRESHOLDS["l2_queue_len"] == 5000
    assert MEMORY_INTENT_BACKPRESSURE_THRESHOLDS["l3_queue_len"] == 10000
    assert MEMORY_INTENT_BACKPRESSURE_THRESHOLDS["dead_letter_rate"] == 0.005
    assert MEMORY_INTENT_BACKPRESSURE_THRESHOLDS["p95_latency_ms"] == 5000.0


def test_evaluate_backpressure_level_should_keep_l1_when_queue_is_low() -> None:
    """L1：队列未达阈值时保持正常处理。"""

    result = worker_service.evaluate_backpressure_level(
        queue_len=320,
        dead_letter_rate=0.001,
        latency_p95_ms=1500.0,
    )

    assert result["level"] == "L1"
    assert result["throttle_enabled"] is False
    assert result["circuit_open"] is False
    assert result["gate_passed"] is True
    assert result["alerts"] == []


def test_evaluate_backpressure_level_should_switch_to_l2_when_queue_reaches_threshold() -> None:
    """L2：队列达到第一档阈值应触发限流与门禁告警。"""

    result = worker_service.evaluate_backpressure_level(queue_len=5000)

    assert result["level"] == "L2"
    assert result["throttle_enabled"] is True
    assert result["circuit_open"] is False
    assert result["gate_passed"] is False
    assert result["alerts"][0]["code"] == "memory.intent.queue.l2"
    assert result["alerts"][0]["severity"] == "warning"


def test_evaluate_backpressure_level_should_open_circuit_on_l3() -> None:
    """L3：队列进入熔断阈值应停止消费。"""

    result = worker_service.evaluate_backpressure_level(queue_len=10000)

    assert result["level"] == "L3"
    assert result["throttle_enabled"] is True
    assert result["circuit_open"] is True
    assert result["gate_passed"] is False
    assert result["alerts"][0]["code"] == "memory.intent.queue.l3"
    assert result["alerts"][0]["severity"] == "critical"


def test_evaluate_backpressure_level_should_support_disabled_rollback_mode() -> None:
    """回滚：disabled 模式应跳过背压动作。"""

    result = worker_service.evaluate_backpressure_level(
        queue_len=20000,
        dead_letter_rate=0.02,
        latency_p95_ms=9000.0,
        backpressure_mode="disabled",
    )

    assert result["mode"] == "disabled"
    assert result["level"] == "L1"
    assert result["throttle_enabled"] is False
    assert result["circuit_open"] is False
    assert result["alerts"] == []
    assert result["gate_passed"] is True


def test_emit_memory_intent_metrics_should_report_alerts_and_gate_status() -> None:
    """观测输出应携带队列与时延门禁结论。"""

    payload = worker_service.emit_memory_intent_metrics(
        queue_len=4200,
        dead_letter_rate=0.009,
        latency_p95_ms=6500.0,
    )

    assert payload["backpressure_level"] == "L1"
    assert payload["queue_len"] == 4200
    assert payload["dead_letter_rate"] == 0.009
    assert payload["latency_p95_ms"] == 6500.0
    assert payload["gate_passed"] is False
    assert {item["code"] for item in payload["alerts"]} == {
        "memory.intent.dead_letter_rate.high",
        "memory.intent.latency.p95.high",
    }


def test_resolve_backpressure_thresholds_should_normalize_invalid_inputs() -> None:
    """阈值解析应处理错误输入并保证 L3 不低于 L2。"""

    thresholds = worker_service.resolve_backpressure_thresholds(
        {
            "l2_queue_len": 8000,
            "l3_queue_len": 2000,
            "dead_letter_rate": "bad-number",
            "p95_latency_ms": 0,
        }
    )

    assert thresholds["l2_queue_len"] == 8000.0
    assert thresholds["l3_queue_len"] == 8000.0
    assert thresholds["dead_letter_rate"] == MEMORY_INTENT_BACKPRESSURE_THRESHOLDS["dead_letter_rate"]
    assert thresholds["p95_latency_ms"] == 5000.0


def test_run_once_should_short_circuit_when_l3_is_triggered(monkeypatch) -> None:  # noqa: ANN001
    """L3 熔断时应立即返回，不触发任务状态机。"""

    class _Repo:
        @staticmethod
        def promote_retryable_failed(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("熔断路径不应回捞")

        @staticmethod
        def claim_pending(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("熔断路径不应抢占任务")

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _Repo)

    result = worker_service.run_once(
        _Session(),
        worker_id="worker-circuit",
        process_job=lambda job: None,
        metrics_provider=lambda db: {
            "queue_len": 12000,
            "dead_letter_rate": 0.001,
            "latency_p95_ms": 20.0,
        },
    )

    assert result["status"] == "circuit_open"
    assert result["job_id"] is None
    assert result["backpressure"]["backpressure_level"] == "L3"


def test_run_once_should_reduce_recover_limit_under_l2_backpressure(monkeypatch) -> None:  # noqa: ANN001
    """L2 限流时应降低回捞批量并继续消费任务。"""

    captured: dict[str, object] = {}
    job = _Job(id=321)

    class _Repo:
        @staticmethod
        def promote_retryable_failed(*args, **kwargs):  # noqa: ANN002, ANN003
            captured["limit"] = kwargs.get("limit")
            return 3

        @staticmethod
        def claim_pending(*args, **kwargs):  # noqa: ANN002, ANN003
            return job

        @staticmethod
        def mark_succeeded(*args, **kwargs):  # noqa: ANN002, ANN003
            job.status = "succeeded"
            return job

        @staticmethod
        def mark_failed(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("成功路径不应走 mark_failed")

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _Repo)
    db = _Session()

    result = worker_service.run_once(
        db,
        worker_id="worker-l2",
        process_job=lambda current_job: None,
        retry_recover_limit=100,
        now=datetime(2026, 3, 4, 12, 0, 0),
        metrics_provider=lambda database: {
            "queue_len": 5000,
            "dead_letter_rate": 0.001,
            "latency_p95_ms": 1200.0,
        },
    )

    assert captured["limit"] == 32
    assert result["status"] == "succeeded"
    assert result["recovered_count"] == 3
    assert result["backpressure"]["backpressure_level"] == "L2"
    assert db.commit_called == 1


def test_run_once_should_mark_failed_when_handler_errors(monkeypatch) -> None:  # noqa: ANN001
    """任务处理异常时应写入失败状态并返回错误信息。"""

    captured: dict[str, object] = {}
    job = _Job(id=654)

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
            job.status = "failed"
            return job

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _Repo)
    db = _Session()

    def _raise_handler_error(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("llm timeout")

    result = worker_service.run_once(
        db,
        worker_id="worker-failed",
        process_job=_raise_handler_error,
        now=datetime(2026, 3, 4, 12, 10, 0),
        metrics_provider=lambda database: {
            "queue_len": 300,
            "dead_letter_rate": 0.001,
            "latency_p95_ms": 1000.0,
        },
    )

    assert result["status"] == "failed"
    assert "llm timeout" in result["error"]
    assert captured["worker_id"] == "worker-failed"
    assert db.commit_called == 1


def test_run_once_should_fallback_to_safe_metrics_when_provider_fails(monkeypatch) -> None:  # noqa: ANN001
    """指标采集异常时应降级为安全默认值，不影响消费流程。"""

    class _Repo:
        @staticmethod
        def promote_retryable_failed(*args, **kwargs):  # noqa: ANN002, ANN003
            return 0

        @staticmethod
        def claim_pending(*args, **kwargs):  # noqa: ANN002, ANN003
            return None

    monkeypatch.setattr(worker_service, "user_memory_intent_job_repo", _Repo)

    result = worker_service.run_once(
        _Session(),
        worker_id="worker-safe",
        process_job=lambda job: None,
        metrics_provider=lambda db: (_ for _ in ()).throw(RuntimeError("metrics broken")),
    )

    assert result["status"] == "idle"
    assert result["backpressure"]["queue_len"] == 0
    assert result["backpressure"]["gate_passed"] is True
