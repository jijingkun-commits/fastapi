"""批量待办操作工具（中文注释）。

提供批量完成待办的工具。
"""
import logging
from typing import List

from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.runnables.config import RunnableConfig

logger = logging.getLogger(__name__)


class BatchCompleteTodosInput(BaseModel):
    """批量完成待办输入参数。"""
    todo_ids: List[int] = Field(description="待办 ID 列表，例如 [1, 2, 3]")


def _get_user_id(config: RunnableConfig) -> int:
    """从 config 中提取 user_id。"""
    if config and "configurable" in config:
        return config["configurable"].get("user_id")
    return None


@tool(args_schema=BatchCompleteTodosInput)
def batch_complete_todos(todo_ids: List[int], config: RunnableConfig = None) -> str:
    """批量完成多个待办事项。
    
    一次性将多个待办任务标记为已完成。适用于完成一组相关任务或清理已完成工作。
    """
    user_id = _get_user_id(config)
    if not user_id:
        return "❌ 无法获取用户信息，请确保已登录"
    
    if not todo_ids:
        return "❌ 请提供要完成的待办 ID 列表"
    
    try:
        from app.db.session import get_db_context
        from app.repositories.todo_repository import todo_repo
        
        with get_db_context() as db:
            completed_count = todo_repo.batch_complete(db, todo_ids, user_id)
            
            if completed_count == 0:
                return f"❌ 未找到可完成的待办（ID: {', '.join(map(str, todo_ids))}）"
            elif completed_count == len(todo_ids):
                return f"🎉 成功完成 {completed_count} 个待办！\n\nID: {', '.join(map(str, todo_ids))}"
            else:
                return f"✅ 成功完成 {completed_count}/{len(todo_ids)} 个待办\n\nID: {', '.join(map(str, todo_ids[:completed_count]))}"
            
    except Exception as e:
        logger.exception("批量完成待办失败: %s", e)
        return f"❌ 批量完成失败: {str(e)}"
