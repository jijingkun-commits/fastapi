"""简单测试 LangChain 工具调用结构。

运行方法：
    python app/ai/test_tool_calls.py
"""
import asyncio
import os
import sys

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()


@pytest.mark.asyncio
async def test_simple_agent():
    """使用简单的 agent 测试工具调用结构。"""
    if os.getenv("RUN_LIVE_TOOL_CALL_TESTS") != "1":
        pytest.skip("默认跳过联机 tool call 探针；如需执行请设置 RUN_LIVE_TOOL_CALL_TESTS=1")
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
    from langchain.agents import create_agent
    
    # 导入 LLM
    from app.ai.llm_util import get_scene_llm
    from app.ai.scene_registry import SCENE_KEY_KNOWLEDGE_AGENT_FACTORY
    
    llm = get_scene_llm(scene_key=SCENE_KEY_KNOWLEDGE_AGENT_FACTORY, force_thinking=False)
    
    # 创建测试工具
    @tool
    def test_search(query: str) -> str:
        """搜索知识库。"""
        return f"搜索结果: {query}"
    
    # 创建简单 agent
    agent = create_agent(
        model=llm,
        tools=[test_search],
        system_prompt="你是一个助手，使用工具回答问题。"
    )
    
    test_input = {
        "messages": [HumanMessage(content="帮我搜索一下天气")],
    }
    
    print("\n" + "="*60)
    print("🔍 测试 LangChain Agent 工具调用结构")
    print("="*60 + "\n")
    
    # 测试 astream
    async for mode, chunk in agent.astream(
        test_input, 
        stream_mode=["messages", "values"]
    ):
        if mode == "messages":
            if isinstance(chunk, tuple) and len(chunk) == 2:
                msg, metadata = chunk
                
                if isinstance(msg, (AIMessage, AIMessageChunk)):
                    tool_calls = getattr(msg, 'tool_calls', None)
                    if tool_calls:
                        print(f"\n📦 [messages] 检测到 {len(tool_calls)} 个 tool_calls:")
                        for i, tc in enumerate(tool_calls):
                            print(f"   [{i}] type: {type(tc)}")
                            if isinstance(tc, dict):
                                print(f"       name: '{tc.get('name', 'N/A')}'")
                                print(f"       args: {tc.get('args', 'N/A')}")
                                print(f"       id: {tc.get('id', 'N/A')}")
                            else:
                                print(f"       完整: {tc}")
        
        elif mode == "values":
            messages = chunk.get("messages", [])
            for msg in messages:
                if isinstance(msg, AIMessage):
                    tool_calls = getattr(msg, 'tool_calls', None)
                    if tool_calls:
                        print(f"\n📦 [values] 最终 state 中检测到 {len(tool_calls)} 个 tool_calls:")
                        for i, tc in enumerate(tool_calls):
                            print(f"   [{i}] name: '{tc.get('name', 'N/A')}'")
                            print(f"       args: {tc.get('args', 'N/A')}")
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_simple_agent())
