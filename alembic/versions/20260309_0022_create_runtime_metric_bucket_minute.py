"""创建总览分钟桶事实源表。

Revision ID: 20260309_0022
Revises: 20260307_0021
Create Date: 2026-03-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260309_0022"
down_revision = "20260307_0021"
branch_labels = None
depends_on = None


TABLE = "t_runtime_metric_bucket_minute"
IDX_SCOPE_BUCKET = "ix_runtime_metric_bucket_minute_scope_bucket"
IDX_MODULE_BUCKET = "ix_runtime_metric_bucket_minute_module_bucket"
IDX_LAST_EVENT = "ix_runtime_metric_bucket_minute_last_event_at"


def _table_exists() -> bool | None:
    if not hasattr(op, "get_context") or not hasattr(op, "get_bind"):
        return None
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return False
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(TABLE)


def _existing_indexes() -> set[str] | None:
    if not hasattr(op, "get_context") or not hasattr(op, "get_bind"):
        return None
    context = op.get_context()
    if bool(getattr(context, "as_sql", False)):
        return set()
    inspector = sa.inspect(op.get_bind())
    return {index["name"] for index in inspector.get_indexes(TABLE)}


def upgrade() -> None:
    """升级：创建总览分钟桶事实源表。"""

    table_exists = _table_exists()
    if table_exists is not True:
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("bucket_minute", sa.DateTime(timezone=True), nullable=False),
            sa.Column("scope", sa.String(length=32), nullable=False),
            sa.Column("module_key", sa.String(length=64), nullable=False),
            sa.Column("request_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("success_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("error_4xx_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("error_5xx_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column(
                "latency_histogram",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("cost_total", sa.Numeric(precision=12, scale=4), nullable=False, server_default=sa.text("0")),
            sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.CheckConstraint(
                "request_count >= 0",
                name="ck_runtime_metric_bucket_minute_request_count_non_negative",
            ),
            sa.CheckConstraint(
                "success_count >= 0",
                name="ck_runtime_metric_bucket_minute_success_count_non_negative",
            ),
            sa.CheckConstraint(
                "error_4xx_count >= 0",
                name="ck_runtime_metric_bucket_minute_error_4xx_count_non_negative",
            ),
            sa.CheckConstraint(
                "error_5xx_count >= 0",
                name="ck_runtime_metric_bucket_minute_error_5xx_count_non_negative",
            ),
            sa.CheckConstraint(
                "cost_total >= 0",
                name="ck_runtime_metric_bucket_minute_cost_total_non_negative",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "bucket_minute",
                "scope",
                "module_key",
                name="uq_runtime_metric_bucket_minute_bucket_scope_module",
            ),
            comment="管理后台总览分钟桶事实源",
        )

    existing_indexes = _existing_indexes() or set()
    if IDX_SCOPE_BUCKET not in existing_indexes:
        op.create_index(IDX_SCOPE_BUCKET, TABLE, ["scope", "bucket_minute"], unique=False)
    if IDX_MODULE_BUCKET not in existing_indexes:
        op.create_index(IDX_MODULE_BUCKET, TABLE, ["module_key", "bucket_minute"], unique=False)
    if IDX_LAST_EVENT not in existing_indexes:
        op.create_index(IDX_LAST_EVENT, TABLE, ["last_event_at"], unique=False)


def downgrade() -> None:
    """降级：删除总览分钟桶事实源表。"""

    table_exists = _table_exists()
    if table_exists is False:
        return

    existing_indexes = _existing_indexes() or {IDX_LAST_EVENT, IDX_MODULE_BUCKET, IDX_SCOPE_BUCKET}
    if IDX_LAST_EVENT in existing_indexes:
        op.drop_index(IDX_LAST_EVENT, table_name=TABLE)
    if IDX_MODULE_BUCKET in existing_indexes:
        op.drop_index(IDX_MODULE_BUCKET, table_name=TABLE)
    if IDX_SCOPE_BUCKET in existing_indexes:
        op.drop_index(IDX_SCOPE_BUCKET, table_name=TABLE)
    op.drop_table(TABLE)
