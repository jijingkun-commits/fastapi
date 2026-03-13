"""Data intent router 补充轮回归。"""

from app.ai.router.data_intent_router import decide_data_intent



def test_dimension_supplement_can_reuse_frame_context() -> None:
    contract = decide_data_intent(
        "按分行",
        session_frame={
            "metric": "贷款余额",
            "time_range": "2025-06-30",
        },
        dimension_catalog=[{"name": "分行"}],
    )

    assert contract["decision"] == "accept"
    assert contract["route"] == "detail_query"
    assert contract["slots"]["metric"] == "贷款余额"
    assert contract["slots"]["time_range"] == "2025-06-30"
    assert contract["slots"]["dimensions"] == ["分行"]



def test_chart_supplement_can_reuse_handoff_frame_context() -> None:
    contract = decide_data_intent(
        "改成图看看",
        handoff_frame={
            "metric": "贷款余额",
            "time_range": "2025-06-30",
            "dimensions": ["分行"],
        },
    )

    assert contract["decision"] == "accept"
    assert contract["route"] == "visualization"
    assert contract["slots"]["metric"] == "贷款余额"
