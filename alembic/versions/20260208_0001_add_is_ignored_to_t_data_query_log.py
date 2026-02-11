"""为 t_data_query_log 增加 is_ignored 字段。

Revision ID: 20260208_0001
Revises: 
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260208_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级：新增忽略标记字段。"""
    op.add_column(
        "t_data_query_log",
        sa.Column("is_ignored", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("t_data_query_log", "is_ignored", server_default=None)


def downgrade() -> None:
    """降级：移除忽略标记字段。"""
    op.drop_column("t_data_query_log", "is_ignored")
