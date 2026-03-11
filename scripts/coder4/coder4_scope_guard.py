#!/usr/bin/env python3
"""Scope guard entry: delegate scope request handling to set_active_task."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from task_split_paths import DEFAULT_ACTIVE_TASK_INDEX_PATH, detect_repo_root, iter_task_split_paths, resolve_task_split_paths

DEFAULT_SCOPE_REQUEST_FILENAME = "coder4_scope_request.json"
DEFAULT_SET_ACTIVE_SCRIPT = Path("scripts/set_active_task.py")


def resolve_repo_root(raw_repo_root: str) -> Path:
    value = str(raw_repo_root or "").strip()
    if value:
        path = Path(value).expanduser()
        return (Path.cwd() / path).resolve() if not path.is_absolute() else path.resolve()
    return detect_repo_root(Path(__file__))


def resolve_default_task_split_dir(repo_root: Path, raw_task_split_dir: str) -> Path:
    explicit = str(raw_task_split_dir or "").strip()
    if explicit:
        return resolve_task_split_paths(repo_root, explicit, must_exist=False).canonical_task_split_dir

    env_split = str(os.getenv("WT_FLOW_TASK_SPLIT_DIR") or "").strip()
    if env_split:
        return resolve_task_split_paths(repo_root, env_split, must_exist=False).canonical_task_split_dir

    candidates = [item.canonical_task_split_dir for item in iter_task_split_paths(repo_root) if item.active_task_file.is_file()]
    if not candidates:
        raise ValueError("未找到任务级 _active_task.json，请显式传 --task-split-dir 或 --scope-request")
    if len(candidates) > 1:
        raise ValueError(f"检测到多个任务级 _active_task.json（{len(candidates)} 个），请显式传 --task-split-dir 或 --scope-request")
    return candidates[0]


def resolve_scope_request_path(args: argparse.Namespace, repo_root: Path) -> Path:
    explicit = str(args.scope_request or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return (repo_root / path).resolve() if not path.is_absolute() else path.resolve()

    task_split_dir = resolve_default_task_split_dir(repo_root, args.task_split_dir)
    locator = resolve_task_split_paths(repo_root, task_split_dir.name, must_exist=False)
    return (locator.runtime_task_split_dir / DEFAULT_SCOPE_REQUEST_FILENAME).resolve()


def resolve_set_active_script(repo_root: Path, raw_path: str) -> Path:
    value = str(raw_path or "").strip()
    path = Path(value).expanduser() if value else DEFAULT_SET_ACTIVE_SCRIPT
    return (repo_root / path).resolve() if not path.is_absolute() else path.resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guard for coder4 scope switching using a pending request file.")
    parser.add_argument("--repo-root", default="", help="Repository root path.")
    parser.add_argument("--scope-request", default="", help="Path to scope request json.")
    parser.add_argument("--set-active-script", default=str(DEFAULT_SET_ACTIVE_SCRIPT), help="Path to set_active_task.py")
    parser.add_argument("--task-split-dir", default="", help="Optional fallback task split dir.")
    parser.add_argument("--project-id", default="", help="Optional fallback project id.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root(args.repo_root)
    scope_request_path = resolve_scope_request_path(args, repo_root)
    set_active_script = resolve_set_active_script(repo_root, args.set_active_script)
    command = [
        sys.executable,
        str(set_active_script),
        "--repo-root",
        str(repo_root),
        "--scope-request",
        str(scope_request_path),
        "--active-task-path",
        DEFAULT_ACTIVE_TASK_INDEX_PATH,
    ]
    if str(args.task_split_dir or "").strip():
        command.extend(["--task-split-dir", str(args.task_split_dir).strip()])
    if str(args.project_id or "").strip():
        command.extend(["--project-id", str(args.project_id).strip()])
    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
