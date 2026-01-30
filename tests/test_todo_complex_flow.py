import asyncio
import sys
import os
import logging
from typing import List, Dict, Any

# Ensure project root is in path
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from app.ai.workflow.todo_graph import create_todo_graph  # Fix: Import factory
from app.services.llm_config_service import LLMConfigService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("ComplexTest")

async def run_complex_scenario():
    print("=== 🚀 Starting Todo Agent Complex Stress Test (10 Rounds) ===\n")

    # 0. Ensure Config
    if not LLMConfigService.is_type_configured("chat"):
        LLMConfigService._lazy_init()
    
    # 1. Setup Graph with Memory (state retention)
    memory = MemorySaver()
    # Create graph instance using the factory
    graph = create_todo_graph(checkpointer=memory)
    
    thread_id = "test_thread_complex_002"
    config = {"configurable": {"thread_id": thread_id, "user_id": 2}}
    
    # 2. Define Scenario Inputs
    verify_rounds = [
        # R1: Ambiguity
        "最近事情太多了，帮我把接下来要做的事情理一理。",
        # R2: Multi-project (high level)
        "工作的为主吧。大概有几个项目：一个是预售资金系统的投标材料，一个是 AI 中台相关的方案，还有几个零碎的临时事",
        # R3: Priority & Relative Time
        "预售资金那个挺急的，好像这周内要给。AI 中台倒是不那么急，但领导下周可能要听汇报。零碎的先不管。",
        # R4: Decomposition & Dependency
        "技术方案我负责，但商务那块是公司部给。技术方案里要写系统架构、信创适配、实施计划。",
        # R5: Conflict (Delay vs Urge)
        "对了，人力系统全行测评那件事之前说这周出初稿，可能要顺延一下。但办公室昨天又催了。",
        # R6: Time Constraint & Constraints
        "人力系统的放到下周二之前吧。但周一我基本一整天都在开会。",
        # R7: Scope Change (Simple -> Complex)
        "AI 中台那个，其实不是写方案那么简单。我想先理一个落地路线图，顺便把组织模式也想一想。",
        # R8: Interrupt (High Priority)
        "等等，刚刚领导发消息了，说明天下午要一个“AI + 金融场景落地”的 1 页简要说明。",
        # R9: Merge/Refactor
        "那 AI 中台的完整路线图可以先不做那么细，跟明天那个 1 页说明能不能合并一部分？",
        # R10: Final Output
        "可以，按优先级给我。",
        # R11: Final Confirmation (triggers execute)
        "确认"
    ]

    print(f"🧵 Thread ID: {thread_id}")

    # 3. Execution Loop
    for i, user_input in enumerate(verify_rounds, 1):
        print(f"\n--- Round {i} ---")
        print(f"👤 User: {user_input}")
        
        # Stream the graph execution
        # Note: 'graph' in todo_graph.py is likely already compiled.
        # We need to invoke it. ensuring inputs match state schema.
        
        inputs = {
            "messages": [HumanMessage(content=user_input)],
            "user_id": 2,
            # Initialize other state keys if needed, graph usually handles defaults
        }
        
        print("🤖 Agent: ", end="", flush=True)
        response_content = ""
        
        try:
            # Using ainvoke or stream. Here we use stream to see steps if needed, 
            # but for simplicity in reporting, we'll just get the final response.
            # We use invoke to get the final state.
            
            # Since the graph is stateful with checkpointer, we pass config.
            # The user input "messages" will be appended to history.
            
            async for event in graph.astream(inputs, config=config, stream_mode="values"):
                # Capturing the last message from AI
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    if isinstance(last_msg, AIMessage):
                        # This might print multiple times as state updates, 
                        # so we just capture the final one or print incrementally if it changes.
                        response_content = last_msg.content
            
            print(f"{response_content}\n")
            
            # Optional: Inspect State (intent, pending_ops) if supported by graph schema
            # snapshot = await graph.aget_state(config)
            # print(f"   [State Debug] Pending Op: {snapshot.values.get('pending_operation')}")

        except Exception as e:
            print(f"\n❌ Error in Round {i}: {e}")
            import traceback
            traceback.print_exc()
            break
            
    print("\n=== Test Complete ===")


async def main():
    await run_complex_scenario()
    return 0

if __name__ == "__main__":
    asyncio.run(main())
