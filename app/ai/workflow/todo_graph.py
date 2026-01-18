"""LangGraph 待办 Agent - 多轮对话增强版（中文注释）。

支持:
- 主动澄清追问
- 任务拆解
- 冲突检测
- 优先级动态调整
"""
import logging
import json
from typing import TypedDict, Optional, Dict, List, Annotated, Literal, Union
from datetime import datetime

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from app.ai.llm_util import get_llm
from app.db.session import get_db_context  # 数据库上下文管理器
from app.repositories.todo_repository import TodoRepository  # 待办仓库
from app.core.types import ToolResult, ToolResultBuilder  # 统一类型

# 🆕 导入自定义事件工具
from langgraph.config import get_stream_writer
from app.ai.events import emit_result, emit_token, emit_status, emit_error

# 创建仓库实例
todo_repo = TodoRepository()


logger = logging.getLogger(__name__)


# ==================== 状态定义 ====================

class TodoAgentState(TypedDict):
    """待办 Agent 状态 - 多轮对话增强版。"""
    # === 基础字段 ===
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: Optional[int]  # 🔧 新增：用户 ID（与 MultiAgentState 一致）
    thread_id: Optional[str]  # 🔧 新增：对话线程 ID
    pending_operation: Optional[Dict]  # 待确认的操作
    user_confirmed: Optional[bool]     # 用户确认状态
    quick_mode: Optional[bool]         # 快速模式(跳过确认)
    
    # === 🆕 对话管理 ===
    conversation_context: Optional[Dict]  # 当前讨论的上下文
    active_projects: Optional[List[str]]  # 正在讨论的项目列表
    current_focus: Optional[str]          # 当前焦点任务
    
    # === 🆕 任务池 ===
    draft_todos: Optional[List[Dict]]           # 草稿待办(未确认)
    pending_clarifications: Optional[List[str]] # 待澄清的问题
    
    # === 🆕 冲突与约束 ===
    detected_conflicts: Optional[List[Dict]]  # 检测到的冲突
    time_constraints: Optional[Dict]          # 时间约束(会议、不可用时段)
    
    # === 🆕 提取信息(保留用于向后兼容) ===
    extracted_info: Optional[Dict]
    
    # === 🆕 P3: 项目队列(逐项目追问) ===
    project_queue: Optional[List[str]]       # 待处理项目队列
    current_project_index: Optional[int]     # 当前处理的项目索引


# 注意：OperationResult 已废弃，统一使用 ToolResult (从 app.core.types 导入)


# ==================== 系统提示词 ====================

ANALYZE_PROMPT = """你是待办管理助手的意图分析模块。

## 任务
分析用户消息,判断意图并提取信息。支持多轮对话和复杂场景。

## 意图分类 (11种)

### 1. clarify (需要澄清) - **新增优先级**
**触发条件**:
- 模糊/高层级: "帮我理一理", "太多了", "有几个项目"
- 缺少关键信息: 无具体任务、时间、范围
- 隐含需求: "领导要听汇报" (需准备材料但未明确)

**输出**:
```json
{
  "intent": "clarify",
  "needs_clarification": true,
  "missing_info": ["具体任务", "时间范围"],
  "context_hints": {"mentioned": ["项目", "汇报"]},
  "projects": ["预售资金系统", "AI中台"]
}
```
**注意**: 如果用户提到了多个项目名称，必须在 `projects` 数组中列出。


### 2. query (查询)
**关键词**: 列出、查看、显示、有哪些
**示例**: "列出上海的待办" → query, keyword="上海"

### 3. create (创建)
**关键词**: 创建、添加、记录、明天、下周
**复杂任务标记**:
```json
{
  "intent": "create",
  "is_complex": true,
  "subtask_hints": ["系统架构", "信创适配"],
  "dependencies": ["等待商务方案"]
}
```

### 4. update (更新)
**关键词**: 修改、改成、延后、推迟
**冲突标记**:
```json
{
  "intent": "update",
  "conflict_risk": "high",
  "conflicts": ["延期但有催办"]
}
```

### 5. complete (完成)
**关键词**: 完成、做完了

### 6. delete (删除)
**关键词**: 删除、取消

### 7. batch_create (批量创建) - **新增**
**触发条件**: 一次性提到多个待办
**示例**: 
- "明天去上海,后天去北京"
- "这周要开会、写报告、做测试"

**输出**:
```json
{
  "intent": "batch_create",
  "extracted_info": {
    "todos": [
      {"title": "去上海", "time": "明天", "location": "上海"},
      {"title": "去北京", "time": "后天", "location": "北京"}
    ]
  }
}
```
**注意**: extracted_info 支持以下字段:
- title: 待办标题
- time/due_date: 截止时间
- location: 地点/位置
- priority: 优先级 (1=高, 2=中, 3=低)
- description: 详细描述
- category: 分类

### 8. batch_complete (批量完成)
**关键词**: 批量、全部完成

### 9. merge (合并) - **新增**
**关键词**: 合并、结合、一起做
**示例**: "路线图跟说明能不能合并?"
**输出**:
```json
{
  "intent": "merge",
  "extracted_info": {
    "target_tasks": ["路线图", "说明"],
    "merge_strategy": "combine_description"
  }
}
```

### 10. priority_adjust (优先级调整) - **新增**
**触发**: 插入紧急任务、"刚刚领导说"
**示例**: "刚收到消息,明天急需..."

### 11. context_switch (上下文切换) - **新增**
**触发**: "对了"、"还有"、从一个项目切换到另一个
**示例**: "对了,人力系统那个..."

### 12. confirm (用户确认) - **重要**
**触发条件**: 当系统之前展示了待办信息并询问确认时，用户回复确认
**关键词**: 好的、确认、可以、没问题、就这样、创建吧、对

### 13. chat (闲聊)
非待办相关

### 14. constraint (约束声明) - **新增**
**触发**: 提到不可用时间、外部依赖、强制死线
**示例**: 
- "周一我全天开会"
- "必须等商务部给方案"
**输出**:
```json
{
  "intent": "constraint",
  "extracted_info": {
    "constraints": {
        "monday_unavailable": true,
        "external_dependency": "商务部方案"
    }
  }
}
```

### 15. summarize (汇总请求) - **新增**
**触发**: 用户请求查看待办清单或汇总
**关键词**: 清单、列表、按优先级、汇总、给我看看、总结一下
**示例**: 
- "按优先级给我待办清单"
- "可以，给我看看"
- "汇总一下"
**输出**:
```json
{
  "intent": "summarize"
}
```

## 🧠 隐含需求推理 (Phase 4)
当用户提到以下业务关键词时,主动追问相关准备工作:

| 关键词 | 隐含需求 | 建议追问 |
|--------|----------|---------|
| 汇报/汇报会 | PPT、数据、会议材料 | "需要准备PPT或会议材料吗?" |
| 投标/招标 | 技术方案、报价、资质文件 | "是否需要准备技术方案或报价?" |
| 评审/审核 | 文档、测试报告、演示 | "需要准备评审文档吗?" |
| 培训/讲课 | 课件、演示环境 | "需要准备培训材料吗?" |
| 发布/上线 | 测试、文档、回滚方案 | "发布前需要哪些准备工作?" |

**识别逻辑**:
1. 检测用户消息中的业务关键词
2. 如果发现关键词,在 `missing_info` 中添加相关建议
3. 在 `context_hints` 中标记检测到的业务场景

**示例**:
用户: "领导下周要听项目汇报"
```json
{
  "intent": "clarify",
  "needs_clarification": true,
  "missing_info": ["汇报时间", "需要准备PPT或会议材料吗?"],
  "context_hints": {"business_type": "汇报", "implied_tasks": ["准备PPT", "整理数据"]}
}
```

## 判断规则 ⚠️
1. 输入模糊/缺信息 → **clarify (最优先)**
2. 检测到业务关键词 → **clarify** (触发隐含需求推理)
3. "周一不可用/必须等" → **constraint** (提取约束)
4. "列出/查看" → query
5. "合并/结合" → merge
6. "刚刚/紧急" → priority_adjust
7. "对了/还有" → context_switch
8. "清单/列表/汇总/按优先级" → **summarize** (汇总输出)
9. 明确动作+时间 → create

## 输出格式
必须返回JSON:
```json
{
  "intent": "clarify",
  "needs_confirmation": false,
  "extracted_info": {},
  "is_complex": false,
  "conflict_risk": "none",
  "time_constraints": {} 
}
```

只返回JSON,不要其他内容。
"""


# ==================== 辅助函数 ====================

# 注释: _needs_create_confirmation 函数已废弃
# 当前策略: 所有创建操作都需要确认(除非quick_mode)
# 如需恢复智能确认,可以取消注释以下代码

# def _needs_create_confirmation(extracted_info: Dict) -> bool:
#     """判断创建操作是否需要确认。
#     
#     规则:
#     - 如果标题明确 → 无需确认
#     - 如果标题缺失或模糊 → 需要确认
#     """
#     title = extracted_info.get("title", "").strip()
#     
#     # 标题为空或过短
#     if not title or len(title) < 2:
#         return True
#     
#     # 标题过于模糊
#     vague_keywords = ["这个", "那个", "它", "东西", "事情"]
#     if any(keyword in title for keyword in vague_keywords):
#         return True
#     
#     # 信息完整,无需确认
#     return False


# ==================== 辅助函数 ====================

def _recover_todo_from_messages(messages: list) -> Optional[Dict]:
    """从消息历史中恢复待办上下文。
    
    解析 AI 之前给出的待办信息（标题、时间、地点等）。
    
    Returns:
        提取的待办信息字典，如果无法恢复则返回 None
    """
    import re
    
    for msg in reversed(messages):
        if not hasattr(msg, 'type') or msg.type != 'ai':
            continue
        
        content = str(getattr(msg, 'content', ''))
        if not content or '待办信息' not in content:
            continue
        
        # 解析待办信息
        recovered = {}
        
        # 标题
        title_match = re.search(r'标题[：:]\s*(.+?)(?:\n|$)', content)
        if title_match:
            recovered['title'] = title_match.group(1).strip()
        
        # 时间
        time_match = re.search(r'时间[：:]\s*(.+?)(?:\n|$)', content)
        if time_match:
            recovered['time'] = time_match.group(1).strip()
        
        # 地点
        location_match = re.search(r'地点[：:]\s*(.+?)(?:\n|$)', content)
        if location_match:
            recovered['location'] = location_match.group(1).strip()
        
        # 优先级
        priority_match = re.search(r'优先级[：:]\s*(.+?)(?:\n|$)', content)
        if priority_match:
            priority_text = priority_match.group(1).strip()
            if '高' in priority_text:
                recovered['priority'] = 1
            elif '低' in priority_text:
                recovered['priority'] = 3
            else:
                recovered['priority'] = 2
        
        if recovered.get('title'):
            logger.info(f"从消息历史解析待办: {recovered}")
            return recovered
    
    return None


# ==================== 节点函数 ====================

def analyze_intent(state: TodoAgentState) -> TodoAgentState:
    """分析用户意图节点。
    
    职责：
    1. 调用 LLM 分析最后一条用户消息
    2. 判断是否需要确认
    3. 提取待办相关信息
    """
    logger.info("=== analyze_intent 节点 ===")
    
    messages = state["messages"]
    
    # 获取最近的历史消息 (最多5条)
    recent_messages = messages[-5:] if messages else []
    
    # 构建分析用的消息列表
    # 1. System Prompt
    analysis_messages = [SystemMessage(content=ANALYZE_PROMPT)]
    
    # 2. 历史消息 (直接附加, 保持对话流)
    # 注意: 我们需要确保 SystemMessage 在最前
    analysis_messages.extend(recent_messages)
    
    logger.info(f"分析用户消息 (上下文: {len(recent_messages)} 条)")
    
    # 🆕 P2: 历史任务查询 - 获取用户现有待办列表
    existing_todos_context = ""
    try:
        user_id = _get_user_id_from_state(state)
        if user_id:
            with get_db_context() as db:
                existing_todos = todo_repo.list_by_user(db, user_id, status="pending")
                if existing_todos:
                    # 构建简洁的任务列表上下文
                    todo_list = []
                    for t in existing_todos[:10]:  # 最多 10 条
                        due_str = t.due_date.strftime("%m月%d日") if t.due_date else "无截止"
                        priority_map = {1: "高", 2: "中", 3: "低"}
                        priority_str = priority_map.get(t.priority, "中")
                        todo_list.append(f"- {t.title} (截止:{due_str}, 优先级:{priority_str})")
                    
                    existing_todos_context = f"\n\n## 用户现有待办 ({len(existing_todos)}项)\n" + "\n".join(todo_list)
                    logger.info(f"加载用户现有待办: {len(existing_todos)} 项")
    except Exception as e:
        logger.warning(f"查询历史任务失败: {e}")

    
    # 🧹 清理上一轮的临时状态
    if state.get("pending_clarifications"):
        state["pending_clarifications"] = []
    if state.get("detected_conflicts"):
        state["detected_conflicts"] = []
    
    # 调用 LLM 分析（禁用流式输出，避免内部 JSON 被发送到前端）
    llm = get_llm(enable_streaming=False)
    try:
        # 🆕 P2: 将历史任务上下文注入到系统提示中
        enhanced_prompt = ANALYZE_PROMPT
        if existing_todos_context:
            enhanced_prompt += existing_todos_context
            enhanced_prompt += "\n\n## 冲突检测提示\n如果用户新任务与现有任务在同一天或有潜在冲突，设置 `conflict_risk: 'high'`。"
        
        # 重建分析消息，使用增强提示
        analysis_messages = [SystemMessage(content=enhanced_prompt)]
        analysis_messages.extend(recent_messages)
        
        response = llm.invoke(analysis_messages, config={"tags": ["internal_thought"]})
        # DeepSeek Reasoner返回的内容在content中
        result_text = response.content
        logger.info(f"LLM 分析结果: {result_text}")
        
        # 解析 JSON
        analysis = json.loads(result_text)
        
        # 🆕 Phase 1A: NLP 时间解析增强
        from app.services.time_parser import NaturalTimeParser
        time_parser = NaturalTimeParser()
        
        intent = analysis.get("intent", "chat")
        extracted_info = analysis.get("extracted_info", {})
        
        # 尝试提取并解析时间字段
        # 通常 LLM 会提取出如 "周三下午" 这样的原生文本放在 time 或 due_date 中
        raw_time = extracted_info.get("time") or extracted_info.get("due_date")
        if raw_time and isinstance(raw_time, str):
            parsed_time, meta = time_parser.parse(raw_time)
            if parsed_time:
                # 更新为 ISO 格式的标准时间
                extracted_info["due_date"] = parsed_time.isoformat()
                # 保留原始时间描述，用于澄清或确认
                extracted_info["original_time"] = meta.get("original_text")
                logger.info(f"时间解析: '{raw_time}' -> {extracted_info['due_date']}")
                
                # 特殊处理：如果是模糊时间，可能需要用户进一步澄清？
                # 目前 NaturalTimeParser 已经做了尽力推断，先信任它
                
            # 提取约束 (如 "周一不可用")
            constraints = meta.get("constraints")
            if constraints:
                # 合并到 time_constraints
                current_constraints = state.get("time_constraints") or {}
                # 注意：这里需要深度合并
                if "blocked_weekdays" in constraints:
                    current_blocked = set(current_constraints.get("blocked_weekdays", []))
                    current_blocked.update(constraints["blocked_weekdays"])
                    current_constraints["blocked_weekdays"] = list(current_blocked)
                
                state["time_constraints"] = current_constraints
                logger.info(f"解析到时间约束: {constraints}")

        # 🆕 Phase 3: 紧急任务检测与优先级提升
        # 检测紧急关键词
        last_user_msg = ""
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                last_user_msg = msg.content
                break
        
        urgent_keywords = ["刚刚", "紧急", "立刻", "马上", "领导说", "老板说", "赶紧"]
        is_urgent = any(kw in last_user_msg for kw in urgent_keywords)
        
        if is_urgent and intent == "create":
            # 自动提升优先级
            extracted_info["priority"] = 1
            extracted_info["is_urgent"] = True
            logger.info("检测到紧急任务，自动提升为高优先级")
            
            # 检查同一天是否有其他任务可能受影响
            due_date = extracted_info.get("due_date")
            if due_date:
                try:
                    from app.db.session import get_db_context
                    from app.repositories.todo_repository import todo_repo
                    from datetime import datetime
                    
                    # 解析新任务的日期
                    if isinstance(due_date, str):
                        new_due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    else:
                        new_due = due_date
                    
                    # 获取用户信息
                    user_id = None
                    if hasattr(state, 'get'):
                        pending_op = state.get("pending_operation")
                        if pending_op:
                            user_id = pending_op.get("user_id")
                    
                    # 仅在能获取用户ID时查询
                    if user_id:
                        with get_db_context() as db:
                            existing_todos = todo_repo.list_by_user(db, user_id, status="todo")
                            
                            affected_tasks = []
                            for todo in existing_todos:
                                if todo.due_date and todo.due_date.date() == new_due.date():
                                    if todo.priority >= 2:  # 中低优先级
                                        affected_tasks.append(todo.title)
                            
                            if affected_tasks:
                                # 记录受影响的任务
                                extracted_info["affected_tasks"] = affected_tasks
                                logger.info(f"紧急任务可能影响: {affected_tasks}")
                except Exception as e:
                    logger.warning(f"检查受影响任务失败: {e}")

        is_complex = analysis.get("is_complex", False)
        conflict_risk = analysis.get("conflict_risk", "none")
        quick_mode = state.get("quick_mode", False)
        
        # 🆕 处理clarify意图 - 区分两种场景
        if intent == "clarify":
            # 检查是否有部分待办信息
            has_partial_todo = (
                extracted_info.get("title") or 
                extracted_info.get("time") or 
                extracted_info.get("description")
            )
            
            if has_partial_todo:
                # 场景A: 有部分待办信息但需要补充 (如"明天开会")
                # 设置 pending_operation 以便后续确认
                state["pending_operation"] = {
                    "action": "create",
                    "data": extracted_info,
                    "needs_clarification": True  # 🆕 标记需要澄清
                }
                state["pending_clarifications"] = analysis.get("missing_info", [])
                state["conversation_context"] = analysis.get("context_hints", {})
                logger.info(f"部分待办信息,需要澄清: {extracted_info.get('title')}")
            else:
                # 场景B: 纯澄清,无待办信息 (如"帮我理一理")
                state["pending_clarifications"] = analysis.get("missing_info", [])
                state["conversation_context"] = analysis.get("context_hints", {})
                
                # 🆕 P3: 多项目队列填充
                projects = analysis.get("projects", [])
                if projects and len(projects) > 1:
                    state["project_queue"] = projects
                    state["current_project_index"] = 0
                    state["active_projects"] = projects
                    logger.info(f"识别到多项目: {projects}")
                else:
                    logger.info("纯澄清模式,无待办信息")
            
            return state
        
        # 🆕 处理 confirm 意图 - 用户确认创建待办
        if intent == "confirm":
            # 检查是否有待确认的操作
            pending_op = state.get("pending_operation")
            if pending_op and pending_op.get("needs_clarification"):
                # 用户确认了，移除 needs_clarification 标记
                # 这样下次 route_next 会路由到 confirm 节点触发 interrupt
                pending_op["needs_clarification"] = False
                state["pending_operation"] = pending_op
                logger.info(f"用户确认创建: {pending_op['data'].get('title')}")
            else:
                # 没有待确认的操作，尝试从 extracted_info 或消息历史重建 pending_operation
                if extracted_info and (extracted_info.get("title") or extracted_info.get("time")):
                    logger.info(f"从 extracted_info 重建 pending_operation: {extracted_info}")
                    state["pending_operation"] = {
                        "action": "create",
                        "data": extracted_info,
                        "needs_clarification": False,
                    }
                else:
                    # 尝试从消息历史中恢复待办上下文
                    recovered_data = _recover_todo_from_messages(messages)
                    if recovered_data:
                        # 合并用户补充的信息（如果有）
                        if extracted_info:
                            for key, value in extracted_info.items():
                                if value:
                                    recovered_data[key] = value
                        logger.info(f"从消息历史恢复待办上下文: {recovered_data}")
                        state["pending_operation"] = {
                            "action": "create",
                            "data": recovered_data,
                            "needs_clarification": True,  # 让用户确认
                        }
                    else:
                        logger.warning("收到 confirm 意图但无法恢复待办上下文")
                        state["pending_operation"] = None
            return state
        
        # 🆕 处理用户补充信息的场景
        # 如果用户在确认阶段补充了更多信息，合并到已有的待办数据中
        pending_op = state.get("pending_operation")
        if pending_op and pending_op.get("needs_clarification") and extracted_info:
            # 用户补充了信息，合并数据
            existing_data = pending_op.get("data", {})
            for key, value in extracted_info.items():
                if value:  # 只更新非空值
                    existing_data[key] = value
            pending_op["data"] = existing_data
            state["pending_operation"] = pending_op
            logger.info(f"用户补充信息: {extracted_info}")
            # 继续走确认流程（保持 needs_clarification = True）
            return state
        
        # 🆕 处理 batch_create 意图
        if intent == "batch_create":
            todos = extracted_info.get("todos", [])
            if todos:
                state["draft_todos"] = todos
                state["pending_operation"] = {
                    "action": "batch_create",
                    "data": {"count": len(todos), "todos": todos}
                }
                logger.info(f"批量创建: {len(todos)} 个待办")
            return state

        # 🆕 处理 summarize 意图 - 汇总输出
        if intent == "summarize":
            state["pending_operation"] = {
                "action": "summarize",
                "data": {},
                "skip_confirmation": True  # 汇总不需要确认
            }
            logger.info("识别到汇总请求")
            return state

        # 🆕 处理 constraint 意图 或 顺带的 constraints
        time_constraints = analysis.get("time_constraints")
        if intent == "constraint":
             ext_constraints = extracted_info.get("constraints", {})
             if ext_constraints:
                 current_constraints = state.get("time_constraints") or {}
                 current_constraints.update(ext_constraints)
                 state["time_constraints"] = current_constraints
                 logger.info(f"更新时间约束: {ext_constraints}")
                 # 约束通常伴随着对之前计划的影响，可能需要重新检测冲突
                 # 我们暂时视为一次 update 操作来触发检测，或者直接返回让后续节点处理
                 return state

        # 提取顺带的约束(mix-in)
        if time_constraints:
             current_constraints = state.get("time_constraints") or {}
             current_constraints.update(time_constraints)
             state["time_constraints"] = current_constraints

        # 标记复杂任务和冲突风险
        if is_complex:
            # 添加到draft_todos等待拆解
            draft_todos = state.get("draft_todos", [])
            draft_todos.append({
                "title": extracted_info.get("title"),
                "is_complex": True,
                "subtask_hints": analysis.get("subtask_hints", []),
                "dependencies": analysis.get("dependencies", []),
                **extracted_info
            })
            state["draft_todos"] = draft_todos
        
        if conflict_risk != "none":
            state["detected_conflicts"] = analysis.get("conflicts", [])
        
        # 智能确认策略
        if quick_mode:
            needs_confirmation = False
            logger.info("快速模式:跳过确认")
        elif intent == "create":
            needs_confirmation = True
            logger.info("创建操作:需要确认")
        elif intent in ["delete", "update", "batch_complete", "merge"]: # merge 也需要确认
            needs_confirmation = True
        elif intent in ["query", "complete"]:
            needs_confirmation = False
        
        if needs_confirmation:
            # 设置待确认操作
            # 对于创建操作，先经过 clarify 节点展示信息并询问用户
            # 用户确认后才进入人工审核（interrupt）
            state["pending_operation"] = {
                "action": intent,
                "data": extracted_info,
                "needs_clarification": intent == "create"  # 创建操作需要先确认
            }
            state["extracted_info"] = extracted_info
            logger.info(f"需要确认: {intent}, 需要先澄清: {intent == 'create'}")
        else:
            # 直接执行（也需要设置 pending_operation，供 execute 节点使用）
            state["pending_operation"] = {
                "action": intent,
                "data": extracted_info,
                "skip_confirmation": True  # 标记跳过确认
            }
            state["extracted_info"] = extracted_info
            logger.info(f"直接执行: {intent}")

        
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        # 降级处理：如果无法解析，假设是闲聊
        state["pending_operation"] = None
    
    return state


def request_confirmation(state: TodoAgentState) -> TodoAgentState:
    """请求用户确认节点。
    
    职责：
    1. 生成友好的确认消息
    2. 展示提取的信息
    3. 引导用户补充或确认
    """
    logger.info("=== request_confirmation 节点 ===")
    
    operation = state.get("pending_operation")
    
    if not operation:
        logger.warning("无待确认操作")
        return state
    
    action = operation.get("action")
    # 优先使用 operation["data"]，而非 extracted_info
    # 因为 operation["data"] 是最新的、经过处理的数据
    data = operation.get("data", {})
    
    logger.info(f"待确认的操作数据: action={action}, data={data}")
    
    # 生成确认消息
    if action == "create":
        # 为所有字段提供默认值，避免显示空字符串
        title = data.get("title") or "新待办"
        time_str = data.get("time") or data.get("due_date") or ""
        priority = data.get("priority") or "中"
        category = data.get("category") or ""
        description = data.get("description") or ""
        
        # 如果标题看起来是空的或者只有默认值，尝试从描述或原始消息中提取
        if title == "新待办" and description:
            title = description[:50]  # 使用描述的前50个字符作为标题
        
        confirm_msg = f"""好的，我帮你记录这个待办 📝

**{title}**
- 📅 时间：{time_str if time_str else '未设置'}
- ⭐ 优先级：{priority}
- 🏷️ 分类：{category if category else '未分类'}
{f'- 📄 描述：{description}' if description else ''}

要补充一些信息吗？比如：
1. 具体时间（几点）
2. 详细描述
3. 是否需要提醒

直接说"确认"即可创建，或告诉我补充内容～
"""
    
    elif action == "batch_complete":
        count = data.get("count", 0)
        confirm_msg = f"即将批量完成 {count} 个待办，确认吗？"
    
    elif action == "delete":
        title = data.get("title", "待办")
        confirm_msg = f"确认删除 **{title}** 吗？"
    
    elif action == "update":
        title = data.get("title", "待办")
        confirm_msg = f"确认更新 **{title}** 吗？"

    elif action == "merge":
        target_tasks = data.get("target_tasks", [])
        confirm_msg = f"确认合并以下任务吗？\n" + "\n".join([f"- {t}" for t in target_tasks])
    
    else:
        # 改进默认确认消息，显示数据概要
        data_summary = ", ".join([f"{k}: {v}" for k, v in data.items() if v])[:100]
        confirm_msg = f"确认执行 {action} 操作吗？\n\n参数：{data_summary if data_summary else '(无)'}"
    
    # 生成客户能看懂的详细摘要（用于前端显示）
    friendly_summary = ""
    if action == "create":
        # 提取所有可能的字段
        title = data.get("title") or "新待办"
        time_str = data.get("time") or data.get("due_date") or ""
        priority = data.get("priority") or "中"
        category = data.get("category") or ""
        description = data.get("description") or ""
        tags = data.get("tags") or []
        
        # 构建详细的多行摘要
        lines = [f"**创建待办**"]
        lines.append(f"📝 标题：{title}")
        if time_str:
            lines.append(f"⏰ 时间：{time_str}")
        lines.append(f"⭐ 优先级：{priority}")
        if category:
            lines.append(f"🏷️ 分类：{category}")
        if description:
            lines.append(f"📄 描述：{description}")
        if tags:
            lines.append(f"🔖 标签：{', '.join(tags) if isinstance(tags, list) else tags}")
        
        friendly_summary = "\n".join(lines)
        
    elif action == "update":
        title = data.get("title", "待办")
        lines = [f"**更新待办**", f"📝 标题：{title}"]
        
        # 显示所有要更新的字段
        if "time" in data or "due_date" in data:
            time_str = data.get("time") or data.get("due_date")
            lines.append(f"⏰ 新时间：{time_str}")
        if "priority" in data:
            lines.append(f"⭐ 新优先级：{data.get('priority')}")
        if "category" in data:
            lines.append(f"🏷️ 新分类：{data.get('category')}")
        if "status" in data:
            lines.append(f"📊 新状态：{data.get('status')}")
        
        friendly_summary = "\n".join(lines)
        
    elif action == "delete":
        title = data.get("title", "待办")
        friendly_summary = f"**删除待办**\n📝 标题：{title}"
        
    elif action == "batch_complete":
        count = data.get("count", 0)
        friendly_summary = f"**批量操作**\n✅ 完成 {count} 个待办"
        
    elif action == "merge":
        target_tasks = data.get("target_tasks", [])
        friendly_summary = f"**合并待办**\n🔗 将合并以下任务:\n" + "\n".join([f"- {t}" for t in target_tasks])

    else:
        friendly_summary = f"**执行操作**\n操作类型：{action}"
    
    # 构造前端期望的确认数据结构（与 CompactApproval 组件适配）
    # 将 data 字段复制并添加客户可读的显示消息
    display_args = {
        **data,
        "_display_message": friendly_summary  # 关键：前端优先显示此字段
    }
    
    confirmation_data = {
        "action_requests": [
            {
                "name": action,  # create / update / delete 等
                "args": display_args
            }
        ]
    }
    
    logger.info(f"请求用户确认 (interrupt): {action}, message_preview={confirm_msg[:50]}...")
    
    # 触发中断，发送数据给前端
    # resume_value 将包含用户的决策 (decision)
    decision = interrupt(confirmation_data)
    
    logger.info(f"收到用户决策 (resume): {decision}")
    
    # 根据决策更新状态
    if decision.get("type") == "accept":
        # 如果用户修改了参数 (例如修改了时间)
        if "args" in decision:
            logger.info(f"用户更新了参数: {decision['args']}")
            if state["pending_operation"]:
                 state["pending_operation"]["data"].update(decision["args"])
        
        return {"user_confirmed": True}
        
    elif decision.get("type") == "reject":
        logger.info("用户拒绝了操作")
        return {"user_confirmed": False}
        
    # 默认情况
    return {"user_confirmed": False}


def execute_operation(state: TodoAgentState) -> TodoAgentState:
    """执行操作节点。
    
    职责：
    1. 检查用户确认状态
    2. 调用对应的工具函数
    3. 通过 custom 事件发送结构化结果
    4. 返回结果（同时追加 AIMessage 用于历史记录）
    """
    logger.info("=== execute_operation 节点 ===")
    
    # 获取 StreamWriter 用于发送自定义事件
    writer = get_stream_writer()
    
    user_confirmed = state.get("user_confirmed")
    operation = state.get("pending_operation")
    extracted_info = state.get("extracted_info", {})
    
    # 如果用户取消
    if user_confirmed is False:
        state["messages"].append(AIMessage(content="好的，已取消操作 👌"))
        return state
    
    # 如果没有操作（如查询）
    if not operation:
        # 直接调用查询
        result = _execute_query(extracted_info, state)
        
        # 转换 ToolResult 为 AIMessage
        if result["success"]:
            additional_kwargs = {}
            if result.get("data"):
                additional_kwargs["data"] = result["data"]
            if result.get("data_type"):
                additional_kwargs["data_type"] = result["data_type"]
            
            state["messages"].append(AIMessage(
                content=result["message"],
                additional_kwargs=additional_kwargs
            ))
            
            # 发送 custom 事件用于前端流式渲染
            if result.get("data_type"):
                emit_result(writer, 
                           data_type=result["data_type"],
                           data=result.get("data", {}),
                           message=result["message"],
                           node="execute_operation")
            else:
                emit_token(writer, content=result["message"], node="execute_operation")
        else:
            error_msg = f"❌ {result['message']}"
            if result.get("error"):
                error_msg += f"\n错误详情: {result['error']}"
            state["messages"].append(AIMessage(content=error_msg))
        
        return state

    
    # 执行确认后的操作
    action = operation.get("action")
    data = operation.get("data", {})
    
    logger.info(f"执行操作: {action}")
    
    try:
        if action == "create":
            result = _execute_create(data, state)
        elif action == "update":
            result = _execute_update(data, state)
        elif action == "complete":
            result = _execute_complete(data, state)
        elif action == "delete":
            result = _execute_delete(data, state)
        elif action == "batch_complete":
            result = _execute_batch_complete(data, state)
        elif action == "query":
            result = _execute_query(data, state)
        elif action == "merge":
            result = _execute_merge(data, state)
        else:
            result = f"⚠️ 暂不支持操作: {action}"
        
        # 统一转换 ToolResult 为 AIMessage
        if result["success"]:
            # 成功：构造包含数据的 AIMessage
            additional_kwargs = {}
            if result.get("data"):
                additional_kwargs["data"] = result["data"]
            if result.get("data_type"):
                additional_kwargs["data_type"] = result["data_type"]
            
            state["messages"].append(AIMessage(
                content=result["message"],
                additional_kwargs=additional_kwargs
            ))
            
            # 发送 custom 事件用于前端流式渲染
            if result.get("data_type"):
                emit_result(writer, 
                           data_type=result["data_type"],
                           data=result.get("data", {}),
                           message=result["message"],
                           node="execute_operation")
            else:
                emit_token(writer, content=result["message"], node="execute_operation")
        else:
            # 失败：显示错误信息
            error_msg = f"❌ {result['message']}"
            if result.get("error"):
                error_msg += f"\n错误详情: {result['error']}"
            state["messages"].append(AIMessage(content=error_msg))
            
    except Exception as e:
        logger.exception(f"执行失败: {e}")
        state["messages"].append(AIMessage(content=f"❌ 操作失败: {str(e)}"))
    
    return state


# ==================== 工具调用辅助函数 ====================

def _get_user_id_from_state(state: TodoAgentState, config: RunnableConfig = None) -> int:
    """从 state 或 RunnableConfig 中获取 user_id。
    
    优先级：
    1. state.get("user_id") - 主要来源（由 graph 调用方传递）
    2. RunnableConfig.configurable["user_id"]
    3. pending_operation["user_id"]
    
    Args:
        state: TodoAgentState
        config: RunnableConfig（可选）
        
    Returns:
        int: 用户 ID
        
    Raises:
        ValueError: 如果无法获取 user_id
    """
    # 优先从 state 直接读取（MultiAgentState 有 user_id 字段）
    user_id = state.get("user_id")
    if user_id is not None:
        return int(user_id)
    
    # 尝试从 RunnableConfig 获取
    if config and hasattr(config, "configurable"):
        user_id = config.get("configurable", {}).get("user_id")
        if user_id is not None:
            return int(user_id)
    
    # 尝试从 pending_operation 中获取
    pending_op = state.get("pending_operation")
    if pending_op and "user_id" in pending_op:
        return int(pending_op["user_id"])
    
    # 无法获取时抛出异常，而非返回默认值
    error_msg = (
        "无法获取 user_id：请确保在调用 graph 时传递 user_id 参数，"
        "例如 graph.ainvoke({'messages': [...], 'user_id': 1})"
    )
    logger.error(error_msg)
    raise ValueError(error_msg)


def _execute_query(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行查询操作 - 返回结构化数据以供前端渲染 UI。"""
    
    user_id = _get_user_id_from_state(state)
    
    status = data.get("status")
    category = data.get("category")
    priority = data.get("priority")
    keyword = data.get("keyword")
    
    logger.info(f"执行查询: user_id={user_id}, status={status}, category={category}, priority={priority}, keyword={keyword}")
    
    try:
        with get_db_context() as db:
            todos = todo_repo.list_by_user(
                db, 
                user_id, 
                status=status,
                category=category,
                priority=priority,
                keyword=keyword
            )
            
            # 序列化待办数据
            todos_data = []
            for t in todos:
                todos_data.append({
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "description": t.description,
                    "priority": t.priority,
                    "due_date": t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else None,
                    "category": t.category,
                    "tags": t.tags,
                    # 新增字段支持 TodoListCard
                    "start_time": t.start_time.strftime("%Y-%m-%d %H:%M") if t.start_time else None,
                    "progress": t.progress,
                    "progress_notes": t.progress_notes
                })
            
            # 返回统一的 ToolResult
            message = f"为您找到 {len(todos)} 个待办事项" if todos else "没有找到符合条件的待办事项"
            
            return ToolResultBuilder.success(
                message, 
                data={"todos": todos_data}, 
                data_type="todo_list"
            )
            
    except Exception as e:
        logger.exception(f"查询待办失败: {e}")
        return ToolResultBuilder.error("查询待办失败", str(e))


def _execute_create(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行创建操作。"""
    from app.ai.tools.todo_tools import add_todo
    
    user_id = _get_user_id_from_state(state)
    config = RunnableConfig(configurable={"user_id": user_id})
    
    # 解析时间表达
    due_date = data.get("time") or data.get("due_date")
    
    try:
        result_str = add_todo.invoke({
            "title": data.get("title", "新待办"),
            "description": data.get("description", ""),
            "priority": _parse_priority(data.get("priority")),
            "due_date": due_date,
            "category": data.get("category"),
            "tags": data.get("tags"),
            "reminder_enabled": data.get("reminder_enabled", False),
            "config": config
        })
        
        return ToolResultBuilder.success(result_str)
    except Exception as e:
        logger.exception(f"创建待办失败: {e}")
        return ToolResultBuilder.error("创建待办失败", str(e))


def _execute_update(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行更新操作。"""
    from app.ai.tools.todo_tools import update_todo
    
    user_id = _get_user_id_from_state(state)
    config = RunnableConfig(configurable={"user_id": user_id})
    
    try:
        result_str = update_todo.invoke({
            "todo_id": data.get("todo_id"),
            "title": data.get("title"),
            "description": data.get("description"),
            "priority": _parse_priority(data.get("priority")),
            "due_date": data.get("due_date"),
            "category": data.get("category"),
            "status": data.get("status"),
            "config": config
        })
        
        return ToolResultBuilder.success(result_str)
    except Exception as e:
        logger.exception(f"更新待办失败: {e}")
        return ToolResultBuilder.error("更新待办失败", str(e))


def _execute_complete(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行完成操作。"""
    from app.ai.tools.todo_tools import complete_todo
    
    user_id = _get_user_id_from_state(state)
    config = RunnableConfig(configurable={"user_id": user_id})
    
    try:
        result_str = complete_todo.invoke({
            "todo_id": data.get("todo_id"),
            "config": config
        })
        
        return ToolResultBuilder.success(result_str)
    except Exception as e:
        logger.exception(f"完成待办失败: {e}")
        return ToolResultBuilder.error("完成待办失败", str(e))


def _execute_delete(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行删除操作。"""
    from app.ai.tools.todo_tools import delete_todo
    
    user_id = _get_user_id_from_state(state)
    config = RunnableConfig(configurable={"user_id": user_id})
    
    try:
        result_str = delete_todo.invoke({
            "todo_id": data.get("todo_id"),
            "config": config
        })
        
        return ToolResultBuilder.success(result_str)
    except Exception as e:
        logger.exception(f"删除待办失败: {e}")
        return ToolResultBuilder.error("删除待办失败", str(e))


def _execute_batch_complete(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行批量完成操作。"""
    from app.ai.tools.batch_todo_tools import batch_complete_todos
    
    user_id = _get_user_id_from_state(state)
    config = RunnableConfig(configurable={"user_id": user_id})
    
    try:
        result_str = batch_complete_todos.invoke({
            "todo_ids": data.get("todo_ids", []),
            "config": config
        })
        
        return ToolResultBuilder.success(result_str)
    except Exception as e:
        logger.exception(f"批量完成待办失败: {e}")
        return ToolResultBuilder.error("批量完成待办失败", str(e))


def _execute_merge(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行合并操作。
    
    逻辑：
    1. 如果是 draft_todos 里的任务，合并描述
    2. 如果是现有任务，建议更新（目前简化为返回提示）
    """
    target_tasks = data.get("target_tasks", [])
    merge_strategy = data.get("merge_strategy", "combine_description")
    
    logger.info(f"执行合并: target={target_tasks}, strategy={merge_strategy}")
    
    if not target_tasks:
        return ToolResultBuilder.error("合并失败", "没有指定要合并的任务")
    
    draft_todos = state.get("draft_todos", [])
    
    # 尝试在 draft_todos 中找到这些任务
    merged_indices = []
    merged_titles = []
    base_todo = None
    
    for i, todo in enumerate(draft_todos):
        # 模糊匹配标题
        for target in target_tasks:
            if target in todo.get("title", ""):
                if i not in merged_indices:
                    merged_indices.append(i)
                    merged_titles.append(todo.get("title"))
                    
                    if base_todo is None:
                        base_todo = todo
                    else:
                         # 合并逻辑：将后续任务的 标题/描述/hint 合并到 base
                        base_todo["description"] = (base_todo.get("description", "") + "\n\n" + 
                                                  f"【合并自 {todo.get('title')}】:\n" + todo.get("description", "")).strip()
                        
                        # 合并子任务提示
                        if todo.get("subtask_hints"):
                            base_todo_hints = base_todo.get("subtask_hints", [])
                            base_todo_hints.extend(todo.get("subtask_hints", []))
                            base_todo["subtask_hints"] = list(set(base_todo_hints)) # 去重
                        
                        # 合并依赖
                        if todo.get("dependencies"):
                            base_todo_deps = base_todo.get("dependencies", [])
                            base_todo_deps.extend(todo.get("dependencies", []))
                            base_todo["dependencies"] = list(set(base_todo_deps))
    
    if len(merged_indices) > 1:
        # 从 draft_todos 中移除被合并的任务（除了 base）
        # 倒序移除以免影响索引
        state["draft_todos"] = [t for i, t in enumerate(draft_todos) if i == merged_indices[0] or i not in merged_indices]
        
        return ToolResultBuilder.success(
            f"已将 {', '.join(merged_titles[1:])} 合并到 **{merged_titles[0]}** 中",
            data={"merged_todo": base_todo}
        )
    else:
        # 如果找不到足够的 draft 任务，可能是针对已存在任务的合并建议
        # 这里仅做简单反馈
        return ToolResultBuilder.success(
            f"收到合并请求 ({', '.join(target_tasks)})，已记录偏好。建议手动更新主任务描述。"
        )


def _parse_priority(priority_str: Optional[str]) -> int:
    """解析优先级字符串为数字。"""
    if not priority_str:
        return 2
    
    priority_map = {
        "高": 1, "high": 1, "1": 1,
        "中": 2, "medium": 2, "2": 2,
        "低": 3, "low": 3, "3": 3
    }
    
    return priority_map.get(str(priority_str).lower(), 2)


# ==================== 路由函数 ====================

def route_next(state: TodoAgentState) -> Literal["clarify", "decompose", "conflict", "confirm", "execute", "summarize", "end"]:
    """路由到下一个节点 - 增强版。
    
    流程优先级:
    0. 汇总请求 → summarize
    1. 有待办 + 需要澄清 → clarify (澄清完会再次进入 analyze)
    2. 纯澄清 (无待办) → clarify
    3. 有复杂任务 → decompose
    4. 有待办需要冲突检测 → conflict
    5. 有待办需要确认 → confirm
    6. 有待办跳过确认（如查询） → execute
    7. 默认执行 → execute
    """
    pending_op = state.get("pending_operation")
    
    # 0. 汇总请求 → summarize
    if pending_op and pending_op.get("action") == "summarize":
        logger.info("路由到: summarize (汇总输出)")
        return "summarize"
    
    # 1. 检查是否需要跳过确认（如查询操作）
    if pending_op and pending_op.get("skip_confirmation"):
        logger.info("路由到: execute (跳过确认)")
        return "execute"
    
    # 1. 有待办 + 需要澄清 → clarify (澄清完会再次进入 analyze)
    if pending_op and pending_op.get("needs_clarification"):
        logger.info("路由到: clarify (待办需要补充信息)")
        return "clarify"
    
    # 2. 纯澄清 (无待办) → clarify
    if state.get("pending_clarifications") and not pending_op:
        logger.info("路由到: clarify (纯澄清模式)")
        return "clarify"
    
    # 3. 有复杂任务需要拆解?
    draft_todos = state.get("draft_todos", [])
    if any(t.get("is_complex") for t in draft_todos):
        logger.info("路由到: decompose (任务拆解)")
        return "decompose"
    
    # 4. 有待办需要冲突检测?
    if draft_todos and not state.get("detected_conflicts"):
        logger.info("路由到: conflict (冲突检测)")
        return "conflict"
    
    if state.get("pending_operation"):
        logger.info("路由到: confirm")
        return "confirm"
    
    # 5. 默认执行
    logger.info("路由到: execute")
    return "execute"



# ==================== 图构建 ====================

def create_todo_graph(model=None, enable_thinking: bool = False, model_id: str = None, checkpointer=None):
    """创建 LangGraph 待办 Agent - 多轮对话增强版。
    
    Args:
        model: LLM 实例
        enable_thinking: 是否启用深度思考
        model_id: 模型 ID
        checkpointer: 检查点保存器（可选）
        
    Returns:
        编译后的 Graph 实例
    """
    # 导入增强节点
    from app.ai.agents.todo_enhanced_nodes import (
        clarify_node,
        conflict_detection_node,
        task_decomposition_node
    )
    from app.ai.agents.summarize_node import summarize_node
    
    # 创建工作流
    workflow = StateGraph(TodoAgentState)
    
    # === 添加节点 ===
    workflow.add_node("analyze", analyze_intent)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("decompose", task_decomposition_node)
    workflow.add_node("conflict", conflict_detection_node)
    workflow.add_node("confirm", request_confirmation)
    workflow.add_node("execute", execute_operation)
    workflow.add_node("summarize", summarize_node)  # 汇总节点
    
    # === 设置入口 ===
    workflow.set_entry_point("analyze")
    
    # === 设置边 ===
    
    # analyze → 条件路由 (clarify/decompose/conflict/confirm/execute)
    workflow.add_conditional_edges(
        "analyze",
        route_next,
        {
            "clarify": "clarify",
            "decompose": "decompose",
            "conflict": "conflict",
            "confirm": "confirm",
            "execute": "execute",
            "summarize": "summarize"  # 汇总路由
        }
    )
    
    # clarify → END (等待用户回复)
    workflow.add_edge("clarify", END)
    
    # decompose → conflict (拆解后检测冲突)
    workflow.add_edge("decompose", "conflict")
    
    # summarize → END (汇总后结束)
    workflow.add_edge("summarize", END)
    
    # conflict → confirm/execute
    workflow.add_conditional_edges(
        "conflict",
        lambda state: "confirm" if state.get("pending_operation") else "execute",
        {
            "confirm": "confirm",
            "execute": "execute"
        }
    )
    
    # confirm → execute (确认后执行)
    workflow.add_edge("confirm", "execute")
    
    # execute → END
    workflow.add_edge("execute", END)
    
    # === 编译图 ===
    # 允许外部传入 checkpointer，以便在多智能体集成时共享或使用持久化存储
    if checkpointer is None:
        checkpointer = MemorySaver()
        
    # 注意：移除了 interrupt_before，因为：
    # 1. 查询操作（list_todos）是只读的，不需要中断
    # 2. 在多智能体架构中，中断会导致子图挂起而无法返回结果
    # 3. 确认逻辑应该在对话流中通过 clarify_node 自然完成
    graph = workflow.compile(
        checkpointer=checkpointer
        # 注意：不再使用 interrupt_before，而是使用 confirm 节点内的 interrupt() 函数
    )
    
    logger.info("✅ 待办Agent Graph (多轮对话增强版) 创建成功")
    return graph
