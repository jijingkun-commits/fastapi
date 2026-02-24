"""对话运行态模型（中文注释）。

用于记录每次流式会话（run）的生命周期状态，支撑运行时取消与审计。
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatRunStatus(str, Enum):
    """Run 状态枚举。"""

    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatRun(Base):
    """对话运行态表。"""

    __tablename__ = "t_chat_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="运行ID")
    thread_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="会话线程ID")
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="用户ID")

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ChatRunStatus.RUNNING.value,
        comment="运行状态: running/stopping/stopped/completed/failed",
    )
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="取消原因")
    cancel_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="取消模式: soft/hard")

    cancel_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="取消请求时间")
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="停止时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="完成时间")
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="失败时间")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="失败原因")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_chat_run_thread_status", "thread_id", "status"),
        Index("idx_chat_run_user_created", "user_id", "created_at"),
    )
