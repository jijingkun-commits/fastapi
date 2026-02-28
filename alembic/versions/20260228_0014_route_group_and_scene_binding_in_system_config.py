"""Persist route_group in t_llm_scene and scene-model binding in t_system_config.

Revision ID: 20260228_0014
Revises: 20260228_0013
Create Date: 2026-02-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260228_0014"
down_revision = "20260228_0013"
branch_labels = None
depends_on = None


SCENE_BINDING_PREFIX = "llm.scene_binding."

ROUTE_GROUP_DEFAULT_CHAT = "default_chat"
ROUTE_GROUP_LIGHTWEIGHT = "lightweight"
ROUTE_GROUP_SQL_GENERATION = "sql_generation"
ROUTE_GROUP_EMBEDDING = "embedding"
ROUTE_GROUP_VISION = "vision"

ROUTE_GROUP_BY_SCENE_KEY = {
    "app.ai.workflow.multi_agent_graph.create_multi_agent_graph": ROUTE_GROUP_DEFAULT_CHAT,
    "app.ai.agents.todo_agent.create_todo_agent": ROUTE_GROUP_DEFAULT_CHAT,
    "app.ai.agents.knowledge_agent.create_knowledge_agent": ROUTE_GROUP_DEFAULT_CHAT,
    "app.ai.workflow.data_graph.analyze_data_intent": ROUTE_GROUP_SQL_GENERATION,
    "app.ai.workflow.todo_graph.analyze_intent": ROUTE_GROUP_SQL_GENERATION,
    "app.ai.workflow.todo_graph._invoke_llm_for_intent": ROUTE_GROUP_SQL_GENERATION,
    "app.ai.agents.todo_enhanced_nodes.task_decomposition_node": ROUTE_GROUP_SQL_GENERATION,
    "app.ai.semantic.vanna_client.submit_prompt": ROUTE_GROUP_SQL_GENERATION,
    "app.api.v1.endpoints.data_admin_api.convert_etl_to_select": ROUTE_GROUP_SQL_GENERATION,
    "app.api.v1.endpoints.data_admin_api._batch_convert_ai_extract": ROUTE_GROUP_SQL_GENERATION,
    "app.ai.intent_classifier.classify_intent": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.parameter_extractor.extract_todo_params": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.parameter_extractor.extract_query_params": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.parameter_extractor.extract_chart_params": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.llm_judge.evaluate_response": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.llm_judge.evaluate_response_detailed": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.llm_judge.evaluate_sql_response_sync": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.llm_judge.evaluate_sql_response": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.llm_judge.evaluate_chart_response": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.utils.sql_evaluator.evaluate_sql_semantic": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.utils.sql_evaluator.should_retry_sql_generation": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.workflow.todo_graph._merge_description": ROUTE_GROUP_LIGHTWEIGHT,
    "app.ai.utils.embedding_util.get_embedding": ROUTE_GROUP_EMBEDDING,
    "app.ai.tools.vision_tool.analyze_image": ROUTE_GROUP_VISION,
}


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


def _index_exists(conn, table_name: str, index_name: str) -> bool:
    result = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE tablename = :table_name
              AND indexname = :index_name
            LIMIT 1
            """
        ),
        {"table_name": table_name, "index_name": index_name},
    ).scalar()
    return bool(result)


def upgrade() -> None:
    """Add route_group column and migrate scene->model binding to t_system_config."""

    conn = op.get_bind()

    if not _column_exists(conn, "t_llm_scene", "route_group"):
        op.add_column("t_llm_scene", sa.Column("route_group", sa.String(length=32), nullable=True))

    for scene_key, route_group in ROUTE_GROUP_BY_SCENE_KEY.items():
        conn.execute(
            sa.text(
                """
                UPDATE t_llm_scene
                SET route_group = :route_group,
                    update_time = NOW()
                WHERE scene_key = :scene_key
                """
            ),
            {"scene_key": scene_key, "route_group": route_group},
        )

    conn.execute(
        sa.text(
            """
            UPDATE t_llm_scene
            SET route_group = :fallback_group,
                update_time = NOW()
            WHERE route_group IS NULL OR route_group = ''
            """
        ),
        {"fallback_group": ROUTE_GROUP_DEFAULT_CHAT},
    )

    op.alter_column("t_llm_scene", "route_group", existing_type=sa.String(length=32), nullable=False)
    if not _index_exists(conn, "t_llm_scene", "ix_t_llm_scene_route_group"):
        op.create_index("ix_t_llm_scene_route_group", "t_llm_scene", ["route_group"], unique=False)

    # 兼容字段改为可空：运行时绑定来源改为 t_system_config。
    op.alter_column("t_llm_scene", "default_model_id", existing_type=sa.Integer(), nullable=True)

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
            SELECT
                :prefix || scene_key AS config_key,
                default_model_id::text AS config_value,
                'number' AS value_type,
                'llm_scene_binding' AS category,
                'LLM 场景绑定: ' || scene_key AS description,
                FALSE AS is_secret,
                FALSE AS is_readonly
            FROM t_llm_scene
            WHERE default_model_id IS NOT NULL
            ON CONFLICT (config_key)
            DO UPDATE SET
                config_value = EXCLUDED.config_value,
                value_type = EXCLUDED.value_type,
                category = EXCLUDED.category,
                description = EXCLUDED.description,
                update_time = NOW()
            """
        ),
        {"prefix": SCENE_BINDING_PREFIX},
    )


def downgrade() -> None:
    """Best-effort rollback for route_group and scene binding migration."""

    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DELETE FROM t_system_config
            WHERE category = 'llm_scene_binding'
               OR config_key LIKE :prefix
            """
        ),
        {"prefix": f"{SCENE_BINDING_PREFIX}%"},
    )

    if _index_exists(conn, "t_llm_scene", "ix_t_llm_scene_route_group"):
        op.drop_index("ix_t_llm_scene_route_group", table_name="t_llm_scene")

    if _column_exists(conn, "t_llm_scene", "route_group"):
        op.drop_column("t_llm_scene", "route_group")

    null_count = conn.execute(
        sa.text("SELECT COUNT(1) FROM t_llm_scene WHERE default_model_id IS NULL")
    ).scalar()
    if not null_count:
        op.alter_column("t_llm_scene", "default_model_id", existing_type=sa.Integer(), nullable=False)

