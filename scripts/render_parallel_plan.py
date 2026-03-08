#!/usr/bin/env python3
"""从 vk_cards.json 渲染 parallel_plan.md 人类可读总览。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 根节点不是对象: {path}")
    return payload


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _repo_relative(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(repo_root.resolve()))
    except ValueError:
        return str(resolved)


def _resolve_repo_path(raw: str | None, *, repo_root: Path) -> Path | None:
    value = str(raw or "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path.resolve()


def resolve_parallel_plan_path(
    vk_cards_payload: dict[str, Any],
    *,
    vk_cards_path: Path,
    repo_root: Path,
    override: str | None = None,
) -> Path:
    override_path = _resolve_repo_path(override, repo_root=repo_root)
    if override_path is not None:
        return override_path

    source_files = vk_cards_payload.get("source_files") or {}
    if isinstance(source_files, dict):
        candidate = _resolve_repo_path(source_files.get("parallel_plan"), repo_root=repo_root)
        if candidate is not None:
            return candidate

    return (vk_cards_path.parent / "parallel_plan.md").resolve()


def ensure_parallel_plan_source(
    vk_cards_payload: dict[str, Any],
    *,
    parallel_plan_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    source_files = vk_cards_payload.get("source_files")
    if not isinstance(source_files, dict):
        source_files = {}
        vk_cards_payload["source_files"] = source_files
    source_files["parallel_plan"] = _repo_relative(parallel_plan_path, repo_root)
    return vk_cards_payload


def _as_list(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    return [raw]


def _fmt_list(raw: Any, *, empty: str = "-", sep: str = ", ") -> str:
    items = [str(item).strip() for item in _as_list(raw) if str(item).strip()]
    return sep.join(items) if items else empty


def _fmt_bool(raw: Any) -> str:
    return "true" if bool(raw) else "false"


def _md_escape(value: Any) -> str:
    return str(value or "-").replace("|", "\\|").replace("\n", " ")


def _append_table(lines: list[str], headers: list[str], rows: list[list[Any]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(_md_escape(cell) for cell in row) + " |")
    lines.append("")


def render_parallel_plan(vk_cards_payload: dict[str, Any], *, generated_at: str | None = None) -> str:
    task_key = str(vk_cards_payload.get("task_key") or "").strip()
    plan_title = str(vk_cards_payload.get("plan_title") or task_key or "parallel_plan").strip()
    task_split_dir = str(vk_cards_payload.get("task_split_dir") or "").strip()
    source_files = vk_cards_payload.get("source_files") or {}
    execution_contract = vk_cards_payload.get("execution_contract") or {}
    gate_contract = vk_cards_payload.get("gate_contract") or {}
    automation_contract = vk_cards_payload.get("automation_contract") or {}
    preflight = vk_cards_payload.get("preflight") or {}
    mapping_checks = vk_cards_payload.get("mapping_checks") or {}
    cards = [card for card in _as_list(vk_cards_payload.get("cards")) if isinstance(card, dict)]
    gate_results = vk_cards_payload.get("gate_results") or {}
    generated_label = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = [
        f"# {plan_title} 自动生成总览",
        "",
        "> 本文件由 `vk_cards.json` 自动生成，请勿手工维护为独立真理源。",
        f"> task_key: `{task_key or '-'}`",
        f"> task_split_dir: `{task_split_dir or '-'}`",
        f"> generated_at: `{generated_label}`",
        "",
        "## 1. 执行策略",
        "",
        f"- execution_mode: `{str(vk_cards_payload.get('execution_mode') or '').strip() or '-'}`",
        f"- single_active_card: `{_fmt_bool(vk_cards_payload.get('single_active_card', True))}`",
        f"- card_order: `{_fmt_list(vk_cards_payload.get('card_order'))}`",
        f"- gate_contract.mode: `{str(gate_contract.get('mode') or '').strip() or '-'}`",
        f"- gate_contract.gate_ids: `{_fmt_list(gate_contract.get('gate_ids'))}`",
        f"- gate_contract.depends_on: `{json.dumps(gate_contract.get('depends_on') or {}, ensure_ascii=False)}`",
        f"- auto_done_policy: `{json.dumps(vk_cards_payload.get('auto_done_policy') or {}, ensure_ascii=False)}`",
        f"- execution_contract: `{json.dumps(execution_contract, ensure_ascii=False)}`",
        "",
        "## 2. 来源文件",
        "",
        f"- requirements: `{str(source_files.get('requirements') or '-').strip() or '-'}`",
        f"- implementation_plan: `{str(source_files.get('implementation_plan') or '-').strip() or '-'}`",
        f"- parallel_plan: `{str(source_files.get('parallel_plan') or '-').strip() or '-'}`",
        f"- workstreams_count: `{len(_as_list(source_files.get('workstreams')))}`",
        "",
    ]

    if automation_contract:
        lines.extend(
            [
                "## 3. automation_contract",
                "",
                "```json",
                json.dumps(automation_contract, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## 4. 预检与映射摘要",
            "",
            f"- preflight.card_id: `{str(preflight.get('card_id') or '-').strip() or '-'}`",
            f"- preflight.feature_ids: `{_fmt_list(preflight.get('feature_ids'))}`",
            f"- preflight.required_done_gate: `{_fmt_list(preflight.get('required_done_gate'))}`",
            f"- mapping_checks: `{json.dumps(mapping_checks, ensure_ascii=False)}`",
            "",
            "## 5. 卡片总览",
            "",
        ]
    )

    if cards:
        rows = []
        for card in cards:
            rows.append(
                [
                    card.get("card_id") or "-",
                    card.get("title") or "-",
                    card.get("task_mode") or "-",
                    _fmt_list(card.get("depends_on")),
                    _fmt_list(card.get("feature_ids")),
                    _fmt_list(card.get("task_ids")),
                    card.get("pr_id") or "-",
                    card.get("source_ws_file") or "-",
                ]
            )
        _append_table(
            lines,
            ["card_id", "title", "task_mode", "depends_on", "feature_ids", "task_ids", "pr_id", "source_ws_file"],
            rows,
        )
    else:
        lines.extend(["- 无卡片定义", ""])

    lines.extend(["## 6. Gate 状态", ""])
    if gate_results:
        lines.append(f"- updated_at: `{str(gate_results.get('updated_at') or '-').strip() or '-'}`")
        lines.append(f"- overall_passed: `{_fmt_bool(gate_results.get('overall_passed'))}`")
        lines.append(f"- gate_ids: `{_fmt_list(gate_results.get('gate_ids'))}`")
        lines.append(f"- conclusion: `{str(gate_results.get('conclusion') or '-').strip() or '-'}`")
        lines.append("")
        checks = gate_results.get("checks") or {}
        if isinstance(checks, dict) and checks:
            rows = []
            for check_name in ("pytest", "tsc", "lint", "docs_guard"):
                check_payload = checks.get(check_name) or {}
                rows.append(
                    [
                        check_name,
                        check_payload.get("status") or "-",
                        check_payload.get("exit_code") if "exit_code" in check_payload else "-",
                        check_payload.get("summary") or check_payload.get("command") or "-",
                    ]
                )
            _append_table(lines, ["check", "status", "exit_code", "summary"], rows)
    else:
        lines.extend(["- 待执行", ""])

    workstreams = _as_list(source_files.get("workstreams"))
    if workstreams:
        lines.extend(["## 7. Workstreams 索引", ""])
        for item in workstreams:
            lines.append(f"- `{str(item).strip()}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_parallel_plan_summary(
    vk_cards_path: Path,
    *,
    repo_root: Path,
    parallel_plan_path: Path | None = None,
    generated_at: str | None = None,
) -> Path:
    payload = load_json(vk_cards_path)
    summary_path = parallel_plan_path or resolve_parallel_plan_path(payload, vk_cards_path=vk_cards_path, repo_root=repo_root)
    content = render_parallel_plan(payload, generated_at=generated_at)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(content, encoding="utf-8")
    return summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description="从 vk_cards.json 自动生成 parallel_plan.md 总览")
    parser.add_argument("--cards", required=True, help="vk_cards.json 路径")
    parser.add_argument("--output", default="", help="可选输出路径；默认写回 source_files.parallel_plan 或同目录 parallel_plan.md")
    args = parser.parse_args()

    repo_root = ROOT
    vk_cards_path = _resolve_repo_path(args.cards, repo_root=repo_root)
    if vk_cards_path is None or not vk_cards_path.exists():
        raise FileNotFoundError(f"vk_cards.json 不存在: {args.cards}")
    payload = load_json(vk_cards_path)
    output_path = resolve_parallel_plan_path(payload, vk_cards_path=vk_cards_path, repo_root=repo_root, override=args.output or None)
    payload = ensure_parallel_plan_source(payload, parallel_plan_path=output_path, repo_root=repo_root)
    dump_json(vk_cards_path, payload)
    write_parallel_plan_summary(vk_cards_path, repo_root=repo_root, parallel_plan_path=output_path)
    print(str(output_path))


if __name__ == "__main__":
    main()
