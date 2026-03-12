#!/usr/bin/env python3
"""统一门禁入口：按 mode 分发到既有 workflow contract 校验实现。"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from task_split_paths import CANONICAL_TASK_SPLIT_BASE, LEGACY_TASK_SPLIT_BASE, resolve_task_split_paths

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
USAGE_LOG_PATH = ROOT / "logs" / "workflow-gate-usage.jsonl"
USAGE_OBSERVED_MODES = {"clarify_plan", "clarify_consistency", "plan_vk_coverage", "gate_contract", "integration_gate"}
TRUTH_SOURCE_FILENAMES = {"_active_task.json", "task-ledger.jsonl", "coder4-idempotency.json", "task-runner-state.json", "task-runner-state.json.lock"}



TEMPORAL_GATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("temporal_zero_call_requirement", re.compile(r"(?:连续|删除前)?\s*7\s*天.*零调用|7\s*天.*零调用")),
    ("temporal_window_hint", re.compile(r"观测窗口|时间窗")),
    ("temporal_window_flag", re.compile(r"--window-days(?:=|\s+)")),
    ("temporal_window_field", re.compile(r"ZERO_CALL_WINDOW_NOT_MATURE|eligible_after|window_days")),
)

YAML_BLOCK_PATTERN = re.compile(r"```yaml\s*(.*?)```", flags=re.DOTALL | re.IGNORECASE)
DB_RISK_TAGS = {"chat_db", "data_db"}
DB_EVIDENCE_HINTS = {
    "chat_db": ("chat_db", "write_read", "write-read"),
    "data_db": ("data_db", "route_sql", "analytics_route", "sql_result"),
}
ALLOWED_ACCEPTANCE_KINDS = {"unit", "api", "chat_db", "data_db", "scripted_flow", "integration", "e2e"}


def _normalize_contract_token(raw: Any) -> str:
    return str(raw or "").strip().strip("`'\"").lower()


def _split_key_value(text: str) -> tuple[str, str]:
    key, sep, value = str(text or "").partition(":")
    if not sep:
        return key.strip(), ""
    return key.strip(), value.strip()


def _parse_inline_list(raw: str) -> list[str]:
    value = str(raw or "").strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    items = []
    for segment in value.split(","):
        token = _normalize_contract_token(segment)
        if token:
            items.append(token)
    return items


def _extract_yaml_blocks_from_markdown(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    return YAML_BLOCK_PATTERN.findall(content)


def _find_yaml_block(blocks: list[str], marker: str) -> str:
    for block in blocks:
        if marker in block:
            return block
    raise ValueError(f"缺少 yaml block: {marker}")


def _parse_implementation_tasks_contract(implementation_path: Path) -> list[dict[str, Any]]:
    blocks = _extract_yaml_blocks_from_markdown(implementation_path)
    block = _find_yaml_block(blocks, "implementation_tasks:")
    lines = block.splitlines()

    start_idx = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith("implementation_tasks:"):
            start_idx = idx
            break
    if start_idx < 0:
        return []

    tasks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    list_mode = ""
    acceptance_mode = False
    current_acceptance: dict[str, str] | None = None

    idx = start_idx + 1
    while idx < len(lines):
        raw_line = lines[idx]
        line = raw_line.rstrip()
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if acceptance_mode and current_acceptance is not None and indent <= 4:
            current["acceptance_cmds"].append(current_acceptance)
            current_acceptance = None

        if not stripped:
            idx += 1
            continue
        if indent < 2:
            break

        if indent == 2 and stripped.startswith("- "):
            if current is not None:
                if current_acceptance is not None:
                    current["acceptance_cmds"].append(current_acceptance)
                    current_acceptance = None
                tasks.append(current)
            current = {
                "task_id": "",
                "risk_tags": [],
                "mandatory_evidence": [],
                "acceptance_cmds": [],
            }
            list_mode = ""
            acceptance_mode = False

            key, value = _split_key_value(stripped[2:])
            if key == "task_id":
                current["task_id"] = _normalize_contract_token(value).upper()
            idx += 1
            continue

        if current is None:
            idx += 1
            continue

        if indent == 4:
            key, value = _split_key_value(stripped)
            list_mode = ""
            if key == "task_id":
                current["task_id"] = _normalize_contract_token(value).upper()
                acceptance_mode = False
            elif key == "risk_tags":
                current["risk_tags"].extend(_parse_inline_list(value))
                list_mode = "risk_tags" if not value else ""
                acceptance_mode = False
            elif key == "mandatory_evidence":
                current["mandatory_evidence"].extend(_parse_inline_list(value))
                list_mode = "mandatory_evidence" if not value else ""
                acceptance_mode = False
            elif key == "acceptance_cmds":
                acceptance_mode = True
                if value and value not in {"[]", ""}:
                    for cmd in _parse_inline_list(value):
                        current["acceptance_cmds"].append({"kind": "", "cmd": cmd})
            else:
                acceptance_mode = False
            idx += 1
            continue

        if list_mode in {"risk_tags", "mandatory_evidence"} and indent >= 6 and stripped.startswith("- "):
            token = _normalize_contract_token(stripped[2:])
            if token:
                current[list_mode].append(token)
            idx += 1
            continue

        if acceptance_mode and indent >= 6:
            if stripped.startswith("- "):
                if current_acceptance is not None:
                    current["acceptance_cmds"].append(current_acceptance)
                entry = stripped[2:].strip()
                cmd_item = {"kind": "", "cmd": ""}
                key, value = _split_key_value(entry)
                if key in {"kind", "cmd"}:
                    cmd_item[key] = _normalize_contract_token(value)
                else:
                    cmd_item["cmd"] = _normalize_contract_token(entry)
                current_acceptance = cmd_item
            elif current_acceptance is not None and indent >= 8:
                key, value = _split_key_value(stripped)
                if key in {"kind", "cmd"}:
                    current_acceptance[key] = _normalize_contract_token(value)
            idx += 1
            continue

        idx += 1

    if current is not None:
        if current_acceptance is not None:
            current["acceptance_cmds"].append(current_acceptance)
        tasks.append(current)

    normalized_tasks: list[dict[str, Any]] = []
    for task in tasks:
        normalized_tasks.append(
            {
                "task_id": str(task.get("task_id") or "").strip().upper(),
                "risk_tags": sorted({item for item in task.get("risk_tags", []) if item}),
                "mandatory_evidence": sorted({item for item in task.get("mandatory_evidence", []) if item}),
                "acceptance_cmds": [
                    {
                        "kind": _normalize_contract_token(item.get("kind")),
                        "cmd": str(item.get("cmd") or "").strip(),
                    }
                    for item in task.get("acceptance_cmds", [])
                    if isinstance(item, dict)
                ],
            }
        )
    return normalized_tasks


def _db_hint_from_acceptance(task: dict[str, Any]) -> bool:
    for item in task.get("acceptance_cmds", []):
        kind = _normalize_contract_token(item.get("kind"))
        if "chat_db" in kind or "data_db" in kind:
            return True
    return False


def _validate_plan_db_evidence_contract(implementation_path: Path) -> dict[str, Any]:
    tasks = _parse_implementation_tasks_contract(implementation_path)
    errors: list[dict[str, Any]] = []

    for task in tasks:
        task_id = task.get("task_id") or "UNKNOWN"
        risk_tags = set(task.get("risk_tags") or [])
        mandatory = set(task.get("mandatory_evidence") or [])
        acceptance_cmds = task.get("acceptance_cmds") or []

        inferred_db_hint = bool({tag for tag in mandatory if "chat_db" in tag or "data_db" in tag}) or _db_hint_from_acceptance(task)
        has_chat_risk = "chat_db" in risk_tags
        has_data_risk = "data_db" in risk_tags
        db_risk = has_chat_risk or has_data_risk or inferred_db_hint

        if db_risk and not risk_tags:
            errors.append(
                {
                    "code": "PLAN_RISK_TAGS_MISSING",
                    "message": "DB 风险任务缺少 risk_tags",
                    "details": {"task_id": task_id},
                }
            )

        if db_risk:
            if not mandatory:
                errors.append(
                    {
                        "code": "PLAN_DB_EVIDENCE_MISSING",
                        "message": "DB 风险任务缺少 mandatory_evidence",
                        "details": {"task_id": task_id, "risk_tags": sorted(risk_tags)},
                    }
                )
            if has_chat_risk and not any(any(hint in item for hint in DB_EVIDENCE_HINTS["chat_db"]) for item in mandatory):
                errors.append(
                    {
                        "code": "PLAN_DB_EVIDENCE_MISSING",
                        "message": "chat_db 风险任务缺少 chat_db 类 mandatory_evidence",
                        "details": {"task_id": task_id, "mandatory_evidence": sorted(mandatory)},
                    }
                )
            if has_data_risk and not any(any(hint in item for hint in DB_EVIDENCE_HINTS["data_db"]) for item in mandatory):
                errors.append(
                    {
                        "code": "PLAN_DB_EVIDENCE_MISSING",
                        "message": "data_db 风险任务缺少 data_db 类 mandatory_evidence",
                        "details": {"task_id": task_id, "mandatory_evidence": sorted(mandatory)},
                    }
                )

        if db_risk:
            invalid_cmds = []
            for item in acceptance_cmds:
                kind = _normalize_contract_token(item.get("kind"))
                cmd = str(item.get("cmd") or "").strip()
                if not kind or not cmd or kind not in ALLOWED_ACCEPTANCE_KINDS:
                    invalid_cmds.append({"kind": kind, "cmd": cmd})
            if invalid_cmds:
                errors.append(
                    {
                        "code": "PLAN_EVIDENCE_KIND_INVALID",
                        "message": "DB 风险任务 acceptance_cmds[*].kind/cmd 不合法",
                        "details": {"task_id": task_id, "invalid_acceptance_cmds": invalid_cmds},
                    }
                )

    return {
        "ok": not errors,
        "implementation_plan": str(implementation_path),
        "tasks_checked": len(tasks),
        "errors": errors,
    }


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def _validate_vkplan_db_evidence_contract(*, repo_root: Path, task_split_dir: Path, implementation_path: Path) -> dict[str, Any]:
    tasks = _parse_implementation_tasks_contract(implementation_path)
    tasks_by_id = {str(task.get("task_id") or "").upper(): task for task in tasks if task.get("task_id")}

    locator = resolve_task_split_paths(repo_root, task_split_dir.name, must_exist=True)
    vk_cards_path = locator.vk_cards_file
    vk_cards_payload = _load_json_object(vk_cards_path)
    cards = vk_cards_payload.get("cards") or []

    cards_by_task: dict[str, list[dict[str, Any]]] = {}
    evidence_mapping_missing: list[dict[str, Any]] = []

    for raw_card in cards:
        if not isinstance(raw_card, dict):
            continue
        card_id = str(raw_card.get("card_id") or "").strip().upper()
        task_ids = [str(item or "").strip().upper() for item in raw_card.get("task_ids") or [] if str(item or "").strip()]
        card_tags = {_normalize_contract_token(item) for item in raw_card.get("risk_tags") or [] if _normalize_contract_token(item)}
        card_evidence = {_normalize_contract_token(item) for item in raw_card.get("mandatory_evidence") or [] if _normalize_contract_token(item)}

        for task_id in task_ids:
            cards_by_task.setdefault(task_id, []).append(raw_card)
            task = tasks_by_id.get(task_id)
            if not task:
                continue
            required_tags = set(task.get("risk_tags") or [])
            required_evidence = set(task.get("mandatory_evidence") or [])
            missing_tags = sorted(required_tags - card_tags)
            missing_evidence = sorted(required_evidence - card_evidence)
            if missing_tags or missing_evidence:
                evidence_mapping_missing.append(
                    {
                        "card_id": card_id,
                        "task_id": task_id,
                        "missing_risk_tags": missing_tags,
                        "missing_mandatory_evidence": missing_evidence,
                    }
                )

    split_unclosed: list[dict[str, Any]] = []
    for task_id, task in tasks_by_id.items():
        risk_tags = set(task.get("risk_tags") or [])
        if not (risk_tags & DB_RISK_TAGS):
            continue
        task_cards = cards_by_task.get(task_id, [])
        if len(task_cards) <= 1:
            continue
        candidate_card_ids = {str(card.get("card_id") or "").strip().upper() for card in task_cards}
        closure_ok = False
        for card in task_cards:
            closure = card.get("cross_card_closure")
            if not isinstance(closure, dict):
                continue
            if not bool(closure.get("required")):
                continue
            owner = str(closure.get("closure_owner") or "").strip().upper()
            if owner and owner in candidate_card_ids:
                closure_ok = True
                break
        if not closure_ok:
            split_unclosed.append(
                {
                    "task_id": task_id,
                    "cards": sorted(candidate_card_ids),
                    "risk_tags": sorted(risk_tags),
                }
            )

    errors: list[dict[str, Any]] = []
    if evidence_mapping_missing:
        errors.append(
            {
                "code": "VKPLAN_EVIDENCE_MAPPING_BROKEN",
                "message": "vk_cards 证据继承不完整（risk_tags/mandatory_evidence）",
                "details": evidence_mapping_missing,
            }
        )
    if split_unclosed:
        errors.append(
            {
                "code": "VKPLAN_DB_CHAIN_SPLIT_UNCLOSED",
                "message": "DB 风险链路拆卡后缺少 cross_card_closure 闭环声明",
                "details": split_unclosed,
            }
        )

    return {
        "ok": not errors,
        "implementation_plan": str(implementation_path),
        "vk_cards": str(vk_cards_path),
        "evidence_mapping_missing": evidence_mapping_missing,
        "db_chain_split_unclosed": split_unclosed,
        "errors": errors,
    }


def _merge_error_entries(existing: Any, new_errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for item in existing if isinstance(existing, list) else []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "")
        message = str(item.get("message") or "")
        key = (code, message)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)

    for item in new_errors:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "")
        message = str(item.get("message") or "")
        key = (code, message)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _resolve_reported_path(repo_root: Path, raw_path: Any) -> Path | None:
    value = str(raw_path or "").strip()
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    if not path.exists() or not path.is_file():
        return None
    return path.resolve()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_jsonl_path(raw_path: str | None, *, default_path: Path) -> Path:
    if not raw_path:
        return default_path
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def usage_record_schema_v1(*, mode: str, caller: str, exit_code: int, log_path: Path | None = None) -> dict[str, Any]:
    resolved_log_path = (log_path or USAGE_LOG_PATH).resolve()
    return {
        "schema_version": "usage_record_schema_v1",
        "record_type": "usage_event",
        "recorded_at": _utc_now_iso(),
        "mode": mode,
        "caller": caller,
        "legacy_entry": caller.startswith("legacy:"),
        "ok": exit_code == 0,
        "exit_code": exit_code,
        "log_path": str(resolved_log_path),
    }


def emit_usage_log(*, mode: str, caller: str, exit_code: int, log_path: Path | None = None) -> dict[str, Any]:
    resolved_log_path = (log_path or USAGE_LOG_PATH).resolve()
    record = usage_record_schema_v1(mode=mode, caller=caller, exit_code=exit_code, log_path=resolved_log_path)
    _append_jsonl(resolved_log_path, record)
    return record


def aggregate_usage_window(window_days: int, *, log_path: Path | None = None) -> dict[str, Any]:
    resolved_log_path = (log_path or USAGE_LOG_PATH).resolve()
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_log_path.touch(exist_ok=True)

    cutoff = _utc_now() - timedelta(days=window_days)
    events: list[dict[str, Any]] = []
    per_mode: dict[str, int] = {}
    legacy_calls = 0
    total_calls = 0

    for line in resolved_log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or payload.get("record_type") != "usage_event":
            continue
        recorded_at_raw = str(payload.get("recorded_at") or "").strip()
        if not recorded_at_raw:
            continue
        try:
            recorded_at = datetime.fromisoformat(recorded_at_raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if recorded_at < cutoff:
            continue
        total_calls += 1
        mode = str(payload.get("mode") or "unknown").strip()
        per_mode[mode] = per_mode.get(mode, 0) + 1
        if bool(payload.get("legacy_entry")):
            legacy_calls += 1
        events.append(payload)

    return {
        "ok": True,
        "window_days": window_days,
        "log_path": str(resolved_log_path),
        "summary": {
            "total_calls": total_calls,
            "legacy_calls": legacy_calls,
            "unified_entry_calls": total_calls - legacy_calls,
            "zero_call_window_met": legacy_calls == 0,
            "per_mode": dict(sorted(per_mode.items())),
        },
        "events": events,
    }


@dataclass(frozen=True)
class ModeSpec:
    mode: str
    description: str
    runner: Callable[[Sequence[str]], int] | None = None
    script: str | None = None
    available: bool = True
    planned_card: str | None = None


@dataclass(frozen=True)
class LegacyWrapperSpec:
    mode: str
    script: str
    build_args: Callable[[argparse.Namespace, dict[str, Any]], list[str]]


def _serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _resolve_output_path(output: str | None) -> Path | None:
    if not output or output == "-":
        return None
    output_path = Path(output).expanduser()
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    return output_path.resolve()


def _extract_output_target(passthrough_args: Sequence[str]) -> str | None:
    for index, arg in enumerate(passthrough_args):
        if arg == "--output":
            if index + 1 < len(passthrough_args):
                return passthrough_args[index + 1]
            return ""
        if arg.startswith("--output="):
            return arg.split("=", 1)[1]
    return None


def _emit_payload(payload: dict[str, Any], output_target: str | None) -> None:
    serialized = _serialize(payload)
    output_path = _resolve_output_path(output_target)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized + "\n", encoding="utf-8")
        print(f"written: {output_path}")
    print(serialized)


def _available_modes_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "modes": [
            {
                "mode": spec.mode,
                "description": spec.description,
                "available": spec.available,
                "planned_card": spec.planned_card,
            }
            for spec in MODE_REGISTRY.values()
        ],
    }


def _run_subprocess(script: str, passthrough_args: Sequence[str]) -> int:
    completed = subprocess.run(
        [sys.executable, str((ROOT / script).resolve()), *passthrough_args],
        cwd=ROOT,
        check=False,
    )
    return completed.returncode


def _run_clarify_plan(passthrough_args: Sequence[str]) -> int:
    import check_clarify_plan_alignment as module

    args = module._build_parser().parse_args(list(passthrough_args))
    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        result = module.run_alignment_check(
            repo_root=repo_root,
            task_split_dir_raw=args.task_split_dir,
            requirements_path_raw=args.requirements_path,
            implementation_path_raw=args.implementation_path,
            design_path_raw=args.design_path,
        )
    except module.AlignmentCheckError as exc:
        payload = {
            "ok": False,
            "error": {
                "code": "CLARIFY_PLAN_ALIGNMENT_FAILED",
                "message": str(exc),
            },
        }
        module._write_output(payload, args.output)
        return 2

    implementation_path = _resolve_reported_path(repo_root, result.get("implementation_plan"))
    if implementation_path is not None:
        db_contract = _validate_plan_db_evidence_contract(implementation_path)
        result["db_evidence_contract"] = db_contract
        if not db_contract.get("ok"):
            result["ok"] = False
            result["errors"] = _merge_error_entries(result.get("errors"), db_contract.get("errors") or [])
    else:
        result["db_evidence_contract"] = {
            "ok": False,
            "errors": [
                {
                    "code": "PLAN_DB_EVIDENCE_MISSING",
                    "message": "无法定位 implementation_plan，无法执行 DB 证据契约校验",
                    "details": {},
                }
            ],
        }
        result["ok"] = False
        result["errors"] = _merge_error_entries(result.get("errors"), result["db_evidence_contract"]["errors"])

    module._write_output(result, args.output)
    return 0 if result.get("ok") else 2


def _run_plan_vk_coverage(passthrough_args: Sequence[str]) -> int:
    import check_plan_vk_coverage as module

    args = module._build_parser().parse_args(list(passthrough_args))
    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        result = module.run_check(repo_root=repo_root, task_split_dir_raw=args.task_split_dir)
    except module.CoverageCheckError as exc:
        payload = {
            "ok": False,
            "error": {
                "code": "VKPLAN_CONSUMPTION_GAP",
                "message": str(exc),
            },
        }
        module._write_output(payload, args.output)
        return 2

    task_split_dir = _resolve_task_split_dir_arg(repo_root, args.task_split_dir)
    implementation_path = _resolve_reported_path(repo_root, result.get("implementation_plan"))
    if implementation_path is not None:
        db_contract = _validate_vkplan_db_evidence_contract(
            repo_root=repo_root,
            task_split_dir=task_split_dir,
            implementation_path=implementation_path,
        )
        result["db_evidence_contract"] = db_contract
        result["evidence_mapping_missing"] = db_contract.get("evidence_mapping_missing") or []
        result["db_chain_split_unclosed"] = db_contract.get("db_chain_split_unclosed") or []
        if not db_contract.get("ok"):
            result["ok"] = False
            result["errors"] = _merge_error_entries(result.get("errors"), db_contract.get("errors") or [])
    else:
        missing_impl_error = {
            "code": "VKPLAN_EVIDENCE_MAPPING_BROKEN",
            "message": "无法定位 implementation_plan，无法执行 vk 证据继承校验",
            "details": {"task_split_dir": str(task_split_dir)},
        }
        result["ok"] = False
        result["evidence_mapping_missing"] = result.get("evidence_mapping_missing") or []
        result["db_chain_split_unclosed"] = result.get("db_chain_split_unclosed") or []
        result["errors"] = _merge_error_entries(result.get("errors"), [missing_impl_error])

    module._write_output(result, args.output)
    return 0 if result.get("ok") else 2


def _run_gate_contract(passthrough_args: Sequence[str]) -> int:
    import check_gate_contract_consistency as module

    parser = argparse.ArgumentParser(description="检查 Gate 契约在三份文档中的一致性")
    parser.add_argument("--task-split-dir", required=True, help="任务拆解目录名或绝对路径")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument("--output", default="", help="可选输出 JSON 文件路径，'-' 表示打印 JSON")
    args = parser.parse_args(list(passthrough_args))

    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        task_split_dir = module._resolve_task_split_dir(repo_root, args.task_split_dir)
        result = module.run_check(task_split_dir, repo_root)
    except module.ContractParseError as exc:
        print(f"GATE_CONTRACT_CONSISTENCY: FAIL\n- {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"GATE_CONTRACT_CONSISTENCY: FAIL\n- unexpected error: {exc}", file=sys.stderr)
        return 1

    if result["ok"]:
        print("GATE_CONTRACT_CONSISTENCY: PASS")
        print(
            f"- task_key={result['task_key']} gate_ids="
            f"{result['contracts']['vk_cards']['gate_contract']['gate_ids']}"
        )
        module._write_output(args.output, result)
        return 0

    print("GATE_CONTRACT_CONSISTENCY: FAIL", file=sys.stderr)
    for issue in result["errors"]:
        print(f"- {issue}", file=sys.stderr)
    module._write_output(args.output, result)
    return 1


def _run_integration_gate(passthrough_args: Sequence[str]) -> int:
    from coder4 import check_integration_gate as module

    parser = argparse.ArgumentParser(description="IG01 集成门禁校验")
    parser.add_argument("--task-split-dir", required=True, help="任务拆解目录名或绝对路径")
    parser.add_argument("--baseline", default="master", help="主干基线分支（默认 master）")
    parser.add_argument("--state-dir", default=str(module.DEFAULT_STATE_DIR), help="状态目录（默认 .artifacts/states/task_splits/<task_split_dir>）")
    parser.add_argument("--repo-root", default=str(module.ROOT), help="仓库根目录")
    parser.add_argument("--output", default="", help="可选输出 JSON 文件路径，'-' 表示打印 JSON")
    args = parser.parse_args(list(passthrough_args))

    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        task_split_dir = module._resolve_task_split_dir(repo_root, args.task_split_dir)
        resolved_state_dir = _resolve_integration_state_dir(
            repo_root=repo_root,
            task_split_dir=task_split_dir,
            raw_state_dir=args.state_dir,
        )
        result = module.run_check(
            repo_root=repo_root,
            task_split_dir=task_split_dir,
            state_dir=resolved_state_dir,
            baseline=args.baseline,
        )
    except module.IntegrationGateError as exc:
        print(f"INTEGRATION_GATE: FAIL\n- {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"INTEGRATION_GATE: FAIL\n- unexpected error: {exc}", file=sys.stderr)
        return 1

    if result["ok"]:
        print("INTEGRATION_GATE: PASS")
        print(f"- baseline={args.baseline} merge_required_cards={len(result['merge_required_cards'])}")
        module._write_output(args.output, result)
        return 0

    print("INTEGRATION_GATE: FAIL", file=sys.stderr)
    for issue in result["errors"]:
        print(f"- {issue}", file=sys.stderr)
    module._write_output(args.output, result)
    return 1


def _detect_common_repo_root(repo_root: Path) -> Path:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        check=False,
        capture_output=True,
        text=True,
    )
    raw = str(completed.stdout or "").strip()
    if completed.returncode != 0 or not raw:
        return repo_root.resolve()

    common_dir = Path(raw).expanduser()
    if not common_dir.is_absolute():
        common_dir = (repo_root / common_dir).resolve()
    if common_dir.name == ".git":
        return common_dir.parent.resolve()
    return common_dir.resolve()


def _resolve_integration_state_dir(*, repo_root: Path, task_split_dir: Path, raw_state_dir: str) -> Path:
    state_dir = Path(str(raw_state_dir or ".state")).expanduser()
    if state_dir.is_absolute():
        return state_dir.resolve()

    locator = resolve_task_split_paths(repo_root, task_split_dir.name, must_exist=False)
    if str(raw_state_dir).strip() in {".state", "./.state", ""}:
        return locator.runtime_task_split_dir.resolve()

    return (repo_root / state_dir).resolve()


def _resolve_task_split_dir_arg(repo_root: Path, raw_value: str) -> Path:
    raw = str(raw_value or "").strip()
    if not raw:
        raise SystemExit("缺少 --task-split-dir")

    direct = Path(raw).expanduser()
    canonical_root = (repo_root / CANONICAL_TASK_SPLIT_BASE).resolve()
    legacy_root = (repo_root / LEGACY_TASK_SPLIT_BASE).resolve()
    candidates = [direct] if direct.is_absolute() else [(repo_root / raw), (canonical_root / raw), (legacy_root / raw)]
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.exists() and candidate.is_dir() and candidate in {canonical_root, legacy_root}:
            return canonical_root

    try:
        return resolve_task_split_paths(repo_root, raw, must_exist=True).canonical_task_split_dir
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc


def _load_task_source_files(task_split_dir: Path) -> dict[str, Any]:
    locator = resolve_task_split_paths(ROOT, task_split_dir.name, must_exist=False)
    cards_path = locator.vk_cards_file
    payload = json.loads(cards_path.read_text(encoding="utf-8"))
    source_files = payload.get("source_files") or {}
    if not isinstance(source_files, dict):
        return {}
    return source_files


def _build_clarify_plan_args(args: argparse.Namespace, source_files: dict[str, Any]) -> list[str]:
    requirements = str(source_files.get("requirements") or "").strip()
    implementation = str(source_files.get("implementation_plan") or "").strip()
    if not requirements or not implementation:
        raise SystemExit("legacy_wrapper_compat 缺少 source_files.requirements / implementation_plan")
    return [
        "--requirements-path",
        requirements,
        "--implementation-path",
        implementation,
        "--output",
        "-",
    ]


def _build_task_split_args(args: argparse.Namespace, source_files: dict[str, Any]) -> list[str]:
    del source_files
    return ["--task-split-dir", args.task_split_dir, "--output", "-"]


def _build_integration_args(args: argparse.Namespace, source_files: dict[str, Any]) -> list[str]:
    del source_files
    return [
        "--task-split-dir",
        args.task_split_dir,
        "--baseline",
        args.baseline,
        "--output",
        "-",
    ]


LEGACY_WRAPPERS: tuple[LegacyWrapperSpec, ...] = (
    LegacyWrapperSpec(
        mode="clarify_plan",
        script="scripts/check_clarify_plan_alignment.py",
        build_args=_build_clarify_plan_args,
    ),
    LegacyWrapperSpec(
        mode="plan_vk_coverage",
        script="scripts/check_plan_vk_coverage.py",
        build_args=_build_task_split_args,
    ),
    LegacyWrapperSpec(
        mode="gate_contract",
        script="scripts/check_gate_contract_consistency.py",
        build_args=_build_task_split_args,
    ),
    LegacyWrapperSpec(
        mode="integration_gate",
        script="scripts/check_integration_gate.py",
        build_args=_build_integration_args,
    ),
)


def _strip_deprecation(stderr: str) -> str:
    lines = []
    for line in str(stderr or "").splitlines():
        if line.startswith("[DEPRECATED]"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _run_legacy_wrapper_compat(passthrough_args: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="旧脚本 wrapper 兼容性检查")
    parser.add_argument("--task-split-dir", required=True, help="任务拆解目录名或绝对路径")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument("--baseline", default="master", help="集成门禁基线")
    parser.add_argument("--output", default="-", help="输出 JSON 文件路径，默认 stdout")
    args = parser.parse_args(list(passthrough_args))

    repo_root = Path(args.repo_root).expanduser().resolve()
    task_split_dir = _resolve_task_split_dir_arg(repo_root, args.task_split_dir)
    source_files = _load_task_source_files(task_split_dir)

    checks: list[dict[str, Any]] = []
    all_ok = True
    for spec in LEGACY_WRAPPERS:
        script_path = (repo_root / spec.script).resolve()
        script_text = script_path.read_text(encoding="utf-8")
        sample_args = spec.build_args(args, source_files)
        direct = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_workflow_contract.py"), "--mode", spec.mode, *sample_args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        legacy = subprocess.run(
            [sys.executable, str(script_path), *sample_args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        marker_ok = "def wrapper_notice" in script_text and f'"{spec.mode}"' in script_text and "check_workflow_contract.py" in script_text
        stdout_match = legacy.stdout == direct.stdout
        stderr_match = _strip_deprecation(legacy.stderr) == direct.stderr.strip()
        returncode_match = legacy.returncode == direct.returncode
        deprecation_present = "[DEPRECATED]" in legacy.stderr
        item_ok = marker_ok and stdout_match and stderr_match and returncode_match and deprecation_present
        all_ok = all_ok and item_ok
        checks.append(
            {
                "mode": spec.mode,
                "legacy_script": spec.script,
                "sample_args": sample_args,
                "wrapper_markers_present": marker_ok,
                "deprecation_present": deprecation_present,
                "stdout_match": stdout_match,
                "stderr_match": stderr_match,
                "returncode_match": returncode_match,
                "legacy_returncode": legacy.returncode,
                "direct_returncode": direct.returncode,
            }
        )

    payload = {
        "ok": all_ok,
        "task_split_dir": str(task_split_dir),
        "checks": checks,
    }
    _emit_payload(payload, args.output)
    return 0 if all_ok else 1


def _task_lifecycle(task_state_dir: Path) -> str:
    state_file = task_state_dir / "task-runner-state.json"
    if not state_file.exists():
        return "unknown"
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "unknown"
    statuses = list((payload.get("card_status_map") or payload.get("card_status") or {}).values())
    normalized = {str(item or "").strip().lower().replace("-", "_") for item in statuses}
    if normalized and normalized.issubset({"done", "skipped"}):
        return "done"
    return "active"


def should_archive_entry(path: Path, *, lifecycle: str, ttl_days: int, now: datetime) -> tuple[bool, str]:
    if path.name in TRUTH_SOURCE_FILENAMES or path.name.startswith("active-session-"):
        return False, "truth_source"
    if lifecycle not in {"done", "archived"}:
        return False, f"lifecycle_{lifecycle}"
    last_modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_days = (now - last_modified).days
    if age_days < ttl_days:
        return False, f"ttl_not_expired:{age_days}"
    return True, "ttl_expired"


def archive_audit_report(task_split_root: Path, ttl_days: int) -> dict[str, Any]:
    now = _utc_now()
    task_dirs = [item for item in task_split_root.iterdir() if item.is_dir() and not item.name.startswith("_")]
    reports: list[dict[str, Any]] = []
    candidates = 0
    protected = 0
    for task_dir in sorted(task_dirs):
        state_root = (ROOT / ".artifacts" / "states" / "task_splits" / task_dir.name)
        if not state_root.exists():
            continue
        task_entries: list[dict[str, Any]] = []
        for task_state_dir in sorted([item for item in state_root.iterdir() if item.is_dir()]):
            lifecycle = _task_lifecycle(task_state_dir)
            for file_path in sorted([item for item in task_state_dir.rglob("*") if item.is_file()]):
                archive_ok, reason = should_archive_entry(file_path, lifecycle=lifecycle, ttl_days=ttl_days, now=now)
                last_modified = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                item = {
                    "path": str(file_path.relative_to(ROOT)),
                    "task_split_dir": task_dir.name,
                    "task_key": task_state_dir.name,
                    "lifecycle": lifecycle,
                    "last_modified": last_modified.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "decision": "archive_candidate" if archive_ok else "protected",
                    "reason": reason,
                }
                task_entries.append(item)
                if archive_ok:
                    candidates += 1
                else:
                    protected += 1
        if task_entries:
            reports.append({"task_split_dir": task_dir.name, "entries": task_entries})

    return {
        "ok": True,
        "ttl_days": ttl_days,
        "task_split_root": str(task_split_root),
        "summary": {
            "archive_candidates": candidates,
            "protected_entries": protected,
            "active_truth_source_harmed": 0,
        },
        "tasks": reports,
    }


def ttl_archive_runner(task_split_root: Path, ttl_days: int) -> dict[str, Any]:
    return archive_audit_report(task_split_root, ttl_days)


def _workflow_usage_log_path(repo_root: Path) -> Path:
    return (repo_root / "logs" / "workflow-gate-usage.jsonl").resolve()


def _scan_temporal_gate_text(path: Path, text: str) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        candidate = str(line or "").strip()
        if not candidate:
            continue
        for label, pattern in TEMPORAL_GATE_PATTERNS:
            if not pattern.search(candidate):
                continue
            errors.append({
                "code": "TEMPORAL_GATE_BLOCKER_DETECTED",
                "rule": label,
                "file": str(path),
                "line": line_no,
                "snippet": candidate,
            })
            break
    return errors


def _resolve_optional_repo_file(repo_root: Path, raw_value: str | None) -> Path | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    return _resolve_repo_relative(raw, repo_root=repo_root)


def check_temporal_gate_contract(task_split_dir: Path | None, repo_root: Path, implementation_path: Path | None = None) -> dict[str, Any]:
    files_to_scan: list[Path] = []
    if implementation_path is not None:
        files_to_scan.append(implementation_path.resolve())

    if task_split_dir is not None:
        task_split_dir = task_split_dir.resolve()
        locator = resolve_task_split_paths(repo_root, task_split_dir.name, must_exist=False)
        files_to_scan.append(locator.parallel_plan_file.resolve())
        files_to_scan.append(locator.vk_cards_file.resolve())
        source_files = _load_task_source_files(task_split_dir)
        impl_candidate = _resolve_optional_repo_file(repo_root, source_files.get("implementation_plan"))
        if impl_candidate is not None:
            files_to_scan.append(impl_candidate)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for file_path in files_to_scan:
        if file_path in seen or not file_path.exists() or not file_path.is_file():
            continue
        seen.add(file_path)
        deduped.append(file_path)

    errors: list[dict[str, Any]] = []
    for file_path in deduped:
        errors.extend(_scan_temporal_gate_text(file_path, file_path.read_text(encoding="utf-8")))

    return {
        "ok": len(errors) == 0,
        "files": [str(item) for item in deduped],
        "errors": errors,
    }


def _run_planning_temporal_gate(passthrough_args: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="规划期时间窗阻断检查")
    parser.add_argument("--task-split-dir", help="任务拆解目录名或绝对路径")
    parser.add_argument("--implementation-path", help="implementation_plan 路径")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument("--output", default="-", help="输出路径；默认 stdout")
    args = parser.parse_args(list(passthrough_args))

    repo_root = Path(args.repo_root).expanduser().resolve()
    task_split_dir = _resolve_task_split_dir_arg(repo_root, args.task_split_dir) if args.task_split_dir else None
    implementation_path = _resolve_optional_repo_file(repo_root, args.implementation_path)

    if task_split_dir is None and implementation_path is None:
        payload = {
            "ok": False,
            "error": {
                "code": "PLANNING_TEMPORAL_GATE_INPUT_REQUIRED",
                "message": "缺少 --task-split-dir 或 --implementation-path",
            },
        }
        _emit_payload(payload, args.output)
        return 2

    payload = check_temporal_gate_contract(task_split_dir, repo_root, implementation_path)
    if not payload.get("ok"):
        payload["error"] = {
            "code": "VKPLAN_TEMPORAL_BLOCKER_FORBIDDEN" if task_split_dir is not None else "PLAN_TEMPORAL_GATE_FORBIDDEN",
            "message": "检测到依赖自然时间成熟的阻断条件，请改为观测证据或人工放行说明",
        }
    _emit_payload(payload, args.output)
    return 0 if payload.get("ok") else 2


def _resolve_repo_relative(path_str: str, *, repo_root: Path = ROOT) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _wrapper_shell_report(*, repo_root: Path) -> dict[str, Any]:
    wrapper_targets = [
        ("scripts/check_clarify_plan_alignment.py", "clarify_plan"),
        ("scripts/check_plan_vk_coverage.py", "plan_vk_coverage"),
        ("scripts/check_gate_contract_consistency.py", "gate_contract"),
        ("scripts/check_integration_gate.py", "integration_gate"),
    ]
    entries = []
    for rel_path, mode in wrapper_targets:
        path = _resolve_repo_relative(rel_path, repo_root=repo_root)
        text = path.read_text(encoding="utf-8")
        line_count = len(text.splitlines())
        has_wrapper = "def wrapper_notice" in text and 'check_workflow_contract.py' in text and f'"{mode}"' in text
        thin_shell = line_count <= 80
        entries.append({
            "path": rel_path,
            "mode": mode,
            "line_count": line_count,
            "has_wrapper_notice": has_wrapper,
            "thin_shell": thin_shell,
            "ok": has_wrapper and thin_shell,
        })
    return {
        "ok": all(item["ok"] for item in entries),
        "entries": entries,
    }


def retirement_guard(*, wrapper_report: dict[str, Any], usage_report: dict[str, Any], ttl_report: dict[str, Any]) -> dict[str, Any]:

    blockers: list[dict[str, Any]] = []
    if not wrapper_report.get("ok"):
        blockers.append({
            "code": "LEGACY_WRAPPER_NOT_THIN",
            "files": [item["path"] for item in wrapper_report.get("entries", []) if not item.get("ok")],
        })

    legacy_calls = int(((usage_report.get("summary") or {}).get("legacy_calls") or 0))
    if legacy_calls > 0:
        blockers.append({
            "code": "LEGACY_USAGE_DETECTED",
            "legacy_calls": legacy_calls,
        })

    if int(((ttl_report.get("summary") or {}).get("active_truth_source_harmed") or 0)) != 0:
        blockers.append({
            "code": "TTL_GUARD_VIOLATION",
            "summary": ttl_report.get("summary"),
        })

    return {
        "ok": len(blockers) == 0,
        "blockers": blockers,
    }


def _run_full_gate(passthrough_args: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="C07 pre-merge 收口门禁验收")
    parser.add_argument("--task-split-dir", required=True, help="任务拆解目录名或绝对路径")
    parser.add_argument("--baseline", default="master", help="主干基线")
    parser.add_argument("--window-days", type=int, default=7, help="usage 统计窗口（仅报表，不阻断放行）")
    parser.add_argument("--ttl-days", type=int, default=14, help="TTL 审计窗口")
    parser.add_argument("--include-integration", action="store_true", help="显式纳入 post-merge integration_gate 阻断")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument("--output", default="-", help="输出路径；默认 stdout")
    args = parser.parse_args(list(passthrough_args))

    repo_root = Path(args.repo_root).expanduser().resolve()
    task_split_dir = _resolve_task_split_dir_arg(repo_root, args.task_split_dir)
    source_files = _load_task_source_files(task_split_dir)

    import check_clarify_plan_alignment as clarify_module
    import check_plan_vk_coverage as vk_module
    import check_gate_contract_consistency as gate_module

    checked_at = _utc_now()
    requirements = str(source_files.get("requirements") or "").strip()
    implementation = str(source_files.get("implementation_plan") or "").strip()
    clarify_ok = False
    clarify_payload: dict[str, Any]
    try:
        clarify_payload = clarify_module.run_alignment_check(
            repo_root=repo_root,
            task_split_dir_raw=None,
            requirements_path_raw=requirements,
            implementation_path_raw=implementation,
            design_path_raw=None,
        )
        clarify_ok = bool(clarify_payload.get("ok"))
    except Exception as exc:  # noqa: BLE001
        clarify_payload = {"ok": False, "error": str(exc)}

    try:
        vk_payload = vk_module.run_check(repo_root=repo_root, task_split_dir_raw=str(task_split_dir))
        vk_ok = bool(vk_payload.get("ok"))
    except Exception as exc:  # noqa: BLE001
        vk_payload = {"ok": False, "error": str(exc)}
        vk_ok = False

    try:
        gate_payload = gate_module.run_check(task_split_dir, repo_root)
        gate_ok = bool(gate_payload.get("ok"))
    except Exception as exc:  # noqa: BLE001
        gate_payload = {"ok": False, "error": str(exc)}
        gate_ok = False

    if args.include_integration:
        from coder4 import check_integration_gate as integration_module

        try:
            integration_payload = integration_module.run_check(
                repo_root=repo_root,
                task_split_dir=task_split_dir,
                state_dir=_resolve_integration_state_dir(
                    repo_root=repo_root,
                    task_split_dir=task_split_dir,
                    raw_state_dir=".state",
                ),
                baseline=args.baseline,
            )
            integration_ok = bool(integration_payload.get("ok"))
        except Exception as exc:  # noqa: BLE001
            integration_payload = {"ok": False, "error": str(exc)}
            integration_ok = False
    else:
        integration_payload = {
            "ok": True,
            "skipped": True,
            "reason": "pre_merge_full_gate",
            "message": "integration_gate 属于 post-merge 主干可见性校验；默认不纳入 C07 pre-merge 阻断",
        }
        integration_ok = True

    usage_payload = aggregate_usage_window(args.window_days, log_path=_workflow_usage_log_path(repo_root))
    ttl_payload = ttl_archive_runner(task_split_dir.parent, args.ttl_days)
    wrapper_payload = _wrapper_shell_report(repo_root=repo_root)
    guard_payload = retirement_guard(
        wrapper_report=wrapper_payload,
        usage_report=usage_payload,
        ttl_report=ttl_payload,
    )

    payload = {
        "ok": all([clarify_ok, vk_ok, gate_ok, integration_ok, usage_payload.get("ok"), ttl_payload.get("ok"), guard_payload.get("ok")]),
        "checked_at": checked_at.replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
        "task_split_dir": str(task_split_dir),
        "baseline": args.baseline,
        "checks": {
            "clarify_plan": clarify_payload,
            "plan_vk_coverage": vk_payload,
            "gate_contract": gate_payload,
            "integration_gate": integration_payload,
            "usage_report": usage_payload,
            "ttl_audit": ttl_payload,
            "wrapper_shell": wrapper_payload,
        },
        "retirement_guard": guard_payload,
    }
    _emit_payload(payload, args.output)
    return 0 if payload.get("ok") else 1


def _run_ttl_audit(passthrough_args: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="TTL 归档审计")
    parser.add_argument("--task-split-dir", required=True, help="任务拆解根目录或单个任务拆解目录")
    parser.add_argument("--ttl-days", type=int, default=14, help="TTL 天数")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument("--output", default="-", help="输出路径；默认 stdout")
    args = parser.parse_args(list(passthrough_args))

    repo_root = Path(args.repo_root).expanduser().resolve()
    task_split_root = _resolve_task_split_dir_arg(repo_root, args.task_split_dir)
    payload = ttl_archive_runner(task_split_root, args.ttl_days)
    _emit_payload(payload, args.output)
    return 0 if payload.get("ok") else 1


def _run_usage_report(passthrough_args: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="旧入口调用观测报告")
    parser.add_argument("--window-days", type=int, default=7, help="统计窗口（仅报表使用，不作为退役阻断）")
    parser.add_argument("--log-path", default=str(USAGE_LOG_PATH.relative_to(ROOT)), help="usage 运行态 jsonl 路径")
    parser.add_argument("--report-output", default="-", help="聚合报告输出路径；默认 stdout")
    args = parser.parse_args(list(passthrough_args))

    log_path = _resolve_jsonl_path(args.log_path, default_path=USAGE_LOG_PATH)
    payload = aggregate_usage_window(args.window_days, log_path=log_path)
    _emit_payload(payload, args.report_output)
    return 0


MODE_REGISTRY: dict[str, ModeSpec] = {
    "clarify_plan": ModeSpec(
        mode="clarify_plan",
        description="校验 requirements / design / implementation_plan 承接完整性",
        runner=_run_clarify_plan,
    ),
    "clarify_consistency": ModeSpec(
        mode="clarify_consistency",
        description="校验 clarify 命令、模板与镜像一致性",
        script="scripts/check_clarify_contract_consistency.py",
    ),
    "plan_vk_coverage": ModeSpec(
        mode="plan_vk_coverage",
        description="校验 /jjk-vkplan 是否完整消费 /jjk-plan 产物",
        runner=_run_plan_vk_coverage,
    ),
    "planning_temporal_gate": ModeSpec(
        mode="planning_temporal_gate",
        description="禁止把时间窗口成熟条件建模为阻断型计划门禁",
        runner=_run_planning_temporal_gate,
    ),
    "gate_contract": ModeSpec(
        mode="gate_contract",
        description="检查 Gate 契约在三份文档中的一致性",
        runner=_run_gate_contract,
    ),
    "integration_gate": ModeSpec(
        mode="integration_gate",
        description="IG01 集成门禁校验：实现卡必须已合并且主干可见",
        runner=_run_integration_gate,
    ),
    "legacy_wrapper_compat": ModeSpec(
        mode="legacy_wrapper_compat",
        description="旧脚本 wrapper 兼容性检查",
        runner=_run_legacy_wrapper_compat,
    ),
    "usage-report": ModeSpec(
        mode="usage-report",
        description="旧入口调用观测报告",
        runner=_run_usage_report,
    ),
    "ttl-audit": ModeSpec(
        mode="ttl-audit",
        description="过程文件 TTL 审计",
        runner=_run_ttl_audit,
    ),
    "full-gate": ModeSpec(
        mode="full-gate",
        description="C07 pre-merge 收口门禁验收",
        runner=_run_full_gate,
    ),
}


def parse_args(argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description="统一 workflow contract 门禁入口")
    parser.add_argument("--mode", help="执行模式")
    parser.add_argument("--list-modes", action="store_true", help="列出当前支持的模式")
    return parser.parse_known_args(argv)


def run_mode(mode: str, passthrough_args: Sequence[str]) -> int:
    output_target = _extract_output_target(passthrough_args)
    normalized_mode = str(mode or "").strip()
    spec = MODE_REGISTRY.get(normalized_mode)
    if spec is None:
        _emit_payload(
            {
                "ok": False,
                "mode": normalized_mode,
                "error": {
                    "code": "WORKFLOW_CONTRACT_MODE_UNSUPPORTED",
                    "message": f"不支持的 mode: {normalized_mode}",
                },
                "supported_modes": sorted(MODE_REGISTRY.keys()),
            },
            output_target,
        )
        return 2

    if spec.runner is not None:
        exit_code = spec.runner(passthrough_args)
    elif spec.available and spec.script:
        exit_code = _run_subprocess(spec.script, passthrough_args)
    else:
        _emit_payload(
            {
                "ok": False,
                "mode": normalized_mode,
                "error": {
                    "code": "WORKFLOW_CONTRACT_MODE_NOT_READY",
                    "message": f"mode={normalized_mode} 计划在 {spec.planned_card or '后续卡片'} 实现",
                },
            },
            output_target,
        )
        return 3

    if normalized_mode in USAGE_OBSERVED_MODES and os.environ.get("WORKFLOW_GATE_DISABLE_USAGE_LOG") != "1":
        emit_usage_log(
            mode=normalized_mode,
            caller=os.environ.get("WORKFLOW_GATE_CALLER", "unified_entry"),
            exit_code=exit_code,
        )
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    args, passthrough_args = parse_args(argv)
    if args.list_modes:
        _emit_payload(_available_modes_payload(), _extract_output_target(passthrough_args))
        return 0

    if not args.mode:
        _emit_payload(
            {
                "ok": False,
                "error": {
                    "code": "WORKFLOW_CONTRACT_MODE_REQUIRED",
                    "message": "缺少 --mode",
                },
                "supported_modes": sorted(MODE_REGISTRY.keys()),
            },
            _extract_output_target(passthrough_args),
        )
        return 2

    return run_mode(args.mode, passthrough_args)


if __name__ == "__main__":
    raise SystemExit(main())
