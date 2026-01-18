"""MCP 客户端模块（中文注释）。

本模块提供 MCP（Model Context Protocol）服务器的客户端封装。
支持连接各类 MCP 服务并加载其提供的工具。
"""
from app.ai.mcp.chart_client import (
    get_mcp_client,
    load_chart_tools,
    get_cached_chart_tools,
    call_chart_tool,
    get_mcp_chart_config,
)

__all__ = [
    "get_mcp_client",
    "load_chart_tools",
    "get_cached_chart_tools",
    "call_chart_tool",
    "get_mcp_chart_config",
]
