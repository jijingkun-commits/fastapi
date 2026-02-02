"""Workflow 模块初始化（中文注释）。

本模块包含所有 LangGraph 图定义，便于统一管理和导入。

注意：单智能体模式 (chat_graph.py) 已废弃（2026-01-31），
备份见 docs/开发文档/归档备份/单智能体模式备份.md
"""
from app.ai.workflow.multi_agent_graph import get_multi_agent_graph, create_multi_agent_graph, MultiAgentState

__all__ = [
    "get_multi_agent_graph",
    "create_multi_agent_graph",
    "MultiAgentState",
]


