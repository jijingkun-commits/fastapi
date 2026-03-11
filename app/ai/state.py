"""Agent 状态定义。"""
from typing import Any, Annotated, Dict, List, Literal, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentType:

    DATA = "data_expert"
    TODO = "todo_expert"


AGENT_DESCRIPTIONS = {
    AgentType.DATA: """将复杂的多步骤数据分析任务分配给数据专家。

**委派给 data_expert 的场景**（需要多个工具配合）：
- 读取 Excel/CSV 文件并进行多维度分析
- 数据清洗 + 统计分析 + 可视化
- 需要 Python 代码进行复杂计算

**不需要委派的简单任务**（你可以直接处理）：
- 简单绘图 → 直接用 fig_inter
- 知识库搜索 → 先 load_skills 对应 skill，再用已授权工具

**必须委派的任务**：
- 所有 SQL 查询 → 先 load_skills 加载数据相关 skill，再委派给 data_expert
""",
    AgentType.TODO: """将待办事项管理任务分配给待办助手。

**适用场景**:
- 查询/列出待办: "列出我的待办"、"查看工作类待办"
- 创建待办: "帮我记录一个待办"、"明天10点开会"
- 更新/完成/删除: "完成待办1"、"删除第3个任务"

**重要**: 待办管理需要确认流程，必须委派给 todo_expert。
""",
}


class BaseAgentState(TypedDict, total=False):

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: int
    thread_id: str
    enable_thinking: bool
    model_id: str


class TodoAnchorState(TypedDict, total=False):

    current_todo_id: int


class RoutingTransientState(TypedDict, total=False):

    pending_handoff: Dict
    handoff_queue: List[Dict]
    completed_handoffs: List[Dict]
    handoff_execution_trace: List[Dict]
    multi_intent_mode: bool


class SupervisorConversationState(TypedDict, total=False):

    session_frame: Dict
    turn_act: Literal["NEW_QUERY", "SUPPLEMENT", "CORRECTION", "CONFIRM", "UNKNOWN"]
    clarify_fsm_state: str
    clarify_round: int
    frame_source_map: Dict


class TodoWorkflowState(TypedDict, total=False):

    pending_operation: Dict
    user_confirmed: bool
    quick_mode: bool
    conversation_context: Dict
    active_projects: List[str]
    current_focus: str
    pending_clarifications: List[str]
    response_message: str
    detected_conflicts: List[Dict]
    time_constraints: Dict
    draft_todos: List[Dict]
    project_queue: List[str]
    current_project_index: int
    extracted_info: Dict


class DataWorkflowState(TypedDict, total=False):

    query_context: Dict
    retrieved_schema: List[Dict]
    target_schema: str
    time_range: str
    filters: List[str]
    dimensions: List[str]
    matched_metric: str
    metric_params: Dict
    generated_sql: str
    sql_source: Literal["metric", "training", "vanna", "template", "vanna_rag"]
    sql_result: Any
    pending_sql: str
    sql_approved: bool
    viz_type: str
    viz_data: Dict
    data_intent: Literal["metric_query", "free_query", "visualization", "clarification"]
    clarification_needed: str
    last_clarify_slot: str
    clarify_count: int
    continuation_mode: bool
    iterations: int
    last_error: str
    sql_history: List[Dict]
    execution_success: bool
    fallback_target: str


class RuntimeRecoveryState(TypedDict, total=False):

    recovery_metrics: Dict[str, Any]
    fallback_route: str
    plugin_lifecycle_status: str


class ResponseGuidanceContract(TypedDict, total=False):

    kind: Literal["memory_archive"]
    status: Literal["persisted", "already_absent"]
    target_slot_key: str
    target_canonical_text: str
    followup_behavior: Literal["reuse_resolved_target"]


class MultiAgentState(
    BaseAgentState,
    TodoAnchorState,
    RoutingTransientState,
    SupervisorConversationState,
    total=False,
):

    attachment_manifest: List[Dict[str, Any]]
    lightweight_probe: List[Dict[str, Any]]
    attachment_planning: Dict[str, Any]
    evaluation: str
    evaluation_route: str
    iteration_count: int
    thinking_content: str
    _graph_type: Literal["multi_agent"]
    detected_intent: str
    intent_route: str
    intent_mode: Literal["model_primary", "heuristic_only"]
    skill_context: str
    skill_catalog_manifest: List[Dict[str, Any]]
    skill_catalog_context: str
    loaded_skill_registry: Dict[str, Dict[str, Any]]
    loaded_skill_context: str
    allowed_tool_registry: Dict[str, Dict[str, Any]]
    catalog_version: str
    visible_skill_count: int
    system_context: str
    memory_context: str
    response_guidance_contract: ResponseGuidanceContract
    runtime_recovery_state: RuntimeRecoveryState
    turn_id: str
    decomposed_goals: List[Dict[str, Any]]
    task_graph: Dict[str, Any]
    task_runs: List[Dict[str, Any]]
    deliverables: List[Dict[str, Any]]
    coverage_report: Dict[str, Any]
    final_answer: str
    delivery_meta: Dict[str, Any]
    coverage_retry_count: int
    coverage_gate_route: str
    coverage_partial_gap_allowed: bool
    router_result_v2: Dict[str, Any]


class TodoAgentState(
    BaseAgentState,
    TodoAnchorState,
    RoutingTransientState,
    SupervisorConversationState,
    TodoWorkflowState,
    total=False,
):
    pass


class DataAgentState(
    BaseAgentState,
    RoutingTransientState,
    SupervisorConversationState,
    DataWorkflowState,
    total=False,
):
    pass
