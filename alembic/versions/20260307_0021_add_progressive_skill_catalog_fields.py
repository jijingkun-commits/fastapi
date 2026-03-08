"""为 progressive skill catalog 增加 definition/version 元数据字段。

Revision ID: 20260307_0021
Revises: 20260304_0020
Create Date: 2026-03-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260307_0021"
down_revision = "20260304_0020"
branch_labels = None
depends_on = None


DEF_TABLE = "t_agent_skill_definitions"
VER_TABLE = "t_agent_skill_versions"


def _get_existing_columns(table_name: str) -> set[str]:
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return set()

    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing_def = _get_existing_columns(DEF_TABLE)
    existing_ver = _get_existing_columns(VER_TABLE)

    if "catalog_path" not in existing_def:
        op.add_column(DEF_TABLE, sa.Column("catalog_path", sa.String(length=255), nullable=True))
    if "catalog_order" not in existing_def:
        op.add_column(
            DEF_TABLE,
            sa.Column("catalog_order", sa.Integer(), nullable=False, server_default=sa.text("100")),
        )

    if "catalog_description" not in existing_ver:
        op.add_column(VER_TABLE, sa.Column("catalog_description", sa.Text(), nullable=True))
    if "when_to_use" not in existing_ver:
        op.add_column(VER_TABLE, sa.Column("when_to_use", sa.Text(), nullable=True))

    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return

    op.execute(
        sa.text(
            """
            UPDATE t_agent_skill_definitions
            SET catalog_path = COALESCE(NULLIF(catalog_path, ''), replace(skill_id, '.', '/'))
            WHERE catalog_path IS NULL OR catalog_path = ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE t_agent_skill_definitions
            SET catalog_order = COALESCE(catalog_order, 100)
            WHERE catalog_order IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE t_agent_skill_versions
            SET catalog_description = COALESCE(NULLIF(catalog_description, ''), description)
            WHERE catalog_description IS NULL OR catalog_description = ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE t_agent_skill_versions
            SET when_to_use = COALESCE(
                NULLIF(when_to_use, ''),
                NULLIF(left(COALESCE(catalog_description, description, ''), 160), '')
            )
            WHERE when_to_use IS NULL OR when_to_use = ''
            """
        )
    )


def downgrade() -> None:
    existing_ver = _get_existing_columns(VER_TABLE)
    existing_def = _get_existing_columns(DEF_TABLE)

    if "when_to_use" in existing_ver:
        op.drop_column(VER_TABLE, "when_to_use")
    if "catalog_description" in existing_ver:
        op.drop_column(VER_TABLE, "catalog_description")
    if "catalog_order" in existing_def:
        op.drop_column(DEF_TABLE, "catalog_order")
    if "catalog_path" in existing_def:
        op.drop_column(DEF_TABLE, "catalog_path")
