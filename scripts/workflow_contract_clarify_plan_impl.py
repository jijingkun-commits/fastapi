#!/usr/bin/env python3
"""校验 requirements / design / implementation_plan 承接是否完整。"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from task_split_paths import resolve_task_split_paths

ROOT = Path(__file__).resolve().parents[1]
TASK_SPLIT_BASE = Path("workdocs/任务拆解")
REQUIREMENTS_BASE = Path("workdocs/需求")
LEGACY_REQUIREMENTS_BASE = Path("docs/内部参考/迭代需求")
YAML_BLOCK_PATTERN = re.compile(r"```yaml\s*(.*?)```", flags=re.DOTALL | re.IGNORECASE)
FORBIDDEN_PROTOCOL_TOKENS = (
    "intent_plan",
    "validate_intent_plan_contract",
    "legacy_json_object",
)
REQUIRED_TASK_SCALAR_FIELDS = (
    "phase",
    "change_type",
    "owner",
    "pr_id",
    "risk_point",
    "rollback_point",
)
REQUIRED_TASK_LIST_FIELDS = (
    "depends_on_tasks",
    "file_paths",
    "symbols",
    "acceptance_cmds",
)
REQUIRED_PRODUCT_CONTRACT_FIELDS = (
    "target_users",
    "core_scenarios",
    "business_goals",
    "non_goals",
    "acceptance_gates",
)
REQUIRED_PRODUCT_CONTRACT_SUMMARY_FIELDS = (
    "target_users",
    "core_scenarios",
    "business_goal_metrics",
    "non_goals",
    "acceptance_gates",
)
PRODUCT_CONTRACT_PLACEHOLDERS = (
    "tbd",
    "todo",
    "待确认",
    "后续补充",
    "待补",
)


class AlignmentCheckError(RuntimeError):
    """承接校验失败。"""


def _normalize_id(raw: Any) -> str:
    return str(raw or "").strip().strip("`'\"").upper()


def _normalize_cmd(raw: Any) -> str:
    return " ".join(str(raw or "").strip().split())


def _normalize_text(raw: Any) -> str:
    return " ".join(str(raw or "").strip().split()).strip("`'\"")


def _as_list(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return list(raw)
    return [raw]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _split_key_value(text: str) -> tuple[str, str]:
    key, sep, value = text.partition(":")
    if not sep:
        return text.strip(), ""
    return key.strip(), value.strip()


def _parse_inline_list(raw: str, *, as_cmd: bool = False) -> list[str]:
    value = str(raw or "").strip()
    if not value:
        return []

    try:
        parsed = ast.literal_eval(value)
    except Exception:
        parsed = None

    items: list[Any]
    if isinstance(parsed, (list, tuple, set)):
        items = list(parsed)
    else:
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]
        items = [item.strip() for item in value.split(",") if item.strip()]

    if as_cmd:
        return [_normalize_cmd(item) for item in items if _normalize_cmd(item)]
    return [_normalize_text(item) for item in items if _normalize_text(item)]


def _parse_scalar_literal(raw: str) -> Any:
    value = str(raw or "").strip().strip("`")
    if not value:
        return ""

    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False

    try:
        return ast.literal_eval(value)
    except Exception:
        return value.strip("'\"")


def _extract_yaml_blocks(markdown_path: Path) -> list[str]:
    content = markdown_path.read_text(encoding="utf-8")
    blocks = YAML_BLOCK_PATTERN.findall(content)
    if not blocks:
        raise AlignmentCheckError(f"{markdown_path} 未找到 ```yaml``` 代码块")
    return blocks


def _detect_forbidden_protocol_tokens(*, blocks: list[str]) -> list[str]:
    hits: list[str] = []
    lower_blocks = "\n".join(blocks).lower()
    for token in FORBIDDEN_PROTOCOL_TOKENS:
        if re.search(rf"\b{re.escape(token.lower())}\b", lower_blocks):
            hits.append(token)
    if hits:
        return sorted(set(hits))
    return []


def _find_block(blocks: list[str], marker: str, source: Path) -> str:
    for block in blocks:
        if marker in block:
            return block
    raise AlignmentCheckError(f"{source} 未找到包含 `{marker}` 的 yaml 代码块")


def _resolve_task_split_dir(repo_root: Path, raw_value: str) -> Path:
    raw = str(raw_value or "").strip()
    if not raw:
        raise AlignmentCheckError("缺少 --task-split-dir")

    direct = Path(raw).expanduser()
    candidates: list[Path] = []
    if direct.is_absolute():
        candidates.append(direct)
    else:
        candidates.extend(
            [
                (repo_root / raw),
                (repo_root / TASK_SPLIT_BASE / raw),
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()

    joined = " | ".join(str(path) for path in candidates)
    raise AlignmentCheckError(f"无法定位 task_split_dir: {raw}; candidates={joined}")


def _resolve_markdown_path(*, repo_root: Path, raw_value: str | None, label: str) -> Path:
    raw = str(raw_value or "").strip()
    if not raw:
        raise AlignmentCheckError(f"缺少 {label} 路径")

    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    candidate = candidate.resolve()

    if not candidate.exists() or not candidate.is_file():
        raise AlignmentCheckError(f"{label} 不存在: {candidate}")
    return candidate


def _resolve_implementation_plan(
    *,
    repo_root: Path,
    task_split_dir: Path | None,
    implementation_path_raw: str | None,
) -> Path:
    if implementation_path_raw:
        return _resolve_markdown_path(
            repo_root=repo_root,
            raw_value=implementation_path_raw,
            label="implementation_plan",
        )

    if task_split_dir is None:
        raise AlignmentCheckError("缺少 implementation_plan 输入：请提供 --task-split-dir 或 --implementation-path")

    canonical_path = task_split_dir / "contracts" / "implementation_plan.md"
    if canonical_path.exists() and canonical_path.is_file():
        return canonical_path.resolve()

    split_name = task_split_dir.name
    inferred_topic = split_name.split("_", 1)[1] if re.match(r"^\d{4}-\d{2}-\d{2}_", split_name) else split_name
    legacy_path = repo_root / LEGACY_REQUIREMENTS_BASE / f"{inferred_topic}_implementation_plan.md"
    if legacy_path.exists() and legacy_path.is_file():
        return legacy_path.resolve()

    raise AlignmentCheckError(f"无法推断 implementation_plan: task_split_dir={task_split_dir}")


def _parse_execution_contract_source(implementation_path: Path, field_name: str) -> str:
    try:
        blocks = _extract_yaml_blocks(implementation_path)
    except AlignmentCheckError:
        return ""

    pattern = re.compile(rf"(?m)^\s{{2,4}}{re.escape(field_name)}:\s*(.+?)\s*$")
    for block in blocks:
        if "execution_contract:" not in block:
            continue
        match = pattern.search(block)
        if match:
            return _normalize_text(match.group(1))
    return ""


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _resolve_requirements_path(
    *,
    repo_root: Path,
    requirements_path_raw: str | None,
    implementation_path: Path,
) -> Path:
    if requirements_path_raw:
        return _resolve_markdown_path(
            repo_root=repo_root,
            raw_value=requirements_path_raw,
            label="requirements",
        )

    declared_source = _parse_execution_contract_source(implementation_path, "requirements_source")
    if declared_source:
        return _resolve_markdown_path(
            repo_root=repo_root,
            raw_value=declared_source,
            label="requirements",
        )

    canonical_task_split_base = (repo_root / TASK_SPLIT_BASE).resolve()
    if implementation_path.name == "implementation_plan.md" and _is_relative_to(
        implementation_path, canonical_task_split_base
    ):
        rel = implementation_path.relative_to(canonical_task_split_base)
        if len(rel.parts) >= 3 and rel.parts[1] == "contracts":
            split_name = rel.parts[0]
            inferred_topic = split_name.split("_", 1)[1] if re.match(r"^\d{4}-\d{2}-\d{2}_", split_name) else split_name
            req_path = repo_root / REQUIREMENTS_BASE / inferred_topic / "requirements.md"
            if req_path.exists() and req_path.is_file():
                return req_path.resolve()
            raise AlignmentCheckError(f"无法定位 requirements 文档: {req_path}")

    impl_name = implementation_path.name
    if impl_name.endswith("_implementation_plan.md"):
        req_name = impl_name.replace("_implementation_plan.md", "_requirements.md")
        req_path = implementation_path.parent / req_name
        if req_path.exists() and req_path.is_file():
            return req_path.resolve()

    raise AlignmentCheckError(f"implementation_plan 命名不符合约定，且无法推断 requirements: {implementation_path}")


def _strip_code_blocks(content: str) -> str:
    return re.sub(r"```.*?```", "", content, flags=re.DOTALL)


def _parse_design_approval(design_path: Path) -> dict[str, Any]:
    content = design_path.read_text(encoding="utf-8")
    plain = _strip_code_blocks(content)
    fields: dict[str, Any] = {}
    for key in ("design_approved", "approved_at", "approved_round", "approval_evidence"):
        pattern = rf"(?m)^\s*[-*]?\s*{key}\s*:\s*(.+?)\s*$"
        match = re.search(pattern, plain)
        if not match:
            continue
        fields[key] = _parse_scalar_literal(match.group(1))
    return fields


def _contains_placeholder(raw: Any) -> bool:
    text = _normalize_text(raw).lower()
    if not text:
        return False
    return any(token in text for token in PRODUCT_CONTRACT_PLACEHOLDERS)


def _parse_design_product_contract(design_path: Path) -> dict[str, Any]:
    content = design_path.read_text(encoding="utf-8")
    section_match = re.search(
        r"(?ims)^##\s+\d+\.\s*product_contract[^\n]*\n(.*?)(?=^##\s+\d+\.\s+|\Z)",
        content,
    )
    if not section_match:
        return {
            "section_exists": False,
            "fields": {},
            "missing_fields": list(REQUIRED_PRODUCT_CONTRACT_FIELDS),
            "empty_fields": [],
            "placeholder_fields": [],
        }

    section = section_match.group(1)
    lines = section.splitlines()
    parsed_fields: dict[str, str] = {}

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        bullet_match = re.match(r"^\s*-\s*([A-Za-z_][\w-]*)[^:：]*[:：]\s*(.*)\s*$", line)
        if not bullet_match:
            idx += 1
            continue

        field = _normalize_text(re.sub(r"[（(].*$", "", bullet_match.group(1)))
        value_parts: list[str] = []
        initial_value = _normalize_text(bullet_match.group(2))
        if initial_value:
            value_parts.append(initial_value)

        idx += 1
        while idx < len(lines):
            next_line = lines[idx]
            if re.match(r"^\s*-\s*[A-Za-z_][\w-]*[^:：]*[:：]", next_line):
                break
            candidate = _normalize_text(next_line.lstrip("- ").strip())
            if candidate and not candidate.startswith("```"):
                value_parts.append(candidate)
            idx += 1

        parsed_fields[field] = " ".join(value_parts).strip()

    missing_fields: list[str] = []
    empty_fields: list[str] = []
    placeholder_fields: list[str] = []
    for field in REQUIRED_PRODUCT_CONTRACT_FIELDS:
        if field not in parsed_fields:
            missing_fields.append(field)
            continue
        field_value = _normalize_text(parsed_fields.get(field))
        if not field_value:
            empty_fields.append(field)
            continue
        if _contains_placeholder(field_value):
            placeholder_fields.append(field)

    return {
        "section_exists": True,
        "fields": parsed_fields,
        "missing_fields": missing_fields,
        "empty_fields": empty_fields,
        "placeholder_fields": placeholder_fields,
    }


def _parse_design_freeze_summary(block: str) -> dict[str, Any]:
    lines = block.splitlines()
    try:
        start_idx = next(
            idx for idx, line in enumerate(lines) if line.strip().startswith("design_freeze_summary:")
        )
    except StopIteration as exc:
        raise AlignmentCheckError("design_freeze_summary 解析失败：缺少 design_freeze_summary") from exc

    summary: dict[str, Any] = {}
    current_list_key = ""
    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        indent = _indent(line)

        if not stripped:
            idx += 1
            continue
        if indent < 2:
            break

        if indent == 2:
            key, value = _split_key_value(stripped)
            current_list_key = ""
            if key in {"missing_blocks", "blocked_by"}:
                values = _parse_inline_list(value)
                summary[key] = values
                if value == "":
                    current_list_key = key
            else:
                summary[key] = _parse_scalar_literal(value)
            idx += 1
            continue

        if indent >= 4 and current_list_key and stripped.startswith("- "):
            summary.setdefault(current_list_key, [])
            summary[current_list_key].append(_normalize_text(stripped[2:]))
            idx += 1
            continue

        idx += 1

    summary.setdefault("missing_blocks", [])
    summary.setdefault("blocked_by", [])
    return summary


def _parse_clarify_consistency_check(block: str) -> dict[str, Any]:
    lines = block.splitlines()
    try:
        start_idx = next(
            idx for idx, line in enumerate(lines) if line.strip().startswith("clarify_consistency_check:")
        )
    except StopIteration as exc:
        raise AlignmentCheckError("clarify_consistency_check 解析失败：缺少 clarify_consistency_check") from exc

    summary: dict[str, Any] = {}
    current_list_key = ""
    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        indent = _indent(line)

        if not stripped:
            idx += 1
            continue
        if indent < 2:
            break

        if indent == 2:
            key, value = _split_key_value(stripped)
            current_list_key = ""
            if key in {"fail_fast_codes"}:
                values = _parse_inline_list(value)
                summary[key] = values
                if value == "":
                    current_list_key = key
            else:
                summary[key] = _parse_scalar_literal(value)
            idx += 1
            continue

        if indent >= 4 and current_list_key and stripped.startswith("- "):
            summary.setdefault(current_list_key, [])
            summary[current_list_key].append(_normalize_text(stripped[2:]))
            idx += 1
            continue

        idx += 1

    summary.setdefault("fail_fast_codes", [])
    return summary


def _parse_clarify_handoff_contract(block: str) -> dict[str, Any]:
    version_match = re.search(r"(?m)^\s{2}version:\s*(.+?)\s*$", block)
    topic_match = re.search(r"(?m)^\s{2}topic:\s*(.+?)\s*$", block)
    handoff_ready_match = re.search(r"(?m)^\s{2}handoff_ready:\s*(.+?)\s*$", block)
    schema_mode = "v2" if re.search(r"(?m)^\s{2}required:\s*$", block) else "v1"

    if schema_mode == "v2":
        product_contract_summary_pattern = (
            r"(?ms)^\s{4}product_contract_summary:\s*\n(.*?)(?=^\s{4}[A-Za-z_][\w-]*:\s*$|^\s{2}[A-Za-z_][\w-]*:\s*$|\Z)"
        )
        requirement_seed_section_pattern = (
            r"(?ms)^\s{4}requirement_seeds:\s*\n(.*?)(?=^\s{4}[A-Za-z_][\w-]*:\s*$|^\s{2}[A-Za-z_][\w-]*:\s*$|\Z)"
        )
        requirement_seed_item_pattern = r"(?m)^\s{6}-\s*[A-Za-z_][\w-]*\s*:\s*.*$"
        implementation_seed_pattern = r"(?m)^\s{6}-\s*task_id:\s*(.+?)\s*$"
        execution_chain_pattern = r"(?m)^\s{4}execution_chain_seed:\s*$"
        execution_contract_hint_pattern = r"(?m)^\s{6}execution_contract_hint:\s*$"
    else:
        product_contract_summary_pattern = r"$^"
        requirement_seed_section_pattern = (
            r"(?ms)^\s{2}requirement_seeds:\s*\n(.*?)(?=^\s{2}[A-Za-z_][\w-]*:\s*$|\Z)"
        )
        requirement_seed_item_pattern = r"(?m)^\s{4}-\s*[A-Za-z_][\w-]*\s*:\s*.*$"
        implementation_seed_pattern = r"(?m)^\s{4}-\s*task_id:\s*(.+?)\s*$"
        execution_chain_pattern = r"(?m)^\s{2}execution_chain_seed:\s*$"
        execution_contract_hint_pattern = r"(?m)^\s{4}execution_contract_hint:\s*$"

    requirement_seed_count = 0
    requirement_seed_section_match = re.search(requirement_seed_section_pattern, block)
    if requirement_seed_section_match:
        requirement_seed_section = requirement_seed_section_match.group(1)
        requirement_seed_count = len(re.findall(requirement_seed_item_pattern, requirement_seed_section))

    if requirement_seed_count <= 0:
        inline_requirement_seeds_match = re.search(
            r"(?m)^\s{2,4}requirement_seeds:\s*\[(.+?)\]\s*$",
            block,
        )
        if inline_requirement_seeds_match:
            inline_payload = inline_requirement_seeds_match.group(1).strip()
            if inline_payload and inline_payload != "[]":
                requirement_seed_count = 1

    if requirement_seed_count <= 0:
        requirement_seed_count = len(re.findall(r"(?m)^\s{4}-\s*design_item:\s*.+$", block))

    implementation_seed_task_ids = [
        _normalize_id(raw)
        for raw in re.findall(implementation_seed_pattern, block)
        if _normalize_id(raw)
    ]
    if not implementation_seed_task_ids:
        implementation_seed_task_ids = [
            _normalize_id(raw)
            for raw in re.findall(r"(?m)^\s{4}-\s*task_id:\s*(.+?)\s*$", block)
            if _normalize_id(raw)
        ]

    has_execution_chain_seed = re.search(execution_chain_pattern, block) is not None or re.search(
        r"(?m)^\s{2}execution_chain_seed:\s*$",
        block,
    ) is not None
    has_execution_contract_hint = re.search(
        execution_contract_hint_pattern,
        block,
    ) is not None or re.search(r"(?m)^\s{4}execution_contract_hint:\s*$", block) is not None

    product_contract_summary_fields: dict[str, list[str] | str] = {}
    product_contract_summary_match = re.search(product_contract_summary_pattern, block)
    if product_contract_summary_match:
        section_lines = product_contract_summary_match.group(1).splitlines()
        line_idx = 0
        while line_idx < len(section_lines):
            line = section_lines[line_idx]
            kv_match = re.match(r"^\s{6}([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$", line)
            if not kv_match:
                line_idx += 1
                continue

            field = _normalize_text(kv_match.group(1))
            inline_value = _normalize_text(kv_match.group(2))
            values: list[str] = []
            if inline_value:
                if inline_value.startswith("[") and inline_value.endswith("]"):
                    parsed_inline = _parse_inline_list(inline_value)
                    product_contract_summary_fields[field] = parsed_inline
                    line_idx += 1
                    continue
                values.append(inline_value)

            line_idx += 1
            while line_idx < len(section_lines):
                list_line = section_lines[line_idx]
                if re.match(r"^\s{6}[A-Za-z_][\w-]*\s*:\s*", list_line):
                    break
                list_item_match = re.match(r"^\s{8}-\s*(.*?)\s*$", list_line)
                if list_item_match:
                    normalized_item = _normalize_text(list_item_match.group(1))
                    if normalized_item:
                        values.append(normalized_item)
                line_idx += 1

            if values:
                product_contract_summary_fields[field] = values
            else:
                product_contract_summary_fields[field] = ""

    product_contract_summary_missing = [
        field
        for field in REQUIRED_PRODUCT_CONTRACT_SUMMARY_FIELDS
        if field not in product_contract_summary_fields
    ]
    product_contract_summary_empty = [
        field
        for field in REQUIRED_PRODUCT_CONTRACT_SUMMARY_FIELDS
        if field in product_contract_summary_fields
        and not any(_normalize_text(value) for value in _as_list(product_contract_summary_fields.get(field)))
    ]
    product_contract_summary_placeholder = [
        field
        for field in REQUIRED_PRODUCT_CONTRACT_SUMMARY_FIELDS
        if field in product_contract_summary_fields
        and any(_contains_placeholder(value) for value in _as_list(product_contract_summary_fields.get(field)))
    ]

    return {
        "schema_mode": schema_mode,
        "version": _normalize_text(version_match.group(1)) if version_match else "",
        "topic": _normalize_text(topic_match.group(1)) if topic_match else "",
        "handoff_ready": _parse_scalar_literal(handoff_ready_match.group(1)) if handoff_ready_match else False,
        "requirement_seed_count": requirement_seed_count,
        "implementation_seed_task_ids": implementation_seed_task_ids,
        "has_execution_chain_seed": has_execution_chain_seed,
        "has_execution_contract_hint": has_execution_contract_hint,
        "has_product_contract_summary": bool(product_contract_summary_match),
        "product_contract_summary_fields": product_contract_summary_fields,
        "product_contract_summary_missing": product_contract_summary_missing,
        "product_contract_summary_empty": product_contract_summary_empty,
        "product_contract_summary_placeholder": product_contract_summary_placeholder,
    }


def _parse_requirements_contract(block: str) -> dict[str, Any]:
    lines = block.splitlines()
    try:
        start_idx = next(
            idx for idx, line in enumerate(lines) if line.strip().startswith("requirements_contract:")
        )
    except StopIteration as exc:
        raise AlignmentCheckError("requirements_contract 解析失败：缺少 requirements_contract") from exc

    contract: dict[str, Any] = {}
    freeze_summary: dict[str, Any] = {}
    in_freeze = False
    current_list_key = ""

    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        indent = _indent(line)

        if not stripped:
            idx += 1
            continue
        if indent < 2:
            break

        if indent == 2:
            key, value = _split_key_value(stripped)
            in_freeze = False
            current_list_key = ""

            if key == "design_freeze_summary":
                in_freeze = True
                contract[key] = freeze_summary
            else:
                contract[key] = _parse_scalar_literal(value)
            idx += 1
            continue

        if in_freeze and indent == 4:
            key, value = _split_key_value(stripped)
            current_list_key = ""
            if key in {"missing_blocks", "blocked_by"}:
                values = _parse_inline_list(value)
                freeze_summary[key] = values
                if value == "":
                    current_list_key = key
            else:
                freeze_summary[key] = _parse_scalar_literal(value)
            idx += 1
            continue

        if in_freeze and indent >= 6 and current_list_key and stripped.startswith("- "):
            freeze_summary.setdefault(current_list_key, [])
            freeze_summary[current_list_key].append(_normalize_text(stripped[2:]))
            idx += 1
            continue

        idx += 1

    freeze_summary.setdefault("missing_blocks", [])
    freeze_summary.setdefault("blocked_by", [])
    contract.setdefault("design_freeze_summary", freeze_summary)
    return contract


def _parse_traceability_matrix(block: str) -> list[dict[str, Any]]:
    lines = block.splitlines()
    try:
        start_idx = next(idx for idx, line in enumerate(lines) if line.strip().startswith("traceability_matrix:"))
    except StopIteration as exc:
        raise AlignmentCheckError("traceability_matrix 解析失败：缺少 traceability_matrix") from exc

    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        indent = _indent(line)

        if not stripped:
            idx += 1
            continue
        if indent < 2:
            break

        if indent == 2 and stripped.startswith("- "):
            if current:
                rows.append(current)
            current = {}
            key, value = _split_key_value(stripped[2:])
            if key:
                current[key] = _parse_scalar_literal(value)
            idx += 1
            continue

        if current is None:
            idx += 1
            continue

        if indent == 4:
            key, value = _split_key_value(stripped)
            if key:
                current[key] = _parse_scalar_literal(value)
            idx += 1
            continue

        idx += 1

    if current:
        rows.append(current)

    return rows


def _parse_implementation_tasks(block: str) -> dict[str, dict[str, Any]]:
    lines = block.splitlines()
    try:
        start_idx = next(
            idx for idx, line in enumerate(lines) if line.strip().startswith("implementation_tasks:")
        )
    except StopIteration as exc:
        raise AlignmentCheckError("implementation_tasks 解析失败：缺少 implementation_tasks") from exc

    tasks: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    current_list_key = ""

    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        indent = _indent(line)

        if not stripped:
            idx += 1
            continue
        if indent < 2:
            break

        if indent == 2 and stripped.startswith("- "):
            if current and current.get("task_id"):
                task_id = _normalize_id(current["task_id"])
                if task_id in tasks:
                    raise AlignmentCheckError(f"implementation_tasks 存在重复 task_id: {task_id}")
                tasks[task_id] = current

            current = {
                "task_id": "",
                "phase": "",
                "change_type": "",
                "owner": "",
                "pr_id": "",
                "risk_point": "",
                "rollback_point": "",
                "depends_on_tasks": [],
                "file_paths": [],
                "symbols": [],
                "acceptance_cmds": [],
            }
            current_list_key = ""

            key, value = _split_key_value(stripped[2:])
            if key == "task_id":
                current["task_id"] = _normalize_id(value)
            idx += 1
            continue

        if current is None:
            idx += 1
            continue

        if indent == 4:
            key, value = _split_key_value(stripped)
            current_list_key = ""

            if key == "task_id":
                current["task_id"] = _normalize_id(value)
            elif key in {"phase", "change_type", "owner", "pr_id", "risk_point", "rollback_point"}:
                current[key] = _normalize_text(value)
            elif key in {"depends_on_tasks", "file_paths", "symbols"}:
                current[key] = [item for item in _parse_inline_list(value) if item]
                if value == "":
                    current_list_key = key
            elif key == "acceptance_cmds":
                current[key] = [cmd for cmd in _parse_inline_list(value, as_cmd=True) if cmd]
                if value == "":
                    current_list_key = key
            idx += 1
            continue

        if current_list_key and indent >= 6 and stripped.startswith("- "):
            if current_list_key == "acceptance_cmds":
                cmd = _normalize_cmd(stripped[2:])
                if cmd and cmd not in current[current_list_key]:
                    current[current_list_key].append(cmd)
            else:
                value = _normalize_text(stripped[2:])
                if value and value not in current[current_list_key]:
                    current[current_list_key].append(value)
            idx += 1
            continue

        idx += 1

    if current and current.get("task_id"):
        task_id = _normalize_id(current["task_id"])
        if task_id in tasks:
            raise AlignmentCheckError(f"implementation_tasks 存在重复 task_id: {task_id}")
        tasks[task_id] = current

    return tasks


def _parse_implementation_readiness(block: str) -> dict[str, Any]:
    lines = block.splitlines()
    try:
        start_idx = next(
            idx for idx, line in enumerate(lines) if line.strip().startswith("implementation_readiness:")
        )
    except StopIteration as exc:
        raise AlignmentCheckError("implementation_readiness 解析失败：缺少 implementation_readiness") from exc

    readiness: dict[str, Any] = {}
    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        indent = _indent(line)

        if not stripped:
            idx += 1
            continue
        if indent < 2:
            break

        if indent == 2:
            key, value = _split_key_value(stripped)
            readiness[key] = _parse_scalar_literal(value)
        idx += 1

    return readiness


def _resolve_design_path(
    *,
    repo_root: Path,
    design_path_raw: str | None,
    requirements_path: Path,
    requirements_contract: dict[str, Any],
) -> Path:
    if design_path_raw:
        return _resolve_markdown_path(repo_root=repo_root, raw_value=design_path_raw, label="design")

    design_source = _normalize_text(requirements_contract.get("design_source"))
    if not design_source:
        raise AlignmentCheckError("requirements_contract.design_source 不能为空（禁止从叙述文本回退推断）")

    candidate = Path(design_source).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    candidate = candidate.resolve()
    if not candidate.exists() or not candidate.is_file():
        raise AlignmentCheckError(f"design_source 指向文件不存在: {candidate}")
    return candidate


def _normalize_cmd_for_ref(raw: str) -> str:
    cmd = _normalize_cmd(raw)
    if "&&" in cmd:
        parts = [part.strip() for part in cmd.split("&&") if part.strip()]
        if parts:
            cmd = parts[-1]
    cmd = cmd.replace("PYTHONPATH=. ", "")
    return _normalize_cmd(cmd)


def _commands_equivalent(left: str, right: str) -> bool:
    a = _normalize_cmd_for_ref(left)
    b = _normalize_cmd_for_ref(right)
    if not a or not b:
        return False
    return a == b


def run_alignment_check(
    *,
    repo_root: Path,
    task_split_dir_raw: str | None = None,
    requirements_path_raw: str | None = None,
    implementation_path_raw: str | None = None,
    design_path_raw: str | None = None,
) -> dict[str, Any]:
    task_split_dir = (
        _resolve_task_split_dir(repo_root, task_split_dir_raw) if task_split_dir_raw else None
    )
    implementation_path = _resolve_implementation_plan(
        repo_root=repo_root,
        task_split_dir=task_split_dir,
        implementation_path_raw=implementation_path_raw,
    )
    requirements_path = _resolve_requirements_path(
        repo_root=repo_root,
        requirements_path_raw=requirements_path_raw,
        implementation_path=implementation_path,
    )

    requirements_blocks = _extract_yaml_blocks(requirements_path)
    forbidden_in_requirements = _detect_forbidden_protocol_tokens(
        blocks=requirements_blocks,
    )
    req_contract_block = _find_block(requirements_blocks, "requirements_contract:", requirements_path)
    requirements_contract = _parse_requirements_contract(req_contract_block)

    design_path = _resolve_design_path(
        repo_root=repo_root,
        design_path_raw=design_path_raw,
        requirements_path=requirements_path,
        requirements_contract=requirements_contract,
    )

    design_blocks = _extract_yaml_blocks(design_path)
    design_freeze_block = _find_block(design_blocks, "design_freeze_summary:", design_path)
    design_freeze_summary = _parse_design_freeze_summary(design_freeze_block)
    design_approval = _parse_design_approval(design_path)
    design_product_contract = _parse_design_product_contract(design_path)
    clarify_consistency_check: dict[str, Any] = {}
    try:
        clarify_consistency_block = _find_block(design_blocks, "clarify_consistency_check:", design_path)
    except AlignmentCheckError:
        clarify_consistency_block = ""
    if clarify_consistency_block:
        clarify_consistency_check = _parse_clarify_consistency_check(clarify_consistency_block)
    handoff_contract: dict[str, Any] = {}
    try:
        handoff_block = _find_block(design_blocks, "clarify_handoff_contract:", design_path)
    except AlignmentCheckError:
        handoff_block = ""
    if handoff_block:
        handoff_contract = _parse_clarify_handoff_contract(handoff_block)

    impl_blocks = _extract_yaml_blocks(implementation_path)
    forbidden_in_implementation = _detect_forbidden_protocol_tokens(
        blocks=impl_blocks,
    )
    impl_tasks_block = _find_block(impl_blocks, "implementation_tasks:", implementation_path)
    implementation_tasks = _parse_implementation_tasks(impl_tasks_block)
    readiness_block = _find_block(impl_blocks, "implementation_readiness:", implementation_path)
    implementation_readiness = _parse_implementation_readiness(readiness_block)

    traceability_block = _find_block(requirements_blocks, "traceability_matrix:", requirements_path)
    traceability_matrix = _parse_traceability_matrix(traceability_block)

    errors: list[dict[str, Any]] = []

    def add_error(code: str, message: str, details: Any) -> None:
        errors.append({"code": code, "message": message, "details": details})

    if forbidden_in_requirements:
        add_error(
            "PLAN_FORBIDDEN_PROTOCOL_FIELD_DETECTED",
            "requirements 检测到禁用旧协议字段",
            {
                "file": str(requirements_path),
                "tokens": forbidden_in_requirements,
            },
        )

    if forbidden_in_implementation:
        add_error(
            "PLAN_FORBIDDEN_PROTOCOL_FIELD_DETECTED",
            "implementation_plan 检测到禁用旧协议字段",
            {
                "file": str(implementation_path),
                "tokens": forbidden_in_implementation,
            },
        )

    if design_approval.get("design_approved") is not True:
        add_error(
            "DESIGN_APPROVAL_REQUIRED",
            "design 缺少 design_approved=true",
            {"design_approved": design_approval.get("design_approved")},
        )

    approval_missing = [
        field
        for field in ("approved_at", "approved_round", "approval_evidence")
        if not _normalize_text(design_approval.get(field))
    ]
    if approval_missing:
        code = (
            "DESIGN_APPROVAL_EVIDENCE_MISSING"
            if "approval_evidence" in approval_missing and len(approval_missing) == 1
            else "DESIGN_APPROVAL_REQUIRED"
        )
        add_error(
            code,
            "design 审批记录字段不完整",
            {"missing_fields": approval_missing},
        )

    if requirements_contract.get("design_approved") is not True:
        add_error(
            "PLAN_REQUIREMENTS_CONTRACT_BROKEN",
            "requirements_contract.design_approved 必须为 true",
            {"design_approved": requirements_contract.get("design_approved")},
        )

    if not clarify_consistency_block:
        add_error(
            "CLARIFY_CONSISTENCY_CHECK_MISSING",
            "design 缺少 clarify_consistency_check 机读区块",
            {},
        )
    else:
        clarify_phase = _normalize_text(clarify_consistency_check.get("clarify_phase")).lower()
        if clarify_phase != "approval":
            add_error(
                "CLARIFY_DESIGN_STATE_INVALID",
                "clarify_consistency_check.clarify_phase 必须为 approval",
                {"clarify_phase": clarify_consistency_check.get("clarify_phase")},
            )
        question_mode = _normalize_text(clarify_consistency_check.get("question_mode")).lower()
        if question_mode not in {"package", "single"}:
            add_error(
                "CLARIFY_QUESTION_MODE_INVALID",
                "clarify_consistency_check.question_mode 仅允许 package|single",
                {"question_mode": clarify_consistency_check.get("question_mode")},
            )
        current_round_raw = clarify_consistency_check.get("current_round")
        try:
            current_round = int(current_round_raw)
        except Exception:
            current_round = 0
        if current_round < 1:
            add_error(
                "CLARIFY_ROUND_INVALID",
                "clarify_consistency_check.current_round 必须 >= 1",
                {"current_round": current_round_raw},
            )
        open_questions_raw = clarify_consistency_check.get("open_questions_count")
        try:
            open_questions_count = int(open_questions_raw)
        except Exception:
            open_questions_count = -1
        if open_questions_count != 0:
            add_error(
                "CLARIFY_OPEN_QUESTIONS_REMAIN",
                "clarify_consistency_check.open_questions_count 必须为 0",
                {"open_questions_count": open_questions_raw},
            )
        fail_fast_codes = [code for code in _as_list(clarify_consistency_check.get("fail_fast_codes")) if _normalize_text(code)]
        if fail_fast_codes:
            add_error(
                "CLARIFY_CONSISTENCY_FAIL_FAST",
                "clarify_consistency_check.fail_fast_codes 必须为空",
                {"fail_fast_codes": fail_fast_codes},
            )

    if not handoff_block:
        add_error(
            "CLARIFY_HANDOFF_CONTRACT_MISSING",
            "design 缺少 clarify_handoff_contract 机读区块",
            {},
        )
    else:
        if handoff_contract.get("handoff_ready") is not True:
            add_error(
                "CLARIFY_PLAN_BRIDGE_BROKEN",
                "clarify_handoff_contract.handoff_ready 必须为 true",
                {"handoff_ready": handoff_contract.get("handoff_ready")},
            )
        if int(handoff_contract.get("requirement_seed_count", 0)) <= 0:
            add_error(
                "CLARIFY_PLAN_BRIDGE_BROKEN",
                "clarify_handoff_contract.required.requirement_seeds（或 v1 requirement_seeds）不能为空",
                {"requirement_seed_count": handoff_contract.get("requirement_seed_count", 0)},
            )
        if not handoff_contract.get("implementation_seed_task_ids"):
            add_error(
                "CLARIFY_PLAN_BRIDGE_BROKEN",
                "clarify_handoff_contract.required.implementation_seeds（或 v1 implementation_seeds）不能为空",
                {},
            )
        if not handoff_contract.get("has_execution_chain_seed"):
            add_error(
                "CLARIFY_PLAN_BRIDGE_BROKEN",
                "clarify_handoff_contract 缺少 execution_chain_seed",
                {},
            )
        if not handoff_contract.get("has_execution_contract_hint"):
            add_error(
                "CLARIFY_PLAN_BRIDGE_BROKEN",
                "clarify_handoff_contract.required.execution_chain_seed（或 v1 execution_chain_seed）缺少 execution_contract_hint",
                {},
            )
        if not handoff_contract.get("has_product_contract_summary"):
            add_error(
                "PLAN_PRODUCT_CONTRACT_MISSING",
                "clarify_handoff_contract.required.product_contract_summary 缺失",
                {},
            )
        product_summary_gaps = {
            "missing_fields": handoff_contract.get("product_contract_summary_missing", []),
            "empty_fields": handoff_contract.get("product_contract_summary_empty", []),
            "placeholder_fields": handoff_contract.get("product_contract_summary_placeholder", []),
        }
        if (
            product_summary_gaps["missing_fields"]
            or product_summary_gaps["empty_fields"]
            or product_summary_gaps["placeholder_fields"]
        ):
            add_error(
                "PLAN_PRODUCT_CONTRACT_INCOMPLETE",
                "product_contract_summary 字段不完整或包含占位值",
                product_summary_gaps,
            )

    req_handoff_source = _normalize_text(requirements_contract.get("clarify_handoff_source"))
    req_handoff_version = _normalize_text(requirements_contract.get("clarify_handoff_version"))
    if handoff_block and not req_handoff_source:
        add_error(
            "CLARIFY_PLAN_BRIDGE_BROKEN",
            "requirements_contract.clarify_handoff_source 不能为空",
            {},
        )
    if handoff_block and not req_handoff_version:
        add_error(
            "CLARIFY_PLAN_BRIDGE_BROKEN",
            "requirements_contract.clarify_handoff_version 不能为空",
            {},
        )
    handoff_version = _normalize_text(handoff_contract.get("version"))
    if handoff_block and req_handoff_version and handoff_version and req_handoff_version != handoff_version:
        add_error(
            "CLARIFY_PLAN_BRIDGE_BROKEN",
            "clarify_handoff_version 在 design 与 requirements 间不一致",
            {
                "design_handoff_version": handoff_version,
                "requirements_handoff_version": req_handoff_version,
            },
        )

    req_approval_evidence = _normalize_text(requirements_contract.get("design_approval_evidence"))
    if not req_approval_evidence:
        add_error(
            "DESIGN_APPROVAL_EVIDENCE_MISSING",
            "requirements_contract.design_approval_evidence 不能为空",
            {},
        )

    design_approval_evidence = _normalize_text(design_approval.get("approval_evidence"))
    if req_approval_evidence and design_approval_evidence and req_approval_evidence != design_approval_evidence:
        add_error(
            "CLARIFY_PLAN_BRIDGE_BROKEN",
            "design 与 requirements 的审批证据不一致",
            {
                "design_approval_evidence": design_approval_evidence,
                "requirements_approval_evidence": req_approval_evidence,
            },
        )

    req_design_source = _normalize_text(requirements_contract.get("design_source"))
    if req_design_source:
        req_design_path = Path(req_design_source).expanduser()
        if not req_design_path.is_absolute():
            req_design_path = (repo_root / req_design_path).resolve()
        else:
            req_design_path = req_design_path.resolve()
        if req_design_path != design_path:
            add_error(
                "CLARIFY_PLAN_BRIDGE_BROKEN",
                "requirements_contract.design_source 与实际 design 路径不一致",
                {
                    "requirements_contract.design_source": str(req_design_path),
                    "resolved_design_path": str(design_path),
                },
            )

    req_freeze_summary = requirements_contract.get("design_freeze_summary")
    if not isinstance(req_freeze_summary, dict):
        add_error(
            "PLAN_REQUIREMENTS_CONTRACT_BROKEN",
            "requirements_contract.design_freeze_summary 缺失或类型错误",
            {"design_freeze_summary": req_freeze_summary},
        )
        req_freeze_summary = {}

    for summary_name, summary in (
        ("design", design_freeze_summary),
        ("requirements", req_freeze_summary),
    ):
        actionable = bool(summary.get("design_actionable"))
        missing_blocks = _as_list(summary.get("missing_blocks"))
        if not actionable or missing_blocks:
            add_error(
                "DESIGN_NOT_ACTIONABLE",
                f"{summary_name} 的 design_freeze_summary 不可执行",
                {
                    "design_actionable": summary.get("design_actionable"),
                    "missing_blocks": missing_blocks,
                },
            )

        risk_count_raw = summary.get("risk_counterexamples_count")
        try:
            risk_count = int(risk_count_raw)
        except Exception:
            risk_count = 0
        if risk_count < 2:
            add_error(
                "DESIGN_RISK_EXAMPLES_INSUFFICIENT",
                f"{summary_name} 的 risk_counterexamples_count < 2",
                {"risk_counterexamples_count": risk_count_raw},
            )

        if summary.get("product_contract_ready") is not True:
            add_error(
                "PLAN_PRODUCT_CONTRACT_MISSING",
                f"{summary_name} 的 product_contract_ready 必须为 true",
                {"product_contract_ready": summary.get("product_contract_ready")},
            )

    freeze_keys = (
        "design_actionable",
        "missing_blocks",
        "risk_level",
        "risk_counterexamples_count",
        "product_contract_ready",
    )
    freeze_diff: list[dict[str, Any]] = []
    for key in freeze_keys:
        design_value = design_freeze_summary.get(key)
        req_value = req_freeze_summary.get(key)
        if isinstance(design_value, list):
            design_value = sorted(_normalize_text(item) for item in design_value if _normalize_text(item))
        if isinstance(req_value, list):
            req_value = sorted(_normalize_text(item) for item in req_value if _normalize_text(item))
        if design_value == req_value:
            continue
        freeze_diff.append(
            {
                "field": key,
                "design": design_value,
                "requirements": req_value,
            }
        )
    if freeze_diff:
        add_error(
            "CLARIFY_PLAN_BRIDGE_BROKEN",
            "design_freeze_summary 在 design 与 requirements 间不一致",
            freeze_diff,
        )

    if not design_product_contract.get("section_exists"):
        add_error(
            "PLAN_PRODUCT_CONTRACT_MISSING",
            "design 缺少 product_contract（PRD-Lite）章节",
            {},
        )
    product_contract_gaps = {
        "missing_fields": design_product_contract.get("missing_fields", []),
        "empty_fields": design_product_contract.get("empty_fields", []),
        "placeholder_fields": design_product_contract.get("placeholder_fields", []),
    }
    if (
        product_contract_gaps["missing_fields"]
        or product_contract_gaps["empty_fields"]
        or product_contract_gaps["placeholder_fields"]
    ):
        add_error(
            "PLAN_PRODUCT_CONTRACT_INCOMPLETE",
            "design.product_contract 字段不完整或包含占位值",
            product_contract_gaps,
        )

    if not traceability_matrix:
        add_error(
            "PLAN_TRACEABILITY_MATRIX_MISSING",
            "traceability_matrix 不能为空",
            {},
        )

    detail_insufficient: list[dict[str, Any]] = []
    for task_id, task in implementation_tasks.items():
        missing_fields: list[str] = []
        for field in REQUIRED_TASK_SCALAR_FIELDS:
            if not _normalize_text(task.get(field)):
                missing_fields.append(field)
        for field in REQUIRED_TASK_LIST_FIELDS:
            if not _as_list(task.get(field)):
                missing_fields.append(field)
        if missing_fields:
            detail_insufficient.append(
                {
                    "task_id": task_id,
                    "missing_fields": sorted(set(missing_fields)),
                }
            )

    if detail_insufficient:
        add_error(
            "PLAN_IMPLEMENTATION_DETAIL_INSUFFICIENT",
            "implementation_tasks 缺少可执行实现细节字段",
            detail_insufficient,
        )

    impl_task_ids = set(implementation_tasks.keys())
    trace_task_ids: set[str] = set()
    missing_trace_fields: list[dict[str, Any]] = []
    acceptance_ref_errors: list[dict[str, Any]] = []

    for idx, row in enumerate(traceability_matrix, start=1):
        if not isinstance(row, dict):
            missing_trace_fields.append({"row": idx, "reason": "row_not_object"})
            continue
        task_id = _normalize_id(row.get("task_id"))
        cmd_ref = _normalize_cmd(str(row.get("acceptance_cmd_ref") or ""))
        if not task_id or not cmd_ref:
            missing_trace_fields.append(
                {
                    "row": idx,
                    "task_id": task_id,
                    "acceptance_cmd_ref": cmd_ref,
                }
            )
            continue

        trace_task_ids.add(task_id)
        impl_task = implementation_tasks.get(task_id)
        if not impl_task:
            acceptance_ref_errors.append(
                {
                    "row": idx,
                    "task_id": task_id,
                    "error": "task_id_not_found_in_implementation_tasks",
                }
            )
            continue

        impl_cmds = {cmd for cmd in _as_list(impl_task.get("acceptance_cmds")) if _normalize_cmd(cmd)}
        if any(_commands_equivalent(cmd_ref, impl_cmd) for impl_cmd in impl_cmds):
            continue

        acceptance_ref_errors.append(
            {
                "row": idx,
                "task_id": task_id,
                "acceptance_cmd_ref": cmd_ref,
                "implementation_acceptance_cmds": sorted(impl_cmds),
            }
        )

    if missing_trace_fields:
        add_error(
            "PLAN_TRACEABILITY_MATRIX_BROKEN",
            "traceability_matrix 存在缺少 task_id 或 acceptance_cmd_ref 的行",
            missing_trace_fields,
        )

    if acceptance_ref_errors:
        add_error(
            "PLAN_ACCEPTANCE_REF_BROKEN",
            "traceability_matrix 与 implementation_tasks.acceptance_cmds 不一致",
            acceptance_ref_errors,
        )

    missing_trace_for_impl = sorted(impl_task_ids - trace_task_ids)
    if missing_trace_for_impl:
        add_error(
            "PLAN_TRACEABILITY_MATRIX_BROKEN",
            "implementation_tasks 存在未被 traceability_matrix 覆盖的 task_id",
            {"missing_task_ids": missing_trace_for_impl},
        )

    if handoff_block:
        handoff_task_ids = set(_as_list(handoff_contract.get("implementation_seed_task_ids")))
        missing_impl_for_handoff = sorted(handoff_task_ids - impl_task_ids)
        if missing_impl_for_handoff:
            add_error(
                "CLARIFY_PLAN_BRIDGE_BROKEN",
                "clarify_handoff_contract implementation_seeds 未完整映射到 implementation_tasks",
                {"missing_task_ids": missing_impl_for_handoff},
            )

    requirements_status = _normalize_text(requirements_contract.get("status")).lower()
    implementation_ready = bool(implementation_readiness.get("implementation_ready"))
    if requirements_status in {"draft", "草稿"} and implementation_ready:
        add_error(
            "PLAN_READINESS_STATUS_CONFLICT",
            "requirements_contract.status 为 draft/草稿 时 implementation_ready 不能为 true",
            {
                "requirements_status": requirements_contract.get("status"),
                "implementation_ready": implementation_readiness.get("implementation_ready"),
            },
        )

    ok = len(errors) == 0
    return {
        "ok": ok,
        "task_split_dir": task_split_dir.name if task_split_dir else "",
        "design": str(design_path),
        "requirements": str(requirements_path),
        "implementation_plan": str(implementation_path),
        "summary": {
            "traceability_rows": len(traceability_matrix),
            "implementation_tasks": len(implementation_tasks),
            "tasks_missing_required_details": len(detail_insufficient),
        },
        "errors": errors,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验 requirements / design / implementation_plan 承接完整性")
    parser.add_argument("--task-split-dir", help="任务拆解目录（名称或路径）")
    parser.add_argument("--requirements-path", help="requirements 文档路径")
    parser.add_argument("--implementation-path", help="implementation_plan 文档路径")
    parser.add_argument("--design-path", help="design 文档路径（可选；默认从 requirements_contract.design_source 推断）")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument("--output", default="-", help="输出路径；默认 stdout，传 '-' 表示 stdout")
    return parser


def _write_output(payload: dict[str, Any], output: str) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if output == "-":
        print(serialized)
        return

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized + "\n", encoding="utf-8")
    print(f"written: {output_path}")
    print(serialized)


def main() -> int:
    args = _build_parser().parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()

    try:
        result = run_alignment_check(
            repo_root=repo_root,
            task_split_dir_raw=args.task_split_dir,
            requirements_path_raw=args.requirements_path,
            implementation_path_raw=args.implementation_path,
            design_path_raw=args.design_path,
        )
    except AlignmentCheckError as exc:
        payload = {
            "ok": False,
            "error": {
                "code": "CLARIFY_PLAN_ALIGNMENT_FAILED",
                "message": str(exc),
            },
        }
        _write_output(payload, args.output)
        return 2

    _write_output(result, args.output)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
