"""Data intent clarify contract 回归。"""

import sys
import types

from langchain_core.messages import HumanMessage

if "app.ai.semantic" not in sys.modules:
    semantic_stub = types.ModuleType("app.ai.semantic")

    def _stub_get_vanna():
        raise RuntimeError("test stub: get_vanna should not be called in analyze_data_intent tests")

    semantic_stub.get_vanna = _stub_get_vanna
    sys.modules["app.ai.semantic"] = semantic_stub

from app.ai.workflow.data_graph import analyze_data_intent




def test_clarify_slot_must_come_from_contract_not_from_llm_text() -> None:
    state = {"messages": [HumanMessage(content="图表")]}
    result = analyze_data_intent(state)

    assert result["data_intent"] == "clarification"
    assert result["last_clarify_slot"] == "metric"
    assert "指标" in result["clarification_needed"]
    assert result["query_context"]["clarify_reason"] == "contract:missing_metric_time"


def test_metric_only_query_must_emit_structured_time_range_clarify_contract() -> None:
    state = {"messages": [HumanMessage(content="贷款余额")]}
    result = analyze_data_intent(state)

    assert result["data_intent"] == "clarification"
    assert result["last_clarify_slot"] == "time_range"
    assert "时间范围" in result["clarification_needed"]
    assert result["query_context"]["clarify_reason"] == "contract:missing_time_range"
    assert result["query_context"]["intent_decision"] == "needs_clarification"
    assert result["query_context"]["intent_safe_to_execute"] is False
