"""integration gate 运行态 state_dir 解析回归测试。"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path("scripts/check_workflow_contract.py")


def _load_module():
    module_name = f"check_workflow_contract_state_dir_test_{uuid.uuid4().hex}"
    scripts_dir = SCRIPT_PATH.parent.resolve()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _git(cwd: Path, *args: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Codex",
            "GIT_AUTHOR_EMAIL": "codex@example.com",
            "GIT_COMMITTER_NAME": "Codex",
            "GIT_COMMITTER_EMAIL": "codex@example.com",
        }
    )
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)


def test_resolve_integration_state_dir_prefers_common_repo_state_for_worktree(tmp_path):
    module = _load_module()

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _git(repo_root, "init", "-b", "master")

    task_rel = Path("workdocs/任务拆解/2026-03-07_workflow-gate")
    (repo_root / task_rel).mkdir(parents=True, exist_ok=True)
    (repo_root / task_rel / "contracts").mkdir(parents=True, exist_ok=True)
    (repo_root / task_rel / "contracts" / "vk_cards.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(repo_root, "add", "README.md", str(task_rel / "contracts" / "vk_cards.json"))
    _git(repo_root, "commit", "-m", "init")

    worktree_root = repo_root / ".worktrees" / "G01" / "session"
    _git(repo_root, "worktree", "add", "-b", "feature/test-g01", str(worktree_root), "HEAD")

    expected = (repo_root / ".artifacts" / "states" / "task_splits" / "2026-03-07_workflow-gate").resolve()
    resolved = module._resolve_integration_state_dir(
        repo_root=worktree_root,
        task_split_dir=(worktree_root / task_rel),
        raw_state_dir=".state",
    )

    assert resolved == expected
