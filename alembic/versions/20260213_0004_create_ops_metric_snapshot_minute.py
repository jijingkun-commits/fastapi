"""创建总览观测分钟快照表。

Revision ID: 20260213_0004
Revises: 20260213_0003
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260213_0004"
down_revision = "20260213_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级：创建总览驾驶舱分钟级快照表。"""

    op.create_table(
        "t_ops_metric_snapshot_minute",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_minute", sa.DateTime(timezone=True), nullable=False),
        sa.Column("health_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("health_level", sa.String(length=16), nullable=False),
        sa.Column("budget_usage_pct", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column(
            "snapshot_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "health_score >= 0 AND health_score <= 100",
            name="ck_ops_metric_snapshot_minute_health_score_range",
        ),
        sa.CheckConstraint(
            "budget_usage_pct >= 0",
            name="ck_ops_metric_snapshot_minute_budget_usage_pct_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_minute", name="uq_ops_metric_snapshot_minute_snapshot_minute"),
        comment="管理后台总览分钟级观测快照",
    )

    op.create_index(
        "ix_ops_metric_snapshot_minute_health_level_minute",
        "t_ops_metric_snapshot_minute",
        ["health_level", "snapshot_minute"],
        unique=False,
    )
    op.create_index(
        "ix_ops_metric_snapshot_minute_created_at",
        "t_ops_metric_snapshot_minute",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """降级：删除总览驾驶舱分钟级快照表。"""

    op.drop_index("ix_ops_metric_snapshot_minute_created_at", table_name="t_ops_metric_snapshot_minute")
    op.drop_index("ix_ops_metric_snapshot_minute_health_level_minute", table_name="t_ops_metric_snapshot_minute")
    op.drop_table("t_ops_metric_snapshot_minute")
