"""运行时请求观测缓存。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable


def _utc_now() -> datetime:
    """返回当前 UTC 时间。"""

    return datetime.now(timezone.utc)


def _ensure_aware_datetime(value: datetime) -> datetime:
    """将时间统一为带时区的 UTC 时间。"""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class RuntimeRequestMetricEvent:
    """单条请求观测事件。"""

    recorded_at: datetime
    path: str
    status_code: int
    duration_ms: float


class RuntimeRequestMetricsStore:
    """内存请求观测缓冲区。"""

    def __init__(
        self,
        *,
        max_events: int = 6000,
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._events: deque[RuntimeRequestMetricEvent] = deque(maxlen=max_events)
        self._now_provider = now_provider
        self._lock = Lock()

    def record(
        self,
        *,
        path: str,
        status_code: int,
        duration_ms: float,
        recorded_at: datetime | None = None,
    ) -> None:
        """记录单条请求观测事件。"""

        if not path:
            return

        try:
            normalized_status = int(status_code)
        except (TypeError, ValueError):
            normalized_status = 0

        try:
            normalized_duration = float(duration_ms)
        except (TypeError, ValueError):
            normalized_duration = 0.0

        if normalized_duration < 0:
            normalized_duration = 0.0

        timestamp = _ensure_aware_datetime(recorded_at or self._now_provider())
        event = RuntimeRequestMetricEvent(
            recorded_at=timestamp,
            path=str(path),
            status_code=normalized_status,
            duration_ms=normalized_duration,
        )

        with self._lock:
            self._events.append(event)

    def list_recent(self, *, window_sec: int = 300) -> tuple[datetime, list[RuntimeRequestMetricEvent]]:
        """读取指定窗口内的观测事件。"""

        normalized_window_sec = max(1, int(window_sec))
        now = _ensure_aware_datetime(self._now_provider())
        cutoff = now - timedelta(seconds=normalized_window_sec)

        with self._lock:
            events = [event for event in self._events if event.recorded_at >= cutoff]

        return now, events


runtime_request_metrics_store = RuntimeRequestMetricsStore()


def record_runtime_request_metric(*, path: str, status_code: int, duration_ms: float) -> None:
    """写入全局请求观测事件。"""

    runtime_request_metrics_store.record(
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
    )


__all__ = [
    "RuntimeRequestMetricEvent",
    "RuntimeRequestMetricsStore",
    "record_runtime_request_metric",
    "runtime_request_metrics_store",
]

