import pytest

from app.ai.agents import knowledge_agent
from app.ai.workflow import multi_agent_graph


class _StopCreateAgent(RuntimeError):
    pass


class _StopCreateReactAgent(RuntimeError):
    pass


def test_create_knowledge_agent_uses_langchain_create_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_create_agent(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "knowledge-agent-sentinel"

    def _deprecated_create_react_agent(*args, **kwargs):
        raise AssertionError("deprecated create_react_agent should not be used")

    monkeypatch.setattr(knowledge_agent, "get_scene_llm", lambda **_: "fake-llm")
    monkeypatch.setattr(knowledge_agent, "create_agent", _fake_create_agent, raising=False)
    monkeypatch.setattr(knowledge_agent, "create_react_agent", _deprecated_create_react_agent, raising=False)

    agent = knowledge_agent.create_knowledge_agent()

    assert agent == "knowledge-agent-sentinel"
    assert captured["kwargs"]["system_prompt"] == knowledge_agent.KNOWLEDGE_AGENT_SYSTEM_PROMPT
    assert captured["kwargs"]["name"] == "knowledge_agent"
    assert captured["kwargs"]["model"] == "fake-llm"


@pytest.mark.asyncio
async def test_create_multi_agent_graph_keeps_runtime_gated_supervisor_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_create_react_agent(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        raise _StopCreateReactAgent("stop after supervisor factory")

    monkeypatch.setattr(multi_agent_graph, "get_scene_llm", lambda **_: "fake-llm")
    monkeypatch.setattr(
        multi_agent_graph,
        "_get_supervisor_handoff_tool_entries",
        lambda: [{"tool": "handoff-tool"}],
        raising=False,
    )
    monkeypatch.setattr(multi_agent_graph, "_get_supervisor_tools", lambda: ["simple-tool"], raising=False)
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name=None: [entry["tool"] if isinstance(entry, dict) else entry.tool for entry in entries],
        raising=False,
    )
    monkeypatch.setattr(multi_agent_graph, "_create_decompose_goals_tool", lambda _llm: "decompose-tool")
    monkeypatch.setattr(multi_agent_graph, "_build_runtime_tool_call_wrapper", lambda entries, agent_name=None: (None, None), raising=False)
    monkeypatch.setattr(multi_agent_graph, "ToolNode", lambda tools, wrap_tool_call=None, awrap_tool_call=None: ("tool-node", tools), raising=False)
    monkeypatch.setattr(multi_agent_graph, "create_react_agent", _fake_create_react_agent, raising=False)

    with pytest.raises(_StopCreateReactAgent):
        await multi_agent_graph.create_multi_agent_graph()

    assert callable(captured["args"][0])
    assert captured["args"][1][0] == "tool-node"
    assert captured["kwargs"]["prompt"] == multi_agent_graph.SUPERVISOR_PROMPT
    assert captured["kwargs"]["name"] == "supervisor"
