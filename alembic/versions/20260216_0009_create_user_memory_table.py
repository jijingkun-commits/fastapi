"""新增用户偏好记忆表 t_user_memory。

Revision ID: 20260216_0009
Revises: 20260216_0008
Create Date: 2026-02-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260216_0009"
down_revision = "20260216_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级：创建 t_user_memory 表与索引。"""

    op.create_table(
        "t_user_memory",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default=sa.text("'global'")),
        sa.Column("memory_key", sa.String(length=128), nullable=False),
        sa.Column("memory_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default=sa.text("1.000")),
        sa.Column("source_thread_id", sa.String(length=100), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("create_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("update_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
    )

    op.create_index(
        "idx_user_memory_user_scope",
        "t_user_memory",
        ["user_id", "scope"],
        unique=False,
    )
    op.create_index(
        "idx_user_memory_user_update",
        "t_user_memory",
        ["user_id", "update_time"],
        unique=False,
    )
    op.create_index(
        "idx_user_memory_active_unique",
        "t_user_memory",
        ["user_id", "scope", "memory_key"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    """降级：删除 t_user_memory 表与索引。"""

    op.drop_index("idx_user_memory_active_unique", table_name="t_user_memory")
    op.drop_index("idx_user_memory_user_update", table_name="t_user_memory")
    op.drop_index("idx_user_memory_user_scope", table_name="t_user_memory")
    op.drop_table("t_user_memory")
