#!/usr/bin/env python3
"""特殊处理文档同步检查。

目标：
- 当变更命中《防屎山记录手册》已登记的涉及文件时，强制要求同步更新手册。
- 支持 staged（pre-commit）和 diff range（CI）两种模式。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL_PATH = Path("docs/开发文档/架构设计/防屎山记录手册.md")

SP_HEADING_RE = re.compile(r"^##\s+(SP-\d{3})[:：].*$", re.M)
PATH_IN_BACKTICK_RE = re.compile(
    r"`((?:app|web/src|scripts|alembic|config|install)/[^`\n]+)`"
)


def run_git_diff_name_only(*, cached: bool, diff_range: str) -> list[str]:
    cmd = ["git", "diff"]
    if cached:
        cmd.append("--cached")
    cmd.extend(["--name-only", "-z", "--diff-filter=ACMRTUXB"])
    if diff_range:
        cmd.append(diff_range)

    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "git diff 执行失败")

    changed_files: list[str] = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        changed_files.append(raw_path.decode("utf-8", errors="surrogateescape"))
    return changed_files


def _normalize_path(text: str) -> str:
    value = text.strip().strip("`").strip()
    value = value.split("#", 1)[0].strip()
    value = re.sub(r":\d+(?::\d+)?$", "", value)
    value = value.rstrip(".,;:)")
    return value


def parse_special_file_map(manual_abs_path: Path) -> dict[str, set[str]]:
    text = manual_abs_path.read_text(encoding="utf-8")

    matches = list(SP_HEADING_RE.finditer(text))
    file_to_sp: dict[str, set[str]] = {}

    for idx, match in enumerate(matches):
        sp_id = match.group(1)
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section = text[start:end]

        for path_match in PATH_IN_BACKTICK_RE.finditer(section):
            normalized = _normalize_path(path_match.group(1))
            if not normalized:
                continue
            file_to_sp.setdefault(normalized, set()).add(sp_id)

    return file_to_sp


def check_special_doc_sync(
    *,
    manual_rel_path: Path,
    changed_files: list[str],
) -> tuple[bool, str]:
    manual_rel = manual_rel_path.as_posix()
    manual_abs = ROOT / manual_rel
    if not manual_abs.exists():
        return False, f"手册不存在: {manual_rel}"

    file_to_sp = parse_special_file_map(manual_abs)
    if not file_to_sp:
        return False, "未从手册解析到任何涉及文件，请检查手册格式"

    touched_special: list[tuple[str, list[str]]] = []
    for changed in changed_files:
        sp_ids = file_to_sp.get(changed)
        if not sp_ids:
            continue
        touched_special.append((changed, sorted(sp_ids)))

    if not touched_special:
        return True, "未命中已登记特殊处理文件，跳过强制校验"

    manual_changed = manual_rel in set(changed_files)
    if manual_changed:
        lines = [
            "命中已登记特殊处理文件，并检测到手册同步更新，检查通过：",
        ]
        for changed, sp_ids in touched_special:
            lines.append(f"- {changed} -> {', '.join(sp_ids)}")
        return True, "\n".join(lines)

    lines = [
        "检测到已登记特殊处理文件变更，但未同步更新《防屎山记录手册》：",
    ]
    for changed, sp_ids in touched_special:
        lines.append(f"- {changed} -> {', '.join(sp_ids)}")
    lines.append(f"要求同步更新: {manual_rel}")
    return False, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="特殊处理文档同步检查")
    parser.add_argument("--cached", action="store_true", help="检查 staged 变更（pre-commit）")
    parser.add_argument(
        "--diff-range",
        default="",
        help="检查指定 diff range（示例: origin/main...HEAD）",
    )
    parser.add_argument(
        "--manual-path",
        default=MANUAL_PATH.as_posix(),
        help="防屎山记录手册路径（相对仓库根目录）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="失败时返回非零退出码",
    )
    args = parser.parse_args()

    if args.cached and args.diff_range:
        print("不能同时使用 --cached 与 --diff-range", file=sys.stderr)
        return 2

    try:
        changed_files = run_git_diff_name_only(cached=args.cached, diff_range=args.diff_range)
    except RuntimeError as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        return 2

    if not changed_files:
        print("无变更文件，跳过检查")
        return 0

    ok, message = check_special_doc_sync(
        manual_rel_path=Path(args.manual_path),
        changed_files=changed_files,
    )
    print(message)

    if ok:
        return 0
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
