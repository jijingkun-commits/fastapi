"""仓库测试解释器解析脚本回归测试。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


SCRIPT_PATH = Path("scripts/repo_python.sh")


def _make_executable(path: Path, content: str = "#!/usr/bin/env bash\nexit 0\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)



def _run_repo_python(repo_root: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), "--repo-root", str(repo_root)],
        check=False,
        capture_output=True,
        text=True,
        env=command_env,
    )



def test_repo_python_prefers_vk_runtime_venv(tmp_path: Path):
    runtime_python = tmp_path / "runtime-venv" / "bin" / "python"
    _make_executable(runtime_python)
    _make_executable(tmp_path / "venv" / "bin" / "python")

    result = _run_repo_python(tmp_path, {"VK_RUNTIME_VENV": "runtime-venv"})

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(runtime_python)



def test_repo_python_prefers_repo_venv_before_dotvenv_and_vibe(tmp_path: Path):
    venv_python = tmp_path / "venv" / "bin" / "python"
    _make_executable(venv_python)
    _make_executable(tmp_path / ".venv" / "bin" / "python")
    _make_executable(tmp_path / ".vibe" / "venv" / "bin" / "python")

    result = _run_repo_python(tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(venv_python)



def test_repo_python_falls_back_to_system_python_when_repo_venv_missing(tmp_path: Path):
    fake_bin = tmp_path / "fake-bin"
    system_python = fake_bin / "python3"
    _make_executable(system_python)

    result = _run_repo_python(tmp_path, {"PATH": f"{fake_bin}:{os.environ['PATH']}"})

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(system_python)
