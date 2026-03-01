"""planner json_object -> text_parse 分级降级链路测试。"""

from langchain_core.messages import AIMessage, HumanMessage

import app.ai.workflow.multi_agent_graph as graph
from app.ai.workflow.multi_agent_graph import _build_planner_intent_plan


class _FakeToolBoundLLM:
    def __init__(self, response, *, should_raise: bool = False):
        self.response = response
        self.should_raise = should_raise

    def invoke(self, _prompt: str):
        if self.should_raise:
            raise RuntimeError("mock-tool-call-failed")
        return self.response


class _FakeStructuredLLM:
    def __init__(self, response, *, should_raise: bool = False):
        self.response = response
        self.should_raise = should_raise

    def invoke(self, _prompt: str):
        if self.should_raise:
            raise RuntimeError("mock-json-object-failed")
        return self.response


class _FakePlannerLLM:
    def __init__(
        self,
        *,
        tool_response,
        structured_response,
        text_response,
        tool_raise: bool = False,
        structured_raise: bool = False,
    ):
        self._tool_response = tool_response
        self._structured_response = structured_response
        self._text_response = text_response
        self._tool_raise = tool_raise
        self._structured_raise = structured_raise
        self.bind_tools_called = 0

    def bind_tools(self, _tools, tool_choice=None):
        self.bind_tools_called += 1
        return _FakeToolBoundLLM(self._tool_response, should_raise=self._tool_raise)

    def with_structured_output(self, _schema):
        return _FakeStructuredLLM(self._structured_response, should_raise=self._structured_raise)

    def invoke(self, _prompt: str):
        return self._text_response


def test_tool_and_json_object_fail_then_text_parse_take_over(monkeypatch) -> None:
    """tool_call 与 json_object 同时失败时，应降级到 text_parse。"""
    monkeypatch.delenv("PLANNER_STRUCTURED_STRATEGY", raising=False)
    monkeypatch.delenv("PLANNER_DISABLE_TOOL_CALL", raising=False)
    monkeypatch.delenv("PLANNER_DISABLE_JSON_OBJECT", raising=False)
    monkeypatch.delenv("PLANNER_DISABLE_TEXT_PARSE", raising=False)
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": True, "supports_structured_output": True},
    )

    llm = _FakePlannerLLM(
        tool_response=AIMessage(content="", tool_calls=[]),
        structured_response={"goals": [{"kind": "general.reply"}]},
        text_response='```json\n{"goals":[{"kind":"todo.query","title":"待办事项"}]}\n```',
        tool_raise=True,
        structured_raise=True,
    )
    state = {"messages": [HumanMessage(content="帮我看下待办")]}

    plan = _build_planner_intent_plan(state, llm=llm, mode="model_primary")

    assert plan["source"] == "model_primary"
    assert plan["planner_strategy"] == "text_parse"
    assert plan.get("planner_strategy_fallback") == "json_object_failed"
    assert any(goal.get("kind") == "todo.query" for goal in plan.get("goals", []))


def test_legacy_strategy_can_fallback_to_text_parse(monkeypatch) -> None:
    """强制 legacy_json_object 时，json_object 失败也可降级到 text_parse。"""
    monkeypatch.setenv("PLANNER_STRUCTURED_STRATEGY", "legacy_json_object")
    monkeypatch.delenv("PLANNER_DISABLE_JSON_OBJECT", raising=False)
    monkeypatch.delenv("PLANNER_DISABLE_TEXT_PARSE", raising=False)
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": False, "supports_structured_output": True},
    )

    llm = _FakePlannerLLM(
        tool_response=AIMessage(content="", tool_calls=[]),
        structured_response={"goals": [{"kind": "general.reply"}]},
        text_response='{"goals":[{"kind":"external.lookup","title":"外部信息"}]}',
        structured_raise=True,
    )
    state = {"messages": [HumanMessage(content="帮我看下天气")]}

    plan = _build_planner_intent_plan(state, llm=llm, mode="model_primary")

    assert llm.bind_tools_called == 0
    assert plan["planner_strategy"] == "text_parse"
    assert plan.get("planner_strategy_fallback") == "json_object_failed"
    assert any(goal.get("kind") == "external.lookup" for goal in plan.get("goals", []))


def test_invalid_text_parse_output_enters_heuristic_fallback(monkeypatch) -> None:
    """text_parse 输出非法 JSON 时，应回退 heuristic_fallback。"""
    monkeypatch.setenv("PLANNER_STRUCTURED_STRATEGY", "legacy_json_object")
    monkeypatch.delenv("PLANNER_DISABLE_JSON_OBJECT", raising=False)
    monkeypatch.delenv("PLANNER_DISABLE_TEXT_PARSE", raising=False)
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": False, "supports_structured_output": True},
    )

    llm = _FakePlannerLLM(
        tool_response=AIMessage(content="", tool_calls=[]),
        structured_response={"goals": [{"kind": "general.reply"}]},
        text_response="not-a-json",
        structured_raise=True,
    )
    state = {"messages": [HumanMessage(content="请看下待办")]}

    plan = _build_planner_intent_plan(state, llm=llm, mode="model_primary")

    assert plan["source"] == "heuristic_fallback"
    assert plan.get("fallback_meta", {}).get("reason_code") == "invalid_output"
