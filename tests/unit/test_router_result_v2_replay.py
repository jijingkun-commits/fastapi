"""router_result_v2 data_intent 嵌入与 replay 回归。"""

from app.ai.workflow.data_graph import build_data_query_handoff_frame
from app.ai.workflow.multi_agent_graph import _apply_router_contract_guard, _build_router_result_v2_payload



def test_apply_router_contract_guard_embeds_data_intent_into_route_decision() -> None:
    handoff = {
        "target_agent": "data_expert",
        "frame": build_data_query_handoff_frame("查询2025-06-30按分行统计贷款余额前10名，画柱状图"),
    }
    state = {
        "decomposed_goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "data.query",
                "title": "问数目标",
                "must_answer": True,
                "allowed_agents": ["data_expert"],
            }
        ]
    }

    accepted, blocked, pending = _apply_router_contract_guard([handoff], state=state)

    assert blocked == []
    assert pending == []
    data_intent = accepted[0]["route_decision"]["data_intent"]
    assert data_intent["decision"] == "accept"
    assert data_intent["route"] == "visualization"
    assert data_intent["slots"]["metric"] == "贷款余额"


def test_apply_router_contract_guard_keeps_time_clarify_as_canonical_data_intent() -> None:
    handoff = {
        "target_agent": "data_expert",
        "frame": build_data_query_handoff_frame("贷款余额"),
    }
    state = {
        "decomposed_goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "data.query",
                "title": "问数目标",
                "must_answer": True,
                "allowed_agents": ["data_expert"],
            }
        ]
    }

    accepted, blocked, pending = _apply_router_contract_guard([handoff], state=state)

    assert blocked == []
    assert pending == []
    data_intent = accepted[0]["route_decision"]["data_intent"]
    assert data_intent["decision"] == "needs_clarification"
    assert data_intent["route"] == "clarification"
    assert data_intent["safe_to_execute"] is False
    assert data_intent["clarify"] == {
        "target_slot": "time_range",
        "reason_code": "missing_time_range",
        "prompt_template_key": "ask_time_range",
    }



def test_router_result_v2_payload_keeps_nested_data_intent() -> None:
    payload = _build_router_result_v2_payload(
        accepted_decisions=[
            {
                "goal_id": "GOAL-01",
                "target_agent": "data_expert",
                "dispatch_reason": "compiled_data_goal_frame",
                "priority": 1,
                "blocked_by": [],
                "data_intent": {
                    "decision": "accept",
                    "route": "metric_query",
                    "confidence": 0.8,
                    "reason_code": "multi_signal_accept",
                    "evidence_codes": ["metric_metadata_support:贷款余额"],
                    "conflict_codes": [],
                    "slots": {"metric": "贷款余额"},
                    "safe_to_execute": True,
                },
            }
        ],
        event="intent_router_dispatch_ready",
    )

    assert payload["route_decisions"][0]["data_intent"]["decision"] == "accept"
    assert payload["route_decisions"][0]["data_intent"]["slots"]["metric"] == "贷款余额"
