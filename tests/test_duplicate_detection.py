"""重复检测功能测试脚本。

验证用户创建重复任务时的交互流程：
1. 用户请求创建与现有任务相似的待办
2. 系统检测到相似任务并提示用户
3. 用户选择"仍需新建"后成功创建
"""
import asyncio
import logging
import os
import sys

# 添加项目根目录到 sys.path
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from app.ai.workflow.todo_graph import create_todo_graph
from app.services.llm_config_service import LLMConfigService

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 测试用例
TEST_ROUNDS = [
    # Round 1: 请求创建一个与现有任务完全匹配的待办
    "帮我加一个 AI + 金融场景落地简要说明 的待办",
    # Round 2: 用户确认仍需新建
    "仍需新建",
]

async def main():
    from uuid import uuid4
    
    print("=== 重复检测功能测试 ===\n")
    
    # 初始化 LLM 配置
    if not LLMConfigService.is_type_configured("chat"):
        LLMConfigService._lazy_init()
    
    # 创建 Graph
    memory = MemorySaver()
    graph = create_todo_graph(checkpointer=memory)
    thread_id = f"test_duplicate_{uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id, "user_id": 2}}
    
    print(f"🧵 Thread ID: {thread_id}\n")
    
    for i, user_msg in enumerate(TEST_ROUNDS, 1):
        print(f"--- Round {i} ---")
        print(f"👤 User: {user_msg}")
        
        final_response = ""
        duplicate_detected = False
        
        events = graph.stream(
            {"messages": [HumanMessage(content=user_msg)], "user_id": 2},
            config=config,
            stream_mode="updates"
        )
        
        for event in events:
            for node, updates in event.items():
                if node == "analyze_intent" or node == "analyze":
                    pending_op = updates.get("pending_operation", {})
                    if pending_op and pending_op.get("duplicate_warning"):
                        duplicate_detected = True
                        print(f"🔍 [重复检测触发]")
                        duplicates = updates.get("duplicate_candidates", [])
                        for dup in duplicates:
                            print(f"    相似任务: #{dup['id']} {dup['title']} (相似度 {int(dup['similarity']*100)}%)")
                
                if "messages" in updates:
                    for msg in updates.get("messages", []):
                        if hasattr(msg, "content") and msg.content:
                            final_response = msg.content
        
        if final_response:
            display = final_response[:500] + "..." if len(final_response) > 500 else final_response
            print(f"🤖 Agent: {display}")
        print()
    
    print("=== Test Complete ===")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
