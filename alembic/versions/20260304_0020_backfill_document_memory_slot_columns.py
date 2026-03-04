"""Backfill document memory slot columns.

Revision ID: 20260304_0020
Revises: 20260304_0019
Create Date: 2026-03-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260304_0020"
down_revision = "20260304_0019"
branch_labels = None
depends_on = None


def _table_exists(conn: sa.engine.Connection, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = :table_name
            LIMIT 1
            """
        ),
        {"table_name": table_name},
    ).scalar()
    return bool(result)


def _column_exists(conn: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).scalar()
    return bool(result)


def _index_exists(conn: sa.engine.Connection, table_name: str, index_name: str) -> bool:
    result = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename = :table_name
              AND indexname = :index_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "index_name": index_name},
    ).scalar()
    return bool(result)


def upgrade() -> None:
    """升级：为文档记忆主表补齐槽位治理字段与索引。"""

    conn = op.get_bind()
    table_name = "t_user_memory_document"

    if not _table_exists(conn, table_name):
        return

    if not _column_exists(conn, table_name, "slot_key"):
        op.add_column(
            table_name,
            sa.Column(
                "slot_key",
                sa.String(length=128),
                nullable=True,
                comment="槽位键（归一化后）",
            ),
        )

    if not _column_exists(conn, table_name, "operation"):
        op.add_column(
            table_name,
            sa.Column(
                "operation",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'upsert'"),
                comment="最近一次写入操作: upsert/archive/drop",
            ),
        )

    if not _column_exists(conn, table_name, "last_event_time"):
        op.add_column(
            table_name,
            sa.Column(
                "last_event_time",
                sa.DateTime(),
                nullable=True,
                comment="最新事件时间（用于乱序保护）",
            ),
        )

    if _column_exists(conn, table_name, "slot_key"):
        conn.execute(
            sa.text(
                """
                UPDATE t_user_memory_document
                SET slot_key = doc_key
                WHERE (slot_key IS NULL OR btrim(slot_key) = '')
                  AND doc_key IS NOT NULL
                """
            )
        )

    if (
        _column_exists(conn, table_name, "slot_key")
        and not _index_exists(conn, table_name, "idx_user_memory_document_user_slot")
    ):
        op.create_index(
            "idx_user_memory_document_user_slot",
            table_name,
            ["user_id", "slot_key", "status"],
            unique=False,
        )

    if (
        _column_exists(conn, table_name, "slot_key")
        and _column_exists(conn, table_name, "last_event_time")
        and not _index_exists(conn, table_name, "idx_user_memory_document_slot_event")
    ):
        op.create_index(
            "idx_user_memory_document_slot_event",
            table_name,
            ["user_id", "slot_key", "last_event_time"],
            unique=False,
        )


def downgrade() -> None:
    """降级：移除文档记忆槽位治理字段与索引。"""

    conn = op.get_bind()
    table_name = "t_user_memory_document"

    if not _table_exists(conn, table_name):
        return

    if _index_exists(conn, table_name, "idx_user_memory_document_slot_event"):
        op.drop_index("idx_user_memory_document_slot_event", table_name=table_name)

    if _index_exists(conn, table_name, "idx_user_memory_document_user_slot"):
        op.drop_index("idx_user_memory_document_user_slot", table_name=table_name)

    if _column_exists(conn, table_name, "last_event_time"):
        op.drop_column(table_name, "last_event_time")

    if _column_exists(conn, table_name, "operation"):
        op.drop_column(table_name, "operation")

    if _column_exists(conn, table_name, "slot_key"):
        op.drop_column(table_name, "slot_key")
