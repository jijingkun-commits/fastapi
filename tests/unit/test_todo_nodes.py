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
    
    @patch('app.ai.workflow.todo_graph.get_scene_llm')
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
    
    @patch('app.ai.workflow.todo_graph.get_scene_llm')
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

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
    def test_selected_todo_external_supplement_should_not_trigger_out_of_scope(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        """已选中待办时，补充天气/股价信息应走 update，不应被越界拦截。"""
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"update","action_state":"need_confirm",'
            '"response_message":"好的，已整理外部信息并准备更新待办。",'
            '"extracted_info":{"description":"请关注会前路线。"},'
            '"missing_info":[]}'
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="描述里添加，当天的天气情况")],
            "user_id": 1,
            "current_todo_id": 88,
            "pending_handoff": {
                "target_agent": "todo_expert",
                "task_description": "请补充外部信息后更新待办",
                "turn_act_hint": "SUPPLEMENT",
                "frame": {
                    "todo_action": "update",
                    "todo_fields": {"todo_id": 88, "description": "原始描述"},
                    "tool_observations": [
                        {
                            "tool": "tavily_search",
                            "topic": "web_search",
                            "summary": "上海明天多云，10~16℃",
                            "status": "ok",
                        }
                    ],
                },
            },
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

        assert result.get("pending_operation", {}).get("action") == "update"
        description = result.get("pending_operation", {}).get("data", {}).get("description", "")
        assert "外部信息补充" in description
        assert "上海明天多云" in description

    @patch("app.ai.workflow.todo_graph.parse_time_info", side_effect=lambda extracted_info, _constraints: (extracted_info, None))
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
    def test_analyze_intent_should_use_contract_first_handoff_messages(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        """handoff 场景下，todo analyze 只应消费内部 contract + 最新用户补充。"""
        from app.ai.workflow.todo_graph import analyze_intent

        captured = {}

        class _FakeLLM:
            def invoke(self, messages):
                captured["messages"] = messages
                return MagicMock(content=(
                    '{"intent":"update","action_state":"need_confirm",'
                    '"response_message":"好的，已准备更新待办。",'
                    '"extracted_info":{"description":"补充天气信息"},'
                    '"missing_info":[]}'
                ))

        mock_get_llm.return_value = _FakeLLM()

        state = {
            "messages": [
                HumanMessage(content="旧问题：帮我查天气"),
                AIMessage(content="旧回答：上海多云"),
                HumanMessage(content="描述里添加，当天的天气情况"),
            ],
            "user_id": 1,
            "pending_handoff": {
                "target_agent": "todo_expert",
                "task_description": "请补充外部信息后更新待办",
                "turn_act_hint": "SUPPLEMENT",
                "frame": {
                    "todo_action": "update",
                    "todo_fields": {"todo_id": 88, "description": "原始描述"},
                },
            },
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

        analyze_intent(state)

        analysis_messages = captured["messages"]
        assert len(analysis_messages) == 3
        assert analysis_messages[1].name == "__internal_todo_handoff__"
        assert analysis_messages[1].additional_kwargs["expert_input_contract"]["contract_id"] == "todo_handoff_frame"
        assert analysis_messages[2].content == "描述里添加，当天的天气情况"
        joined = "\n".join(str(msg.content) for msg in analysis_messages[1:])
        assert "旧问题：帮我查天气" not in joined
        assert "旧回答：上海多云" not in joined

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
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
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
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
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
            '"missing_info":["time_range"]}'
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


class TestTodoCompoundSingleGoalRecognition:
    """单目标复合描述识别回归。"""

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
    def test_compound_single_goal_should_promote_to_need_confirm(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        """目标+必要动作表达应归并为单待办确认，而不是二选一澄清。"""
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"create","action_state":"need_clarify",'
            '"response_message":"你这句话里包含了两件事（回老家过清明、订高铁票），我一次只能帮你记录一个待办。",'
            '"extracted_info":{"title":"回老家过清明","description":"订高铁票"},'
            '"missing_info":["todo_target","todo_action"]}'
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="帮我记录一下，我下周要去一趟老家，过清明，到时候还要定高铁票")],
            "user_id": 1,
            "pending_operation": None,
            "pending_clarifications": None,
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": None,
            "response_message": None,
            "clarify_fsm_state": "idle",
            "clarify_round": 0,
        }

        result = analyze_intent(state)

        pending = result.get("pending_operation", {})
        assert pending.get("action") == "create"
        assert pending.get("needs_clarification") is False
        assert "确认" in str(result.get("response_message") or "")

        pending_data = pending.get("data") or {}
        assert "回老家过清明" in str(pending_data.get("title") or "")
        assert "订高铁票" in str(pending_data.get("description") or "")

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
    def test_single_todo_preference_should_stop_repeat_clarify(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        """用户明确“一个待办”时，应从澄清态收敛到确认态。"""
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"create","action_state":"need_clarify",'
            '"response_message":"好的，我一次只能先记录一个待办。你要记录哪一个？",'
            '"extracted_info":{},'
            '"missing_info":["todo_target","todo_action"]}'
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="先就帮我记录一下。一个待办")],
            "user_id": 1,
            "pending_operation": {
                "action": "create",
                "data": {"title": "回老家过清明", "description": "包含订高铁票"},
                "needs_clarification": True,
            },
            "pending_clarifications": ["目标待办", "操作动作"],
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": {"title": "回老家过清明"},
            "response_message": None,
            "clarify_fsm_state": "asked_target",
            "clarify_round": 1,
        }

        result = analyze_intent(state)

        pending = result.get("pending_operation", {})
        assert pending.get("action") == "create"
        assert pending.get("needs_clarification") is False
        assert result.get("clarify_fsm_state") == "done"
        assert result.get("clarify_round") == 0
        assert "确认" in str(result.get("response_message") or "")


class TestTodoWorkflowStateSemantics:
    """WS-01 状态字段语义收敛回归。"""

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.is_implicit_reference_message", return_value=False)
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
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
            '"missing_info":["todo_action","todo_action",""]}'
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
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
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


class TestTodoRejectSupplementRecovery:
    """拒绝后补充应恢复创建草稿（需求 §3.4）。"""

    def test_merge_create_draft_with_supplement_should_override_time_location_and_append_desc(self):
        """单元：补充信息应覆盖时间/地点并保留同一草稿上下文。"""
        from app.ai.workflow.todo_graph import _merge_create_draft_with_supplement

        draft = {
            "title": "和张三开会",
            "time": "明天上午9点",
            "location": "陆家嘴",
            "description": "与张三开会",
        }
        supplement = {
            "time": "明天下午3点",
            "location": "会议室A",
            "description": "需要带投影线",
        }

        merged = _merge_create_draft_with_supplement(draft, supplement)

        assert merged["title"] == "和张三开会"
        assert merged["time"] == "明天下午3点"
        assert merged["location"] == "会议室A"
        assert "与张三开会" in str(merged.get("description") or "")
        assert "需要带投影线" in str(merged.get("description") or "")

    def test_global_todo_state_should_include_response_message(self):
        """全局 Todo 状态契约必须包含 response_message，避免 clarify 节点丢字段。"""
        from app.ai import state as ai_state

        assert "response_message" in ai_state.TodoAgentState.__annotations__

    def test_normalize_missing_info_should_only_accept_canonical_slots(self):
        """missing_info 仅接受 canonical slot，非法字段应被忽略。"""
        from app.ai.workflow.todo_graph import _normalize_missing_info

        normalized = _normalize_missing_info(["target_todo", "todo_id", "time_range", "todo_action"])
        assert normalized == ["时间范围", "操作动作"]

    def test_normalize_missing_slots_should_return_canonical_slots(self):
        """missing_info 内部处理应统一为 canonical slot。"""
        from app.ai.workflow.todo_graph import _normalize_missing_slots

        normalized_slots = _normalize_missing_slots(
            ["todo_target", "todo_target", "time_range", "todo_action", "target_todo", "操作动作"]
        )
        assert normalized_slots == ["todo_target", "time_range", "todo_action"]

    def test_normalize_missing_slots_should_drop_non_canonical_values(self):
        """strict 模式下，非 canonical 槽位必须被丢弃。"""
        from app.ai.workflow.todo_graph import _normalize_missing_slots

        normalized_slots = _normalize_missing_slots(["target_todo", "todo_id", "目标待办", "时间范围"])
        assert normalized_slots == []

    def test_clarify_goal_template_missing_info_should_use_canonical_slots(self):
        """Goal 模板中的 clarify 示例必须只使用 canonical slot。"""
        from app.ai.config.goal_templates import GOAL_TEMPLATES

        allowed_slots = {"todo_target", "time_range", "todo_action"}
        examples = GOAL_TEMPLATES["clarify"].few_shot_examples
        for _, expected in examples:
            for slot in expected.get("missing_info", []):
                assert slot in allowed_slots

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
    def test_reject_then_supplement_should_recover_create_draft(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        """场景：创建待办被拒绝后，用户补充信息应恢复同一创建草稿。"""
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"update","action_state":"need_clarify",'
            '"response_message":"我可以帮你把补充信息更新到待办里，你想更新哪一个？",'
            '"extracted_info":{"description":"需要带纸和笔"},'
            '"missing_info":["todo_target"]}'
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [
                HumanMessage(content="明天上午9点去陆家嘴和张三开会"),
                AIMessage(
                    content="好的，我帮你记录这个待办",
                    additional_kwargs={
                        "operation": {
                            "action": "create",
                            "data": {
                                "title": "和张三开会",
                                "time": "明天上午9点",
                                "due_date": "2026-02-19T09:00:00",
                                "location": "陆家嘴",
                                "description": "与张三开会",
                            },
                        }
                    },
                ),
                HumanMessage(content="拒绝"),
                AIMessage(content="好的，已取消操作。有其他需要帮助的吗？"),
                HumanMessage(content="需要带纸和笔"),
            ],
            "user_id": 1,
            "pending_operation": None,
            "pending_clarifications": None,
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": None,
            "response_message": None,
            "clarify_fsm_state": "idle",
            "clarify_round": 0,
        }

        result = analyze_intent(state)

        pending = result.get("pending_operation", {})
        assert pending.get("action") == "create"
        assert pending.get("needs_clarification") is False
        assert result.get("clarify_fsm_state") == "done"

        merged_desc = str((pending.get("data") or {}).get("description") or "")
        assert "与张三开会" in merged_desc
        assert "需要带纸和笔" in merged_desc
        assert "确认创建" in str(result.get("response_message") or "")

    @patch(
        "app.ai.workflow.todo_graph.parse_time_info",
        side_effect=lambda info, constraints=None: (info, constraints),
    )
    @patch("app.ai.workflow.todo_graph.query_existing_todos", return_value="")
    @patch("app.ai.workflow.todo_graph._get_user_id_from_state", return_value=1)
    @patch("app.ai.workflow.todo_graph.get_scene_llm")
    def test_reject_then_supplement_time_location_should_keep_same_create_draft(
        self,
        mock_get_llm,
        _mock_user_id,
        _mock_query,
        _mock_parse_time,
    ):
        """场景：拒绝后补充时间/地点，应恢复同一创建草稿并进入再确认。"""
        from app.ai.workflow.todo_graph import analyze_intent

        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            '{"intent":"update","action_state":"need_clarify",'
            '"response_message":"我可以帮你更新补充信息，你想更新哪一个待办？",'
            '"extracted_info":{"time":"明天下午3点","location":"会议室A","description":"改到明天下午3点，在会议室A开会"},'
            '"missing_info":["todo_target"]}'
        )
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [
                HumanMessage(content="明天上午9点和张三在陆家嘴开会"),
                AIMessage(
                    content="好的，我帮你记录这个待办",
                    additional_kwargs={
                        "operation": {
                            "action": "create",
                            "data": {
                                "title": "和张三开会",
                                "time": "明天上午9点",
                                "location": "陆家嘴",
                                "description": "与张三开会",
                            },
                        }
                    },
                ),
                HumanMessage(content="拒绝"),
                AIMessage(content="好的，已取消操作。有其他需要帮助的吗？"),
                HumanMessage(content="改到明天下午3点，在会议室A开会"),
            ],
            "user_id": 1,
            "pending_operation": None,
            "pending_clarifications": None,
            "user_confirmed": None,
            "quick_mode": None,
            "conversation_context": None,
            "current_focus": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": None,
            "response_message": None,
            "clarify_fsm_state": "idle",
            "clarify_round": 0,
        }

        result = analyze_intent(state)

        pending = result.get("pending_operation", {})
        pending_data = pending.get("data") or {}
        assert pending.get("action") == "create"
        assert pending.get("needs_clarification") is False
        assert pending_data.get("title") == "和张三开会"
        assert pending_data.get("time") == "明天下午3点"
        assert pending_data.get("location") == "会议室A"
        assert "确认创建" in str(result.get("response_message") or "")


class TestTodoOperationPayloadHelpers:
    """待办 operation 载荷 helper 测试。"""

    def test_build_operation_additional_kwargs_payload_normalizes_structure(self):
        from app.ai.protocol import build_operation_additional_kwargs_payload

        additional_kwargs = build_operation_additional_kwargs_payload(
            {
                "action": " update ",
                "data": "invalid",
                "summary": "更新待办",
            }
        )

        assert additional_kwargs == {
            "operation": {
                "action": "update",
                "data": {},
                "summary": "更新待办",
            }
        }

    def test_extract_operation_from_ai_message(self):
        from app.ai.protocol import extract_operation_from_ai_message

        message = AIMessage(
            content="确认创建",
            additional_kwargs={
                "operation": {
                    "action": "create",
                    "data": {"title": "项目汇报"},
                }
            },
        )

        operation = extract_operation_from_ai_message(message)
        assert operation == {"action": "create", "data": {"title": "项目汇报"}}

        assert extract_operation_from_ai_message(HumanMessage(content="hello")) is None

    def test_build_todo_operation_payload_for_update(self):
        from app.ai.workflow.todo_graph import _build_todo_operation_payload

        operation_data = _build_todo_operation_payload(
            action="update",
            data={
                "todo_id": 101,
                "resolved_title": "项目汇报",
                "due_date": "2026-02-20 10:00",
                "priority": "高",
            },
            summary="更新待办",
            update_title_fallback="待办",
        )

        assert operation_data["action"] == "update"
        assert operation_data["target_task"] == {"id": 101, "title": "项目汇报"}
        assert operation_data["diff"] == {
            "due_date": {"old": None, "new": "2026-02-20 10:00"},
            "priority": {"old": None, "new": "高"},
        }

    def test_build_todo_operation_payload_for_delete(self):
        from app.ai.workflow.todo_graph import _build_todo_operation_payload

        operation_data = _build_todo_operation_payload(
            action="delete",
            data={
                "todo_id": 102,
                "title": "回访客户",
            },
            summary="删除待办",
            update_title_fallback="待办",
        )

        assert operation_data["action"] == "delete"
        assert operation_data["target_task"] == {"id": 102, "title": "回访客户"}
        assert "diff" not in operation_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
