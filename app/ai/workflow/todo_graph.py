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

# 导入自定义事件工具
from langgraph.config import get_stream_writer
from app.ai.events import emit_clarification, emit_token, emit_status, emit_error

# 导入统一的状态辅助函数
from app.ai.utils.state_helpers import get_user_id, get_user_id_optional

# 导入实体解析节点
from app.ai.agents.resolve_node import resolve_entity, route_after_resolve

# 导入意图分析辅助函数
from app.ai.workflow.todo_intent_helpers import (
    filter_messages_for_todo,
    query_existing_todos,
    parse_time_info,
    detect_urgent_task,
    process_clarify_intent,
    process_confirm_intent,
    process_batch_create_intent,
    process_summarize_intent,
    process_constraint_intent,
    determine_confirmation_need
)

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


from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# ==================== Pydantic 响应模型 (P1-4) ====================

class IntentResult(BaseModel):
    """LLM 意图分析结果模型"""
    intent: str = Field(description="用户意图: create, update, delete, query, confirm, clarify 等")
    extracted_info: Dict = Field(default={}, description="提取的实体信息: title, time, due_date, priority 等")
    missing_info: List[str] = Field(default=[], description="缺失的关键信息")
    is_complex: bool = Field(default=False, description="是否为复杂任务")
    conflict_risk: str = Field(default="none", description="冲突风险: high, medium, none")
    context_hints: Dict = Field(default={}, description="上下文线索")
    projects: List[str] = Field(default=[], description="涉及的项目列表")
    time_constraints: Dict = Field(default={}, description="时间约束")


# ==================== 节点函数 ====================

def _get_user_id_from_state(state: TodoAgentState) -> Optional[int]:
    """从 State 中获取用户 ID (统一入口)"""
    return get_user_id_optional(state, config=None)


def _get_user_todo_context(user_id: int) -> str:
    """获取用户现有待办上下文字符串"""
    if not user_id:
        return ""
        
    try:
        with get_db_context() as db:
            existing_todos = todo_repo.list_by_user(db, user_id, status="pending")
            if not existing_todos:
                return ""
                
            # 构建简洁的任务列表上下文
            todo_list = []
            for t in existing_todos[:10]:  # 最多 10 条
                due_str = t.due_date.strftime("%m月%d日") if t.due_date else "无截止"
                priority_map = {1: "高", 2: "中", 3: "低"}
                priority_str = priority_map.get(t.priority, "中")
                todo_list.append(f"- {t.title} (截止:{due_str}, 优先级:{priority_str})")
            
            context = f"\n\n## 用户现有待办 ({len(existing_todos)}项)\n" + "\n".join(todo_list)
            logger.info(f"加载用户现有待办: {len(existing_todos)} 项")
            return context
    except Exception as e:
        logger.warning(f"查询历史任务失败: {e}")
        return ""

def analyze_intent(state: TodoAgentState) -> Dict:
    """分析用户意图节点（重构版）。
    
    使用辅助函数拆分逻辑，返回增量更新字典而非直接修改 state。
    
    职责：
    1. 调用 LLM 分析最后一条用户消息
    2. 判断是否需要确认
    3. 提取待办相关信息
    """
    logger.info("=== analyze_intent 节点 ===")
    
    # 收集需要更新的字段
    updates: Dict = {}
    
    messages = state.get("messages", [])
    
    # Step 1: 消息过滤与 Handoff 上下文构建
    pending_handoff = state.get("pending_handoff")
    filtered_messages, handoff_context = filter_messages_for_todo(messages, pending_handoff)
    recent_messages = filtered_messages[-5:] if filtered_messages else []
    
    logger.info(f"分析用户消息 (Original: {len(messages)}, Filtered: {len(filtered_messages)}, Use: {len(recent_messages)})")
    
    # Step 2: 历史任务查询 (通过 Helper)
    user_id = _get_user_id_from_state(state)
    existing_todos_context = ""
    if user_id:
        existing_todos_context = query_existing_todos(user_id)
    
    # 清理上一轮的临时状态
    if state.get("pending_clarifications"):
        updates["pending_clarifications"] = []
    if state.get("detected_conflicts"):
        updates["detected_conflicts"] = []
    
    # Step 3: 调用 LLM 分析
    llm = get_llm(enable_streaming=False)
    
    # 构建 Parser
    parser = JsonOutputParser(pydantic_object=IntentResult)
    format_instructions = parser.get_format_instructions()
    
    # 构建 Prompt
    system_prompt = f"{ANALYZE_PROMPT}\n{handoff_context}\n{existing_todos_context}\n\n## 冲突检测提示\n如果用户新任务与现有任务在同一天或有潜在冲突，设置 `conflict_risk: 'high'`。\n\n{format_instructions}"
    
    analysis_messages = [SystemMessage(content=system_prompt)]
    analysis_messages.extend(recent_messages)
    
    try:
        response = llm.invoke(analysis_messages, config={"tags": ["internal_thought"]})
        result_text = response.content
        logger.info(f"LLM 分析结果长度: {len(result_text)}")
        
        try:
            analysis_dict = parser.parse(result_text)
        except Exception as e:
            logger.warning(f"解析 JSON 失败，重试清理: {e}")
            # 简单的 markdown json 清理
            clean_text = result_text.replace("```json", "").replace("```", "").strip()
            start = clean_text.find("{")
            end = clean_text.rfind("}")
            if start != -1 and end != -1:
                clean_text = clean_text[start:end+1]
            analysis_dict = json.loads(clean_text)
        
        analysis = analysis_dict

        intent = analysis.get("intent", "chat")
        extracted_info = analysis.get("extracted_info", {})
        
        # Step 4: 时间解析
        extracted_info, time_constraints = parse_time_info(
            extracted_info, 
            state.get("time_constraints")
        )
        if time_constraints:
            updates["time_constraints"] = time_constraints
        
        # Step 5: 紧急任务检测
        extracted_info = detect_urgent_task(messages, intent, extracted_info, user_id)
        
        # Step 6: 意图分支处理
        
        # 6.1 clarify 意图
        if intent == "clarify":
            result = process_clarify_intent(analysis, extracted_info)
            updates.update(result.to_dict())
            return updates
        
        # 6.2 confirm 意图
        if intent == "confirm":
            result = process_confirm_intent(state.get("pending_operation"), extracted_info)
            updates.update(result.to_dict())
            return updates
        
        # 6.3 用户补充信息场景
        pending_op = state.get("pending_operation")
        if pending_op and pending_op.get("needs_clarification") and extracted_info:
            existing_data = pending_op.get("data", {})
            for key, value in extracted_info.items():
                if value:
                    existing_data[key] = value
            pending_op["data"] = existing_data
            updates["pending_operation"] = pending_op
            return updates
        
        # 6.4 batch_create 意图
        if intent == "batch_create":
            result = process_batch_create_intent(extracted_info)
            updates.update(result.to_dict())
            return updates
        
        # 6.5 summarize 意图
        if intent == "summarize":
            result = process_summarize_intent()
            updates.update(result.to_dict())
            return updates
        
        # 6.6 constraint 意图
        if intent == "constraint":
            result = process_constraint_intent(extracted_info, state.get("time_constraints"))
            updates.update(result.to_dict())
            return updates
        
        # 6.7 处理顺带的约束
        analysis_time_constraints = analysis.get("time_constraints")
        if analysis_time_constraints:
            current_constraints = state.get("time_constraints") or {}
            current_constraints.update(analysis_time_constraints)
            updates["time_constraints"] = current_constraints
        
        # Step 7: 复杂任务和冲突风险标记
        is_complex = analysis.get("is_complex", False)
        conflict_risk = analysis.get("conflict_risk", "none")
        
        if is_complex:
            draft_todos = list(state.get("draft_todos") or [])
            draft_todos.append({
                "title": extracted_info.get("title"),
                "is_complex": True,
                "subtask_hints": analysis.get("subtask_hints", []),
                "dependencies": analysis.get("dependencies", []),
                **extracted_info
            })
            updates["draft_todos"] = draft_todos
        
        if conflict_risk != "none":
            updates["detected_conflicts"] = analysis.get("conflicts", [])
        
        # Step 8: 确定是否需要确认
        quick_mode = state.get("quick_mode", False)
        needs_confirmation, needs_clarification = determine_confirmation_need(intent, quick_mode)
        
        if needs_confirmation:
            updates["pending_operation"] = {
                "action": intent,
                "data": extracted_info,
                "needs_clarification": needs_clarification
            }
            updates["extracted_info"] = extracted_info
            logger.info(f"需要确认: {intent}, 需要先澄清: {needs_clarification}")
        else:
            updates["pending_operation"] = {
                "action": intent,
                "data": extracted_info,
                "skip_confirmation": True
            }
            updates["extracted_info"] = extracted_info
            logger.info(f"直接执行: {intent}")
            
    except Exception as e:
        logger.error(f"意图分析严重错误: {e}")
        updates["pending_operation"] = None
    
    return updates
def ask_confirmation(state: TodoAgentState) -> Dict:
    """请求用户确认节点。
    
    发送包含 Confirmation Card 的消息给用户。
    实际的等待中断在 wait_for_confirmation 节点处理。
    """
    logger.info("=== ask_confirmation 节点 ===")
    
    operation = state.get("pending_operation")
    if not operation:
        logger.warning("无待确认操作")
        return {}
    
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
        # 优先使用 resolve 节点解析后的信息
        todo_id = data.get("todo_id")
        title = data.get("resolved_title") or data.get("title") or "待办"
        id_hint = f" (ID: {todo_id})" if todo_id else ""
        confirm_msg = f"确认删除 **{title}**{id_hint} 吗？"
    
    elif action == "update":
        # 优先使用 resolve 节点解析后的信息
        todo_id = data.get("todo_id")
        title = data.get("resolved_title") or data.get("title") or "待办"
        id_hint = f" (ID: {todo_id})" if todo_id else ""
        confirm_msg = f"确认更新 **{title}**{id_hint} 吗？"

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
    
    logger.info(f"请求用户确认: {action}, message_preview={confirm_msg[:50]}...")
    
    # 构造结构化 operation 对象用于前端渲染 ConfirmationCard
    operation_data = {
        "action": action, # 统一使用 action 字段
        "data": data,
        "summary": friendly_summary
    }
    
    # 对于更新操作，尝试构造 diff 数据
    if action == "update":
        todo_id = data.get("todo_id")
        resolved_title = data.get("resolved_title")
        
        # 填充 target_task
        if todo_id:
            operation_data["target_task"] = {
                "id": todo_id,
                "title": resolved_title or title
            }
        
        # 填充 diff
        # 注意：这里简化处理，实际 diff 需要从数据库获取原始值进行对比
        # 但在 route_next 或 resolve 阶段我们可能已经有了原始数据
        # 如果 state 中没有原始待办，这里只能显示新值
        diff = {}
        for key, value in data.items():
            if key in ["title", "priority", "due_date", "description", "category"] and value:
                # 假设旧值未知，前端会显示 "-> 新值"
                diff[key] = {"old": None, "new": value}
        operation_data["diff"] = diff
        
    elif action == "delete":
         todo_id = data.get("todo_id")
         if todo_id:
            operation_data["target_task"] = {
                "id": todo_id,
                "title": data.get("resolved_title") or data.get("title")
            }

    # 返回 AIMessage
    msg = AIMessage(
        content=confirm_msg,
        additional_kwargs={
            "requires_confirmation": True,
            "operation": operation_data
        }
    )
    
    return {
        "messages": [msg],
        "pending_operation": operation, # 保持 pending_operation 状态
        "user_confirmed": None # 重置确认状态
    }


def wait_for_confirmation(state: TodoAgentState) -> Dict:
    """等待用户确认节点。
    
    接受前端 resume 的数据并更新状态。
    """
    logger.info("=== wait_for_confirmation 节点 ===")
    
    # 触发中断，等待用户回复
    # 前端 resume 时传递的数据将作为 interrupt 的返回值
    decision = interrupt(None)
    
    logger.info(f"收到用户决策 (resume): {decision}")
    
    if not decision:
        return {"user_confirmed": False}
    
    # 根据决策更新状态
    # 兼容两种格式：
    # 1. 完整数据: {"confirmed": True, ...}
    # 2. 也是完整数据，前端直接把 ConfirmationCard 的表单传回来
    
    # 检查是否包含 confirmed 字段 (前端 ai.tsx 默认传 {confirmed: true})
    is_confirmed = decision.get("confirmed", False)
    
    if is_confirmed or decision.get("type") == "accept":
        # 如果用户修改了参数 (例如修改了时间)
        # 前端可能直接混在 decision 顶层，也可能在 args 里
        update_data = {}
        for k, v in decision.items():
            if k not in ["confirmed", "type", "_display_message"]:
                update_data[k] = v
                
        if "args" in decision:
            update_data.update(decision["args"])
            
        if update_data and state["pending_operation"]:
             logger.info(f"用户更新了参数: {update_data}")
             state["pending_operation"]["data"].update(update_data)
        
        return {"user_confirmed": True}
        
    elif decision.get("type") == "reject" or not is_confirmed:
        logger.info("用户拒绝了操作")
        return {"user_confirmed": False}
        
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
        elif action == "batch_create":
            result = _execute_batch_create(data, state)
        elif action == "query":
            result = _execute_query(data, state)
        elif action == "merge":
            result = _execute_merge(data, state)
        else:
            result = ToolResultBuilder.error(f"暂不支持操作: {action}")
        
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

# _get_user_id_from_state 已迁移到 app.ai.utils.state_helpers
# 为保持向后兼容，创建别名
_get_user_id_from_state = get_user_id


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


def _execute_batch_create(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行批量创建操作。
    
    用于处理用户在一条消息中提到多个待办的场景，如：
    "明天开会，后天出差"
    """
    from app.ai.tools.todo_tools import add_todo
    
    user_id = _get_user_id_from_state(state)
    config = RunnableConfig(configurable={"user_id": user_id})
    
    todos = data.get("todos", [])
    if not todos:
        return ToolResultBuilder.error("没有待创建的待办项")
    
    created = []
    failed = []
    
    for todo_data in todos:
        try:
            due_date = todo_data.get("time") or todo_data.get("due_date")
            result_str = add_todo.invoke({
                "title": todo_data.get("title", "新待办"),
                "description": todo_data.get("description", ""),
                "priority": _parse_priority(todo_data.get("priority")),
                "due_date": due_date,
                "category": todo_data.get("category"),
                "tags": todo_data.get("tags"),
                "reminder_enabled": todo_data.get("reminder_enabled", False),
                "config": config
            })
            created.append(todo_data.get("title", "新待办"))
            logger.info(f"批量创建: 成功创建 '{todo_data.get('title')}'")
        except Exception as e:
            failed.append(todo_data.get("title", "未知"))
            logger.exception(f"批量创建失败: {todo_data.get('title')}, 错误: {e}")
    
    # 汇总结果
    if created and not failed:
        return ToolResultBuilder.success(
            f"成功创建 {len(created)} 个待办：{', '.join(created)}"
        )
    elif created and failed:
        return ToolResultBuilder.success(
            f"部分成功：创建了 {len(created)} 个，失败 {len(failed)} 个\n"
            f"成功：{', '.join(created)}\n"
            f"失败：{', '.join(failed)}"
        )
    else:
        return ToolResultBuilder.error(f"批量创建失败：{', '.join(failed)}")


def _execute_update(data: Dict, state: TodoAgentState) -> ToolResult:
    """执行更新操作。
    
    注意：必须提供 todo_id。ID 解析应在 resolve_entity 阶段完成。
    如果缺失 todo_id，将返回系统错误。
    """
    from app.ai.tools.todo_tools import update_todo
    
    user_id = _get_user_id_from_state(state)
    config = RunnableConfig(configurable={"user_id": user_id})
    
    todo_id = data.get("todo_id")
    
    # 如果没有 todo_id，直接报错 (ID 解析应在 resolve 阶段完成)
    if not todo_id:
        return ToolResultBuilder.error("系统错误：缺失待办 ID (请先尝试解析该任务)")
    
    try:
        result_str = update_todo.invoke({
            "todo_id": todo_id,
            "title": data.get("new_title"),  # 注意：更新时使用 new_title
            "description": data.get("description"),
            "priority": _parse_priority(data.get("priority")),
            "due_date": data.get("due_date") or data.get("time"),
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
    
    if not data.get("todo_id"):
        return ToolResultBuilder.error("系统错误：缺失待办 ID (请先尝试解析该任务)")
    
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

def route_next(state: TodoAgentState) -> Literal["clarify", "decompose", "conflict", "resolve", "execute", "summarize", "end"]:
    """路由到下一个节点 - 增强版。
    
    流程优先级:
    0. 汇总请求 → summarize
    1. 有待办 + 需要澄清 → clarify (澄清完会再次进入 analyze)
    2. 纯澄清 (无待办) → clarify
    3. 有复杂任务 → decompose
    4. 有待办需要冲突检测 → conflict
    5. 有待办需要实体解析 → resolve（新增）
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
    
    # 5. 有待办需要实体解析或确认 → resolve（新流程）
    if state.get("pending_operation"):
        logger.info("路由到: resolve (实体解析)")
        return "resolve"
    
    # 6. 默认执行
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
    workflow.add_node("resolve", resolve_entity)              # 新增：实体解析节点
    workflow.add_node("confirm", ask_confirmation)           # 发送确认消息
    workflow.add_node("wait_confirm", wait_for_confirmation) # 等待用户决策
    workflow.add_node("execute", execute_operation)
    workflow.add_node("summarize", summarize_node)  # 汇总节点
    
    # === 设置入口 ===
    workflow.set_entry_point("analyze")
    
    # === 设置边 ===
    
    # analyze → 条件路由 (clarify/decompose/conflict/resolve/execute)
    workflow.add_conditional_edges(
        "analyze",
        route_next,
        {
            "clarify": "clarify",
            "decompose": "decompose",
            "conflict": "conflict",
            "resolve": "resolve",  # 新增：实体解析路由
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
    
    # conflict → resolve (改为先解析再确认)
    workflow.add_conditional_edges(
        "conflict",
        lambda state: "resolve" if state.get("pending_operation") else "execute",
        {
            "resolve": "resolve",
            "execute": "execute"
        }
    )
    
    # resolve → 条件路由 (clarify/confirm/execute)
    workflow.add_conditional_edges(
        "resolve",
        route_after_resolve,
        {
            "clarify": "clarify",
            "confirm": "confirm",
            "execute": "execute"
        }
    )
    
    # confirm → wait_confirm (发送消息后等待)
    workflow.add_edge("confirm", "wait_confirm")
    
    # wait_confirm → execute (收到决策后执行)
    #注意：如果用户拒绝，execute_node 会处理 user_confirmed=False 的情况并取消
    workflow.add_edge("wait_confirm", "execute")
    
    # execute → END
    workflow.add_edge("execute", END)
    
    # === 编译图 ===
    # 允许外部传入 checkpointer，以便在多智能体集成时共享或使用持久化存储
    if checkpointer is None:
        checkpointer = MemorySaver()
        
    # 注意：使用 wait_for_confirmation 内部的 interrupt() 实现暂停
    graph = workflow.compile(
        checkpointer=checkpointer
    )
    
    logger.info("待办Agent Graph (多轮对话增强版) 创建成功")
    return graph
