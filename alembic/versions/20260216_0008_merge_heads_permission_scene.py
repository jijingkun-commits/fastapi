"""收敛 askdata 权限链路与场景治理链路的多 Head。

Revision ID: 20260216_0008
Revises: 20260216_0006, 20260216_0007
Create Date: 2026-02-16
"""

from __future__ import annotations


# revision identifiers, used by Alembic.
revision = "20260216_0008"
down_revision = ("20260216_0006", "20260216_0007")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级：合并分支，不涉及 DDL。"""

    pass


def downgrade() -> None:
    """降级：拆分分支，不涉及 DDL。"""

    pass
