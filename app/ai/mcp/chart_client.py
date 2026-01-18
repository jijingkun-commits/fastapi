"""MCP 图表服务客户端模块（中文注释）。

本模块提供连接本地 MCP 图表生成服务的客户端。
使用 langchain-mcp-adapters 库通过 SSE 协议连接 MCP 服务器。
"""
import logging
from typing import Optional
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.core.config import MCP_CHART_SERVER_URL


logger = logging.getLogger(__name__)


# 全局 MCP 客户端实例（单例模式）
_mcp_client: Optional[MultiServerMCPClient] = None
_mcp_tools: list = []


def get_mcp_chart_config() -> dict:
    """获取 MCP 图表服务器配置。
    
    Returns:
        dict: MCP 服务器配置字典
    """
    return {
        "chart_server": {
            "transport": "sse",
            "url": MCP_CHART_SERVER_URL,
            "timeout": 30.0,  # 初始连接超时（秒）
            "sse_read_timeout": 300.0,  # SSE 保活超时（秒）
        }
    }


@asynccontextmanager
async def get_mcp_client():
    """获取 MCP 客户端上下文管理器。
    
    用于临时获取 MCP 客户端并在使用后自动清理。
    
    Yields:
        MultiServerMCPClient: MCP 客户端实例
    
    Example:
        async with get_mcp_client() as client:
            tools = await client.get_tools()
    """
    config = get_mcp_chart_config()
    client = MultiServerMCPClient(config)
    
    try:
        logger.info("正在连接 MCP 图表服务: %s", MCP_CHART_SERVER_URL)
        yield client
    finally:
        # 清理客户端资源（如果需要）
        logger.debug("MCP 客户端上下文关闭")


async def load_chart_tools() -> list:
    """加载图表 MCP 服务器提供的工具。
    
    Returns:
        list: LangChain 兼容的工具列表
    """
    global _mcp_tools
    
    try:
        async with get_mcp_client() as client:
            tools = await client.get_tools()
            _mcp_tools = tools
            
            # 记录加载的工具信息
            tool_names = [t.name for t in tools]
            logger.info("成功加载 %d 个 MCP 图表工具: %s", len(tools), tool_names)
            
            return tools
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        logger.error("加载 MCP 图表工具失败: %s", error_msg)
        return []


def get_cached_chart_tools() -> list:
    """获取缓存的图表工具列表。
    
    如果尚未加载工具，返回空列表。
    使用 load_chart_tools() 首次加载工具。
    
    Returns:
        list: 缓存的工具列表
    """
    return _mcp_tools


async def call_chart_tool(tool_name: str, **kwargs) -> dict:
    """直接调用图表工具。
    
    Args:
        tool_name: 工具名称
        **kwargs: 工具参数
        
    Returns:
        dict: 工具执行结果
    """
    async with get_mcp_client() as client:
        tools = await client.get_tools()
        
        # 查找指定工具
        target_tool = None
        for tool in tools:
            if tool.name == tool_name:
                target_tool = tool
                break
        
        if not target_tool:
            raise ValueError(f"未找到工具: {tool_name}")
        
        # 执行工具
        result = await target_tool.ainvoke(kwargs)
        logger.info("图表工具 %s 执行成功", tool_name)
        return result
