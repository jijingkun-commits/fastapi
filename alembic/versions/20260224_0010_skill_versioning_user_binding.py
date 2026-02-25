"""新增 Skill 版本与用户绑定三层治理表。

Revision ID: 20260224_0010
Revises: 20260216_0009
Create Date: 2026-02-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "20260224_0010"
down_revision = "20260216_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级：创建 Skill 定义、版本、用户绑定三层表结构。"""

    op.create_table(
        "t_agent_skill_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("skill_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default=sa.text("'global'")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("skill_id", name="uq_agent_skill_definitions_skill_id"),
    )

    op.create_index(
        "idx_agent_skill_definitions_skill_id",
        "t_agent_skill_definitions",
        ["skill_id"],
        unique=True,
    )

    op.create_table(
        "t_agent_skill_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("definition_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding", Vector(dim=2048), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default=sa.text("'global'")),
        sa.Column(
            "trigger_phrases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "conflicts_with",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("published_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["t_agent_skill_definitions.id"],
            ondelete="CASCADE",
            name="fk_agent_skill_versions_definition_id",
        ),
        sa.UniqueConstraint("skill_id", "version", name="uq_agent_skill_versions_skill_id_version"),
    )

    op.create_index("idx_agent_skill_versions_skill_id", "t_agent_skill_versions", ["skill_id"], unique=False)
    op.create_index("idx_agent_skill_versions_status", "t_agent_skill_versions", ["status"], unique=False)
    op.create_index(
        "idx_agent_skill_versions_skill_status",
        "t_agent_skill_versions",
        ["skill_id", "status"],
        unique=False,
    )

    op.create_table(
        "t_user_skill_bindings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("binding_status", sa.String(length=32), nullable=False, server_default=sa.text("'enabled'")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority_override", sa.Integer(), nullable=True),
        sa.Column(
            "config_override",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["t_user.id"], ondelete="CASCADE", name="fk_user_skill_bindings_user_id"),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["t_agent_skill_definitions.skill_id"],
            ondelete="CASCADE",
            name="fk_user_skill_bindings_skill_id",
        ),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_user_skill_bindings_user_skill"),
    )

    op.create_index("idx_user_skill_bindings_user", "t_user_skill_bindings", ["user_id"], unique=False)
    op.create_index("idx_user_skill_bindings_skill", "t_user_skill_bindings", ["skill_id"], unique=False)
    op.create_index("idx_user_skill_bindings_status", "t_user_skill_bindings", ["binding_status"], unique=False)


def downgrade() -> None:
    """降级：删除 Skill 三层治理相关表结构。"""

    op.drop_index("idx_user_skill_bindings_status", table_name="t_user_skill_bindings")
    op.drop_index("idx_user_skill_bindings_skill", table_name="t_user_skill_bindings")
    op.drop_index("idx_user_skill_bindings_user", table_name="t_user_skill_bindings")
    op.drop_table("t_user_skill_bindings")

    op.drop_index("idx_agent_skill_versions_skill_status", table_name="t_agent_skill_versions")
    op.drop_index("idx_agent_skill_versions_status", table_name="t_agent_skill_versions")
    op.drop_index("idx_agent_skill_versions_skill_id", table_name="t_agent_skill_versions")
    op.drop_table("t_agent_skill_versions")

    op.drop_index("idx_agent_skill_definitions_skill_id", table_name="t_agent_skill_definitions")
    op.drop_table("t_agent_skill_definitions")
