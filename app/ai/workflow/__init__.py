"""Workflow 模块初始化（中文注释）。

本模块包含所有 LangGraph 图定义，便于统一管理和导入。
"""
from app.ai.workflow.chat_graph import get_chat_graph, create_chat_graph, AgentState
from app.ai.workflow.multi_agent_graph import get_multi_agent_graph, create_multi_agent_graph

__all__ = [
    "get_chat_graph", 
    "create_chat_graph", 
    "AgentState",
    "get_multi_agent_graph",
    "create_multi_agent_graph",
]


