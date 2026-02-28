"""intent fallback 触发网关测试。"""

import pytest
from langchain_core.messages import HumanMessage

import app.ai.workflow.multi_agent_graph as graph
from app.ai.workflow.multi_agent_graph import _build_planner_intent_plan


def _base_state() -> dict:
    return {"messages": [HumanMessage(content="请帮我看下今天的待办")]}


def test_fallback_gate_classifies_model_failure(monkeypatch) -> None:
    """模型调用失败应进入 fallback 并标注 model_failure 规则。"""

    def _raise_model_failure(_state, _llm):
        raise graph._PlannerModelInvokeError("provider unavailable")

    monkeypatch.delenv("ENABLE_INTENT_FALLBACK_GATE", raising=False)
    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_model_failure)

    plan = _build_planner_intent_plan(_base_state(), llm=object(), mode="model_primary")

    assert plan["source"] == "heuristic_fallback"
    meta = plan["fallback_meta"]
    assert meta["fallback_rule_id"] == "planner_fallback.model_failure"
    assert meta["trigger"] == "model_failure"


def test_fallback_gate_classifies_timeout(monkeypatch) -> None:
    """超时异常应进入 timeout 规则。"""

    def _raise_timeout(_state, _llm):
        raise TimeoutError("planner timeout")

    monkeypatch.delenv("ENABLE_INTENT_FALLBACK_GATE", raising=False)
    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_timeout)

    plan = _build_planner_intent_plan(_base_state(), llm=object(), mode="model_primary")

    assert plan["source"] == "heuristic_fallback"
    meta = plan["fallback_meta"]
    assert meta["fallback_rule_id"] == "planner_fallback.timeout"
    assert meta["trigger"] == "timeout"


def test_fallback_gate_classifies_invalid_output(monkeypatch) -> None:
    """非法输出异常应进入 invalid_output 规则。"""

    def _raise_invalid(_state, _llm):
        raise graph._PlannerModelOutputError("invalid schema")

    monkeypatch.delenv("ENABLE_INTENT_FALLBACK_GATE", raising=False)
    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_invalid)

    plan = _build_planner_intent_plan(_base_state(), llm=object(), mode="model_primary")

    assert plan["source"] == "heuristic_fallback"
    meta = plan["fallback_meta"]
    assert meta["fallback_rule_id"] == "planner_fallback.invalid_output"
    assert meta["trigger"] == "invalid_output"


def test_fallback_gate_rejects_unclassified_error_when_enabled(monkeypatch) -> None:
    """兜底网关开启时，未分类异常不应静默 fallback。"""

    def _raise_unclassified(_state, _llm):
        raise KeyError("unexpected bug")

    monkeypatch.delenv("ENABLE_INTENT_FALLBACK_GATE", raising=False)
    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_unclassified)

    with pytest.raises(KeyError):
        _build_planner_intent_plan(_base_state(), llm=object(), mode="model_primary")


def test_fallback_gate_legacy_mode_catches_all(monkeypatch) -> None:
    """关闭兜底网关时，应回到历史 catch-all 兜底。"""

    def _raise_unclassified(_state, _llm):
        raise KeyError("unexpected bug")

    monkeypatch.setenv("ENABLE_INTENT_FALLBACK_GATE", "false")
    monkeypatch.setattr(graph, "_infer_model_intent_plan", _raise_unclassified)

    plan = _build_planner_intent_plan(_base_state(), llm=object(), mode="model_primary")

    assert plan["source"] == "heuristic_fallback"
    meta = plan["fallback_meta"]
    assert meta["fallback_rule_id"] == "planner_fallback.legacy_catch_all"
    assert meta["trigger"] == "legacy"


def test_build_planner_status_message_hides_internal_fallback_reason() -> None:
    """状态文案不应泄露 planner 内部异常细节。"""

    raw_plan = {
        "version": 1,
        "source": "heuristic_fallback",
        "user_query": "先查待办 + 再看天气",
        "goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "todo.query",
                "title": "待办事项",
                "must_answer": True,
                "allowed_agents": ["todo_expert"],
            }
        ],
        "fallback_meta": {
            "reason": "planner_model_error:_PlannerModelOutputError",
            "fallback_rule_id": "planner_fallback.invalid_output",
            "trigger": "invalid_output",
        },
    }
    normalized_plan = {
        "version": 1,
        "source": "heuristic_fallback",
        "user_query": "先查待办 + 再看天气",
        "goals": list(raw_plan["goals"]),
    }

    status_message = graph._build_planner_status_message(
        normalized_plan,
        raw_intent_plan=raw_plan,
    )

    assert "已自动切换规则兜底" in status_message
    assert "planner_model_error" not in status_message
    assert "_PlannerModelOutputError" not in status_message
