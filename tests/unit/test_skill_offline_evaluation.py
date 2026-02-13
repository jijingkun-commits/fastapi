"""skill 离线评测脚本测试。"""

import json
from pathlib import Path

from scripts.skill_offline_evaluation import (
    compute_query_hash,
    evaluate_case,
    run_evaluation,
    run_single_case,
)


def _build_dataset(path: Path) -> None:
    payload = {
        "name": "skill_retrieval_offline_eval",
        "version": "test",
        "source": "unit",
        "cases": [
            {
                "case_id": "SK-T-001",
                "scenario": "银行贷款分析",
                "query": "按分行统计贷款余额",
                "scope": "data",
                "thread_id": "thread-a",
                "trace_id": "trace-a",
                "expected_selected_skill_ids": ["sql-expert"],
                "expected_candidate_contains": ["sql-expert"],
                "mock_debug": {
                    "skill_candidates": [
                        {
                            "skill_id": "sql-expert",
                            "final_score": 0.92,
                            "selected": True,
                            "drop_reasons": [],
                        }
                    ],
                    "selected_skill_ids": ["sql-expert"],
                },
            },
            {
                "case_id": "SK-T-002",
                "scenario": "客户明细脱敏",
                "query": "客户证件号明细无权限时返回脱敏",
                "scope": "admin",
                "thread_id": "thread-b",
                "trace_id": "trace-b",
                "expected_selected_skill_ids": ["api-doc"],
                "expected_candidate_contains": ["api-doc"],
                "mock_debug": {
                    "skill_candidates": [
                        {
                            "skill_id": "api-doc",
                            "final_score": 0.84,
                            "selected": True,
                            "drop_reasons": [],
                        }
                    ],
                    "selected_skill_ids": ["api-doc"],
                },
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_run_single_case_should_backfill_retrieval_log() -> None:
    """mock 模式执行样例时应自动补齐 retrieval_log。"""

    case = {
        "case_id": "SK-T-003",
        "query": "按分行统计贷款余额",
        "thread_id": "thread-c",
        "trace_id": "trace-c",
        "mock_debug": {
            "skill_candidates": [{"skill_id": "sql-expert", "selected": True, "drop_reasons": []}],
            "selected_skill_ids": ["sql-expert"],
        },
    }

    payload = run_single_case(case, use_live_search=False)

    retrieval_log = payload["retrieval_log"]
    assert retrieval_log["thread_id"] == "thread-c"
    assert retrieval_log["trace_id"] == "trace-c"
    assert retrieval_log["query_hash"] == compute_query_hash("按分行统计贷款余额")
    assert retrieval_log["selected_skill_ids"] == ["sql-expert"]


def test_evaluate_case_should_detect_missing_retrieval_log_fields() -> None:
    """缺少 trace_id 时样例应判定失败。"""

    case = {
        "case_id": "SK-T-004",
        "scenario": "银行合规边界",
        "query": "客户手机号脱敏",
        "scope": "admin",
        "thread_id": "thread-d",
        "trace_id": "trace-d",
        "expected_selected_skill_ids": ["api-doc"],
        "expected_candidate_contains": ["api-doc"],
    }
    debug_payload = {
        "skill_candidates": [{"skill_id": "api-doc", "selected": True, "drop_reasons": []}],
        "selected_skill_ids": ["api-doc"],
        "retrieval_log": {
            "thread_id": "thread-d",
            "query_hash": compute_query_hash("客户手机号脱敏"),
            "selected_skill_ids": ["api-doc"],
        },
    }

    report = evaluate_case(case, debug_payload)

    assert report["passed"] is False
    assert "trace_id" in report["missing_retrieval_log_fields"]


def test_run_evaluation_should_generate_summary_and_baseline_delta(tmp_path: Path) -> None:
    """离线评测应生成汇总结果，并输出与 baseline 的对比。"""

    dataset_path = tmp_path / "dataset.json"
    baseline_path = tmp_path / "baseline.json"
    output_path = tmp_path / "result.json"

    _build_dataset(dataset_path)

    baseline_payload = {
        "summary": {
            "total_cases": 2,
            "passed_cases": 1,
            "failed_cases": 1,
            "pass_rate": 0.5,
            "avg_precision": 0.5,
            "avg_recall": 0.5,
        }
    }
    baseline_path.write_text(json.dumps(baseline_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = run_evaluation(
        dataset_path=dataset_path,
        output_path=output_path,
        baseline_path=baseline_path,
        use_live_search=False,
    )

    assert output_path.exists()
    assert report["summary"]["total_cases"] == 2
    assert report["summary"]["passed_cases"] == 2
    assert report["summary"]["pass_rate"] == 1.0
    assert report["baseline_compare"]["delta"]["pass_rate_delta"] == 0.5
