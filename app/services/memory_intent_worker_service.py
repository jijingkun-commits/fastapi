"""用户记忆意图 Worker 服务（中文注释）。"""

from __future__ import annotations

import logging
from datetime import datetime
from math import ceil
from typing import Callable, Mapping

from sqlalchemy.orm import Session

from app.core.config_contract import MEMORY_INTENT_BACKPRESSURE_THRESHOLDS
from app.models.user_memory_intent_job import (
    MEMORY_INTENT_STATUS_DEAD_LETTER,
    MEMORY_INTENT_STATUS_PENDING,
    MEMORY_INTENT_STATUS_SUCCEEDED,
    UserMemoryIntentJob,
)
from app.repositories import user_memory_intent_job_repo
from app.services.config_resolver import ConfigResolver

logger = logging.getLogger(__name__)

BACKPRESSURE_LEVEL_L1 = "L1"
BACKPRESSURE_LEVEL_L2 = "L2"
BACKPRESSURE_LEVEL_L3 = "L3"

_BACKPRESSURE_MODE_ENABLED = "enabled"
_BACKPRESSURE_MODE_DISABLED = "disabled"


def _safe_non_negative_int(value: object, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = int(default)
    return max(0, parsed)


def _safe_non_negative_float(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = float(default)
    return max(0.0, parsed)


def _normalize_backpressure_mode(backpressure_mode: str | None) -> str:
    """规范化背压模式。"""

    normalized = str(backpressure_mode or "").strip().lower()
    if not normalized:
        normalized = ConfigResolver.get_string("memory.intent.backpressure_mode", _BACKPRESSURE_MODE_ENABLED)
        normalized = str(normalized).strip().lower()
    if normalized not in {_BACKPRESSURE_MODE_ENABLED, _BACKPRESSURE_MODE_DISABLED}:
        return _BACKPRESSURE_MODE_ENABLED
    return normalized


def _percentile(values: list[float], percent: float) -> float | None:
    """计算百分位（最近秩）。"""

    if not values:
        return None
    sorted_values = sorted(values)
    index = max(0, ceil(float(percent) * len(sorted_values)) - 1)
    return float(sorted_values[index])


def resolve_backpressure_thresholds(overrides: Mapping[str, object] | None = None) -> dict[str, float]:
    """解析背压阈值（默认值 + 动态配置 + 临时覆盖）。"""

    resolved = {
        "l2_queue_len": float(_safe_non_negative_int(MEMORY_INTENT_BACKPRESSURE_THRESHOLDS.get("l2_queue_len"), 5000)),
        "l3_queue_len": float(_safe_non_negative_int(MEMORY_INTENT_BACKPRESSURE_THRESHOLDS.get("l3_queue_len"), 10000)),
        "dead_letter_rate": float(
            _safe_non_negative_float(MEMORY_INTENT_BACKPRESSURE_THRESHOLDS.get("dead_letter_rate"), 0.005)
        ),
        "p95_latency_ms": float(
            _safe_non_negative_float(MEMORY_INTENT_BACKPRESSURE_THRESHOLDS.get("p95_latency_ms"), 5000.0)
        ),
    }
    dynamic_overrides = ConfigResolver.get_json_dict("memory.intent.backpressure.thresholds", {})
    for source in (dynamic_overrides, dict(overrides or {})):
        if not isinstance(source, dict):
            continue
        if "l2_queue_len" in source:
            resolved["l2_queue_len"] = float(_safe_non_negative_int(source.get("l2_queue_len"), int(resolved["l2_queue_len"])))
        if "l3_queue_len" in source:
            resolved["l3_queue_len"] = float(_safe_non_negative_int(source.get("l3_queue_len"), int(resolved["l3_queue_len"])))
        if "dead_letter_rate" in source:
            resolved["dead_letter_rate"] = float(
                _safe_non_negative_float(source.get("dead_letter_rate"), resolved["dead_letter_rate"])
            )
        if "p95_latency_ms" in source:
            resolved["p95_latency_ms"] = float(
                _safe_non_negative_float(source.get("p95_latency_ms"), resolved["p95_latency_ms"])
            )

    if resolved["l3_queue_len"] < resolved["l2_queue_len"]:
        resolved["l3_queue_len"] = resolved["l2_queue_len"]
    if resolved["p95_latency_ms"] <= 0.0:
        resolved["p95_latency_ms"] = 5000.0

    return resolved


def evaluate_backpressure_level(
    *,
    queue_len: int,
    dead_letter_rate: float = 0.0,
    latency_p95_ms: float | None = None,
    backpressure_mode: str | None = None,
    thresholds: Mapping[str, object] | None = None,
    metrics_gate_enabled: bool | None = None,
) -> dict[str, object]:
    """评估背压等级与门禁结论。"""

    resolved_thresholds = resolve_backpressure_thresholds(thresholds)
    mode = _normalize_backpressure_mode(backpressure_mode)

    queue_value = _safe_non_negative_int(queue_len)
    dead_rate_value = _safe_non_negative_float(dead_letter_rate)
    latency_value = None
    if latency_p95_ms is not None:
        latency_value = _safe_non_negative_float(latency_p95_ms)

    if mode == _BACKPRESSURE_MODE_DISABLED:
        return {
            "mode": mode,
            "level": BACKPRESSURE_LEVEL_L1,
            "queue_len": queue_value,
            "dead_letter_rate": dead_rate_value,
            "latency_p95_ms": latency_value,
            "throttle_enabled": False,
            "circuit_open": False,
            "gate_passed": True,
            "alerts": [],
            "thresholds": resolved_thresholds,
        }

    alerts: list[dict[str, str]] = []
    l2_queue_len = int(resolved_thresholds["l2_queue_len"])
    l3_queue_len = int(resolved_thresholds["l3_queue_len"])

    if queue_value >= l3_queue_len:
        level = BACKPRESSURE_LEVEL_L3
        alerts.append(
            {
                "code": "memory.intent.queue.l3",
                "severity": "critical",
                "message": f"pending 队列 {queue_value} 已达到 L3 阈值 {l3_queue_len}",
            }
        )
    elif queue_value >= l2_queue_len:
        level = BACKPRESSURE_LEVEL_L2
        alerts.append(
            {
                "code": "memory.intent.queue.l2",
                "severity": "warning",
                "message": f"pending 队列 {queue_value} 已达到 L2 阈值 {l2_queue_len}",
            }
        )
    else:
        level = BACKPRESSURE_LEVEL_L1

    dead_letter_threshold = float(resolved_thresholds["dead_letter_rate"])
    if dead_rate_value > dead_letter_threshold:
        alerts.append(
            {
                "code": "memory.intent.dead_letter_rate.high",
                "severity": "warning",
                "message": (
                    f"dead_letter_rate={dead_rate_value:.4f} 超过阈值 {dead_letter_threshold:.4f}"
                ),
            }
        )

    latency_threshold = float(resolved_thresholds["p95_latency_ms"])
    if latency_value is not None and latency_value > latency_threshold:
        alerts.append(
            {
                "code": "memory.intent.latency.p95.high",
                "severity": "warning",
                "message": f"P95 时延 {latency_value:.1f}ms 超过阈值 {latency_threshold:.1f}ms",
            }
        )

    if metrics_gate_enabled is None:
        gate_enabled = ConfigResolver.get_bool("memory.intent.metrics_gate_enabled", True)
    else:
        gate_enabled = bool(metrics_gate_enabled)

    return {
        "mode": mode,
        "level": level,
        "queue_len": queue_value,
        "dead_letter_rate": dead_rate_value,
        "latency_p95_ms": latency_value,
        "throttle_enabled": level in {BACKPRESSURE_LEVEL_L2, BACKPRESSURE_LEVEL_L3},
        "circuit_open": level == BACKPRESSURE_LEVEL_L3,
        "gate_passed": (not gate_enabled) or len(alerts) == 0,
        "alerts": alerts,
        "thresholds": resolved_thresholds,
    }


def emit_memory_intent_metrics(
    *,
    queue_len: int,
    dead_letter_rate: float,
    latency_p95_ms: float | None,
    backpressure_mode: str | None = None,
    thresholds: Mapping[str, object] | None = None,
    metrics_gate_enabled: bool | None = None,
) -> dict[str, object]:
    """构建观测指标与门禁快照。"""

    evaluated = evaluate_backpressure_level(
        queue_len=queue_len,
        dead_letter_rate=dead_letter_rate,
        latency_p95_ms=latency_p95_ms,
        backpressure_mode=backpressure_mode,
        thresholds=thresholds,
        metrics_gate_enabled=metrics_gate_enabled,
    )
    return {
        "backpressure_mode": str(evaluated["mode"]),
        "backpressure_level": str(evaluated["level"]),
        "queue_len": int(evaluated["queue_len"]),
        "dead_letter_rate": float(evaluated["dead_letter_rate"]),
        "latency_p95_ms": evaluated["latency_p95_ms"],
        "throttle_enabled": bool(evaluated["throttle_enabled"]),
        "circuit_open": bool(evaluated["circuit_open"]),
        "gate_passed": bool(evaluated["gate_passed"]),
        "alerts": list(evaluated["alerts"]),
        "thresholds": dict(evaluated["thresholds"]),
    }


def collect_memory_intent_observability(
    db: Session,
    *,
    latency_sample_limit: int = 256,
) -> dict[str, float | int | None]:
    """从任务表采集背压评估所需指标。"""

    safe_sample_limit = max(1, int(latency_sample_limit))
    queue_len = int(
        db.query(UserMemoryIntentJob)
        .filter(UserMemoryIntentJob.status == MEMORY_INTENT_STATUS_PENDING)
        .count()
    )
    dead_letter_count = int(
        db.query(UserMemoryIntentJob)
        .filter(UserMemoryIntentJob.status == MEMORY_INTENT_STATUS_DEAD_LETTER)
        .count()
    )
    total_count = int(db.query(UserMemoryIntentJob).count())
    dead_letter_rate = (dead_letter_count / total_count) if total_count > 0 else 0.0

    latency_rows = (
        db.query(UserMemoryIntentJob.event_time, UserMemoryIntentJob.update_time)
        .filter(UserMemoryIntentJob.status == MEMORY_INTENT_STATUS_SUCCEEDED)
        .order_by(UserMemoryIntentJob.update_time.desc(), UserMemoryIntentJob.id.desc())
        .limit(safe_sample_limit)
        .all()
    )
    latency_values: list[float] = []
    for event_time, update_time in latency_rows:
        if not isinstance(event_time, datetime) or not isinstance(update_time, datetime):
            continue
        latency_ms = (update_time - event_time).total_seconds() * 1000.0
        if latency_ms >= 0.0:
            latency_values.append(float(latency_ms))

    return {
        "queue_len": queue_len,
        "dead_letter_rate": dead_letter_rate,
        "latency_p95_ms": _percentile(latency_values, 0.95),
    }


def _resolve_runtime_metrics(
    db: Session,
    *,
    metrics_provider: Callable[[Session], Mapping[str, float | int | None]] | None = None,
    backpressure_mode: str | None = None,
) -> dict[str, object]:
    """统一收敛背压指标采集异常，避免影响主链路。"""

    try:
        observability = (
            dict(metrics_provider(db)) if metrics_provider is not None else collect_memory_intent_observability(db)
        )
    except Exception:
        logger.warning("memory_intent_backpressure_observability_failed", exc_info=True)
        observability = {
            "queue_len": 0,
            "dead_letter_rate": 0.0,
            "latency_p95_ms": None,
        }

    return emit_memory_intent_metrics(
        queue_len=_safe_non_negative_int(observability.get("queue_len"), 0),
        dead_letter_rate=_safe_non_negative_float(observability.get("dead_letter_rate"), 0.0),
        latency_p95_ms=observability.get("latency_p95_ms"),
        backpressure_mode=backpressure_mode,
    )


def run_once(
    db: Session,
    *,
    worker_id: str,
    process_job: Callable[[UserMemoryIntentJob], None],
    lease_seconds: int = user_memory_intent_job_repo.DEFAULT_WORKER_LEASE_SECONDS,
    max_attempts: int = user_memory_intent_job_repo.DEFAULT_MAX_ATTEMPTS,
    retry_base_seconds: int = user_memory_intent_job_repo.DEFAULT_RETRY_BASE_SECONDS,
    retry_recover_limit: int = user_memory_intent_job_repo.DEFAULT_RETRY_RECOVER_LIMIT,
    now: datetime | None = None,
    backpressure_mode: str | None = None,
    metrics_provider: Callable[[Session], Mapping[str, float | int | None]] | None = None,
    metrics_sink: Callable[[dict[str, object]], None] | None = None,
) -> dict[str, object]:
    """执行一轮 Worker 消费：回捞重试、抢占任务、推进状态机。"""

    current_time = now or datetime.now()
    metrics_snapshot = _resolve_runtime_metrics(
        db,
        metrics_provider=metrics_provider,
        backpressure_mode=backpressure_mode,
    )
    if metrics_sink is not None:
        metrics_sink(dict(metrics_snapshot))

    if bool(metrics_snapshot["circuit_open"]):
        return {
            "status": "circuit_open",
            "job_id": None,
            "recovered_count": 0,
            "backpressure": metrics_snapshot,
        }

    effective_recover_limit = int(retry_recover_limit)
    if bool(metrics_snapshot["throttle_enabled"]):
        effective_recover_limit = min(effective_recover_limit, 32)

    recovered_count = user_memory_intent_job_repo.promote_retryable_failed(
        db,
        now=current_time,
        limit=effective_recover_limit,
    )
    job = user_memory_intent_job_repo.claim_pending(
        db,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        now=current_time,
    )
    if job is None:
        return {
            "status": "idle",
            "job_id": None,
            "recovered_count": int(recovered_count),
            "backpressure": metrics_snapshot,
        }

    try:
        process_job(job)
        finished_time = now or datetime.now()
        finished = user_memory_intent_job_repo.mark_succeeded(
            db,
            job_id=int(job.id),
            worker_id=worker_id,
            now=finished_time,
        )
        db.commit()
        resolved = finished or job
        return {
            "status": str(resolved.status),
            "job_id": int(resolved.id),
            "recovered_count": int(recovered_count),
            "backpressure": metrics_snapshot,
        }
    except Exception as process_error:
        try:
            failed_time = now or datetime.now()
            failed = user_memory_intent_job_repo.mark_failed(
                db,
                job_id=int(job.id),
                worker_id=worker_id,
                error_message=str(process_error),
                max_attempts=max_attempts,
                base_retry_seconds=retry_base_seconds,
                now=failed_time,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        resolved = failed or job
        return {
            "status": str(resolved.status),
            "job_id": int(resolved.id),
            "recovered_count": int(recovered_count),
            "error": str(process_error),
            "backpressure": metrics_snapshot,
        }


class MemoryIntentWorkerService:
    """记忆意图 Worker 轻量服务封装。"""

    def __init__(
        self,
        *,
        worker_id: str,
        lease_seconds: int = user_memory_intent_job_repo.DEFAULT_WORKER_LEASE_SECONDS,
        max_attempts: int = user_memory_intent_job_repo.DEFAULT_MAX_ATTEMPTS,
        retry_base_seconds: int = user_memory_intent_job_repo.DEFAULT_RETRY_BASE_SECONDS,
        retry_recover_limit: int = user_memory_intent_job_repo.DEFAULT_RETRY_RECOVER_LIMIT,
        backpressure_mode: str | None = None,
        metrics_provider: Callable[[Session], Mapping[str, float | int | None]] | None = None,
        metrics_sink: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self.worker_id = str(worker_id)
        self.lease_seconds = int(lease_seconds)
        self.max_attempts = int(max_attempts)
        self.retry_base_seconds = int(retry_base_seconds)
        self.retry_recover_limit = int(retry_recover_limit)
        self.backpressure_mode = backpressure_mode
        self.metrics_provider = metrics_provider
        self.metrics_sink = metrics_sink

    def run_once(
        self,
        db: Session,
        *,
        process_job: Callable[[UserMemoryIntentJob], None],
        now: datetime | None = None,
    ) -> dict[str, object]:
        """按实例配置执行一轮消费。"""

        return run_once(
            db,
            worker_id=self.worker_id,
            process_job=process_job,
            lease_seconds=self.lease_seconds,
            max_attempts=self.max_attempts,
            retry_base_seconds=self.retry_base_seconds,
            retry_recover_limit=self.retry_recover_limit,
            now=now,
            backpressure_mode=self.backpressure_mode,
            metrics_provider=self.metrics_provider,
            metrics_sink=self.metrics_sink,
        )

