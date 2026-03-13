"""jjk_deleteworktree 脚本回归测试。"""

from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT_PATH = (Path(__file__).resolve().parents[2] / "scripts" / "jjk_deleteworktree.sh")


def _run_command(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = _run_command(cwd, ["git", *args])
    assert result.returncode == 0, result.stderr
    return result


def _init_repo(repo_root: Path) -> None:
    repo_root.mkdir()
    _git(repo_root, "init", "-b", "master")
    _git(repo_root, "config", "user.name", "Codex Test")
    _git(repo_root, "config", "user.email", "codex@example.com")
    (repo_root / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo_root, "add", "README.md")
    _git(repo_root, "commit", "-m", "base")


def _create_feature_worktree(repo_root: Path, feature_wt: Path) -> None:
    _git(repo_root, "worktree", "add", "-b", "codex/delete-me", str(feature_wt), "master")
    (feature_wt / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(feature_wt, "add", "feature.txt")
    _git(feature_wt, "commit", "-m", "feature")


def test_deleteworktree_uses_base_branch_worktree_context(tmp_path: Path):
    repo_root = tmp_path / "repo"
    master_ctx = tmp_path / "master-ctx"
    feature_wt = tmp_path / "feature-wt"

    _init_repo(repo_root)
    _git(repo_root, "branch", "busy")
    _git(repo_root, "checkout", "busy")
    _git(repo_root, "worktree", "add", str(master_ctx), "master")
    _create_feature_worktree(repo_root, feature_wt)
    _git(master_ctx, "merge", "--no-ff", "codex/delete-me", "-m", "merge feature")

    script_result = _run_command(feature_wt, ["bash", str(SCRIPT_PATH)])

    assert script_result.returncode == 0, script_result.stderr
    assert f"git -C {master_ctx.resolve()}" in script_result.stdout
    assert " branch -d codex/delete-me" in script_result.stdout
    assert _git(repo_root, "branch", "--show-current").stdout.strip() == "busy"

    delete_result = _run_command(tmp_path, ["bash", "-lc", script_result.stdout.strip()])

    assert delete_result.returncode == 0, delete_result.stderr
    assert not feature_wt.exists()
    assert _git(repo_root, "branch", "--list", "codex/delete-me").stdout.strip() == ""


def test_deleteworktree_fails_without_base_branch_worktree_context(tmp_path: Path):
    repo_root = tmp_path / "repo"
    feature_wt = tmp_path / "feature-wt"

    _init_repo(repo_root)
    _create_feature_worktree(repo_root, feature_wt)
    _git(repo_root, "merge", "--no-ff", "codex/delete-me", "-m", "merge feature")
    _git(repo_root, "branch", "busy")
    _git(repo_root, "checkout", "busy")

    script_result = _run_command(feature_wt, ["bash", str(SCRIPT_PATH)])

    assert script_result.returncode != 0
    assert "DELETE_WORKTREE_BASE_CONTEXT_MISSING" in script_result.stderr
