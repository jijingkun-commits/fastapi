"""coder4 dispatch 执行器路由回归测试。"""

from __future__ import annotations

import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/coder4/coder4_bootstrap_kernel.py")


def _load_kernel_module():
    module_name = f"coder4_dispatch_executor_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_ctx(module, *, dispatch_executor: str = "wtimp", dispatch_executor_mode: str = "cardrun_dispatch"):
    return module.KernelContext(
        project_id="proj-1",
        task_key="PP-20260306-CARDRUN-WTIMP",
        execution_mode="serial",
        single_active_card=True,
        preflight_required="C00",
        preflight_ok=True,
        preflight_reason="preflight_card_done",
        card_order=["C01"],
        cards_by_id={"C01": {"card_id": "C01"}},
        scoped_tasks=[],
        unscoped_tasks=[],
        card_status_map={"C01": "inprogress"},
        card_task_map={"C01": {"id": "task-c01", "status": "inprogress"}},
        scope_guard_ok=True,
        scope_guard_reason="scope_guard_passed",
        scope_guard_details=[],
        main_repo_path="/tmp",
        main_repo_clean=True,
        main_repo_dirty_preview=[],
        main_repo_dirty_ignored_preview=[],
        main_repo_error=None,
        dispatch_executor=dispatch_executor,
        dispatch_executor_mode=dispatch_executor_mode,
    )


def test_resolve_dispatch_executor_uses_active_then_default_then_cli_override():
    module = _load_kernel_module()

    executor, mode = module.resolve_dispatch_executor(
        active_payload={
            "dispatch_executor": "WTIMP",
            "dispatch_executor_mode": "CARDRUN_DISPATCH",
        }
    )
    assert executor == "wtimp"
    assert mode == "cardrun_dispatch"

    executor, mode = module.resolve_dispatch_executor(active_payload={})
    assert executor == module.DEFAULT_DISPATCH_EXECUTOR
    assert mode == module.DEFAULT_DISPATCH_EXECUTOR_MODE

    executor, mode = module.resolve_dispatch_executor(
        active_payload={"dispatch_executor": "wtimp", "dispatch_executor_mode": "cardrun_dispatch"},
        cli_override="legacy",
    )
    assert executor == "legacy"
    assert mode == "cardrun_dispatch"


def test_apply_dispatch_action_returns_executor_evidence_and_executed_result():
    module = _load_kernel_module()
    ctx = _build_ctx(module)

    payload = module.apply_action(
        "http://127.0.0.1:3001",
        ctx,
        "dispatch",
        "C01",
        "task-c01",
        active_task_path=Path("/tmp/active-task.json"),
        commit_sha="abc123",
        merge_sha="def456",
        subagent_id="agent-1",
        ws_file="workstreams/WS-01.md",
    )

    assert payload["performed"] is True
    assert payload["action"] == "dispatch"
    assert payload["executor_mode"] == "wtimp"
    assert payload["executor_dispatch_mode"] == "cardrun_dispatch"
    assert payload["merge_owner"] == "wt_flow"
    assert payload["commit_sha"] == "abc123"
    assert payload["merge_sha"] == "def456"

    assert module._derive_attempt_result("dispatch", applied_performed=True) == "dispatch_executed"
    assert module._derive_attempt_result("dispatch", applied_performed=False) == "dispatch_pending"
