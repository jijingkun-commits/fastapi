"""coder4 active session worktree 解析测试。"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/coder4/coder4_bootstrap_kernel.py")
TASK_SPLIT_DIR = "2026-03-06_cardrun_dispatch_bridge"
TASK_KEY = "PP-20260306-CARDRUN-WTIMP"


def _load_kernel_module():
    module_name = f"coder4_worktree_session_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_workspace(tmp_path: Path) -> tuple[Path, str, str]:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)

    task_dir = tmp_path / "docs" / "内部参考" / "任务拆解" / TASK_SPLIT_DIR
    active_task_path = task_dir / "_active_task.json"
    _write_json(
        active_task_path,
        {
            "project_id": "project-1",
            "task_split_dir": TASK_SPLIT_DIR,
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "single_active_card": True,
            "preflight_required": "C00",
        },
    )

    ws_file = f"docs/内部参考/任务拆解/{TASK_SPLIT_DIR}/workstreams/WS-C01_test.md"
    (tmp_path / ws_file).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ws_file).write_text("# ws\n", encoding="utf-8")

    sanitized_task_key = module_task_key_segment(TASK_KEY)
    worktree_path = str((tmp_path / ".worktrees" / sanitized_task_key / "C01" / "session-1").resolve())
    Path(worktree_path).mkdir(parents=True, exist_ok=True)

    _write_json(
        task_dir / ".state" / sanitized_task_key / "active-session-session-1.json",
        {
            "branch": f"feature/{sanitized_task_key}/C01/session-1",
            "worktree": worktree_path,
            "base_branch": "master",
            "task_key": TASK_KEY,
            "session_id": "session-1",
        },
    )

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init fixture"], cwd=tmp_path, check=True, capture_output=True)
    return active_task_path, ws_file, worktree_path


def module_task_key_segment(task_key: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in task_key).strip("._")


def _build_ctx(module, ws_file: str):
    return module.KernelContext(
        project_id="project-1",
        task_key=TASK_KEY,
        execution_mode="serial",
        single_active_card=True,
        preflight_required="C00",
        preflight_ok=True,
        preflight_reason="preflight_card_done",
        card_order=["C01"],
        cards_by_id={"C01": {"card_id": "C01", "source_ws_file": ws_file}},
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


def test_build_wtimp_dispatch_request_uses_task_ws_file_and_session_worktree(tmp_path):
    module = _load_kernel_module()
    active_task_path, ws_file, worktree_path = _prepare_workspace(tmp_path)
    ctx = _build_ctx(module, ws_file)

    request = module.build_wtimp_dispatch_request(
        ctx,
        "C01",
        active_task_path=active_task_path,
    )

    assert request.task_key == TASK_KEY
    assert request.card_id == "C01"
    assert request.ws_file == ws_file
    assert request.worktree_path == worktree_path
    assert request.executor_mode == "cardrun_dispatch"


def test_resolve_active_session_worktree_path_fails_on_multiple_sessions(tmp_path):
    module = _load_kernel_module()
    active_task_path, ws_file, _ = _prepare_workspace(tmp_path)
    ctx = _build_ctx(module, ws_file)
    session_dir = active_task_path.parent / ".state" / module.sanitize_task_key_segment(TASK_KEY)
    _write_json(
        session_dir / "active-session-session-2.json",
        {
            "branch": f"feature/{module.sanitize_task_key_segment(TASK_KEY)}/C01/session-2",
            "worktree": str((tmp_path / ".worktrees" / module.sanitize_task_key_segment(TASK_KEY) / "C01" / "session-2").resolve()),
            "base_branch": "master",
            "task_key": TASK_KEY,
            "session_id": "session-2",
        },
    )

    with pytest.raises(module.CardrunContractError) as exc_info:
        module.build_wtimp_dispatch_request(
            ctx,
            "C01",
            active_task_path=active_task_path,
        )

    assert exc_info.value.code == "CARDRUN_CONTEXT_INVALID"


def test_resolve_active_session_worktree_path_rejects_card_mismatch(tmp_path):
    module = _load_kernel_module()
    active_task_path, ws_file, _ = _prepare_workspace(tmp_path)
    ctx = _build_ctx(module, ws_file)
    session_dir = active_task_path.parent / ".state" / module.sanitize_task_key_segment(TASK_KEY)
    _write_json(
        session_dir / "active-session-session-1.json",
        {
            "branch": f"feature/{module.sanitize_task_key_segment(TASK_KEY)}/C02/session-1",
            "worktree": str((tmp_path / ".worktrees" / module.sanitize_task_key_segment(TASK_KEY) / "C02" / "session-1").resolve()),
            "base_branch": "master",
            "task_key": TASK_KEY,
            "session_id": "session-1",
        },
    )

    with pytest.raises(module.CardrunContractError) as exc_info:
        module.build_wtimp_dispatch_request(
            ctx,
            "C01",
            active_task_path=active_task_path,
        )

    assert exc_info.value.code == "CARDRUN_CONTEXT_INVALID"
