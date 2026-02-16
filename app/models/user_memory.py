"""用户偏好记忆模型（中文注释）。

用于存储跨会话复用的用户显式偏好。
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserMemory(Base):
    """用户偏好记忆表。"""

    __tablename__ = "t_user_memory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="global", comment="作用域")
    memory_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="偏好键")
    memory_value: Mapped[str] = mapped_column(Text, nullable=False, comment="偏好值")
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        default=Decimal("1.000"),
        comment="置信度(0~1)",
    )
    source_thread_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="来源线程ID"
    )
    source_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="来源消息ID"
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", comment="状态")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="最近命中时间"
    )

    __table_args__ = (
        Index("idx_user_memory_user_scope", "user_id", "scope"),
        Index("idx_user_memory_user_update", "user_id", "update_time"),
        Index(
            "idx_user_memory_active_unique",
            "user_id",
            "scope",
            "memory_key",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )
