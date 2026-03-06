"""coder4 dispatch 单一路径收口约束测试。"""

from __future__ import annotations

import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/coder4/coder4_bootstrap_kernel.py")


def _load_kernel_module():
    module_name = f"coder4_single_merge_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_ctx(module):
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
        dispatch_executor="wtimp",
        dispatch_executor_mode="cardrun_dispatch",
    )


def test_dispatch_mode_returns_wt_flow_merge_owner_and_never_calls_http(monkeypatch):
    module = _load_kernel_module()
    ctx = _build_ctx(module)

    def _unexpected_http(*_args, **_kwargs):
        raise AssertionError("dispatch 模式不应直接调用 HTTP merge/seed 接口")

    monkeypatch.setattr(module, "http_json", _unexpected_http)

    payload = module.apply_action(
        "http://127.0.0.1:3001",
        ctx,
        "dispatch",
        "C01",
        "task-c01",
        active_task_path=Path("/tmp/active-task.json"),
        commit_sha="abc123",
    )

    assert payload["performed"] is True
    assert payload["action"] == "dispatch"
    assert payload["merge_owner"] == "wt_flow"
    assert payload["executor_dispatch_mode"] == "cardrun_dispatch"
    assert payload["merge_sha"] is None
    assert "vk_sync" not in payload
