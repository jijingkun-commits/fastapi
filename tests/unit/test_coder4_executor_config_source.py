"""coder4 dispatch 执行器配置来源回归测试。"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/coder4/coder4_bootstrap_kernel.py")
TASK_KEY = "PP-20260306-CARDRUN-WTIMP"
TASK_SPLIT_DIR = "2026-03-06_cardrun_wtimp_executor"


def _load_kernel_module():
    module_name = f"coder4_executor_config_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_workspace(
    tmp_path: Path,
    *,
    dispatch_executor: str | None = None,
    dispatch_executor_mode: str | None = None,
) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)

    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "set_active_task.py").write_text("# test stub\n", encoding="utf-8")

    active_payload = {
        "project_id": "project-1",
        "task_split_dir": TASK_SPLIT_DIR,
        "task_key": TASK_KEY,
        "execution_mode": "serial",
        "single_active_card": True,
        "preflight_required": "C00",
    }
    if dispatch_executor is not None:
        active_payload["dispatch_executor"] = dispatch_executor
    if dispatch_executor_mode is not None:
        active_payload["dispatch_executor_mode"] = dispatch_executor_mode

    active_task_path = tmp_path / "docs" / "内部参考" / "任务拆解" / "_active_task.json"
    _write_json(active_task_path, active_payload)

    _write_json(
        active_task_path.parent / "vk_cards.json",
        {
            "execution_mode": "serial",
            "card_order": ["C01"],
            "cards": [
                {
                    "card_id": "C01",
                    "task_ids": ["T-01"],
                    "pr_id": "PR-01",
                    "hard_depends_on": [],
                    "acceptance_checks": ["pytest -q tests/unit/test_dummy.py"],
                }
            ],
            "task_to_pr_mapping": [
                {
                    "task_id": "T-01",
                    "pr_id": "PR-01",
                }
            ],
        },
    )

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init fixture"], cwd=tmp_path, check=True, capture_output=True)
    return active_task_path


def _stub_coverage_gate(monkeypatch, module):
    monkeypatch.setattr(
        module,
        "run_plan_vk_coverage_check",
        lambda **_kwargs: {
            "ok": True,
            "missing_task_ids": [],
            "missing_task_id_fields": [],
            "empty_task_ids": [],
            "clarify_plan_alignment": {"ok": True},
        },
    )


def test_build_kernel_context_uses_active_task_dispatch_executor(monkeypatch, tmp_path):
    module = _load_kernel_module()
    _stub_coverage_gate(monkeypatch, module)
    active_task_path = _prepare_workspace(
        tmp_path,
        dispatch_executor="wtimp",
        dispatch_executor_mode="cardrun_dispatch",
    )

    ctx = module.build_kernel_context(
        active_task_path,
        "http://127.0.0.1:3001",
        local_mode=True,
    )

    assert ctx.dispatch_executor == "wtimp"
    assert ctx.dispatch_executor_mode == "cardrun_dispatch"


def test_build_kernel_context_falls_back_to_default_executor(monkeypatch, tmp_path):
    module = _load_kernel_module()
    _stub_coverage_gate(monkeypatch, module)
    active_task_path = _prepare_workspace(tmp_path)

    ctx = module.build_kernel_context(
        active_task_path,
        "http://127.0.0.1:3001",
        local_mode=True,
    )

    assert ctx.dispatch_executor == module.DEFAULT_DISPATCH_EXECUTOR
    assert ctx.dispatch_executor_mode == module.DEFAULT_DISPATCH_EXECUTOR_MODE


def test_build_kernel_context_allows_cli_override(monkeypatch, tmp_path):
    module = _load_kernel_module()
    _stub_coverage_gate(monkeypatch, module)
    active_task_path = _prepare_workspace(
        tmp_path,
        dispatch_executor="wtimp",
        dispatch_executor_mode="cardrun_dispatch",
    )

    ctx = module.build_kernel_context(
        active_task_path,
        "http://127.0.0.1:3001",
        local_mode=True,
        dispatch_executor_override="legacy",
    )

    assert ctx.dispatch_executor == "legacy"
    assert ctx.dispatch_executor_mode == "cardrun_dispatch"
