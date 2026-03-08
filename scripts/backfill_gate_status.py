#!/usr/bin/env python3
"""Gate 门禁结果自动回填工具。

用途：
1. 执行 Gate 统一命令（pytest/tsc/lint/docs_guard）；
2. 解析关键结果；
3. 优先回写到 `vk_cards.json.gate_results`；
4. 同步自动生成 `parallel_plan.md` 人类可读总览。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from render_parallel_plan import (  # noqa: E402
    dump_json,
    ensure_parallel_plan_source,
    load_json,
    render_parallel_plan,
    resolve_parallel_plan_path,
)


@dataclass
class CommandResult:
    command: str
    return_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


def run_command(command: str, cwd: Path | None = None) -> CommandResult:
    process = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    return CommandResult(
        command=command,
        return_code=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
    )


def resolve_baseline_branch(project_root: Path, preferred_branch: str | None = None) -> str:
    candidates = [preferred_branch] if preferred_branch else ["main", "master"]
    for branch in candidates:
        if not branch:
            continue
        result = run_command(f"git rev-parse --verify {branch}", cwd=project_root)
        if result.return_code == 0:
            return branch

    expected = preferred_branch or "main/master"
    raise SystemExit(
        f"无法定位基线分支（{expected}）。请先同步本地分支，或使用 --baseline-branch 显式指定。"
    )


def ensure_head_contains_baseline(project_root: Path, baseline_branch: str) -> None:
    baseline_head_result = run_command(
        f"git rev-parse --verify {baseline_branch}",
        cwd=project_root,
    )
    if baseline_head_result.return_code != 0:
        raise SystemExit(
            f"无法读取基线分支 `{baseline_branch}` HEAD：{baseline_head_result.output or 'unknown error'}"
        )

    baseline_head = baseline_head_result.stdout.strip()
    contains_result = run_command(
        f"git merge-base --is-ancestor {baseline_head} HEAD",
        cwd=project_root,
    )

    if contains_result.return_code == 0:
        short_sha = baseline_head[:8]
        print(f"基线检查通过：HEAD 已包含 `{baseline_branch}`@{short_sha}")
        return

    if contains_result.return_code == 1:
        short_sha = baseline_head[:8]
        raise SystemExit(
            "Gate 硬拦截：当前分支未包含基线最新提交 "
            f"`{baseline_branch}`@{short_sha}。请先 rebase/merge 后重试；"
            "若确需跳过，请显式传入 --skip-baseline-check。"
        )

    raise SystemExit(
        "基线祖先检查执行失败："
        f"{contains_result.output or f'exit={contains_result.return_code}'}"
    )


def parse_pytest_summary(output: str) -> tuple[str, dict[str, int]]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    summary_line = ""
    for line in reversed(lines):
        if " in " in line and re.search(r"\b(passed|failed|errors?|skipped|warnings?)\b", line):
            summary_line = line
            break

    counts: dict[str, int] = {}
    for number, label in re.findall(
        r"(\d+)\s+(passed|failed|error|errors|skipped|warning|warnings)",
        summary_line,
    ):
        key = "error" if label in {"error", "errors"} else label.rstrip("s")
        counts[key] = counts.get(key, 0) + int(number)

    return summary_line, counts


def parse_lint_warning_count(output: str) -> int:
    return len(re.findall(r"Warning:", output))


def format_pytest_status(result: CommandResult) -> str:
    summary_line, counts = parse_pytest_summary(result.output)
    if result.return_code == 0:
        passed = counts.get("passed")
        if passed is not None:
            return f"通过（{passed} passed）"
        return "通过"

    failed = counts.get("failed", 0)
    errors = counts.get("error", 0)
    skipped = counts.get("skipped", 0)
    pieces = []
    if failed:
        pieces.append(f"{failed} failed")
    if errors:
        pieces.append(f"{errors} error")
    if skipped:
        pieces.append(f"{skipped} skipped")

    if pieces:
        return f"失败（{', '.join(pieces)}）"
    if summary_line:
        return f"失败（{summary_line}）"
    return f"失败（exit={result.return_code}）"


def format_simple_status(result: CommandResult, warning_count: int | None = None) -> str:
    if result.return_code == 0:
        if warning_count is not None:
            return f"通过（{warning_count} warning）"
        return "通过"
    if warning_count is not None:
        return f"失败（exit={result.return_code}, {warning_count} warning）"
    return f"失败（exit={result.return_code}）"


def format_docs_guard_status(stats: dict[str, int]) -> str:
    errors = int(stats.get("errors", 0))
    warnings = int(stats.get("warnings", 0))
    if errors == 0:
        return f"通过（{errors} error, {warnings} warning）"
    return f"失败（{errors} error, {warnings} warning）"


def _resolve_repo_path(raw: str | None, *, project_root: Path) -> Path | None:
    value = str(raw or "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path.resolve()


def resolve_vk_cards_path(*, project_root: Path, cards_path: str | None = None, plan_path: str | None = None) -> Path:
    candidate = _resolve_repo_path(cards_path, project_root=project_root)
    if candidate is not None:
        return candidate

    plan_candidate = _resolve_repo_path(plan_path, project_root=project_root)
    if plan_candidate is not None:
        return (plan_candidate.parent / "vk_cards.json").resolve()

    raise FileNotFoundError("缺少 --cards 或 --plan，无法定位 vk_cards.json")


def _command_payload(
    result: CommandResult,
    *,
    status: str,
    summary: str,
    warnings: int | None = None,
    errors: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": result.command,
        "exit_code": result.return_code,
        "passed": result.return_code == 0,
        "status": status,
        "summary": summary,
    }
    if warnings is not None:
        payload["warnings"] = warnings
    if errors is not None:
        payload["errors"] = errors
    return payload


def build_gate_results_payload(
    *,
    vk_cards_payload: dict[str, Any],
    pytest_result: CommandResult,
    tsc_result: CommandResult,
    lint_result: CommandResult,
    docs_result: CommandResult,
    docs_report: dict[str, Any],
    generated_at: str,
    baseline_branch: str | None,
    baseline_checked: bool,
) -> dict[str, Any]:
    stats = docs_report.get("stats", {}) if isinstance(docs_report, dict) else {}
    docs_errors = int(stats.get("errors", 0))
    docs_warnings = int(stats.get("warnings", 0))
    lint_warnings = parse_lint_warning_count(lint_result.output)

    pytest_status = format_pytest_status(pytest_result)
    pytest_summary, _ = parse_pytest_summary(pytest_result.output)
    tsc_status = format_simple_status(tsc_result)
    lint_status = format_simple_status(lint_result, warning_count=lint_warnings)
    docs_status = format_docs_guard_status({"errors": docs_errors, "warnings": docs_warnings})

    overall_passed = all(
        result.return_code == 0 for result in (pytest_result, tsc_result, lint_result, docs_result)
    )
    conclusion = "Gate 通过，可进入后续收口。" if overall_passed else "Gate 未通过，请修复失败项后重试。"

    return {
        "updated_at": generated_at,
        "generator": "scripts/backfill_gate_status.py",
        "overall_passed": overall_passed,
        "gate_ids": list((vk_cards_payload.get("gate_contract") or {}).get("gate_ids") or []),
        "baseline": {
            "checked": baseline_checked,
            "branch": baseline_branch or "",
            "status": "passed" if baseline_checked else "skipped",
        },
        "checks": {
            "pytest": _command_payload(
                pytest_result,
                status=pytest_status,
                summary=pytest_summary or pytest_status,
            ),
            "tsc": _command_payload(
                tsc_result,
                status=tsc_status,
                summary=tsc_status,
            ),
            "lint": _command_payload(
                lint_result,
                status=lint_status,
                summary=lint_status,
                warnings=lint_warnings,
            ),
            "docs_guard": _command_payload(
                docs_result,
                status=docs_status,
                summary=docs_status,
                warnings=docs_warnings,
                errors=docs_errors,
            ),
        },
        "conclusion": conclusion,
    }


def run_gate_backfill(
    *,
    project_root: Path,
    vk_cards_path: Path,
    parallel_plan_path: Path | None = None,
    pytest_cmd: str = "venv/bin/python -m pytest -q --override-ini addopts='' --maxfail=20",
    tsc_cmd: str = "npx tsc --noEmit",
    lint_cmd: str = "npm run -s lint",
    docs_cmd: str = "venv/bin/python scripts/docs_guard.py --strict",
    baseline_branch: str = "",
    skip_baseline_check: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    vk_cards_path = vk_cards_path.resolve()
    if not vk_cards_path.exists():
        raise FileNotFoundError(f"vk_cards.json 不存在: {vk_cards_path}")

    vk_cards_payload = load_json(vk_cards_path)
    resolved_parallel_plan_path = parallel_plan_path or resolve_parallel_plan_path(
        vk_cards_payload,
        vk_cards_path=vk_cards_path,
        repo_root=project_root,
    )
    baseline_used = ""
    baseline_checked = False

    if not skip_baseline_check:
        baseline_used = resolve_baseline_branch(
            project_root=project_root,
            preferred_branch=baseline_branch.strip() or None,
        )
        ensure_head_contains_baseline(project_root=project_root, baseline_branch=baseline_used)
        baseline_checked = True
    else:
        print("警告：已跳过 Gate 基线硬拦截（--skip-baseline-check）")

    pytest_result = run_command(pytest_cmd, cwd=project_root)
    tsc_result = run_command(tsc_cmd, cwd=project_root / "web")
    lint_result = run_command(lint_cmd, cwd=project_root / "web")

    with tempfile.NamedTemporaryFile(prefix="docs_guard_", suffix=".json", delete=False) as temp_file:
        docs_json_path = Path(temp_file.name)

    docs_command = f"{docs_cmd} --json-out {docs_json_path}"
    docs_result = run_command(docs_command, cwd=project_root)

    docs_report: dict[str, Any] = {}
    if docs_json_path.exists():
        docs_report = json.loads(docs_json_path.read_text(encoding="utf-8"))
        docs_json_path.unlink(missing_ok=True)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    gate_results = build_gate_results_payload(
        vk_cards_payload=vk_cards_payload,
        pytest_result=pytest_result,
        tsc_result=tsc_result,
        lint_result=lint_result,
        docs_result=docs_result,
        docs_report=docs_report,
        generated_at=generated_at,
        baseline_branch=baseline_used,
        baseline_checked=baseline_checked,
    )

    print("Gate 结果摘要:")
    for check_name in ("pytest", "tsc", "lint", "docs_guard"):
        print(f"- {check_name}: {gate_results['checks'][check_name]['status']}")

    if dry_run:
        return {
            "overall_passed": gate_results["overall_passed"],
            "gate_results": gate_results,
            "parallel_plan_path": str(resolved_parallel_plan_path),
        }

    vk_cards_payload["gate_results"] = gate_results
    ensure_parallel_plan_source(
        vk_cards_payload,
        parallel_plan_path=resolved_parallel_plan_path,
        repo_root=project_root,
    )
    dump_json(vk_cards_path, vk_cards_payload)

    rendered_content = render_parallel_plan(vk_cards_payload, generated_at=generated_at)
    resolved_parallel_plan_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_parallel_plan_path.write_text(rendered_content, encoding="utf-8")

    return {
        "overall_passed": gate_results["overall_passed"],
        "gate_results": gate_results,
        "parallel_plan_path": str(resolved_parallel_plan_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="执行 Gate 命令并回写 vk_cards.json，同时自动生成 parallel_plan.md")
    parser.add_argument("--cards", default="", help="vk_cards.json 路径（推荐）")
    parser.add_argument("--plan", default="", help="parallel_plan.md 路径（兼容旧参数，可推导 vk_cards.json）")
    parser.add_argument(
        "--pytest-cmd",
        default="venv/bin/python -m pytest -q --override-ini addopts='' --maxfail=20",
        help="pytest 命令",
    )
    parser.add_argument(
        "--tsc-cmd",
        default="npx tsc --noEmit",
        help="前端 tsc 命令（在 web 目录执行）",
    )
    parser.add_argument(
        "--lint-cmd",
        default="npm run -s lint",
        help="前端 lint 命令（在 web 目录执行）",
    )
    parser.add_argument(
        "--docs-cmd",
        default="venv/bin/python scripts/docs_guard.py --strict",
        help="docs_guard 命令（会自动附加 --json-out）",
    )
    parser.add_argument(
        "--baseline-branch",
        default="",
        help="基线分支名（默认自动探测 main/master）",
    )
    parser.add_argument(
        "--skip-baseline-check",
        action="store_true",
        help="跳过 Gate 基线硬拦截（不推荐）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印结果，不回写 vk_cards.json / parallel_plan.md",
    )

    args = parser.parse_args()
    project_root = Path.cwd().resolve()
    vk_cards_path = resolve_vk_cards_path(project_root=project_root, cards_path=args.cards, plan_path=args.plan)
    plan_override = _resolve_repo_path(args.plan, project_root=project_root) if args.plan else None

    payload = run_gate_backfill(
        project_root=project_root,
        vk_cards_path=vk_cards_path,
        parallel_plan_path=plan_override,
        pytest_cmd=args.pytest_cmd,
        tsc_cmd=args.tsc_cmd,
        lint_cmd=args.lint_cmd,
        docs_cmd=args.docs_cmd,
        baseline_branch=args.baseline_branch,
        skip_baseline_check=args.skip_baseline_check,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("dry-run 模式：未回写 vk_cards.json / parallel_plan.md")

    if not payload["overall_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
