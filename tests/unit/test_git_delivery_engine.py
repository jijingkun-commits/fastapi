"""git delivery engine 回归测试。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


SOURCE_SCRIPT = Path("scripts/coder4/git-delivery-engine.sh")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("# fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init fixture"], cwd=tmp_path, check=True, capture_output=True)


def _copy_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "scripts" / "coder4" / "git-delivery-engine.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_SCRIPT, script_path)
    script_path.chmod(0o755)
    return script_path


def _create_source_worktree(tmp_path: Path, branch: str, rel_path: str = ".worktrees/source") -> Path:
    worktree_path = tmp_path / rel_path
    subprocess.run(["git", "worktree", "add", "-b", branch, str(worktree_path), "master"], cwd=tmp_path, check=True, capture_output=True)
    return worktree_path


def _engine_json(result: subprocess.CompletedProcess[str]) -> dict:
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines, f"stdout is empty: stderr={result.stderr}"
    return json.loads(lines[-1])


def _run_engine(script_path: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(script_path), *args], cwd=cwd, env=os.environ, text=True, capture_output=True)


def test_delivery_prepare_base_reuses_existing_master_checkout(tmp_path: Path):
    _init_repo(tmp_path)
    script_path = _copy_script(tmp_path)
    worktree_path = _create_source_worktree(tmp_path, "codex/test-prepare-base")

    result = _run_engine(
        script_path,
        "prepare-base",
        "--source-branch",
        "codex/test-prepare-base",
        "--source-worktree",
        str(worktree_path),
        "--base-branch",
        "master",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    payload = _engine_json(result)
    assert payload["status"] == "base_ready"
    assert payload["base_checkout"] == str(tmp_path)
    assert payload["created_by_engine"] is False


def test_delivery_prepare_base_creates_temp_checkout_when_master_not_checked_out(tmp_path: Path):
    _init_repo(tmp_path)
    script_path = _copy_script(tmp_path)
    subprocess.run(["git", "checkout", "-b", "dev-base"], cwd=tmp_path, check=True, capture_output=True)
    worktree_path = _create_source_worktree(tmp_path, "codex/test-prepare-base-temp")

    result = _run_engine(
        script_path,
        "prepare-base",
        "--source-branch",
        "codex/test-prepare-base-temp",
        "--source-worktree",
        str(worktree_path),
        "--base-branch",
        "master",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    payload = _engine_json(result)
    assert payload["status"] == "base_ready"
    assert payload["created_by_engine"] is True
    assert payload["base_checkout"] != str(tmp_path)
    assert Path(payload["base_checkout"]).exists()

    branch_name = subprocess.run(["git", "branch", "--show-current"], cwd=payload["base_checkout"], text=True, capture_output=True, check=True)
    assert branch_name.stdout.strip() == "master"


def test_delivery_merge_merges_feature_into_master(tmp_path: Path):
    _init_repo(tmp_path)
    script_path = _copy_script(tmp_path)
    branch = "codex/test-merge"
    worktree_path = _create_source_worktree(tmp_path, branch)

    (worktree_path / "README.md").write_text("# fixture\nfeature merge change\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feature merge change"], cwd=worktree_path, check=True, capture_output=True)

    result = _run_engine(
        script_path,
        "merge",
        "--source-branch",
        branch,
        "--source-worktree",
        str(worktree_path),
        "--base-branch",
        "master",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    payload = _engine_json(result)
    assert payload["status"] == "merged"
    assert payload["source_branch"] == branch
    assert "feature merge change" in (tmp_path / "README.md").read_text(encoding="utf-8")
    assert payload["base_checkout"] == str(tmp_path)
    assert payload["merge_commit"]


def test_delivery_merge_rebases_when_base_branch_advanced(tmp_path: Path):
    _init_repo(tmp_path)
    script_path = _copy_script(tmp_path)
    branch = "codex/test-rebase-success"
    worktree_path = _create_source_worktree(tmp_path, branch)

    _write_text(worktree_path / "feature.txt", "feature\n")
    subprocess.run(["git", "add", "feature.txt"], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feature change"], cwd=worktree_path, check=True, capture_output=True)

    _write_text(tmp_path / "base.txt", "base\n")
    subprocess.run(["git", "add", "base.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "base advance"], cwd=tmp_path, check=True, capture_output=True)

    result = _run_engine(
        script_path,
        "merge",
        "--source-branch",
        branch,
        "--source-worktree",
        str(worktree_path),
        "--base-branch",
        "master",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    payload = _engine_json(result)
    assert payload["status"] == "merged"
    assert payload["rebase_performed"] is True
    assert (tmp_path / "feature.txt").read_text(encoding="utf-8") == "feature\n"
    assert (tmp_path / "base.txt").read_text(encoding="utf-8") == "base\n"


def test_delivery_merge_keeps_rebase_in_progress_for_continue_or_abort(tmp_path: Path):
    _init_repo(tmp_path)
    script_path = _copy_script(tmp_path)
    branch = "codex/test-rebase-conflict"
    worktree_path = _create_source_worktree(tmp_path, branch)

    (worktree_path / "README.md").write_text("# feature side\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feature readme"], cwd=worktree_path, check=True, capture_output=True)

    (tmp_path / "README.md").write_text("# base side\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "base readme"], cwd=tmp_path, check=True, capture_output=True)

    result = _run_engine(
        script_path,
        "merge",
        "--source-branch",
        branch,
        "--source-worktree",
        str(worktree_path),
        "--base-branch",
        "master",
        cwd=tmp_path,
    )

    assert result.returncode != 0
    payload = _engine_json(result)
    assert payload["status"] == "rebase_conflict"
    assert payload["source_branch"] == branch

    status_result = _run_engine(
        script_path,
        "status",
        "--source-branch",
        branch,
        "--source-worktree",
        str(worktree_path),
        cwd=tmp_path,
    )
    assert status_result.returncode == 0, status_result.stderr
    status_payload = _engine_json(status_result)
    assert status_payload["status"] == "rebase_conflict"
    assert status_payload["source_worktree"] == str(worktree_path)

    rebase_head = subprocess.run(["git", "rev-parse", "--verify", "REBASE_HEAD"], cwd=worktree_path, text=True, capture_output=True)
    assert rebase_head.returncode == 0

    abort_result = _run_engine(
        script_path,
        "abort",
        "--source-branch",
        branch,
        "--source-worktree",
        str(worktree_path),
        cwd=tmp_path,
    )
    assert abort_result.returncode == 0, abort_result.stderr
    abort_payload = _engine_json(abort_result)
    assert abort_payload["status"] == "aborted"

    idle_result = _run_engine(
        script_path,
        "status",
        "--source-branch",
        branch,
        "--source-worktree",
        str(worktree_path),
        cwd=tmp_path,
    )
    assert idle_result.returncode == 0, idle_result.stderr
    idle_payload = _engine_json(idle_result)
    assert idle_payload["status"] == "idle"


def test_delivery_continue_resumes_rebase_and_completes_merge(tmp_path: Path):
    _init_repo(tmp_path)
    script_path = _copy_script(tmp_path)
    branch = "codex/test-rebase-continue"
    worktree_path = _create_source_worktree(tmp_path, branch)

    (worktree_path / "README.md").write_text("# feature side\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feature readme"], cwd=worktree_path, check=True, capture_output=True)

    (tmp_path / "README.md").write_text("# base side\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "base readme"], cwd=tmp_path, check=True, capture_output=True)

    first_result = _run_engine(
        script_path,
        "merge",
        "--source-branch",
        branch,
        "--source-worktree",
        str(worktree_path),
        "--base-branch",
        "master",
        cwd=tmp_path,
    )
    assert first_result.returncode != 0
    assert _engine_json(first_result)["status"] == "rebase_conflict"

    (worktree_path / "README.md").write_text("# base side\n# feature side\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=worktree_path, check=True, capture_output=True)

    continue_result = _run_engine(
        script_path,
        "continue",
        "--source-branch",
        branch,
        "--source-worktree",
        str(worktree_path),
        cwd=tmp_path,
    )

    assert continue_result.returncode == 0, continue_result.stderr
    continue_payload = _engine_json(continue_result)
    assert continue_payload["status"] == "merged"
    assert "# feature side" in (tmp_path / "README.md").read_text(encoding="utf-8")
