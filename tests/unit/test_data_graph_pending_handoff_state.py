"""DataGraph 状态 schema 回归测试。"""

from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.ai.state import DataAgentState


class _ProbeState(TypedDict, total=False):
    """最小化测试状态：用于验证未声明字段会被裁剪。"""

    messages: Annotated[list, add_messages]
    known: str


def test_langgraph_drops_unknown_state_key_without_schema_field():
    """基线：未在 schema 中声明的字段会在节点入参中丢失。"""

    captured = {}

    def probe(state: _ProbeState):
        captured["pending_handoff"] = state.get("pending_handoff")
        return {}

    workflow = StateGraph(_ProbeState)
    workflow.add_node("probe", probe)
    workflow.set_entry_point("probe")
    workflow.add_edge("probe", END)

    graph = workflow.compile()
    graph.invoke(
        {
            "messages": [HumanMessage(content="hi")],
            "known": "ok",
            "pending_handoff": {"target_agent": "data_expert"},
        }
    )

    assert captured["pending_handoff"] is None


def test_data_agent_state_keeps_pending_handoff_for_subgraph():
    """DataAgentState 应保留 pending_handoff，供 analyze_data_intent 消费。"""

    captured = {}

    def probe(state: DataAgentState):
        captured["pending_handoff"] = state.get("pending_handoff")
        return {}

    workflow = StateGraph(DataAgentState)
    workflow.add_node("probe", probe)
    workflow.set_entry_point("probe")
    workflow.add_edge("probe", END)

    graph = workflow.compile()
    payload = {
        "messages": [HumanMessage(content="生成柱状图")],
        "pending_handoff": {
            "target_agent": "data_expert",
            "task_description": "在上一轮贷款余额 Top10 结果基础上生成柱状图",
            "turn_act_hint": "SUPPLEMENT",
        },
    }
    result = graph.invoke(payload)

    assert captured["pending_handoff"] is not None
    assert captured["pending_handoff"]["turn_act_hint"] == "SUPPLEMENT"
    assert result.get("pending_handoff", {}).get("target_agent") == "data_expert"

