#!/usr/bin/env python3
"""docs 文档治理校验脚本。

检查项：
1. 相对链接存在性（忽略 fenced code / inline code）
2. docs/SUMMARY.md 链接目标存在性
3. 非归档且非任务拆解/规划草稿文档是否被 SUMMARY 收录
4. 测试报告命名与主/归档规则
5. 双库变量名黑名单（DATA_DATABASE_URL）
6. OpenClaw Gate 看板（11.2/11.5）状态收口
7. 波次回滚演练矩阵（WAVE_ROLLBACK_DRILL_MATRIX）完整性
8. G01 证据四元组与绑定关系校验
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
SUMMARY_FILE = DOCS_DIR / "SUMMARY.md"
REPORT_DIR = ROOT / "workdocs" / "归档" / "报告" / "测试报告"
WAVE_PLAN_FILE = ROOT / "workdocs" / "归档" / "正文" / "实施计划" / "迁移执行波次_implementation_plan.md"
ITERATION_REQUIREMENTS_DIR = ROOT / "workdocs" / "归档" / "正文" / "需求"
ITERATION_IMPLEMENTATION_PLAN_DIR = ROOT / "workdocs" / "归档" / "正文" / "实施计划"
REQUIREMENTS_SUFFIX = "_requirements.md"
IMPLEMENTATION_PLAN_SUFFIX = "_implementation_plan.md"
G01_WORKSTREAM_FILE = (
    ROOT
    / "workdocs"
    / "归档"
    / "任务拆解"
    / "2026-02-21_openclaw迁移重建基线"
    / "workstreams"
    / "WS-G01_G1_实测证据闭环.md"
)
G01_CARD_KEY = "PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-G01"

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
PENDING_EVIDENCE_TOKENS = ("待回填", "tbd", "todo", "pending", "待补", "待定")
TC_ID_RE = re.compile(r"\bTC-[A-Za-z0-9-]+\b")


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

CURRENT_STATE_DOC_ROOTS = (
    DOCS_DIR / "产品文档",
    DOCS_DIR / "开发文档" / "架构设计",
    DOCS_DIR / "API文档",
)
CURRENT_STATE_PROCESS_DOCS = {
    DOCS_DIR / "开发文档" / "架构设计" / "防屎山记录手册.md",
    DOCS_DIR / "内部参考" / "迭代需求" / "README.md",
    DOCS_DIR / "内部参考" / "任务拆解" / "README.md",
}
PROCESS_DOC_ROOTS: tuple[Path, ...] = ()
RUNTIME_JSON_FILENAMES = {
    "task-runner-state.json",
    "coder4-idempotency.json",
    "coder4_scope_request.json",
    "vktodo_dryrun_result.json",
}
RUNTIME_JSON_PATTERNS = (
    re.compile(r"^active-session-[^.]+\.json$"),
    re.compile(r"^attempt_\d+\.json$"),
)
CURRENT_STATE_TIMESTAMP_RE = re.compile(r"^> 更新时间：\d{4}-\d{2}-\d{2}$", re.MULTILINE)
CURRENT_STATE_FORBIDDEN_HEADING_RULES = (
    (
        "incremental_heading",
        re.compile(r"^\s{0,3}#{2,6}\s+.*增量需求.*$", re.MULTILINE),
        "主文档禁止使用 `增量需求` 章节，新增事实必须融合到原功能位",
    ),
    (
        "progress_heading",
        re.compile(r"^\s{0,3}#{2,6}\s+.*实现进展.*$", re.MULTILINE),
        "主文档禁止使用 `实现进展` 章节，应改写为当前架构/行为说明",
    ),
    (
        "executed_heading",
        re.compile(r"^\s{0,3}#{2,6}\s+.*已执行.*$", re.MULTILINE),
        "主文档禁止使用 `已执行` 状态标题，应改写为当前落地形态",
    ),
    (
        "implemented_heading",
        re.compile(r"^\s{0,3}#{2,6}\s+.*已实现.*$", re.MULTILINE),
        "主文档标题不应以 `已实现` 描述历史阶段，应直接描述当前能力",
    ),
    (
        "supplement_heading",
        re.compile(r"^\s{0,3}#{2,6}\s+.*补充[）)]?\s*$", re.MULTILINE),
        "主文档禁止使用 `补充` 标题，应把补充内容并入原章节",
    ),
)
CURRENT_STATE_LEGACY_ALLOWLIST = {
    "docs/产品文档/配置治理需求.md": {"timestamp_missing"},
    "docs/开发文档/架构设计/附件系统设计.md": {"timestamp_missing"},
    "docs/开发文档/架构设计/前端UI设计方案.md": {"timestamp_missing"},
    "docs/开发文档/架构设计/问数引擎设计.md": {"timestamp_missing"},
    "docs/开发文档/架构设计/待办Agent设计.md": {"timestamp_missing"},
    "docs/产品文档/聊天系统需求.md": {"timestamp_missing", "incremental_heading"},
    "docs/产品文档/问数助手需求.md": {"incremental_heading"},
}

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
    if link.startswith("file://"):
        parsed = urlparse(link)
        path_part = unquote(parsed.path or "")
        if not path_part:
            return None
        file_path = Path(path_part)
        if file_path.is_absolute():
            return file_path.resolve()
        return (src.parent / file_path).resolve()

    path_part = link.split("#", 1)[0].strip()
    if not path_part or path_part.startswith("/"):
        return None
    if is_placeholder_link(path_part):
        return None

    return (src.parent / path_part).resolve()


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def resolve_doc_role(path: Path) -> str:
    if path in CURRENT_STATE_PROCESS_DOCS:
        return "process"
    for root in PROCESS_DOC_ROOTS:
        if is_relative_to(path, root):
            return "process"
    for root in CURRENT_STATE_DOC_ROOTS:
        if is_relative_to(path, root):
            return "current_state"
    return "support"


def is_allowlisted(path: Path, issue_key: str, *, force_strict: bool) -> bool:
    if force_strict:
        return False
    rel_path = str(path.relative_to(ROOT))
    return issue_key in CURRENT_STATE_LEGACY_ALLOWLIST.get(rel_path, set())


def resolve_selected_docs(raw_paths: list[str]) -> list[Path]:
    selected: list[Path] = []
    for raw_path in raw_paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not candidate.exists() or candidate.suffix.lower() != ".md":
            continue
        if not is_relative_to(candidate, DOCS_DIR):
            continue
        selected.append(candidate)

    unique: list[Path] = []
    seen: set[Path] = set()
    for doc in selected:
        if doc in seen:
            continue
        seen.add(doc)
        unique.append(doc)
    return sorted(unique)


def format_path_for_detail(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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


def iter_requirement_plan_pairs() -> Iterable[tuple[Path, Path]]:
    if not ITERATION_REQUIREMENTS_DIR.exists():
        return

    for req_file in sorted(ITERATION_REQUIREMENTS_DIR.glob(f"*{REQUIREMENTS_SUFFIX}")):
        if "_templates" in req_file.parts:
            continue
        plan_name = req_file.name.replace(REQUIREMENTS_SUFFIX, IMPLEMENTATION_PLAN_SUFFIX)
        if plan_name == req_file.name:
            continue
        plan_file = ITERATION_IMPLEMENTATION_PLAN_DIR / plan_name
        if plan_file.exists():
            yield req_file, plan_file


def extract_requirement_status(text: str) -> str:
    match = re.search(r"状态[：:]\s*([^\n\r`]+)", text, re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def extract_implementation_ready(text: str) -> bool | None:
    matches = list(re.finditer(r"implementation_ready:\s*(true|false)", text, re.IGNORECASE))
    if not matches:
        return None
    latest = matches[-1].group(1).strip().lower()
    return latest == "true"


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


def normalize_table_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def is_pending_evidence_value(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True
    return any(token in normalized for token in PENDING_EVIDENCE_TOKENS)


def check_g01_evidence_binding(findings: list[Finding]) -> int:
    count = 0
    file_label = str(G01_WORKSTREAM_FILE.relative_to(ROOT))

    if not G01_WORKSTREAM_FILE.exists():
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail="G01 工作包文档不存在",
            )
        )
        return 1

    text = read_text(G01_WORKSTREAM_FILE)
    section_61 = extract_level3_section(text, "### 6.1")
    if not section_61:
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail="缺少 6.1 证据四元组实测记录章节",
            )
        )
        return 1

    rows = parse_markdown_table_rows(section_61)
    if len(rows) < 2:
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail="6.1 证据表缺少表头或数据行",
            )
        )
        return 1

    header = [normalize_table_cell(cell).lower() for cell in rows[0]]
    header_index = {name: idx for idx, name in enumerate(header)}
    required_columns = (
        "target_task_id",
        "evidence_task_id",
        "task_id",
        "turn_id",
        "process_id",
        "status",
    )
    missing_columns = [column for column in required_columns if column not in header_index]
    if missing_columns:
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail=f"6.1 证据表缺少列：{', '.join(missing_columns)}",
            )
        )
        return 1

    normalized_rows: list[dict[str, str]] = []
    for row in rows[1:]:
        padded_row = row + [""] * (len(header) - len(row))
        mapped = {
            column: normalize_table_cell(padded_row[index])
            for column, index in header_index.items()
            if index < len(padded_row)
        }
        if any(mapped.get(column, "") for column in required_columns):
            normalized_rows.append(mapped)

    if not normalized_rows:
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail="6.1 证据表未提供有效数据行",
            )
        )
        return 1

    latest = normalized_rows[-1]

    for column in required_columns:
        value = latest.get(column, "")
        if is_pending_evidence_value(value):
            count += 1
            findings.append(
                Finding(
                    category="g01_evidence_binding",
                    level="error",
                    file=file_label,
                    detail=f"最新证据行字段 `{column}` 缺失或仍为占位：{value or '空值'}",
                )
            )

    target_task_id = latest.get("target_task_id", "")
    evidence_task_id = latest.get("evidence_task_id", "")
    task_id = latest.get("task_id", "")
    status = latest.get("status", "")
    bind_result = latest.get("bind_result", "")

    if target_task_id and target_task_id != evidence_task_id:
        count += 1
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail=(
                    "证据绑定不一致："
                    f"target_task_id={target_task_id}, evidence_task_id={evidence_task_id}"
                ),
            )
        )

    if target_task_id and target_task_id != G01_CARD_KEY:
        count += 1
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail=(
                    "target_task_id 与 G01 card_key 不一致："
                    f"{target_task_id} != {G01_CARD_KEY}"
                ),
            )
        )

    if task_id and evidence_task_id and task_id != evidence_task_id:
        count += 1
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail=f"task_id 与 evidence_task_id 不一致：{task_id} != {evidence_task_id}",
            )
        )

    if status and (has_pending_status(status) or not has_pass_status(status)):
        count += 1
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail=f"最新证据行状态未收口：{status}",
            )
        )

    if bind_result and (has_pending_status(bind_result) or not ("一致" in bind_result or has_pass_status(bind_result))):
        count += 1
        findings.append(
            Finding(
                category="g01_evidence_binding",
                level="error",
                file=file_label,
                detail=f"最新证据行 bind_result 未收口：{bind_result}",
            )
        )

    return count


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
                        detail=f"{raw} -> {format_path_for_detail(target)}",
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


def is_task_split_phase1_compat_json(path: Path) -> bool:
    # Phase 2 已完成，docs 下不再允许 task_split 兼容 JSON。
    del path
    return False


def is_runtime_json_artifact(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    if path.name in RUNTIME_JSON_FILENAMES:
        return True
    return any(pattern.match(path.name) for pattern in RUNTIME_JSON_PATTERNS)


def iter_git_tracked_paths(pathspec: str) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", pathspec],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    tracked: list[Path] = []
    for line in result.stdout.splitlines():
        raw = line.strip()
        if raw:
            tracked.append(Path(raw))
    return tracked


def is_summary_optional_doc(path: Path) -> bool:
    rel_posix = path.relative_to(DOCS_DIR).as_posix()
    if rel_posix.startswith("内部参考/任务拆解/"):
        return True
    if rel_posix.startswith("plans/"):
        return True
    if rel_posix.startswith("内部参考/迭代需求/"):
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
        if is_summary_optional_doc(md_file):
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


def check_runtime_artifact_pollution(findings: list[Finding]) -> int:
    count = 0
    for current_root, dirnames, filenames in os.walk(DOCS_DIR, followlinks=False):
        current_path = Path(current_root)

        kept_dirs: list[str] = []
        for dirname in dirnames:
            candidate = current_path / dirname
            if dirname == ".state" and not candidate.is_symlink():
                count += 1
                findings.append(
                    Finding(
                        category="runtime_artifact_pollution",
                        level="error",
                        file=str(candidate.relative_to(ROOT)),
                        detail="docs 目录不应承载真实 `.state` 运行态目录，应迁移到 `.artifacts/`",
                    )
                )
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            candidate = current_path / filename
            suffix = candidate.suffix.lower()
            if suffix in {".jsonl", ".lock"}:
                count += 1
                findings.append(
                    Finding(
                        category="runtime_artifact_pollution",
                        level="error",
                        file=str(candidate.relative_to(ROOT)),
                        detail="docs 目录不应承载真实运行态文件（.jsonl/.lock），应迁移到 `.artifacts/`",
                    )
                )
                continue
            if is_task_split_phase1_compat_json(candidate):
                continue
            if not is_runtime_json_artifact(candidate):
                continue
            count += 1
            findings.append(
                Finding(
                    category="runtime_artifact_pollution",
                    level="error",
                    file=str(candidate.relative_to(ROOT)),
                    detail="docs 目录不应承载 task_split 机器 JSON 或真实运行态 JSON；Phase 2 起统一迁移到 workdocs/任务拆解/** 或 .artifacts/**",
                )
            )
    return count


def check_current_state_docs(findings: list[Finding], selected_docs: list[Path]) -> tuple[int, int]:
    timestamp_missing = 0
    forbidden_headings = 0
    force_strict = bool(selected_docs)
    docs = selected_docs if selected_docs else list(iter_markdown_files())

    for md_file in docs:
        if resolve_doc_role(md_file) != "current_state":
            continue

        rel_file = str(md_file.relative_to(ROOT))
        text = read_text(md_file)

        if not CURRENT_STATE_TIMESTAMP_RE.search(text):
            if is_allowlisted(md_file, "timestamp_missing", force_strict=force_strict):
                findings.append(
                    Finding(
                        category="current_state_legacy_allowlist",
                        level="warning",
                        file=rel_file,
                        detail="存量债务已命中 allowlist：timestamp_missing；需后续收敛 `> 更新时间：YYYY-MM-DD`",
                    )
                )
            else:
                timestamp_missing += 1
                findings.append(
                    Finding(
                        category="current_state_timestamp_missing",
                        level="error",
                        file=rel_file,
                        detail="主文档缺少标准头部 `> 更新时间：YYYY-MM-DD`",
                    )
                )

        for issue_key, pattern, message in CURRENT_STATE_FORBIDDEN_HEADING_RULES:
            matches = [match.group(0).strip() for match in pattern.finditer(text)]
            if not matches:
                continue

            preview = "；".join(matches[:2])
            suffix = "" if len(matches) <= 2 else f"；... 共 {len(matches)} 处"
            if is_allowlisted(md_file, issue_key, force_strict=force_strict):
                findings.append(
                    Finding(
                        category="current_state_legacy_allowlist",
                        level="warning",
                        file=rel_file,
                        detail=f"存量债务已命中 allowlist：{issue_key}；{message}；命中标题：{preview}{suffix}",
                    )
                )
                continue

            forbidden_headings += len(matches)
            findings.append(
                Finding(
                    category="current_state_forbidden_heading",
                    level="error",
                    file=rel_file,
                    detail=f"{message}；命中标题：{preview}{suffix}",
                )
            )

    return timestamp_missing, forbidden_headings


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


def check_tracked_runtime_state_pollution(findings: list[Finding]) -> int:
    count = 0
    for rel_path in iter_git_tracked_paths(".state"):
        candidate = ROOT / rel_path
        if not candidate.exists():
            continue
        count += 1
        findings.append(
            Finding(
                category="runtime_artifact_pollution",
                level="error",
                file=str(rel_path),
                detail="根 `.state/` 运行态文件不应纳入版本控制，应迁移到 `.artifacts/` 或从 Git 跟踪中移除",
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


def check_requirement_plan_status_consistency(findings: list[Finding]) -> int:
    count = 0
    for req_file, plan_file in iter_requirement_plan_pairs():
        req_text = read_text(req_file)
        plan_text = read_text(plan_file)
        status = extract_requirement_status(req_text)
        implementation_ready = extract_implementation_ready(plan_text)
        if not status or implementation_ready is None:
            continue

        normalized_status = re.sub(r"\s+", "", status).lower()
        if ("draft" in normalized_status or "草稿" in normalized_status) and implementation_ready:
            count += 1
            findings.append(
                Finding(
                    category="requirement_status_mismatch",
                    level="error",
                    file=str(req_file.relative_to(ROOT)),
                    detail=(
                        f"需求状态为 `{status}`，但 `{plan_file.relative_to(ROOT)}` "
                        "中 implementation_ready=true"
                    ),
                )
            )
    return count


def check_requirement_tc_traceability(findings: list[Finding]) -> int:
    count = 0
    for req_file, plan_file in iter_requirement_plan_pairs():
        req_text = read_text(req_file)
        req_tc_ids = sorted(set(TC_ID_RE.findall(req_text)))
        if not req_tc_ids:
            continue

        plan_text = read_text(plan_file)
        plan_tc_ids = set(TC_ID_RE.findall(plan_text))
        missing_tc = [tc_id for tc_id in req_tc_ids if tc_id not in plan_tc_ids]
        if not missing_tc:
            continue

        count += len(missing_tc)
        preview = ", ".join(missing_tc[:6])
        suffix = "" if len(missing_tc) <= 6 else f" ... 共 {len(missing_tc)} 项"
        findings.append(
            Finding(
                category="requirement_tc_traceability",
                level="warning",
                file=str(req_file.relative_to(ROOT)),
                detail=(
                    f"`{plan_file.relative_to(ROOT)}` 未显式覆盖 TC 映射："
                    f"{preview}{suffix}"
                ),
            )
        )
    return count


def check_requirement_nfr_numeric_threshold(findings: list[Finding]) -> int:
    count = 0
    section_pattern = re.compile(
        r"^##\s*[\d.]*\s*非功能需求[^\n]*\n(.*?)(?=^##\s|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    for req_file in sorted(ITERATION_REQUIREMENTS_DIR.glob(f"*{REQUIREMENTS_SUFFIX}")):
        if "_templates" in req_file.parts:
            continue
        req_text = read_text(req_file)
        match = section_pattern.search(req_text)
        if not match:
            continue
        nfr_body = match.group(1)
        if re.search(r"\d", nfr_body):
            continue

        count += 1
        findings.append(
            Finding(
                category="requirement_nfr_threshold",
                level="warning",
                file=str(req_file.relative_to(ROOT)),
                detail="非功能需求未发现数字阈值，建议补充 P50/P95、错误率或恢复时长",
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


def print_human_report(report: dict, *, non_blocking: bool = False) -> None:
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
    print(f"current_state_timestamp_missing: {stats['current_state_timestamp_missing']}")
    print(f"current_state_forbidden_headings: {stats['current_state_forbidden_headings']}")
    print(f"runtime_artifact_pollution: {stats['runtime_artifact_pollution']}")
    print(f"blacklist_var_hits: {stats['blacklist_var_hits']}")
    print(f"openclaw_gate_status_errors: {stats['openclaw_gate_status_errors']}")
    print(f"g01_evidence_binding_errors: {stats['g01_evidence_binding_errors']}")
    print(f"wave_rollback_matrix_errors: {stats['wave_rollback_matrix_errors']}")
    print(f"path_reference_missing: {stats['path_reference_missing']}")
    print(f"requirement_status_mismatch: {stats['requirement_status_mismatch']}")
    print(f"requirement_tc_traceability_missing: {stats['requirement_tc_traceability_missing']}")
    print(f"requirement_nfr_threshold_missing: {stats['requirement_nfr_threshold_missing']}")
    print(f"errors: {stats['errors']} | warnings: {stats['warnings']}")

    if report["findings"]:
        print("\n详细问题:")
        for finding in report["findings"]:
            print(
                f"- [{finding['level']}] {finding['category']} "
                f"{finding['file']} -> {finding['detail']}"
            )

    if non_blocking and not report["strict_pass"]:
        print("\n提示：当前运行于非阻断模式，docs_guard 仅提醒，不阻断提交。")


def main() -> int:
    parser = argparse.ArgumentParser(description="docs 文档治理检查")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--strict", action="store_true", help="发现 error 时返回非零退出码")
    mode_group.add_argument("--non-blocking", action="store_true", help="发现 error 时仅打印报告，不返回非零退出码")
    parser.add_argument(
        "--check-paths",
        action="store_true",
        help="检查核心文档中的内联代码路径是否存在（结果以 warning 输出）",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=[],
        help="仅对指定 markdown 文档执行主文档 current_state 强校验；显式传入时忽略 legacy allowlist",
    )
    parser.add_argument("--json-out", type=str, default="", help="输出 JSON 报告路径")
    args = parser.parse_args()

    findings: list[Finding] = []
    selected_docs = resolve_selected_docs(args.paths)
    current_state_timestamp_missing, current_state_forbidden_headings = check_current_state_docs(
        findings,
        selected_docs,
    )

    stats = {
        "broken_links": check_broken_links(findings),
        "summary_broken_targets": check_summary_targets(findings),
        "report_naming_errors": check_report_naming(findings),
        "current_state_timestamp_missing": current_state_timestamp_missing,
        "current_state_forbidden_headings": current_state_forbidden_headings,
        "runtime_artifact_pollution": (
            check_runtime_artifact_pollution(findings)
            + check_tracked_runtime_state_pollution(findings)
        ),
        "blacklist_var_hits": check_blacklist_vars(findings),
        "openclaw_gate_status_errors": check_openclaw_gate_status(findings),
        "g01_evidence_binding_errors": check_g01_evidence_binding(findings),
        "wave_rollback_matrix_errors": check_wave_rollback_matrix(findings),
        "path_reference_missing": check_inline_path_refs(findings) if args.check_paths else 0,
        "requirement_status_mismatch": check_requirement_plan_status_consistency(findings),
        "requirement_tc_traceability_missing": check_requirement_tc_traceability(findings),
        "requirement_nfr_threshold_missing": check_requirement_nfr_numeric_threshold(findings),
    }
    covered, total = check_summary_coverage(findings)

    report = summarize(findings, covered, total, stats)
    print_human_report(report, non_blocking=args.non_blocking)

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
