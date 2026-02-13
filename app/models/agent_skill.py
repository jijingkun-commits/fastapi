"""技能模型：Agent Skills 存储（中文注释）。"""
from sqlalchemy import Boolean, Column, Integer, String, Text, TIMESTAMP, text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class AgentSkill(Base):
    """Agent 技能表：存储向量化技能知识与触发策略元数据。"""

    __tablename__ = "t_agent_skills"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(String(100), unique=True, nullable=False, comment="技能唯一标识")
    name = Column(String(200), nullable=False, comment="技能名称")
    description = Column(Text, comment="技能描述(用于向量匹配)")
    content = Column(Text, nullable=False, comment="SKILL.md 完整内容")
    file_hash = Column(String(64), comment="文件 MD5 (用于增量同步)")
    embedding = Column(Vector(2048), comment="智谱 embedding-3 向量 (2048维)")

    is_enabled = Column(Boolean, nullable=False, server_default=text("true"), comment="是否启用")
    auto_enabled = Column(Boolean, nullable=False, server_default=text("true"), comment="是否允许自动触发")
    priority = Column(Integer, nullable=False, server_default=text("100"), comment="冲突裁决优先级，值越小优先级越高")
    scope = Column(String(32), nullable=False, server_default=text("'global'"), comment="技能作用域：global/data/todo/admin")
    trigger_phrases = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="触发短语列表")
    conflicts_with = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="冲突技能 ID 列表")

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
