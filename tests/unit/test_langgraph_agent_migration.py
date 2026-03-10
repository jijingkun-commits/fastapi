import pytest

from app.ai.agents import knowledge_agent
from app.ai.workflow import multi_agent_graph


class _StopCreateAgent(RuntimeError):
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
async def test_create_multi_agent_graph_uses_langchain_create_agent_for_supervisor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_create_agent(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        raise _StopCreateAgent("stop after supervisor factory")

    def _deprecated_create_react_agent(*args, **kwargs):
        raise AssertionError("deprecated create_react_agent should not be used")

    monkeypatch.setattr(multi_agent_graph, "get_scene_llm", lambda **_: "fake-llm")
    monkeypatch.setattr(multi_agent_graph, "_create_task_handoff_tool", lambda *args, **kwargs: "handoff-tool")
    monkeypatch.setattr(multi_agent_graph, "_get_supervisor_tools", lambda: ["simple-tool"])
    monkeypatch.setattr(multi_agent_graph, "_create_decompose_goals_tool", lambda _llm: "decompose-tool")
    monkeypatch.setattr(multi_agent_graph, "create_agent", _fake_create_agent, raising=False)
    monkeypatch.setattr(multi_agent_graph, "create_react_agent", _deprecated_create_react_agent, raising=False)

    with pytest.raises(_StopCreateAgent):
        await multi_agent_graph.create_multi_agent_graph()

    assert captured["args"] == ()
    assert captured["kwargs"]["model"] == "fake-llm"
    assert captured["kwargs"]["system_prompt"] == multi_agent_graph.SUPERVISOR_PROMPT
    assert captured["kwargs"]["name"] == "supervisor"
    expected_handoff_count = sum(
        1 for agent_type in multi_agent_graph.AGENT_DESCRIPTIONS if agent_type != multi_agent_graph.AgentType.DATA
    )
    assert captured["kwargs"]["tools"] == [
        *(["handoff-tool"] * expected_handoff_count),
        "decompose-tool",
        "simple-tool",
    ]
