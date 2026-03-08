"""开发期定向 pytest 入口回归测试。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


SCRIPT_PATH = Path("scripts/pytest_targeted.sh")
ERROR_MARKER = "PYTEST_TARGETED_COVERAGE_MIXED"



def _make_fake_python(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env bash\nprintf '%s\n' \"$*\" > \"${PYTEST_ARGS_LOG:?}\"\nexit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)



def _run_targeted(repo_root: Path, args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), "--repo-root", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        env=command_env,
    )



def test_pytest_targeted_injects_no_cov_and_forwards_pytest_args(tmp_path: Path):
    fake_python = tmp_path / "runtime-venv" / "bin" / "python"
    args_log = tmp_path / "pytest-args.log"
    _make_fake_python(fake_python)

    result = _run_targeted(
        tmp_path,
        ["tests/unit/test_sample.py", "-q"],
        {
            "VK_RUNTIME_VENV": "runtime-venv",
            "PYTEST_ARGS_LOG": str(args_log),
        },
    )

    assert result.returncode == 0, result.stderr
    assert args_log.read_text(encoding="utf-8").strip() == "-m pytest --no-cov tests/unit/test_sample.py -q"



def test_pytest_targeted_rejects_cov_flags(tmp_path: Path):
    fake_python = tmp_path / "runtime-venv" / "bin" / "python"
    args_log = tmp_path / "pytest-args.log"
    _make_fake_python(fake_python)

    result = _run_targeted(
        tmp_path,
        ["tests/unit/test_sample.py", "--cov=app"],
        {
            "VK_RUNTIME_VENV": "runtime-venv",
            "PYTEST_ARGS_LOG": str(args_log),
        },
    )

    assert result.returncode != 0
    assert ERROR_MARKER in result.stderr
    assert not args_log.exists()
