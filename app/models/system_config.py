"""系统配置模型（中文注释）。"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Boolean, TIMESTAMP, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemConfig(Base):
    """系统通用配置（键值对）。"""
    __tablename__ = "t_system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="配置键")
    config_value: Mapped[str] = mapped_column(Text, nullable=False, comment="配置值")
    value_type: Mapped[str] = mapped_column(String(20), default="string", comment="值类型")
    category: Mapped[Optional[str]] = mapped_column(String(50), comment="分类")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="说明")
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否敏感")
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否只读")
    create_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<SystemConfig(key={self.config_key}, value={self.config_value})>"
