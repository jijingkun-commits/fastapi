"""Data intent semantic source-of-truth 回归测试。"""

from app.ai.router.data_intent_resolver import (
    resolve_dimension_with_whitelist,
    resolve_metric_source_of_truth,
)


def test_metric_truth_source_must_be_t_metric_definition() -> None:
    resolved = resolve_metric_source_of_truth(
        "贷款余额",
        fetcher=lambda name: {
            "metric_id": "loan_balance",
            "metric_name": name,
            "query_template": "SELECT 1",
            "source": "t_metric_definition",
        },
    )

    assert resolved["metric_name"] == "贷款余额"
    assert resolved["source"] == "t_metric_definition"



def test_dimension_truth_source_must_be_t_meta_columns() -> None:
    resolved = resolve_dimension_with_whitelist(
        ["分行", "支行"],
        fetcher=lambda names: [
            {
                "requested": item,
                "canonical": item,
                "column_name": f"{item}_column",
                "source": "t_meta_columns",
            }
            for item in names
        ],
    )

    assert [item["canonical"] for item in resolved] == ["分行", "支行"]
    assert all(item["source"] == "t_meta_columns" for item in resolved)
