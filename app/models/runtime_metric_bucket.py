"""总览分钟桶事实源模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class RuntimeMetricBucketMinute(Base):
    """总览分钟聚合读模型。"""

    __tablename__ = "t_runtime_metric_bucket_minute"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket_minute: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="分钟桶时间（向下取整到分钟）",
    )
    scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="观测范围：all_business / user_question / admin_operation",
    )
    module_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="模块标识",
    )
    request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="请求数",
    )
    success_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="成功数",
    )
    error_4xx_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="4xx 数",
    )
    error_5xx_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="5xx 数",
    )
    latency_histogram: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="延迟分桶聚合结构",
    )
    cost_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=Decimal("0"),
        server_default=text("0"),
        comment="成本累计",
    )
    last_event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="最后一条事件时间",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "bucket_minute",
            "scope",
            "module_key",
            name="uq_runtime_metric_bucket_minute_bucket_scope_module",
        ),
        CheckConstraint("request_count >= 0", name="ck_runtime_metric_bucket_minute_request_count_non_negative"),
        CheckConstraint("success_count >= 0", name="ck_runtime_metric_bucket_minute_success_count_non_negative"),
        CheckConstraint("error_4xx_count >= 0", name="ck_runtime_metric_bucket_minute_error_4xx_count_non_negative"),
        CheckConstraint("error_5xx_count >= 0", name="ck_runtime_metric_bucket_minute_error_5xx_count_non_negative"),
        CheckConstraint("cost_total >= 0", name="ck_runtime_metric_bucket_minute_cost_total_non_negative"),
        Index("ix_runtime_metric_bucket_minute_scope_bucket", "scope", "bucket_minute"),
        Index("ix_runtime_metric_bucket_minute_module_bucket", "module_key", "bucket_minute"),
        Index("ix_runtime_metric_bucket_minute_last_event_at", "last_event_at"),
    )


__all__ = ["RuntimeMetricBucketMinute"]
