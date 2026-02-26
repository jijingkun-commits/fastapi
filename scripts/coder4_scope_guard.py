#!/usr/bin/env python3
"""Apply one pending coder4 scope switch request to _active_task.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPO_ROOT = Path("/Users/jijingkun/bojxAI/fastapi")
DEFAULT_ACTIVE_TASK = DEFAULT_REPO_ROOT / "docs/内部参考/任务拆解/_active_task.json"
DEFAULT_SCOPE_REQUEST = Path(
    "/Users/jijingkun/.openclaw/workspace-dev/state/coder4_scope_request.json"
)
DEFAULT_SET_ACTIVE_SCRIPT = DEFAULT_REPO_ROOT / "scripts/set_active_task.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"json root must be object: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guard for coder4 scope switching using a pending request file."
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Repository root path.",
    )
    parser.add_argument(
        "--active-task",
        default=str(DEFAULT_ACTIVE_TASK),
        help="Path to _active_task.json",
    )
    parser.add_argument(
        "--scope-request",
        default=str(DEFAULT_SCOPE_REQUEST),
        help="Path to coder4 scope request json.",
    )
    parser.add_argument(
        "--set-active-script",
        default=str(DEFAULT_SET_ACTIVE_SCRIPT),
        help="Path to set_active_task.py",
    )
    return parser.parse_args()


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def validate_split(repo_root: Path, task_split_dir: str) -> tuple[Path, str]:
    split_root = repo_root / "docs" / "内部参考" / "任务拆解"
    split_dir = split_root / task_split_dir
    if not split_dir.exists():
        raise ValueError(f"task_split_dir not found: {split_dir}")
    vk_cards_path = split_dir / "vk_cards.json"
    if not vk_cards_path.exists():
        raise ValueError(f"vk_cards.json not found: {vk_cards_path}")
    vk_cards = load_json(vk_cards_path)
    task_key = str(vk_cards.get("task_key") or "").strip()
    if not task_key:
        raise ValueError(f"task_key missing in {vk_cards_path}")
    return split_dir, task_key


def mark_applied(
    request_payload: dict[str, Any],
    *,
    request_path: Path,
    action: str,
    task_key: str,
) -> None:
    request_payload["applied"] = True
    request_payload["applied_at"] = now_iso()
    request_payload["applied_by"] = "scripts/coder4_scope_guard.py"
    request_payload["applied_action"] = action
    request_payload["applied_task_key"] = task_key
    write_json(request_path, request_payload)


def run_set_active(
    *,
    repo_root: Path,
    set_active_script: Path,
    task_split_dir: str,
    project_id: str,
) -> dict[str, str]:
    cmd = [
        sys.executable,
        str(set_active_script),
        "--task-split-dir",
        task_split_dir,
        "--project-id",
        project_id,
        "--updated-by",
        "scripts/coder4_scope_guard.py",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        detail = stderr or stdout or f"returncode={proc.returncode}"
        raise RuntimeError(f"set_active_task failed: {detail}")
    return {"stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    active_task_path = Path(args.active_task).resolve()
    request_path = Path(args.scope_request).resolve()
    set_active_script = Path(args.set_active_script).resolve()

    try:
        request_payload = load_optional_json(request_path)
        if request_payload is None:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "action": "no_request",
                        "reason": "scope_request_missing",
                        "request_path": str(request_path),
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        if bool(request_payload.get("applied")):
            print(
                json.dumps(
                    {
                        "ok": True,
                        "action": "no_request",
                        "reason": "scope_request_already_applied",
                        "request_path": str(request_path),
                        "applied_at": request_payload.get("applied_at"),
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        task_split_dir = str(request_payload.get("task_split_dir") or "").strip()
        if not task_split_dir:
            raise ValueError("scope request missing task_split_dir")

        active_payload = load_optional_json(active_task_path) or {}
        project_id = str(request_payload.get("project_id") or "").strip()
        if not project_id:
            project_id = str(active_payload.get("project_id") or "").strip()
        if not project_id:
            raise ValueError("scope request missing project_id and active_task has no fallback")

        _, task_key = validate_split(repo_root, task_split_dir)

        current_split = str(active_payload.get("task_split_dir") or "").strip()
        current_project = str(active_payload.get("project_id") or "").strip()
        if current_split == task_split_dir and current_project == project_id:
            mark_applied(
                request_payload,
                request_path=request_path,
                action="already_active",
                task_key=task_key,
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "action": "already_active",
                        "task_split_dir": task_split_dir,
                        "project_id": project_id,
                        "task_key": task_key,
                        "active_task": str(active_task_path),
                        "request_path": str(request_path),
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        set_active_result = run_set_active(
            repo_root=repo_root,
            set_active_script=set_active_script,
            task_split_dir=task_split_dir,
            project_id=project_id,
        )

        mark_applied(
            request_payload,
            request_path=request_path,
            action="scope_switched",
            task_key=task_key,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "action": "scope_switched",
                    "task_split_dir": task_split_dir,
                    "project_id": project_id,
                    "task_key": task_key,
                    "active_task": str(active_task_path),
                    "request_path": str(request_path),
                    "set_active_stdout": set_active_result["stdout"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "action": "scope_switch_failed",
                    "error": str(exc),
                    "active_task": str(active_task_path),
                    "request_path": str(request_path),
                },
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
