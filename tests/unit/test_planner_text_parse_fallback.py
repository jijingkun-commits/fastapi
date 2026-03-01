"""planner text_parse 三级降级路径测试。"""

from langchain_core.messages import HumanMessage
import pytest

import app.ai.workflow.multi_agent_graph as graph
from app.ai.workflow.multi_agent_graph import _build_planner_intent_plan


class _FakeStructuredLLM:
    def invoke(self, _prompt: str):
        raise RuntimeError("mock-json-object-failed")


class _FakeTextParsePlannerLLM:
    def __init__(self, text_response: str):
        self._text_response = text_response
        self.bind_tools_called = 0
        self.invoke_called = 0

    def with_structured_output(self, _schema):
        return _FakeStructuredLLM()

    def invoke(self, _prompt: str):
        self.invoke_called += 1
        return self._text_response


def test_text_parse_supports_markdown_json_block(monkeypatch) -> None:
    """text_parse 应能解析 markdown 代码块内的 JSON 对象。"""
    monkeypatch.setenv("PLANNER_STRUCTURED_STRATEGY", "legacy_json_object")
    monkeypatch.delenv("PLANNER_DISABLE_JSON_OBJECT", raising=False)
    monkeypatch.setenv("PLANNER_DISABLE_TEXT_PARSE", "false")
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": False, "supports_structured_output": True},
    )

    llm = _FakeTextParsePlannerLLM(
        text_response='```json\n{"goals":[{"kind":"external.lookup","title":"外部信息"}]}\n```'
    )
    state = {"messages": [HumanMessage(content="帮我看下天气")]}

    plan = _build_planner_intent_plan(state, llm=llm, mode="model_primary")

    assert plan["source"] == "model_primary"
    assert plan["planner_strategy"] == "text_parse"
    assert any(goal.get("kind") == "external.lookup" for goal in list(plan.get("goals") or []))


def test_text_parse_disabled_enters_heuristic_fallback(monkeypatch) -> None:
    """关闭 text_parse 后，json_object 失败应回落 heuristic_fallback。"""
    monkeypatch.setenv("PLANNER_STRUCTURED_STRATEGY", "legacy_json_object")
    monkeypatch.delenv("PLANNER_DISABLE_JSON_OBJECT", raising=False)
    monkeypatch.setenv("PLANNER_DISABLE_TEXT_PARSE", "true")
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": False, "supports_structured_output": True},
    )

    llm = _FakeTextParsePlannerLLM(text_response='{"goals":[{"kind":"todo.query"}]}')
    state = {"messages": [HumanMessage(content="帮我看下待办")]}

    plan = _build_planner_intent_plan(state, llm=llm, mode="model_primary")

    assert plan["source"] == "heuristic_fallback"
    assert plan.get("fallback_meta", {}).get("trigger") == "model_failure"


def test_infer_model_intent_plan_via_text_parse_rejects_invalid_json(monkeypatch) -> None:
    """text_parse 输出无效 JSON 时应抛出 invalid_output 错误。"""
    monkeypatch.setenv("PLANNER_DISABLE_TEXT_PARSE", "false")
    llm = _FakeTextParsePlannerLLM(text_response="not-json")
    state = {"messages": [HumanMessage(content="你好")]}

    with pytest.raises(graph._PlannerModelOutputError):
        graph._infer_model_intent_plan_via_text_parse(state, llm)


def test_text_parse_default_disabled_raises_invoke_error(monkeypatch) -> None:
    """默认配置应禁用 text_parse，且不触发模型调用。"""
    monkeypatch.delenv("PLANNER_DISABLE_TEXT_PARSE", raising=False)
    llm = _FakeTextParsePlannerLLM(text_response='{"goals":[{"kind":"general.reply"}]}')
    state = {"messages": [HumanMessage(content="你好")]}

    with pytest.raises(graph._PlannerModelInvokeError):
        graph._infer_model_intent_plan_via_text_parse(state, llm)

    assert llm.invoke_called == 0
