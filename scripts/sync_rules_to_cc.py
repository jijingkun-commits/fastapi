"""Cursor 规则同步到 Claude Code 的转换脚本。

从 .cursor/rules/*.mdc 读取规则文件，去除 frontmatter（--- 块），
输出到 .claude/rules/*.md。文件名下划线转连字符，后缀 .mdc -> .md。

用法:
    python scripts/sync_rules_to_cc.py
    python scripts/sync_rules_to_cc.py --exclude doc_sync,banking-context
    python scripts/sync_rules_to_cc.py --lite doc_sync
"""

import argparse
import re
from pathlib import Path
from typing import Optional, Set

# 项目根目录（兼容 symlink：脚本实体在 .cursor/scripts/，需向上三级）
_script_path = Path(__file__).resolve()
if _script_path.parent.parent.name == ".cursor":
    ROOT = _script_path.parent.parent.parent
else:
    ROOT = _script_path.parent.parent
CURSOR_RULES_DIR = ROOT / ".cursor" / "rules"
CLAUDE_RULES_DIR = ROOT / ".claude" / "rules"

# frontmatter 正则：匹配文件开头的 --- ... --- 块
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)

# 手工维护的文件，sync 脚本不会覆盖
MANUAL_FILES = {"teammate-preamble", "doc-sync-lite"}


def strip_frontmatter(content: str) -> str:
    """去除 MDC 文件开头的 frontmatter 块。"""
    return FRONTMATTER_RE.sub("", content).lstrip("\n")


def mdc_to_md_name(mdc_name: str) -> str:
    """将 .mdc 文件名转换为 .md 文件名（下划线转连字符）。"""
    stem = Path(mdc_name).stem
    return stem.replace("_", "-") + ".md"


def sync_rules(
    exclude: Optional[Set[str]] = None,
    lite: Optional[Set[str]] = None,
) -> list[str]:
    """同步规则文件，返回生成的文件列表。"""
    exclude = exclude or set()
    lite = lite or set()
    CLAUDE_RULES_DIR.mkdir(parents=True, exist_ok=True)

    generated = []
    for mdc_file in sorted(CURSOR_RULES_DIR.glob("*.mdc")):
        stem = mdc_file.stem
        if stem in exclude:
            continue
        if stem in lite:
            # 精简模式跳过，由外部手工处理
            continue

        out_name = mdc_to_md_name(mdc_file.name)
        # 保护手工维护的文件
        if Path(out_name).stem in MANUAL_FILES:
            print(f"  跳过手工文件: {out_name}")
            continue

        content = mdc_file.read_text(encoding="utf-8")
        cleaned = strip_frontmatter(content)
        out_path = CLAUDE_RULES_DIR / out_name
        out_path.write_text(cleaned, encoding="utf-8")
        generated.append(out_name)

    # 清理孤儿文件：删除不在本次生成列表中的自动生成文件
    generated_set = set(generated)
    for existing in CLAUDE_RULES_DIR.glob("*.md"):
        if existing.stem in MANUAL_FILES:
            continue
        if existing.name not in generated_set:
            existing.unlink()
            print(f"  清理孤儿: {existing.name}")

    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="同步 Cursor 规则到 Claude Code")
    parser.add_argument(
        "--exclude",
        default="doc_sync",
        help="排除的规则文件名（逗号分隔，不含后缀），默认: doc_sync",
    )
    parser.add_argument(
        "--lite",
        default="",
        help="需要精简处理的规则文件名（逗号分隔，不含后缀）",
    )
    args = parser.parse_args()

    exclude = {s.strip() for s in args.exclude.split(",") if s.strip()}
    lite = {s.strip() for s in args.lite.split(",") if s.strip()}

    generated = sync_rules(exclude=exclude, lite=lite)

    print(f"已生成 {len(generated)} 个规则文件到 {CLAUDE_RULES_DIR}/:")
    for name in generated:
        print(f"  - {name}")

    if exclude:
        print(f"已排除: {', '.join(sorted(exclude))}")
    if lite:
        print(f"精简模式: {', '.join(sorted(lite))}")


if __name__ == "__main__":
    main()
