"""测试冲突检测节点的增强功能。"""
import unittest
from datetime import datetime, timedelta
from app.ai.agents.todo_enhanced_nodes import conflict_detection_node

class TestConflictDetectionNode(unittest.TestCase):
    
    def test_blocked_weekday_conflict(self):
        """测试被屏蔽的星期冲突检测"""
        # 假设周一(1)被标记为不可用
        # 创建一个周一截止的任务
        next_monday = datetime(2026, 1, 12, 9, 0)  # 2026-01-12 is Monday
        
        state = {
            "messages": [],
            "draft_todos": [
                {"title": "周一任务", "due_date": next_monday.isoformat()}
            ],
            "time_constraints": {"blocked_weekdays": [1]},  # 周一不可用
            "detected_conflicts": []
        }
        
        new_state = conflict_detection_node(state)
        
        conflicts = new_state.get("detected_conflicts", [])
        self.assertTrue(len(conflicts) > 0)
        self.assertEqual(conflicts[0]["type"], "blocked_day")
        self.assertIn("周一", conflicts[0]["description"])

    def test_workload_overflow(self):
        """测试工作量超载检测"""
        # 同一天 5 个任务 (默认 2h/个 = 10h > 8h)
        target_date = datetime(2026, 1, 15, 9, 0)
        
        state = {
            "messages": [],
            "draft_todos": [
                {"title": f"任务{i}", "due_date": target_date.isoformat()}
                for i in range(5)
            ],
            "time_constraints": {},
            "detected_conflicts": []
        }
        
        new_state = conflict_detection_node(state)
        
        conflicts = new_state.get("detected_conflicts", [])
        self.assertTrue(len(conflicts) > 0)
        self.assertEqual(conflicts[0]["type"], "workload_overflow")
        self.assertIn("过载", conflicts[0]["description"])

    def test_no_conflict_normal_load(self):
        """测试正常工作量不触发冲突"""
        target_date = datetime(2026, 1, 15, 9, 0)
        
        state = {
            "messages": [],
            "draft_todos": [
                {"title": "任务1", "due_date": target_date.isoformat()},
                {"title": "任务2", "due_date": target_date.isoformat()}
            ],
            "time_constraints": {},
            "detected_conflicts": []
        }
        
        new_state = conflict_detection_node(state)
        
        # 2个任务 * 2h = 4h < 8h，不应该有冲突
        conflicts = new_state.get("detected_conflicts", [])
        self.assertEqual(len(conflicts), 0)
