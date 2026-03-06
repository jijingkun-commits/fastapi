"""wtimp dispatch bridge 回归测试。"""

from __future__ import annotations

import subprocess
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/coder4/wtimp_dispatch_bridge.py")


def _load_module():
    module_name = f"coder4_wtimp_dispatch_bridge_test_{uuid.uuid4().hex}"
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_build_codex_exec_command_for_cardrun_dispatch():
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="docs/内部参考/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    command = module.build_codex_exec_command(request)

    assert command[:3] == ["codex", "-a", "never"]
    assert "exec" in command
    assert "--skip-git-repo-check" in command
    assert "--sandbox" in command
    assert "workspace-write" in command
    assert "$jjk-wtimp" in command[-1]
    assert "cardrun_dispatch" in command[-1]
    assert request.ws_file in command[-1]


def test_run_dispatch_parses_json_result_and_requires_commit_sha(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="docs/内部参考/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    stdout = """some log\n{"ok": true, "executor": "wtimp", "executor_mode": "cardrun_dispatch", "card_id": "C02", "ws_file": "docs/内部参考/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md", "subagent_id": "wtimp-C02-1", "commit_sha": "abc123def456", "merge_sha": null, "changed_files": ["scripts/coder4/coder4_bootstrap_kernel.py"], "acceptance_results": [{"cmd": "pytest -q tests/unit/test_dummy.py", "exit_code": 0, "summary": "1 passed"}]}\n"""

    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=_args[0] if _args else ["codex"],
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    result = module.run_dispatch(request)

    assert result.ok is True
    assert result.executor == "wtimp"
    assert result.executor_mode == "cardrun_dispatch"
    assert result.card_id == "C02"
    assert result.ws_file == request.ws_file
    assert result.subagent_id == "wtimp-C02-1"
    assert result.commit_sha == "abc123def456"
    assert result.merge_sha is None
    assert result.changed_files == ["scripts/coder4/coder4_bootstrap_kernel.py"]
    assert result.acceptance_results[0]["exit_code"] == 0


def test_run_dispatch_fails_when_commit_sha_missing(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="docs/内部参考/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    stdout = '{"ok": true, "executor": "wtimp", "executor_mode": "cardrun_dispatch", "card_id": "C02", "ws_file": "docs/内部参考/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md", "subagent_id": "wtimp-C02-1", "commit_sha": "", "merge_sha": null, "changed_files": [], "acceptance_results": []}'

    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=_args[0] if _args else ["codex"],
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_NO_COMMIT_EVIDENCE"
    assert exc_info.value.details["card_id"] == "C02"


def test_run_dispatch_maps_nonzero_exit_to_subagent_failed(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="docs/内部参考/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=_args[0] if _args else ["codex"],
            returncode=1,
            stdout="bridge failed",
            stderr="boom",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_SUBAGENT_FAILED"
    assert exc_info.value.details["exit_code"] == 1
