"""待办助手 Agent - 任务管理专家（中文注释）- 升级版。

专注于待办事项的创建、查询、更新、进度跟踪和完成。
支持分类、标签、提醒等高级功能。
"""
import logging
from langchain.agents import create_agent

from app.ai.llm_util import get_llm

logger = logging.getLogger(__name__)

# 待办助手 Agent 系统提示词（升级版）
from app.ai.prompts.todo_prompts import TODO_AGENT_SYSTEM_PROMPT


def create_todo_agent(
    model=None, 
    enable_thinking: bool = False, 
    model_id: str = None,
    use_graph: bool = True  # 新增：默认使用 LangGraph
):
    """创建待办助手 Agent 实例（升级版）。
    
    Args:
        model: 可选，指定 LLM 实例。如果为 None，则自动创建
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识
        use_graph: 是否使用 LangGraph（默认 True）
        
    Returns:
        编译后的 Agent 实例（LangGraph）或 create_agent 实例
    """
    if use_graph:
        # 使用 LangGraph 实现
        logger.info("创建 LangGraph 待办 Agent")
        from app.ai.workflow.todo_graph import create_todo_graph
        return create_todo_graph(model, enable_thinking, model_id)
    
    # 以下是原有的 create_agent 实现（向后兼容）
    if model is None:
        model = get_llm(force_thinking=enable_thinking, model_id=model_id)
    
    # 加载待办管理工具（升级版）
    tools = []
    try:
        from app.ai.tools.todo_tools import (
            add_todo, 
            list_todos, 
            update_progress,
            update_todo,
            complete_todo, 
            delete_todo
        )
        from app.ai.tools.batch_todo_tools import batch_complete_todos
        
        tools = [
            add_todo, 
            list_todos, 
            update_progress,
            update_todo,
            complete_todo, 
            delete_todo,
            batch_complete_todos
        ]
        logger.info("待办管理工具已加载（升级版），工具数量: %d", len(tools))
    except ImportError as e:
        logger.warning("待办工具导入失败: %s", e)
    
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=TODO_AGENT_SYSTEM_PROMPT,
        name="todo_agent",
    )
    
    logger.info("待办助手 Agent 创建完成（升级版）")
    return agent
