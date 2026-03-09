"""为 skill version 增加 tool_contract 字段。

Revision ID: 20260308_0022
Revises: 20260307_0021
Create Date: 2026-03-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260308_0022"
down_revision = "20260307_0021"
branch_labels = None
depends_on = None


VER_TABLE = "t_agent_skill_versions"


def _get_existing_columns(table_name: str) -> set[str]:
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return set()

    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing_ver = _get_existing_columns(VER_TABLE)

    if "tool_contract" not in existing_ver:
        op.add_column(
            VER_TABLE,
            sa.Column("tool_contract", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        )

    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return

    op.execute(
        sa.text(
            """
            UPDATE t_agent_skill_versions
            SET tool_contract = COALESCE(tool_contract, '{}'::jsonb)
            WHERE tool_contract IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE t_agent_skill_versions
            SET tool_contract = jsonb_build_object(
                'required_tools', jsonb_build_array('knowledge_search'),
                'optional_tools', '[]'::jsonb,
                'tool_groups', jsonb_build_array('knowledge'),
                'expose_after_load', true
            )
            WHERE skill_id = 'knowledge-search'
              AND status = 'published'
              AND COALESCE(tool_contract, '{}'::jsonb) = '{}'::jsonb
            """
        )
    )


def downgrade() -> None:
    existing_ver = _get_existing_columns(VER_TABLE)

    if "tool_contract" in existing_ver:
        op.drop_column(VER_TABLE, "tool_contract")
