"""待办意图分析辅助函数（中文注释）。

从 todo_graph.py 的 analyze_intent 函数中拆分出的辅助函数。
目的：提升代码可读性和可测试性。

设计原则：
1. 辅助函数接收必要参数，返回处理结果
2. 不直接修改 state，而是返回需要更新的数据
3. 便于单元测试
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


# ==================== 消息过滤 ====================

def filter_messages_for_todo(
    messages: List[BaseMessage], 
    pending_handoff: Optional[Dict] = None
) -> Tuple[List[BaseMessage], str, Optional[Dict]]:
    """过滤消息并构建 Handoff 上下文。
    
    Args:
        messages: 原始消息列表
        pending_handoff: 来自 Supervisor 的 Handoff 信息
        
    Returns:
        (过滤后的消息列表, Handoff 上下文字符串, 预提取的 extracted_info)
    """
    from app.ai.protocol import MessageFilter
    import re
    
    # 待办相关的安全工具白名单
    SAFE_TOOLS = {'add_todo', 'list_todos', 'update_todo', 'complete_todo', 'delete_todo', 'update_progress'}
    
    filtered_messages = MessageFilter.filter_for_tool_whitelist(messages, SAFE_TOOLS)
    
    # 构建 Handoff 上下文 + 解析结构化信息
    handoff_context = ""
    pre_extracted_info = None
    
    if pending_handoff:
        task_desc = pending_handoff.get("task_description", "")
        if task_desc:
            handoff_context = f"\n\n## 任务来源 (Supervisor Handoff)\n用户意图已由 Supervisor 预识别：{task_desc}\n请基于此描述进行操作。"
            
            # 从 task_description 中解析结构化信息
            pre_extracted_info = {}
            
            # 解析标题
            title_match = re.search(r'标题[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if title_match:
                pre_extracted_info["title"] = title_match.group(1).strip()
            
            # 解析时间
            time_match = re.search(r'时间[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if time_match:
                pre_extracted_info["time"] = time_match.group(1).strip()
            
            # 解析地点
            location_match = re.search(r'地点[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if location_match:
                pre_extracted_info["location"] = location_match.group(1).strip()
            
            # 解析参与人员
            participants_match = re.search(r'参与人员[：:]\s*(.+?)(?:\n|$|-)', task_desc)
            if participants_match:
                pre_extracted_info["participants"] = [p.strip() for p in participants_match.group(1).split('、')]
            
            if pre_extracted_info:
                logger.info(f"从 Handoff 预提取信息: {pre_extracted_info}")
    
    return filtered_messages, handoff_context, pre_extracted_info


# ==================== 历史任务查询 ====================

def query_existing_todos(user_id: int, limit: int = 10) -> str:
    """查询用户现有待办列表。
    
    Args:
        user_id: 用户 ID
        limit: 返回的最大条数
        
    Returns:
        格式化的待办列表上下文字符串，用于注入到提示词中
    """
    from app.db.session import get_db_context
    from app.repositories.todo_repository import todo_repo
    
    try:
        with get_db_context() as db:
            existing_todos = todo_repo.list_by_user(db, user_id, status="pending")
            if not existing_todos:
                return ""
            
            todo_list = []
            for t in existing_todos[:limit]:
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


# ==================== 时间解析 ====================

def parse_time_info(extracted_info: Dict, state_time_constraints: Optional[Dict] = None) -> Tuple[Dict, Optional[Dict]]:
    """解析时间信息并提取约束。
    
    Args:
        extracted_info: LLM 提取的信息
        state_time_constraints: 现有的时间约束
        
    Returns:
        (更新后的 extracted_info, 更新后的 time_constraints)
    """
    from app.services.time_parser import NaturalTimeParser
    
    time_parser = NaturalTimeParser()
    
    raw_time = extracted_info.get("time") or extracted_info.get("due_date")
    if not raw_time or not isinstance(raw_time, str):
        return extracted_info, state_time_constraints
    
    parsed_time, meta = time_parser.parse(raw_time)
    if parsed_time:
        extracted_info["due_date"] = parsed_time.isoformat()
        extracted_info["original_time"] = meta.get("original_text")
        logger.info(f"时间解析: '{raw_time}' -> {extracted_info['due_date']}")
    
    # 提取约束 (如 "周一不可用")
    constraints = meta.get("constraints")
    if constraints:
        current_constraints = state_time_constraints or {}
        if "blocked_weekdays" in constraints:
            current_blocked = set(current_constraints.get("blocked_weekdays", []))
            current_blocked.update(constraints["blocked_weekdays"])
            current_constraints["blocked_weekdays"] = list(current_blocked)
        logger.info(f"解析到时间约束: {constraints}")
        return extracted_info, current_constraints
    
    return extracted_info, state_time_constraints


# ==================== 紧急任务检测 ====================

def detect_urgent_task(
    messages: List[BaseMessage], 
    intent: str, 
    extracted_info: Dict,
    user_id: Optional[int] = None
) -> Dict:
    """检测紧急任务并更新提取信息。
    
    Args:
        messages: 消息列表
        intent: 当前意图
        extracted_info: 已提取的信息
        user_id: 用户 ID（用于查询受影响的任务）
        
    Returns:
        更新后的 extracted_info
    """
    # 获取最后一条用户消息
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            last_user_msg = msg.content
            break
    
    urgent_keywords = ["刚刚", "紧急", "立刻", "马上", "领导说", "老板说", "赶紧"]
    is_urgent = any(kw in last_user_msg for kw in urgent_keywords)
    
    if not is_urgent or intent != "create":
        return extracted_info
    
    # 自动提升优先级
    extracted_info["priority"] = 1
    extracted_info["is_urgent"] = True
    logger.info("检测到紧急任务，自动提升为高优先级")
    
    # 检查同一天是否有其他任务可能受影响
    due_date = extracted_info.get("due_date")
    if due_date and user_id:
        try:
            from app.db.session import get_db_context
            from app.repositories.todo_repository import todo_repo
            
            if isinstance(due_date, str):
                new_due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            else:
                new_due = due_date
            
            with get_db_context() as db:
                existing_todos = todo_repo.list_by_user(db, user_id, status="todo")
                
                affected_tasks = []
                for todo in existing_todos:
                    if todo.due_date and todo.due_date.date() == new_due.date():
                        if todo.priority >= 2:  # 中低优先级
                            affected_tasks.append(todo.title)
                
                if affected_tasks:
                    extracted_info["affected_tasks"] = affected_tasks
                    logger.info(f"紧急任务可能影响: {affected_tasks}")
        except Exception as e:
            logger.warning(f"检查受影响任务失败: {e}")
    
    return extracted_info


# ==================== 意图处理结果 ====================

class IntentProcessResult:
    """意图处理结果，用于返回需要更新的 state 字段。"""
    
    def __init__(self):
        self.updates: Dict[str, Any] = {}
        self.should_return_early: bool = False
    
    def set(self, key: str, value: Any):
        """设置需要更新的字段。"""
        self.updates[key] = value
        return self
    
    def early_return(self):
        """标记应该提前返回。"""
        self.should_return_early = True
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return self.updates


def process_clarify_intent(
    analysis: Dict, 
    extracted_info: Dict
) -> IntentProcessResult:
    """处理 clarify 意图。
    
    生成友好的追问消息，避免显示原始 JSON。
    
    Args:
        analysis: LLM 分析结果
        extracted_info: 提取的信息
        
    Returns:
        IntentProcessResult 包含需要更新的字段（包括 messages）
    """
    from langchain_core.messages import AIMessage
    
    result = IntentProcessResult()
    
    # 检查是否有部分待办信息
    has_partial_todo = (
        extracted_info.get("title") or 
        extracted_info.get("time") or 
        extracted_info.get("description")
    )
    
    missing_info = analysis.get("missing_info", [])
    questions = analysis.get("questions", [])
    
    if has_partial_todo:
        # 场景A: 有部分待办信息但需要补充
        # 生成确认式消息
        title = extracted_info.get("title") or "待办事项"
        time_str = extracted_info.get("time") or extracted_info.get("due_date") or ""
        
        lines = [f"好的，我帮你记录这个待办 📝", ""]
        lines.append(f"**{title}**")
        if time_str:
            lines.append(f"- ⏰ 时间：{time_str}")
        lines.append("")
        lines.append("您可以：")
        lines.append("1. 回复「**确认**」直接创建")
        lines.append("2. 补充更多信息（如优先级、详细描述等）")
        
        clarify_msg = "\n".join(lines)
        
        result.set("messages", [AIMessage(content=clarify_msg)])
        result.set("pending_operation", {
            "action": "create",
            "data": extracted_info,
            "needs_clarification": True
        })
        result.set("pending_clarifications", missing_info)
        result.set("conversation_context", analysis.get("context_hints", {}))
        logger.info(f"部分待办信息，生成确认消息: {title}")
    else:
        # 场景B: 纯澄清，无待办信息
        # 生成友好的追问消息
        if questions:
            clarify_msg = "我需要了解更多信息：\n\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        elif missing_info:
            clarify_msg = "请补充以下信息：\n\n" + "\n".join([f"• {m}" for m in missing_info])
        else:
            clarify_msg = "请告诉我具体需要完成什么任务？"
        
        result.set("messages", [AIMessage(content=clarify_msg)])
        result.set("pending_clarifications", missing_info)
        result.set("conversation_context", analysis.get("context_hints", {}))
        
        # 多项目队列填充
        projects = analysis.get("projects", [])
        if projects and len(projects) > 1:
            result.set("project_queue", projects)
            result.set("current_project_index", 0)
            result.set("active_projects", projects)
            logger.info(f"识别到多项目: {projects}")
        else:
            logger.info(f"纯澄清模式，生成追问消息")
    
    return result.early_return()


def process_confirm_intent(
    pending_operation: Optional[Dict],
    extracted_info: Dict
) -> IntentProcessResult:
    """处理 confirm 意图。
    
    Args:
        pending_operation: 当前待确认的操作
        extracted_info: 提取的信息
        
    Returns:
        IntentProcessResult 包含需要更新的字段
    """
    result = IntentProcessResult()
    
    if pending_operation and pending_operation.get("needs_clarification"):
        # 用户确认了，移除 needs_clarification 标记
        pending_operation["needs_clarification"] = False
        result.set("pending_operation", pending_operation)
        result.set("user_confirmed", True)
        logger.info(f"用户确认创建: {pending_operation['data'].get('title')}")
    elif extracted_info and (extracted_info.get("title") or extracted_info.get("time")):
        # 从 extracted_info 重建 pending_operation
        logger.info(f"从 extracted_info 重建 pending_operation: {extracted_info}")
        result.set("pending_operation", {
            "action": "create",
            "data": extracted_info,
            "needs_clarification": False,
        })
        result.set("user_confirmed", True)
    else:
        logger.warning("收到 confirm 意图但无 pending_operation")
        result.set("pending_operation", None)
    
    return result.early_return()


def process_batch_create_intent(extracted_info: Dict) -> IntentProcessResult:
    """处理 batch_create 意图。"""
    result = IntentProcessResult()
    
    todos = extracted_info.get("todos", [])
    if todos:
        result.set("draft_todos", todos)
        result.set("pending_operation", {
            "action": "batch_create",
            "data": {"count": len(todos), "todos": todos}
        })
        logger.info(f"批量创建: {len(todos)} 个待办")
    
    return result.early_return()


def process_summarize_intent() -> IntentProcessResult:
    """处理 summarize 意图。"""
    result = IntentProcessResult()
    
    result.set("pending_operation", {
        "action": "summarize",
        "data": {},
        "skip_confirmation": True
    })
    logger.info("识别到汇总请求")
    
    return result.early_return()


def process_constraint_intent(
    extracted_info: Dict, 
    current_time_constraints: Optional[Dict]
) -> IntentProcessResult:
    """处理 constraint 意图。"""
    result = IntentProcessResult()
    
    ext_constraints = extracted_info.get("constraints", {})
    if ext_constraints:
        current_constraints = current_time_constraints or {}
        current_constraints.update(ext_constraints)
        result.set("time_constraints", current_constraints)
        logger.info(f"更新时间约束: {ext_constraints}")
    
    return result.early_return()


def determine_confirmation_need(
    intent: str, 
    quick_mode: bool,
    extracted_info: Optional[Dict] = None
) -> Tuple[bool, bool]:
    """判断是否需要确认和是否需要先澄清。
    
    优化策略：
    - 如果标题已明确，直接确认，不再追问补充信息
    - 仅当标题缺失或过于模糊时才要求澄清
    
    Args:
        intent: 意图类型
        quick_mode: 是否快速模式
        extracted_info: 提取的信息（用于判断信息完整度）
        
    Returns:
        (needs_confirmation, needs_clarification)
    """
    if quick_mode:
        logger.info("快速模式:跳过确认")
        return False, False
    
    if intent == "create":
        # 检查标题是否明确
        if extracted_info:
            title = (extracted_info.get("title") or "").strip()
           
            # 标题明确且不模糊 -> 只需确认，不需要澄清
            vague_keywords = ["这个", "那个", "它", "东西", "事情"]
            is_vague = (
                not title or  # 标题为空
                len(title) < 2 or  # 标题太短（但允许单字如"会"）
                any(title == kw for kw in vague_keywords)  # 完全等于模糊词
            )
            
            if is_vague:
                logger.info(f"创建操作: 标题模糊 (title='{title}')，需要澄清")
                return True, True
            else:
                logger.info(f"创建操作: 标题明确 (title='{title}')，只需确认")
                return True, False
        
        # 没有 extracted_info，默认需要澄清
        logger.info("创建操作: 无信息，需要澄清")
        return True, True
    
    if intent in ["delete", "update", "batch_complete", "merge"]:
        return True, False
    
    if intent in ["query", "complete"]:
        return False, False
    
    return False, False
