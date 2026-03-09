"""为 t_chat_run 增加 last_activity_at 与 active 查询索引。

Revision ID: 20260308_0022
Revises: 20260307_0021
Create Date: 2026-03-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260308_0022"
down_revision = "20260307_0021"
branch_labels = None
depends_on = None


TABLE = "t_chat_run"
INDEX = "idx_chat_run_user_status_updated"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("last_activity_at", sa.DateTime(), nullable=True, comment="最近活动时间"))
    op.create_index(INDEX, TABLE, ["user_id", "status", sa.text("updated_at DESC")], unique=False)


def downgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE)
    op.drop_column(TABLE, "last_activity_at")
