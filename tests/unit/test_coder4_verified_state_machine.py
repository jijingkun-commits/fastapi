"""cardrun verified 状态机回归测试。"""

from __future__ import annotations

import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/coder4/coder4_bootstrap_kernel.py")


def _load_kernel_module():
    module_name = f"coder4_verified_state_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_ctx(module, *, status: str = "verified"):
    return module.KernelContext(
        project_id="proj-1",
        task_key="PP-20260307-VERIFIED-STATE",
        execution_mode="serial",
        single_active_card=True,
        preflight_required="C00",
        preflight_ok=True,
        preflight_reason="preflight_card_done",
        card_order=["C01", "C02"],
        cards_by_id={
            "C01": {"card_id": "C01", "source_ws_file": "docs/ws/WS-C01.md"},
            "C02": {"card_id": "C02", "source_ws_file": "docs/ws/WS-C02.md"},
        },
        scoped_tasks=[],
        unscoped_tasks=[],
        card_status_map={"C01": status, "C02": "todo"},
        card_task_map={
            "C01": {"id": "task-c01", "status": status},
            "C02": {"id": "task-c02", "status": "todo"},
        },
        scope_guard_ok=True,
        scope_guard_reason="scope_guard_passed",
        scope_guard_details=[],
        main_repo_path="/tmp",
        main_repo_clean=True,
        main_repo_dirty_preview=[],
        main_repo_dirty_ignored_preview=[],
        main_repo_error=None,
        dispatch_executor="wtimp",
        dispatch_executor_mode="cardrun_dispatch",
    )


def test_decide_action_treats_verified_as_first_class_waiting_merge_state():
    module = _load_kernel_module()
    ctx = _build_ctx(module, status="verified")

    action, card_id, task_id, target_status, blocked_details = module.decide_action(ctx)

    assert action == "awaiting_merge"
    assert card_id == "C01"
    assert task_id == "task-c01"
    assert target_status == "verified"
    assert blocked_details == [
        {
            "card_id": "C01",
            "status": "verified",
            "reason": "verified_waiting_merge",
        }
    ]
    assert module._derive_attempt_result("awaiting_merge", applied_performed=False) == "verified_waiting_merge"


def test_evaluate_scope_guard_blocks_unscoped_verified_task_when_single_active():
    module = _load_kernel_module()

    ok, reason, details = module.evaluate_scope_guard(
        scoped_tasks=[{"id": "task-scoped", "status": "todo", "title": "C01 scoped"}],
        unscoped_tasks=[{"id": "task-other", "status": "verified", "title": "C02 other task"}],
        single_active_card=True,
    )

    assert ok is False
    assert reason == "scope_conflict_unscoped_active"
    assert details[0]["reason"] == "scope_conflict_unscoped_active"
    assert details[0]["tasks"][0]["status"] == "verified"
