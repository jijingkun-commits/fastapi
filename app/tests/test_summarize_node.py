"""summarize_node 单元测试。

测试汇总节点的按优先级分组功能。
"""
import unittest
from datetime import datetime, timedelta

from app.ai.agents.summarize_node import (
    summarize_node,
    _get_time_group,
    _format_due_date,
    should_summarize
)
from app.ai.workflow.todo_graph import TodoAgentState


class TestSummarizeNode(unittest.TestCase):
    
    def test_time_group_today(self):
        """测试今天的时间分组。"""
        now = datetime.now()
        due = now + timedelta(hours=3)
        group = _get_time_group(due, now)
        self.assertEqual(group, "today")
    
    def test_time_group_tomorrow(self):
        """测试明天的时间分组。"""
        now = datetime.now()
        due = now + timedelta(days=1)
        group = _get_time_group(due, now)
        self.assertEqual(group, "tomorrow")
    
    def test_time_group_this_week(self):
        """测试本周的时间分组。"""
        now = datetime.now()
        due = now + timedelta(days=5)
        group = _get_time_group(due, now)
        self.assertEqual(group, "this_week")
    
    def test_time_group_overdue(self):
        """测试已过期的时间分组。"""
        now = datetime.now()
        due = now - timedelta(days=2)
        group = _get_time_group(due, now)
        self.assertEqual(group, "overdue")
    
    def test_time_group_none(self):
        """测试无截止日期。"""
        now = datetime.now()
        group = _get_time_group(None, now)
        self.assertEqual(group, "unscheduled")
    
    def test_format_due_date_today(self):
        """测试今天的日期格式化。"""
        now = datetime.now()
        due = now.replace(hour=14, minute=30)
        formatted = _format_due_date(due, now)
        self.assertIn("今天", formatted)
        self.assertIn("14:30", formatted)
    
    def test_format_due_date_tomorrow(self):
        """测试明天的日期格式化。"""
        now = datetime.now()
        due = now + timedelta(days=1)
        due = due.replace(hour=10, minute=0)
        formatted = _format_due_date(due, now)
        self.assertIn("明天", formatted)
    
    def test_format_due_date_overdue(self):
        """测试过期日期格式化。"""
        now = datetime.now()
        due = now - timedelta(days=3)
        formatted = _format_due_date(due, now)
        self.assertIn("已过期", formatted)
        self.assertIn("3", formatted)
    
    def test_should_summarize_explicit(self):
        """测试显式汇总请求识别。"""
        state = {
            "pending_operation": {"action": "summarize"},
            "messages": []
        }
        result = should_summarize(state)
        self.assertTrue(result)
    
    def test_should_summarize_no_request(self):
        """测试无汇总请求。"""
        state = {
            "pending_operation": None,
            "messages": []
        }
        result = should_summarize(state)
        self.assertFalse(result)
    
    def test_summarize_node_with_draft_todos(self):
        """测试 summarize_node 处理 draft_todos。"""
        now = datetime.now()
        state = {
            "messages": [],
            "draft_todos": [
                {"title": "紧急任务", "priority": 1, "due_date": (now + timedelta(days=1)).isoformat()},
                {"title": "普通任务", "priority": 2, "due_date": (now + timedelta(days=3)).isoformat()},
                {"title": "低优任务", "priority": 3, "due_date": None},
            ],
            "pending_operation": None
        }
        
        result = summarize_node(state)
        
        # 验证消息被添加
        self.assertEqual(len(result["messages"]), 1)
        message = result["messages"][0].content
        
        # 验证格式
        self.assertIn("📋 待办清单", message)
        self.assertIn("🔴 高优先级", message)
        self.assertIn("🟡 中优先级", message)
        self.assertIn("🔵 低优先级", message)
        self.assertIn("紧急任务", message)
        self.assertIn("普通任务", message)
        self.assertIn("低优任务", message)
    
    def test_summarize_node_empty(self):
        """测试空待办列表。"""
        state = {
            "messages": [],
            "draft_todos": [],
            "pending_operation": None
        }
        
        result = summarize_node(state)
        
        self.assertEqual(len(result["messages"]), 1)
        self.assertIn("没有待处理", result["messages"][0].content)


if __name__ == "__main__":
    unittest.main()
