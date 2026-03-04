"""意图目标分解：模型主判定与兜底策略测试。"""

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

import app.ai.workflow.multi_agent_graph as graph
from app.ai.workflow.multi_agent_graph import (
    _build_planner_intent_plan as _build_intent_plan,
    _infer_initial_intent_plan,
)


def test_infer_initial_intent_plan_avoids_data_goal_for_generic_query_word() -> None:
    """包含“查询”动作词的待办问句，不应误判为 data.query。"""
    state = {"messages": [HumanMessage(content="帮我查询一下今天的待办清单")]}

    plan = _infer_initial_intent_plan(state)
    kinds = [str(goal.get("kind") or "") for goal in list(plan.get("goals") or [])]

    assert "todo.query" in kinds
    assert "data.query" not in kinds
    todo_goal = next(goal for goal in plan["goals"] if goal.get("kind") == "todo.query")
    assert todo_goal["allowed_agents"] == ["todo_expert"]


def test_infer_initial_intent_plan_keeps_data_goal_when_mixed_with_external() -> None:
    """数据查询 + 天气等外部信息并存时，必须同时保留 data 与 external 目标。"""
    state = {
        "messages": [
            HumanMessage(content="1、查询2025年6月30日贷款余额前10名客户\n2、查询嘉兴今天的天气"),
        ]
    }

    plan = _infer_initial_intent_plan(state)
    kinds = [str(goal.get("kind") or "") for goal in list(plan.get("goals") or [])]

    assert kinds == ["data.query", "external.lookup"]

    data_goal = next(goal for goal in plan["goals"] if goal.get("kind") == "data.query")
    external_goal = next(goal for goal in plan["goals"] if goal.get("kind") == "external.lookup")
    assert data_goal["allowed_agents"] == ["data_expert"]
    assert external_goal["allowed_agents"] == []


def test_resolve_decomposed_goals_prefers_model_primary(monkeypatch) -> None:
    """decompose_goals 在模型可用时应优先采用结构化 planner 结果。"""

    def _fake_build_plan(_state, *, llm, mode):
        assert llm is not None
        assert mode == "model_primary"
        return {
            "source": "model_primary",
            "goals": [
                {"goal_id": "GOAL-01", "order": 1, "kind": "data.query", "title": "数据查询", "must_answer": True},
                {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
            ],
        }

    monkeypatch.setattr(graph, "_resolve_intent_planner_settings", lambda _state: {"intent_mode": "model_primary"})
    monkeypatch.setattr(graph, "_build_planner_intent_plan", _fake_build_plan)

    goals, source = graph._resolve_decomposed_goals_for_query(
        "1、查贷款余额前10\n2、查嘉兴天气",
        llm=object(),
    )

    assert source == "model_primary"
    assert [goal["kind"] for goal in goals] == ["data.query", "external.lookup"]


def test_resolve_decomposed_goals_reconcile_explicit_multi_goal(monkeypatch) -> None:
    """显式多目标表达下，若模型漏拆目标，应自动触发规则补齐。"""

    def _fake_build_plan(_state, *, llm, mode):
        return {
            "source": "model_primary",
            "goals": [
                {"goal_id": "GOAL-01", "order": 1, "kind": "data.query", "title": "数据查询", "must_answer": True},
            ],
        }

    def _fake_rule_goals(_query: str):
        return [
            {"goal_id": "GOAL-01", "order": 1, "kind": "data.query", "title": "数据查询", "must_answer": True},
            {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
        ]

    monkeypatch.setattr(graph, "_resolve_intent_planner_settings", lambda _state: {"intent_mode": "model_primary"})
    monkeypatch.setattr(graph, "_build_planner_intent_plan", _fake_build_plan)
    monkeypatch.setattr(graph, "_build_decomposed_goals_for_query", _fake_rule_goals)

    goals, source = graph._resolve_decomposed_goals_for_query(
        "1、查贷款余额前10\n2、查嘉兴天气",
        llm=object(),
    )

    assert source == "model_primary+rule_reconcile"
    assert [goal["kind"] for goal in goals] == ["data.query", "external.lookup"]


def test_build_intent_plan_uses_model_primary_when_available(monkeypatch) -> None:
    """模型路径可用时，应优先使用 model_primary 结果。"""

    def _fake_model_plan(_state, _llm):
        return {
            "version": 1,
            "source": "model_primary",
            "user_query": "先看天气再看待办",
            "goals": [
                {
                    "goal_id": "GOAL-01",
                    "order": 1,
                    "kind": "external.lookup",
                    "title": "外部信息",
                    "must_answer": True,
                    "confidence": 0.88,
                }
            ],
        }

    monkeypatch.setattr(graph, "_infer_model_intent_plan", _fake_model_plan)

    state = {"messages": [HumanMessage(content="先看天气再看待办")]}
    plan = _build_intent_plan(state, llm=object(), mode="model_primary")

    assert plan["source"] == "model_primary"
    assert plan["goals"][0]["kind"] == "external.lookup"
    assert plan["goals"][0]["allowed_agents"] == []


def test_build_intent_plan_fallbacks_when_model_fails(monkeypatch) -> None:
    """模型失败时应回退到 heuristic_fallback，并记录原因。"""

    def _raise_model_error(_state, _llm):
        raise RuntimeError("mock-llm-down")

    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_model_error)

    state = {"messages": [HumanMessage(content="请帮我看下待办")]}
    plan = _build_intent_plan(state, llm=object(), mode="model_primary")

    assert plan["source"] == "heuristic_fallback"
    assert plan.get("fallback_meta", {}).get("reason", "").startswith("planner_model_error:")
    assert any(goal.get("kind") == "todo.query" for goal in list(plan.get("goals") or []))


def test_build_intent_plan_supports_heuristic_only_mode(monkeypatch) -> None:
    """显式指定 heuristic_only 时不调用模型路径。"""

    def _raise_if_called(*_args, **_kwargs):
        raise AssertionError("_infer_model_intent_plan should not be called in heuristic_only mode")

    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_if_called)

    state = {"messages": [HumanMessage(content="请帮我看下待办")]}
    plan = _build_intent_plan(state, llm=object(), mode="heuristic_only")

    assert plan["source"] == "heuristic_only"
    assert any(goal.get("kind") == "todo.query" for goal in list(plan.get("goals") or []))
    assert all("allowed_agents" in goal for goal in list(plan.get("goals") or []))


def test_infer_model_intent_plan_accepts_string_goal_list() -> None:
    """模型仅返回 goals 字符串数组时，仍应完成归一化而非报错。"""

    class _FakeStructuredLLM:
        def invoke(self, _prompt: str):
            return {"goals": ["todo.query", "external.lookup"]}

    class _FakeLLM:
        def with_structured_output(self, _schema):
            return _FakeStructuredLLM()

    state = {"messages": [HumanMessage(content="先查待办 + 再看天气")]}
    plan = graph._infer_model_intent_plan(state, _FakeLLM())

    kinds = [str(goal.get("kind") or "") for goal in list(plan.get("goals") or [])]
    assert kinds == ["todo.query", "external.lookup"]
    assert plan["goals"][0]["allowed_agents"] == ["todo_expert"]


def test_json_object_primary_recovers_validation_error_weak_goals() -> None:
    """structured invoke 阶段抛弱结构校验错时，应在主路径恢复，不触发兜底。"""

    class _FakeStructuredLLM:
        def invoke(self, _prompt: str):
            raise ValidationError.from_exception_data(
                "_IntentPlanModel",
                [
                    {
                        "type": "model_type",
                        "loc": ("goals", 0),
                        "msg": "Input should be an object",
                        "input": "todo.query",
                        "ctx": {"class_name": "_IntentGoalModel"},
                    },
                    {
                        "type": "model_type",
                        "loc": ("goals", 1),
                        "msg": "Input should be an object",
                        "input": "external.lookup",
                        "ctx": {"class_name": "_IntentGoalModel"},
                    },
                ],
            )

    class _FakeLLM:
        def with_structured_output(self, _schema):
            return _FakeStructuredLLM()

    state = {"messages": [HumanMessage(content="先查待办 + 再看天气")]}
    plan = _build_intent_plan(state, llm=_FakeLLM(), mode="model_primary")

    assert plan["source"] == "model_primary"
    assert [goal["kind"] for goal in plan["goals"]] == ["todo.query", "external.lookup"]
    assert plan["goals"][0]["allowed_agents"] == ["todo_expert"]


def test_json_object_primary_unrecoverable_validation_still_fallback() -> None:
    """invoke 阶段遇到不可恢复校验错误时，应维持 invalid_output 兜底。"""

    class _FakeStructuredLLM:
        def invoke(self, _prompt: str):
            raise ValidationError.from_exception_data(
                "_IntentPlanModel",
                [
                    {
                        "type": "model_type",
                        "loc": ("goals", 0),
                        "msg": "Input should be an object",
                        "input": "",
                        "ctx": {"class_name": "_IntentGoalModel"},
                    }
                ],
            )

    class _FakeLLM:
        def with_structured_output(self, _schema):
            return _FakeStructuredLLM()

    state = {"messages": [HumanMessage(content="你好")]}
    plan = _build_intent_plan(state, llm=_FakeLLM(), mode="model_primary")

    assert plan["source"] == "heuristic_fallback"
    assert plan.get("fallback_meta", {}).get("reason_code") == "invalid_output"
