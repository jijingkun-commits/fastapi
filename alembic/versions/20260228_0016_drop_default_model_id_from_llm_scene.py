"""Drop deprecated default_model_id from t_llm_scene.

Revision ID: 20260228_0016
Revises: 20260228_0015
Create Date: 2026-02-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260228_0016"
down_revision = "20260228_0015"
branch_labels = None
depends_on = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).scalar()
    return bool(result)


def _fk_constraints_by_column(conn, table_name: str, column_name: str) -> list[str]:
    rows = conn.execute(
        sa.text(
            """
            SELECT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_name = :table_name
              AND tc.constraint_type = 'FOREIGN KEY'
              AND kcu.column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).fetchall()
    return [row[0] for row in rows]


def _constraint_exists(conn, table_name: str, constraint_name: str) -> bool:
    result = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_name = :table_name
              AND constraint_name = :constraint_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "constraint_name": constraint_name},
    ).scalar()
    return bool(result)


def upgrade() -> None:
    """移除已废弃的 scene 默认模型列，避免多真源。"""

    conn = op.get_bind()

    if not _column_exists(conn, "t_llm_scene", "default_model_id"):
        return

    for constraint_name in _fk_constraints_by_column(conn, "t_llm_scene", "default_model_id"):
        op.drop_constraint(constraint_name, "t_llm_scene", type_="foreignkey")

    op.drop_column("t_llm_scene", "default_model_id")


def downgrade() -> None:
    """回滚时恢复兼容列（空值），并恢复外键约束。"""

    conn = op.get_bind()

    if not _column_exists(conn, "t_llm_scene", "default_model_id"):
        op.add_column(
            "t_llm_scene",
            sa.Column(
                "default_model_id",
                sa.Integer(),
                nullable=True,
                comment="默认模型 ID（兼容字段）",
            ),
        )

    fk_name = "t_llm_scene_default_model_id_fkey"
    if not _constraint_exists(conn, "t_llm_scene", fk_name):
        op.create_foreign_key(
            fk_name,
            "t_llm_scene",
            "t_llm_model",
            ["default_model_id"],
            ["id"],
            ondelete="RESTRICT",
        )
