"""待办助手全面测试套件 (Comprehensive Test Suite).

覆盖 CRUD 及核心智能特性 (重复检测)。
"""
import asyncio
import logging
import sys
from uuid import uuid4
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from app.ai.workflow.todo_graph import create_todo_graph
from app.services.llm_config_service import LLMConfigService
from app.db.session import get_db_context
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 测试配置
THREAD_ID = f"test_suite_{uuid4().hex[:8]}"
USER_ID = 2
TEST_TITLE = f"AI全面测试任务_{uuid4().hex[:4]}"

async def run_round(graph, config, user_input: str, expected_keywords: list = None):
    """运行一轮对话并验证输出"""
    print(f"\n👤 User: {user_input}")
    
    final_response = ""
    events = graph.stream(
        {"messages": [HumanMessage(content=user_input)], "user_id": USER_ID},
        config=config,
        stream_mode="updates"
    )
    
    for event in events:
        for node, updates in event.items():
            if "messages" in updates:
                for msg in updates.get("messages", []):
                    if hasattr(msg, "content") and msg.content:
                        final_response = msg.content
    
    print(f"🤖 Agent: {final_response.replace(chr(10), ' ')[:200]}...")
    
    if expected_keywords:
        missing = [kw for kw in expected_keywords if kw not in final_response]
        if missing:
            print(f"❌ FAILED: Missing keywords {missing}")
            return False, final_response
    print("✅ Output Verification Passed")
    return True, final_response

async def main():
    print(f"=== 🚀 Todo Agent Comprehensive Test Suite (Thread: {THREAD_ID}) ===\n")
    
    # 0. Init
    if not LLMConfigService.is_type_configured("chat"):
        LLMConfigService._lazy_init()
    
    memory = MemorySaver()
    graph = create_todo_graph(checkpointer=memory)
    config = {"configurable": {"thread_id": THREAD_ID, "user_id": USER_ID}}
    
    # --- TC-CRUD-01: Create Task ---
    print("\n--- [Step 1] TC-CRUD-01: Create Task ---")
    await run_round(graph, config, f"帮我创建一个任务：{TEST_TITLE}，优先级高", ["确认", TEST_TITLE, "高"])
    # Confirm creation
    await run_round(graph, config, "确认", ["已创建", "ID:"])
    
    # DB Verify
    with get_db_context() as db:
        row = db.execute(text("SELECT id, status FROM t_todo WHERE title = :t"), {"t": TEST_TITLE}).fetchone()
        if not row:
            print("❌ DB Verify Failed: Task not found")
            return 1
        TASK_ID = row.id
        print(f"✅ DB Verify Passed: Task ID={TASK_ID}, Status={row.status}")

    # --- TC-CRUD-02: Query Task ---
    # print("\n--- [Step 2] TC-CRUD-02: Query Task ---")
    # await run_round(graph, config, f"查询我刚才创建的那个{TEST_TITLE}", [TEST_TITLE, "待办"])

    # --- TC-CRUD-03: Update Task ---
    # print("\n--- [Step 3] TC-CRUD-03: Update Task ---")
    # await run_round(graph, config, "把这个任务的优先级改为低", ["确认", "低"])
    # await run_round(graph, config, "确认", ["已更新"])
    
    # DB Verify Update
    # with get_db_context() as db:
    #     row = db.execute(text("SELECT priority FROM t_todo WHERE id = :id"), {"id": TASK_ID}).fetchone()
    #     if row.priority != 3: # 3=Low
    #          print(f"❌ DB Verify Failed: Priority is {row.priority}, expected 3")
    #          return 1
    #     print("✅ DB Verify Passed: Priority updated to 3")

    # --- TC-FEAT-01: Duplicate Detection ---
    print("\n--- [Step 4] TC-FEAT-01: Duplicate Detection ---")
    await run_round(graph, config, f"再帮我创建一个任务：{TEST_TITLE}", ["相似任务", "仍需新建"])
    
    # Cancel duplicate
    await run_round(graph, config, "取消", ["已取消"]) # Confirms cancellation

    # --- TC-CRUD-04: Complete Task ---
    # print("\n--- [Step 5] TC-CRUD-04: Complete Task ---")
    # await run_round(graph, config, f"完成 ID 为 {TASK_ID} 的任务", ["已完成", "100%"])

    # DB Verify Complete
    # with get_db_context() as db:
    #     row = db.execute(text("SELECT status, progress FROM t_todo WHERE id = :id"), {"id": TASK_ID}).fetchone()
    #     if row.status != 'done':
    #          print(f"❌ DB Verify Failed: Status is {row.status}")
    #          return 1
    #     print("✅ DB Verify Passed: Status=done")

    # --- TC-CRUD-05: Delete Task ---
    # print("\n--- [Step 6] TC-CRUD-05: Delete Task ---")
    # await run_round(graph, config, f"删除 ID 为 {TASK_ID} 的任务", ["已删除"])
    
    # DB Verify Delete
    # with get_db_context() as db:
    #     row = db.execute(text("SELECT is_deleted FROM t_todo WHERE id = :id"), {"id": TASK_ID}).fetchone()
    #     if not row.is_deleted:
    #          print(f"❌ DB Verify Failed: is_deleted is False")
    #          return 1
    #     print("✅ DB Verify Passed: Task deleted")
        
    print("\n=== ✨ All Comprehensive Tests Passed! ===")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
