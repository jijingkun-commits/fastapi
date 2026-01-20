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
- 简单 SQL 查询 → 直接用 sql_inter
- 简单绘图 → 直接用 fig_inter
- 知识库搜索 → 直接用 knowledge_search
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


class MultiAgentState(BaseAgentState, total=False):
    """多智能体 Supervisor 状态定义。
    
    继承 BaseAgentState，扩展以下字段：
    - 运行时状态（附件分析、评估、迭代计数）
    - 意图识别（detected_intent, intent_route）
    - 委派控制（pending_handoff）
    """
    # 运行时状态
    enable_thinking: bool          # 是否启用深度思考模式
    model_id: str                  # 模型标识
    attachment_analysis: str       # 附件分析结果（由 preprocess 节点填充）
    evaluation: str                # 专家工作评估结果（由 evaluate 节点填充）
    iteration_count: int           # 当前迭代次数（防止无限循环）
    thinking_content: str          # 深度思考内容
    
    # Graph 类型标记
    _graph_type: Literal["multi_agent"]
    
    # 意图识别（借鉴 Flock Intent Recognition）
    detected_intent: str
    intent_route: str
    
    # 委派控制
    pending_handoff: Dict         # 待处理的委派指令（由 handoff 工具返回值解析）


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
