"""wt-flow verified 状态回归测试。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


SOURCE_SCRIPT = Path("scripts/coder4/wt-flow.sh")
TASK_SPLIT_DIR = "2026-03-07_verified_state_machine"
TASK_KEY = "PP-20260307-VERIFIED-STATE"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sanitize_task_key_segment(task_key: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in task_key).strip("._")


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("# fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init fixture"], cwd=tmp_path, check=True, capture_output=True)


def _copy_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "scripts" / "coder4" / "wt-flow.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_SCRIPT, script_path)
    script_path.chmod(0o755)
    return script_path


def _prepare_task_fixture(tmp_path: Path, *, state_payload: dict) -> tuple[Path, Path, Path, Path]:
    _init_repo(tmp_path)
    script_path = _copy_script(tmp_path)

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
    _write_json(
        task_dir / "vk_cards.json",
        {
            "execution_mode": "serial",
            "card_order": ["C01", "C02"],
            "cards": [
                {"card_id": "C01", "acceptance_checks": []},
                {"card_id": "C02", "acceptance_checks": []},
            ],
        },
    )

    task_state_root = task_dir / ".state" / _sanitize_task_key_segment(TASK_KEY)
    state_file = task_state_root / "task-runner-state.json"
    _write_json(state_file, state_payload)
    return script_path, active_task_path, task_state_root, state_file


def test_wt_flow_next_blocks_when_verified_card_exists(tmp_path: Path):
    script_path, active_task_path, task_state_root, _ = _prepare_task_fixture(
        tmp_path,
        state_payload={
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "card_order": ["C01", "C02"],
            "current_card": "C01",
            "card_status_map": {"C01": "verified", "C02": "todo"},
        },
    )

    result = subprocess.run(
        ["bash", str(script_path), "next", f"--state-dir={task_state_root.parent}"],
        cwd=tmp_path,
        env=os.environ
        | {
            "WT_FLOW_ACTIVE_TASK_FILE": str(active_task_path),
        },
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "BLOCKED" in result.stdout
    assert "C01" in result.stdout


def test_wt_flow_verify_allows_rg_acceptance_check(tmp_path: Path):
    script_path, active_task_path, task_state_root, state_file = _prepare_task_fixture(
        tmp_path,
        state_payload={
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "card_order": ["C01", "C02"],
            "current_card": "C01",
            "card_status_map": {"C01": "inprogress", "C02": "todo"},
        },
    )

    cards_file = tmp_path / "docs" / "内部参考" / "任务拆解" / TASK_SPLIT_DIR / "vk_cards.json"
    cards_payload = json.loads(cards_file.read_text(encoding="utf-8"))
    cards_payload["cards"][0]["acceptance_checks"] = ['rg -n "fixture" README.md']
    _write_json(cards_file, cards_payload)

    sanitized = _sanitize_task_key_segment(TASK_KEY)
    session_id = "session-verify-rg"
    worktree_path = tmp_path / ".worktrees" / sanitized / "C01" / session_id
    worktree_path.mkdir(parents=True, exist_ok=True)
    (worktree_path / "README.md").write_text("fixture\n", encoding="utf-8")
    _write_json(
        task_state_root / f"active-session-{session_id}.json",
        {
            "branch": f"feature/{sanitized}/C01/{session_id}",
            "worktree": str(worktree_path),
            "base_branch": "master",
            "task_key": TASK_KEY,
            "session_id": session_id,
        },
    )

    result = subprocess.run(
        ["bash", str(script_path), "verify", "C01", f"--state-dir={task_state_root.parent}"],
        cwd=tmp_path,
        env=os.environ
        | {
            "WT_FLOW_ACTIVE_TASK_FILE": str(active_task_path),
            "WT_FLOW_SESSION_ID": session_id,
        },
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    state_payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert state_payload["card_status_map"]["C01"] == "verified"
    assert state_payload["gate_results"]["C01"]["passed"] is True
    assert state_payload["gate_results"]["C01"]["evidence"][0]["prefix"] == "rg"


def test_wt_flow_merge_requires_verified_state_not_done(tmp_path: Path):
    script_path, active_task_path, task_state_root, _ = _prepare_task_fixture(
        tmp_path,
        state_payload={
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "card_order": ["C01", "C02"],
            "current_card": "C01",
            "card_status_map": {"C01": "done", "C02": "todo"},
        },
    )

    sanitized = _sanitize_task_key_segment(TASK_KEY)
    session_id = "session-1"
    worktree_path = tmp_path / ".worktrees" / sanitized / "C01" / session_id
    worktree_path.mkdir(parents=True, exist_ok=True)
    _write_json(
        task_state_root / f"active-session-{session_id}.json",
        {
            "branch": f"feature/{sanitized}/C01/{session_id}",
            "worktree": str(worktree_path),
            "base_branch": "master",
            "task_key": TASK_KEY,
            "session_id": session_id,
        },
    )

    result = subprocess.run(
        ["bash", str(script_path), "merge", f"--state-dir={task_state_root.parent}"],
        cwd=tmp_path,
        env=os.environ
        | {
            "WT_FLOW_ACTIVE_TASK_FILE": str(active_task_path),
            "WT_FLOW_SESSION_ID": session_id,
        },
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "当前状态=done" in result.stderr
    assert "verified" in result.stderr



def test_wt_flow_merge_from_card_worktree_uses_common_repo_driver(tmp_path: Path):
    script_path, active_task_path, task_state_root, state_file = _prepare_task_fixture(
        tmp_path,
        state_payload={
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "card_order": ["C01", "C02"],
            "current_card": "C01",
            "card_status_map": {"C01": "verified", "C02": "todo"},
        },
    )

    sanitized = _sanitize_task_key_segment(TASK_KEY)
    session_id = "session-merge-common-root"
    branch = f"feature/{sanitized}/C01/{session_id}"
    worktree_path = tmp_path / ".worktrees" / sanitized / "C01" / session_id
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), "master"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    readme_path = worktree_path / "README.md"
    readme_path.write_text("# fixture\nfeature merge change\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feature merge change"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )
    _write_json(
        task_state_root / f"active-session-{session_id}.json",
        {
            "branch": branch,
            "worktree": str(worktree_path),
            "base_branch": "master",
            "task_key": TASK_KEY,
            "session_id": session_id,
        },
    )

    result = subprocess.run(
        ["bash", str(script_path), "merge", "--no-cleanup", f"--state-dir={task_state_root.parent}"],
        cwd=worktree_path,
        env=os.environ
        | {
            "WT_FLOW_ACTIVE_TASK_FILE": str(active_task_path),
            "WT_FLOW_SESSION_ID": session_id,
        },
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert "feature merge change" in (tmp_path / "README.md").read_text(encoding="utf-8")
    state_payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert state_payload["card_status_map"]["C01"] == "done"
    assert state_payload["merge_results"]["C01"]["merged"] is True
    assert state_payload["merge_results"]["C01"]["branch"] == branch



def test_wt_flow_merge_from_card_worktree_cleans_up_with_common_repo_driver(tmp_path: Path):
    script_path, active_task_path, task_state_root, state_file = _prepare_task_fixture(
        tmp_path,
        state_payload={
            "schema_version": "1.0.0",
            "task_key": TASK_KEY,
            "execution_mode": "serial",
            "card_order": ["C01", "C02"],
            "current_card": "C01",
            "card_status_map": {"C01": "verified", "C02": "todo"},
        },
    )

    sanitized = _sanitize_task_key_segment(TASK_KEY)
    session_id = "session-merge-cleanup"
    branch = f"feature/{sanitized}/C01/{session_id}"
    worktree_path = tmp_path / ".worktrees" / sanitized / "C01" / session_id
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), "master"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (worktree_path / "README.md").write_text("# fixture\ncleanup merge change\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "cleanup merge change"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )
    session_file = task_state_root / f"active-session-{session_id}.json"
    _write_json(
        session_file,
        {
            "branch": branch,
            "worktree": str(worktree_path),
            "base_branch": "master",
            "task_key": TASK_KEY,
            "session_id": session_id,
        },
    )

    result = subprocess.run(
        ["bash", str(script_path), "merge", f"--state-dir={task_state_root.parent}"],
        cwd=worktree_path,
        env=os.environ
        | {
            "WT_FLOW_ACTIVE_TASK_FILE": str(active_task_path),
            "WT_FLOW_SESSION_ID": session_id,
        },
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert not worktree_path.exists()
    assert not session_file.exists()
    branch_exists = subprocess.run(
        ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert branch_exists.returncode != 0
    state_payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert state_payload["card_status_map"]["C01"] == "done"
