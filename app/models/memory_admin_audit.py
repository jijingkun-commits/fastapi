"""记忆管理动作审计模型（中文注释）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserMemoryAdminAudit(Base):
    """记忆管理动作审计表。"""

    __tablename__ = "t_user_memory_admin_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operator_user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="操作人用户ID")
    target_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="目标用户ID")
    memory_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="记忆文档ID")
    action: Mapped[str] = mapped_column(String(64), nullable=False, comment="管理动作")
    action_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, comment="动作上下文")
    result_status: Mapped[str] = mapped_column(String(16), nullable=False, comment="执行结果")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="失败原因")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_memory_admin_audit_operator_time", "operator_user_id", "create_time"),
        Index("idx_memory_admin_audit_target_time", "target_user_id", "create_time"),
        Index("idx_memory_admin_audit_memory_time", "memory_id", "create_time"),
    )
