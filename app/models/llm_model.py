"""LLM 模型定义（中文注释）。"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Boolean, TIMESTAMP, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LLMModel(Base):
    """具体的 LLM 模型（如 gpt-4, deepseek-chat）。"""
    __tablename__ = "t_llm_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("t_llm_provider.id", ondelete="CASCADE"), nullable=False
    )
    model_code: Mapped[str] = mapped_column(String(100), nullable=False, comment="模型代码")
    model_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="显示名称")
    model_type: Mapped[str] = mapped_column(String(50), default="chat", comment="模型类型")

    # 能力标记
    supports_thinking: Mapped[bool] = mapped_column(Boolean, default=False, comment="支持深度思考")
    supports_tool_call: Mapped[bool] = mapped_column(Boolean, default=True, comment="支持工具调用")
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=True, comment="支持流式输出")
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=4096, comment="最大输出 token")
    context_window: Mapped[int] = mapped_column(Integer, default=32000, comment="上下文窗口大小")

    # 默认参数
    default_temperature: Mapped[float] = mapped_column(Float, default=0.7, comment="默认温度")
    thinking_budget: Mapped[int] = mapped_column(Integer, default=4096, comment="思考 token 预算")

    # 显示配置
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否默认模型")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    # 速率限制
    rpm_limit: Mapped[Optional[int]] = mapped_column(Integer, comment="每分钟请求数限制")
    tpm_limit: Mapped[Optional[int]] = mapped_column(Integer, comment="每分钟 token 限制")

    extra_config: Mapped[Optional[dict]] = mapped_column(JSONB, comment="额外配置")
    create_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系
    provider: Mapped["LLMProvider"] = relationship(
        "LLMProvider", back_populates="models"
    )
    scenes: Mapped[list["LLMScene"]] = relationship(
        "LLMScene",
        back_populates="default_model",
    )

    def __repr__(self):
        return f"<LLMModel(code={self.model_code}, name={self.model_name})>"
