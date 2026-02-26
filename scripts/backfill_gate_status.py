#!/usr/bin/env python3
"""Gate 门禁结果自动回填工具。

用途：
1. 执行 Gate 统一命令（pytest/tsc/lint/docs_guard）；
2. 解析关键结果；
3. 自动回填到 parallel_plan.md 的 Gate 状态章节。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


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


def replace_with_fallback_patterns(
    text: str,
    patterns: list[str],
    replacement: str,
    append_hint: str,
) -> str:
    for pattern in patterns:
        compiled = re.compile(pattern, re.DOTALL)
        if compiled.search(text):
            return compiled.sub(replacement, text, count=1)
    return text + f"\n\n{append_hint}\n\n{replacement}\n"


def update_parallel_plan(
    plan_path: Path,
    pytest_status: str,
    tsc_status: str,
    lint_status: str,
    docs_status: str,
    docs_errors: int,
    now_label: str,
) -> None:
    content = plan_path.read_text(encoding="utf-8")

    section_101 = (
        f"### 10.1 WS-G1 结果（自动回填：{now_label}）\n\n"
        f"- `pytest`：{pytest_status}\n"
        f"- `tsc`：{tsc_status}\n"
        f"- `lint`：{lint_status}\n"
        f"- `docs_guard`：{docs_status}\n"
    )

    content = replace_with_fallback_patterns(
        content,
        [
            r"### 10\.1 WS-G1 结果(?:（[^）]*）)?\n[\s\S]*?(?=\n### 10\.2 WS-G2 预期动作)",
            r"### 9\.1 WS-G1 结果(?:（[^）]*）)?\n[\s\S]*?(?=\n### 9\.2 WS-G2 预期动作)",
        ],
        section_101,
        "### 10.1 WS-G1 结果",
    )

    if docs_errors == 0:
        gate_conclusion = "业务与文档门禁通过，可关闭本轮 Gate。"
    else:
        gate_conclusion = "业务门禁可通过但文档门禁未通过，请先修复文档后重跑 Gate。"

    section_11 = (
        f"## 11. Gate 收口结果（自动回填：{now_label}）\n\n"
        "1. `WS-G1` 已执行：\n"
        f"   - `pytest` {pytest_status}\n"
        f"   - `tsc` {tsc_status}\n"
        f"   - `lint` {lint_status}\n"
        f"   - `docs_guard` {docs_status}\n"
        "2. `WS-G2` 已执行：\n"
        f"   - `docs_guard --strict` {docs_status}\n"
        "3. Gate 结论：\n"
        f"   - {gate_conclusion}\n"
    )

    content = replace_with_fallback_patterns(
        content,
        [
            r"## 11\. Gate 收口结果(?:（[^）]*）)?\n[\s\S]*$",
            r"## 10\. Gate 收口结果(?:（[^）]*）)?\n[\s\S]*$",
        ],
        section_11,
        "## 11. Gate 收口结果",
    )

    plan_path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="执行 Gate 命令并自动回填 parallel_plan.md")
    parser.add_argument(
        "--plan",
        required=True,
        help="parallel_plan.md 路径",
    )
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
        help="仅打印结果，不回写文件",
    )

    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        raise FileNotFoundError(f"parallel_plan.md 不存在: {plan_path}")

    project_root = Path.cwd()

    if not args.skip_baseline_check:
        baseline_branch = resolve_baseline_branch(
            project_root=project_root,
            preferred_branch=args.baseline_branch.strip() or None,
        )
        ensure_head_contains_baseline(project_root=project_root, baseline_branch=baseline_branch)
    else:
        print("警告：已跳过 Gate 基线硬拦截（--skip-baseline-check）")

    pytest_result = run_command(args.pytest_cmd, cwd=project_root)
    tsc_result = run_command(args.tsc_cmd, cwd=project_root / "web")
    lint_result = run_command(args.lint_cmd, cwd=project_root / "web")

    with tempfile.NamedTemporaryFile(prefix="docs_guard_", suffix=".json", delete=False) as temp_file:
        docs_json_path = Path(temp_file.name)

    docs_command = f"{args.docs_cmd} --json-out {docs_json_path}"
    docs_result = run_command(docs_command, cwd=project_root)

    docs_report = {}
    if docs_json_path.exists():
        docs_report = json.loads(docs_json_path.read_text(encoding="utf-8"))
        docs_json_path.unlink(missing_ok=True)

    stats = docs_report.get("stats", {})
    docs_errors = int(stats.get("errors", 0))

    pytest_status = format_pytest_status(pytest_result)
    tsc_status = format_simple_status(tsc_result)
    lint_status = format_simple_status(
        lint_result,
        warning_count=parse_lint_warning_count(lint_result.output),
    )
    docs_status = format_docs_guard_status(
        {
            "errors": docs_errors,
            "warnings": int(stats.get("warnings", 0)),
        }
    )

    now_label = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("Gate 结果摘要:")
    print(f"- pytest: {pytest_status}")
    print(f"- tsc: {tsc_status}")
    print(f"- lint: {lint_status}")
    print(f"- docs_guard: {docs_status}")

    if args.dry_run:
        print("dry-run 模式：未回写 parallel_plan.md")
        return

    update_parallel_plan(
        plan_path=plan_path,
        pytest_status=pytest_status,
        tsc_status=tsc_status,
        lint_status=lint_status,
        docs_status=docs_status,
        docs_errors=docs_errors,
        now_label=now_label,
    )

    if any(result.return_code != 0 for result in [pytest_result, tsc_result, lint_result, docs_result]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
