"""开发工具接口单元测试。"""

from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import dev_codex_api
from app.api.v1.endpoints.dev_codex_api import (
    CodexExecRequest,
    _build_codex_command,
    _ensure_dev_environment,
    _resolve_workdir,
    run_codex_exec,
)


def test_ensure_dev_environment_block_prod():
    """生产环境应拒绝调用。"""

    with patch.object(dev_codex_api.core_config, "ENV", "prod"):
        with pytest.raises(HTTPException) as exc_info:
            _ensure_dev_environment()
    assert exc_info.value.status_code == 403


def test_resolve_workdir_reject_outside_project():
    """执行目录超出项目根目录应被拒绝。"""

    with patch.object(dev_codex_api.core_config, "PROJECT_ROOT", Path("/tmp/project")):
        with pytest.raises(HTTPException) as exc_info:
            _resolve_workdir("/tmp/other")
    assert exc_info.value.status_code == 400


def test_build_codex_command_with_model():
    """命令构造应包含模型参数。"""

    request = CodexExecRequest(prompt="hi", model="gpt-5.2", sandbox="read-only")
    command = _build_codex_command(request)
    assert command[:4] == ["codex", "-a", "never", "-m"]
    assert "gpt-5.2" in command
    assert "exec" in command


def test_run_codex_exec_success():
    """命令执行成功时返回 ok=true。"""

    request = CodexExecRequest(prompt="hi", sandbox="read-only")
    completed = subprocess.CompletedProcess(args=["codex"], returncode=0, stdout="hi", stderr="")

    with patch.object(dev_codex_api.core_config, "ENV", "dev"), patch(
        "app.api.v1.endpoints.dev_codex_api.subprocess.run",
        return_value=completed,
    ) as mocked_run:
        response = run_codex_exec(request)

    assert response.ok is True
    assert response.exit_code == 0
    assert response.stdout == "hi"
    assert response.dev_only is True
    mocked_run.assert_called_once()


def test_run_codex_exec_timeout():
    """命令超时时返回 exit_code=124。"""

    request = CodexExecRequest(prompt="hi", timeout_sec=10)

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=10, output="part", stderr="too slow")

    with patch.object(dev_codex_api.core_config, "ENV", "dev"), patch(
        "app.api.v1.endpoints.dev_codex_api.subprocess.run",
        side_effect=_raise_timeout,
    ):
        response = run_codex_exec(request)

    assert response.ok is False
    assert response.exit_code == 124
    assert "执行超时" in response.stderr
