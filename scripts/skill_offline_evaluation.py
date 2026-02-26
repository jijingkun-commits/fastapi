"""Skill 检索离线评测脚本。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Any, Dict, Iterable, List, Tuple

REQUIRED_RETRIEVAL_LOG_FIELDS = ("thread_id", "trace_id", "query_hash", "selected_skill_ids")
DEFAULT_DATASET_PATH = Path("tests/fixtures/skill_retrieval_offline_eval_cases.json")
DEFAULT_BASELINE_PATH = Path("tests/fixtures/skill_retrieval_offline_eval_baseline.json")
DEFAULT_OUTPUT_PATH = Path("tests/artifacts/skill_retrieval_offline_eval_result.json")


def compute_query_hash(query: str) -> str:
    """计算查询哈希，避免在产物中写入原始问题。"""

    import hashlib

    normalized = " ".join(query.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def load_json(path: Path) -> Dict[str, Any]:
    """加载 JSON 文件。"""

    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    """保存 JSON 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def calc_precision_recall(selected: Iterable[str], expected: Iterable[str]) -> Tuple[float, float]:
    """计算单条样例的 precision / recall。"""

    selected_set = {item for item in selected if item}
    expected_set = {item for item in expected if item}

    if not expected_set:
        precision = 1.0 if not selected_set else 0.0
        return precision, 1.0

    hit_count = len(selected_set & expected_set)
    precision = hit_count / len(selected_set) if selected_set else 0.0
    recall = hit_count / len(expected_set)
    return precision, recall


def ensure_retrieval_log(case: Dict[str, Any], debug_payload: Dict[str, Any]) -> Dict[str, Any]:
    """确保每个样例都存在最小可追溯 retrieval_log。"""

    retrieval_log = debug_payload.get("retrieval_log")
    if isinstance(retrieval_log, dict):
        return retrieval_log

    selected_skill_ids = [
        item for item in debug_payload.get("selected_skill_ids", []) if isinstance(item, str) and item.strip()
    ]
    return {
        "thread_id": str(case.get("thread_id") or "-"),
        "trace_id": str(case.get("trace_id") or "-"),
        "query_hash": compute_query_hash(str(case.get("query") or "")),
        "selected_skill_ids": selected_skill_ids,
    }


def evaluate_case(case: Dict[str, Any], debug_payload: Dict[str, Any]) -> Dict[str, Any]:
    """评估单条样例。"""

    expected_selected = [
        item for item in case.get("expected_selected_skill_ids", []) if isinstance(item, str) and item.strip()
    ]
    expected_candidates = [
        item for item in case.get("expected_candidate_contains", []) if isinstance(item, str) and item.strip()
    ]

    selected_skill_ids = [
        item for item in debug_payload.get("selected_skill_ids", []) if isinstance(item, str) and item.strip()
    ]
    candidate_skill_ids = [
        item.get("skill_id")
        for item in debug_payload.get("skill_candidates", [])
        if isinstance(item, dict) and isinstance(item.get("skill_id"), str)
    ]

    retrieval_log = ensure_retrieval_log(case, debug_payload)

    missing_expected = sorted(set(expected_selected) - set(selected_skill_ids))
    missing_candidates = sorted(set(expected_candidates) - set(candidate_skill_ids))

    missing_log_fields = [field for field in REQUIRED_RETRIEVAL_LOG_FIELDS if field not in retrieval_log]
    trace_mismatch = case.get("trace_id") and retrieval_log.get("trace_id") != case.get("trace_id")
    thread_mismatch = case.get("thread_id") and retrieval_log.get("thread_id") != case.get("thread_id")
    selected_sync_ok = retrieval_log.get("selected_skill_ids") == selected_skill_ids

    precision, recall = calc_precision_recall(selected_skill_ids, expected_selected)
    passed = (
        not missing_expected
        and not missing_candidates
        and not missing_log_fields
        and not trace_mismatch
        and not thread_mismatch
        and selected_sync_ok
    )

    return {
        "case_id": case.get("case_id"),
        "scenario": case.get("scenario"),
        "query": case.get("query"),
        "scope": case.get("scope", "global"),
        "expected_selected_skill_ids": expected_selected,
        "actual_selected_skill_ids": selected_skill_ids,
        "candidate_skill_ids": candidate_skill_ids,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "passed": passed,
        "missing_expected": missing_expected,
        "missing_candidates": missing_candidates,
        "missing_retrieval_log_fields": missing_log_fields,
        "trace_mismatch": bool(trace_mismatch),
        "thread_mismatch": bool(thread_mismatch),
        "selected_sync_ok": selected_sync_ok,
        "retrieval_log": retrieval_log,
    }


def run_single_case(case: Dict[str, Any], use_live_search: bool) -> Dict[str, Any]:
    """执行单条样例，返回调试载荷。"""

    if not use_live_search:
        debug_payload = case.get("mock_debug")
        if not isinstance(debug_payload, dict):
            raise ValueError(f"case {case.get('case_id')} 缺少 mock_debug")

        payload = json.loads(json.dumps(debug_payload, ensure_ascii=False))
        payload["retrieval_log"] = ensure_retrieval_log(case, payload)
        return payload

    from app.services.skill_service import SkillService

    return SkillService.search_skills_debug(
        query=str(case.get("query") or ""),
        top_k=int(case.get("top_k") or 2),
        scope=str(case.get("scope") or "global"),
        threshold=case.get("threshold"),
        auto_only=True,
        thread_id=str(case.get("thread_id") or ""),
        trace_id=str(case.get("trace_id") or ""),
    )


def compare_with_baseline(summary: Dict[str, Any], baseline_summary: Dict[str, Any]) -> Dict[str, Any]:
    """计算与 baseline 的差值。"""

    deltas = {
        "pass_rate_delta": round(summary["pass_rate"] - float(baseline_summary.get("pass_rate", 0.0)), 4),
        "avg_precision_delta": round(summary["avg_precision"] - float(baseline_summary.get("avg_precision", 0.0)), 4),
        "avg_recall_delta": round(summary["avg_recall"] - float(baseline_summary.get("avg_recall", 0.0)), 4),
    }
    regressed = any(value < 0 for value in deltas.values())
    return {
        "baseline": baseline_summary,
        "delta": deltas,
        "regressed": regressed,
    }


def build_report(
    dataset: Dict[str, Any],
    case_reports: List[Dict[str, Any]],
    baseline_summary: Dict[str, Any] | None,
    use_live_search: bool,
) -> Dict[str, Any]:
    """构造评测报告。"""

    total = len(case_reports)
    passed = sum(1 for item in case_reports if item.get("passed"))
    pass_rate = round(passed / total, 4) if total else 0.0

    precisions = [float(item.get("precision", 0.0)) for item in case_reports]
    recalls = [float(item.get("recall", 0.0)) for item in case_reports]

    summary = {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "pass_rate": pass_rate,
        "avg_precision": round(fmean(precisions), 4) if precisions else 0.0,
        "avg_recall": round(fmean(recalls), 4) if recalls else 0.0,
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": dataset.get("name", "skill_retrieval_offline_eval"),
            "version": dataset.get("version", "unknown"),
            "source": dataset.get("source", str(DEFAULT_DATASET_PATH)),
        },
        "mode": "live" if use_live_search else "mock",
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
    use_live_search: bool,
) -> Dict[str, Any]:
    """执行离线评测主流程。"""

    dataset = load_json(dataset_path)
    cases = dataset.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"评测集为空: {dataset_path}")

    case_reports: List[Dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue

        try:
            debug_payload = run_single_case(case, use_live_search=use_live_search)
            case_report = evaluate_case(case, debug_payload)
        except Exception as exc:  # pragma: no cover - 脚本异常兜底
            case_report = {
                "case_id": case.get("case_id"),
                "scenario": case.get("scenario"),
                "query": case.get("query"),
                "scope": case.get("scope", "global"),
                "precision": 0.0,
                "recall": 0.0,
                "passed": False,
                "error": str(exc),
                "expected_selected_skill_ids": case.get("expected_selected_skill_ids", []),
                "actual_selected_skill_ids": [],
                "candidate_skill_ids": [],
                "missing_expected": case.get("expected_selected_skill_ids", []),
                "missing_candidates": case.get("expected_candidate_contains", []),
                "missing_retrieval_log_fields": list(REQUIRED_RETRIEVAL_LOG_FIELDS),
                "trace_mismatch": False,
                "thread_mismatch": False,
                "selected_sync_ok": False,
                "retrieval_log": {
                    "thread_id": str(case.get("thread_id") or "-"),
                    "trace_id": str(case.get("trace_id") or "-"),
                    "query_hash": compute_query_hash(str(case.get("query") or "")),
                    "selected_skill_ids": [],
                },
            }

        case_reports.append(case_report)

    baseline_summary = None
    if baseline_path and baseline_path.exists():
        baseline_payload = load_json(baseline_path)
        baseline_summary = baseline_payload.get("summary") if isinstance(baseline_payload, dict) else None
        if not isinstance(baseline_summary, dict):
            baseline_summary = None

    report = build_report(
        dataset=dataset,
        case_reports=case_reports,
        baseline_summary=baseline_summary,
        use_live_search=use_live_search,
    )
    save_json(output_path, report)
    return report


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="Skill 检索离线评测")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH, help="评测集 JSON 路径")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="评测结果输出路径")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH, help="基线 JSON 路径")
    parser.add_argument("--live", action="store_true", help="启用 live 检索（连接真实 SkillService）")
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=1.0,
        help="最低通过率阈值，低于阈值时脚本返回非零退出码",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="将本次 summary 回写到 baseline 文件",
    )
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""

    args = parse_args()
    report = run_evaluation(
        dataset_path=args.dataset,
        output_path=args.output,
        baseline_path=args.baseline,
        use_live_search=args.live,
    )

    summary = report["summary"]
    print(
        "[skill-offline-eval] total={total_cases} passed={passed_cases} pass_rate={pass_rate:.2%} "
        "precision={avg_precision:.4f} recall={avg_recall:.4f}".format(**summary)
    )

    baseline_compare = report.get("baseline_compare")
    if isinstance(baseline_compare, dict):
        delta = baseline_compare.get("delta", {})
        print(
            "[skill-offline-eval] delta pass_rate={pass_rate_delta:+.4f} "
            "precision={avg_precision_delta:+.4f} recall={avg_recall_delta:+.4f}".format(
                pass_rate_delta=float(delta.get("pass_rate_delta", 0.0)),
                avg_precision_delta=float(delta.get("avg_precision_delta", 0.0)),
                avg_recall_delta=float(delta.get("avg_recall_delta", 0.0)),
            )
        )

    if args.update_baseline:
        baseline_payload = {
            "generated_at": report["generated_at"],
            "dataset": report["dataset"],
            "summary": summary,
        }
        save_json(args.baseline, baseline_payload)
        print(f"[skill-offline-eval] baseline updated: {args.baseline}")

    pass_rate = float(summary.get("pass_rate", 0.0))
    if pass_rate < float(args.min_pass_rate):
        print(
            f"[skill-offline-eval] pass_rate {pass_rate:.4f} < min_pass_rate {args.min_pass_rate:.4f}",
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
