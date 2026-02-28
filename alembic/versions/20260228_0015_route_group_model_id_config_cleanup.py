"""Use route-group model_id config and remove per-scene binding configs.

Revision ID: 20260228_0015
Revises: 20260228_0014
Create Date: 2026-02-28
"""

from __future__ import annotations

from collections import Counter

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260228_0015"
down_revision = "20260228_0014"
branch_labels = None
depends_on = None


SCENE_BINDING_PREFIX = "llm.scene_binding."

ROUTE_GROUP_DEFAULT_CHAT = "default_chat"
ROUTE_GROUP_LIGHTWEIGHT = "lightweight"
ROUTE_GROUP_SQL_GENERATION = "sql_generation"
ROUTE_GROUP_EMBEDDING = "embedding"
ROUTE_GROUP_VISION = "vision"

ROUTE_GROUP_CONFIG_KEY = {
    ROUTE_GROUP_DEFAULT_CHAT: "model_routing.default_chat",
    ROUTE_GROUP_LIGHTWEIGHT: "model_routing.lightweight",
    ROUTE_GROUP_SQL_GENERATION: "model_routing.sql_generation",
    ROUTE_GROUP_EMBEDDING: "embedding",
    ROUTE_GROUP_VISION: "vision",
}

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


def _resolve_model_id_by_code(conn, model_code: str | None) -> int | None:
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


def _resolve_default_model_id_by_type(conn, model_type: str) -> int | None:
    model_id = conn.execute(
        sa.text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_type = :model_type
              AND is_default = TRUE
              AND is_active = TRUE
            ORDER BY id ASC
            LIMIT 1
            """
        ),
        {"model_type": model_type},
    ).scalar()
    if model_id:
        return model_id

    return conn.execute(
        sa.text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_type = :model_type
              AND is_active = TRUE
            ORDER BY sort_order ASC, id ASC
            LIMIT 1
            """
        ),
        {"model_type": model_type},
    ).scalar()


def _resolve_model_id_from_config_value(conn, config_key: str) -> int | None:
    raw_value = conn.execute(
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
    if raw_value is None:
        return None

    normalized = str(raw_value).strip()
    if not normalized:
        return None

    if normalized.isdigit():
        model_id = int(normalized)
        exists = conn.execute(
            sa.text(
                """
                SELECT 1
                FROM t_llm_model
                WHERE id = :model_id
                  AND is_active = TRUE
                LIMIT 1
                """
            ),
            {"model_id": model_id},
        ).scalar()
        return model_id if exists else None

    return _resolve_model_id_by_code(conn, normalized)


def _resolve_majority_from_scene_binding(conn, route_group: str) -> int | None:
    scene_keys = [
        scene_key
        for scene_key, group in ROUTE_GROUP_BY_SCENE_KEY.items()
        if group == route_group
    ]
    if not scene_keys:
        return None

    values = []
    for scene_key in scene_keys:
        raw_value = conn.execute(
            sa.text(
                """
                SELECT config_value
                FROM t_system_config
                WHERE config_key = :config_key
                LIMIT 1
                """
            ),
            {"config_key": f"{SCENE_BINDING_PREFIX}{scene_key}"},
        ).scalar()
        if raw_value is None:
            continue

        normalized = str(raw_value).strip()
        if not normalized or not normalized.isdigit():
            continue

        model_id = int(normalized)
        exists = conn.execute(
            sa.text(
                """
                SELECT 1
                FROM t_llm_model
                WHERE id = :model_id
                  AND is_active = TRUE
                LIMIT 1
                """
            ),
            {"model_id": model_id},
        ).scalar()
        if exists:
            values.append(model_id)

    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _resolve_majority_from_scene_table(conn, route_group: str) -> int | None:
    rows = conn.execute(
        sa.text(
            """
            SELECT default_model_id
            FROM t_llm_scene
            WHERE route_group = :route_group
              AND default_model_id IS NOT NULL
            """
        ),
        {"route_group": route_group},
    ).fetchall()
    values = []
    for row in rows:
        model_id = int(row[0])
        exists = conn.execute(
            sa.text(
                """
                SELECT 1
                FROM t_llm_model
                WHERE id = :model_id
                  AND is_active = TRUE
                LIMIT 1
                """
            ),
            {"model_id": model_id},
        ).scalar()
        if exists:
            values.append(model_id)
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _resolve_fallback_model_id(conn, route_group: str) -> int | None:
    if route_group == ROUTE_GROUP_EMBEDDING:
        return _resolve_default_model_id_by_type(conn, "embedding")
    if route_group == ROUTE_GROUP_VISION:
        return (
            _resolve_default_model_id_by_type(conn, "vision")
            or _resolve_default_model_id_by_type(conn, "chat")
            or _resolve_default_model_id_by_type(conn, "reasoning")
        )
    return _resolve_default_model_id_by_type(conn, "chat")


def upgrade() -> None:
    """Normalize routing config to route_group -> model_id and remove scene bindings."""

    conn = op.get_bind()

    # 纠正/补齐 route_group
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

    for route_group, config_key in ROUTE_GROUP_CONFIG_KEY.items():
        model_id = _resolve_model_id_from_config_value(conn, config_key)
        if not model_id:
            model_id = _resolve_majority_from_scene_binding(conn, route_group)
        if not model_id:
            model_id = _resolve_majority_from_scene_table(conn, route_group)
        if not model_id:
            model_id = _resolve_fallback_model_id(conn, route_group)

        if not model_id:
            raise RuntimeError(f"未找到可用模型，无法初始化路由分组: {route_group}")

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
                ) VALUES (
                    :config_key,
                    :config_value,
                    'number',
                    'model_routing',
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
                    update_time = NOW()
                """
            ),
            {
                "config_key": config_key,
                "config_value": str(model_id),
                "description": f"模型路由分组绑定: {route_group}",
            },
        )

    # 清理旧的 per-scene 绑定配置
    conn.execute(
        sa.text(
            """
            DELETE FROM t_system_config
            WHERE config_key LIKE :prefix
               OR category = 'llm_scene_binding'
            """
        ),
        {"prefix": f"{SCENE_BINDING_PREFIX}%"},
    )


def downgrade() -> None:
    """No-op downgrade for data migration."""

