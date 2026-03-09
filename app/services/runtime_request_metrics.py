"""运行时请求观测写入口。"""

from __future__ import annotations

from datetime import datetime

from app.services.runtime_metric_bucket_writer import runtime_metric_bucket_writer


def record_runtime_request_metric(
    *,
    path: str,
    status_code: int,
    duration_ms: float,
    recorded_at: datetime | None = None,
) -> None:
    """将 API 请求写入分钟桶事实源。"""

    runtime_metric_bucket_writer.record_request(
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        recorded_at=recorded_at,
    )


__all__ = [
    "record_runtime_request_metric",
    "runtime_metric_bucket_writer",
]
