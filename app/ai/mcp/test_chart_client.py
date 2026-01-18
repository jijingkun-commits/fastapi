"""MCP 图表客户端测试脚本（中文注释）。

测试 MCP 图表服务器连接和工具加载功能。
运行前请确保 mcp-server-chart 服务已启动（端口 1122）。
"""
import asyncio
import sys
import traceback

# 将项目根目录添加到 Python 路径
sys.path.insert(0, "/Users/jijingkun/bojxAI/fastapi")

from app.ai.mcp import load_chart_tools, get_mcp_chart_config


async def test_mcp_connection():
    """测试 MCP 图表服务连接。"""
    print("=" * 50)
    print("MCP 图表服务客户端测试")
    print("=" * 50)
    
    # 显示配置信息
    config = get_mcp_chart_config()
    print(f"\n服务器配置:")
    print(f"  - 服务器名称: chart_server")
    print(f"  - 传输协议: {config['chart_server']['transport']}")
    print(f"  - 服务器 URL: {config['chart_server']['url']}")
    print(f"  - 连接超时: {config['chart_server']['timeout']}s")
    
    # 尝试加载工具
    print(f"\n正在连接 MCP 服务器...")
    try:
        tools = await load_chart_tools()
        
        if tools:
            print(f"\n✅ 成功加载 {len(tools)} 个工具:")
            for i, tool in enumerate(tools, 1):
                print(f"\n  {i}. {tool.name}")
                if hasattr(tool, "description"):
                    desc = tool.description or ""
                    print(f"     描述: {desc[:100]}..." if len(desc) > 100 else f"     描述: {desc}")
        else:
            print("\n⚠️  未加载到任何工具（服务可能未启动或无可用工具）")
            
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print("\n详细错误信息:")
        traceback.print_exc()
        print("\n请确保:")
        print("  1. mcp-server-chart 服务已启动")
        print("  2. 服务运行在端口 1122")
        print("  3. 检查正确的 SSE 端点路径（常见路径: /sse, /mcp, /events）")
        print(f"\n当前配置的 URL: {config['chart_server']['url']}")
        print("如需修改，请设置环境变量 MCP_CHART_SERVER_URL")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
