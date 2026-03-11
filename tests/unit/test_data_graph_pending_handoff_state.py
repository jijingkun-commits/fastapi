"""DataGraph 状态 schema 回归测试。"""

from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.ai.state import DataAgentState
from app.ai.workflow.data_graph import _extract_handoff_context


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



def test_extract_handoff_context_should_include_contract_metadata():
    """handoff.frame 存在时，应输出 data contract 元信息。"""
    context = _extract_handoff_context({
        "pending_handoff": {
            "target_agent": "data_expert",
            "turn_act_hint": "NEW_QUERY",
            "frame": {
                "query_text": "查询2025-06-30贷款余额前10名客户",
                "metric": "贷款余额",
                "time_range": "2025-06-30",
            },
        }
    })

    assert context["query_text"] == "查询2025-06-30贷款余额前10名客户"
    assert context["expert_input_contract"] == {
        "contract_id": "data_handoff_query_text",
        "contract_version": "v1",
        "target_agent": "data_expert",
        "state_owner": "supervisor",
        "source_fields": ["pending_handoff.frame.query_text"],
    }
