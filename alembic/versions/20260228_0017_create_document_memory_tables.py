"""Create document memory tables and seed feature configs.

Revision ID: 20260228_0017
Revises: 20260228_0016
Create Date: 2026-02-28
"""

from __future__ import annotations

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260228_0017"
down_revision = "20260228_0016"
branch_labels = None
depends_on = None


CONFIG_ROWS = (
    {
        "config_key": "feature.enable_document_memory",
        "config_value": "false",
        "value_type": "boolean",
        "category": "feature",
        "description": "文档化永久记忆总开关（两表）",
    },
    {
        "config_key": "feature.enable_document_memory_recall",
        "config_value": "false",
        "value_type": "boolean",
        "category": "feature",
        "description": "文档化记忆召回开关",
    },
    {
        "config_key": "feature.enable_document_memory_flush",
        "config_value": "false",
        "value_type": "boolean",
        "category": "feature",
        "description": "文档化记忆写入开关",
    },
    {
        "config_key": "memory.document.max_results",
        "config_value": "6",
        "value_type": "number",
        "category": "memory",
        "description": "文档记忆检索结果上限",
    },
    {
        "config_key": "memory.document.max_injected_chars",
        "config_value": "1200",
        "value_type": "number",
        "category": "memory",
        "description": "文档记忆注入预算（字符）",
    },
    {
        "config_key": "memory.document.hybrid.vector_weight",
        "config_value": "0.7",
        "value_type": "number",
        "category": "memory",
        "description": "文档记忆向量权重",
    },
    {
        "config_key": "memory.document.hybrid.text_weight",
        "config_value": "0.3",
        "value_type": "number",
        "category": "memory",
        "description": "文档记忆文本权重",
    },
)


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


def _index_exists(conn: sa.engine.Connection, index_name: str) -> bool:
    result = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND indexname = :index_name
            LIMIT 1
            """
        ),
        {"index_name": index_name},
    ).scalar()
    return bool(result)


def upgrade() -> None:
    """升级：创建文档化记忆两表并初始化配置。"""

    conn = op.get_bind()

    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    if not _table_exists(conn, "t_user_memory_document"):
        op.create_table(
            "t_user_memory_document",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "doc_kind",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'daily'"),
            ),
            sa.Column("doc_key", sa.String(length=128), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("content_md", sa.Text(), nullable=False),
            sa.Column("summary_md", sa.Text(), nullable=True),
            sa.Column(
                "source",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'memory'"),
            ),
            sa.Column(
                "scope",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'private'"),
            ),
            sa.Column("scope_ref", sa.String(length=128), nullable=True),
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
            sa.Column(
                "revision",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("source_thread_id", sa.String(length=100), nullable=True),
            sa.Column("source_message_id", sa.BigInteger(), nullable=True),
            sa.Column(
                "create_time",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "update_time",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    if not _index_exists(conn, "idx_user_memory_document_user_update"):
        op.create_index(
            "idx_user_memory_document_user_update",
            "t_user_memory_document",
            ["user_id", "update_time"],
            unique=False,
        )
    if not _index_exists(conn, "idx_user_memory_document_user_scope"):
        op.create_index(
            "idx_user_memory_document_user_scope",
            "t_user_memory_document",
            ["user_id", "source", "scope", "status"],
            unique=False,
        )
    if not _index_exists(conn, "idx_user_memory_document_active_unique"):
        op.create_index(
            "idx_user_memory_document_active_unique",
            "t_user_memory_document",
            ["user_id", "doc_kind", "doc_key"],
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
        )

    if not _table_exists(conn, "t_user_memory_chunk"):
        op.create_table(
            "t_user_memory_chunk",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column(
                "doc_id",
                sa.BigInteger(),
                sa.ForeignKey("t_user_memory_document.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("chunk_no", sa.Integer(), nullable=False),
            sa.Column("start_line", sa.Integer(), nullable=False),
            sa.Column("end_line", sa.Integer(), nullable=False),
            sa.Column("chunk_text", sa.Text(), nullable=False),
            sa.Column("chunk_hash", sa.String(length=64), nullable=False),
            sa.Column(
                "chunk_tsv",
                postgresql.TSVECTOR(),
                sa.Computed("to_tsvector('simple', coalesce(chunk_text, ''))", persisted=True),
                nullable=False,
            ),
            sa.Column("embedding", Vector(1536), nullable=True),
            sa.Column("embedding_model", sa.String(length=128), nullable=True),
            sa.Column(
                "source",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'memory'"),
            ),
            sa.Column(
                "create_time",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "update_time",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    if not _index_exists(conn, "idx_user_memory_chunk_user_doc_no"):
        op.create_index(
            "idx_user_memory_chunk_user_doc_no",
            "t_user_memory_chunk",
            ["user_id", "doc_id", "chunk_no"],
            unique=False,
        )
    if not _index_exists(conn, "idx_user_memory_chunk_doc"):
        op.create_index(
            "idx_user_memory_chunk_doc",
            "t_user_memory_chunk",
            ["doc_id"],
            unique=False,
        )
    if not _index_exists(conn, "idx_user_memory_chunk_unique_hash"):
        op.create_index(
            "idx_user_memory_chunk_unique_hash",
            "t_user_memory_chunk",
            ["user_id", "doc_id", "chunk_hash"],
            unique=True,
        )
    if not _index_exists(conn, "idx_user_memory_chunk_tsv"):
        op.create_index(
            "idx_user_memory_chunk_tsv",
            "t_user_memory_chunk",
            ["chunk_tsv"],
            unique=False,
            postgresql_using="gin",
        )

    if _table_exists(conn, "t_system_config"):
        upsert_sql = sa.text(
            """
            INSERT INTO t_system_config (
                config_key,
                config_value,
                value_type,
                category,
                description,
                is_secret,
                is_readonly
            )
            VALUES (
                :config_key,
                :config_value,
                :value_type,
                :category,
                :description,
                FALSE,
                FALSE
            )
            ON CONFLICT (config_key)
            DO UPDATE SET
                config_value = EXCLUDED.config_value,
                value_type = EXCLUDED.value_type,
                category = EXCLUDED.category,
                description = EXCLUDED.description,
                is_secret = EXCLUDED.is_secret,
                is_readonly = EXCLUDED.is_readonly,
                update_time = NOW()
            """
        )
        for row in CONFIG_ROWS:
            conn.execute(upsert_sql, row)


def downgrade() -> None:
    """降级：删除文档化记忆两表并移除配置。"""

    conn = op.get_bind()

    if _table_exists(conn, "t_system_config"):
        conn.execute(
            sa.text(
                """
                DELETE FROM t_system_config
                WHERE config_key IN (
                    'feature.enable_document_memory',
                    'feature.enable_document_memory_recall',
                    'feature.enable_document_memory_flush',
                    'memory.document.max_results',
                    'memory.document.max_injected_chars',
                    'memory.document.hybrid.vector_weight',
                    'memory.document.hybrid.text_weight'
                )
                """
            )
        )

    if _table_exists(conn, "t_user_memory_chunk"):
        op.drop_table("t_user_memory_chunk")
    if _table_exists(conn, "t_user_memory_document"):
        op.drop_table("t_user_memory_document")
