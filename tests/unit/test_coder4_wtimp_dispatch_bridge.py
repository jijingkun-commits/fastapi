"""wtimp dispatch bridge 回归测试。"""

from __future__ import annotations

import subprocess
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import signal

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


class _FakePopenProcess:
    def __init__(
        self,
        *,
        pid: int = 43210,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
        communicate_exc: Exception | None = None,
    ) -> None:
        self.pid = pid
        self._stdout = stdout
        self._stderr = stderr
        self._final_returncode = returncode
        self._communicate_exc = communicate_exc
        self.returncode = None if communicate_exc is not None else returncode

    def communicate(self, timeout: int | None = None):
        if self._communicate_exc is not None:
            raise self._communicate_exc
        self.returncode = self._final_returncode
        return self._stdout, self._stderr

    def wait(self, timeout: int | None = None):
        if self.returncode is None:
            self.returncode = self._final_returncode
        return self.returncode


def _patch_popen(monkeypatch, module, process: _FakePopenProcess):
    popen_calls: dict[str, object] = {}

    def _legacy_run(*_args, **_kwargs):
        raise AssertionError("legacy subprocess.run should not be used")

    def _fake_popen(command, **kwargs):
        popen_calls["command"] = command
        popen_calls["kwargs"] = kwargs
        return process

    monkeypatch.setattr(module.subprocess, "run", _legacy_run)
    monkeypatch.setattr(module.subprocess, "Popen", _fake_popen, raising=False)
    return popen_calls


def test_build_codex_exec_command_for_cardrun_dispatch():
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
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
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    stdout = """some log\n{"ok": true, "executor": "wtimp", "executor_mode": "cardrun_dispatch", "card_id": "C02", "ws_file": "workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md", "subagent_id": "wtimp-C02-1", "commit_sha": "abc123def456", "merge_sha": null, "changed_files": ["scripts/coder4/coder4_bootstrap_kernel.py"], "acceptance_results": [{"kind": "chat_db", "cmd": "pytest -q tests/unit/test_dummy.py", "exit_code": 0, "summary": "1 passed"}], "evidence_satisfied": true}\n"""

    process = _FakePopenProcess(stdout=stdout, stderr="", returncode=0)
    _patch_popen(monkeypatch, module, process)

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
    assert result.acceptance_results[0]["kind"] == "chat_db"
    assert result.acceptance_results[0]["exit_code"] == 0
    assert result.evidence_satisfied is True


def test_run_dispatch_fails_when_commit_sha_missing(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    stdout = '{"ok": true, "executor": "wtimp", "executor_mode": "cardrun_dispatch", "card_id": "C02", "ws_file": "workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md", "subagent_id": "wtimp-C02-1", "commit_sha": "", "merge_sha": null, "changed_files": [], "acceptance_results": [], "evidence_satisfied": true}'

    process = _FakePopenProcess(stdout=stdout, stderr="", returncode=0)
    _patch_popen(monkeypatch, module, process)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_NO_COMMIT_EVIDENCE"
    assert exc_info.value.details["card_id"] == "C02"


def test_run_dispatch_maps_nonzero_exit_to_subagent_failed(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    process = _FakePopenProcess(stdout="bridge failed", stderr="boom", returncode=1)
    _patch_popen(monkeypatch, module, process)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_SUBAGENT_FAILED"
    assert exc_info.value.details["exit_code"] == 1



def test_run_dispatch_maps_timeout_to_subagent_failed(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
        timeout_seconds=12,
    )

    process = _FakePopenProcess(
        communicate_exc=subprocess.TimeoutExpired(
            cmd=["codex"],
            timeout=12,
            output="partial stdout",
            stderr="partial stderr",
        )
    )
    _patch_popen(monkeypatch, module, process)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_SUBAGENT_FAILED"
    assert exc_info.value.details["timeout_seconds"] == 12
    assert exc_info.value.details["stdout_preview"] == "partial stdout"
    assert exc_info.value.details["stderr_preview"] == "partial stderr"


def test_run_dispatch_timeout_terminates_process_group(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
        timeout_seconds=12,
    )

    process = _FakePopenProcess(
        communicate_exc=subprocess.TimeoutExpired(
            cmd=["codex"],
            timeout=12,
            output="partial stdout",
            stderr="partial stderr",
        )
    )
    popen_calls = _patch_popen(monkeypatch, module, process)
    cleanup_calls: list[tuple[int, object]] = []
    monkeypatch.setattr(
        module,
        "os",
        SimpleNamespace(killpg=lambda pgid, sig: cleanup_calls.append((pgid, sig))),
        raising=False,
    )
    monkeypatch.setattr(module, "signal", signal, raising=False)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert popen_calls["kwargs"]["start_new_session"] is True
    assert cleanup_calls
    assert cleanup_calls[0][0] == process.pid
    assert cleanup_calls[0][1] == signal.SIGTERM
    assert exc_info.value.code == "CARDRUN_SUBAGENT_FAILED"
    assert exc_info.value.details["session_cleanup"]["attempted"] is True
    assert exc_info.value.details["session_cleanup"]["signals"][0] == "SIGTERM"


def test_run_dispatch_rejects_non_contract_json_log_object(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    process = _FakePopenProcess(stdout='log line\n{"note": "progress"}\n', stderr="", returncode=0)
    _patch_popen(monkeypatch, module, process)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_EXECUTION_RESULT_INVALID"


def test_run_dispatch_rejects_multiple_contract_payloads(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    stdout = (
        '{"ok": true, "executor": "wtimp", "executor_mode": "cardrun_dispatch", '
        '"card_id": "C02", "ws_file": "workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md", '
        '"subagent_id": "wtimp-C02-1", "commit_sha": "abc123", "merge_sha": null, '
        '"changed_files": ["scripts/coder4/coder4_bootstrap_kernel.py"], "acceptance_results": [], "evidence_satisfied": true}'
        '\nnoise\n'
        '{"ok": true, "executor": "wtimp", "executor_mode": "cardrun_dispatch", '
        '"card_id": "C02", "ws_file": "workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md", '
        '"subagent_id": "wtimp-C02-2", "commit_sha": "def456", "merge_sha": null, '
        '"changed_files": ["scripts/coder4/wtimp_dispatch_bridge.py"], "acceptance_results": [], "evidence_satisfied": true}'
    )
    process = _FakePopenProcess(stdout=stdout, stderr="", returncode=0)
    _patch_popen(monkeypatch, module, process)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_EXECUTION_RESULT_INVALID"



def test_run_dispatch_rejects_missing_evidence_satisfied(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    stdout = (
        '{"ok": true, "executor": "wtimp", "executor_mode": "cardrun_dispatch", '
        '"card_id": "C02", "ws_file": "workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md", '
        '"subagent_id": "wtimp-C02-1", "commit_sha": "abc123", "merge_sha": null, '
        '"changed_files": [], "acceptance_results": []}'
    )

    process = _FakePopenProcess(stdout=stdout, stderr="", returncode=0)
    _patch_popen(monkeypatch, module, process)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_EXECUTION_RESULT_INVALID"


def test_run_dispatch_rejects_untyped_acceptance_results(monkeypatch):
    module = _load_module()
    request = module.WtimpDispatchRequest(
        task_key="PP-20260306-CARDRUN-WTIMP",
        card_id="C02",
        ws_file="workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md",
        worktree_path="/tmp/worktree-c02",
        executor_mode="cardrun_dispatch",
    )

    stdout = (
        '{"ok": true, "executor": "wtimp", "executor_mode": "cardrun_dispatch", '
        '"card_id": "C02", "ws_file": "workdocs/任务拆解/2026-03-06_xxx/workstreams/WS-C02.md", '
        '"subagent_id": "wtimp-C02-1", "commit_sha": "abc123", "merge_sha": null, '
        '"changed_files": [], "acceptance_results": [{"cmd": "pytest -q", "exit_code": 0, "summary": "ok"}], '
        '"evidence_satisfied": true}'
    )

    process = _FakePopenProcess(stdout=stdout, stderr="", returncode=0)
    _patch_popen(monkeypatch, module, process)

    with pytest.raises(module.WtimpDispatchError) as exc_info:
        module.run_dispatch(request)

    assert exc_info.value.code == "CARDRUN_EXECUTION_RESULT_INVALID"
