"""为 t_user 增加 data_role 并回填历史数据。

Revision ID: 20260216_0006
Revises: 20260213_0004
Create Date: 2026-02-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260216_0006"
down_revision = "20260213_0004"
branch_labels = None
depends_on = None


def _get_user_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if "t_user" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("t_user")}


def upgrade() -> None:
    """升级：新增 data_role 字段并完成历史回填。"""

    columns = _get_user_columns()
    if not columns:
        return

    if "data_role" not in columns:
        op.add_column(
            "t_user",
            sa.Column(
                "data_role",
                sa.String(length=50),
                nullable=True,
                server_default=sa.text("'staff'"),
                comment="数据角色: head_president/department_gm/department_vgm/staff",
            ),
        )

    op.execute("UPDATE t_user SET data_role = 'staff' WHERE data_role IS NULL OR BTRIM(data_role) = ''")
    op.alter_column(
        "t_user",
        "data_role",
        existing_type=sa.String(length=50),
        nullable=False,
        server_default=sa.text("'staff'"),
    )


def downgrade() -> None:
    """降级：移除 data_role 字段。"""

    columns = _get_user_columns()
    if "data_role" in columns:
        op.drop_column("t_user", "data_role")
