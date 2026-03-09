"""总览分钟桶写入器。"""

from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session

from app.db.session import get_db_context
from app.models import RuntimeMetricBucketMinute
from app.observability.request_scope_resolver import RequestMetricScope, resolve_request_metric_context

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """返回当前 UTC 时间。"""

    return datetime.now(timezone.utc)


def _ensure_aware_datetime(value: datetime) -> datetime:
    """将时间统一为带时区的 UTC 时间。"""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_bucket_minute(value: datetime) -> datetime:
    """向下取整到分钟。"""

    aware_value = _ensure_aware_datetime(value)
    return aware_value.replace(second=0, microsecond=0)


def _normalize_status_code(value: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_duration_ms(value: float) -> float:
    try:
        duration_ms = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(duration_ms, 0.0)


def _normalize_cost_total(value: float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        normalized = value
    else:
        try:
            normalized = Decimal(str(value))
        except Exception:
            normalized = Decimal("0")
    return normalized if normalized >= 0 else Decimal("0")


def _is_success_status(status_code: int) -> bool:
    return 200 <= status_code < 400


def _build_latency_histogram(previous: dict | None, duration_ms: float) -> dict[str, float | int | dict[str, int]]:
    normalized_previous = previous if isinstance(previous, dict) else {}
    count = int(normalized_previous.get("count") or 0) + 1
    total_ms = float(normalized_previous.get("total_ms") or 0.0) + duration_ms
    min_ms = duration_ms if count == 1 else min(float(normalized_previous.get("min_ms") or duration_ms), duration_ms)
    max_ms = duration_ms if count == 1 else max(float(normalized_previous.get("max_ms") or duration_ms), duration_ms)
    buckets = normalized_previous.get("buckets") if isinstance(normalized_previous.get("buckets"), dict) else {}
    normalized_buckets = {str(key): int(value) for key, value in buckets.items()}

    if duration_ms <= 100:
        bucket_key = "le_100"
    elif duration_ms <= 300:
        bucket_key = "le_300"
    elif duration_ms <= 1000:
        bucket_key = "le_1000"
    else:
        bucket_key = "gt_1000"
    normalized_buckets[bucket_key] = normalized_buckets.get(bucket_key, 0) + 1

    return {
        "count": count,
        "total_ms": round(total_ms, 4),
        "min_ms": round(min_ms, 4),
        "max_ms": round(max_ms, 4),
        "buckets": normalized_buckets,
    }


class RuntimeMetricBucketWriter:
    """将请求事实写入分钟桶读模型。"""

    def __init__(
        self,
        *,
        session_context_factory: Callable[[], AbstractContextManager[Session]] = get_db_context,
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._session_context_factory = session_context_factory
        self._now_provider = now_provider

    def record_request(
        self,
        *,
        path: str,
        status_code: int,
        duration_ms: float,
        recorded_at: datetime | None = None,
        cost_total: float | Decimal = 0,
    ) -> bool:
        """将单条请求写入分钟桶。"""

        normalized_path = str(path or "")
        if not normalized_path:
            return False

        normalized_status = _normalize_status_code(status_code)
        normalized_duration = _normalize_duration_ms(duration_ms)
        normalized_cost = _normalize_cost_total(cost_total)
        event_time = _ensure_aware_datetime(recorded_at or self._now_provider())
        bucket_minute = _normalize_bucket_minute(event_time)
        resolved = resolve_request_metric_context(normalized_path)

        scopes: list[RequestMetricScope]
        if resolved.scope is RequestMetricScope.ADMIN_OPERATION:
            scopes = [RequestMetricScope.ADMIN_OPERATION]
        elif resolved.scope is RequestMetricScope.USER_QUESTION:
            scopes = [RequestMetricScope.ALL_BUSINESS, RequestMetricScope.USER_QUESTION]
        else:
            scopes = [RequestMetricScope.ALL_BUSINESS]

        try:
            with self._session_context_factory() as session:
                for scope in scopes:
                    row = (
                        session.query(RuntimeMetricBucketMinute)
                        .filter(RuntimeMetricBucketMinute.bucket_minute == bucket_minute)
                        .filter(RuntimeMetricBucketMinute.scope == scope.value)
                        .filter(RuntimeMetricBucketMinute.module_key == resolved.module_key)
                        .one_or_none()
                    )

                    if row is None:
                        row = RuntimeMetricBucketMinute(
                            bucket_minute=bucket_minute,
                            scope=scope.value,
                            module_key=resolved.module_key,
                            request_count=0,
                            success_count=0,
                            error_4xx_count=0,
                            error_5xx_count=0,
                            latency_histogram={},
                            cost_total=Decimal("0"),
                            last_event_at=event_time,
                        )
                        session.add(row)

                    row.request_count += 1
                    if _is_success_status(normalized_status):
                        row.success_count += 1
                    elif 400 <= normalized_status < 500:
                        row.error_4xx_count += 1
                    elif normalized_status >= 500:
                        row.error_5xx_count += 1
                    row.latency_histogram = _build_latency_histogram(row.latency_histogram, normalized_duration)
                    row.cost_total = _normalize_cost_total(row.cost_total + normalized_cost)
                    if event_time > row.last_event_at:
                        row.last_event_at = event_time

                session.commit()
            return True
        except Exception:
            logger.exception("写入总览分钟桶失败")
            return False


runtime_metric_bucket_writer = RuntimeMetricBucketWriter()


__all__ = ["RuntimeMetricBucketWriter", "runtime_metric_bucket_writer"]
