#!/usr/bin/env python3
"""Scope guard entry: delegate scope request handling to set_active_task."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


TASK_SPLIT_BASE = Path("docs/内部参考/任务拆解")
TASK_ACTIVE_FILENAME = "_active_task.json"
DEFAULT_SCOPE_REQUEST_FILENAME = "coder4_scope_request.json"
DEFAULT_SET_ACTIVE_SCRIPT = Path("scripts/set_active_task.py")


def detect_repo_root(start: Path) -> Path:
    resolved = start.resolve()
    for ancestor in (resolved, *resolved.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return resolved.parents[2]


def resolve_repo_root(raw_repo_root: str) -> Path:
    value = str(raw_repo_root or "").strip()
    if value:
        repo_root = Path(value).expanduser()
        if not repo_root.is_absolute():
            repo_root = (Path.cwd() / repo_root).resolve()
        else:
            repo_root = repo_root.resolve()
        return repo_root
    return detect_repo_root(Path(__file__))


def resolve_task_split_dir(repo_root: Path, raw_task_split_dir: str) -> Path:
    raw = str(raw_task_split_dir or "").strip()
    if not raw:
        raise ValueError("missing task_split_dir")
    direct = Path(raw).expanduser()
    candidates: list[Path] = []
    if direct.is_absolute():
        candidates.append(direct)
    else:
        candidates.extend(
            [
                (repo_root / raw),
                (repo_root / TASK_SPLIT_BASE / raw),
            ]
        )
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    joined = " | ".join(str(path) for path in candidates)
    raise ValueError(f"cannot resolve task_split_dir: {raw}; candidates={joined}")


def resolve_default_task_split_dir(repo_root: Path, raw_task_split_dir: str) -> Path:
    explicit = str(raw_task_split_dir or "").strip()
    if explicit:
        return resolve_task_split_dir(repo_root, explicit)

    env_split = str(os.getenv("WT_FLOW_TASK_SPLIT_DIR") or "").strip()
    if env_split:
        return resolve_task_split_dir(repo_root, env_split)

    split_root = repo_root / TASK_SPLIT_BASE
    candidates = sorted(path.parent.resolve() for path in split_root.glob(f"*/{TASK_ACTIVE_FILENAME}") if path.is_file())
    if not candidates:
        raise ValueError(
            "未找到任务级 _active_task.json，请显式传 --task-split-dir 或 --scope-request"
        )
    if len(candidates) > 1:
        raise ValueError(
            f"检测到多个任务级 _active_task.json（{len(candidates)} 个），请显式传 --task-split-dir 或 --scope-request"
        )
    return candidates[0]


def resolve_scope_request_path(args: argparse.Namespace, repo_root: Path) -> Path:
    explicit = str(args.scope_request or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            return (repo_root / path).resolve()
        return path.resolve()

    task_split_dir = resolve_default_task_split_dir(repo_root, args.task_split_dir)
    return (task_split_dir / ".state" / DEFAULT_SCOPE_REQUEST_FILENAME).resolve()


def resolve_set_active_script(repo_root: Path, raw_path: str) -> Path:
    value = str(raw_path or "").strip()
    path = Path(value).expanduser() if value else DEFAULT_SET_ACTIVE_SCRIPT
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guard for coder4 scope switching using a pending request file."
    )
    parser.add_argument("--repo-root", default="", help="Repository root path.")
    parser.add_argument("--scope-request", default="", help="Path to scope request json.")
    parser.add_argument("--set-active-script", default=str(DEFAULT_SET_ACTIVE_SCRIPT), help="Path to set_active_task.py")
    parser.add_argument("--task-split-dir", default="", help="Optional fallback task split dir.")
    parser.add_argument("--project-id", default="", help="Optional fallback project id.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root(args.repo_root)
    set_active_script = resolve_set_active_script(repo_root, args.set_active_script)
    if not set_active_script.exists():
        payload = {
            "ok": False,
            "action": "scope_switch_failed",
            "error": f"set_active_task not found: {set_active_script}",
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    try:
        scope_request_path = resolve_scope_request_path(args, repo_root)
    except ValueError as exc:
        payload = {
            "ok": False,
            "action": "scope_switch_failed",
            "error": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    cmd = [
        sys.executable,
        str(set_active_script),
        "--repo-root",
        str(repo_root),
        "--scope-request",
        str(scope_request_path),
        "--updated-by",
        "scripts/coder4/coder4_scope_guard.py",
    ]
    if str(args.task_split_dir or "").strip():
        cmd.extend(["--task-split-dir", str(args.task_split_dir).strip()])
    if str(args.project_id or "").strip():
        cmd.extend(["--project-id", str(args.project_id).strip()])

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0:
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
