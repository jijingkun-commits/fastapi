#!/usr/bin/env python3
"""校验 /jjk-vkplan 是否完整消费 /jjk-plan 产物。"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from check_clarify_plan_alignment import AlignmentCheckError, run_alignment_check


ROOT = Path(__file__).resolve().parents[1]
TASK_SPLIT_BASE = Path("docs/内部参考/任务拆解")
REQUIREMENTS_BASE = Path("docs/内部参考/迭代需求")
YAML_BLOCK_PATTERN = re.compile(r"```yaml\s*(.*?)```", flags=re.DOTALL | re.IGNORECASE)
REQUIRED_EXECUTION_FIELDS = (
    "delivery_mode",
    "execution_unit",
    "commit_policy",
    "stop_boundary",
    "stop_on_blocked",
)


class CoverageCheckError(RuntimeError):
    """覆盖校验失败。"""


def _normalize_id(raw: Any) -> str:
    return str(raw or "").strip().strip("`'\"").upper()


def _normalize_cmd(raw: Any) -> str:
    return " ".join(str(raw or "").strip().split())


def _normalize_scalar(raw: Any) -> str:
    if isinstance(raw, bool):
        return "true" if raw else "false"
    return str(raw or "").strip().lower()


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
    return [_normalize_id(item) for item in items if _normalize_id(item)]


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


def _resolve_task_split_dir(repo_root: Path, raw_value: str) -> Path:
    raw = str(raw_value or "").strip()
    if not raw:
        raise CoverageCheckError("缺少 --task-split-dir")

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
    raise CoverageCheckError(f"无法定位 task_split_dir: {raw}; candidates={joined}")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CoverageCheckError(f"JSON 根节点不是对象: {path}")
    return payload


def _extract_yaml_blocks(markdown_path: Path) -> list[str]:
    content = markdown_path.read_text(encoding="utf-8")
    blocks = YAML_BLOCK_PATTERN.findall(content)
    if not blocks:
        raise CoverageCheckError(f"{markdown_path} 未找到 ```yaml``` 代码块")
    return blocks


def _find_block(blocks: list[str], marker: str, source: Path) -> str:
    for block in blocks:
        if marker in block:
            return block
    raise CoverageCheckError(f"{source} 未找到包含 `{marker}` 的 yaml 代码块")


def _resolve_implementation_plan(
    *, repo_root: Path, task_split_dir: Path, vk_cards: dict[str, Any]
) -> Path:
    source_files = vk_cards.get("source_files")
    if isinstance(source_files, dict):
        impl_path_raw = str(source_files.get("implementation_plan") or "").strip()
        if impl_path_raw:
            impl_path = Path(impl_path_raw)
            if not impl_path.is_absolute():
                impl_path = repo_root / impl_path
            if impl_path.exists() and impl_path.is_file():
                return impl_path.resolve()

    split_name = task_split_dir.name
    inferred_topic = split_name
    if re.match(r"^\d{4}-\d{2}-\d{2}_", split_name):
        inferred_topic = split_name.split("_", 1)[1]
    inferred_path = repo_root / REQUIREMENTS_BASE / f"{inferred_topic}_implementation_plan.md"
    if inferred_path.exists() and inferred_path.is_file():
        return inferred_path.resolve()

    raise CoverageCheckError(
        "无法定位 implementation_plan："
        f"source_files.implementation_plan={source_files if isinstance(source_files, dict) else None}"
    )


def _parse_implementation_tasks(block: str) -> list[dict[str, Any]]:
    lines = block.splitlines()
    try:
        start_idx = next(
            idx for idx, line in enumerate(lines) if line.strip().startswith("implementation_tasks:")
        )
    except StopIteration as exc:
        raise CoverageCheckError("implementation_tasks 解析失败：缺少 implementation_tasks") from exc

    tasks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_acceptance = False
    in_feature_list = False

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
                tasks.append(current)
            current = {
                "task_id": "",
                "feature_ids": set(),
                "pr_id": "",
                "acceptance_cmds": set(),
            }
            in_acceptance = False
            in_feature_list = False

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
            in_acceptance = False
            in_feature_list = False

            if key == "feature_id":
                feature_id = _normalize_id(value)
                if feature_id:
                    current["feature_ids"].add(feature_id)
            elif key == "feature_ids":
                for feature_id in _parse_inline_list(value):
                    current["feature_ids"].add(feature_id)
                in_feature_list = value == ""
            elif key == "pr_id":
                current["pr_id"] = _normalize_id(value)
            elif key == "acceptance_cmds":
                for cmd in _parse_inline_list(value, as_cmd=True):
                    current["acceptance_cmds"].add(cmd)
                in_acceptance = True
            idx += 1
            continue

        if in_feature_list and indent >= 6 and stripped.startswith("- "):
            feature_id = _normalize_id(stripped[2:])
            if feature_id:
                current["feature_ids"].add(feature_id)
            idx += 1
            continue

        if in_acceptance and indent >= 6 and stripped.startswith("- "):
            cmd = _normalize_cmd(stripped[2:])
            if cmd:
                current["acceptance_cmds"].add(cmd)
            idx += 1
            continue

        idx += 1

    if current:
        tasks.append(current)

    return tasks


def _parse_planning_contract(block: str) -> dict[str, Any]:
    lines = block.splitlines()
    try:
        start_idx = next(idx for idx, line in enumerate(lines) if line.strip().startswith("planning_contract:"))
    except StopIteration as exc:
        raise CoverageCheckError("planning_contract 解析失败：缺少 planning_contract") from exc

    cards: list[dict[str, Any]] = []
    task_to_pr_mapping: list[dict[str, Any]] = []

    section = ""
    current_card: dict[str, Any] | None = None
    current_map: dict[str, Any] | None = None
    in_card_features = False
    in_card_checks = False
    in_map_acceptance = False

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

        if indent == 2 and stripped.startswith("cards:"):
            if current_map:
                task_to_pr_mapping.append(current_map)
                current_map = None
            section = "cards"
            idx += 1
            continue

        if indent == 2 and stripped.startswith("task_to_pr_mapping:"):
            if current_card:
                cards.append(current_card)
                current_card = None
            section = "mapping"
            idx += 1
            continue

        if section == "cards":
            if indent == 4 and stripped.startswith("- "):
                if current_card:
                    cards.append(current_card)
                current_card = {
                    "card_id": "",
                    "feature_ids": set(),
                    "acceptance_checks": set(),
                }
                in_card_features = False
                in_card_checks = False

                key, value = _split_key_value(stripped[2:])
                if key == "card_id":
                    current_card["card_id"] = _normalize_id(value)
                idx += 1
                continue

            if current_card is None:
                idx += 1
                continue

            if indent == 6:
                key, value = _split_key_value(stripped)
                in_card_features = False
                in_card_checks = False

                if key == "card_id":
                    current_card["card_id"] = _normalize_id(value)
                elif key == "feature_ids":
                    for feature_id in _parse_inline_list(value):
                        current_card["feature_ids"].add(feature_id)
                    in_card_features = value == ""
                elif key == "acceptance_checks":
                    for cmd in _parse_inline_list(value, as_cmd=True):
                        current_card["acceptance_checks"].add(cmd)
                    in_card_checks = True
                idx += 1
                continue

            if in_card_features and indent >= 8 and stripped.startswith("- "):
                feature_id = _normalize_id(stripped[2:])
                if feature_id:
                    current_card["feature_ids"].add(feature_id)
                idx += 1
                continue

            if in_card_checks and indent >= 8 and stripped.startswith("- "):
                cmd = _normalize_cmd(stripped[2:])
                if cmd:
                    current_card["acceptance_checks"].add(cmd)
                idx += 1
                continue

            idx += 1
            continue

        if section == "mapping":
            if indent == 4 and stripped.startswith("- "):
                if current_map:
                    task_to_pr_mapping.append(current_map)
                current_map = {
                    "task_id": "",
                    "pr_id": "",
                    "acceptance_cmds": set(),
                }
                in_map_acceptance = False

                key, value = _split_key_value(stripped[2:])
                if key == "task_id":
                    current_map["task_id"] = _normalize_id(value)
                idx += 1
                continue

            if current_map is None:
                idx += 1
                continue

            if indent == 6:
                key, value = _split_key_value(stripped)
                in_map_acceptance = False
                if key == "task_id":
                    current_map["task_id"] = _normalize_id(value)
                elif key == "pr_id":
                    current_map["pr_id"] = _normalize_id(value)
                elif key == "acceptance_cmds":
                    for cmd in _parse_inline_list(value, as_cmd=True):
                        current_map["acceptance_cmds"].add(cmd)
                    in_map_acceptance = True
                idx += 1
                continue

            if in_map_acceptance and indent >= 8 and stripped.startswith("- "):
                cmd = _normalize_cmd(stripped[2:])
                if cmd:
                    current_map["acceptance_cmds"].add(cmd)
                idx += 1
                continue

            idx += 1
            continue

        idx += 1

    if current_card:
        cards.append(current_card)
    if current_map:
        task_to_pr_mapping.append(current_map)

    return {
        "cards": cards,
        "task_to_pr_mapping": task_to_pr_mapping,
    }


def _parse_execution_contract(block: str) -> dict[str, Any]:
    lines = block.splitlines()
    try:
        start_idx = next(idx for idx, line in enumerate(lines) if line.strip().startswith("execution_contract:"))
    except StopIteration as exc:
        raise CoverageCheckError("execution_contract 解析失败：缺少 execution_contract") from exc

    execution_contract: dict[str, Any] = {}
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
            if key:
                execution_contract[key] = _parse_scalar_literal(value)
        idx += 1

    return execution_contract


def _collect_contracts(implementation_path: Path) -> dict[str, Any]:
    blocks = _extract_yaml_blocks(implementation_path)
    planning_block = _find_block(blocks, "planning_contract:", implementation_path)
    tasks_block = _find_block(blocks, "implementation_tasks:", implementation_path)
    execution_block = _find_block(blocks, "execution_contract:", implementation_path)

    planning_contract = _parse_planning_contract(planning_block)
    implementation_tasks = _parse_implementation_tasks(tasks_block)
    execution_contract = _parse_execution_contract(execution_block)

    if not planning_contract.get("task_to_pr_mapping"):
        raise CoverageCheckError(f"{implementation_path} planning_contract 缺少 task_to_pr_mapping")
    if not planning_contract.get("cards"):
        raise CoverageCheckError(f"{implementation_path} planning_contract 缺少 cards")
    if not implementation_tasks:
        raise CoverageCheckError(f"{implementation_path} implementation_tasks 为空")

    return {
        "planning_contract": planning_contract,
        "implementation_tasks": implementation_tasks,
        "execution_contract": execution_contract,
        "warnings": [],
    }


def _collect_implementation_tasks(raw_tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    task_map: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()

    for item in raw_tasks:
        task_id = _normalize_id(item.get("task_id"))
        if not task_id:
            continue
        if task_id in task_map:
            duplicates.add(task_id)

        features = {
            _normalize_id(feature)
            for feature in (_as_list(item.get("feature_ids")) + _as_list(item.get("feature_id")))
            if _normalize_id(feature)
        }
        acceptance_cmds = {
            _normalize_cmd(cmd) for cmd in _as_list(item.get("acceptance_cmds")) if _normalize_cmd(cmd)
        }

        task_map[task_id] = {
            "task_id": task_id,
            "pr_id": _normalize_id(item.get("pr_id")),
            "feature_ids": features,
            "acceptance_cmds": acceptance_cmds,
        }

    if duplicates:
        raise CoverageCheckError(f"implementation_tasks 存在重复 task_id: {sorted(duplicates)}")

    return task_map


def _collect_task_to_pr_mapping(planning_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()

    for item in _as_list(planning_contract.get("task_to_pr_mapping")):
        if not isinstance(item, dict):
            continue
        task_id = _normalize_id(item.get("task_id"))
        if not task_id:
            continue
        if task_id in mapping:
            duplicates.add(task_id)

        mapping[task_id] = {
            "task_id": task_id,
            "pr_id": _normalize_id(item.get("pr_id")),
            "acceptance_cmds": {
                _normalize_cmd(cmd)
                for cmd in _as_list(item.get("acceptance_cmds"))
                if _normalize_cmd(cmd)
            },
        }

    if duplicates:
        raise CoverageCheckError(f"task_to_pr_mapping 存在重复 task_id: {sorted(duplicates)}")

    return mapping


def _collect_planning_cards(planning_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()

    for item in _as_list(planning_contract.get("cards")):
        if not isinstance(item, dict):
            continue
        card_id = _normalize_id(item.get("card_id"))
        if not card_id:
            continue
        if card_id in cards:
            duplicates.add(card_id)

        feature_ids = {
            _normalize_id(feature)
            for feature in _as_list(item.get("feature_ids"))
            if _normalize_id(feature)
        }
        acceptance_checks = {
            _normalize_cmd(cmd)
            for cmd in _as_list(item.get("acceptance_checks"))
            if _normalize_cmd(cmd)
        }
        cards[card_id] = {
            "card_id": card_id,
            "feature_ids": feature_ids,
            "acceptance_checks": acceptance_checks,
        }

    if duplicates:
        raise CoverageCheckError(f"planning_contract.cards 存在重复 card_id: {sorted(duplicates)}")

    return cards


def _collect_vk_cards(vk_cards: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()

    for item in _as_list(vk_cards.get("cards")):
        if not isinstance(item, dict):
            continue
        card_id = _normalize_id(item.get("card_id"))
        if not card_id:
            continue
        if card_id in cards:
            duplicates.add(card_id)

        task_ids_field = item.get("task_ids")
        task_ids_raw = _as_list(task_ids_field)
        task_ids_present = "task_ids" in item
        task_ids = {_normalize_id(task) for task in task_ids_raw if _normalize_id(task)}
        cards[card_id] = {
            "card_id": card_id,
            "feature_ids": {
                _normalize_id(feature)
                for feature in _as_list(item.get("feature_ids"))
                if _normalize_id(feature)
            },
            "task_ids": task_ids,
            "task_ids_present": task_ids_present,
            "pr_id": _normalize_id(item.get("pr_id")),
            "acceptance_checks": {
                _normalize_cmd(cmd)
                for cmd in _as_list(item.get("acceptance_checks"))
                if _normalize_cmd(cmd)
            },
        }

    if duplicates:
        raise CoverageCheckError(f"vk_cards.cards 存在重复 card_id: {sorted(duplicates)}")

    return cards


def _check_coverage(*, contracts: dict[str, Any], vk_cards_payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []

    def add_error(code: str, message: str, details: Any) -> None:
        errors.append({"code": code, "message": message, "details": details})

    planning_contract = contracts["planning_contract"]
    implementation_tasks_raw = contracts["implementation_tasks"]
    execution_contract = contracts["execution_contract"]

    if not isinstance(execution_contract, dict) or not execution_contract:
        add_error(
            "VKPLAN_EXECUTION_CONTRACT_MISSING",
            "implementation_plan 缺少 execution_contract",
            {},
        )

    implementation_tasks = _collect_implementation_tasks(implementation_tasks_raw)
    task_to_pr = _collect_task_to_pr_mapping(planning_contract)
    planning_cards = _collect_planning_cards(planning_contract)
    vk_cards = _collect_vk_cards(vk_cards_payload)

    impl_task_ids = set(implementation_tasks.keys())
    mapping_task_ids = set(task_to_pr.keys())
    plan_card_ids = set(planning_cards.keys())
    vk_card_ids = set(vk_cards.keys())

    impl_feature_ids = {
        feature_id
        for task in implementation_tasks.values()
        for feature_id in task["feature_ids"]
        if feature_id
    }
    plan_feature_ids = {
        feature_id
        for card in planning_cards.values()
        for feature_id in card["feature_ids"]
        if feature_id
    }
    vk_feature_ids = {
        feature_id
        for card in vk_cards.values()
        for feature_id in card["feature_ids"]
        if feature_id
    }
    vk_task_ids = {
        task_id for card in vk_cards.values() for task_id in card["task_ids"] if task_id
    }

    missing_impl_task_mapping = sorted(impl_task_ids - mapping_task_ids)
    if missing_impl_task_mapping:
        add_error(
            "VKPLAN_TASK_MAPPING_GAP",
            "implementation_tasks 存在未映射到 task_to_pr_mapping 的 task_id",
            missing_impl_task_mapping,
        )

    extra_mapping_tasks = sorted(mapping_task_ids - impl_task_ids)
    if extra_mapping_tasks:
        add_error(
            "VKPLAN_TASK_MAPPING_GAP",
            "task_to_pr_mapping 存在 implementation_tasks 未定义的 task_id",
            extra_mapping_tasks,
        )

    missing_plan_cards = sorted(plan_card_ids - vk_card_ids)
    if missing_plan_cards:
        add_error(
            "VKPLAN_CARD_MAPPING_BROKEN",
            "planning_contract.cards 未完整映射到 vk_cards.cards",
            missing_plan_cards,
        )

    missing_task_id_fields = sorted(
        card["card_id"] for card in vk_cards.values() if not card.get("task_ids_present")
    )
    empty_task_id_fields = sorted(
        card["card_id"]
        for card in vk_cards.values()
        if card.get("task_ids_present") and not card.get("task_ids")
    )
    if missing_task_id_fields or empty_task_id_fields:
        add_error(
            "VKPLAN_TASK_IDS_REQUIRED",
            "vk_cards.cards[*].task_ids 必填且不能为空",
            {
                "missing_task_ids_field": missing_task_id_fields,
                "empty_task_ids": empty_task_id_fields,
            },
        )

    missing_feature_ids = sorted((impl_feature_ids | plan_feature_ids) - vk_feature_ids)
    if missing_feature_ids:
        add_error(
            "VKPLAN_CONSUMPTION_GAP",
            "feature_id 存在未消费项",
            missing_feature_ids,
        )

    missing_task_ids = sorted(impl_task_ids - vk_task_ids)
    if missing_task_ids:
        add_error(
            "VKPLAN_CONSUMPTION_GAP",
            "task_id 存在未消费项",
            missing_task_ids,
        )

    pr_mapping_mismatch: list[dict[str, Any]] = []
    for task_id, mapping in task_to_pr.items():
        expected_pr_id = mapping["pr_id"]
        if not expected_pr_id:
            continue
        cards_with_task = [card for card in vk_cards.values() if task_id in card["task_ids"]]
        if not cards_with_task:
            continue
        if any(card["pr_id"] == expected_pr_id for card in cards_with_task):
            continue
        pr_mapping_mismatch.append(
            {
                "task_id": task_id,
                "expected_pr_id": expected_pr_id,
                "actual_pr_ids": sorted({card["pr_id"] for card in cards_with_task if card["pr_id"]}),
                "cards": [card["card_id"] for card in cards_with_task],
            }
        )
    if pr_mapping_mismatch:
        add_error(
            "VKPLAN_PR_MAPPING_BROKEN",
            "task_id -> pr_id 映射与 vk_cards 不一致",
            pr_mapping_mismatch,
        )

    expected_acceptance_by_task = {
        task_id: set(task["acceptance_cmds"]) | set(task_to_pr.get(task_id, {}).get("acceptance_cmds") or set())
        for task_id, task in implementation_tasks.items()
    }

    acceptance_mapping_missing: list[dict[str, Any]] = []
    for card in vk_cards.values():
        card_task_ids = sorted(task_id for task_id in card["task_ids"] if task_id in implementation_tasks)
        if not card_task_ids:
            continue

        expected_cmds = {
            cmd
            for task_id in card_task_ids
            for cmd in expected_acceptance_by_task.get(task_id, set())
            if cmd
        }
        actual_cmds = {cmd for cmd in card["acceptance_checks"] if cmd}
        missing_cmds = sorted(cmd for cmd in expected_cmds if cmd not in actual_cmds)
        extra_cmds = sorted(cmd for cmd in actual_cmds if cmd not in expected_cmds)
        if not missing_cmds and not extra_cmds:
            continue

        acceptance_mapping_missing.append(
            {
                "card_id": card["card_id"],
                "task_ids": card_task_ids,
                "missing_cmds": missing_cmds,
                "extra_cmds": extra_cmds,
            }
        )

    if acceptance_mapping_missing:
        add_error(
            "VKPLAN_ACCEPTANCE_MAPPING_BROKEN",
            "acceptance_cmds 与卡片 acceptance_checks 不一致",
            acceptance_mapping_missing,
        )

    execution_contract_mismatch: list[dict[str, Any]] = []
    vk_execution_contract = vk_cards_payload.get("execution_contract")
    if not isinstance(vk_execution_contract, dict):
        add_error(
            "VKPLAN_EXECUTION_CONTRACT_MISMATCH",
            "vk_cards.json 缺少 execution_contract",
            {"required_fields": list(REQUIRED_EXECUTION_FIELDS)},
        )
    else:
        missing_exec_fields = [
            field
            for field in REQUIRED_EXECUTION_FIELDS
            if field not in execution_contract or field not in vk_execution_contract
        ]
        if missing_exec_fields:
            add_error(
                "VKPLAN_EXECUTION_CONTRACT_MISMATCH",
                "execution_contract 缺少必填字段",
                {"missing_fields": missing_exec_fields},
            )

        for field in REQUIRED_EXECUTION_FIELDS:
            plan_value = _normalize_scalar(execution_contract.get(field))
            vk_value = _normalize_scalar(vk_execution_contract.get(field))
            if not plan_value or not vk_value or plan_value == vk_value:
                continue
            execution_contract_mismatch.append(
                {
                    "field": field,
                    "implementation_plan": plan_value,
                    "vk_cards": vk_value,
                }
            )

    if execution_contract_mismatch:
        add_error(
            "VKPLAN_EXECUTION_CONTRACT_MISMATCH",
            "execution_contract 字段值不一致",
            execution_contract_mismatch,
        )

    return {
        "errors": errors,
        "missing_feature_ids": missing_feature_ids,
        "missing_task_ids": missing_task_ids,
        "execution_contract_mismatch": execution_contract_mismatch,
        "acceptance_mapping_missing": acceptance_mapping_missing,
        "missing_plan_card_ids": missing_plan_cards,
        "missing_task_id_fields": missing_task_id_fields,
        "empty_task_ids": empty_task_id_fields,
        "summary": {
            "implementation_tasks": len(implementation_tasks),
            "task_to_pr_mapping": len(task_to_pr),
            "planning_cards": len(planning_cards),
            "vk_cards": len(vk_cards),
            "impl_feature_ids": len(impl_feature_ids),
            "vk_feature_ids": len(vk_feature_ids),
        },
    }


def run_check(*, repo_root: Path, task_split_dir_raw: str) -> dict[str, Any]:
    task_split_dir = _resolve_task_split_dir(repo_root, task_split_dir_raw)
    vk_cards_path = task_split_dir / "vk_cards.json"
    if not vk_cards_path.exists():
        raise CoverageCheckError(f"缺少文件: {vk_cards_path}")

    vk_cards_payload = _load_json(vk_cards_path)
    implementation_plan = _resolve_implementation_plan(
        repo_root=repo_root,
        task_split_dir=task_split_dir,
        vk_cards=vk_cards_payload,
    )
    try:
        clarify_plan_alignment = run_alignment_check(
            repo_root=repo_root,
            task_split_dir_raw=task_split_dir.name,
            implementation_path_raw=str(implementation_plan),
        )
    except AlignmentCheckError as exc:
        clarify_plan_alignment = {
            "ok": False,
            "error": {
                "code": "CLARIFY_PLAN_ALIGNMENT_FAILED",
                "message": str(exc),
            },
        }

    contracts = _collect_contracts(implementation_plan)
    coverage = _check_coverage(contracts=contracts, vk_cards_payload=vk_cards_payload)

    errors = list(coverage["errors"])
    if not clarify_plan_alignment.get("ok"):
        details = (
            clarify_plan_alignment.get("errors")
            if isinstance(clarify_plan_alignment.get("errors"), list)
            else clarify_plan_alignment.get("error") or {}
        )
        if isinstance(details, list):
            propagated_codes = {
                item.get("code")
                for item in details
                if isinstance(item, dict) and item.get("code")
            }
            for code in (
                "PLAN_FORBIDDEN_PROTOCOL_FIELD_DETECTED",
                "PLAN_IMPLEMENTATION_DETAIL_INSUFFICIENT",
            ):
                if code in propagated_codes:
                    errors.append(
                        {
                            "code": code,
                            "message": f"clarify -> plan 承接校验命中 {code}",
                            "details": details,
                        }
                    )
        errors.append(
            {
                "code": "CLARIFY_PLAN_ALIGNMENT_FAILED",
                "message": "clarify -> plan 承接校验未通过",
                "details": details,
            }
        )
    ok = not errors
    if coverage["missing_feature_ids"] or coverage["missing_task_ids"]:
        ok = False

    return {
        "ok": ok,
        "task_split_dir": task_split_dir.name,
        "task_split_dir_path": str(task_split_dir),
        "implementation_plan": str(implementation_plan),
        "vk_cards": str(vk_cards_path),
        "warnings": contracts.get("warnings") or [],
        "missing_feature_ids": coverage["missing_feature_ids"],
        "missing_task_ids": coverage["missing_task_ids"],
        "execution_contract_mismatch": coverage["execution_contract_mismatch"],
        "acceptance_mapping_missing": coverage["acceptance_mapping_missing"],
        "missing_plan_card_ids": coverage["missing_plan_card_ids"],
        "missing_task_id_fields": coverage["missing_task_id_fields"],
        "empty_task_ids": coverage["empty_task_ids"],
        "clarify_plan_alignment": clarify_plan_alignment,
        "summary": coverage["summary"],
        "errors": errors,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验 /jjk-vkplan 是否完整消费 /jjk-plan 产物")
    parser.add_argument("--task-split-dir", required=True, help="任务拆解目录（名称或路径）")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument(
        "--output",
        default="-",
        help="输出文件路径；默认 stdout，传 '-' 表示 stdout",
    )
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
        result = run_check(repo_root=repo_root, task_split_dir_raw=args.task_split_dir)
    except CoverageCheckError as exc:
        payload = {
            "ok": False,
            "error": {
                "code": "VKPLAN_CONSUMPTION_GAP",
                "message": str(exc),
            },
        }
        _write_output(payload, args.output)
        return 2

    _write_output(result, args.output)
    return 0 if result.get("ok") else 2


def wrapper_notice() -> str:
    return "[DEPRECATED] check_plan_vk_coverage.py 已降级为 wrapper，请改用 python3 scripts/check_workflow_contract.py --mode plan_vk_coverage"


def _run_legacy_wrapper(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    print(wrapper_notice(), file=sys.stderr)
    command = [
        sys.executable,
        str((Path(__file__).resolve().parent / "check_workflow_contract.py").resolve()),
        "--mode",
        "plan_vk_coverage",
        *args,
    ]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(_run_legacy_wrapper())
