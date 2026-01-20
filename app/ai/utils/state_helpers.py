"""状态辅助函数模块（中文注释）。

提供统一的状态访问和操作函数，避免各模块重复实现。
"""
import logging
from typing import Optional, Any, Dict

from langchain_core.runnables.config import RunnableConfig

logger = logging.getLogger(__name__)


def get_user_id(
    state: Dict[str, Any],
    config: Optional[RunnableConfig] = None
) -> int:
    """从 state 或 RunnableConfig 中获取 user_id。
    
    统一的 user_id 获取逻辑，优先级：
    1. state["user_id"] - 主要来源（由 graph 调用方传递）
    2. RunnableConfig.configurable["user_id"]
    3. state["pending_operation"]["user_id"]
    
    Args:
        state: Agent 状态字典
        config: RunnableConfig（可选）
        
    Returns:
        int: 用户 ID
        
    Raises:
        ValueError: 如果无法获取 user_id
    """
    # 优先从 state 直接读取
    user_id = state.get("user_id")
    if user_id is not None:
        return int(user_id)
    
    # 尝试从 RunnableConfig 获取
    if config:
        configurable = getattr(config, "configurable", None) or config.get("configurable", {})
        if isinstance(configurable, dict):
            user_id = configurable.get("user_id")
            if user_id is not None:
                return int(user_id)
    
    # 尝试从 pending_operation 中获取
    pending_op = state.get("pending_operation")
    if pending_op and isinstance(pending_op, dict) and "user_id" in pending_op:
        return int(pending_op["user_id"])
    
    # 无法获取时抛出异常
    error_msg = (
        "无法获取 user_id：请确保在调用 graph 时传递 user_id 参数，"
        "例如 graph.ainvoke({'messages': [...], 'user_id': 1})"
    )
    logger.error(error_msg)
    raise ValueError(error_msg)


def get_user_id_optional(
    state: Dict[str, Any],
    config: Optional[RunnableConfig] = None
) -> Optional[int]:
    """获取 user_id 的非抛异常版本。
    
    与 get_user_id 相同的逻辑，但找不到时返回 None 而非抛异常。
    适用于非关键路径。
    """
    try:
        return get_user_id(state, config)
    except ValueError:
        return None


def get_current_todo_id(
    state: Dict[str, Any],
    config: Optional[RunnableConfig] = None
) -> Optional[int]:
    """获取当前讨论的待办 ID。
    
    优先级：
    1. RunnableConfig.configurable["current_todo_id"]
    2. state["current_focus_todo_id"]
    3. state["pending_operation"]["todo_id"]
    """
    # 从 config 获取
    if config:
        configurable = getattr(config, "configurable", None) or config.get("configurable", {})
        if isinstance(configurable, dict):
            todo_id = configurable.get("current_todo_id")
            if todo_id is not None:
                return int(todo_id)
    
    # 从 state 获取
    todo_id = state.get("current_focus_todo_id")
    if todo_id is not None:
        return int(todo_id)
    
    # 从 pending_operation 获取
    pending_op = state.get("pending_operation")
    if pending_op and isinstance(pending_op, dict):
        todo_id = pending_op.get("todo_id") or pending_op.get("data", {}).get("todo_id")
        if todo_id is not None:
            return int(todo_id)
    
    return None
