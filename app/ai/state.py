"""Agent 状态定义模块（中文注释）。

本模块统一定义各类 Agent 使用的状态类型。

设计原则：
1. 使用 TypedDict 保持 LangGraph 兼容性
2. 公共字段在 BaseAgentState 中定义
3. MultiAgentState 和 TodoAgentState 通过继承扩展
"""
from typing import TypedDict, Optional, Annotated, Sequence, List, Dict, Literal, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentType:
    """专家 Agent 类型枚举。"""
    DATA = "data_expert"
    TODO = "todo_expert"


# Agent 描述映射（用于 Supervisor 决策）
AGENT_DESCRIPTIONS = {
    AgentType.DATA: """将复杂的多步骤数据分析任务分配给数据专家。

**委派给 data_expert 的场景**（需要多个工具配合）：
- 读取 Excel/CSV 文件并进行多维度分析
- 数据清洗 + 统计分析 + 可视化
- 需要 Python 代码进行复杂计算

**不需要委派的简单任务**（你可以直接处理）：
- 简单绘图 → 直接用 fig_inter
- 知识库搜索 → 直接用 knowledge_search

**必须委派的任务**：
- 所有 SQL 查询 → 必须委派给 data_expert
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
    """基础 Agent 状态 - 所有 Agent 共享的字段。
    
    使用 total=False 允许所有字段可选。
    """
    # 核心字段
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: int
    thread_id: str
    current_todo_id: int            # 前端选中待办锚点（可选，供 supervisor/todo 共享）
    pending_handoff: Dict           # 当前轮 Supervisor 委派上下文（含 frame/tool_observations，供专家子图消费）
    
    # 模型配置（由 chat_service 注入，所有节点可读取）
    enable_thinking: bool          # 是否启用深度思考模式
    model_id: str                  # 用户选择的模型标识
    
    # TodoExpert 共享状态（多轮对话支持）
    pending_operation: Dict       # 待确认的操作
    user_confirmed: bool          # 用户确认状态
    quick_mode: bool              # 快速模式(跳过确认)
    conversation_context: Dict    # 当前讨论的上下文
    active_projects: List[str]    # 正在讨论的项目列表
    current_focus: str            # 当前焦点任务
    pending_clarifications: List[str]  # 待澄清的问题
    detected_conflicts: List[Dict]     # 检测到的冲突
    time_constraints: Dict             # 时间约束

    # 会话意图内核（跨 data/todo 复用）
    session_frame: Dict                # 统一会话帧（槽位真值）
    turn_act: Literal["NEW_QUERY", "SUPPLEMENT", "CORRECTION", "CONFIRM", "UNKNOWN"]
    clarify_fsm_state: str             # 澄清状态机状态
    clarify_round: int                 # 当前任务澄清轮次
    frame_source_map: Dict             # 槽位来源（current/handoff/state/default）


class MultiAgentState(BaseAgentState, total=False):
    """多智能体 Supervisor 状态定义。
    
    继承 BaseAgentState，扩展以下字段：
    - 运行时状态（附件分析、评估、迭代计数）
    - 意图识别（detected_intent, intent_route）
    """
    # 运行时状态（enable_thinking / model_id 已提升至 BaseAgentState）
    attachment_analysis: str       # 附件分析结果（由 preprocess 节点填充）
    evaluation: str                # 专家工作评估结果（由 evaluate 节点填充）
    iteration_count: int           # 当前迭代次数（防止无限循环）
    thinking_content: str          # 深度思考内容
    
    # Graph 类型标记
    _graph_type: Literal["multi_agent"]
    
    # 意图识别（借鉴 Flock Intent Recognition）
    detected_intent: str
    intent_route: str
    
    # Skills RAG
    skill_context: str            # 检索到的相关技能上下文（由 preprocess 节点填充）
    
    # 系统上下文
    system_context: str           # 系统级上下文信息（当前时间、用户信息等）


class TodoAgentState(BaseAgentState, total=False):
    """待办 Agent 状态 - 多轮对话增强版。
    
    继承 BaseAgentState，扩展以下字段：
    - 任务池（draft_todos）
    - 项目队列（project_queue, current_project_index）
    - 提取信息（extracted_info）
    """
    # 任务池
    draft_todos: List[Dict]            # 草稿待办(未确认)
    
    # 项目队列(逐项目追问)
    project_queue: List[str]           # 待处理项目队列
    current_project_index: int         # 当前处理的项目索引
    
    # 提取信息(保留用于向后兼容)
    extracted_info: Dict


class DataAgentState(BaseAgentState, total=False):
    """问数 Agent 状态定义。
    
    继承 BaseAgentState，扩展以下字段：
    - 查询上下文（query_context, time_range, filters）
    - SQL 生成（generated_sql, sql_source, sql_approved）
    - 指标匹配（matched_metric, metric_params）
    - 可视化（viz_type, viz_data）
    - 错误恢复（iterations, last_error, sql_history）
    """
    # 查询上下文
    query_context: Dict                # 当前查询的完整上下文
    retrieved_schema: List[Dict]       # 检索到的相关表结构
    target_schema: str                 # 目标 Schema（由 schema 路由确定）
    time_range: str                    # 时间范围（如 "本月", "过去7天"）
    filters: List[str]                 # 筛选条件列表
    dimensions: List[str]              # 聚合维度列表
    
    # 指标匹配
    matched_metric: str                # 匹配到的指标名称（如 "total_gmv"）
    metric_params: Dict                # 指标参数（维度、筛选等）
    
    # SQL 生成
    generated_sql: str                 # 生成的 SQL 语句
    sql_source: Literal["metric", "training", "vanna", "template", "vanna_rag"]  # SQL 来源
    sql_result: Any                    # SQL 执行结果
    pending_sql: str                   # 待审核的 SQL（需用户确认时）
    sql_approved: bool                 # SQL 是否已批准
    
    # 可视化
    viz_type: str                      # 图表类型（pie, bar, line 等）
    viz_data: Dict                     # 图表数据
    
    # 意图分类
    data_intent: Literal["metric_query", "free_query", "visualization", "clarification"]
    clarification_needed: str          # 需要用户澄清的内容

    # 澄清控制（多轮补充与重复澄清保护）
    last_clarify_slot: str             # 上一次澄清槽位（metric/time_range/display_mode/org_level）
    clarify_count: int                 # 当前任务内已澄清次数
    continuation_mode: bool            # 当前轮是否识别为补充型短回复
    
    # 错误恢复（自愈机制）
    iterations: int                    # 当前迭代次数（用于限制重试）
    last_error: str                    # 最后一次执行错误信息
    sql_history: List[Dict]            # SQL 生成历史 [{"sql": str, "error": str}]

    # 执行状态（用于路由/自愈）
    execution_success: bool            # SQL 执行是否成功（route_after_execute 依赖）
    fallback_target: str               # 空结果降级目标: "training"(→训练集) / "schema"(→通用RAG) / None
