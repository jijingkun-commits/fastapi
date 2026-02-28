"""planner Tool Calling 主路径测试。"""

from langchain_core.messages import AIMessage, HumanMessage

import app.ai.workflow.multi_agent_graph as graph
from app.ai.workflow.multi_agent_graph import _build_planner_intent_plan


class _FakeToolBoundLLM:
    def __init__(self, response, *, should_raise: bool = False):
        self.response = response
        self.should_raise = should_raise
        self.prompt = ""

    def invoke(self, prompt: str):
        self.prompt = prompt
        if self.should_raise:
            raise RuntimeError("mock-tool-call-failed")
        return self.response


class _FakeStructuredLLM:
    def __init__(self, response):
        self.response = response
        self.prompt = ""

    def invoke(self, prompt: str):
        self.prompt = prompt
        return self.response


class _FakePlannerLLM:
    def __init__(self, *, tool_response, structured_response, tool_raise: bool = False):
        self._tool_response = tool_response
        self._structured_response = structured_response
        self._tool_raise = tool_raise
        self.bind_tools_called = 0

    def bind_tools(self, _tools, tool_choice=None):
        self.bind_tools_called += 1
        return _FakeToolBoundLLM(self._tool_response, should_raise=self._tool_raise)

    def with_structured_output(self, _schema):
        return _FakeStructuredLLM(self._structured_response)


def test_tool_call_primary_builds_plan_from_tool_args(monkeypatch) -> None:
    """tool_call 主路径可用时，应优先采用 tool args 产出目标。"""
    monkeypatch.delenv("PLANNER_STRUCTURED_STRATEGY", raising=False)
    monkeypatch.delenv("PLANNER_DISABLE_TOOL_CALL", raising=False)
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": True, "supports_structured_output": True},
    )

    llm = _FakePlannerLLM(
        tool_response=AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call-1",
                    "name": "intent_plan",
                    "args": {"goals": [{"kind": "todo.query", "title": "待办事项"}]},
                }
            ],
        ),
        structured_response={"goals": [{"kind": "general.reply"}]},
    )
    state = {"messages": [HumanMessage(content="帮我看下待办")]}

    plan = _build_planner_intent_plan(state, llm=llm, mode="model_primary")

    assert llm.bind_tools_called == 1
    assert plan["source"] == "model_primary"
    assert plan["planner_strategy"] == "tool_call_primary"
    assert any(goal.get("kind") == "todo.query" for goal in plan.get("goals", []))


def test_tool_call_primary_fallbacks_to_legacy_json_object(monkeypatch) -> None:
    """tool_call 失败后应自动降级到 json_object 路径。"""
    monkeypatch.delenv("PLANNER_STRUCTURED_STRATEGY", raising=False)
    monkeypatch.delenv("PLANNER_DISABLE_TOOL_CALL", raising=False)
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": True, "supports_structured_output": True},
    )

    llm = _FakePlannerLLM(
        tool_response=AIMessage(content="", tool_calls=[]),
        structured_response={"goals": [{"kind": "external.lookup", "title": "外部信息"}]},
        tool_raise=True,
    )
    state = {"messages": [HumanMessage(content="帮我看看天气")]}

    plan = _build_planner_intent_plan(state, llm=llm, mode="model_primary")

    assert plan["source"] == "model_primary"
    assert plan["planner_strategy"] == "legacy_json_object"
    assert plan.get("planner_strategy_fallback") == "tool_call_failed"
    assert any(goal.get("kind") == "external.lookup" for goal in plan.get("goals", []))


def test_disable_tool_call_switch_uses_legacy_path(monkeypatch) -> None:
    """关闭 PLANNER_DISABLE_TOOL_CALL 时，不应尝试 bind_tools。"""
    monkeypatch.setenv("PLANNER_DISABLE_TOOL_CALL", "true")
    monkeypatch.delenv("PLANNER_STRUCTURED_STRATEGY", raising=False)
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": True, "supports_structured_output": True},
    )

    llm = _FakePlannerLLM(
        tool_response=AIMessage(content="", tool_calls=[]),
        structured_response={"goals": [{"kind": "general.reply", "title": "问题回复"}]},
    )
    state = {"messages": [HumanMessage(content="你好")]}

    plan = _build_planner_intent_plan(state, llm=llm, mode="model_primary")

    assert llm.bind_tools_called == 0
    assert plan["planner_strategy"] == "legacy_json_object"
