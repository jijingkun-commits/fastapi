"""创建 LLM 场景治理表并初始化调用点配置。

Revision ID: 20260215_0005
Revises: 20260213_0004
Create Date: 2026-02-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260215_0005"
down_revision = "20260213_0004"
branch_labels = None
depends_on = None


ROUTE_GROUP_DEFAULT_CHAT = "default_chat"
ROUTE_GROUP_LIGHTWEIGHT = "lightweight"
ROUTE_GROUP_SQL_GENERATION = "sql_generation"


INITIAL_SCENES = (
    {
        "scene_key": "app.ai.workflow.multi_agent_graph.create_multi_agent_graph",
        "scene_name": "主对话-Supervisor",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_DEFAULT_CHAT,
        "description": "主对话总控节点",
    },
    {
        "scene_key": "app.ai.agents.todo_agent.create_todo_agent",
        "scene_name": "待办Agent工厂",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_DEFAULT_CHAT,
        "description": "待办 Agent create_agent 兼容入口",
    },
    {
        "scene_key": "app.ai.agents.knowledge_agent.create_knowledge_agent",
        "scene_name": "知识库Agent工厂",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_DEFAULT_CHAT,
        "description": "知识库 Agent 创建入口",
    },
    {
        "scene_key": "app.ai.workflow.data_graph.analyze_data_intent",
        "scene_name": "问数意图分析",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_SQL_GENERATION,
        "description": "问数复杂意图分析",
    },
    {
        "scene_key": "app.ai.workflow.todo_graph.analyze_intent",
        "scene_name": "待办意图分析",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_SQL_GENERATION,
        "description": "待办内部分析",
    },
    {
        "scene_key": "app.ai.workflow.todo_graph._invoke_llm_for_intent",
        "scene_name": "待办意图分析辅助",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_SQL_GENERATION,
        "description": "待办意图解析工具函数",
    },
    {
        "scene_key": "app.ai.agents.todo_enhanced_nodes.task_decomposition_node",
        "scene_name": "待办任务拆解",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_SQL_GENERATION,
        "description": "复合任务拆解",
    },
    {
        "scene_key": "app.ai.semantic.vanna_client.submit_prompt",
        "scene_name": "Vanna SQL 生成",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_SQL_GENERATION,
        "description": "问数 SQL 生成入口",
    },
    {
        "scene_key": "app.api.v1.endpoints.data_admin_api.convert_etl_to_select",
        "scene_name": "ETL 转换",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_SQL_GENERATION,
        "description": "管理端 ETL 转 SQL",
    },
    {
        "scene_key": "app.api.v1.endpoints.data_admin_api._batch_convert_ai_extract",
        "scene_name": "批量 ETL 转换",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_SQL_GENERATION,
        "description": "管理端批量 ETL 转 SQL",
    },
    {
        "scene_key": "app.ai.intent_classifier.classify_intent",
        "scene_name": "意图分类",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "轻量意图识别",
    },
    {
        "scene_key": "app.ai.parameter_extractor.extract_todo_params",
        "scene_name": "待办参数提取",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "待办参数提取",
    },
    {
        "scene_key": "app.ai.parameter_extractor.extract_query_params",
        "scene_name": "查询参数提取",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "问数参数提取",
    },
    {
        "scene_key": "app.ai.parameter_extractor.extract_chart_params",
        "scene_name": "图表参数提取",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "图表参数提取",
    },
    {
        "scene_key": "app.ai.llm_judge.evaluate_response",
        "scene_name": "回复评估",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "LLM Judge 质量评估",
    },
    {
        "scene_key": "app.ai.llm_judge.evaluate_response_detailed",
        "scene_name": "回复评估-详细",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "LLM Judge 详细评估",
    },
    {
        "scene_key": "app.ai.llm_judge.evaluate_sql_response_sync",
        "scene_name": "SQL 评估-同步",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "同步 SQL 评估",
    },
    {
        "scene_key": "app.ai.llm_judge.evaluate_sql_response",
        "scene_name": "SQL 评估-异步",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "异步 SQL 评估",
    },
    {
        "scene_key": "app.ai.llm_judge.evaluate_chart_response",
        "scene_name": "图表评估",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "图表代码评估",
    },
    {
        "scene_key": "app.ai.utils.sql_evaluator.evaluate_sql_semantic",
        "scene_name": "SQL 语义评估",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "SQL 语义质量评估",
    },
    {
        "scene_key": "app.ai.utils.sql_evaluator.should_retry_sql_generation",
        "scene_name": "SQL 重试判定",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "SQL 重试策略判定",
    },
    {
        "scene_key": "app.ai.workflow.todo_graph._merge_description",
        "scene_name": "待办描述融合",
        "scene_type": "text",
        "route_group": ROUTE_GROUP_LIGHTWEIGHT,
        "description": "待办描述语义融合",
    },
)


def _query_scalar(conn, sql: str, params: dict | None = None):
    result = conn.execute(sa.text(sql), params or {})
    return result.scalar()


def _resolve_model_id_by_code(conn, model_code: str | None):
    if not model_code:
        return None

    return _query_scalar(
        conn,
        """
        SELECT id
        FROM t_llm_model
        WHERE model_code = :model_code
          AND is_active = TRUE
        LIMIT 1
        """,
        {"model_code": model_code},
    )


def _resolve_default_chat_model_id(conn):
    model_id = _query_scalar(
        conn,
        """
        SELECT id
        FROM t_llm_model
        WHERE model_type = 'chat'
          AND is_default = TRUE
          AND is_active = TRUE
        ORDER BY id ASC
        LIMIT 1
        """,
    )
    if model_id:
        return model_id

    model_id = _query_scalar(
        conn,
        """
        SELECT id
        FROM t_llm_model
        WHERE model_type = 'chat'
          AND is_active = TRUE
        ORDER BY sort_order ASC, id ASC
        LIMIT 1
        """,
    )
    if model_id:
        return model_id

    return _query_scalar(
        conn,
        """
        SELECT id
        FROM t_llm_model
        WHERE is_active = TRUE
        ORDER BY sort_order ASC, id ASC
        LIMIT 1
        """,
    )


def _get_route_code(conn, key: str):
    return _query_scalar(
        conn,
        """
        SELECT config_value
        FROM t_system_config
        WHERE config_key = :key
        LIMIT 1
        """,
        {"key": key},
    )


def _resolve_route_model_ids(conn):
    default_chat_code = _get_route_code(conn, "model_routing.default_chat")
    lightweight_code = _get_route_code(conn, "model_routing.lightweight")
    sql_generation_code = _get_route_code(conn, "model_routing.sql_generation")

    default_chat_model_id = _resolve_model_id_by_code(conn, default_chat_code)
    if not default_chat_model_id:
        default_chat_model_id = _resolve_default_chat_model_id(conn)

    if not default_chat_model_id:
        raise RuntimeError("未找到可用模型，无法初始化 t_llm_scene")

    lightweight_model_id = _resolve_model_id_by_code(conn, lightweight_code) or default_chat_model_id
    sql_generation_model_id = _resolve_model_id_by_code(conn, sql_generation_code) or default_chat_model_id

    return {
        ROUTE_GROUP_DEFAULT_CHAT: default_chat_model_id,
        ROUTE_GROUP_LIGHTWEIGHT: lightweight_model_id,
        ROUTE_GROUP_SQL_GENERATION: sql_generation_model_id,
    }


def upgrade() -> None:
    """升级：创建场景治理表并初始化场景配置。"""

    op.create_table(
        "t_llm_scene",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scene_key", sa.String(length=255), nullable=False),
        sa.Column("scene_name", sa.String(length=120), nullable=False),
        sa.Column("scene_type", sa.String(length=32), nullable=False, server_default="text"),
        sa.Column("default_model_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("create_time", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.Column("update_time", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["default_model_id"], ["t_llm_model.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene_key", name="uq_t_llm_scene_scene_key"),
        sa.CheckConstraint("position('.' in scene_key) > 0", name="ck_t_llm_scene_scene_key_format"),
        sa.CheckConstraint(
            "scene_type in ('text','image','video','audio','embedding','vision','rerank','asr','tts')",
            name="ck_t_llm_scene_scene_type",
        ),
        comment="LLM 调用场景治理表",
    )

    op.create_index("ix_t_llm_scene_scene_type", "t_llm_scene", ["scene_type"], unique=False)

    conn = op.get_bind()
    model_ids = _resolve_route_model_ids(conn)

    insert_sql = sa.text(
        """
        INSERT INTO t_llm_scene (
            scene_key,
            scene_name,
            scene_type,
            default_model_id,
            description,
            is_active
        ) VALUES (
            :scene_key,
            :scene_name,
            :scene_type,
            :default_model_id,
            :description,
            TRUE
        )
        ON CONFLICT (scene_key)
        DO UPDATE SET
            scene_name = EXCLUDED.scene_name,
            scene_type = EXCLUDED.scene_type,
            default_model_id = EXCLUDED.default_model_id,
            description = EXCLUDED.description,
            is_active = TRUE,
            update_time = now()
        """
    )

    for scene in INITIAL_SCENES:
        default_model_id = model_ids[scene["route_group"]]
        conn.execute(
            insert_sql,
            {
                "scene_key": scene["scene_key"],
                "scene_name": scene["scene_name"],
                "scene_type": scene["scene_type"],
                "default_model_id": default_model_id,
                "description": scene["description"],
            },
        )


def downgrade() -> None:
    """降级：删除场景治理表。"""

    op.drop_index("ix_t_llm_scene_scene_type", table_name="t_llm_scene")
    op.drop_table("t_llm_scene")
