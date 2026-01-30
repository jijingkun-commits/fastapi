import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage, AIMessage
from app.ai.workflow.todo_graph import analyze_intent, execute_operation, TodoAgentState
from app.db.session import get_db_context
from app.repositories.todo_repository import TodoRepository
from sqlalchemy import text

# Intent for "Buy Milk"
MOCK_INTENT_RESPONSE = '{"intent": "create", "extracted_info": {"title": "Test_Buy_Milk", "priority": 1}}'

def mock_get_llm(enable_streaming=False):
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content=MOCK_INTENT_RESPONSE)
    return llm

@patch('app.ai.workflow.todo_graph.get_llm', side_effect=mock_get_llm)
@patch('app.ai.workflow.todo_graph.query_existing_todos', return_value="")
@patch('app.ai.workflow.todo_graph._get_user_id_from_state', return_value=1)
@patch('app.ai.workflow.todo_graph.get_stream_writer')
def run_persistence_test(mock_writer, mock_user, mock_query, mock_llm_factory):
    # Mock writer callable
    mock_writer.return_value = MagicMock()
    
    print("=== Verifying Todo DB Persistence ===")
    
    # 1. Setup State
    state = {
        "messages": [HumanMessage(content="Buy Milk")],
        "user_id": 1,
        "time_constraints": {},
        "draft_todos": [], 
        "quick_mode": False
    }

    print("Step 1: Analyzing Intent (Mocked LLM)...")
    # 2. Analyze Intent
    updates = analyze_intent(state)
    state.update(updates)
    
    pending_op = state.get("pending_operation")
    if not pending_op:
        print("❌ FAILED: No pending operation created.")
        return

    print(f"  -> Generated Operation: {pending_op['action']} - {pending_op['data']}")

    # 3. Simulate User Confirmation (if needed) or direct execution
    # analyze_intent logic sets 'skip_confirmation' based on logic. 
    # For 'create' it usually requires confirmation unless quick_mode.
    # We will force skip_confirmation for this test or simulate confirmation.
    
    print("Step 2: Executing Operation (REAL DB)...")
    
    # Execute
    final_state = execute_operation(state)
    
    # 4. Verify DB
    print("Step 3: Checking Database...")
    repo = TodoRepository()
    with get_db_context() as db:
        # Check if "Test_Buy_Milk" exists
        stmt = text("SELECT id, title, status FROM t_todo WHERE title = :title AND user_id = :uid")
        result = db.execute(stmt, {"title": "Test_Buy_Milk", "uid": 1}).fetchone()
        
        if result:
            print(f"  ✅ SUCCESS: Found Task in DB! ID={result.id}, Title='{result.title}', Status='{result.status}'")
            # Cleanup
            print("  -> Cleaning up test data...")
            db.execute(text("DELETE FROM t_todo WHERE id = :id"), {"id": result.id})
            db.commit()
            print("  -> Cleanup complete.")
        else:
            print("  ❌ FAILED: Task not found in database.")

if __name__ == "__main__":
    run_persistence_test()
