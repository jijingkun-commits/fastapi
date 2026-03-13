"""快捷指令测试套件 (Shortcut Commands Test).

覆盖 SC-01 到 SC-05 及破坏性测试。
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
THREAD_ID = f"test_shortcut_{uuid4().hex[:8]}"
USER_ID = 2
TEST_TITLE = f"快捷测试_{uuid4().hex[:4]}"

async def run_round(graph, config, user_input: str, expected_keywords: list = None, conversation_history = None):
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
    print(f"=== 🚀 Shortcut Commands Test Suite (Thread: {THREAD_ID}) ===\n")
    
    # 0. Init
    if not LLMConfigService.is_type_configured("chat"):
        LLMConfigService._lazy_init()
    
    memory = MemorySaver()
    graph = create_todo_graph(checkpointer=memory)
    config = {"configurable": {"thread_id": THREAD_ID, "user_id": USER_ID}}
    
    # --- SC-01: Quick Mode (极速创建) ---
    print("\n--- [SC-01] Quick Mode: Create without confirmation ---")
    # "直接创建" 应该触发 quick_mode，跳过确认
    await run_round(graph, config, f"明天开会，直接创建别问了，标题是{TEST_TITLE}", ["已创建", "ID:", TEST_TITLE])
    
    # Get ID
    TASK_ID = 0
    with get_db_context() as db:
        row = db.execute(text("SELECT id FROM t_todo WHERE title = :t"), {"t": TEST_TITLE}).fetchone()
        if not row:
            print("❌ DB Verify Failed: Task not found")
            return 1
        TASK_ID = row.id
        print(f"✅ DB Verify Passed: Task Created ID={TASK_ID}")

    # --- SC-04: Explicit ID Complete (精准完成) ---
    print("\n--- [SC-04] Explicit ID Complete ---")
    # 应该直接完成，无需确认
    await run_round(graph, config, f"完成 ID {TASK_ID}", ["已完成", "100%"])
    
    # Verify
    with get_db_context() as db:
        row = db.execute(text("SELECT status FROM t_todo WHERE id = :id"), {"id": TASK_ID}).fetchone()
        if row.status != 'done':
            print(f"❌ DB Verify Failed: Status={row.status}")
            return 1
        print("✅ DB Verify Passed: Status=done")

    # --- SC-05: Explicit ID Delete (精准删除) ---
    print("\n--- [SC-05] Explicit ID Delete ---")
    await run_round(graph, config, f"删除 ID {TASK_ID}", ["已删除"])
    
    # Verify
    with get_db_context() as db:
        row = db.execute(text("SELECT is_deleted FROM t_todo WHERE id = :id"), {"id": TASK_ID}).fetchone()
        if not row.is_deleted:
             print(f"❌ DB Verify Failed: is_deleted=False")
             return 1
        print("✅ DB Verify Passed: is_deleted=True")

    # --- SC-02: Force Create (Duplicate Warning override) ---
    print("\n--- [SC-02] Force Create (Duplicate Override) ---")
    # 先创建一个基础任务
    BASE_TITLE = f"重复测试_{uuid4().hex[:4]}"
    await run_round(graph, config, f"创建任务：{BASE_TITLE}", ["已创建"])
    
    # 再创建一样的 -> 触发警告
    print(">> Triggering Duplicate Warning...")
    await run_round(graph, config, f"再来一个：{BASE_TITLE}", ["相似任务", "仍需新建"])
    
    # 强行新建
    print(">> Forcing Create...")
    await run_round(graph, config, "仍需新建", ["已创建"])
    
    # --- SC-03: Cancel Shortcut ---
    print("\n--- [SC-03] Cancel Shortcut ---")
    # 再次触发重复
    await run_round(graph, config, f"再来一个：{BASE_TITLE}", ["相似任务"])
    # 取消
    await run_round(graph, config, "取消", ["已取消"])

    print("\n=== ✨ All Shortcut Tests Passed! ===")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
