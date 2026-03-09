"""删除 t_todo 历史完成布尔列。

Revision ID: 20260309_0026
Revises: 20260309_0025
Create Date: 2026-03-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260309_0026"
down_revision = "20260309_0025"
branch_labels = None
depends_on = None


TABLE = "t_todo"
LEGACY_COLUMN = "is_completed"


def _has_column(column_name: str) -> bool:
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return False
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(TABLE):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(TABLE))


def upgrade() -> None:
    """升级：回填空状态后删除历史完成布尔列。"""

    if not _has_column(LEGACY_COLUMN):
        return

    op.execute(
        sa.text(
            """
            UPDATE t_todo
            SET status = CASE
                WHEN status IS NOT NULL AND BTRIM(status) <> '' THEN status
                WHEN COALESCE(progress, 0) >= 100 OR actual_completion_time IS NOT NULL THEN 'done'
                WHEN is_completed IS TRUE THEN 'done'
                ELSE 'todo'
            END
            WHERE status IS NULL OR BTRIM(status) = ''
            """
        )
    )
    op.drop_column(TABLE, LEGACY_COLUMN)


def downgrade() -> None:
    """降级：恢复历史完成布尔列，并由 status 反推值。"""

    if _has_column(LEGACY_COLUMN):
        return

    op.add_column(
        TABLE,
        sa.Column(LEGACY_COLUMN, sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.execute(
        sa.text(
            """
            UPDATE t_todo
            SET is_completed = (status = 'done')
            """
        )
    )
    op.alter_column(TABLE, LEGACY_COLUMN, server_default=None)
