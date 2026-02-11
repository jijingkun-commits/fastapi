"""结果增强规则模型（中文注释）。"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ResultEnrichmentRule(Base):
    """结果增强规则配置。"""

    __tablename__ = "t_result_enrichment_rule"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(100), unique=True, nullable=False, comment="规则编码")
    rule_name = Column(String(200), nullable=False, comment="规则名称")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    priority = Column(Integer, nullable=False, default=100, comment="优先级（越小越先执行）")

    key_column_candidates = Column(JSONB, nullable=False, comment="结果 key 候选列")
    target_column = Column(String(100), nullable=False, comment="补齐后的目标列")

    source_table = Column(String(200), nullable=False, comment="映射来源表 schema.table")
    source_key_column = Column(String(100), nullable=False, comment="映射来源 key 列")
    source_value_column = Column(String(100), nullable=False, comment="映射来源 value 列")
    source_date_column = Column(String(100), nullable=True, comment="映射来源日期列")
    result_date_column_candidates = Column(JSONB, nullable=False, comment="结果日期候选列")

    description = Column(Text, nullable=True, comment="规则描述")
    created_by = Column(String(64), nullable=True, comment="创建人")
    updated_by = Column(String(64), nullable=True, comment="更新人")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    audits = relationship(
        "ResultEnrichmentRuleAudit",
        back_populates="rule",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("priority >= 0", name="ck_result_enrichment_rule_priority_non_negative"),
        CheckConstraint(
            "jsonb_typeof(key_column_candidates) = 'array' AND jsonb_array_length(key_column_candidates) > 0",
            name="ck_result_enrichment_rule_key_candidates_non_empty",
        ),
        CheckConstraint(
            "jsonb_typeof(result_date_column_candidates) = 'array' "
            "AND jsonb_array_length(result_date_column_candidates) > 0",
            name="ck_result_enrichment_rule_result_date_candidates_non_empty",
        ),
        CheckConstraint(
            "source_table ~ '^[a-zA-Z_][a-zA-Z0-9_]*\\.[a-zA-Z_][a-zA-Z0-9_]*$'",
            name="ck_result_enrichment_rule_source_table_format",
        ),
    )


class ResultEnrichmentRuleAudit(Base):
    """结果增强规则审计日志。"""

    __tablename__ = "t_result_enrichment_rule_audit"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(
        Integer,
        ForeignKey("t_result_enrichment_rule.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    op_type = Column(String(20), nullable=False, comment="操作类型")
    before_json = Column(JSONB, nullable=True, comment="操作前快照")
    after_json = Column(JSONB, nullable=True, comment="操作后快照")
    operator_id = Column(String(64), nullable=True, comment="操作人")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    rule = relationship("ResultEnrichmentRule", back_populates="audits")

