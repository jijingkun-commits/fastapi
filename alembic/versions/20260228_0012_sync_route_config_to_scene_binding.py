"""Sync legacy model_routing config into scene bindings.

Revision ID: 20260228_0012
Revises: 20260227_0011
Create Date: 2026-02-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260228_0012"
down_revision = "20260227_0011"
branch_labels = None
depends_on = None


_ROUTE_CONFIG_TO_SCENES = {
    "model_routing.default_chat": (
        "app.ai.workflow.multi_agent_graph.create_multi_agent_graph",
        "app.ai.agents.todo_agent.create_todo_agent",
        "app.ai.agents.knowledge_agent.create_knowledge_agent",
    ),
    "model_routing.lightweight": (
        "app.ai.intent_classifier.classify_intent",
        "app.ai.parameter_extractor.extract_todo_params",
        "app.ai.parameter_extractor.extract_query_params",
        "app.ai.parameter_extractor.extract_chart_params",
        "app.ai.llm_judge.evaluate_response",
        "app.ai.llm_judge.evaluate_response_detailed",
        "app.ai.llm_judge.evaluate_sql_response_sync",
        "app.ai.llm_judge.evaluate_sql_response",
        "app.ai.llm_judge.evaluate_chart_response",
        "app.ai.utils.sql_evaluator.evaluate_sql_semantic",
        "app.ai.utils.sql_evaluator.should_retry_sql_generation",
        "app.ai.workflow.todo_graph._merge_description",
    ),
    "model_routing.sql_generation": (
        "app.ai.workflow.data_graph.analyze_data_intent",
        "app.ai.workflow.todo_graph.analyze_intent",
        "app.ai.workflow.todo_graph._invoke_llm_for_intent",
        "app.ai.agents.todo_enhanced_nodes.task_decomposition_node",
        "app.ai.semantic.vanna_client.submit_prompt",
        "app.api.v1.endpoints.data_admin_api.convert_etl_to_select",
        "app.api.v1.endpoints.data_admin_api._batch_convert_ai_extract",
    ),
}


def _get_route_model_id(conn, config_key: str) -> int | None:
    model_code = conn.execute(
        sa.text(
            """
            SELECT config_value
            FROM t_system_config
            WHERE config_key = :config_key
            LIMIT 1
            """
        ),
        {"config_key": config_key},
    ).scalar()
    if not model_code:
        return None

    return conn.execute(
        sa.text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_code = :model_code
              AND is_active = TRUE
            LIMIT 1
            """
        ),
        {"model_code": model_code},
    ).scalar()


def upgrade() -> None:
    """Backfill route-group scene bindings from legacy routing config."""

    conn = op.get_bind()
    for config_key, scene_keys in _ROUTE_CONFIG_TO_SCENES.items():
        model_id = _get_route_model_id(conn, config_key)
        if not model_id:
            continue

        for scene_key in scene_keys:
            conn.execute(
                sa.text(
                    """
                    UPDATE t_llm_scene
                    SET default_model_id = :model_id,
                        update_time = NOW()
                    WHERE scene_key = :scene_key
                    """
                ),
                {
                    "model_id": model_id,
                    "scene_key": scene_key,
                },
            )


def downgrade() -> None:
    """No-op: data backfill is irreversible by design."""

