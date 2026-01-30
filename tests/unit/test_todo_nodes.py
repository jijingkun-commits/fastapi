"""Todo Agent 核心节点单元测试。

测试覆盖：
1. resolve_entity - 实体解析节点
2. _dispatch_execute - 执行器分派
3. wait_for_confirmation - 确认等待节点（返回类型检查）
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict

from langchain_core.messages import AIMessage, HumanMessage


# ==================== resolve_entity 测试 ====================

class TestResolveEntity:
    """resolve_entity 节点测试。"""
    
    @pytest.fixture
    def mock_state_base(self):
        """基础 state fixture。"""
        return {
            "messages": [HumanMessage(content="删除买菜这个待办")],
            "user_id": 1,
            "pending_operation": None,
            "user_confirmed": None,
        }
    
    def test_no_pending_operation_returns_empty_dict(self, mock_state_base):
        """无待处理操作时应返回空字典。"""
        from app.ai.agents.resolve_node import resolve_entity
        
        state = mock_state_base
        result = resolve_entity(state)
        
        assert isinstance(result, dict)
        assert result == {}
    
    def test_skip_actions_return_empty_dict(self, mock_state_base):
        """create/query 等操作应跳过解析，返回空字典。"""
        from app.ai.agents.resolve_node import resolve_entity
        
        skip_actions = ["create", "batch_create", "query", "summarize", "clarify"]
        
        for action in skip_actions:
            state = {
                **mock_state_base,
                "pending_operation": {"action": action, "data": {}}
            }
            result = resolve_entity(state)
            
            assert isinstance(result, dict)
            assert result == {}, f"Action '{action}' should return empty dict"
    
    def test_existing_todo_id_returns_empty_dict(self, mock_state_base):
        """已有 todo_id 时应跳过解析，返回空字典。"""
        from app.ai.agents.resolve_node import resolve_entity
        
        state = {
            **mock_state_base,
            "pending_operation": {
                "action": "delete",
                "data": {"todo_id": 123}
            }
        }
        result = resolve_entity(state)
        
        assert isinstance(result, dict)
        assert result == {}
    
    @patch('app.ai.agents.resolve_node.get_user_id_optional')
    def test_no_user_id_returns_empty_dict(self, mock_get_user_id, mock_state_base):
        """无法获取 user_id 时应返回空字典。"""
        from app.ai.agents.resolve_node import resolve_entity
        
        mock_get_user_id.return_value = None
        
        state = {
            **mock_state_base,
            "user_id": None,
            "pending_operation": {
                "action": "delete",
                "data": {"title": "测试"}
            }
        }
        result = resolve_entity(state)
        
        assert isinstance(result, dict)
        assert result == {}
    
    @patch('app.ai.agents.resolve_node.get_user_id_optional')
    def test_no_keyword_needs_clarification(self, mock_get_user_id, mock_state_base):
        """无关键词时应设置需要澄清。"""
        from app.ai.agents.resolve_node import resolve_entity
        
        mock_get_user_id.return_value = 1
        
        state = {
            **mock_state_base,
            "pending_operation": {
                "action": "delete",
                "data": {}  # 无 title/keyword
            }
        }
        result = resolve_entity(state)
        
        assert isinstance(result, dict)
        assert "pending_operation" in result
        assert result["pending_operation"]["needs_clarification"] is True
        assert "pending_clarifications" in result
    
    @patch('app.ai.agents.resolve_node._find_matching_todos')
    @patch('app.ai.agents.resolve_node.get_user_id_optional')
    def test_no_matches_needs_clarification(self, mock_get_user_id, mock_find_todos, mock_state_base):
        """未找到匹配时应设置需要澄清并返回消息。"""
        from app.ai.agents.resolve_node import resolve_entity
        
        mock_get_user_id.return_value = 1
        mock_find_todos.return_value = []  # 无匹配
        
        state = {
            **mock_state_base,
            "pending_operation": {
                "action": "delete",
                "data": {"title": "不存在的任务"}
            }
        }
        result = resolve_entity(state)
        
        assert isinstance(result, dict)
        assert result["pending_operation"]["needs_clarification"] is True
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
    
    @patch('app.ai.agents.resolve_node._find_matching_todos')
    @patch('app.ai.agents.resolve_node.get_user_id_optional')
    def test_single_match_resolves_id(self, mock_get_user_id, mock_find_todos, mock_state_base):
        """单个匹配时应成功解析 ID。"""
        from app.ai.agents.resolve_node import resolve_entity
        
        mock_get_user_id.return_value = 1
        mock_find_todos.return_value = [{"id": 42, "title": "买菜"}]
        
        state = {
            **mock_state_base,
            "pending_operation": {
                "action": "delete",
                "data": {"title": "买菜"}
            }
        }
        result = resolve_entity(state)
        
        assert isinstance(result, dict)
        assert "pending_operation" in result
        assert result["pending_operation"]["data"]["todo_id"] == 42
        assert result["pending_operation"]["data"]["resolved_title"] == "买菜"
        assert result["pending_operation"]["needs_clarification"] is False
    
    @patch('app.ai.agents.resolve_node._find_matching_todos')
    @patch('app.ai.agents.resolve_node.get_user_id_optional')
    def test_multiple_matches_needs_selection(self, mock_get_user_id, mock_find_todos, mock_state_base):
        """多个匹配时应列出选项供选择。"""
        from app.ai.agents.resolve_node import resolve_entity
        
        mock_get_user_id.return_value = 1
        mock_find_todos.return_value = [
            {"id": 1, "title": "买菜 - 周一"},
            {"id": 2, "title": "买菜 - 周二"},
        ]
        
        state = {
            **mock_state_base,
            "pending_operation": {
                "action": "delete",
                "data": {"title": "买菜"}
            }
        }
        result = resolve_entity(state)
        
        assert isinstance(result, dict)
        assert result["pending_operation"]["needs_clarification"] is True
        assert "disambiguation_options" in result["pending_operation"]
        assert len(result["pending_operation"]["disambiguation_options"]) == 2
        assert "messages" in result


# ==================== _dispatch_execute 测试 ====================

class TestDispatchExecute:
    """_dispatch_execute 执行器分派测试。"""
    
    @pytest.fixture
    def mock_state(self):
        """基础 state fixture。"""
        return {
            "messages": [],
            "user_id": 1,
        }
    
    @patch('app.ai.workflow.todo_graph._execute_create')
    def test_dispatch_create(self, mock_execute, mock_state):
        """create 操作应分派到 _execute_create。"""
        from app.ai.workflow.todo_graph import _dispatch_execute
        from app.core.types import ToolResultBuilder
        
        mock_execute.return_value = ToolResultBuilder.success("创建成功")
        
        result = _dispatch_execute("create", {"title": "测试"}, mock_state)
        
        mock_execute.assert_called_once()
        assert result["success"] is True
    
    def test_dispatch_delete(self, mock_state):
        """delete 操作应分派到 _execute_delete。"""
        from app.ai.workflow.todo_graph import _dispatch_execute, _get_executor_map
        
        # 验证 delete 操作存在于映射中
        executor_map = _get_executor_map()
        assert "delete" in executor_map
        
        # 验证映射中包含所有预期的操作
        expected_actions = ["create", "update", "delete", "complete", "query"]
        for action in expected_actions:
            assert action in executor_map, f"Action '{action}' should be in executor_map"
    
    def test_dispatch_unknown_action(self, mock_state):
        """未知操作应返回错误。"""
        from app.ai.workflow.todo_graph import _dispatch_execute
        
        result = _dispatch_execute("unknown_action", {}, mock_state)
        
        assert result["success"] is False
        assert "暂不支持" in result["message"]


# ==================== wait_for_confirmation 返回类型测试 ====================

class TestWaitForConfirmationReturnType:
    """wait_for_confirmation 返回类型测试。
    
    验证修复后的函数返回 Dict 而非直接修改 state。
    """
    
    def test_return_type_is_dict(self):
        """返回值应为 Dict 类型。"""
        from app.ai.workflow.todo_graph import wait_for_confirmation
        import inspect
        
        # 检查函数签名中的返回类型注解
        sig = inspect.signature(wait_for_confirmation)
        return_annotation = sig.return_annotation
        
        assert return_annotation == Dict, f"Expected Dict, got {return_annotation}"


# ==================== _invoke_llm_for_intent 测试 ====================

class TestInvokeLLMForIntent:
    """_invoke_llm_for_intent 辅助函数测试。"""
    
    @patch('app.ai.workflow.todo_graph.get_llm')
    def test_applies_heuristic_title(self, mock_get_llm):
        """当 LLM 未提取标题时应使用启发式标题。"""
        from app.ai.workflow.todo_graph import _invoke_llm_for_intent
        
        # Mock LLM 返回不带标题的结果
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = '{"intent": "clarify", "extracted_info": {}}'
        mock_get_llm.return_value = mock_llm
        
        result = _invoke_llm_for_intent(
            recent_messages=[HumanMessage(content="创建待办")],
            system_prompt="test prompt",
            heuristic_title="启发式标题",
            pre_extracted_info=None
        )
        
        assert result["extracted_info"]["title"] == "启发式标题"
        assert result["intent"] == "create"  # clarify 被修正为 create
    
    @patch('app.ai.workflow.todo_graph.get_llm')
    def test_merges_pre_extracted_info(self, mock_get_llm):
        """应合并 Handoff 预提取的信息。"""
        from app.ai.workflow.todo_graph import _invoke_llm_for_intent
        
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = '{"intent": "create", "extracted_info": {"title": "测试"}}'
        mock_get_llm.return_value = mock_llm
        
        result = _invoke_llm_for_intent(
            recent_messages=[HumanMessage(content="创建待办")],
            system_prompt="test prompt",
            heuristic_title=None,
            pre_extracted_info={"priority": "高", "category": "工作"}
        )
        
        assert result["extracted_info"]["title"] == "测试"  # 保留 LLM 结果
        assert result["extracted_info"]["priority"] == "高"  # 合并预提取
        assert result["extracted_info"]["category"] == "工作"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
