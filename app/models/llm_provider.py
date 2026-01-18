"""LLM 提供商模型（中文注释）。"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Integer, String, Boolean, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LLMProvider(Base):
    """LLM 提供商（如 OpenAI, DeepSeek, Qwen）。"""
    __tablename__ = "t_llm_provider"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="提供商代码")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="显示名称")
    base_url: Mapped[Optional[str]] = mapped_column(String(500), comment="API 基础地址")
    api_key: Mapped[Optional[str]] = mapped_column(String(500), comment="API Key")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    extra_config: Mapped[Optional[dict]] = mapped_column(JSONB, comment="额外配置")
    create_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系
    models: Mapped[List["LLMModel"]] = relationship(
        "LLMModel", back_populates="provider", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<LLMProvider(code={self.code}, name={self.name})>"
