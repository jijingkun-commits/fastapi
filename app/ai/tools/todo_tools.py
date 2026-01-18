"""待办事项工具模块（中文注释）- 升级版。

提供待办助手 Agent 可调用的任务管理工具，支持完整的待办管理功能。
"""
import logging
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables.config import RunnableConfig

logger = logging.getLogger(__name__)


# ==================== Pydantic Schemas ====================

class AddTodoInput(BaseModel):
    """添加待办输入参数。"""
    title: str = Field(description="待办事项的标题，简洁明了")
    description: str = Field(default="", description="可选的详细描述")
    priority: int = Field(default=2, description="优先级：1=高, 2=中, 3=低")
    start_time: Optional[str] = Field(default=None, description="开始时间，格式：YYYY-MM-DD HH:MM")
    due_date: Optional[str] = Field(default=None, description="截止日期，格式：YYYY-MM-DD HH:MM")
    category: Optional[str] = Field(default=None, description="分类：工作/生活/学习等")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    reminder_enabled: bool = Field(default=False, description="是否启用提醒")
    reminder_advance_minutes: Optional[int] = Field(default=None, description="提前多少分钟提醒")


class ListTodosInput(BaseModel):
    """列出待办输入参数。"""
    status: Optional[str] = Field(default=None, description="状态过滤：todo/in_progress/done/cancelled/pending/completed")
    category: Optional[str] = Field(default=None, description="分类过滤")
    priority: Optional[int] = Field(default=None, description="优先级过滤：1=高, 2=中, 3=低")
    keyword: Optional[str] = Field(default=None, description="标题关键词搜索,模糊匹配")


class TodoIdInput(BaseModel):
    """待办 ID 输入参数。"""
    todo_id: int = Field(description="待办事项的 ID")


class UpdateProgressInput(BaseModel):
    """更新进度输入参数。"""
    todo_id: int = Field(description="待办事项的 ID")
    progress: int = Field(description="进度百分比 (0-100)")
    progress_notes: Optional[str] = Field(default=None, description="进展说明")


class UpdateTodoInput(BaseModel):
    """更新待办输入参数。"""
    todo_id: int = Field(description="待办事项的 ID")
    title: Optional[str] = Field(default=None, description="新标题")
    description: Optional[str] = Field(default=None, description="新描述")
    priority: Optional[int] = Field(default=None, description="新优先级")
    due_date: Optional[str] = Field(default=None, description="新截止日期")
    category: Optional[str] = Field(default=None, description="新分类")
    status: Optional[str] = Field(default=None, description="新状态")


# ==================== Helper Functions ====================

def _get_user_id(config: RunnableConfig) -> Optional[int]:
    """从 config 中提取 user_id。"""
    if config and "configurable" in config:
        return config["configurable"].get("user_id")
    return None


def _parse_datetime(date_str: str) -> Optional[datetime]:
    """解析日期时间字符串。"""
    if not date_str:
        return None
    
    # 支持多种格式
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m-%d %H:%M",  # 简写格式，自动补全年份
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # 如果是简写格式，补全当前年份
            if fmt == "%m-%d %H:%M":
                parsed = parsed.replace(year=datetime.now().year)
            return parsed
        except ValueError:
            continue
    
    raise ValueError(f"无法解析日期时间: {date_str}，支持格式：YYYY-MM-DD HH:MM 或 MM-DD HH:MM")


# ==================== Tools ====================

@tool(args_schema=AddTodoInput)
def add_todo(
    title: str, 
    description: str = "", 
    priority: int = 2, 
    start_time: str = None,
    due_date: str = None,
    category: str = None,
    tags: List[str] = None,
    reminder_enabled: bool = False,
    reminder_advance_minutes: int = None,
    config: RunnableConfig = None
) -> str:
    """创建一个新的待办事项。
    
    使用此工具为用户添加新的待办任务。支持设置标题、描述、优先级、时间、分类、标签和提醒。
    """
    user_id = _get_user_id(config)
    if not user_id:
        return "❌ 无法获取用户信息，请确保已登录"
    
    try:
        from app.db.session import get_db_context
        from app.repositories.todo_repository import todo_repo
        
        # 解析时间
        parsed_start_time = _parse_datetime(start_time) if start_time else None
        parsed_due_date = _parse_datetime(due_date) if due_date else None
        
        with get_db_context() as db:
            todo = todo_repo.create(
                db=db,
                user_id=user_id,
                title=title,
                description=description,
                priority=priority,
                start_time=parsed_start_time,
                due_date=parsed_due_date,
                category=category,
                tags=tags,
                reminder_enabled=reminder_enabled,
                reminder_advance_minutes=reminder_advance_minutes,
            )
            
            # 格式化响应
            priority_text = {1: "🔴高", 2: "🟡中", 3: "🟢低"}.get(priority, "中")
            time_info = []
            if parsed_start_time:
                time_info.append(f"开始：{parsed_start_time.strftime('%m-%d %H:%M')}")
            if parsed_due_date:
                time_info.append(f"截止：{parsed_due_date.strftime('%m-%d %H:%M')}")
            time_text = "\n".join(time_info) if time_info else ""
            
            category_text = f"\n分类：{category}" if category else ""
            tags_text = f"\n标签：{', '.join(tags)}" if tags else ""
            reminder_text = f"\n⏰ 提前 {reminder_advance_minutes} 分钟提醒" if reminder_enabled else ""
            
            return f"""✅ 待办已创建！

**{todo.title}** (ID: {todo.id})
优先级：{priority_text}{category_text}{tags_text}
{time_text}{reminder_text}
""".strip()
            
    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        logger.exception("创建待办失败: %s", e)
        return f"❌ 创建待办失败: {str(e)}"


@tool(args_schema=ListTodosInput)
def list_todos(
    status: str = None, 
    category: str = None,
    priority: int = None,
    keyword: str = None,  # ⬅️ 新增关键词搜索参数
    config: RunnableConfig = None
) -> str:
    """查看待办事项列表。
    
    列出用户的待办任务,支持按状态、分类、优先级、关键词过滤。
    """
    user_id = _get_user_id(config)
    if not user_id:
        return "❌ 无法获取用户信息,请确保已登录"
    
    try:
        from app.db.session import get_db_context
        from app.repositories.todo_repository import todo_repo
        
        # 默认只查询未完成的待办（在数据库层面过滤）
        effective_status = status if status else "pending"
        
        with get_db_context() as db:
            todos = todo_repo.list_by_user(
                db, 
                user_id, 
                status=effective_status,
                category=category,
                priority=priority,
                keyword=keyword
            )
            
            if not todos:
                filter_desc = []
                if status:
                    filter_desc.append(f"状态={status}")
                if category:
                    filter_desc.append(f"分类={category}")
                if priority:
                    filter_desc.append(f"优先级={priority}")
                if keyword:
                    filter_desc.append(f"关键词={keyword}")
                filter_text = f"（{', '.join(filter_desc)}）" if filter_desc else ""
                return f"📋 暂无待办事项{filter_text}"

            lines = ["📋 **待办事项列表**\n"]
            
            for todo in todos:
                # 状态图标
                status_icon = {
                    "todo": "⬜",
                    "in_progress": "◐",
                    "done": "✅",
                    "cancelled": "✗"
                }.get(todo.status, "⬜")
                
                # 优先级图标
                priority_icon = {1: "🔴", 2: "🟡", 3: "🟢"}.get(todo.priority, "")
                
                # 进度条
                if todo.progress > 0 and todo.status != "done":
                    progress_bar = "█" * (todo.progress // 10) + "░" * (10 - todo.progress // 10)
                    progress_text = f" {progress_bar} {todo.progress}%"
                else:
                    progress_text = ""
                
                # 时间信息
                time_parts = []
                if todo.due_date:
                    time_parts.append(f"截止: {todo.due_date.strftime('%m-%d %H:%M')}")
                time_text = f" | {', '.join(time_parts)}" if time_parts else ""
                
                # 分类标签
                category_text = f" [{todo.category}]" if todo.category else ""
                
                lines.append(
                    f"{status_icon} [{todo.id}] {priority_icon} {todo.title}{category_text}{time_text}{progress_text}"
                )
            
            # 统计信息
            status_counts = {
                "todo": len([t for t in todos if t.status == "todo"]),
                "in_progress": len([t for t in todos if t.status == "in_progress"]),
                "done": len([t for t in todos if t.status == "done"]),
            }
            
            lines.append(f"\n---")
            lines.append(f"共 {len(todos)} 项 | 待办 {status_counts['todo']} | 进行中 {status_counts['in_progress']} | 已完成 {status_counts['done']}")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.exception("查询待办失败: %s", e)
        return f"❌ 查询待办失败: {str(e)}"


@tool(args_schema=UpdateProgressInput)
def update_progress(
    todo_id: int,
    progress: int,
    progress_notes: str = None,
    config: RunnableConfig = None
) -> str:
    """更新待办事项的进度。
    
    更新任务的完成进度（0-100），可以添加进展说明。进度达到 100% 时自动标记为完成。
    """
    user_id = _get_user_id(config)
    if not user_id:
        return "❌ 无法获取用户信息，请确保已登录"
    
    if progress < 0 or progress > 100:
        return "❌ 进度必须在 0-100 之间"
    
    try:
        from app.db.session import get_db_context
        from app.repositories.todo_repository import todo_repo
        
        with get_db_context() as db:
            # 先获取待办信息
            todo = todo_repo.get_by_id(db, todo_id, user_id)
            if not todo:
                return f"❌ 未找到 ID 为 {todo_id} 的待办事项"
            
            success = todo_repo.update_progress(
                db, todo_id, user_id, progress, progress_notes
            )
            
            if success:
                # 刷新获取最新状态
                db.refresh(todo)
                
                progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
                notes_text = f"\n📝 {progress_notes}" if progress_notes else ""
                
                if progress >= 100:
                    return f"🎉 恭喜！**{todo.title}** 已完成！\n进度：{progress_bar} {progress}%{notes_text}"
                else:
                    status_text = "进行中 ◐" if progress > 0 else "待办 ⬜"
                    return f"✅ **{todo.title}** 进度已更新\n状态：{status_text}\n进度：{progress_bar} {progress}%{notes_text}"
            else:
                return f"❌ 更新进度失败"
            
    except Exception as e:
        logger.exception("更新进度失败: %s", e)
        return f"❌ 更新进度失败: {str(e)}"


@tool(args_schema=UpdateTodoInput)
def update_todo(
    todo_id: int,
    title: str = None,
    description: str = None,
    priority: int = None,
    due_date: str = None,
    category: str = None,
    status: str = None,
    config: RunnableConfig = None
) -> str:
    """更新待办事项的信息。
    
    可以更新标题、描述、优先级、截止日期、分类等信息。
    """
    user_id = _get_user_id(config)
    if not user_id:
        return "❌ 无法获取用户信息，请确保已登录"
    
    try:
        from app.db.session import get_db_context
        from app.repositories.todo_repository import todo_repo
        
        # 构建更新字段
        updates = {}
        if title:
            updates["title"] = title
        if description is not None:  # 允许设置为空字符串
            updates["description"] = description
        if priority:
            updates["priority"] = priority
        if due_date:
            updates["due_date"] = _parse_datetime(due_date)
        if category:
            updates["category"] = category
        if status:
            updates["status"] = status
            if status == "done":
                updates["actual_completion_time"] = datetime.now()
        
        if not updates:
            return "❌ 没有需要更新的字段"
        
        with get_db_context() as db:
            todo = todo_repo.update_fields(db, todo_id, user_id, **updates)
            
            if todo:
                update_desc = []
                if "title" in updates:
                    update_desc.append(f"标题：{title}")
                if "priority" in updates:
                    priority_text = {1: "🔴高", 2: "🟡中", 3: "🟢低"}.get(priority, "")
                    update_desc.append(f"优先级：{priority_text}")
                if "due_date" in updates:
                    update_desc.append(f"截止日期：{updates['due_date'].strftime('%m-%d %H:%M')}")
                if "status" in updates:
                    update_desc.append(f"状态：{status}")
                
                return f"✅ **{todo.title}** 已更新\n\n" + "\n".join(update_desc)
            else:
                return f"❌ 未找到 ID 为 {todo_id} 的待办事项"
            
    except ValueError as e:
        return f"❌ {str(e)}"
    except Exception as e:
        logger.exception("更新待办失败: %s", e)
        return f"❌ 更新待办失败: {str(e)}"


@tool(args_schema=TodoIdInput)
def complete_todo(todo_id: int, config: RunnableConfig = None) -> str:
    """标记待办事项为已完成。
    
    将指定 ID 的待办任务标记为完成状态，自动记录完成时间。
    """
    user_id = _get_user_id(config)
    if not user_id:
        return "❌ 无法获取用户信息，请确保已登录"
    
    try:
        from app.db.session import get_db_context
        from app.repositories.todo_repository import todo_repo
        
        with get_db_context() as db:
            # 先获取待办信息用于展示
            todo = todo_repo.get_by_id(db, todo_id, user_id)
            if not todo:
                return f"❌ 未找到 ID 为 {todo_id} 的待办事项"
            
            if todo.status == "done":
                return f"ℹ️ **{todo.title}** 已经是完成状态了"
            
            success = todo_repo.complete(db, todo_id, user_id)
            if success:
                return f"🎉 太棒了！**{todo.title}** 已完成！"
            else:
                return f"❌ 标记完成失败"
            
    except Exception as e:
        logger.exception("完成待办失败: %s", e)
        return f"❌ 完成待办失败: {str(e)}"


@tool(args_schema=TodoIdInput)
def delete_todo(todo_id: int, config: RunnableConfig = None) -> str:
    """删除待办事项。
    
    删除指定 ID 的待办任务。此操作会记录到历史日志中。
    """
    user_id = _get_user_id(config)
    if not user_id:
        return "❌ 无法获取用户信息，请确保已登录"
    
    try:
        from app.db.session import get_db_context
        from app.repositories.todo_repository import todo_repo
        
        with get_db_context() as db:
            # 先获取待办信息用于展示
            todo = todo_repo.get_by_id(db, todo_id, user_id)
            if not todo:
                return f"❌ 未找到 ID 为 {todo_id} 的待办事项"
            
            title = todo.title
            success = todo_repo.delete(db, todo_id, user_id)
            if success:
                return f"🗑️ 已删除待办: **{title}**"
            else:
                return f"❌ 删除失败"
            
    except Exception as e:
        logger.exception("删除待办失败: %s", e)
        return f"❌ 删除待办失败: {str(e)}"
