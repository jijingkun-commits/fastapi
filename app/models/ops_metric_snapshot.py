"""总览观测分钟级快照模型。"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class OpsMetricSnapshotMinute(Base):
    """总览驾驶舱分钟级观测快照。"""

    __tablename__ = "t_ops_metric_snapshot_minute"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_minute: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="快照分钟（向下取整到分钟）",
    )
    health_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="健康分（0-100）",
    )
    health_level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="健康等级",
    )
    budget_usage_pct: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        comment="预算使用率百分比",
    )
    snapshot_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="扩展指标快照数据",
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
            "snapshot_minute",
            name="uq_ops_metric_snapshot_minute_snapshot_minute",
        ),
        CheckConstraint(
            "health_score >= 0 AND health_score <= 100",
            name="ck_ops_metric_snapshot_minute_health_score_range",
        ),
        CheckConstraint(
            "budget_usage_pct >= 0",
            name="ck_ops_metric_snapshot_minute_budget_usage_pct_non_negative",
        ),
        Index(
            "ix_ops_metric_snapshot_minute_health_level_minute",
            "health_level",
            "snapshot_minute",
        ),
        Index("ix_ops_metric_snapshot_minute_created_at", "created_at"),
    )

