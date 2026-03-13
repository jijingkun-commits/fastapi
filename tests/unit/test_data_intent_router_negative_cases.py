"""Data intent router 负样本回归。"""

from app.ai.router.data_intent_router import decide_data_intent



def test_dimension_word_inside_unrelated_phrase_must_not_force_dimension_route() -> None:
    contract = decide_data_intent(
        "帮我看看贷款余额，顺便提一下分行开会的事",
        metric_catalog=[{"metric_name": "贷款余额", "aliases": ["贷款"]}],
        dimension_catalog=[{"name": "分行"}],
    )

    assert contract["decision"] == "accept"
    assert contract["route"] == "metric_query"
    assert contract["slots"]["metric"] == "贷款余额"
    assert contract["slots"]["dimensions"] == []



def test_single_keyword_noise_should_be_rejected() -> None:
    contract = decide_data_intent(
        "分行",
        dimension_catalog=[{"name": "分行"}],
    )

    assert contract["decision"] == "reject"
    assert contract["reason_code"] == "insufficient_signal"
