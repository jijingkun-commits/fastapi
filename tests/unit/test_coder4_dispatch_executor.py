"""coder4 dispatch 执行器路由回归测试。"""

from __future__ import annotations

import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/coder4/coder4_bootstrap_kernel.py")


def _load_kernel_module():
    module_name = f"coder4_dispatch_executor_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_ctx(module, *, dispatch_executor: str = "wtimp", dispatch_executor_mode: str = "cardrun_dispatch", dispatch_timeout_seconds: int = 600):
    return module.KernelContext(
        project_id="proj-1",
        task_key="PP-20260306-CARDRUN-WTIMP",
        execution_mode="serial",
        single_active_card=True,
        preflight_required="C00",
        preflight_ok=True,
        preflight_reason="preflight_card_done",
        card_order=["C01"],
        cards_by_id={
            "C01": {
                "card_id": "C01",
                "source_ws_file": "workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C01.md",
            }
        },
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
        dispatch_timeout_seconds=dispatch_timeout_seconds,
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





def test_resolve_dispatch_timeout_seconds_uses_cli_then_env_then_active_then_default(monkeypatch):
    module = _load_kernel_module()

    monkeypatch.delenv(module.DISPATCH_TIMEOUT_ENV, raising=False)
    assert module.resolve_dispatch_timeout_seconds(active_payload={}) == module.DEFAULT_DISPATCH_TIMEOUT_SECONDS
    assert module.resolve_dispatch_timeout_seconds(active_payload={"dispatch_timeout_seconds": 90}) == 90

    monkeypatch.setenv(module.DISPATCH_TIMEOUT_ENV, "75")
    assert module.resolve_dispatch_timeout_seconds(active_payload={"dispatch_timeout_seconds": 90}) == 75
    assert module.resolve_dispatch_timeout_seconds(active_payload={"dispatch_timeout_seconds": 90}, cli_override=45) == 45
def test_apply_dispatch_action_returns_executor_evidence_and_executed_result(monkeypatch, tmp_path):
    module = _load_kernel_module()
    ctx = _build_ctx(module)

    expected_request = module.wtimp_dispatch_bridge.WtimpDispatchRequest(
        task_key=ctx.task_key,
        card_id="C01",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C01.md",
        worktree_path=str((tmp_path / "wt-C01").resolve()),
        executor_mode="cardrun_dispatch",
    )

    def _fake_build_request(*_args, **_kwargs):
        return expected_request

    def _fake_run_dispatch(request):
        assert request == expected_request
        return module.wtimp_dispatch_bridge.WtimpDispatchResult(
            ok=True,
            executor="wtimp",
            executor_mode="cardrun_dispatch",
            card_id="C01",
            ws_file=expected_request.ws_file,
            subagent_id="wtimp-C01-1",
            commit_sha="abc123",
            merge_sha=None,
            changed_files=["scripts/coder4/coder4_bootstrap_kernel.py"],
            acceptance_results=[{"kind": "chat_db", "cmd": "pytest -q", "exit_code": 0, "summary": "1 passed"}],
            evidence_satisfied=True,
            worktree_path=expected_request.worktree_path,
        )

    monkeypatch.setattr(module, "build_wtimp_dispatch_request", _fake_build_request)
    monkeypatch.setattr(module, "run_wtimp_dispatch", _fake_run_dispatch)

    payload = module.apply_action(
        "http://127.0.0.1:3001",
        ctx,
        "dispatch",
        "C01",
        "task-c01",
        active_task_path=tmp_path / "active-task.json",
        commit_sha="manual-should-be-ignored",
        merge_sha="manual-should-be-ignored",
    )

    assert payload["performed"] is True
    assert payload["action"] == "dispatch"
    assert payload["executor_mode"] == "wtimp"
    assert payload["executor_dispatch_mode"] == "cardrun_dispatch"
    assert payload["merge_owner"] == "wt_flow"
    assert payload["subagent_id"] == "wtimp-C01-1"
    assert payload["ws_file"] == expected_request.ws_file
    assert payload["commit_sha"] == "abc123"
    assert payload["merge_sha"] is None
    assert payload["worktree_path"] == expected_request.worktree_path
    assert payload["changed_files"] == ["scripts/coder4/coder4_bootstrap_kernel.py"]
    assert payload["acceptance_results"][0]["kind"] == "chat_db"
    assert payload["evidence_satisfied"] is True

    assert module._derive_attempt_result("dispatch", applied_performed=True) == "dispatch_executed"
    assert module._derive_attempt_result("dispatch", applied_performed=False) == "dispatch_pending"


def test_apply_dispatch_action_maps_bridge_error_to_subagent_failed(monkeypatch, tmp_path):
    module = _load_kernel_module()
    ctx = _build_ctx(module)

    monkeypatch.setattr(
        module,
        "build_wtimp_dispatch_request",
        lambda *_args, **_kwargs: module.wtimp_dispatch_bridge.WtimpDispatchRequest(
            task_key=ctx.task_key,
            card_id="C01",
            ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C01.md",
            worktree_path=str((tmp_path / "wt-C01").resolve()),
            executor_mode="cardrun_dispatch",
        ),
    )

    def _raise_subagent_failed(_request):
        raise module.CardrunContractError(
            "CARDRUN_SUBAGENT_FAILED",
            "wtimp exec failed",
            {"card_id": "C01", "dispatch_executor": "wtimp"},
        )

    monkeypatch.setattr(module, "run_wtimp_dispatch", _raise_subagent_failed)

    with pytest.raises(module.CardrunContractError) as exc_info:
        module.apply_action(
            "http://127.0.0.1:3001",
            ctx,
            "dispatch",
            "C01",
            "task-c01",
            active_task_path=tmp_path / "active-task.json",
        )

    assert exc_info.value.code == "CARDRUN_SUBAGENT_FAILED"
    assert exc_info.value.details["card_id"] == "C01"



def test_build_wtimp_dispatch_request_propagates_dispatch_timeout(monkeypatch, tmp_path):
    module = _load_kernel_module()
    ctx = _build_ctx(module, dispatch_timeout_seconds=45)

    worktree_path = (tmp_path / "wt-C01").resolve()
    monkeypatch.setattr(
        module,
        "resolve_card_source_ws_file",
        lambda *_args, **_kwargs: "workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C01.md",
    )
    monkeypatch.setattr(module, "resolve_active_session_worktree_path", lambda *_args, **_kwargs: str(worktree_path))

    request = module.build_wtimp_dispatch_request(
        ctx,
        "C01",
        active_task_path=tmp_path / "active-task.json",
    )

    assert request.timeout_seconds == 45
    assert request.worktree_path == str(worktree_path)
