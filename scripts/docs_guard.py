#!/usr/bin/env python3
"""docs 文档治理校验脚本。

检查项：
1. 相对链接存在性（忽略 fenced code / inline code）
2. docs/SUMMARY.md 链接目标存在性
3. 非归档文档是否被 SUMMARY 收录
4. 测试报告命名与主/归档规则
5. 双库变量名黑名单（DATA_DATABASE_URL）
6. OpenClaw Gate 看板（11.2/11.5）状态收口
7. 波次回滚演练矩阵（WAVE_ROLLBACK_DRILL_MATRIX）完整性
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
SUMMARY_FILE = DOCS_DIR / "SUMMARY.md"
REPORT_DIR = DOCS_DIR / "开发文档" / "测试管理" / "测试报告"
WAVE_PLAN_FILE = DOCS_DIR / "内部参考" / "迭代需求" / "迁移执行波次_implementation_plan.md"

REQUIRED_GATES = ("G-1", "G-2", "G-3", "G-4")
REQUIRED_WAVES = ("P1", "P2", "P3", "P4", "P5", "P6")
PASS_STATUS_TOKENS = ("通过", "完成", "pass")
PENDING_STATUS_TOKENS = (
    "待执行",
    "进行中",
    "待回填",
    "未通过",
    "失败",
    "阻塞",
    "todo",
    "in_progress",
    "blocked",
    "pending",
)


FENCED_CODE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
INLINE_PATH_RE = re.compile(r"`((?:app|web|scripts|install|config|alembic)/[^`\n]+)`")

MAIN_REPORT_RE = re.compile(r"^[^/]+测试报告\.md$")
ARCHIVE_REPORT_RE = re.compile(r"^[^/]+测试报告_\d{8}_.+\.md$")
ARCHIVE_REPORT_DASH_RE = re.compile(r"^[^/]+测试报告_\d{4}-\d{2}-\d{2}_.+\.md$")
COMPAT_SCENE_REPORT_RE = re.compile(r"^测试报告_[^_]+_\d{8}\.md$")
COMPAT_MODULE_DATED_RE = re.compile(r"^[^/]+测试报告_\d{4}-\d{2}-\d{2}\.md$")

PATH_CHECK_INCLUDE = (
    DOCS_DIR / "README.md",
    DOCS_DIR / "API文档",
    DOCS_DIR / "产品文档",
    DOCS_DIR / "开发文档",
)

PATH_CHECK_IGNORE_TARGETS = {
    "web/node_modules",
    "web/playwright-report/",
    "web/test-results/",
    "web/test-results/results.json",
    "web/frontend-deploy.tar.gz",
}
PATH_CHECK_IGNORE_NORMALIZED = {item.rstrip("/") for item in PATH_CHECK_IGNORE_TARGETS}

PATH_CHECK_PLACEHOLDER_TOKENS = (
    "...",
    "xxx_",
    "MyComponent",
    "my-new-skill",
    "<topic>",
    "<WS-ID>",
)


@dataclass
class Finding:
    category: str
    level: str
    file: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "category": self.category,
            "level": self.level,
            "file": self.file,
            "detail": self.detail,
        }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_code_blocks(text: str) -> str:
    text = FENCED_CODE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def iter_markdown_files() -> Iterable[Path]:
    return sorted(DOCS_DIR.rglob("*.md"))


def is_placeholder_link(link: str) -> bool:
    placeholders = {"url", "...", "{url}", "${url}", "{image_url}", "./..."}
    if link in placeholders:
        return True
    if any(token in link for token in ("{", "}", "$")):
        return True
    return False


def resolve_relative_link(src: Path, raw_link: str) -> Path | None:
    link = raw_link.strip()
    if not link:
        return None
    if link.startswith(("http://", "https://", "mailto:")):
        return None

    path_part = link.split("#", 1)[0].strip()
    if not path_part or path_part.startswith("/"):
        return None
    if is_placeholder_link(path_part):
        return None

    return (src.parent / path_part).resolve()


def parse_summary_links() -> list[str]:
    text = read_text(SUMMARY_FILE)
    links: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(text):
        link = match.group(1).strip()
        if link.startswith(("http://", "https://", "mailto:")):
            continue
        path = link.split("#", 1)[0].strip()
        if path:
            links.append(path)
    return links


def extract_level3_section(text: str, heading_prefix: str) -> str:
    lines = text.splitlines()
    start_index: int | None = None

    for idx, line in enumerate(lines):
        if line.strip().startswith(heading_prefix):
            start_index = idx + 1
            break

    if start_index is None:
        return ""

    end_index = len(lines)
    for idx in range(start_index, len(lines)):
        if lines[idx].startswith("### "):
            end_index = idx
            break

    return "\n".join(lines[start_index:end_index])


def parse_markdown_table_rows(section_text: str) -> list[list[str]]:
    rows: list[list[str]] = []

    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if all(re.fullmatch(r"-+", cell) for cell in cells):
            continue

        rows.append(cells)

    return rows


def has_pending_status(status_text: str) -> bool:
    normalized = status_text.lower()
    return any(token in normalized for token in PENDING_STATUS_TOKENS)


def has_pass_status(status_text: str) -> bool:
    normalized = status_text.lower()
    return any(token in normalized for token in PASS_STATUS_TOKENS)


def check_openclaw_gate_status(findings: list[Finding]) -> int:
    count = 0
    if not WAVE_PLAN_FILE.exists():
        findings.append(
            Finding(
                category="openclaw_gate_status",
                level="error",
                file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                detail="迁移执行波次文档不存在",
            )
        )
        return 1

    text = read_text(WAVE_PLAN_FILE)
    section_112 = extract_level3_section(text, "### 11.2")
    section_115 = extract_level3_section(text, "### 11.5")

    if not section_112:
        count += 1
        findings.append(
            Finding(
                category="openclaw_gate_status",
                level="error",
                file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                detail="缺少 11.2 关卡清单章节",
            )
        )
        return count

    if not section_115:
        count += 1
        findings.append(
            Finding(
                category="openclaw_gate_status",
                level="error",
                file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                detail="缺少 11.5 Gate 状态看板章节",
            )
        )
        return count

    gate_rows_112: dict[str, list[str]] = {}
    for row in parse_markdown_table_rows(section_112):
        match = re.search(r"G-\d+", row[0]) if row else None
        if match:
            gate_rows_112[match.group(0)] = row

    gate_rows_115: dict[str, list[str]] = {}
    for row in parse_markdown_table_rows(section_115):
        match = re.search(r"G-\d+", row[0]) if row else None
        if match:
            gate_rows_115[match.group(0)] = row

    for gate in REQUIRED_GATES:
        row_112 = gate_rows_112.get(gate)
        if row_112 is None:
            count += 1
            findings.append(
                Finding(
                    category="openclaw_gate_status",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"11.2 缺少 {gate} 行",
                )
            )
        elif len(row_112) < 5:
            count += 1
            findings.append(
                Finding(
                    category="openclaw_gate_status",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"11.2 {gate} 列数不足（需包含状态列）",
                )
            )
        else:
            status_text = row_112[4]
            if has_pending_status(status_text) or not has_pass_status(status_text):
                count += 1
                findings.append(
                    Finding(
                        category="openclaw_gate_status",
                        level="error",
                        file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                        detail=f"11.2 {gate} 状态未收口：{status_text}",
                    )
                )

        row_115 = gate_rows_115.get(gate)
        if row_115 is None:
            count += 1
            findings.append(
                Finding(
                    category="openclaw_gate_status",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"11.5 缺少 {gate} 行",
                )
            )
            continue

        if len(row_115) < 6:
            count += 1
            findings.append(
                Finding(
                    category="openclaw_gate_status",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"11.5 {gate} 列数不足（需包含状态/证据/下一步）",
                )
            )
            continue

        status_text = row_115[3]
        evidence_text = row_115[4]
        if has_pending_status(status_text) or not has_pass_status(status_text):
            count += 1
            findings.append(
                Finding(
                    category="openclaw_gate_status",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"11.5 {gate} 状态未收口：{status_text}",
                )
            )

        if "待回填" in evidence_text or "tbd" in evidence_text.lower():
            count += 1
            findings.append(
                Finding(
                    category="openclaw_gate_status",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"11.5 {gate} 证据链接仍为占位：{evidence_text}",
                )
            )

    return count


def check_wave_rollback_matrix(findings: list[Finding]) -> int:
    count = 0
    if not WAVE_PLAN_FILE.exists():
        findings.append(
            Finding(
                category="wave_rollback_matrix",
                level="error",
                file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                detail="迁移执行波次文档不存在",
            )
        )
        return 1

    text = read_text(WAVE_PLAN_FILE)
    section_116 = extract_level3_section(text, "### 11.6 WAVE_ROLLBACK_DRILL_MATRIX")
    if not section_116:
        findings.append(
            Finding(
                category="wave_rollback_matrix",
                level="error",
                file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                detail="缺少 WAVE_ROLLBACK_DRILL_MATRIX 章节",
            )
        )
        return 1

    wave_rows: dict[str, list[str]] = {}
    for row in parse_markdown_table_rows(section_116):
        match = re.search(r"P\d+", row[0]) if row else None
        if match:
            wave_rows[match.group(0)] = row

    for wave in REQUIRED_WAVES:
        row = wave_rows.get(wave)
        if row is None:
            count += 1
            findings.append(
                Finding(
                    category="wave_rollback_matrix",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"矩阵缺少 {wave} 行",
                )
            )
            continue

        if len(row) < 5:
            count += 1
            findings.append(
                Finding(
                    category="wave_rollback_matrix",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"{wave} 列数不足（需包含锚点/结果/证据）",
                )
            )
            continue

        rollback_anchor = row[1]
        recovery_result = row[3]
        evidence_link = row[4]

        if not rollback_anchor:
            count += 1
            findings.append(
                Finding(
                    category="wave_rollback_matrix",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"{wave} 回滚锚点为空",
                )
            )

        if has_pending_status(recovery_result) or not has_pass_status(recovery_result):
            count += 1
            findings.append(
                Finding(
                    category="wave_rollback_matrix",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"{wave} 演练结果未通过：{recovery_result}",
                )
            )

        if "待回填" in evidence_link or "tbd" in evidence_link.lower():
            count += 1
            findings.append(
                Finding(
                    category="wave_rollback_matrix",
                    level="error",
                    file=str(WAVE_PLAN_FILE.relative_to(ROOT)),
                    detail=f"{wave} 证据链接仍为占位：{evidence_link}",
                )
            )

    return count


def check_broken_links(findings: list[Finding]) -> int:
    count = 0
    for md_file in iter_markdown_files():
        text = strip_code_blocks(read_text(md_file))
        for match in MARKDOWN_LINK_RE.finditer(text):
            raw = match.group(1)
            target = resolve_relative_link(md_file, raw)
            if target is None:
                continue
            if not target.exists():
                count += 1
                findings.append(
                    Finding(
                        category="broken_link",
                        level="error",
                        file=str(md_file.relative_to(ROOT)),
                        detail=f"{raw} -> {target.relative_to(ROOT)}",
                    )
                )
    return count


def check_summary_targets(findings: list[Finding]) -> int:
    count = 0
    for link in parse_summary_links():
        target = (DOCS_DIR / link).resolve()
        if not target.exists():
            count += 1
            findings.append(
                Finding(
                    category="summary_broken_target",
                    level="error",
                    file=str(SUMMARY_FILE.relative_to(ROOT)),
                    detail=f"{link}",
                )
            )
    return count


def is_archived_doc(path: Path) -> bool:
    rel = path.relative_to(DOCS_DIR)
    parts = rel.parts
    if "归档备份" in parts:
        return True
    if "测试报告" in parts and path.name != "README.md":
        return True
    return False


def check_summary_coverage(findings: list[Finding]) -> tuple[int, int]:
    links = parse_summary_links()
    linked_targets = {(DOCS_DIR / link).resolve() for link in links}

    required_docs = []
    for md_file in iter_markdown_files():
        if md_file in {DOCS_DIR / "README.md", DOCS_DIR / "SUMMARY.md"}:
            continue
        if is_archived_doc(md_file):
            continue
        required_docs.append(md_file.resolve())

    missing = [doc for doc in required_docs if doc not in linked_targets]
    for doc in missing:
        findings.append(
            Finding(
                category="summary_missing_doc",
                level="error",
                file=str(doc.relative_to(ROOT)),
                detail="未被 docs/SUMMARY.md 收录",
            )
        )

    total = len(required_docs)
    covered = total - len(missing)
    return covered, total


def check_report_naming(findings: list[Finding]) -> int:
    count = 0
    if not REPORT_DIR.exists():
        findings.append(
            Finding(
                category="report_naming",
                level="error",
                file=str(REPORT_DIR.relative_to(ROOT)),
                detail="目录不存在",
            )
        )
        return 1

    for md_file in sorted(REPORT_DIR.glob("*.md")):
        name = md_file.name
        if name == "README.md":
            continue
        if MAIN_REPORT_RE.match(name):
            continue
        if ARCHIVE_REPORT_RE.match(name):
            continue
        if ARCHIVE_REPORT_DASH_RE.match(name):
            continue
        if COMPAT_SCENE_REPORT_RE.match(name) or COMPAT_MODULE_DATED_RE.match(name):
            findings.append(
                Finding(
                    category="report_naming",
                    level="warning",
                    file=str(md_file.relative_to(ROOT)),
                    detail="兼容命名（建议后续统一）",
                )
            )
            continue

        count += 1
        findings.append(
            Finding(
                category="report_naming",
                level="error",
                file=str(md_file.relative_to(ROOT)),
                detail="不符合主报告/归档命名规范",
            )
        )

    return count


def check_blacklist_vars(findings: list[Finding]) -> int:
    count = 0
    pattern = re.compile(r"\bDATA_DATABASE_URL\b")
    for md_file in iter_markdown_files():
        text = read_text(md_file)
        for idx, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                count += 1
                findings.append(
                    Finding(
                        category="blacklist_var",
                        level="error",
                        file=f"{md_file.relative_to(ROOT)}:{idx}",
                        detail="发现黑名单变量 DATA_DATABASE_URL",
                    )
                )
    return count


def iter_path_check_docs() -> Iterable[Path]:
    for root in PATH_CHECK_INCLUDE:
        if root.is_file():
            yield root
            continue
        if not root.exists():
            continue
        for md_file in sorted(root.rglob("*.md")):
            if is_archived_doc(md_file):
                continue
            yield md_file


def should_skip_path_target(target: str) -> bool:
    if not target:
        return True
    if any(token in target for token in ("*", "{", "}", "$", "<", ">")):
        return True
    if any(token in target for token in PATH_CHECK_PLACEHOLDER_TOKENS):
        return True
    if target in PATH_CHECK_IGNORE_TARGETS:
        return True
    if target.rstrip("/") in PATH_CHECK_IGNORE_NORMALIZED:
        return True
    return False


def normalize_path_target(raw_target: str) -> str:
    target = raw_target.strip().rstrip(".,;:)")
    target = target.split("#", 1)[0].strip()
    if re.search(r":\d+:\d+$", target):
        target = re.sub(r":\d+:\d+$", "", target)
    elif re.search(r":\d+$", target):
        target = re.sub(r":\d+$", "", target)
    return target


def check_inline_path_refs(findings: list[Finding]) -> int:
    count = 0
    seen: set[tuple[str, str]] = set()

    for md_file in iter_path_check_docs():
        text = read_text(md_file)
        text_wo_fenced = FENCED_CODE_RE.sub("", text)

        for idx, line in enumerate(text_wo_fenced.splitlines(), start=1):
            for match in INLINE_PATH_RE.finditer(line):
                raw_target = match.group(1)
                target = normalize_path_target(raw_target)

                if should_skip_path_target(target):
                    continue

                target_path = (ROOT / target).resolve()
                if target_path.exists():
                    continue

                key = (str(md_file.relative_to(ROOT)), target)
                if key in seen:
                    continue
                seen.add(key)
                count += 1

                findings.append(
                    Finding(
                        category="path_reference_missing",
                        level="warning",
                        file=f"{md_file.relative_to(ROOT)}:{idx}",
                        detail=f"{raw_target} -> {target}",
                    )
                )

    return count


def summarize(findings: list[Finding], covered: int, total: int, stats: dict[str, int]) -> dict:
    errors = sum(1 for finding in findings if finding.level == "error")
    warnings = sum(1 for finding in findings if finding.level == "warning")
    coverage_ratio = 0.0 if total == 0 else covered / total

    return {
        "strict_pass": errors == 0,
        "stats": {
            **stats,
            "summary_covered_docs": covered,
            "summary_total_required_docs": total,
            "summary_coverage_ratio": round(coverage_ratio, 4),
            "errors": errors,
            "warnings": warnings,
        },
        "findings": [finding.to_dict() for finding in findings],
    }


def print_human_report(report: dict) -> None:
    stats = report["stats"]
    print("=" * 48)
    print("docs_guard 检查报告")
    print("=" * 48)
    print(f"broken_links: {stats['broken_links']}")
    print(f"summary_broken_targets: {stats['summary_broken_targets']}")
    print(
        "summary_coverage: "
        f"{stats['summary_covered_docs']}/{stats['summary_total_required_docs']}"
        f" ({stats['summary_coverage_ratio'] * 100:.2f}%)"
    )
    print(f"report_naming_errors: {stats['report_naming_errors']}")
    print(f"blacklist_var_hits: {stats['blacklist_var_hits']}")
    print(f"openclaw_gate_status_errors: {stats['openclaw_gate_status_errors']}")
    print(f"wave_rollback_matrix_errors: {stats['wave_rollback_matrix_errors']}")
    print(f"path_reference_missing: {stats['path_reference_missing']}")
    print(f"errors: {stats['errors']} | warnings: {stats['warnings']}")

    if report["findings"]:
        print("\n详细问题:")
        for finding in report["findings"]:
            print(
                f"- [{finding['level']}] {finding['category']} "
                f"{finding['file']} -> {finding['detail']}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="docs 文档治理检查")
    parser.add_argument("--strict", action="store_true", help="发现 error 时返回非零退出码")
    parser.add_argument(
        "--check-paths",
        action="store_true",
        help="检查核心文档中的内联代码路径是否存在（结果以 warning 输出）",
    )
    parser.add_argument("--json-out", type=str, default="", help="输出 JSON 报告路径")
    args = parser.parse_args()

    findings: list[Finding] = []

    stats = {
        "broken_links": check_broken_links(findings),
        "summary_broken_targets": check_summary_targets(findings),
        "report_naming_errors": check_report_naming(findings),
        "blacklist_var_hits": check_blacklist_vars(findings),
        "openclaw_gate_status_errors": check_openclaw_gate_status(findings),
        "wave_rollback_matrix_errors": check_wave_rollback_matrix(findings),
        "path_reference_missing": check_inline_path_refs(findings) if args.check_paths else 0,
    }
    covered, total = check_summary_coverage(findings)

    report = summarize(findings, covered, total, stats)
    print_human_report(report)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nJSON 已输出: {out_path}")

    if args.strict and not report["strict_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
