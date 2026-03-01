"""planner fallback reason_code 标准化测试。"""

from langchain_core.messages import HumanMessage

import app.ai.workflow.multi_agent_graph as graph
from app.ai.workflow.multi_agent_graph import _build_planner_intent_plan


def _base_state() -> dict:
    return {"messages": [HumanMessage(content="请帮我看下今天的待办")]}


def test_reason_code_mapping_from_rule_and_trigger() -> None:
    """fallback rule/trigger 应映射到稳定 reason_code。"""
    assert graph._resolve_planner_reason_code(
        fallback_rule_id="planner_fallback.timeout",
        fallback_trigger="timeout",
    ) == "timeout"
    assert graph._resolve_planner_reason_code(
        fallback_rule_id="planner_fallback.invalid_output",
        fallback_trigger="invalid_output",
    ) == "invalid_output"
    assert graph._resolve_planner_reason_code(
        fallback_rule_id="planner_fallback.model_failure",
        fallback_trigger="model_failure",
    ) == "model_failure"
    assert graph._resolve_planner_reason_code(
        fallback_rule_id="planner_fallback.legacy_catch_all",
        fallback_trigger="legacy",
    ) == "legacy"


def test_reason_code_written_when_planner_model_failure(monkeypatch) -> None:
    """模型调用失败时，fallback_meta 必须写入 reason_code=model_failure。"""

    def _raise_model_failure(_state, _llm):
        raise graph._PlannerModelInvokeError("provider unavailable")

    monkeypatch.delenv("ENABLE_INTENT_FALLBACK_GATE", raising=False)
    monkeypatch.setattr(graph, "_infer_model_intent_plan_by_strategy", _raise_model_failure)

    plan = _build_planner_intent_plan(_base_state(), llm=object(), mode="model_primary")

    fallback_meta = plan.get("fallback_meta", {})
    assert plan["source"] == "heuristic_fallback"
    assert fallback_meta.get("fallback_rule_id") == "planner_fallback.model_failure"
    assert fallback_meta.get("trigger") == "model_failure"
    assert fallback_meta.get("reason_code") == "model_failure"


def test_reason_code_written_when_legacy_gate_disabled(monkeypatch) -> None:
    """关闭 fallback gate 时，reason_code 应稳定写入 legacy。"""

    def _raise_unknown(_state, _llm):
        raise KeyError("unexpected bug")

    monkeypatch.setenv("ENABLE_INTENT_FALLBACK_GATE", "false")
    monkeypatch.setattr(graph, "_infer_model_intent_plan_by_strategy", _raise_unknown)

    plan = _build_planner_intent_plan(_base_state(), llm=object(), mode="model_primary")

    fallback_meta = plan.get("fallback_meta", {})
    assert plan["source"] == "heuristic_fallback"
    assert fallback_meta.get("fallback_rule_id") == "planner_fallback.legacy_catch_all"
    assert fallback_meta.get("trigger") == "legacy"
    assert fallback_meta.get("reason_code") == "legacy"
