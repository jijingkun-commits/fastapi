"""知识库离线评测脚本测试。"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.data.kb_offline_evaluation import calc_relevance_score, evaluate_case, run_evaluation


def _write_dataset(path: Path, cases: list[dict]) -> None:
    payload = {
        "name": "kb_offline_eval",
        "version": "test",
        "source": "unit",
        "cases": cases,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_calc_relevance_score_should_combine_doc_and_evidence() -> None:
    """相关性评分应同时考虑文档命中与证据关键词。"""

    case = {
        "expected_docs": ["DOC-001"],
        "must_have_evidence": ["字段映射"],
    }
    debug_payload = {
        "retrieved_docs": [
            {
                "doc_id": "DOC-001",
                "snippet": "该能力支持字段映射与失败重试。",
            }
        ],
        "citations": [{"doc_id": "DOC-001", "quote": "支持字段映射。"}],
    }

    assert calc_relevance_score(case, debug_payload) == 1.0


def test_evaluate_case_should_flag_citation_mismatch() -> None:
    """当引用了非期望文档时应标记 citation_mismatch。"""

    case = {
        "case_id": "KB-T-002",
        "query": "审批流程",
        "expected_docs": ["DOC-002"],
        "must_have_evidence": ["审批"],
        "forbidden_evidence": [],
        "grade_rule": {"min_relevance": 0.8},
    }
    debug_payload = {
        "answer": "流程包含审批和发布。",
        "retrieved_docs": [{"doc_id": "DOC-002", "snippet": "流程包含审批和发布。"}],
        "citations": [{"doc_id": "DOC-999", "quote": "另一个文档"}],
    }

    report = evaluate_case(case, debug_payload)

    assert report["citation_mismatch"] is True
    assert report["error_citation"] == 1
    assert "DOC-999" in report["unexpected_citation_docs"]
    assert report["passed"] is False


def test_kb_offline_eval_summary(tmp_path: Path) -> None:
    """离线评测应输出 relevance 与 citation 汇总指标。"""

    dataset_path = tmp_path / "dataset.json"
    baseline_path = tmp_path / "baseline.json"
    output_path = tmp_path / "report.json"

    cases = [
        {
            "case_id": "KB-T-101",
            "scenario": "命中样本",
            "query": "新渠道功能",
            "expected_docs": ["DOC-A"],
            "must_have_evidence": ["批量导入"],
            "forbidden_evidence": ["跳过审批"],
            "grade_rule": {"min_relevance": 0.8},
            "mock_debug": {
                "answer": "支持批量导入并记录失败明细。",
                "retrieved_docs": [{"doc_id": "DOC-A", "snippet": "支持批量导入。"}],
                "citations": [{"doc_id": "DOC-A", "quote": "支持批量导入。"}],
            },
        },
        {
            "case_id": "KB-T-102",
            "scenario": "错引样本",
            "query": "审批时长",
            "expected_docs": ["DOC-B"],
            "must_have_evidence": ["审批"],
            "forbidden_evidence": [],
            "grade_rule": {"min_relevance": 0.8},
            "mock_debug": {
                "answer": "文档只提到通知，不包含审批。",
                "retrieved_docs": [{"doc_id": "DOC-X", "snippet": "仅包含通知说明。"}],
                "citations": [{"doc_id": "DOC-X", "quote": "仅包含通知说明。"}],
            },
        },
    ]
    _write_dataset(dataset_path, cases)

    baseline_payload = {
        "summary": {
            "total_cases": 2,
            "passed_cases": 1,
            "failed_cases": 1,
            "pass_rate": 0.5,
            "avg_relevance": 0.65,
            "error_citation_rate": 0.5,
        }
    }
    baseline_path.write_text(json.dumps(baseline_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = run_evaluation(
        dataset_path=dataset_path,
        output_path=output_path,
        baseline_path=baseline_path,
        dry_run=True,
    )

    assert output_path.exists()
    assert report["summary"]["total_cases"] == 2
    assert report["summary"]["passed_cases"] == 1
    assert report["summary"]["failed_cases"] == 1
    assert report["summary"]["avg_relevance"] == 0.65
    assert report["summary"]["error_citation_rate"] == 0.5
    assert report["baseline_compare"]["delta"]["pass_rate_delta"] == 0.0
    assert report["baseline_compare"]["delta"]["avg_relevance_delta"] == 0.0
    assert report["baseline_compare"]["delta"]["error_citation_rate_delta"] == 0.0
