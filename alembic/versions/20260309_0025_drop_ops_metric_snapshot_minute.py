"""删除总览旧展示快照表。

Revision ID: 20260309_0025
Revises: 20260309_0024
Create Date: 2026-03-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260309_0025"
down_revision = "20260309_0024"
branch_labels = None
depends_on = None


TABLE = "t_ops_metric_snapshot_minute"
IDX_LEVEL_MINUTE = "ix_ops_metric_snapshot_minute_health_level_minute"
IDX_CREATED_AT = "ix_ops_metric_snapshot_minute_created_at"


def _table_exists() -> bool | None:
    if not hasattr(op, "get_context") or not hasattr(op, "get_bind"):
        return None
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return False
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(TABLE)


def _existing_indexes() -> set[str] | None:
    if not hasattr(op, "get_context") or not hasattr(op, "get_bind"):
        return None
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return set()
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(TABLE)} if inspector.has_table(TABLE) else set()


def upgrade() -> None:
    """升级：删除旧快照表，收敛到分钟桶单一事实源。"""

    table_exists = _table_exists()
    if table_exists is False:
        return

    existing_indexes = _existing_indexes() or {IDX_CREATED_AT, IDX_LEVEL_MINUTE}
    if IDX_CREATED_AT in existing_indexes:
        op.drop_index(IDX_CREATED_AT, table_name=TABLE)
    if IDX_LEVEL_MINUTE in existing_indexes:
        op.drop_index(IDX_LEVEL_MINUTE, table_name=TABLE)
    op.drop_table(TABLE)


def downgrade() -> None:
    """降级：恢复旧展示快照表结构。"""

    table_exists = _table_exists()
    if table_exists is True:
        return

    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_minute", sa.DateTime(timezone=True), nullable=False),
        sa.Column("health_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("health_level", sa.String(length=16), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("budget_usage_pct", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column(
            "snapshot_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "health_score IS NULL OR (health_score >= 0 AND health_score <= 100)",
            name="ck_ops_metric_snapshot_minute_health_score_range",
        ),
        sa.CheckConstraint(
            "budget_usage_pct IS NULL OR budget_usage_pct >= 0",
            name="ck_ops_metric_snapshot_minute_budget_usage_pct_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_minute", name="uq_ops_metric_snapshot_minute_snapshot_minute"),
        comment="管理后台总览分钟级展示快照（已退役）",
    )
    op.create_index(IDX_LEVEL_MINUTE, TABLE, ["health_level", "snapshot_minute"], unique=False)
    op.create_index(IDX_CREATED_AT, TABLE, ["created_at"], unique=False)
