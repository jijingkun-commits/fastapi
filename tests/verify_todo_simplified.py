import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage, AIMessage
from app.ai.workflow.todo_graph import analyze_intent, TodoAgentState

# Mock Responses Map
MOCK_RESPONSES = {
    "TC-01": '{"intent": "create", "extracted_info": {"title": "开会", "due_date": "tomorrow 15:00"}}',
    "TC-02": '{"intent": "query", "extracted_info": {}}',
    "TC-03": '{"intent": "update", "extracted_info": {"due_date": "day after tomorrow"}, "quick_mode": false}',
    "TC-04": '{"intent": "complete", "extracted_info": {"title": "买牛奶"}}',
    "TC-06": '{"intent": "create", "extracted_info": {"title": "买苹果、香蕉和橙子"}}',
    "TC-06-Hallucination": '{"intent": "batch_create", "extracted_info": {"todos": [{"title": "苹果"}, {"title": "香蕉"}]}}', 
    "TC-07": '{"intent": "create", "extracted_info": {"title": "规划旅行"}}',
    "TC-08": '{"intent": "update", "extracted_info": {"title": "任务A"}}', # Simulating that merge is NOT recognized, maybe falling back to update or create
    "TC-09": '{"intent": "chat", "extracted_info": {}}'
}

def mock_get_llm(enable_streaming=False):
    llm = MagicMock()
    
    def mock_invoke(messages, config=None):
        # Extract input text from the last human message
        input_text = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                input_text = msg.content
                break
        
        # Determine case based on input text
        response_json = "{}"
        if "开会" in input_text:
            response_json = MOCK_RESPONSES["TC-01"]
        elif "查看" in input_text:
            response_json = MOCK_RESPONSES["TC-02"]
        elif "改成" in input_text:
            response_json = MOCK_RESPONSES["TC-03"]
        elif "完成" in input_text:
            response_json = MOCK_RESPONSES["TC-04"]
        elif "香蕉" in input_text:
            # Special logic to test hallucination scenario if needed, 
            # for now let's just use the standard Happy Path for TC-06
            if "FORCE_HALLUCINATION" in input_text:
                 response_json = MOCK_RESPONSES["TC-06-Hallucination"]
            else:
                 response_json = MOCK_RESPONSES["TC-06"]
        elif "旅行" in input_text:
            response_json = MOCK_RESPONSES["TC-07"]
        elif "合并" in input_text:
            response_json = MOCK_RESPONSES["TC-08"]
        elif "汇总" in input_text:
            response_json = MOCK_RESPONSES["TC-09"]
            
        return AIMessage(content=response_json)
    
    llm.invoke = mock_invoke
    return llm

@patch('app.ai.workflow.todo_graph.get_llm', side_effect=mock_get_llm)
@patch('app.ai.workflow.todo_graph.query_existing_todos', return_value="Some existing todos") # Mock helper to avoid DB
@patch('app.ai.workflow.todo_graph._get_user_id_from_state', return_value=1)
def run_tests(mock_user, mock_query, mock_llm_factory):
    print("=== Verifying Todo Agent Simplification (With Mocks) ===")
    
    test_cases = [
        # Happy Paths
        ("TC-01", "明天下午3点提醒我开会", ["create"]),
        ("TC-02", "查看所有待办", ["query"]),
        ("TC-03", "把刚才那个任务改成后天", ["update", "resolve"]), 
        ("TC-04", "完成买牛奶的任务", ["complete"]),
        
        # Destructive Paths
        ("TC-06", "我要买苹果、香蕉和橙子", ["create"], ["batch_create"]), 
        ("TC-06-Hallucination", "我要买苹果、香蕉和橙子 FORCE_HALLUCINATION", ["None", "execute"], ["batch_create"]), # Should NOT be batch_create even if LLM says so
        ("TC-07", "帮我规划一次为期三天的旅行，包含订票、酒店和攻略", ["create"], ["decompose"]),
        ("TC-08", "将任务A和任务B合并", ["update", "create"], ["merge"]),
        ("TC-09", "本周工作汇总", ["chat"], ["summarize"]),
    ]
    
    results = []
    
    for case_id, input_text, expected_intents, *forbidden in test_cases:
        forbidden = forbidden[0] if forbidden else []
        print(f"\nRunning {case_id}: Input='{input_text}'")
        
        state = {
            "messages": [HumanMessage(content=input_text)],
            "user_id": 1,
            "time_constraints": {},
            "quick_mode": False
        }
        
        try:
            updates = analyze_intent(state)
            pending_op = updates.get("pending_operation")
            actual_intent = pending_op.get("action") if pending_op else "None"
            
            # Special verification for TC-06-Hallucination
            # If LLM returns batch_create, but code removed the handler, 
            # pending_operation should be None (or at least NOT batch_create)
            # OR it might default to 'execute' with None action if we aren't careful?
            # Let's see what happens.
            
            print(f"  -> Actual Intent: {actual_intent}")
            
            passed = True
            
            # For Hallucination case, we specifically check it is NOT batch_create
            if case_id == "TC-06-Hallucination":
                if actual_intent == "batch_create":
                     print(f"  ❌ FAILED: Code accepted 'batch_create' hallucination!")
                     passed = False
                else:
                     print(f"  ✅ Code ignored/handled 'batch_create' hallucination safely.")
            else:
                if actual_intent not in expected_intents:
                    print(f"  ❌ FAILED: Expected {expected_intents}, got {actual_intent}")
                    passed = False
                else:
                    print(f"  ✅ MATCHED expected intent.")

            if forbidden:
                if actual_intent in forbidden:
                    print(f"  ❌ FAILED: Got forbidden intent {actual_intent}")
                    passed = False
                
                # Check draft_todos is_complex
                draft_todos = updates.get("draft_todos", [])
                for todo in draft_todos:
                    if todo.get("is_complex"):
                         print(f"  ❌ FAILED: Generated 'is_complex' flag.")
                         passed = False
            
            results.append((case_id, passed, actual_intent))
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((case_id, False, str(e)))

    print("\n=== Summary ===")
    all_passed = True
    for cid, p, act in results:
        status = "PASS" if p else "FAIL"
        print(f"{cid}: {status} (Got: {act})")
        if not p: all_passed = False
        
    if all_passed:
        print("\n🎉 All Verification Tests Passed!")
        with open("verification_success.flag", "w") as f:
            f.write("PASS")

if __name__ == "__main__":
    run_tests()
