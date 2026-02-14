"""管理后台总览 API。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, Mapping, Optional, Union
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import OpsMetricSnapshotMinute
from app.schemas.admin_overview import (
    AdminOverviewStreamDoneData,
    AdminOverviewStreamInterruptData,
    AdminOverviewStreamResultData,
    AdminOverviewSummaryResponse,
    AdminOverviewTrendPoint,
    AdminOverviewTrendSeriesResponse,
    AdminOverviewTrendsResponse,
    AdminOverviewTrendWindow,
)
from app.services.admin_overview_service import AdminOverviewService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin-overview", tags=["管理后台总览"])

WINDOW_MINUTES: dict[AdminOverviewTrendWindow, int] = {
    "1h": 60,
    "24h": 24 * 60,
}
STREAM_RETRY_AFTER_SEC = 10


def _utc_now() -> datetime:
    """获取当前 UTC 时间。"""

    return datetime.now(timezone.utc)


def _to_iso8601(value: datetime) -> str:
    """将时间格式化为 RFC3339 字符串。"""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _to_float(value: Any) -> Optional[float]:
    """将数值类型统一为浮点。"""

    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float, Decimal)):
        return float(value)

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return float(candidate)
        except ValueError:
            return None

    return None


def _extract_nested_value(source: Mapping[str, Any], path: Iterable[str]) -> Any:
    """读取嵌套字典值，缺失返回 None。"""

    cursor: Any = source
    for key in path:
        if not isinstance(cursor, Mapping) or key not in cursor:
            return None
        cursor = cursor[key]
    return cursor


def _normalize_trace_id(request: Request) -> Optional[str]:
    """从请求上下文提取 trace_id。"""

    request_state = getattr(request, "state", None)
    correlation_id = getattr(request_state, "correlation_id", None)
    if isinstance(correlation_id, str) and correlation_id:
        return correlation_id

    for header_key in ("X-Request-Id", "X-Correlation-Id"):
        value = request.headers.get(header_key)
        if value:
            return value

    return None


def get_admin_overview_service() -> AdminOverviewService:
    """总览服务依赖。"""

    return AdminOverviewService()


def _query_snapshots_for_window(
    db: Session,
    *,
    minutes: int,
) -> list[OpsMetricSnapshotMinute]:
    """查询窗口内的分钟快照。"""

    cutoff = _utc_now() - timedelta(minutes=minutes)
    return (
        db.query(OpsMetricSnapshotMinute)
        .filter(OpsMetricSnapshotMinute.snapshot_minute >= cutoff)
        .order_by(OpsMetricSnapshotMinute.snapshot_minute.asc())
        .all()
    )


def _build_trend_point(row: OpsMetricSnapshotMinute) -> AdminOverviewTrendPoint:
    """将分钟快照转换为趋势点。"""

    payload = row.snapshot_payload if isinstance(row.snapshot_payload, Mapping) else {}

    request_success_rate = _extract_nested_value(payload, ("request_quality", "success_rate"))
    error_5xx_rate = _extract_nested_value(payload, ("request_quality", "error_5xx_rate"))
    latency_p95_ms = _extract_nested_value(payload, ("request_quality", "latency_p95_ms"))
    qps = _extract_nested_value(payload, ("capacity_cost", "qps"))

    if qps is None:
        qps = payload.get("qps")

    return AdminOverviewTrendPoint(
        timestamp=_to_iso8601(row.snapshot_minute),
        health_score=_to_float(row.health_score),
        request_success_rate=_to_float(request_success_rate),
        error_5xx_rate=_to_float(error_5xx_rate),
        latency_p95_ms=_to_float(latency_p95_ms),
        qps=_to_float(qps),
        budget_usage_pct=_to_float(row.budget_usage_pct),
    )


def _build_window_points(db: Session, window: AdminOverviewTrendWindow) -> list[AdminOverviewTrendPoint]:
    """构建窗口趋势点列表。"""

    rows = _query_snapshots_for_window(db, minutes=WINDOW_MINUTES[window])
    return [_build_trend_point(row) for row in rows]


def _format_sse(event_type: str, data: Mapping[str, Any]) -> str:
    """格式化 SSE 事件。"""

    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


@router.get("/summary", response_model=AdminOverviewSummaryResponse)
def get_admin_overview_summary(
    request: Request,
    service: AdminOverviewService = Depends(get_admin_overview_service),
) -> AdminOverviewSummaryResponse:
    """获取总览快照。"""

    trace_id = _normalize_trace_id(request)
    snapshot = service.get_overview_snapshot(trace_id=trace_id)
    return AdminOverviewSummaryResponse.model_validate(snapshot)


@router.get("/trends", response_model=Union[AdminOverviewTrendsResponse, AdminOverviewTrendSeriesResponse])
def get_admin_overview_trends(
    request: Request,
    window: Optional[AdminOverviewTrendWindow] = Query(default=None),
    db: Session = Depends(get_db),
) -> Union[AdminOverviewTrendsResponse, AdminOverviewTrendSeriesResponse]:
    """获取总览趋势数据。"""

    _ = _normalize_trace_id(request)

    if window is not None:
        points = _build_window_points(db, window)
        snapshot_at = points[-1].timestamp if points else None
        return AdminOverviewTrendSeriesResponse(
            window=window,
            points=points,
            snapshot_at=snapshot_at,
        )

    windows: dict[AdminOverviewTrendWindow, list[AdminOverviewTrendPoint]] = {
        "1h": _build_window_points(db, "1h"),
        "24h": _build_window_points(db, "24h"),
    }

    latest_candidates = [
        windows["24h"][-1].timestamp if windows["24h"] else None,
        windows["1h"][-1].timestamp if windows["1h"] else None,
    ]
    snapshot_at = next((item for item in latest_candidates if item), None)

    return AdminOverviewTrendsResponse(
        windows=windows,
        snapshot_at=snapshot_at,
    )


@router.get("/stream")
async def stream_admin_overview(
    request: Request,
    service: AdminOverviewService = Depends(get_admin_overview_service),
) -> StreamingResponse:
    """总览实时流（SSE）。"""

    trace_id = _normalize_trace_id(request)

    async def _event_generator() -> Any:
        batch_id = f"overview-{uuid4().hex}"

        try:
            snapshot = service.get_overview_snapshot(trace_id=trace_id)
            snapshot_at = str(snapshot.get("snapshot_at") or _to_iso8601(_utc_now()))
            patch = dict(snapshot)
            patch.pop("snapshot_at", None)

            result_data = AdminOverviewStreamResultData(
                snapshot_at=snapshot_at,
                patch=patch,
                trace_id=trace_id,
            )
            yield _format_sse("result", result_data.model_dump(exclude_none=True))
        except Exception as exc:  # pragma: no cover - 异常分支由 API 单测覆盖
            logger.exception("管理后台总览 SSE 推送失败")

            interrupt_data = AdminOverviewStreamInterruptData(
                reason="stream_disconnected",
                level="warning",
                retry_after_sec=STREAM_RETRY_AFTER_SEC,
                message="实时流中断，已建议降级到轮询",
            )
            yield _format_sse("interrupt", interrupt_data.model_dump(exclude_none=True))

            logger.debug("总览流降级原因: %s", type(exc).__name__)
        finally:
            done_data = AdminOverviewStreamDoneData(batch_id=batch_id, final=False)
            yield _format_sse("done", done_data.model_dump(exclude_none=True))

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(_event_generator(), media_type="text/event-stream", headers=headers)
