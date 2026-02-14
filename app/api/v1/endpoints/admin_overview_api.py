"""管理后台总览 API。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Mapping, Protocol
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.schemas.admin_overview import (
    OverviewSummaryResponse,
    OverviewTrendsResponse,
    StreamDoneEventData,
    StreamInterruptEventData,
    StreamResultEventData,
    TrendWindow,
)

logger = logging.getLogger(__name__)

try:  # pragma: no cover - 依赖 WS-01，当前分支可不存在
    from app.models import OpsMetricSnapshotMinute
except Exception:  # pragma: no cover
    OpsMetricSnapshotMinute = None


router = APIRouter(prefix="/admin-overview", tags=["管理后台总览"])


def _utc_now() -> datetime:
    """返回当前 UTC 时间。"""

    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """将时间标准化为 UTC。"""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_iso8601(value: datetime) -> str:
    """将时间转为 RFC3339 字符串。"""

    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _to_float(value: Any) -> float | None:
    """将输入尽可能转换为浮点数。"""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
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


def _format_sse(event_type: str, payload: dict[str, Any]) -> bytes:
    """格式化 SSE 事件。"""

    body = json.dumps(jsonable_encoder(payload), ensure_ascii=False)
    return f"event: {event_type}\ndata: {body}\n\n".encode("utf-8")


class OverviewGateway(Protocol):
    """总览网关协议。"""

    def get_summary(self, trace_id: str | None = None) -> dict[str, Any]:
        """获取总览摘要。"""

    def get_trends(self, window: TrendWindow, trace_id: str | None = None) -> dict[str, Any]:
        """获取总览趋势。"""


class DefaultOverviewGateway:
    """总览网关默认实现。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._service_delegate = self._build_service_delegate()

    @staticmethod
    def _build_service_delegate() -> Any | None:
        """尝试连接 WS-02 聚合服务。"""

        try:
            from app.services.admin_overview_service import AdminOverviewService

            return AdminOverviewService()
        except Exception:
            return None

    def get_summary(self, trace_id: str | None = None) -> dict[str, Any]:
        """返回总览摘要。"""

        if self._service_delegate is not None and hasattr(self._service_delegate, "get_overview_snapshot"):
            try:
                snapshot = self._service_delegate.get_overview_snapshot(trace_id=trace_id)
                if isinstance(snapshot, Mapping):
                    return self._normalize_summary(snapshot, trace_id=trace_id)
            except Exception:
                logger.exception("总览聚合服务调用失败，降级到本地快照")

        stored_payload = self._get_latest_snapshot_payload()
        if stored_payload is not None:
            return self._normalize_summary(stored_payload, trace_id=trace_id)

        return self._build_empty_summary(trace_id=trace_id)

    def get_trends(self, window: TrendWindow, trace_id: str | None = None) -> dict[str, Any]:
        """返回总览趋势。"""

        points = self._load_trend_points(window)
        if not points:
            summary = self.get_summary(trace_id=trace_id)
            points = [self._summary_to_trend_point(summary)]

        return {
            "window": window,
            "interval": "1m" if window == TrendWindow.ONE_HOUR else "1h",
            "points": points,
            "generated_at": _to_iso8601(_utc_now()),
            "meta": {
                "trace_id": trace_id,
            },
        }

    def _get_latest_snapshot_payload(self) -> dict[str, Any] | None:
        """从分钟快照表读取最新快照。"""

        if OpsMetricSnapshotMinute is None:
            return None

        try:
            row = (
                self._db.query(OpsMetricSnapshotMinute)
                .order_by(OpsMetricSnapshotMinute.snapshot_minute.desc())
                .first()
            )
        except SQLAlchemyError:
            logger.debug("读取总览快照失败，可能尚未迁移分钟快照表", exc_info=True)
            return None

        if row is None:
            return None

        payload = dict(getattr(row, "snapshot_payload", {}) or {})
        payload.setdefault("snapshot_at", _to_iso8601(row.snapshot_minute))
        payload.setdefault("source", "snapshot_store")
        payload.setdefault("degraded", True)
        payload.setdefault("health_score", _to_float(getattr(row, "health_score", None)))
        payload.setdefault("health_level", getattr(row, "health_level", "unknown"))
        payload.setdefault("budget_usage_pct", _to_float(getattr(row, "budget_usage_pct", None)))
        return payload

    def _load_trend_points(self, window: TrendWindow) -> list[dict[str, Any]]:
        """从分钟快照读取趋势点。"""

        if OpsMetricSnapshotMinute is None:
            return []

        now = _utc_now()
        start = now - (timedelta(hours=1) if window == TrendWindow.ONE_HOUR else timedelta(hours=24))

        try:
            rows = (
                self._db.query(OpsMetricSnapshotMinute)
                .filter(OpsMetricSnapshotMinute.snapshot_minute >= start)
                .order_by(OpsMetricSnapshotMinute.snapshot_minute.asc())
                .all()
            )
        except SQLAlchemyError:
            logger.debug("读取总览趋势失败，可能尚未迁移分钟快照表", exc_info=True)
            return []

        if not rows:
            return []

        if window == TrendWindow.ONE_HOUR:
            selected_rows = rows[-60:]
            return [self._snapshot_row_to_trend_point(row) for row in selected_rows]

        hour_buckets: dict[datetime, Any] = {}
        for row in rows:
            snapshot_minute = _as_utc(row.snapshot_minute)
            bucket_key = snapshot_minute.replace(minute=0, second=0, microsecond=0)
            cached = hour_buckets.get(bucket_key)
            if cached is None or _as_utc(cached.snapshot_minute) < snapshot_minute:
                hour_buckets[bucket_key] = row

        ordered_hours = sorted(hour_buckets.keys())
        return [self._snapshot_row_to_trend_point(hour_buckets[key]) for key in ordered_hours]

    def _snapshot_row_to_trend_point(self, row: Any) -> dict[str, Any]:
        """将快照行转为趋势点。"""

        payload = dict(getattr(row, "snapshot_payload", {}) or {})
        request_quality = payload.get("request_quality")
        if not isinstance(request_quality, Mapping):
            request_quality = {}

        return {
            "snapshot_at": _to_iso8601(row.snapshot_minute),
            "health_score": _to_float(getattr(row, "health_score", None)),
            "health_level": str(getattr(row, "health_level", "unknown") or "unknown"),
            "budget_usage_pct": _to_float(getattr(row, "budget_usage_pct", None)),
            "request_total": _to_float(request_quality.get("request_total")),
            "error_5xx_rate": _to_float(request_quality.get("error_5xx_rate")),
            "latency_p95_ms": _to_float(request_quality.get("latency_p95_ms")),
        }

    def _summary_to_trend_point(self, summary: Mapping[str, Any]) -> dict[str, Any]:
        """将 summary 降级成单点趋势。"""

        request_quality = summary.get("request_quality")
        if not isinstance(request_quality, Mapping):
            request_quality = {}

        return {
            "snapshot_at": str(summary.get("snapshot_at") or _to_iso8601(_utc_now())),
            "health_score": _to_float(summary.get("health_score")),
            "health_level": str(summary.get("health_level") or "unknown"),
            "budget_usage_pct": _to_float(summary.get("budget_usage_pct")),
            "request_total": _to_float(request_quality.get("request_total")),
            "error_5xx_rate": _to_float(request_quality.get("error_5xx_rate")),
            "latency_p95_ms": _to_float(request_quality.get("latency_p95_ms")),
        }

    def _normalize_summary(self, payload: Mapping[str, Any], trace_id: str | None) -> dict[str, Any]:
        """规范化总览响应结构。"""

        snapshot = dict(payload)
        generated_at = _to_iso8601(_utc_now())

        snapshot["snapshot_at"] = str(snapshot.get("snapshot_at") or generated_at)
        snapshot["source"] = str(snapshot.get("source") or "live")
        snapshot["degraded"] = bool(snapshot.get("degraded", False))
        snapshot["health_score"] = _to_float(snapshot.get("health_score"))
        snapshot["health_level"] = str(snapshot.get("health_level") or "unknown")
        snapshot["budget_usage_pct"] = _to_float(snapshot.get("budget_usage_pct"))

        for key in ("request_quality", "stability", "capacity_cost", "freshness"):
            value = snapshot.get(key)
            snapshot[key] = dict(value) if isinstance(value, Mapping) else {}

        alerts = snapshot.get("alerts")
        snapshot["alerts"] = [dict(item) for item in alerts if isinstance(item, Mapping)] if isinstance(alerts, list) else []

        module_matrix = snapshot.get("module_matrix")
        if isinstance(module_matrix, list):
            snapshot["module_matrix"] = [
                dict(item) for item in module_matrix if isinstance(item, Mapping)
            ]
        else:
            snapshot["module_matrix"] = self._build_module_matrix_baseline()

        change_feed = snapshot.get("change_feed")
        snapshot["change_feed"] = [
            dict(item) for item in change_feed if isinstance(item, Mapping)
        ] if isinstance(change_feed, list) else []

        meta = snapshot.get("meta")
        normalized_meta = dict(meta) if isinstance(meta, Mapping) else {}
        normalized_meta["generated_at"] = str(normalized_meta.get("generated_at") or generated_at)
        normalized_meta["trace_id"] = trace_id
        snapshot["meta"] = normalized_meta

        return snapshot

    def _build_empty_summary(self, trace_id: str | None) -> dict[str, Any]:
        """构建空总览结构。"""

        generated_at = _to_iso8601(_utc_now())
        return {
            "snapshot_at": generated_at,
            "source": "empty",
            "degraded": True,
            "health_score": None,
            "health_level": "unknown",
            "budget_usage_pct": None,
            "request_quality": {
                "status": "unknown",
                "score": None,
                "request_total": None,
                "success_rate": None,
                "error_5xx_rate": None,
                "latency_p95_ms": None,
            },
            "stability": {
                "status": "unknown",
                "score": None,
                "critical_alerts": None,
                "warning_alerts": None,
            },
            "capacity_cost": {
                "status": "unknown",
                "score": None,
                "qps": None,
                "cost_per_minute": None,
                "budget_per_minute": None,
                "budget_usage_pct": None,
            },
            "alerts": [
                {
                    "code": "overview.snapshot.unavailable",
                    "severity": "warning",
                    "message": "总览快照暂不可用，请稍后重试",
                    "status": "active",
                }
            ],
            "freshness": {
                "status": "unknown",
                "score": None,
                "health_level": "unknown",
                "delay_sec": None,
                "expired": True,
            },
            "module_matrix": self._build_module_matrix_baseline(),
            "change_feed": [],
            "meta": {
                "generated_at": generated_at,
                "trace_id": trace_id,
                "fallback_reason": "snapshot_unavailable",
            },
        }

    def _build_module_matrix_baseline(self) -> list[dict[str, Any]]:
        """构建模块矩阵基础信息。"""

        active_user_count: int | None = None
        message_count: int | None = None

        try:
            active_user_count = self._db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar()
        except SQLAlchemyError:
            logger.debug("统计活跃用户失败", exc_info=True)

        try:
            message_count = self._db.query(func.count(ChatMessage.id)).scalar()
        except SQLAlchemyError:
            logger.debug("统计消息总量失败", exc_info=True)

        return [
            {
                "key": "user_admin",
                "label": "用户与权限",
                "health_level": "unknown",
                "score": None,
                "active_users": active_user_count,
            },
            {
                "key": "chat_runtime",
                "label": "对话运行链路",
                "health_level": "unknown",
                "score": None,
                "message_total": message_count,
            },
        ]


def get_admin_overview_gateway(db: Session = Depends(get_db)) -> OverviewGateway:
    """注入总览网关。"""

    return DefaultOverviewGateway(db)


@router.get("/summary", response_model=OverviewSummaryResponse)
def get_admin_overview_summary(
    request: Request,
    gateway: OverviewGateway = Depends(get_admin_overview_gateway),
):
    """获取总览摘要。"""

    trace_id = request.headers.get("X-Trace-Id")
    return gateway.get_summary(trace_id=trace_id)


@router.get("/trends", response_model=OverviewTrendsResponse)
def get_admin_overview_trends(
    request: Request,
    window: TrendWindow = Query(default=TrendWindow.ONE_HOUR, description="趋势窗口: 1h/24h"),
    gateway: OverviewGateway = Depends(get_admin_overview_gateway),
):
    """获取总览趋势。"""

    trace_id = request.headers.get("X-Trace-Id")
    return gateway.get_trends(window=window, trace_id=trace_id)


@router.get("/stream")
async def stream_admin_overview(
    request: Request,
    gateway: OverviewGateway = Depends(get_admin_overview_gateway),
):
    """提供总览实时 SSE 事件流。"""

    trace_id = request.headers.get("X-Trace-Id")
    batch_id = uuid4().hex

    async def _event_generator():
        try:
            summary = gateway.get_summary(trace_id=trace_id)
            patch = dict(summary)
            snapshot_at = str(patch.pop("snapshot_at", _to_iso8601(_utc_now())))

            result_data = StreamResultEventData(
                snapshot_at=snapshot_at,
                patch=patch,
                trace_id=trace_id,
            )
            yield _format_sse(
                "result",
                {
                    "type": "result",
                    "data": result_data.model_dump(exclude_none=True),
                },
            )
        except Exception:
            logger.exception("总览 SSE 推送失败，返回 interrupt 事件")
            interrupt_data = StreamInterruptEventData(
                reason="stream_degraded",
                level="warning",
                retry_after_sec=10,
                message="实时通道暂不可用，请降级轮询 /api/v1/admin-overview/summary",
            )
            yield _format_sse(
                "interrupt",
                {
                    "type": "interrupt",
                    "data": interrupt_data.model_dump(exclude_none=True),
                },
            )
        finally:
            done_data = StreamDoneEventData(batch_id=batch_id, final=True)
            yield _format_sse(
                "done",
                {
                    "type": "done",
                    "data": done_data.model_dump(exclude_none=True),
                },
            )

    return StreamingResponse(_event_generator(), media_type="text/event-stream")
