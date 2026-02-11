"""Todo Agent 核心节点单元测试。

测试覆盖：
1. resolve_entity - 实体解析节点
2. _dispatch_execute - 执行器分派
3. wait_for_confirmation - 确认等待节点（返回类型检查）
"""
import pytest
from unittest.mock import patch, MagicMock
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
    def test_target_ref_keyword_can_resolve(self, mock_get_user_id, mock_find_todos, mock_state_base):
        """target_ref 字段应可作为实体解析关键词。"""
        from app.ai.agents.resolve_node import resolve_entity

        mock_get_user_id.return_value = 1
        mock_find_todos.return_value = [{"id": 88, "title": "项目汇报"}]

        state = {
            **mock_state_base,
            "pending_operation": {
                "action": "update",
                "data": {"target_ref": "项目汇报"}
            }
        }
        result = resolve_entity(state)

        assert result["pending_operation"]["data"]["todo_id"] == 88
        assert result["pending_operation"]["data"]["resolved_title"] == "项目汇报"
        assert result["pending_operation"]["needs_clarification"] is False

    @patch('app.ai.agents.resolve_node._find_matching_todos')
    @patch('app.ai.agents.resolve_node.get_user_id_optional')
    def test_reference_suffix_cleaned_before_resolve(self, mock_get_user_id, mock_find_todos, mock_state_base):
        """“项目汇报那个”应先清洗为“项目汇报”再匹配。"""
        from app.ai.agents.resolve_node import resolve_entity

        mock_get_user_id.return_value = 1
        mock_find_todos.return_value = [{"id": 99, "title": "项目汇报"}]

        state = {
            **mock_state_base,
            "pending_operation": {
                "action": "update",
                "data": {"title": "项目汇报那个"}
            }
        }
        result = resolve_entity(state)

        assert result["pending_operation"]["data"]["todo_id"] == 99
        assert result["pending_operation"]["data"]["resolved_title"] == "项目汇报"
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

    @patch('app.ai.agents.resolve_node.get_user_id_optional')
    def test_disambiguation_select_by_index(self, mock_get_user_id, mock_state_base):
        """已有候选时输入“第2个”应选中对应待办。"""
        from app.ai.agents.resolve_node import resolve_entity

        mock_get_user_id.return_value = 1
        state = {
            **mock_state_base,
            "messages": [HumanMessage(content="第2个")],
            "pending_operation": {
                "action": "update",
                "data": {"keyword": "报告"},
                "needs_clarification": True,
                "disambiguation_options": [
                    {"id": 10, "title": "项目汇报"},
                    {"id": 20, "title": "周报提交"},
                ],
            }
        }

        result = resolve_entity(state)

        assert result["pending_operation"]["data"]["todo_id"] == 20
        assert result["pending_operation"]["data"]["resolved_title"] == "周报提交"
        assert result["pending_operation"]["needs_clarification"] is False

    @patch('app.ai.agents.resolve_node.get_user_id_optional')
    def test_disambiguation_select_by_id(self, mock_get_user_id, mock_state_base):
        """已有候选时输入“ID为XX”应选中对应待办。"""
        from app.ai.agents.resolve_node import resolve_entity

        mock_get_user_id.return_value = 1
        state = {
            **mock_state_base,
            "messages": [HumanMessage(content="ID 为 10 的那个")],
            "pending_operation": {
                "action": "delete",
                "data": {"keyword": "报告"},
                "needs_clarification": True,
                "disambiguation_options": [
                    {"id": 10, "title": "项目汇报"},
                    {"id": 20, "title": "周报提交"},
                ],
            }
        }

        result = resolve_entity(state)

        assert result["pending_operation"]["data"]["todo_id"] == 10
        assert result["pending_operation"]["data"]["resolved_title"] == "项目汇报"
        assert result["pending_operation"]["needs_clarification"] is False


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


# ==================== 能力边界兜底测试 ====================

class TestOutOfScopeGuard:
    """超出待办能力范围输入兜底测试。"""

    def test_out_of_scope_weather_returns_clarification(self):
        """天气请求应被识别为超范围，不进入待办查询。"""
        from app.ai.workflow.todo_graph import analyze_intent

        state = {
            "messages": [HumanMessage(content="今天上海天气怎么样")],
            "user_id": 1,
            "pending_operation": None,
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": None,
            "pending_clarifications": None,
            "response_message": None,
        }

        result = analyze_intent(state)

        assert isinstance(result, dict)
        assert result.get("pending_operation", {}).get("action") == "out_of_scope"
        assert result.get("pending_operation", {}).get("needs_clarification") is True
        assert "能力范围" in (result.get("response_message") or "")

    def test_in_scope_todo_query_not_blocked(self):
        """包含待办语义的查询不应被超范围兜底误拦截。"""
        from app.ai.workflow.todo_graph import _is_out_of_scope_for_todo

        assert _is_out_of_scope_for_todo("查询我的待办列表") is False

    def test_banking_data_query_is_out_of_scope(self):
        """银行问数请求在待办助手中应识别为超范围。"""
        from app.ai.workflow.todo_graph import _is_out_of_scope_for_todo

        assert _is_out_of_scope_for_todo("查询上月分行贷款余额") is True


class TestTodoCanonicalizationAndClarifyFallback:
    """待办字段归一化与澄清兜底测试。"""

    def test_canonicalize_alias_fields(self):
        """target_ref/new_* 字段应归一到 canonical 字段。"""
        from app.ai.workflow.todo_intent_helpers import canonicalize_extracted_info

        payload = {
            "target_ref": "项目汇报那个",
            "new_due_date": "下周一",
            "new_priority": "高",
            "new_category": "工作",
            "new_description": "补充材料",
        }

        result = canonicalize_extracted_info(payload)

        assert result["title"] == "项目汇报"
        assert result["due_date"] == "下周一"
        assert result["priority"] == "高"
        assert result["category"] == "工作"
        assert result["description"] == "补充材料"
        # 兼容保留原始字段
        assert result["target_ref"] == "项目汇报"
        assert result["new_due_date"] == "下周一"

    def test_clarify_fallback_should_be_contextual(self):
        """response_message 缺失时，clarify_node 应输出上下文化追问。"""
        from app.ai.agents.todo_enhanced_nodes import clarify_node

        state = {
            "messages": [HumanMessage(content="项目汇报那个")],
            "response_message": "",
            "pending_clarifications": ["请选择目标待办"],
            "pending_operation": {
                "action": "update",
                "data": {"title": "项目汇报"},
                "needs_clarification": True,
            },
        }

        result = clarify_node(state)
        assert "messages" in result
        content = result["messages"][0].content
        assert "项目汇报" in content
        assert "请选择目标待办" in content


class TestImplicitReferenceRouting:
    """无动作指代的自适应判定测试。"""

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph._find_todo_candidates_by_keyword")
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_llm")
    def test_analyze_intent_implicit_reference_single_match_defaults_update(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        mock_candidates,
        _mock_parse_time,
    ):
        """“项目汇报那个”且唯一命中时，应默认 update 并进入确认。"""
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"clarify","action_state":"need_clarify","response_message":"",'
            '"extracted_info":{"target_ref":"项目汇报那个"},"missing_info":[]}'
        )
        mock_get_llm.return_value = mock_llm
        mock_candidates.return_value = [{"id": 101, "title": "项目汇报"}]

        state = {
            "messages": [HumanMessage(content="项目汇报那个")],
            "user_id": 1,
            "pending_operation": None,
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": None,
            "pending_clarifications": None,
            "response_message": None,
        }

        result = analyze_intent(state)

        assert result["pending_operation"]["action"] == "update"
        assert result["pending_operation"]["data"]["todo_id"] == 101
        assert result["pending_operation"]["data"]["resolved_title"] == "项目汇报"
        assert result["pending_operation"]["needs_clarification"] is False


class TestTodoSupplementConvergence:
    """补充轮应优先合并已有 pending_operation，避免重复澄清。"""

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_llm")
    def test_supplement_time_should_promote_to_need_confirm(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"clarify","action_state":"need_clarify",'
            '"response_message":"",'
            '"extracted_info":{"time":"明天下午3点"},'
            '"missing_info":["时间"]}'
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="改到明天下午3点")],
            "user_id": 1,
            "pending_operation": {
                "action": "update",
                "data": {"title": "项目汇报"},
                "needs_clarification": True,
            },
            "pending_clarifications": ["时间"],
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": {"title": "项目汇报"},
            "response_message": None,
        }

        result = analyze_intent(state)

        assert result["turn_act"] in {"SUPPLEMENT", "CORRECTION"}
        assert result["pending_operation"]["action"] == "update"
        assert result["pending_operation"]["needs_clarification"] is False
        assert result["pending_operation"]["data"].get("time") == "明天下午3点"
        assert result.get("clarify_fsm_state") == "done"


class TestTodoWorkflowStateSemantics:
    """WS-01 状态字段语义收敛回归。"""

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.is_implicit_reference_message", return_value=False)
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_llm")
    def test_need_clarify_should_set_action_clarify_state_and_round(
        self,
        mock_get_llm,
        _mock_implicit,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        """缺少动作信息时应进入 asked_action 且轮次递增。"""
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"clarify","action_state":"need_clarify",'
            '"response_message":"",'
            '"extracted_info":{"title":"项目汇报"},'
            '"missing_info":["操作动作","操作动作",""]}'
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="项目汇报这个")],
            "user_id": 1,
            "pending_operation": None,
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": None,
            "pending_clarifications": None,
            "response_message": None,
            "clarify_fsm_state": "idle",
            "clarify_round": 0,
        }

        result = analyze_intent(state)

        assert result.get("clarify_fsm_state") == "asked_action"
        assert result.get("clarify_round") == 1
        assert result.get("pending_clarifications") == ["操作动作"]
        assert result.get("pending_operation", {}).get("needs_clarification") is True

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_llm")
    def test_need_confirm_should_reset_clarify_state_and_round(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        """进入确认路径时应清理澄清态。"""
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"update","action_state":"need_confirm",'
            '"response_message":"",'
            '"extracted_info":{"title":"项目汇报","time":"明天10点"},'
            '"missing_info":[]}'
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="把项目汇报改到明天10点")],
            "user_id": 1,
            "pending_operation": {
                "action": "update",
                "data": {"title": "项目汇报"},
                "needs_clarification": True,
            },
            "pending_clarifications": ["时间"],
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": {"title": "项目汇报"},
            "response_message": None,
            "clarify_fsm_state": "asked_time",
            "clarify_round": 2,
        }

        result = analyze_intent(state)

        assert result.get("clarify_fsm_state") == "done"
        assert result.get("clarify_round") == 0
        assert result.get("pending_operation", {}).get("action") == "update"
        assert result.get("pending_operation", {}).get("needs_clarification") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
