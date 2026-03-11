"""管理后台总览 API Schema。"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AdminOverviewTrendWindow = Literal["1h", "24h"]


class AdminOverviewTrendPoint(BaseModel):
    """总览趋势单点。"""

    timestamp: str
    request_qps: Optional[float] = None
    question_qps: Optional[float] = None


class AdminOverviewTrendsResponse(BaseModel):
    """多窗口趋势响应。"""

    windows: dict[AdminOverviewTrendWindow, list[AdminOverviewTrendPoint]]
    snapshot_at: Optional[str] = None


class AdminOverviewTrendSeriesResponse(BaseModel):
    """单窗口趋势响应。"""

    window: AdminOverviewTrendWindow
    status: str
    points: list[AdminOverviewTrendPoint] = Field(default_factory=list)
    snapshot_at: Optional[str] = None


class AdminOverviewSummaryResponse(BaseModel):
    """总览快照响应。"""

    model_config = ConfigDict(extra="forbid")

    snapshot_at: str
    source: str
    degraded: bool
    request_quality: dict[str, Any] = Field(default_factory=dict)
    question_health: dict[str, Any] = Field(default_factory=dict)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    freshness: dict[str, Any] = Field(default_factory=dict)
    module_matrix: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class AdminOverviewStreamResultData(BaseModel):
    """SSE result 事件 data。"""

    snapshot_at: str
    patch: dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None


class AdminOverviewStreamInterruptData(BaseModel):
    """SSE interrupt 事件 data。"""

    reason: str
    level: Literal["info", "warning", "critical"]
    retry_after_sec: Optional[int] = None
    message: Optional[str] = None


class AdminOverviewStreamDoneData(BaseModel):
    """SSE done 事件 data。"""

    batch_id: str
    final: bool = False


class AdminOverviewStreamResultEvent(BaseModel):
    """SSE result 事件。"""

    type: Literal["result"] = "result"
    data: AdminOverviewStreamResultData
    node: Optional[str] = None


class AdminOverviewStreamInterruptEvent(BaseModel):
    """SSE interrupt 事件。"""

    type: Literal["interrupt"] = "interrupt"
    data: AdminOverviewStreamInterruptData
    node: Optional[str] = None


class AdminOverviewStreamDoneEvent(BaseModel):
    """SSE done 事件。"""

    type: Literal["done"] = "done"
    data: AdminOverviewStreamDoneData
    node: Optional[str] = None


__all__ = [
    "AdminOverviewTrendWindow",
    "AdminOverviewTrendPoint",
    "AdminOverviewTrendsResponse",
    "AdminOverviewTrendSeriesResponse",
    "AdminOverviewSummaryResponse",
    "AdminOverviewStreamResultData",
    "AdminOverviewStreamInterruptData",
    "AdminOverviewStreamDoneData",
    "AdminOverviewStreamResultEvent",
    "AdminOverviewStreamInterruptEvent",
    "AdminOverviewStreamDoneEvent",
]
