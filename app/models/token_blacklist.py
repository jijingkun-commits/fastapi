"""Token黑名单模型，用于实现服务端登出（中文注释）。

当用户登出或被禁用时，将其Token的JTI加入黑名单，
使得该Token在过期前也无法使用。
"""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TokenBlacklist(Base):
    """Token黑名单表，存储已失效的Token标识。"""
    __tablename__ = "t_token_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_jti: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, comment="JWT ID，唯一标识"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("t_user.id"), comment="关联用户ID"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, comment="Token原过期时间，用于清理"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), comment="加入黑名单时间"
    )
