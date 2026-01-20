"""汇总节点 - 生成按优先级分组的待办清单（中文注释）。

触发条件:
1. 用户明确请求 "给我清单/列表/按优先级"
2. 多轮对话结束时自动触发（当 draft_todos 非空时）
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from langchain_core.messages import AIMessage

from app.ai.state import TodoAgentState
from app.db.session import get_db_context
from app.repositories.todo_repository import TodoRepository
from app.ai.utils.state_helpers import get_user_id_optional

logger = logging.getLogger(__name__)

# 创建仓库实例
todo_repo = TodoRepository()


# ==================== 时间分组逻辑 ====================

def _get_time_group(due_date: Optional[datetime], now: datetime) -> str:
    """根据截止日期判断时间分组。"""
    if not due_date:
        return "unscheduled"
    
    # 计算时间差
    delta = due_date - now
    
    if delta.days < 0:
        return "overdue"  # 已过期
    elif delta.days == 0:
        return "today"  # 今天
    elif delta.days == 1:
        return "tomorrow"  # 明天
    elif delta.days <= 7:
        return "this_week"  # 本周
    elif delta.days <= 14:
        return "next_week"  # 下周
    else:
        return "later"  # 更远


def _format_due_date(due_date: Optional[datetime], now: datetime) -> str:
    """格式化截止日期为友好字符串。"""
    if not due_date:
        return "未设置"
    
    # 使用日历日期比较，而非 timedelta
    due_day = due_date.date()
    today = now.date()
    
    delta_days = (due_day - today).days
    
    if delta_days < 0:
        return f"已过期 {abs(delta_days)} 天"
    elif delta_days == 0:
        return f"今天 {due_date.strftime('%H:%M')}"
    elif delta_days == 1:
        return f"明天 {due_date.strftime('%H:%M')}"
    else:
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[due_date.weekday()]
        return f"{due_date.strftime('%m月%d日')} ({weekday})"



# ==================== 汇总节点 ====================

def summarize_node(state: TodoAgentState) -> TodoAgentState:
    """汇总节点 - 生成按优先级分组的待办清单。
    
    职责:
    1. 从 draft_todos 或数据库获取待办列表
    2. 按优先级和时间分组
    3. 生成结构化的 Markdown 清单
    """
    logger.info("=== summarize_node 节点 ===")
    
    now = datetime.now()
    
    # 获取待办列表 (优先从 draft_todos，否则查数据库)
    todos = []
    draft_todos = state.get("draft_todos", [])
    
    if draft_todos:
        # 使用对话中收集的草稿待办
        todos = draft_todos
        logger.info(f"使用 draft_todos: {len(todos)} 条")
    else:
        # 从数据库查询用户待办
        user_id = _get_user_id_from_state(state)
        if user_id:
            try:
                with get_db_context() as db:
                    db_todos = todo_repo.list_by_user(db, user_id, status="pending")
                    todos = [_todo_to_dict(t) for t in db_todos]
                    logger.info(f"从数据库查询到: {len(todos)} 条待办")
            except Exception as e:
                logger.error(f"查询待办失败: {e}")
    
    if not todos:
        state["messages"].append(AIMessage(
            content="📋 当前没有待处理的待办事项。"
        ))
        return state
    
    # 按优先级分组
    high_priority = []  # 优先级 1
    medium_priority = []  # 优先级 2
    low_priority = []  # 优先级 3 或更低
    
    for todo in todos:
        priority = todo.get("priority", 2)
        if priority == 1:
            high_priority.append(todo)
        elif priority == 2:
            medium_priority.append(todo)
        else:
            low_priority.append(todo)
    
    # 每组内按截止日期排序
    for group in [high_priority, medium_priority, low_priority]:
        group.sort(key=lambda t: t.get("due_date") or "9999-12-31")
    
    # 生成 Markdown 清单
    lines = ["## 📋 待办清单", ""]
    
    # 高优先级
    if high_priority:
        lines.append("### 🔴 高优先级")
        for i, todo in enumerate(high_priority, 1):
            due_str = _format_due_date(_parse_date(todo.get("due_date")), now)
            deps = todo.get("dependencies", [])
            dep_str = f" (依赖: {', '.join(deps)})" if deps else ""
            lines.append(f"{i}. **{todo.get('title')}** - 截止: {due_str}{dep_str}")
        lines.append("")
    
    # 中优先级
    if medium_priority:
        lines.append("### 🟡 中优先级")
        for i, todo in enumerate(medium_priority, 1):
            due_str = _format_due_date(_parse_date(todo.get("due_date")), now)
            deps = todo.get("dependencies", [])
            dep_str = f" (依赖: {', '.join(deps)})" if deps else ""
            lines.append(f"{i}. **{todo.get('title')}** - 截止: {due_str}{dep_str}")
        lines.append("")
    
    # 低优先级 / 暂缓
    if low_priority:
        lines.append("### 🔵 低优先级 / 暂缓")
        for i, todo in enumerate(low_priority, 1):
            due_str = _format_due_date(_parse_date(todo.get("due_date")), now)
            lines.append(f"{i}. {todo.get('title')} - {due_str}")
        lines.append("")
    
    # 统计信息
    total = len(todos)
    lines.append("---")
    lines.append(f"共 **{total}** 项待办 | 🔴 {len(high_priority)} 高 | 🟡 {len(medium_priority)} 中 | 🔵 {len(low_priority)} 低")
    
    summary_text = "\n".join(lines)
    state["messages"].append(AIMessage(content=summary_text))
    
    logger.info(f"生成待办清单: {total} 项")
    return state


# ==================== 辅助函数 ====================

# _get_user_id_from_state 已迁移到 app.ai.utils.state_helpers
# 为保持向后兼容，创建别名
_get_user_id_from_state = get_user_id_optional


def _todo_to_dict(todo) -> Dict:
    """将 ORM 对象转换为字典。"""
    return {
        "id": todo.id,
        "title": todo.title,
        "description": todo.description,
        "priority": todo.priority,
        "due_date": todo.due_date.isoformat() if todo.due_date else None,
        "status": todo.status,
        "category": todo.category,
    }


def _parse_date(date_val) -> Optional[datetime]:
    """解析日期值为 datetime 对象。"""
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, str):
        try:
            return datetime.fromisoformat(date_val.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


# ==================== 路由辅助函数 ====================

def should_summarize(state: TodoAgentState) -> bool:
    """判断是否应该触发汇总节点。
    
    触发条件:
    1. pending_operation 的 action 为 'summarize'
    2. draft_todos 非空且用户请求了清单
    """
    pending_op = state.get("pending_operation")
    if pending_op and pending_op.get("action") == "summarize":
        return True
    
    # 检查最后一条消息是否包含汇总请求关键词
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, "content") and isinstance(last_msg.content, str):
            summarize_keywords = ["清单", "列表", "按优先级", "汇总", "总结一下"]
            if any(kw in last_msg.content for kw in summarize_keywords):
                return True
    
    return False
