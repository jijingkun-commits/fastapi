"""Data intent router contract 回归测试。"""

from app.ai.router.data_intent_router import build_candidate_signals, decide_data_intent


def test_single_lexical_signal_cannot_accept_without_frame_support() -> None:
    contract = decide_data_intent(
        "按分行",
        metric_catalog=[{"metric_name": "贷款余额", "aliases": ["贷款"]}],
        dimension_catalog=[{"name": "分行"}],
    )

    assert contract["decision"] == "reject"
    assert contract["reason_code"] == "single_lexical_signal_forbidden"
    assert contract["route"] == "detail_query"
    assert contract["safe_to_execute"] is False



def test_multi_signal_query_accepts_visualization_route() -> None:
    contract = decide_data_intent(
        "按分行统计贷款余额前10名，画柱状图",
        metric_catalog=[{"metric_name": "贷款余额", "aliases": ["贷款", "放款余额"]}],
        dimension_catalog=[{"name": "分行"}],
    )

    assert contract["decision"] == "accept"
    assert contract["route"] == "visualization"
    assert contract["slots"]["metric"] == "贷款余额"
    assert contract["slots"]["dimensions"] == ["分行"]
    assert contract["slots"]["chart_type"] == "柱状图"
    assert contract["slots"]["top_n"] == 10
    assert contract["safe_to_execute"] is False



def test_frame_supported_supplement_can_accept_single_new_signal() -> None:
    contract = decide_data_intent(
        "改成图看看",
        session_frame={
            "metric": "贷款余额",
            "time_range": "2025-06-30",
            "dimensions": ["分行"],
        },
    )

    assert contract["decision"] == "accept"
    assert contract["route"] == "visualization"
    assert contract["reason_code"] == "frame_supported_supplement"
    assert contract["slots"]["metric"] == "贷款余额"
    assert contract["slots"]["time_range"] == "2025-06-30"
    assert contract["slots"]["dimensions"] == ["分行"]



def test_low_signal_chart_request_returns_structured_clarify_contract() -> None:
    contract = decide_data_intent("图表")

    assert contract["decision"] == "needs_clarification"
    assert contract["route"] == "clarification"
    assert contract["clarify"] == {
        "target_slot": "metric",
        "reason_code": "missing_metric_time",
        "prompt_template_key": "ask_metric_time_range",
    }


def test_metadata_substring_must_not_be_promoted_to_dimension_signal() -> None:
    signals = build_candidate_signals(
        "贷款余额",
        metric_catalog=[{"metric_name": "贷款余额", "aliases": ["贷款"]}],
        dimension_catalog=[{"name": "余额"}],
    )
    contract = decide_data_intent(
        "贷款余额",
        metric_catalog=[{"metric_name": "贷款余额", "aliases": ["贷款"]}],
        dimension_catalog=[{"name": "余额"}],
    )

    assert [item["code"] for item in signals] == ["metric_metadata_support:贷款余额"]
    assert contract["reason_code"] == "metric_supported_accept"
    assert contract["evidence_codes"] == ["metric_metadata_support:贷款余额"]
