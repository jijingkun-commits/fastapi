"""对比 LangChain stream_mode 下 tool_calls 的差异。

运行方法：
    python app/ai/test_stream_modes.py
"""
import asyncio
import os

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI


@tool
def knowledge_search(query: str) -> str:
    """搜索知识库获取相关信息。
    
    Args:
        query: 搜索关键词
    """
    return f"知识库搜索结果: 关于 '{query}' 的信息..."


@tool  
def weather_search(city: str, date: str = "今天") -> str:
    """查询指定城市的天气。
    
    Args:
        city: 城市名称
        date: 日期，默认为今天
    """
    return f"{city} {date} 天气晴朗，温度 15-22 度"


async def test_stream_modes():
    """测试不同 stream_mode 下 tool_calls 的数据结构。"""
    
    # 直接使用 DeepSeek API
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key="sk-07b7fae4b8dc4d1fb4c9539e59def338",
        base_url="https://api.deepseek.com/v1",
        streaming=True,
    )
    print("✅ 使用 DeepSeek Chat")
    
    # 创建 Agent
    agent = create_react_agent(
        model=llm,
        tools=[knowledge_search, weather_search],
    )
    
    test_input = {"messages": [HumanMessage(content="帮我查一下公司报销规定")]}
    
    print("\n" + "="*70)
    print("🔬 测试 stream_mode='messages' 模式")
    print("="*70)
    
    messages_tool_calls = []
    async for mode, chunk in agent.astream(test_input, stream_mode=["messages"]):
        if mode == "messages" and isinstance(chunk, tuple):
            msg, _ = chunk
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get('name', '')
                    args = tc.get('args', {})
                    if name:  # 只记录有名称的
                        print(f"\n📦 [messages] tool_call:")
                        print(f"   type(msg): {type(msg).__name__}")
                        print(f"   name: '{name}'")
                        print(f"   args: {args}")
                        print(f"   id: {tc.get('id', 'N/A')}")
                        messages_tool_calls.append(tc)
    
    print("\n" + "="*70)
    print("🔬 测试 stream_mode='values' 模式")
    print("="*70)
    
    # 重新测试
    test_input2 = {"messages": [HumanMessage(content="帮我查一下公司报销规定")]}
    
    values_tool_calls = []
    async for mode, chunk in agent.astream(test_input2, stream_mode=["values"]):
        if mode == "values":
            messages = chunk.get("messages", [])
            for msg in messages:
                if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        # 去重
                        tc_id = tc.get('id')
                        name = tc.get('name', '')
                        if tc_id and name and not any(t.get('id') == tc_id for t in values_tool_calls):
                            print(f"\n📦 [values] tool_call:")
                            print(f"   type(msg): {type(msg).__name__}")
                            print(f"   name: '{name}'")
                            print(f"   args: {tc.get('args', {})}")
                            print(f"   id: {tc_id}")
                            values_tool_calls.append(tc)
    
    print("\n" + "="*70)
    print("📊 对比结果")
    print("="*70)
    
    print(f"\n[messages 模式] 收到 {len(messages_tool_calls)} 个有效 tool_calls:")
    for i, tc in enumerate(messages_tool_calls):
        print(f"   [{i}] name='{tc.get('name', '')}' args={tc.get('args', {})}")
    
    print(f"\n[values 模式] 收到 {len(values_tool_calls)} 个有效 tool_calls:")
    for i, tc in enumerate(values_tool_calls):
        print(f"   [{i}] name='{tc.get('name', '')}' args={tc.get('args', {})}")
    
    print("\n" + "="*70)
    print("💡 结论")
    print("="*70)
    
    # 分析差异
    msg_has_args = any(tc.get('args') for tc in messages_tool_calls)
    val_has_args = any(tc.get('args') for tc in values_tool_calls)
    
    if val_has_args and not msg_has_args:
        print("\n✅ 验证通过: values 模式有完整参数，messages 模式参数为空")
        print("   解决方案: 应该从 values 模式获取工具调用参数，而不是 messages 模式")
    elif msg_has_args and val_has_args:
        print("\n🤔 两种模式都有参数（可能不同模型行为不同）")
    elif not msg_has_args and not val_has_args:
        print("\n⚠️ 两种模式都没有参数")
    else:
        print("\n📋 需要进一步分析")


if __name__ == "__main__":
    asyncio.run(test_stream_modes())
