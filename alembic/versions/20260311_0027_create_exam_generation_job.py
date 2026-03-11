"""创建 AI 出题任务表。

Revision ID: 20260311_0027
Revises: 20260309_0026
Create Date: 2026-03-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0027"
down_revision = "20260309_0026"
branch_labels = None
depends_on = None


TABLE = "t_exam_generation_job"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("dataset_ids", sa.JSON(), nullable=False),
        sa.Column("request_snapshot", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("asset_id", sa.BigInteger(), nullable=True),
        sa.Column("minio_object_key", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_exam_generation_job_user_created", TABLE, ["user_id", sa.text("created_at DESC")], unique=False)
    op.create_index("idx_exam_generation_job_user_status_updated", TABLE, ["user_id", "status", sa.text("updated_at DESC")], unique=False)
    op.create_index("ix_t_exam_generation_job_asset_id", TABLE, ["asset_id"], unique=False)
    op.create_index("ix_t_exam_generation_job_user_id", TABLE, ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_t_exam_generation_job_user_id", table_name=TABLE)
    op.drop_index("ix_t_exam_generation_job_asset_id", table_name=TABLE)
    op.drop_index("idx_exam_generation_job_user_status_updated", table_name=TABLE)
    op.drop_index("idx_exam_generation_job_user_created", table_name=TABLE)
    op.drop_table(TABLE)
