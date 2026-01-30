import asyncio
import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage
from app.ai.workflow.todo_graph import analyze_intent, execute_operation
from app.db.session import get_db_context
from sqlalchemy import text
from app.services.llm_config_service import LLMConfigService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("E2E_Test")

# Mock writer to avoid context error locally
from unittest.mock import MagicMock, patch

@patch('app.ai.workflow.todo_graph.get_stream_writer')
@patch('app.ai.workflow.todo_graph._get_user_id_from_state', return_value=1)
def run_real_e2e_test(mock_user, mock_writer):
    mock_writer.return_value = MagicMock()
    
    print("=== 🚀 Starting E2E Test (Real LLM + Real DB) ===")
    
    # 0. Ensure Config is loaded (Testing the fix)
    print("[0/3] Checking LLM Configuration...")
    try:
        if not LLMConfigService.is_type_configured("chat"):
            LLMConfigService._lazy_init()
        model = LLMConfigService.get_model_by_type("chat")
        print(f"  ✅ Using Model: {model.model_code} (API Key: {'***' if model.api_key else 'MISSING'})")
    except Exception as e:
        print(f"  ❌ Config Error: {e}")
        return

    # 1. Setup State
    test_title = "E2E_Test_Buy_Coffee"
    input_text = f"帮我创建一个任务：{test_title}，优先级高"
    print(f"\n[1/3] input: '{input_text}'")
    
    state = {
        "messages": [HumanMessage(content=input_text)],
        "user_id": 1,
        "time_constraints": {},
        "quick_mode": False
    }

    # 2. Analyze Intent (Real LLM)
    print("\n[2/3] Calling Real LLM (analyze_intent)...")
    try:
        updates = analyze_intent(state)
        state.update(updates)
        pending_op = state.get("pending_operation")
        
        if not pending_op:
            print("  ❌ FAILED: LLM did not generate an operation.")
            print(f"  updates: {updates}")
            return
            
        print(f"  ✅ Intent Analyzed: {pending_op.get('action')}")
        print(f"  ✅ Extracted Data: {pending_op.get('data')}")
        
    except Exception as e:
        print(f"  ❌ LLM Call Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Execute Operation (Real DB)
    print("\n[3/3] Executing DB Operation...")
    try:
        # Simulate confirmation if needed (assuming logic requires it, we force logic execution)
        execute_operation(state)
        
        # Verify in DB
        with get_db_context() as db:
            row = db.execute(
                text("SELECT id, title, priority, status FROM t_todo WHERE title = :t"), 
                {"t": test_title}
            ).fetchone()
            
            if row:
                print(f"  ✅ DB SUCCESS: Found task ID={row.id}, Title='{row.title}', Priority={row.priority}")
                
                # Cleanup - DISABLED per user request for manual verification
                # db.execute(text("DELETE FROM t_todo WHERE id = :id"), {"id": row.id})
                # db.commit()
                # print("  🧹 Cleanup complete.")
                print(f"  ⚠️ Data Persisted: Task ID {row.id} left in DB for manual inspection.")
            else:
                print("  ❌ DB FAILED: Task not found in database.")
                
    except Exception as e:
        print(f"  ❌ Execution Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_real_e2e_test()
