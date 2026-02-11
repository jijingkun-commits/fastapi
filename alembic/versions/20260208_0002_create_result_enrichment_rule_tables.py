"""新增结果增强规则配置表。

Revision ID: 20260208_0002
Revises: 20260208_0001
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260208_0002"
down_revision = "20260208_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级：创建结果增强规则与审计表，并插入种子规则。"""
    op.create_table(
        "t_result_enrichment_rule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("rule_name", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("key_column_candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_column", sa.String(length=100), nullable=False),
        sa.Column("source_table", sa.String(length=200), nullable=False),
        sa.Column("source_key_column", sa.String(length=100), nullable=False),
        sa.Column("source_value_column", sa.String(length=100), nullable=False),
        sa.Column("source_date_column", sa.String(length=100), nullable=True),
        sa.Column("result_date_column_candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("priority >= 0", name="ck_result_enrichment_rule_priority_non_negative"),
        sa.CheckConstraint(
            "jsonb_typeof(key_column_candidates) = 'array' AND jsonb_array_length(key_column_candidates) > 0",
            name="ck_result_enrichment_rule_key_candidates_non_empty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result_date_column_candidates) = 'array' AND jsonb_array_length(result_date_column_candidates) > 0",
            name="ck_result_enrichment_rule_result_date_candidates_non_empty",
        ),
        sa.CheckConstraint(
            "source_table ~ '^[a-zA-Z_][a-zA-Z0-9_]*\\.[a-zA-Z_][a-zA-Z0-9_]*$'",
            name="ck_result_enrichment_rule_source_table_format",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_code"),
    )
    op.create_index(
        op.f("ix_t_result_enrichment_rule_id"),
        "t_result_enrichment_rule",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_t_result_enrichment_rule_enabled_priority",
        "t_result_enrichment_rule",
        ["enabled", "priority"],
        unique=False,
    )

    op.create_table(
        "t_result_enrichment_rule_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("op_type", sa.String(length=20), nullable=False),
        sa.Column("before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("operator_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["t_result_enrichment_rule.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_t_result_enrichment_rule_audit_id"),
        "t_result_enrichment_rule_audit",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_t_result_enrichment_rule_audit_rule_id"),
        "t_result_enrichment_rule_audit",
        ["rule_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO t_result_enrichment_rule (
                rule_code, rule_name, enabled, priority,
                key_column_candidates, target_column,
                source_table, source_key_column, source_value_column, source_date_column,
                result_date_column_candidates, description, created_by, updated_by
            ) VALUES
            (
                'customer_name',
                '客户名称补齐',
                true,
                10,
                '["ecif_cust_no"]'::jsonb,
                '客户名称',
                'fdmdata.f_mid_dep_tb',
                'ecif_cust_no',
                'cust_acct_name',
                'data_dt',
                '["data_dt"]'::jsonb,
                '按客户号补齐客户名称，优先同日映射',
                'system',
                'system'
            ),
            (
                'org_name',
                '机构名称补齐',
                false,
                20,
                '["org_no"]'::jsonb,
                '机构名称',
                'fdmdata.f_mid_dep_tb',
                'org_no',
                'org_no_map',
                'data_dt',
                '["data_dt"]'::jsonb,
                '机构编码映射规则（默认关闭，待验证）',
                'system',
                'system'
            ),
            (
                'product_name',
                '产品名称补齐',
                false,
                30,
                '["prod_cd", "product_code"]'::jsonb,
                '产品名称',
                'fdmdata.f_mid_loan_k_tb',
                'prod_cd',
                'prod_nm',
                'data_dt',
                '["data_dt"]'::jsonb,
                '产品编码映射规则（默认关闭，待验证）',
                'system',
                'system'
            )
            """
        )
    )

    op.alter_column("t_result_enrichment_rule", "enabled", server_default=None)
    op.alter_column("t_result_enrichment_rule", "priority", server_default=None)


def downgrade() -> None:
    """降级：删除结果增强规则与审计表。"""
    op.drop_index(op.f("ix_t_result_enrichment_rule_audit_rule_id"), table_name="t_result_enrichment_rule_audit")
    op.drop_index(op.f("ix_t_result_enrichment_rule_audit_id"), table_name="t_result_enrichment_rule_audit")
    op.drop_table("t_result_enrichment_rule_audit")

    op.drop_index("ix_t_result_enrichment_rule_enabled_priority", table_name="t_result_enrichment_rule")
    op.drop_index(op.f("ix_t_result_enrichment_rule_id"), table_name="t_result_enrichment_rule")
    op.drop_table("t_result_enrichment_rule")
