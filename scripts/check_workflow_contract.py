#!/usr/bin/env python3
"""统一门禁入口：按 mode 分发到既有 workflow contract 校验实现。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"


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
    parser.add_argument("--state-dir", default=str(module.DEFAULT_STATE_DIR), help="状态目录（默认 <task_split_dir>/.state）")
    parser.add_argument("--repo-root", default=str(module.ROOT), help="仓库根目录")
    parser.add_argument("--output", default="", help="可选输出 JSON 文件路径，'-' 表示打印 JSON")
    args = parser.parse_args(list(passthrough_args))

    repo_root = Path(args.repo_root).expanduser().resolve()
    try:
        task_split_dir = module._resolve_task_split_dir(repo_root, args.task_split_dir)
        state_dir = Path(args.state_dir).expanduser()
        if state_dir.is_absolute():
            resolved_state_dir = state_dir.resolve()
        elif args.state_dir in {".state", "./.state"}:
            resolved_state_dir = (task_split_dir / ".state").resolve()
        else:
            resolved_state_dir = (repo_root / state_dir).resolve()
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


def _resolve_task_split_dir_arg(repo_root: Path, raw_value: str) -> Path:
    raw = str(raw_value or "").strip()
    if not raw:
        raise SystemExit("缺少 --task-split-dir")
    direct = Path(raw).expanduser()
    candidates: list[Path] = []
    if direct.is_absolute():
        candidates.append(direct)
    else:
        candidates.extend([(repo_root / raw), (repo_root / "docs/内部参考/任务拆解" / raw)])
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    joined = " | ".join(str(path) for path in candidates)
    raise SystemExit(f"无法定位 task_split_dir: {raw}; candidates={joined}")


def _load_task_source_files(task_split_dir: Path) -> dict[str, Any]:
    cards_path = task_split_dir / "vk_cards.json"
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


MODE_REGISTRY: dict[str, ModeSpec] = {
    "clarify_plan": ModeSpec(
        mode="clarify_plan",
        description="校验 /jjk-clarify -> /jjk-plan 产物承接完整性",
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
        available=False,
        planned_card="C05",
    ),
    "ttl-audit": ModeSpec(
        mode="ttl-audit",
        description="过程文件 TTL 审计",
        available=False,
        planned_card="C06",
    ),
    "full-gate": ModeSpec(
        mode="full-gate",
        description="全链路门禁验收",
        available=False,
        planned_card="G01",
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
        return spec.runner(passthrough_args)

    if spec.available and spec.script:
        return _run_subprocess(spec.script, passthrough_args)

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
