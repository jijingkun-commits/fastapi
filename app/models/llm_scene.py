"""LLM 场景治理模型（中文注释）。"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Boolean, TIMESTAMP, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


SCENE_TYPE_TEXT = "text"
SCENE_TYPE_IMAGE = "image"
SCENE_TYPE_VIDEO = "video"
SCENE_TYPE_AUDIO = "audio"
SCENE_TYPE_EMBEDDING = "embedding"
SCENE_TYPE_VISION = "vision"
SCENE_TYPE_RERANK = "rerank"
SCENE_TYPE_ASR = "asr"
SCENE_TYPE_TTS = "tts"

SCENE_TYPE_ENUM = (
    SCENE_TYPE_TEXT,
    SCENE_TYPE_IMAGE,
    SCENE_TYPE_VIDEO,
    SCENE_TYPE_AUDIO,
    SCENE_TYPE_EMBEDDING,
    SCENE_TYPE_VISION,
    SCENE_TYPE_RERANK,
    SCENE_TYPE_ASR,
    SCENE_TYPE_TTS,
)


class LLMScene(Base):
    """LLM 场景治理表。"""

    __tablename__ = "t_llm_scene"
    __table_args__ = (
        CheckConstraint("position('.' in scene_key) > 0", name="ck_t_llm_scene_scene_key_format"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scene_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="调用点唯一键")
    scene_name: Mapped[str] = mapped_column(String(120), nullable=False, comment="场景名称")
    route_group: Mapped[str] = mapped_column(String(32), nullable=False, default="default_chat", comment="路由分组")
    scene_type: Mapped[str] = mapped_column(String(32), nullable=False, default=SCENE_TYPE_TEXT, comment="场景类型")

    description: Mapped[Optional[str]] = mapped_column(Text, comment="场景说明")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    create_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    def __repr__(self):
        return f"<LLMScene(scene_key={self.scene_key}, scene_type={self.scene_type})>"
