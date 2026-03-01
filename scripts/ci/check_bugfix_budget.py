#!/usr/bin/env python3
"""Bugfix 最小变更预算检查。

用途：
- 本地 pre-commit / 手动检查（--cached）
- CI PR 检查（--diff-range）
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

BUGFIX_LABEL_KEYWORDS = (
    "bug",
    "bugfix",
    "fix",
    "hotfix",
    "缺陷",
    "修复",
)

BUGFIX_TITLE_RE = re.compile(r"\b(fix|bugfix|hotfix)\b|缺陷|修复", re.IGNORECASE)
BUGFIX_CHECKBOX_RE = re.compile(r"^\s*-\s*\[[xX]\]\s*bugfix\b", re.IGNORECASE | re.MULTILINE)
BUGFIX_CHECKBOX_CN_RE = re.compile(r"^\s*-\s*\[[xX]\]\s*缺陷修复\b", re.MULTILINE)

IGNORED_PREFIXES = (
    "docs/",
    ".cursor/",
    ".claude/",
    ".github/",
    "tmp/",
)
IGNORED_SUFFIXES = (".md", ".mdc", ".txt", ".rst")


@dataclass
class FileStat:
    path: str
    added: int
    deleted: int


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
        parts = raw_line.split("\t", 2)
        if len(parts) != 3:
            continue
        added_raw, deleted_raw, path = parts
        added = 0 if added_raw == "-" else int(added_raw)
        deleted = 0 if deleted_raw == "-" else int(deleted_raw)
        stats.append(FileStat(path=path.strip(), added=added, deleted=deleted))
    return stats


def parse_labels(value: str) -> list[str]:
    if not value:
        return []
    raw = value.replace("\n", ",")
    labels = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return labels


def is_bugfix_pr(*, title: str, body: str, labels: list[str]) -> tuple[bool, str]:
    for label in labels:
        if any(keyword in label for keyword in BUGFIX_LABEL_KEYWORDS):
            return True, f"命中 PR label: {label}"

    if BUGFIX_CHECKBOX_RE.search(body):
        return True, "命中 PR 模板勾选: bugfix"
    if BUGFIX_CHECKBOX_CN_RE.search(body):
        return True, "命中 PR 模板勾选: 缺陷修复"

    if BUGFIX_TITLE_RE.search(title):
        return True, "命中 PR 标题关键词"

    return False, "未命中 bugfix 特征"


def should_count_file(path: str) -> bool:
    normalized = path.strip()
    if not normalized:
        return False
    if normalized.startswith(IGNORED_PREFIXES):
        return False
    if normalized.endswith(IGNORED_SUFFIXES):
        return False
    return True


def summarize_budget(
    *,
    stats: list[FileStat],
    max_files: int,
    max_net_added: int,
    max_total_added: int,
) -> tuple[bool, str]:
    counted = [item for item in stats if should_count_file(item.path)]
    if not counted:
        return True, "仅检测到文档或规则变更，跳过代码预算检查"

    changed_file_count = len(counted)
    total_added = sum(item.added for item in counted)
    total_deleted = sum(item.deleted for item in counted)
    net_added = total_added - total_deleted

    violations: list[str] = []
    if changed_file_count > max_files:
        violations.append(f"修改代码文件数 {changed_file_count} > {max_files}")
    if net_added > max_net_added:
        violations.append(f"净新增行数 {net_added} > {max_net_added}")
    if total_added > max_total_added:
        violations.append(f"总新增行数 {total_added} > {max_total_added}")

    lines = [
        "Bugfix 预算统计：",
        f"- 修改代码文件数: {changed_file_count}",
        f"- 总新增行数: {total_added}",
        f"- 总删除行数: {total_deleted}",
        f"- 净新增行数: {net_added}",
        "- 代码文件明细:",
    ]
    for item in counted:
        lines.append(f"  - {item.path} (+{item.added} / -{item.deleted})")

    if violations:
        lines.append("预算超限：")
        for entry in violations:
            lines.append(f"- {entry}")
        lines.append("请拆分 PR 或在 PR 说明中给出超预算依据。")
        return False, "\n".join(lines)

    lines.append("预算检查通过。")
    return True, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bugfix 最小变更预算检查")
    parser.add_argument("--cached", action="store_true", help="检查 staged 变更")
    parser.add_argument("--diff-range", default="", help="检查指定 diff range，如 origin/main...HEAD")
    parser.add_argument(
        "--mode",
        choices=("auto", "always", "off"),
        default="auto",
        help="auto=仅 bugfix 检查，always=总是检查，off=跳过",
    )
    parser.add_argument("--pr-title", default="", help="PR 标题（可选）")
    parser.add_argument("--pr-body", default="", help="PR 描述（可选）")
    parser.add_argument("--pr-labels", default="", help="PR labels，逗号分隔（可选）")
    parser.add_argument("--max-files", type=int, default=3, help="修改代码文件数上限")
    parser.add_argument("--max-net-added", type=int, default=80, help="净新增行数上限")
    parser.add_argument("--max-total-added", type=int, default=140, help="总新增行数上限")
    parser.add_argument("--strict", action="store_true", help="失败时返回非零退出码")
    args = parser.parse_args()

    if args.cached and args.diff_range:
        print("不能同时使用 --cached 与 --diff-range", file=sys.stderr)
        return 2

    if args.mode == "off":
        print("检查模式为 off，跳过预算检查")
        return 0

    try:
        stats = run_git_numstat(cached=args.cached, diff_range=args.diff_range)
    except RuntimeError as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        return 2

    if not stats:
        print("无变更文件，跳过检查")
        return 0

    title = args.pr_title or os.getenv("PR_TITLE", "")
    body = args.pr_body or os.getenv("PR_BODY", "")
    labels = parse_labels(args.pr_labels or os.getenv("PR_LABELS", ""))

    if args.mode == "auto":
        bugfix, reason = is_bugfix_pr(title=title, body=body, labels=labels)
        if not bugfix:
            print(f"非 bugfix PR，跳过预算检查：{reason}")
            return 0
        print(f"识别为 bugfix PR：{reason}")

    ok, message = summarize_budget(
        stats=stats,
        max_files=args.max_files,
        max_net_added=args.max_net_added,
        max_total_added=args.max_total_added,
    )
    print(message)

    if ok:
        return 0
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
