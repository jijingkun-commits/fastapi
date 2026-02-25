"""技能模型：Skill 定义、版本与用户绑定（中文注释）。"""
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class AgentSkill(Base):
    """兼容层技能表：存储向量化技能知识与触发策略元数据。"""

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
    priority = Column(
        Integer,
        nullable=False,
        server_default=text("100"),
        comment="冲突裁决优先级，值越小优先级越高",
    )
    scope = Column(
        String(32),
        nullable=False,
        server_default=text("'global'"),
        comment="技能作用域：global/data/todo/admin",
    )
    trigger_phrases = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="触发短语列表")
    conflicts_with = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="冲突技能 ID 列表")

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class AgentSkillDefinition(Base):
    """技能定义层：管理稳定 skill_id 与基础语义。"""

    __tablename__ = "t_agent_skill_definitions"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(String(100), unique=True, nullable=False, comment="稳定技能标识")
    name = Column(String(200), nullable=False, comment="技能名称")
    description = Column(Text, comment="技能定义描述")
    scope = Column(
        String(32),
        nullable=False,
        server_default=text("'global'"),
        comment="定义默认作用域：global/data/todo/admin",
    )
    is_enabled = Column(Boolean, nullable=False, server_default=text("true"), comment="定义层总开关")
    tags = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="定义标签")

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class AgentSkillVersion(Base):
    """技能版本层：承载可发布与可回滚的内容版本。"""

    __tablename__ = "t_agent_skill_versions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_agent_skill_versions_skill_id_version"),
        Index("idx_agent_skill_versions_skill_id", "skill_id"),
        Index("idx_agent_skill_versions_status", "status"),
        Index("idx_agent_skill_versions_skill_status", "skill_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    definition_id = Column(
        Integer,
        ForeignKey("t_agent_skill_definitions.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联技能定义 ID",
    )
    skill_id = Column(String(100), nullable=False, comment="稳定技能标识")
    version = Column(String(64), nullable=False, comment="版本号")
    status = Column(
        String(32),
        nullable=False,
        server_default=text("'draft'"),
        comment="版本状态：draft/published/rollbacked/deprecated",
    )

    name = Column(String(200), nullable=False, comment="版本展示名称")
    description = Column(Text, comment="版本描述")
    content = Column(Text, nullable=False, comment="版本化 SKILL.md 内容")
    file_hash = Column(String(64), comment="版本内容哈希")
    embedding = Column(Vector(2048), comment="版本向量")

    is_enabled = Column(Boolean, nullable=False, server_default=text("true"), comment="版本启用状态")
    auto_enabled = Column(Boolean, nullable=False, server_default=text("true"), comment="自动触发开关")
    priority = Column(Integer, nullable=False, server_default=text("100"), comment="版本优先级")
    scope = Column(
        String(32),
        nullable=False,
        server_default=text("'global'"),
        comment="版本作用域：global/data/todo/admin",
    )
    trigger_phrases = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="触发短语")
    conflicts_with = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"), comment="冲突技能")

    published_at = Column(TIMESTAMP, comment="发布时间")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class UserSkillBinding(Base):
    """用户绑定层：管理用户级版本绑定与覆盖配置。"""

    __tablename__ = "t_user_skill_bindings"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill_bindings_user_skill"),
        Index("idx_user_skill_bindings_user", "user_id"),
        Index("idx_user_skill_bindings_skill", "skill_id"),
        Index("idx_user_skill_bindings_status", "binding_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("t_user.id", ondelete="CASCADE"), nullable=False, comment="用户 ID")
    skill_id = Column(
        String(100),
        ForeignKey("t_agent_skill_definitions.skill_id", ondelete="CASCADE"),
        nullable=False,
        comment="技能 ID",
    )
    version = Column(String(64), comment="绑定版本号")
    binding_status = Column(
        String(32),
        nullable=False,
        server_default=text("'enabled'"),
        comment="绑定状态：enabled/disabled/rollbacked",
    )
    is_enabled = Column(Boolean, nullable=False, server_default=text("true"), comment="绑定启用开关")
    priority_override = Column(Integer, comment="用户级优先级覆盖")
    config_override = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"), comment="用户覆盖配置")

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
