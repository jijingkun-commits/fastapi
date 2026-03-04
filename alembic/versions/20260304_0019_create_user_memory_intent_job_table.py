"""Create user memory intent job table.

Revision ID: 20260304_0019
Revises: 20260228_0018
Create Date: 2026-03-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260304_0019"
down_revision = "20260228_0018"
branch_labels = None
depends_on = None


CONFIG_ROW = {
    "config_key": "memory.intent_async_enabled",
    "config_value": "false",
    "value_type": "boolean",
    "category": "memory",
    "description": "聊天主链路记忆异步入队开关",
}


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
    """升级：创建记忆意图任务表，并补齐配置键。"""

    conn = op.get_bind()

    if not _table_exists(conn, "t_user_memory_intent_job"):
        op.create_table(
            "t_user_memory_intent_job",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
            sa.Column("source_thread_id", sa.String(length=100), nullable=True, comment="来源线程ID"),
            sa.Column("source_message_id", sa.BigInteger(), nullable=False, comment="来源消息ID"),
            sa.Column(
                "event_time",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
                comment="事件时间",
            ),
            sa.Column(
                "payload_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
                comment="任务输入载荷",
            ),
            sa.Column("dedupe_key", sa.String(length=128), nullable=False, comment="业务幂等键"),
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'pending'"),
                comment="任务状态",
            ),
            sa.Column(
                "attempt_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
                comment="已尝试次数",
            ),
            sa.Column(
                "next_retry_time",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
                comment="下次重试时间",
            ),
            sa.Column("lease_until", sa.DateTime(), nullable=True, comment="租约过期时间"),
            sa.Column("claimed_by", sa.String(length=64), nullable=True, comment="当前认领 worker"),
            sa.Column("claimed_at", sa.DateTime(), nullable=True, comment="认领时间"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="失败摘要"),
            sa.Column(
                "create_time",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
                comment="创建时间",
            ),
            sa.Column(
                "update_time",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
                comment="更新时间",
            ),
        )

    if _table_exists(conn, "t_user_memory_intent_job"):
        if not _index_exists(conn, "t_user_memory_intent_job", "idx_user_memory_intent_job_user_create"):
            op.create_index(
                "idx_user_memory_intent_job_user_create",
                "t_user_memory_intent_job",
                ["user_id", "create_time"],
                unique=False,
            )
        if not _index_exists(conn, "t_user_memory_intent_job", "idx_user_memory_intent_job_status_retry"):
            op.create_index(
                "idx_user_memory_intent_job_status_retry",
                "t_user_memory_intent_job",
                ["status", "next_retry_time", "create_time"],
                unique=False,
            )
        if not _index_exists(conn, "t_user_memory_intent_job", "idx_user_memory_intent_job_status_lease"):
            op.create_index(
                "idx_user_memory_intent_job_status_lease",
                "t_user_memory_intent_job",
                ["status", "lease_until"],
                unique=False,
            )
        if not _index_exists(conn, "t_user_memory_intent_job", "idx_user_memory_intent_job_source_unique"):
            op.create_index(
                "idx_user_memory_intent_job_source_unique",
                "t_user_memory_intent_job",
                ["user_id", "source_message_id"],
                unique=True,
            )

    if _table_exists(conn, "t_system_config"):
        conn.execute(
            sa.text(
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
            ),
            CONFIG_ROW,
        )


def downgrade() -> None:
    """降级：移除记忆意图任务表与配置键。"""

    conn = op.get_bind()

    if _table_exists(conn, "t_system_config"):
        conn.execute(
            sa.text(
                """
                DELETE FROM t_system_config
                WHERE config_key = 'memory.intent_async_enabled'
                """
            )
        )

    if _table_exists(conn, "t_user_memory_intent_job"):
        if _index_exists(conn, "t_user_memory_intent_job", "idx_user_memory_intent_job_source_unique"):
            op.drop_index("idx_user_memory_intent_job_source_unique", table_name="t_user_memory_intent_job")
        if _index_exists(conn, "t_user_memory_intent_job", "idx_user_memory_intent_job_status_lease"):
            op.drop_index("idx_user_memory_intent_job_status_lease", table_name="t_user_memory_intent_job")
        if _index_exists(conn, "t_user_memory_intent_job", "idx_user_memory_intent_job_status_retry"):
            op.drop_index("idx_user_memory_intent_job_status_retry", table_name="t_user_memory_intent_job")
        if _index_exists(conn, "t_user_memory_intent_job", "idx_user_memory_intent_job_user_create"):
            op.drop_index("idx_user_memory_intent_job_user_create", table_name="t_user_memory_intent_job")
        op.drop_table("t_user_memory_intent_job")
