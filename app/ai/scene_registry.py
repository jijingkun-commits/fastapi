"""LLM 场景注册表（中文注释）。"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.llm_scene import (
    SCENE_TYPE_EMBEDDING,
    SCENE_TYPE_TEXT,
    SCENE_TYPE_VISION,
)


ROUTE_GROUP_DEFAULT_CHAT = "default_chat"
ROUTE_GROUP_LIGHTWEIGHT = "lightweight"
ROUTE_GROUP_SQL_GENERATION = "sql_generation"
ROUTE_GROUP_EMBEDDING = "embedding"
ROUTE_GROUP_VISION = "vision"


@dataclass(frozen=True)
class SceneDefinition:
    """调用点场景定义。"""

    scene_key: str
    scene_name: str
    scene_type: str
    route_group: str
    description: str


SCENE_KEY_MULTI_AGENT_SUPERVISOR = "app.ai.workflow.multi_agent_graph.create_multi_agent_graph"
SCENE_KEY_TODO_AGENT_FACTORY = "app.ai.agents.todo_agent.create_todo_agent"
SCENE_KEY_KNOWLEDGE_AGENT_FACTORY = "app.ai.agents.knowledge_agent.create_knowledge_agent"

SCENE_KEY_DATA_INTENT_ANALYSIS = "app.ai.workflow.data_graph.analyze_data_intent"
SCENE_KEY_TODO_INTENT_ANALYSIS = "app.ai.workflow.todo_graph.analyze_intent"
SCENE_KEY_TODO_INTENT_HELPER = "app.ai.workflow.todo_graph._invoke_llm_for_intent"
SCENE_KEY_TODO_TASK_DECOMPOSITION = "app.ai.agents.todo_enhanced_nodes.task_decomposition_node"
SCENE_KEY_VANNA_SQL_GENERATION = "app.ai.semantic.vanna_client.submit_prompt"
SCENE_KEY_DATA_ADMIN_ETL_CONVERT = "app.api.v1.endpoints.data_admin_api.convert_etl_to_select"
SCENE_KEY_DATA_ADMIN_BATCH_ETL_CONVERT = "app.api.v1.endpoints.data_admin_api._batch_convert_ai_extract"

SCENE_KEY_INTENT_CLASSIFIER = "app.ai.intent_classifier.classify_intent"
SCENE_KEY_PARAM_TODO = "app.ai.parameter_extractor.extract_todo_params"
SCENE_KEY_PARAM_QUERY = "app.ai.parameter_extractor.extract_query_params"
SCENE_KEY_PARAM_CHART = "app.ai.parameter_extractor.extract_chart_params"
SCENE_KEY_LLM_JUDGE_RESPONSE = "app.ai.llm_judge.evaluate_response"
SCENE_KEY_LLM_JUDGE_RESPONSE_DETAILED = "app.ai.llm_judge.evaluate_response_detailed"
SCENE_KEY_LLM_JUDGE_SQL_SYNC = "app.ai.llm_judge.evaluate_sql_response_sync"
SCENE_KEY_LLM_JUDGE_SQL_ASYNC = "app.ai.llm_judge.evaluate_sql_response"
SCENE_KEY_LLM_JUDGE_CHART = "app.ai.llm_judge.evaluate_chart_response"
SCENE_KEY_SQL_EVALUATOR_SEMANTIC = "app.ai.utils.sql_evaluator.evaluate_sql_semantic"
SCENE_KEY_SQL_EVALUATOR_RETRY = "app.ai.utils.sql_evaluator.should_retry_sql_generation"
SCENE_KEY_TODO_DESC_MERGE = "app.ai.workflow.todo_graph._merge_description"
SCENE_KEY_EMBEDDING_GENERATE = "app.ai.utils.embedding_util.get_embedding"
SCENE_KEY_VISION_ANALYZE_IMAGE = "app.ai.tools.vision_tool.analyze_image"


SCENE_DEFINITIONS = (
    SceneDefinition(
        scene_key=SCENE_KEY_MULTI_AGENT_SUPERVISOR,
        scene_name="主对话-Supervisor",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_DEFAULT_CHAT,
        description="主对话总控节点",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_TODO_AGENT_FACTORY,
        scene_name="待办Agent工厂",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_DEFAULT_CHAT,
        description="create_agent 兼容模式",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_KNOWLEDGE_AGENT_FACTORY,
        scene_name="知识库Agent工厂",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_DEFAULT_CHAT,
        description="知识库Agent创建入口",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_DATA_INTENT_ANALYSIS,
        scene_name="问数意图分析",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_SQL_GENERATION,
        description="问数复杂意图分析",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_TODO_INTENT_ANALYSIS,
        scene_name="待办意图分析",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_SQL_GENERATION,
        description="待办链路内部分析",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_TODO_INTENT_HELPER,
        scene_name="待办意图分析辅助",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_SQL_GENERATION,
        description="待办分析工具函数",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_TODO_TASK_DECOMPOSITION,
        scene_name="待办任务拆解",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_SQL_GENERATION,
        description="复合任务拆解",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_VANNA_SQL_GENERATION,
        scene_name="Vanna SQL 生成",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_SQL_GENERATION,
        description="问数 SQL 生成入口",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_DATA_ADMIN_ETL_CONVERT,
        scene_name="ETL 转换",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_SQL_GENERATION,
        description="管理端 ETL 转 SQL",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_DATA_ADMIN_BATCH_ETL_CONVERT,
        scene_name="批量 ETL 转换",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_SQL_GENERATION,
        description="管理端批量 ETL 转 SQL",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_INTENT_CLASSIFIER,
        scene_name="意图分类",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="轻量意图识别",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_PARAM_TODO,
        scene_name="待办参数提取",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="待办结构化参数提取",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_PARAM_QUERY,
        scene_name="查询参数提取",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="问数结构化参数提取",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_PARAM_CHART,
        scene_name="图表参数提取",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="图表结构化参数提取",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_LLM_JUDGE_RESPONSE,
        scene_name="回复评估",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="LLM Judge 质量评估",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_LLM_JUDGE_RESPONSE_DETAILED,
        scene_name="回复评估-详细",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="LLM Judge 详细评估",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_LLM_JUDGE_SQL_SYNC,
        scene_name="SQL 评估-同步",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="同步 SQL 结果评估",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_LLM_JUDGE_SQL_ASYNC,
        scene_name="SQL 评估-异步",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="异步 SQL 结果评估",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_LLM_JUDGE_CHART,
        scene_name="图表评估",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="图表代码评估",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_SQL_EVALUATOR_SEMANTIC,
        scene_name="SQL 语义评估",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="SQL 质量语义打分",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_SQL_EVALUATOR_RETRY,
        scene_name="SQL 重试判定",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="SQL 重试策略判定",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_TODO_DESC_MERGE,
        scene_name="待办描述融合",
        scene_type=SCENE_TYPE_TEXT,
        route_group=ROUTE_GROUP_LIGHTWEIGHT,
        description="待办描述语义融合",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_EMBEDDING_GENERATE,
        scene_name="文本向量化",
        scene_type=SCENE_TYPE_EMBEDDING,
        route_group=ROUTE_GROUP_EMBEDDING,
        description="Embedding 向量生成",
    ),
    SceneDefinition(
        scene_key=SCENE_KEY_VISION_ANALYZE_IMAGE,
        scene_name="图片理解",
        scene_type=SCENE_TYPE_VISION,
        route_group=ROUTE_GROUP_VISION,
        description="Vision 图片分析工具",
    ),
)

SCENE_DEFINITION_MAP = {item.scene_key: item for item in SCENE_DEFINITIONS}
SCENE_KEYS_BY_ROUTE_GROUP = {
    ROUTE_GROUP_DEFAULT_CHAT: tuple(
        item.scene_key for item in SCENE_DEFINITIONS if item.route_group == ROUTE_GROUP_DEFAULT_CHAT
    ),
    ROUTE_GROUP_LIGHTWEIGHT: tuple(
        item.scene_key for item in SCENE_DEFINITIONS if item.route_group == ROUTE_GROUP_LIGHTWEIGHT
    ),
    ROUTE_GROUP_SQL_GENERATION: tuple(
        item.scene_key for item in SCENE_DEFINITIONS if item.route_group == ROUTE_GROUP_SQL_GENERATION
    ),
    ROUTE_GROUP_EMBEDDING: tuple(
        item.scene_key for item in SCENE_DEFINITIONS if item.route_group == ROUTE_GROUP_EMBEDDING
    ),
    ROUTE_GROUP_VISION: tuple(
        item.scene_key for item in SCENE_DEFINITIONS if item.route_group == ROUTE_GROUP_VISION
    ),
}


def get_required_scene_keys() -> set[str]:
    """返回启动期必须存在的场景键集合。"""

    return set(SCENE_DEFINITION_MAP)


def get_scene_keys_by_route_group(route_group: str) -> tuple[str, ...]:
    """按路由分组返回场景键列表。"""

    return SCENE_KEYS_BY_ROUTE_GROUP.get(route_group, ())
