"""coder4 dispatch 提交证据门禁回归测试。"""

from __future__ import annotations

import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/coder4/coder4_bootstrap_kernel.py")


def _load_kernel_module():
    module_name = f"coder4_commit_gate_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_ctx(module, *, dispatch_executor: str = "wtimp"):
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
        dispatch_executor_mode="cardrun_dispatch",
    )


def test_dispatch_requires_commit_sha_evidence():
    module = _load_kernel_module()
    ctx = _build_ctx(module)

    with pytest.raises(module.CardrunContractError) as exc_info:
        module.apply_action(
            "http://127.0.0.1:3001",
            ctx,
            "dispatch",
            "C01",
            "task-c01",
            active_task_path=Path("/tmp/active-task.json"),
            commit_sha="",
        )

    assert exc_info.value.code == "CARDRUN_NO_COMMIT_EVIDENCE"
    assert exc_info.value.details["card_id"] == "C01"
    assert exc_info.value.details["dispatch_executor"] == "wtimp"


def test_dispatch_rejects_unsupported_executor():
    module = _load_kernel_module()
    ctx = _build_ctx(module, dispatch_executor="imp-ws")

    with pytest.raises(module.CardrunContractError) as exc_info:
        module.apply_action(
            "http://127.0.0.1:3001",
            ctx,
            "dispatch",
            "C01",
            "task-c01",
            active_task_path=Path("/tmp/active-task.json"),
            commit_sha="abc123",
        )

    assert exc_info.value.code == "CARDRUN_EXECUTOR_UNSUPPORTED"
    assert exc_info.value.details["dispatch_executor"] == "imp-ws"
    assert exc_info.value.details["expected"] == module.DEFAULT_DISPATCH_EXECUTOR
