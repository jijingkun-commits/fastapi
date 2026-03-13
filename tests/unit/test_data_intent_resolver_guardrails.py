"""Data intent resolver / guardrail 回归测试。"""

from app.ai.router.data_intent_contract import build_data_intent_contract
from app.ai.router.data_intent_resolver import resolve_data_intent


def test_resolve_data_intent_sets_safe_to_execute_when_truth_sources_match() -> None:
    contract = build_data_intent_contract(
        decision="accept",
        route="visualization",
        confidence=0.88,
        reason_code="multi_signal_accept",
        evidence_codes=["metric_metadata_support:贷款余额", "keyword_candidate.dimension:分行"],
        slots={
            "metric": "贷款余额",
            "time_range": "2025-06-30",
            "dimensions": ["分行"],
            "chart_type": "柱状图",
            "top_n": 10,
        },
        safe_to_execute=False,
    )

    resolved = resolve_data_intent(
        contract,
        user_text="按分行统计贷款余额前10名，画柱状图",
        metric_source_fetcher=lambda name: {
            "metric_id": "loan_balance",
            "metric_name": name,
            "query_template": "SELECT 1",
            "source": "t_metric_definition",
        },
        dimension_source_fetcher=lambda names: [
            {
                "requested": item,
                "canonical": item,
                "column_name": "branch_name",
                "source": "t_meta_columns",
            }
            for item in names
        ],
    )

    assert resolved["decision"] == "accept"
    assert resolved["safe_to_execute"] is True
    assert resolved["slots"]["metric"] == "贷款余额"
    assert resolved["slots"]["dimensions"] == ["分行"]
    assert resolved["resolved_sources"] == {
        "metric": "t_metric_definition",
        "dimensions": "t_meta_columns",
    }



def test_resolve_data_intent_blocks_unknown_dimension() -> None:
    contract = build_data_intent_contract(
        decision="accept",
        route="detail_query",
        confidence=0.81,
        reason_code="multi_signal_accept",
        evidence_codes=["metric_metadata_support:贷款余额", "keyword_candidate.dimension:未知维度"],
        slots={
            "metric": "贷款余额",
            "time_range": "2025-06-30",
            "dimensions": ["未知维度"],
        },
        safe_to_execute=False,
    )

    resolved = resolve_data_intent(
        contract,
        user_text="按未知维度统计贷款余额",
        metric_source_fetcher=lambda name: {
            "metric_id": "loan_balance",
            "metric_name": name,
            "query_template": "SELECT 1",
            "source": "t_metric_definition",
        },
        dimension_source_fetcher=lambda _names: [],
    )

    assert resolved["safe_to_execute"] is False
    assert resolved["reason_code"] == "dimension_not_whitelisted"
    assert resolved["blocked_by"] == ["dimension_not_whitelisted"]


def test_resolve_data_intent_requires_time_range_before_safe_execute() -> None:
    contract = build_data_intent_contract(
        decision="accept",
        route="metric_query",
        confidence=0.74,
        reason_code="metric_supported_accept",
        evidence_codes=["metric_metadata_support:贷款余额"],
        slots={
            "metric": "贷款余额",
            "time_range": None,
            "dimensions": [],
        },
        safe_to_execute=False,
    )

    resolved = resolve_data_intent(
        contract,
        user_text="贷款余额",
        metric_source_fetcher=lambda name: {
            "metric_id": "loan_balance",
            "metric_name": name,
            "query_template": "SELECT 1",
            "source": "t_metric_definition",
        },
    )

    assert resolved["decision"] == "needs_clarification"
    assert resolved["route"] == "clarification"
    assert resolved["reason_code"] == "missing_time_range"
    assert resolved["safe_to_execute"] is False
    assert resolved["blocked_by"] == ["missing_time_range"]
    assert resolved["resolved_sources"] == {"metric": "t_metric_definition"}
    assert resolved["clarify"] == {
        "target_slot": "time_range",
        "reason_code": "missing_time_range",
        "prompt_template_key": "ask_time_range",
    }
