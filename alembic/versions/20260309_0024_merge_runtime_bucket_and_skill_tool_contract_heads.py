"""合并 runtime bucket 与 skill tool_contract 两条迁移头。

Revision ID: 20260309_0024
Revises: 20260309_0022, 20260309_0023
Create Date: 2026-03-09
"""

from __future__ import annotations

revision = "20260309_0024"
down_revision = ("20260309_0022", "20260309_0023")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """合并双 head，不执行额外 DDL。"""

    pass


def downgrade() -> None:
    """拆回双 head，不执行额外 DDL。"""

    pass
