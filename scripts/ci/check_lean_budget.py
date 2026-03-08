#!/usr/bin/env python3
"""Lean Guard：热点文件瘦身门禁。"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class FileStat:
    path: str
    added: int
    deleted: int


@dataclass(frozen=True)
class HotspotRule:
    pattern: str
    max_lines: int
    label: str


HOTSPOT_RULES = (
    HotspotRule(pattern="app/ai/workflow/**/*.py", max_lines=1500, label="workflow"),
    HotspotRule(pattern="app/services/**/*.py", max_lines=800, label="service"),
    HotspotRule(pattern="scripts/**/*.py", max_lines=1000, label="script"),
)

PRIVATE_HELPER_RE = re.compile(r"^\s*(?:async\s+def|def)\s+_[A-Za-z0-9_]+\(")
NESTED_FUNCTION_RE = re.compile(r"^\s{8,}(?:async\s+def|def)\s+[A-Za-z0-9_]+\(")


@dataclass(frozen=True)
class Violation:
    code: str
    path: str
    detail: str


def _normalize_diff_path(path: str) -> str:
    value = path.strip()
    if " => " not in value:
        return value
    if "{" in value and "}" in value:
        prefix, remainder = value.split("{", 1)
        middle, suffix = remainder.split("}", 1)
        _, right = middle.split(" => ", 1)
        return f"{prefix}{right}{suffix}"
    return value.split(" => ", 1)[1].strip()


def run_git_numstat(*, cached: bool, diff_range: str) -> list[FileStat]:
    cmd = ["git", "diff"]
    if cached:
        cmd.append("--cached")
    cmd.extend(["--numstat", "--diff-filter=ACMRTUXB"])
    if diff_range:
        cmd.append(diff_range)

    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff 执行失败")

    stats: list[FileStat] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split("\t")
        if len(parts) < 3:
            continue
        added_raw, deleted_raw = parts[0], parts[1]
        raw_path = parts[-1]
        added = 0 if added_raw == "-" else int(added_raw)
        deleted = 0 if deleted_raw == "-" else int(deleted_raw)
        stats.append(FileStat(path=_normalize_diff_path(raw_path), added=added, deleted=deleted))
    return stats


def matching_rule(path: str) -> HotspotRule | None:
    pure_path = PurePosixPath(path)
    for rule in HOTSPOT_RULES:
        if pure_path.match(rule.pattern):
            return rule
    return None


def current_line_count(path: str) -> int:
    abs_path = ROOT / path
    if not abs_path.exists() or not abs_path.is_file():
        return 0
    text = abs_path.read_text(encoding="utf-8", errors="replace")
    return text.count("\n") + (1 if text else 0)


def run_git_patch(*, cached: bool, diff_range: str, path: str) -> str:
    cmd = ["git", "diff", "-U0"]
    if cached:
        cmd.append("--cached")
    if diff_range:
        cmd.append(diff_range)
    cmd.extend(["--", path])
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git diff patch 执行失败: {path}")
    return result.stdout


def count_added_markers(patch_text: str) -> tuple[int, int]:
    private_helpers = 0
    nested_functions = 0
    for line in patch_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:]
        if PRIVATE_HELPER_RE.match(content):
            private_helpers += 1
        if NESTED_FUNCTION_RE.match(content):
            nested_functions += 1
    return private_helpers, nested_functions


def check_lean_budget(*, stats: list[FileStat], cached: bool, diff_range: str) -> tuple[bool, str]:
    hotspot_stats = [item for item in stats if matching_rule(item.path)]
    if not hotspot_stats:
        return True, "未命中 Lean Guard 热点目录，跳过检查"

    lines: list[str] = ["Lean Guard 检查结果："]
    violations: list[Violation] = []

    for item in hotspot_stats:
        rule = matching_rule(item.path)
        if rule is None:
            continue

        line_count = current_line_count(item.path)
        net_growth = item.added - item.deleted
        patch_text = run_git_patch(cached=cached, diff_range=diff_range, path=item.path)
        private_helpers, nested_functions = count_added_markers(patch_text)
        above_threshold = line_count > rule.max_lines

        lines.append(
            f"- {item.path} [{rule.label}] lines={line_count} threshold={rule.max_lines} "
            f"(+{item.added}/-{item.deleted}, net={net_growth}, private_helpers+={private_helpers}, nested+={nested_functions})"
        )

        if above_threshold and net_growth > 0:
            violations.append(
                Violation(
                    code="LEAN_GUARD_HOTSPOT_GROWTH",
                    path=item.path,
                    detail=f"超阈值热点文件继续净增长（{line_count}>{rule.max_lines}, net={net_growth}）",
                )
            )
        if above_threshold and private_helpers > 0:
            violations.append(
                Violation(
                    code="LEAN_GUARD_PRIVATE_HELPER_ADDED",
                    path=item.path,
                    detail=f"超阈值热点文件新增私有 helper {private_helpers} 个",
                )
            )
        if above_threshold and nested_functions > 0:
            violations.append(
                Violation(
                    code="LEAN_GUARD_NESTED_FUNCTION_ADDED",
                    path=item.path,
                    detail=f"超阈值热点文件新增嵌套函数 {nested_functions} 个",
                )
            )

    if not violations:
        lines.append("Lean Guard 检查通过。")
        return True, "\n".join(lines)

    lines.append("检测到以下违规项：")
    for violation in violations:
        lines.append(f"- [{violation.code}] {violation.path}: {violation.detail}")
    lines.append("要求：外移职责、删除冗余或在非热点文件中承接新增能力，不接受“后续再治理”作为默认口径。")
    return False, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lean Guard：热点文件瘦身门禁")
    parser.add_argument("--cached", action="store_true", help="检查 staged 变更")
    parser.add_argument("--diff-range", default="", help="检查指定 diff range，如 origin/main...HEAD")
    parser.add_argument("--mode", choices=("always", "off"), default="always", help="always=总是检查；off=跳过")
    parser.add_argument("--strict", action="store_true", help="失败时返回非零退出码")
    args = parser.parse_args()

    if args.cached and args.diff_range:
        print("不能同时使用 --cached 与 --diff-range", file=sys.stderr)
        return 2

    if args.mode == "off":
        print("Lean Guard 检查关闭")
        return 0

    try:
        stats = run_git_numstat(cached=args.cached, diff_range=args.diff_range)
    except RuntimeError as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        return 2

    if not stats:
        print("无变更文件，跳过检查")
        return 0

    ok, message = check_lean_budget(stats=stats, cached=args.cached, diff_range=args.diff_range)
    print(message)
    if ok:
        return 0
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
