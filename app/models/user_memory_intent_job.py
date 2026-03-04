"""用户记忆意图异步任务模型（中文注释）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


MEMORY_INTENT_STATUS_PENDING = "pending"
MEMORY_INTENT_STATUS_PROCESSING = "processing"
MEMORY_INTENT_STATUS_SUCCEEDED = "succeeded"
MEMORY_INTENT_STATUS_FAILED = "failed"
MEMORY_INTENT_STATUS_DEAD_LETTER = "dead_letter"


class UserMemoryIntentJob(Base):
    """用户记忆意图任务表。"""

    __tablename__ = "t_user_memory_intent_job"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户ID")
    source_thread_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="来源线程ID",
    )
    source_message_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="来源消息ID",
    )
    event_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        comment="事件时间",
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="任务输入载荷",
    )
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="业务幂等键")
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=MEMORY_INTENT_STATUS_PENDING,
        comment="任务状态",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="已尝试次数",
    )
    next_retry_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        comment="下次重试时间",
    )
    lease_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="租约过期时间",
    )
    claimed_by: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="当前认领 worker",
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="认领时间",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="失败摘要",
    )
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )

    __table_args__ = (
        Index("idx_user_memory_intent_job_user_create", "user_id", "create_time"),
        Index(
            "idx_user_memory_intent_job_status_retry",
            "status",
            "next_retry_time",
            "create_time",
        ),
        Index("idx_user_memory_intent_job_status_lease", "status", "lease_until"),
        Index(
            "idx_user_memory_intent_job_source_unique",
            "user_id",
            "source_message_id",
            unique=True,
        ),
    )
