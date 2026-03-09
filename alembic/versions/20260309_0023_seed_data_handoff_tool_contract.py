"""为数据类 skill 回填 data_expert handoff tool_contract。

Revision ID: 20260309_0023
Revises: 20260308_0022
Create Date: 2026-03-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260309_0023"
down_revision = "20260308_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return

    op.execute(
        sa.text(
            """
            UPDATE t_agent_skill_versions
            SET tool_contract = jsonb_build_object(
                'required_tools', jsonb_build_array('assign_to_data_expert'),
                'optional_tools', '[]'::jsonb,
                'tool_groups', jsonb_build_array('data', 'handoff'),
                'expose_after_load', true
            )
            WHERE skill_id IN ('sql-expert', 'data-insight')
              AND status = 'published'
            """
        )
    )


def downgrade() -> None:
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return

    op.execute(
        sa.text(
            """
            UPDATE t_agent_skill_versions
            SET tool_contract = '{}'::jsonb
            WHERE skill_id IN ('sql-expert', 'data-insight')
              AND status = 'published'
            """
        )
    )
