"""知识库检索离线评测脚本。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any, Dict, List

DEFAULT_DATASET_PATH = Path("tests/fixtures/kb_offline_eval_cases.json")
DEFAULT_BASELINE_PATH = Path("tests/fixtures/kb_offline_eval_baseline.json")
DEFAULT_OUTPUT_PATH = Path("tests/artifacts/kb_offline_eval_result.json")

STAGE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "default": {
        "min_pass_rate": 0.8,
        "min_avg_relevance": 0.8,
        "max_error_citation_rate": 0.05,
    },
    "gate": {
        "min_pass_rate": 0.8,
        "min_avg_relevance": 0.8,
        "max_error_citation_rate": 0.05,
    },
}


def load_json(path: Path) -> Dict[str, Any]:
    """加载 JSON 文件。"""

    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    """保存 JSON 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_str_list(values: Any) -> List[str]:
    """归一化字符串列表，过滤空值。"""

    if not isinstance(values, list):
        return []

    normalized: List[str] = []
    for value in values:
        if not isinstance(value, str):
            continue

        cleaned = value.strip()
        if cleaned:
            normalized.append(cleaned)

    return normalized


def safe_float(value: Any, default: float) -> float:
    """安全转换浮点数。"""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def collect_retrieved_doc_ids(debug_payload: Dict[str, Any]) -> List[str]:
    """提取检索返回的文档 ID。"""

    doc_ids: List[str] = []
    for item in debug_payload.get("retrieved_docs", []):
        if not isinstance(item, dict):
            continue

        doc_id = item.get("doc_id")
        if isinstance(doc_id, str) and doc_id.strip():
            doc_ids.append(doc_id.strip())

    return doc_ids


def collect_citation_doc_ids(debug_payload: Dict[str, Any]) -> List[str]:
    """提取回答中的引用文档 ID。"""

    doc_ids: List[str] = []
    for item in debug_payload.get("citations", []):
        if not isinstance(item, dict):
            continue

        doc_id = item.get("doc_id")
        if isinstance(doc_id, str) and doc_id.strip():
            doc_ids.append(doc_id.strip())

    if doc_ids:
        return doc_ids

    return collect_retrieved_doc_ids(debug_payload)


def collect_evidence_text(debug_payload: Dict[str, Any]) -> str:
    """汇总用于关键词匹配的证据文本。"""

    chunks: List[str] = []

    answer = debug_payload.get("answer")
    if isinstance(answer, str) and answer.strip():
        chunks.append(answer)

    for item in debug_payload.get("retrieved_docs", []):
        if not isinstance(item, dict):
            continue

        for field in ("title", "snippet", "content"):
            value = item.get(field)
            if isinstance(value, str) and value.strip():
                chunks.append(value)

    for item in debug_payload.get("citations", []):
        if not isinstance(item, dict):
            continue

        for field in ("quote", "text"):
            value = item.get(field)
            if isinstance(value, str) and value.strip():
                chunks.append(value)

    return "\n".join(chunks).lower()


def calc_relevance_score(case: Dict[str, Any], debug_payload: Dict[str, Any]) -> float:
    """计算单条样例相关性分数。"""

    expected_docs = set(normalize_str_list(case.get("expected_docs")))
    actual_docs = set(collect_retrieved_doc_ids(debug_payload))

    if expected_docs:
        doc_coverage = len(expected_docs & actual_docs) / len(expected_docs)
    else:
        doc_coverage = 1.0 if not actual_docs else 0.0

    must_have_evidence = normalize_str_list(case.get("must_have_evidence"))
    evidence_text = collect_evidence_text(debug_payload)

    if must_have_evidence:
        evidence_hit = sum(1 for keyword in must_have_evidence if keyword.lower() in evidence_text)
        evidence_coverage = evidence_hit / len(must_have_evidence)
    else:
        evidence_coverage = 1.0

    score = (0.7 * doc_coverage) + (0.3 * evidence_coverage)
    return round(score, 4)


def calc_citation_result(case: Dict[str, Any], debug_payload: Dict[str, Any]) -> Dict[str, Any]:
    """计算引用一致性结果。"""

    expected_docs = set(normalize_str_list(case.get("expected_docs")))
    citation_doc_ids = collect_citation_doc_ids(debug_payload)
    citation_doc_set = set(citation_doc_ids)

    unexpected_docs = sorted(citation_doc_set - expected_docs) if expected_docs else sorted(citation_doc_set)
    missing_expected_docs = sorted(expected_docs - citation_doc_set)

    evidence_text = collect_evidence_text(debug_payload)
    forbidden_hits = [
        keyword for keyword in normalize_str_list(case.get("forbidden_evidence")) if keyword.lower() in evidence_text
    ]

    if expected_docs:
        has_expected_citation = bool(expected_docs & citation_doc_set)
    else:
        has_expected_citation = not citation_doc_set

    citation_mismatch = bool(unexpected_docs or forbidden_hits or not has_expected_citation)

    return {
        "citation_doc_ids": citation_doc_ids,
        "unexpected_citation_docs": unexpected_docs,
        "missing_expected_citation_docs": missing_expected_docs,
        "forbidden_evidence_hits": forbidden_hits,
        "citation_mismatch": citation_mismatch,
    }


def run_single_case(case: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    """执行单条样例，返回可评估调试载荷。"""

    payload_key = "mock_debug" if dry_run else "live_debug"
    debug_payload = case.get(payload_key)
    if not isinstance(debug_payload, dict):
        debug_payload = case.get("mock_debug")

    if not isinstance(debug_payload, dict):
        raise ValueError(f"case {case.get('case_id')} 缺少 {payload_key}/mock_debug")

    return json.loads(json.dumps(debug_payload, ensure_ascii=False))


def evaluate_case(case: Dict[str, Any], debug_payload: Dict[str, Any]) -> Dict[str, Any]:
    """评估单条样例。"""

    grade_rule = case.get("grade_rule") if isinstance(case.get("grade_rule"), dict) else {}
    min_relevance = safe_float(grade_rule.get("min_relevance"), 0.8)
    allow_citation_mismatch = bool(grade_rule.get("allow_citation_mismatch", False))

    relevance_score = calc_relevance_score(case, debug_payload)
    citation_result = calc_citation_result(case, debug_payload)

    passed = relevance_score >= min_relevance and (
        allow_citation_mismatch or not bool(citation_result["citation_mismatch"])
    )

    return {
        "case_id": case.get("case_id"),
        "scenario": case.get("scenario"),
        "query": case.get("query"),
        "expected_docs": normalize_str_list(case.get("expected_docs")),
        "retrieved_doc_ids": collect_retrieved_doc_ids(debug_payload),
        "citation_doc_ids": citation_result["citation_doc_ids"],
        "must_have_evidence": normalize_str_list(case.get("must_have_evidence")),
        "forbidden_evidence": normalize_str_list(case.get("forbidden_evidence")),
        "relevance_score": relevance_score,
        "min_relevance": round(min_relevance, 4),
        "citation_mismatch": bool(citation_result["citation_mismatch"]),
        "error_citation": 1 if citation_result["citation_mismatch"] else 0,
        "unexpected_citation_docs": citation_result["unexpected_citation_docs"],
        "missing_expected_citation_docs": citation_result["missing_expected_citation_docs"],
        "forbidden_evidence_hits": citation_result["forbidden_evidence_hits"],
        "allow_citation_mismatch": allow_citation_mismatch,
        "passed": passed,
    }


def evaluate_cases(cases: List[Dict[str, Any]], dry_run: bool) -> List[Dict[str, Any]]:
    """批量评估样例。"""

    reports: List[Dict[str, Any]] = []

    for case in cases:
        if not isinstance(case, dict):
            continue

        try:
            debug_payload = run_single_case(case, dry_run=dry_run)
            case_report = evaluate_case(case, debug_payload)
        except Exception as exc:  # pragma: no cover - 脚本异常兜底
            case_report = {
                "case_id": case.get("case_id"),
                "scenario": case.get("scenario"),
                "query": case.get("query"),
                "expected_docs": normalize_str_list(case.get("expected_docs")),
                "retrieved_doc_ids": [],
                "citation_doc_ids": [],
                "must_have_evidence": normalize_str_list(case.get("must_have_evidence")),
                "forbidden_evidence": normalize_str_list(case.get("forbidden_evidence")),
                "relevance_score": 0.0,
                "min_relevance": safe_float(
                    case.get("grade_rule", {}).get("min_relevance") if isinstance(case.get("grade_rule"), dict) else 0.8,
                    0.8,
                ),
                "citation_mismatch": True,
                "error_citation": 1,
                "unexpected_citation_docs": [],
                "missing_expected_citation_docs": normalize_str_list(case.get("expected_docs")),
                "forbidden_evidence_hits": [],
                "allow_citation_mismatch": False,
                "passed": False,
                "error": str(exc),
            }

        reports.append(case_report)

    return reports


def compare_with_baseline(summary: Dict[str, Any], baseline_summary: Dict[str, Any]) -> Dict[str, Any]:
    """计算与基线指标的差值。"""

    delta = {
        "pass_rate_delta": round(summary["pass_rate"] - safe_float(baseline_summary.get("pass_rate"), 0.0), 4),
        "avg_relevance_delta": round(
            summary["avg_relevance"] - safe_float(baseline_summary.get("avg_relevance"), 0.0),
            4,
        ),
        "error_citation_rate_delta": round(
            summary["error_citation_rate"] - safe_float(baseline_summary.get("error_citation_rate"), 0.0),
            4,
        ),
    }

    regressed = (
        delta["pass_rate_delta"] < 0
        or delta["avg_relevance_delta"] < 0
        or delta["error_citation_rate_delta"] > 0
    )

    return {
        "baseline": baseline_summary,
        "delta": delta,
        "regressed": regressed,
    }


def build_report(
    dataset: Dict[str, Any],
    case_reports: List[Dict[str, Any]],
    baseline_summary: Dict[str, Any] | None,
    dry_run: bool,
) -> Dict[str, Any]:
    """构建离线评测报告。"""

    total = len(case_reports)
    passed = sum(1 for item in case_reports if item.get("passed"))

    relevance_scores = [safe_float(item.get("relevance_score"), 0.0) for item in case_reports]
    citation_errors = [safe_float(item.get("error_citation"), 0.0) for item in case_reports]

    summary = {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "avg_relevance": round(fmean(relevance_scores), 4) if relevance_scores else 0.0,
        "error_citation_rate": round(fmean(citation_errors), 4) if citation_errors else 0.0,
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": dataset.get("name", "kb_offline_eval"),
            "version": dataset.get("version", "unknown"),
            "source": dataset.get("source", str(DEFAULT_DATASET_PATH)),
        },
        "mode": "dry-run" if dry_run else "live",
        "summary": summary,
        "cases": case_reports,
    }

    if baseline_summary is not None:
        report["baseline_compare"] = compare_with_baseline(summary, baseline_summary)

    return report


def run_evaluation(
    dataset_path: Path,
    output_path: Path,
    baseline_path: Path | None,
    dry_run: bool,
) -> Dict[str, Any]:
    """执行离线评测并写出结果。"""

    dataset = load_json(dataset_path)
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"评测集为空: {dataset_path}")

    case_reports = evaluate_cases(cases, dry_run=dry_run)

    baseline_summary = None
    if baseline_path and baseline_path.exists():
        baseline_payload = load_json(baseline_path)
        if isinstance(baseline_payload, dict) and isinstance(baseline_payload.get("summary"), dict):
            baseline_summary = baseline_payload["summary"]

    report = build_report(dataset=dataset, case_reports=case_reports, baseline_summary=baseline_summary, dry_run=dry_run)
    save_json(output_path, report)
    return report


def resolve_thresholds(
    stage: str,
    min_pass_rate: float | None,
    min_avg_relevance: float | None,
    max_error_citation_rate: float | None,
) -> Dict[str, float]:
    """根据 stage 与显式入参解析门禁阈值。"""

    profile = STAGE_THRESHOLDS.get(stage, STAGE_THRESHOLDS["default"])
    return {
        "min_pass_rate": safe_float(min_pass_rate, profile["min_pass_rate"])
        if min_pass_rate is not None
        else profile["min_pass_rate"],
        "min_avg_relevance": safe_float(min_avg_relevance, profile["min_avg_relevance"])
        if min_avg_relevance is not None
        else profile["min_avg_relevance"],
        "max_error_citation_rate": safe_float(max_error_citation_rate, profile["max_error_citation_rate"])
        if max_error_citation_rate is not None
        else profile["max_error_citation_rate"],
    }


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="知识库检索离线评测")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH, help="评测集 JSON 路径")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="评测报告输出路径")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH, help="基线 JSON 路径")
    parser.add_argument(
        "--stage",
        choices=sorted(STAGE_THRESHOLDS.keys()),
        default="default",
        help="评测阶段；gate 使用统一质量门禁阈值",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅执行样本内 mock_debug，不连接线上服务")
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=None,
        help="最低通过率阈值，低于阈值时返回非零退出码（默认取 stage 配置）",
    )
    parser.add_argument(
        "--min-avg-relevance",
        type=float,
        default=None,
        help="平均相关性阈值，低于阈值时返回非零退出码（默认取 stage 配置）",
    )
    parser.add_argument(
        "--max-error-citation-rate",
        type=float,
        default=None,
        help="错误引用率阈值，高于阈值时返回非零退出码（默认取 stage 配置）",
    )
    parser.add_argument("--update-baseline", action="store_true", help="将本次 summary 回写到 baseline")
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""

    args = parse_args()
    thresholds = resolve_thresholds(
        stage=args.stage,
        min_pass_rate=args.min_pass_rate,
        min_avg_relevance=args.min_avg_relevance,
        max_error_citation_rate=args.max_error_citation_rate,
    )

    report = run_evaluation(
        dataset_path=args.dataset,
        output_path=args.output,
        baseline_path=args.baseline,
        dry_run=args.dry_run,
    )

    summary = report["summary"]
    print(
        "[kb-offline-eval] total={total_cases} passed={passed_cases} pass_rate={pass_rate:.2%} "
        "relevance={avg_relevance:.4f} citation_error={error_citation_rate:.4f}".format(**summary)
    )
    print(
        "[kb-offline-eval] stage={stage} thresholds pass_rate>={min_pass_rate:.4f} "
        "avg_relevance>={min_avg_relevance:.4f} citation_error<={max_error_citation_rate:.4f}".format(
            stage=args.stage,
            **thresholds,
        )
    )

    baseline_compare = report.get("baseline_compare")
    if isinstance(baseline_compare, dict):
        delta = baseline_compare.get("delta", {})
        print(
            "[kb-offline-eval] delta pass_rate={pass_rate_delta:+.4f} "
            "relevance={avg_relevance_delta:+.4f} citation_error={error_citation_rate_delta:+.4f}".format(
                pass_rate_delta=safe_float(delta.get("pass_rate_delta"), 0.0),
                avg_relevance_delta=safe_float(delta.get("avg_relevance_delta"), 0.0),
                error_citation_rate_delta=safe_float(delta.get("error_citation_rate_delta"), 0.0),
            )
        )

    if args.update_baseline:
        baseline_payload = {
            "generated_at": report["generated_at"],
            "dataset": report["dataset"],
            "summary": summary,
        }
        save_json(args.baseline, baseline_payload)
        print(f"[kb-offline-eval] baseline updated: {args.baseline}")

    pass_rate = safe_float(summary.get("pass_rate"), 0.0)
    avg_relevance = safe_float(summary.get("avg_relevance"), 0.0)
    error_citation_rate = safe_float(summary.get("error_citation_rate"), 1.0)

    if pass_rate < thresholds["min_pass_rate"]:
        print(
            "[kb-offline-eval] pass_rate "
            f"{pass_rate:.4f} < min_pass_rate {thresholds['min_pass_rate']:.4f}"
        )
        return 1

    if avg_relevance < thresholds["min_avg_relevance"]:
        print(
            "[kb-offline-eval] avg_relevance "
            f"{avg_relevance:.4f} < min_avg_relevance {thresholds['min_avg_relevance']:.4f}"
        )
        return 1

    if error_citation_rate > thresholds["max_error_citation_rate"]:
        print(
            "[kb-offline-eval] error_citation_rate "
            f"{error_citation_rate:.4f} > max_error_citation_rate {thresholds['max_error_citation_rate']:.4f}"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
