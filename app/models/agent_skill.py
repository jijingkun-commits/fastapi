"""技能模型：Agent Skills 存储（中文注释）。"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.base import Base


class AgentSkill(Base):
    """Agent 技能表：存储向量化的技能知识。"""
    __tablename__ = "t_agent_skills"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(String(100), unique=True, nullable=False, comment="技能唯一标识")
    name = Column(String(200), nullable=False, comment="技能名称")
    description = Column(Text, comment="技能描述(用于向量匹配)")
    content = Column(Text, nullable=False, comment="SKILL.md 完整内容")
    file_hash = Column(String(64), comment="文件 MD5 (用于增量同步)")
    embedding = Column(Vector(2048), comment="智谱 embedding-3 向量 (2048维)")
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
