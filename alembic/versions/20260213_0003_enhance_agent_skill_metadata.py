"""增强技能检索元数据与索引。

Revision ID: 20260213_0003
Revises: 20260208_0002
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260213_0003"
down_revision = "20260208_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级：新增技能治理字段与 Hybrid 检索索引。"""

    op.add_column(
        "t_agent_skills",
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "t_agent_skills",
        sa.Column("auto_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "t_agent_skills",
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
    )
    op.add_column(
        "t_agent_skills",
        sa.Column("scope", sa.String(length=32), nullable=False, server_default=sa.text("'global'")),
    )
    op.add_column(
        "t_agent_skills",
        sa.Column(
            "trigger_phrases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "t_agent_skills",
        sa.Column(
            "conflicts_with",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_agent_skills_embedding_ivfflat
            ON t_agent_skills USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_agent_skills_fts
            ON t_agent_skills USING gin (
                to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, '') || ' ' || coalesce(content, ''))
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_agent_skills_trigger_phrases_gin
            ON t_agent_skills USING gin (trigger_phrases jsonb_path_ops)
            """
        )
    )



def downgrade() -> None:
    """降级：移除技能治理字段与 Hybrid 检索索引。"""

    op.execute(sa.text("DROP INDEX IF EXISTS idx_agent_skills_trigger_phrases_gin"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_agent_skills_fts"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_agent_skills_embedding_ivfflat"))

    op.drop_column("t_agent_skills", "conflicts_with")
    op.drop_column("t_agent_skills", "trigger_phrases")
    op.drop_column("t_agent_skills", "scope")
    op.drop_column("t_agent_skills", "priority")
    op.drop_column("t_agent_skills", "auto_enabled")
    op.drop_column("t_agent_skills", "is_enabled")
