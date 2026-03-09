"""管理后台总览 API。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Union

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.schemas.admin_overview import (
    AdminOverviewStreamInterruptData,
    AdminOverviewStreamResultData,
    AdminOverviewSummaryResponse,
    AdminOverviewTrendSeriesResponse,
    AdminOverviewTrendsResponse,
    AdminOverviewTrendWindow,
)
from app.services.admin_overview_query_service import AdminOverviewQueryService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin-overview", tags=["管理后台总览"])

STREAM_RETRY_AFTER_SEC = 10
STREAM_PUSH_INTERVAL_SEC = 10


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso8601(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _normalize_trace_id(request: Request) -> Optional[str]:
    request_state = getattr(request, "state", None)
    correlation_id = getattr(request_state, "correlation_id", None)
    if isinstance(correlation_id, str) and correlation_id:
        return correlation_id

    for header_key in ("X-Request-Id", "X-Correlation-Id"):
        value = request.headers.get(header_key)
        if value:
            return value
    return None


def get_admin_overview_service() -> AdminOverviewQueryService:
    return AdminOverviewQueryService()


def _format_sse(event_type: str, data: Mapping[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


@router.get("/summary", response_model=AdminOverviewSummaryResponse)
def get_admin_overview_summary(
    request: Request,
    service: AdminOverviewQueryService = Depends(get_admin_overview_service),
) -> AdminOverviewSummaryResponse:
    trace_id = _normalize_trace_id(request)
    snapshot = service.get_overview_snapshot(trace_id=trace_id)
    return AdminOverviewSummaryResponse.model_validate(snapshot)


@router.get("/trends", response_model=Union[AdminOverviewTrendsResponse, AdminOverviewTrendSeriesResponse])
def get_admin_overview_trends(
    request: Request,
    window: Optional[AdminOverviewTrendWindow] = Query(default=None),
    service: AdminOverviewQueryService = Depends(get_admin_overview_service),
) -> Union[AdminOverviewTrendsResponse, AdminOverviewTrendSeriesResponse]:
    _ = _normalize_trace_id(request)
    payload = service.get_overview_trends(window=window)
    if window is None:
        return AdminOverviewTrendsResponse.model_validate(payload)
    return AdminOverviewTrendSeriesResponse.model_validate(payload)


@router.get("/stream")
async def stream_admin_overview(
    request: Request,
    service: AdminOverviewQueryService = Depends(get_admin_overview_service),
) -> StreamingResponse:
    trace_id = _normalize_trace_id(request)

    async def _event_generator() -> Any:
        while True:
            if await request.is_disconnected():
                logger.debug("总览 SSE 客户端已断开，停止推送: trace_id=%s", trace_id)
                break

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
            except Exception:
                logger.exception("管理后台总览 SSE 推送失败")
                interrupt_data = AdminOverviewStreamInterruptData(
                    reason="stream_disconnected",
                    level="warning",
                    retry_after_sec=STREAM_RETRY_AFTER_SEC,
                    message="实时流中断，已建议降级到轮询",
                )
                yield _format_sse("interrupt", interrupt_data.model_dump(exclude_none=True))
                break

            if await request.is_disconnected():
                logger.debug("总览 SSE 客户端已断开，停止推送: trace_id=%s", trace_id)
                break

            await asyncio.sleep(STREAM_PUSH_INTERVAL_SEC)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(_event_generator(), media_type="text/event-stream", headers=headers)
