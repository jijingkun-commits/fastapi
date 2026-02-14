"""管理后台总览 API 的请求/响应模型。"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TrendWindow(str, Enum):
    """总览趋势窗口。"""

    ONE_HOUR = "1h"
    TWENTY_FOUR_HOURS = "24h"


class OverviewSummaryResponse(BaseModel):
    """总览摘要响应。"""

    snapshot_at: str
    source: str
    degraded: bool = False
    health_score: Optional[float] = None
    health_level: str = "unknown"
    budget_usage_pct: Optional[float] = None

    request_quality: dict[str, Any] = Field(default_factory=dict)
    stability: dict[str, Any] = Field(default_factory=dict)
    capacity_cost: dict[str, Any] = Field(default_factory=dict)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    freshness: dict[str, Any] = Field(default_factory=dict)
    module_matrix: list[dict[str, Any]] = Field(default_factory=list)
    change_feed: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class TrendPoint(BaseModel):
    """趋势点位。"""

    snapshot_at: str
    health_score: Optional[float] = None
    health_level: str = "unknown"
    budget_usage_pct: Optional[float] = None
    request_total: Optional[float] = None
    error_5xx_rate: Optional[float] = None
    latency_p95_ms: Optional[float] = None


class OverviewTrendsResponse(BaseModel):
    """总览趋势响应。"""

    window: TrendWindow
    interval: str
    points: list[TrendPoint] = Field(default_factory=list)
    generated_at: str
    meta: dict[str, Any] = Field(default_factory=dict)


class StreamResultEventData(BaseModel):
    """SSE result 事件数据体。"""

    snapshot_at: str
    patch: dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None


class StreamInterruptEventData(BaseModel):
    """SSE interrupt 事件数据体。"""

    reason: str
    level: str
    retry_after_sec: Optional[int] = None
    message: Optional[str] = None


class StreamDoneEventData(BaseModel):
    """SSE done 事件数据体。"""

    batch_id: str
    final: bool = False
