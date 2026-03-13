"""Data intent router llm-shadow 对账回归测试。"""

import asyncio
import sys
import types

import pytest
from langchain_core.messages import HumanMessage

from app.ai.router.data_intent_router import shadow_compare_async
from app.ai.router.data_intent_contract import build_data_intent_contract

if "app.ai.semantic" not in sys.modules:
    semantic_stub = types.ModuleType("app.ai.semantic")

    def _stub_get_vanna():
        raise RuntimeError("test stub: get_vanna should not be called in llm-shadow tests")

    semantic_stub.get_vanna = _stub_get_vanna
    sys.modules["app.ai.semantic"] = semantic_stub

from app.ai.workflow import data_graph


async def _shadow_runner(_text: str) -> dict:
    return {
        "decision": "needs_clarification",
        "route": "clarification",
        "confidence": 0.42,
        "reason_code": "shadow_disagrees",
        "evidence_codes": ["llm_shadow_vote"],
        "conflict_codes": ["decision_mismatch"],
        "slots": {},
        "safe_to_execute": False,
        "clarify": {
            "target_slot": "metric",
            "reason_code": "shadow_disagrees",
            "prompt_template_key": "ask_metric_time_range",
        },
    }



def test_shadow_compare_async_reports_diff_without_overriding_primary() -> None:
    primary = {
        "decision": "accept",
        "route": "metric_query",
        "confidence": 0.91,
        "reason_code": "rule_primary_accept",
        "evidence_codes": ["metric_metadata_support", "resolver_precheck_support"],
        "conflict_codes": [],
        "slots": {"metric": "贷款余额"},
        "safe_to_execute": False,
    }

    shadow = asyncio.run(
        shadow_compare_async(
            user_text="查询贷款余额",
            primary_contract=primary,
            shadow_runner=_shadow_runner,
        )
    )

    assert primary["decision"] == "accept"
    assert shadow["status"] == "mismatch"
    assert shadow["shadow_decision"] == "needs_clarification"
    assert "decision" in shadow["diff_fields"]


@pytest.mark.asyncio
async def test_analyze_data_intent_schedules_shadow_compare_nonblocking(monkeypatch) -> None:
    primary_contract = build_data_intent_contract(
        decision="accept",
        route="metric_query",
        confidence=0.91,
        reason_code="rule_primary_accept",
        evidence_codes=[
            "metric_metadata_support:贷款余额",
            "resolver_precheck_support.time:2025-06-30",
        ],
        slots={
            "metric": "贷款余额",
            "time_range": "2025-06-30",
            "dimensions": [],
            "ranking": {},
        },
        safe_to_execute=True,
    )

    monkeypatch.setattr(data_graph, "decide_data_intent", lambda *args, **kwargs: primary_contract)
    monkeypatch.setattr(
        data_graph,
        "resolve_data_intent",
        lambda contract, **kwargs: {
            **contract,
            "safe_to_execute": True,
            "resolved_sources": {"metric": "t_metric_definition"},
        },
    )
    monkeypatch.setattr(
        data_graph,
        "_resolve_data_intent_shadow_settings",
        lambda: {"intent_mode": "model_primary", "intent_shadow_enabled": True},
    )
    monkeypatch.setattr(data_graph, "_build_data_intent_shadow_runner", lambda _ctx: _shadow_runner)

    captured: list[dict] = []
    monkeypatch.setattr(
        data_graph,
        "_record_data_intent_shadow_compare_result",
        lambda result: captured.append(result),
    )

    result = data_graph.analyze_data_intent({"messages": [HumanMessage(content="查询2025-06-30贷款余额")]})

    assert result["query_context"]["intent_decision"] == "accept"
    assert result["query_context"]["analysis"]["shadow_status"] == "scheduled_nonblocking"

    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert captured
    assert captured[0]["status"] == "mismatch"
    assert captured[0]["shadow_decision"] == "needs_clarification"
