"""新增对话运行态表 t_chat_run。

Revision ID: 20260227_0011
Revises: 20260224_0010
Create Date: 2026-02-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260227_0011"
down_revision = "20260224_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级：创建 run 生命周期表。"""

    op.create_table(
        "t_chat_run",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        sa.Column("cancel_reason", sa.String(length=100), nullable=True),
        sa.Column("cancel_mode", sa.String(length=20), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(), nullable=True),
        sa.Column("stopped_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("run_id", name="uq_chat_run_run_id"),
    )

    op.create_index("idx_chat_run_thread_id", "t_chat_run", ["thread_id"], unique=False)
    op.create_index("idx_chat_run_user_id", "t_chat_run", ["user_id"], unique=False)
    op.create_index("idx_chat_run_thread_status", "t_chat_run", ["thread_id", "status"], unique=False)
    op.create_index("idx_chat_run_user_created", "t_chat_run", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    """降级：删除 run 生命周期表。"""

    op.drop_index("idx_chat_run_user_created", table_name="t_chat_run")
    op.drop_index("idx_chat_run_thread_status", table_name="t_chat_run")
    op.drop_index("idx_chat_run_user_id", table_name="t_chat_run")
    op.drop_index("idx_chat_run_thread_id", table_name="t_chat_run")
    op.drop_table("t_chat_run")
