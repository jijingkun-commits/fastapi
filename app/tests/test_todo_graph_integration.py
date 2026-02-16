"""验证 analyze_intent 集成 NaturalTimeParser 的效果。

模拟 LLM 输出包含相对时间的 extracted_info，检查 analyze_intent 是否正确调用解析器并更新 state。
"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import json

from app.ai.workflow.todo_graph import analyze_intent, TodoAgentState
from app.services.time_parser import NaturalTimeParser

# Mock LLM response
class MockLLMResponse:
    def __init__(self, content):
        self.content = content

class TestAnalyzeIntentIntegration(unittest.TestCase):
    
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
    def test_next_tuesday_integration(self, mock_get_scene_llm):
        # 1. 模拟 LLM 返回 "下周二"
        mock_response = MockLLMResponse(json.dumps({
            "intent": "create",
            "extracted_info": {
                "title": "测试任务",
                "due_date": "下周二" 
            },
            "needs_confirmation": True
        }))
        mock_get_scene_llm.return_value.invoke.return_value = mock_response
        
        # 2. 构造初始 State
        state = {
            "messages": [],
            "user_id": 1,
            "pending_operation": None,
            "time_constraints": {}
        }
        
        # 3. 执行 analyze_intent
        # 我们需要在运行前 patch NaturalTimeParser 的 base_time 以保证测试确定性
        # 或者我们只检查是否转换成了 ISO 格式，且日期合理
        
        # 为了精确断言，我们临时 patch NaturalTimeParser 的 parse 方法？
        # 不，最好测试真实逻辑。我们知道 NaturalTimeParser(regex) 的行为。
        # 假设今天是 X，下周二 = Y。
        
        new_state = analyze_intent(state)
        
        # 4. 验证结果
        pending_op = new_state.get("pending_operation")
        self.assertIsNotNone(pending_op)
        
        data = pending_op["data"]
        self.assertEqual(data["title"], "测试任务")
        
        # 关键断言：due_date 应该被转换为 ISO 格式的日期字符串，而不是原始的 "下周二"
        due_date = data.get("due_date")
        print(f"Parsed Due Date: {due_date}")
        self.assertNotEqual(due_date, "下周二")
        self.assertTrue(due_date.startswith("20")) # 应该是 202x-xx-xx
        
        # 验证 constraints
    
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
    def test_constraint_extraction(self, mock_get_scene_llm):
        # 模拟 LLM 返回包含约束的文本
        mock_response = MockLLMResponse(json.dumps({
            "intent": "create",
            "extracted_info": {
                "title": "开会",
                "time": "下周一 (周五不可用)"
            }
        }))
        mock_get_scene_llm.return_value.invoke.return_value = mock_response
        
        state = {"messages": [], "user_id": 1, "time_constraints": {}}
        new_state = analyze_intent(state)
        
        # 验证 constraints 是否被提取到 state
        constraints = new_state.get("time_constraints")
        self.assertIn("blocked_weekdays", constraints)
        self.assertIn(5, constraints["blocked_weekdays"]) # 周五=5
        
if __name__ == "__main__":
    unittest.main()
