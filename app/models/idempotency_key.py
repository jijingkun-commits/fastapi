"""幂等键模型，对应表 t_idempotency_key（中文注释）。"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Integer, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdempotencyKey(Base):
    """幂等键记录，用于防止重复提交。"""

    __tablename__ = "t_idempotency_key"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False, comment="幂等键")
    user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, comment="用户ID")
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False, comment="端点标识")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started", comment="状态")
    thread_id: Mapped[Optional[str]] = mapped_column(String(100), comment="对话线程ID")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, comment="更新时间")
    
    # 复合索引定义
    __table_args__ = (
        # 幂等键快速查找
        Index("idx_idempotency_key_lookup", "key", "user_id"),
    )
