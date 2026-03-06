#!/usr/bin/env python3
"""统一门禁入口：按 mode 分发到既有 workflow contract 校验脚本。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ModeSpec:
    mode: str
    script: str | None
    description: str
    available: bool = True
    planned_card: str | None = None


MODE_REGISTRY: dict[str, ModeSpec] = {
    "clarify_plan": ModeSpec(
        mode="clarify_plan",
        script="scripts/check_clarify_plan_alignment.py",
        description="校验 /jjk-clarify -> /jjk-plan 产物承接完整性",
    ),
    "clarify_consistency": ModeSpec(
        mode="clarify_consistency",
        script="scripts/check_clarify_contract_consistency.py",
        description="校验 clarify 命令、模板与镜像一致性",
    ),
    "plan_vk_coverage": ModeSpec(
        mode="plan_vk_coverage",
        script="scripts/check_plan_vk_coverage.py",
        description="校验 /jjk-vkplan 是否完整消费 /jjk-plan 产物",
    ),
    "gate_contract": ModeSpec(
        mode="gate_contract",
        script="scripts/check_gate_contract_consistency.py",
        description="检查 Gate 契约在三份文档中的一致性",
    ),
    "integration_gate": ModeSpec(
        mode="integration_gate",
        script="scripts/check_integration_gate.py",
        description="IG01 集成门禁校验：实现卡必须已合并且主干可见",
    ),
    "legacy_wrapper_compat": ModeSpec(
        mode="legacy_wrapper_compat",
        script=None,
        description="旧脚本 wrapper 兼容性检查",
        available=False,
        planned_card="C03",
    ),
    "usage-report": ModeSpec(
        mode="usage-report",
        script=None,
        description="旧入口调用观测报告",
        available=False,
        planned_card="C05",
    ),
    "ttl-audit": ModeSpec(
        mode="ttl-audit",
        script=None,
        description="过程文件 TTL 审计",
        available=False,
        planned_card="C06",
    ),
    "full-gate": ModeSpec(
        mode="full-gate",
        script=None,
        description="全链路门禁验收",
        available=False,
        planned_card="G01",
    ),
}


def _serialize(payload: dict) -> str:
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


def _emit_payload(payload: dict, output_target: str | None) -> None:
    serialized = _serialize(payload)
    output_path = _resolve_output_path(output_target)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized + "\n", encoding="utf-8")
        print(f"written: {output_path}")
    print(serialized)


def _available_modes_payload() -> dict:
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

    if not spec.available or not spec.script:
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

    command = [sys.executable, str((ROOT / spec.script).resolve()), *passthrough_args]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


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
