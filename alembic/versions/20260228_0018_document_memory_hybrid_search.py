"""Enable document memory hybrid search and embedding lifecycle fields.

Revision ID: 20260228_0018
Revises: 20260228_0017
Create Date: 2026-02-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260228_0018"
down_revision = "20260228_0017"
branch_labels = None
depends_on = None


CONFIG_ROWS = (
    {
        "config_key": "feature.enable_document_memory_hybrid_search",
        "config_value": "false",
        "value_type": "boolean",
        "category": "feature",
        "description": "文档记忆混合检索开关（FTS+向量）",
    },
    {
        "config_key": "feature.enable_document_memory_embedding_worker",
        "config_value": "false",
        "value_type": "boolean",
        "category": "feature",
        "description": "文档记忆向量异步补偿开关",
    },
    {
        "config_key": "feature.enable_document_memory_admin_api",
        "config_value": "false",
        "value_type": "boolean",
        "category": "feature",
        "description": "文档记忆后台运维 API 开关",
    },
    {
        "config_key": "memory.document.hybrid.min_score",
        "config_value": "0.05",
        "value_type": "number",
        "category": "memory",
        "description": "文档记忆混合召回最低分",
    },
    {
        "config_key": "memory.document.embedding.batch_size",
        "config_value": "32",
        "value_type": "number",
        "category": "memory",
        "description": "文档记忆向量补偿批大小",
    },
    {
        "config_key": "memory.document.embedding.max_retry",
        "config_value": "3",
        "value_type": "number",
        "category": "memory",
        "description": "文档记忆向量自动重试上限",
    },
)


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


def upgrade() -> None:
    """升级：补齐文档记忆混合检索字段、索引与配置。"""

    conn = op.get_bind()
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    if _table_exists(conn, "t_user_memory_chunk"):
        if not _column_exists(conn, "t_user_memory_chunk", "embedding_status"):
            op.add_column(
                "t_user_memory_chunk",
                sa.Column(
                    "embedding_status",
                    sa.String(length=16),
                    nullable=False,
                    server_default=sa.text("'pending'"),
                ),
            )
        if not _column_exists(conn, "t_user_memory_chunk", "embedding_retry_count"):
            op.add_column(
                "t_user_memory_chunk",
                sa.Column(
                    "embedding_retry_count",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
        if not _column_exists(conn, "t_user_memory_chunk", "embedding_error"):
            op.add_column(
                "t_user_memory_chunk",
                sa.Column("embedding_error", sa.Text(), nullable=True),
            )
        if not _column_exists(conn, "t_user_memory_chunk", "embedding_updated_time"):
            op.add_column(
                "t_user_memory_chunk",
                sa.Column("embedding_updated_time", sa.DateTime(), nullable=True),
            )

        if _column_exists(conn, "t_user_memory_chunk", "embedding"):
            if _index_exists(conn, "t_user_memory_chunk", "idx_user_memory_chunk_embedding_ivfflat"):
                conn.execute(sa.text("DROP INDEX IF EXISTS idx_user_memory_chunk_embedding_ivfflat"))
            if _index_exists(conn, "t_user_memory_chunk", "idx_user_memory_chunk_embedding_hnsw"):
                conn.execute(sa.text("DROP INDEX IF EXISTS idx_user_memory_chunk_embedding_hnsw"))
            conn.execute(sa.text("UPDATE t_user_memory_chunk SET embedding = NULL WHERE embedding IS NOT NULL"))
            conn.execute(
                sa.text(
                    """
                    ALTER TABLE t_user_memory_chunk
                    ALTER COLUMN embedding TYPE vector(2048)
                    """
                )
            )

        if not _index_exists(conn, "t_user_memory_chunk", "idx_user_memory_chunk_embedding_status"):
            op.create_index(
                "idx_user_memory_chunk_embedding_status",
                "t_user_memory_chunk",
                ["user_id", "embedding_status", "update_time"],
                unique=False,
            )
        # pgvector 在当前版本下对 ivfflat/hnsw 均存在 2000 维上限，
        # 2048 维 embedding 暂不创建 ANN 索引，仅保留 user_id 过滤后的精确向量计算。

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
    """降级：移除混合检索新增字段与配置。"""

    conn = op.get_bind()

    if _table_exists(conn, "t_system_config"):
        conn.execute(
            sa.text(
                """
                DELETE FROM t_system_config
                WHERE config_key IN (
                    'feature.enable_document_memory_hybrid_search',
                    'feature.enable_document_memory_embedding_worker',
                    'feature.enable_document_memory_admin_api',
                    'memory.document.hybrid.min_score',
                    'memory.document.embedding.batch_size',
                    'memory.document.embedding.max_retry'
                )
                """
            )
        )

    if _table_exists(conn, "t_user_memory_chunk"):
        if _index_exists(conn, "t_user_memory_chunk", "idx_user_memory_chunk_embedding_hnsw"):
            conn.execute(sa.text("DROP INDEX IF EXISTS idx_user_memory_chunk_embedding_hnsw"))
        if _index_exists(conn, "t_user_memory_chunk", "idx_user_memory_chunk_embedding_ivfflat"):
            conn.execute(sa.text("DROP INDEX IF EXISTS idx_user_memory_chunk_embedding_ivfflat"))
        if _index_exists(conn, "t_user_memory_chunk", "idx_user_memory_chunk_embedding_status"):
            op.drop_index("idx_user_memory_chunk_embedding_status", table_name="t_user_memory_chunk")

        if _column_exists(conn, "t_user_memory_chunk", "embedding_updated_time"):
            op.drop_column("t_user_memory_chunk", "embedding_updated_time")
        if _column_exists(conn, "t_user_memory_chunk", "embedding_error"):
            op.drop_column("t_user_memory_chunk", "embedding_error")
        if _column_exists(conn, "t_user_memory_chunk", "embedding_retry_count"):
            op.drop_column("t_user_memory_chunk", "embedding_retry_count")
        if _column_exists(conn, "t_user_memory_chunk", "embedding_status"):
            op.drop_column("t_user_memory_chunk", "embedding_status")

        if _column_exists(conn, "t_user_memory_chunk", "embedding"):
            conn.execute(sa.text("UPDATE t_user_memory_chunk SET embedding = NULL WHERE embedding IS NOT NULL"))
            conn.execute(
                sa.text(
                    """
                    ALTER TABLE t_user_memory_chunk
                    ALTER COLUMN embedding TYPE vector(1536)
                    """
                )
            )
