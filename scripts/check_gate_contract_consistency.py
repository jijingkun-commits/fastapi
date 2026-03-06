#!/usr/bin/env python3
"""校验 Gate 契约在三份产物中的一致性。

校验目标：
1) docs/内部参考/任务拆解/<task_split_dir>/vk_cards.json
2) docs/内部参考/任务拆解/<task_split_dir>/parallel_plan.md
3) implementation_plan（优先使用 vk_cards.source_files.implementation_plan）

关键对齐项：
- execution_mode
- card_order
- gate_contract.mode
- gate_contract.gate_ids
- gate_contract.depends_on
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASK_SPLIT_BASE = Path("docs/内部参考/任务拆解")


class ContractParseError(RuntimeError):
    """契约解析失败。"""


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ContractParseError(f"JSON 根节点不是对象: {path}")
    return data


def _clean_scalar(raw: str) -> str:
    value = str(raw or "").strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    return value


def _normalize_id(raw: Any) -> str:
    value = str(raw or "").strip().strip("`'\"")
    return value.upper()


def _normalize_mode(raw: Any) -> str:
    return str(raw or "").strip().strip("`'\"").lower()


def _parse_inline_list(raw: str) -> list[str]:
    value = _clean_scalar(raw)
    if not value:
        return []

    try:
        parsed = ast.literal_eval(value)
    except Exception:
        parsed = None

    if isinstance(parsed, (list, tuple, set)):
        return [_normalize_id(item) for item in parsed if str(item).strip()]

    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]

    items = [item.strip().strip("`'\"") for item in value.split(",")]
    return [_normalize_id(item) for item in items if item]


def _normalize_depends_map(raw_map: dict[str, Any]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for key, value in raw_map.items():
        gate_id = _normalize_id(key)
        if not gate_id:
            continue
        if isinstance(value, (list, tuple, set)):
            deps_raw = list(value)
        elif value is None:
            deps_raw = []
        else:
            deps_raw = [value]
        deps: list[str] = []
        seen: set[str] = set()
        for dep in deps_raw:
            dep_id = _normalize_id(dep)
            if not dep_id or dep_id in seen:
                continue
            deps.append(dep_id)
            seen.add(dep_id)
        normalized[gate_id] = deps
    return normalized


def _parse_inline_depends_map(raw: str) -> dict[str, list[str]]:
    value = _clean_scalar(raw)
    if not value:
        return {}

    try:
        parsed = ast.literal_eval(value)
    except Exception:
        parsed = None

    if isinstance(parsed, dict):
        return _normalize_depends_map(parsed)

    match_items = re.findall(r"([A-Za-z0-9_-]+)\s*:\s*\[([^\]]*)\]", value)
    if not match_items:
        raise ContractParseError(f"无法解析 depends_on: {raw}")

    mapped: dict[str, list[str]] = {}
    for gate_id_raw, deps_raw in match_items:
        mapped[_normalize_id(gate_id_raw)] = _parse_inline_list(f"[{deps_raw}]")
    return _normalize_depends_map(mapped)


def _resolve_task_split_dir(repo_root: Path, raw_value: str) -> Path:
    raw = str(raw_value or "").strip()
    if not raw:
        raise ContractParseError("缺少 --task-split-dir")

    direct = Path(raw).expanduser()
    candidates = []
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
    raise ContractParseError(f"无法定位 task_split_dir: {raw}; candidates={joined}")


def _extract_parallel_contract(parallel_path: Path) -> dict[str, Any]:
    lines = parallel_path.read_text(encoding="utf-8").splitlines()

    execution_mode = ""
    card_order: list[str] = []
    gate_mode = ""
    gate_ids: list[str] = []
    gate_depends: dict[str, list[str]] = {}

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("- execution_mode:"):
            execution_mode = _normalize_mode(stripped.split(":", 1)[1])
        elif stripped.startswith("- card_order:"):
            card_order = _parse_inline_list(stripped.split(":", 1)[1])
        elif stripped.startswith("- gate_contract:"):
            sub_index = idx + 1
            while sub_index < len(lines):
                sub_line = lines[sub_index]
                if not sub_line.startswith("  - "):
                    break
                sub_stripped = sub_line.strip()
                if sub_stripped.startswith("- mode:"):
                    gate_mode = _normalize_mode(sub_stripped.split(":", 1)[1])
                elif sub_stripped.startswith("- gate_ids:"):
                    gate_ids = _parse_inline_list(sub_stripped.split(":", 1)[1])
                elif sub_stripped.startswith("- depends_on:"):
                    gate_depends = _parse_inline_depends_map(sub_stripped.split(":", 1)[1])
                sub_index += 1
            break

    if not execution_mode:
        raise ContractParseError(f"{parallel_path} 缺少 execution_mode")
    if not card_order:
        raise ContractParseError(f"{parallel_path} 缺少 card_order")
    if not gate_mode:
        raise ContractParseError(f"{parallel_path} 缺少 gate_contract.mode")
    if not gate_ids:
        raise ContractParseError(f"{parallel_path} 缺少 gate_contract.gate_ids")

    return {
        "execution_mode": execution_mode,
        "card_order": card_order,
        "gate_contract": {
            "mode": gate_mode,
            "gate_ids": gate_ids,
            "depends_on": gate_depends,
        },
    }


def _extract_yaml_block_with_planning_contract(text: str, source: Path) -> str:
    blocks = re.findall(r"```yaml\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    matches = [
        block
        for block in blocks
        if "planning_contract:" in block and "gate_contract:" in block and "card_order:" in block
    ]
    if not matches:
        raise ContractParseError(f"{source} 未找到包含 planning_contract 的 yaml 代码块")
    return matches[-1]


def _extract_impl_contract(implementation_path: Path) -> dict[str, Any]:
    text = implementation_path.read_text(encoding="utf-8")
    block = _extract_yaml_block_with_planning_contract(text, implementation_path)
    lines = block.splitlines()

    try:
        start_idx = next(
            idx for idx, line in enumerate(lines) if line.strip().startswith("planning_contract:")
        )
    except StopIteration as exc:
        raise ContractParseError(f"{implementation_path} 缺少 planning_contract") from exc

    execution_mode = ""
    card_order: list[str] = []
    gate_mode = ""
    gate_ids: list[str] = []
    gate_depends: dict[str, list[str]] = {}

    idx = start_idx + 1
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if not stripped:
            idx += 1
            continue
        if indent < 2:
            break

        if indent == 2 and stripped.startswith("execution_mode:"):
            execution_mode = _normalize_mode(stripped.split(":", 1)[1])
            idx += 1
            continue
        if indent == 2 and stripped.startswith("card_order:"):
            card_order = _parse_inline_list(stripped.split(":", 1)[1])
            idx += 1
            continue
        if indent == 2 and stripped.startswith("gate_contract:"):
            idx += 1
            while idx < len(lines):
                sub_line = lines[idx]
                sub_stripped = sub_line.strip()
                sub_indent = len(sub_line) - len(sub_line.lstrip(" "))
                if not sub_stripped:
                    idx += 1
                    continue
                if sub_indent < 4:
                    break
                if sub_indent == 4 and sub_stripped.startswith("mode:"):
                    gate_mode = _normalize_mode(sub_stripped.split(":", 1)[1])
                    idx += 1
                    continue
                if sub_indent == 4 and sub_stripped.startswith("gate_ids:"):
                    gate_ids = _parse_inline_list(sub_stripped.split(":", 1)[1])
                    idx += 1
                    continue
                if sub_indent == 4 and sub_stripped.startswith("depends_on:"):
                    idx += 1
                    while idx < len(lines):
                        dep_line = lines[idx]
                        dep_stripped = dep_line.strip()
                        dep_indent = len(dep_line) - len(dep_line.lstrip(" "))
                        if not dep_stripped:
                            idx += 1
                            continue
                        if dep_indent < 6:
                            break
                        if dep_indent == 6:
                            key, _, raw_value = dep_stripped.partition(":")
                            gate_key = _normalize_id(key)
                            gate_depends[gate_key] = _parse_inline_list(raw_value)
                        idx += 1
                    continue
                idx += 1
            continue

        idx += 1

    if not execution_mode:
        raise ContractParseError(f"{implementation_path} 缺少 planning_contract.execution_mode")
    if not card_order:
        raise ContractParseError(f"{implementation_path} 缺少 planning_contract.card_order")
    if not gate_mode:
        raise ContractParseError(f"{implementation_path} 缺少 planning_contract.gate_contract.mode")
    if not gate_ids:
        raise ContractParseError(f"{implementation_path} 缺少 planning_contract.gate_contract.gate_ids")

    return {
        "execution_mode": execution_mode,
        "card_order": card_order,
        "gate_contract": {
            "mode": gate_mode,
            "gate_ids": gate_ids,
            "depends_on": _normalize_depends_map(gate_depends),
        },
    }


def _extract_vk_contract(vk_cards: dict[str, Any], vk_cards_path: Path) -> dict[str, Any]:
    execution_mode = _normalize_mode(vk_cards.get("execution_mode"))
    card_order = [_normalize_id(card_id) for card_id in (vk_cards.get("card_order") or [])]
    gate_contract = vk_cards.get("gate_contract") or {}
    if not isinstance(gate_contract, dict):
        raise ContractParseError(f"{vk_cards_path} gate_contract 不是对象")

    gate_mode = _normalize_mode(gate_contract.get("mode"))
    gate_ids = [_normalize_id(card_id) for card_id in (gate_contract.get("gate_ids") or [])]
    gate_depends = _normalize_depends_map(gate_contract.get("depends_on") or {})

    if not execution_mode:
        raise ContractParseError(f"{vk_cards_path} 缺少 execution_mode")
    if not card_order:
        raise ContractParseError(f"{vk_cards_path} 缺少 card_order")
    if not gate_mode:
        raise ContractParseError(f"{vk_cards_path} 缺少 gate_contract.mode")
    if not gate_ids:
        raise ContractParseError(f"{vk_cards_path} 缺少 gate_contract.gate_ids")

    return {
        "execution_mode": execution_mode,
        "card_order": card_order,
        "gate_contract": {
            "mode": gate_mode,
            "gate_ids": gate_ids,
            "depends_on": gate_depends,
        },
    }


def _canonical_contract(contract: dict[str, Any]) -> dict[str, Any]:
    depends_on = contract["gate_contract"].get("depends_on") or {}
    canonical_depends: dict[str, list[str]] = {}
    for gate_id in sorted(depends_on):
        deps = sorted({_normalize_id(dep) for dep in depends_on[gate_id] if _normalize_id(dep)})
        canonical_depends[_normalize_id(gate_id)] = deps

    return {
        "execution_mode": _normalize_mode(contract.get("execution_mode")),
        "card_order": [_normalize_id(card_id) for card_id in contract.get("card_order") or []],
        "gate_contract": {
            "mode": _normalize_mode(contract["gate_contract"].get("mode")),
            "gate_ids": [_normalize_id(card_id) for card_id in contract["gate_contract"].get("gate_ids") or []],
            "depends_on": canonical_depends,
        },
    }


def _compare_contracts(
    *,
    expected_name: str,
    expected: dict[str, Any],
    actual_name: str,
    actual: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    fields = [
        ("execution_mode", expected["execution_mode"], actual["execution_mode"]),
        ("card_order", expected["card_order"], actual["card_order"]),
        ("gate_contract.mode", expected["gate_contract"]["mode"], actual["gate_contract"]["mode"]),
        ("gate_contract.gate_ids", expected["gate_contract"]["gate_ids"], actual["gate_contract"]["gate_ids"]),
        (
            "gate_contract.depends_on",
            expected["gate_contract"]["depends_on"],
            actual["gate_contract"]["depends_on"],
        ),
    ]

    for field_name, expected_value, actual_value in fields:
        if expected_value != actual_value:
            errors.append(
                f"{actual_name}.{field_name} 与 {expected_name} 不一致: "
                f"expected={expected_value} actual={actual_value}"
            )
    return errors


def _validate_gate_membership(contract: dict[str, Any], source_name: str) -> list[str]:
    errors: list[str] = []
    card_order = set(contract["card_order"])
    gate_ids = contract["gate_contract"]["gate_ids"]
    for gate_id in gate_ids:
        if gate_id not in card_order:
            errors.append(f"{source_name} gate_id 不在 card_order 中: {gate_id}")
    for gate_id, deps in contract["gate_contract"]["depends_on"].items():
        if gate_id not in gate_ids:
            errors.append(f"{source_name} depends_on 包含未声明 gate_id: {gate_id}")
        for dep in deps:
            if dep not in card_order:
                errors.append(f"{source_name} depends_on 引用了不存在的卡片: {gate_id}->{dep}")
    return errors


def run_check(task_split_dir: Path, repo_root: Path) -> dict[str, Any]:
    vk_cards_path = task_split_dir / "vk_cards.json"
    parallel_plan_path = task_split_dir / "parallel_plan.md"
    if not vk_cards_path.exists():
        raise ContractParseError(f"缺少文件: {vk_cards_path}")
    if not parallel_plan_path.exists():
        raise ContractParseError(f"缺少文件: {parallel_plan_path}")

    vk_cards = load_json(vk_cards_path)
    source_files = vk_cards.get("source_files") or {}
    implementation_rel = str(source_files.get("implementation_plan") or "").strip()
    if not implementation_rel:
        raise ContractParseError(f"{vk_cards_path} 缺少 source_files.implementation_plan")

    implementation_path = (repo_root / implementation_rel).resolve()
    if not implementation_path.exists():
        raise ContractParseError(f"implementation_plan 不存在: {implementation_path}")

    vk_contract = _canonical_contract(_extract_vk_contract(vk_cards, vk_cards_path))
    parallel_contract = _canonical_contract(_extract_parallel_contract(parallel_plan_path))
    impl_contract = _canonical_contract(_extract_impl_contract(implementation_path))

    errors: list[str] = []
    errors.extend(_compare_contracts(expected_name="vk_cards", expected=vk_contract, actual_name="parallel_plan", actual=parallel_contract))
    errors.extend(
        _compare_contracts(
            expected_name="vk_cards",
            expected=vk_contract,
            actual_name="implementation_plan",
            actual=impl_contract,
        )
    )
    errors.extend(_validate_gate_membership(vk_contract, "vk_cards"))
    errors.extend(_validate_gate_membership(parallel_contract, "parallel_plan"))
    errors.extend(_validate_gate_membership(impl_contract, "implementation_plan"))

    return {
        "ok": not errors,
        "task_split_dir": str(task_split_dir),
        "task_key": str(vk_cards.get("task_key") or ""),
        "files": {
            "vk_cards": str(vk_cards_path),
            "parallel_plan": str(parallel_plan_path),
            "implementation_plan": str(implementation_path),
        },
        "contracts": {
            "vk_cards": vk_contract,
            "parallel_plan": parallel_contract,
            "implementation_plan": impl_contract,
        },
        "errors": errors,
    }


def _write_output(path: str, payload: dict[str, Any]) -> None:
    if not path:
        return
    if path == "-":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    output_path = Path(path).expanduser()
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 Gate 契约在三份文档中的一致性")
    parser.add_argument("--task-split-dir", required=True, help="任务拆解目录名或绝对路径")
    parser.add_argument("--repo-root", default=str(ROOT), help="仓库根目录")
    parser.add_argument("--output", default="", help="可选输出 JSON 文件路径，'-' 表示打印 JSON")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        task_split_dir = _resolve_task_split_dir(repo_root, args.task_split_dir)
        result = run_check(task_split_dir, repo_root)
    except ContractParseError as exc:
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
        _write_output(args.output, result)
        return 0

    print("GATE_CONTRACT_CONSISTENCY: FAIL", file=sys.stderr)
    for issue in result["errors"]:
        print(f"- {issue}", file=sys.stderr)
    _write_output(args.output, result)
    return 1


def wrapper_notice() -> str:
    return "[DEPRECATED] check_gate_contract_consistency.py 已降级为 wrapper，请改用 python3 scripts/check_workflow_contract.py --mode gate_contract"


def _run_legacy_wrapper(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    print(wrapper_notice(), file=sys.stderr)
    command = [
        sys.executable,
        str((Path(__file__).resolve().parent / "check_workflow_contract.py").resolve()),
        "--mode",
        "gate_contract",
        *args,
    ]
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(_run_legacy_wrapper())
