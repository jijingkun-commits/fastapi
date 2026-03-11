#!/usr/bin/env python3
"""Manage task-scoped _active_task.json (direct set + scope request apply)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from task_split_paths import (
    CANONICAL_TASK_SPLIT_BASE,
    TASK_ACTIVE_FILENAME,
    detect_repo_root,
    resolve_task_split_paths,
)

DEFAULT_ACTIVE_TASK_INDEX_PATH = str(CANONICAL_TASK_SPLIT_BASE / TASK_ACTIVE_FILENAME)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"json root must be object: {path}")
    return payload


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write task-scoped _active_task.json (or apply scope request) for coder automation scope lock."
    )
    parser.add_argument("--task-split-dir", default="", help="Task split directory name under workdocs/任务拆解")
    parser.add_argument("--project-id", default="", help="VK project id used by this task")
    parser.add_argument(
        "--auto-done-policy",
        choices=["manual_gate", "hard_gate"],
        default="hard_gate",
        help="Fallback policy when vk_cards.json has no top-level auto_done_policy",
    )
    parser.add_argument(
        "--status-source-of-truth",
        default=None,
        help="Canonical status source document path. If omitted, use workdocs/.../reports/preflight_status.json.",
    )
    parser.add_argument("--updated-by", default="scripts/set_active_task.py", help="Audit field for who wrote the file")
    parser.add_argument("--repo-root", default="", help="Repository root path (optional, defaults to script parent repo root)")
    parser.add_argument(
        "--active-task-path",
        default=DEFAULT_ACTIVE_TASK_INDEX_PATH,
        help="Index active task file path to update alongside task-scoped _active_task.json",
    )
    parser.add_argument("--scope-request", default="", help="Apply pending scope request json (optional).")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resolve_repo_root(raw_repo_root: str) -> Path:
    value = str(raw_repo_root or "").strip()
    if value:
        path = Path(value).expanduser()
        return (Path.cwd() / path).resolve() if not path.is_absolute() else path.resolve()
    return detect_repo_root(Path(__file__))


def resolve_status_source_path(
    *,
    repo_root: Path,
    task_split_dir: Path,
    raw_status_source_of_truth: str | None,
) -> Path:
    locator = resolve_task_split_paths(repo_root, task_split_dir.name, must_exist=False)
    if raw_status_source_of_truth:
        status_source_path = Path(raw_status_source_of_truth).expanduser()
        if not status_source_path.is_absolute():
            status_source_path = (repo_root / status_source_path).resolve()
        else:
            status_source_path = status_source_path.resolve()
        if not status_source_path.exists():
            raise ValueError(f"status_source_of_truth not found: {status_source_path}")
        return status_source_path
    return locator.preflight_status_file.resolve()


def build_active_payload(
    *,
    repo_root: Path,
    task_split_dir: Path,
    project_id: str,
    auto_done_policy: str,
    status_source_of_truth: str | None,
    updated_by: str,
) -> dict[str, Any]:
    locator = resolve_task_split_paths(repo_root, task_split_dir.name, must_exist=False)
    vk_cards_path = locator.vk_cards_file
    if not vk_cards_path.exists():
        raise ValueError(f"vk_cards.json not found: {vk_cards_path}")

    vk_cards = load_json(vk_cards_path)
    task_key = str(vk_cards.get("task_key") or "").strip()
    if not task_key:
        raise ValueError(f"task_key missing in {vk_cards_path}")

    execution_mode = vk_cards.get("execution_mode", "serial")
    single_active_card = bool(vk_cards.get("single_active_card", True))

    auto_done = auto_done_policy
    top_policy = vk_cards.get("auto_done_policy")
    if isinstance(top_policy, dict):
        auto_done = str(top_policy.get("implementation-card", auto_done))

    preflight_required = "C00"
    preflight = vk_cards.get("preflight")
    if isinstance(preflight, dict):
        preflight_required = str(preflight.get("card_id", preflight_required))

    status_source_path = resolve_status_source_path(
        repo_root=repo_root,
        task_split_dir=task_split_dir,
        raw_status_source_of_truth=status_source_of_truth,
    )

    return {
        "project_id": project_id,
        "task_split_dir": task_split_dir.name,
        "task_key": task_key,
        "execution_mode": execution_mode,
        "single_active_card": single_active_card,
        "auto_done_policy": auto_done,
        "preflight_required": preflight_required,
        "status_source_of_truth": str(status_source_path),
        "updated_at": now_iso(),
        "updated_by": updated_by,
    }


def write_active_payload(*, task_split_dir: Path, active_payload: dict[str, Any], repo_root: Path) -> Path:
    locator = resolve_task_split_paths(repo_root, task_split_dir.name, must_exist=False)
    write_json(locator.active_task_file, active_payload)
    return locator.active_task_file


def resolve_active_task_index_path(repo_root: Path, raw_active_task_path: str | None) -> Path:
    raw = str(raw_active_task_path or "").strip() or DEFAULT_ACTIVE_TASK_INDEX_PATH
    path = Path(raw).expanduser()
    return (repo_root / path).resolve() if not path.is_absolute() else path.resolve()


def write_active_index_payload(*, index_path: Path, task_scoped_active_task_path: Path, active_payload: dict[str, Any]) -> Path:
    index_payload = dict(active_payload)
    index_payload["active_task_path"] = str(task_scoped_active_task_path.resolve())
    write_json(index_path, index_payload)
    return index_path


def mark_scope_request_applied(
    request_path: Path,
    request_payload: dict[str, Any],
    *,
    action: str,
    task_key: str,
    updated_by: str,
) -> None:
    request_payload["applied"] = True
    request_payload["applied_at"] = now_iso()
    request_payload["applied_by"] = updated_by
    request_payload["applied_action"] = action
    request_payload["applied_task_key"] = task_key
    write_json(request_path, request_payload)


def apply_scope_request(args: argparse.Namespace, repo_root: Path) -> int:
    request_path = Path(args.scope_request).expanduser()
    request_path = (repo_root / request_path).resolve() if not request_path.is_absolute() else request_path.resolve()

    if not request_path.exists():
        print(json.dumps({"ok": True, "action": "no_request", "reason": "scope_request_missing", "request_path": str(request_path)}, ensure_ascii=False))
        return 0

    request_payload = load_json(request_path)
    if bool(request_payload.get("applied")):
        print(json.dumps({
            "ok": True,
            "action": "no_request",
            "reason": "scope_request_already_applied",
            "request_path": str(request_path),
            "applied_at": request_payload.get("applied_at"),
        }, ensure_ascii=False))
        return 0

    task_split_raw = str(request_payload.get("task_split_dir") or args.task_split_dir or "").strip()
    if not task_split_raw:
        raise ValueError("scope request missing task_split_dir")
    locator = resolve_task_split_paths(repo_root, task_split_raw, must_exist=False)
    task_split_dir = locator.canonical_task_split_dir

    scoped_active_path = locator.active_task_file
    current_active_payload = load_optional_json(scoped_active_path) or {}
    project_id = str(request_payload.get("project_id") or args.project_id or "").strip() or str(current_active_payload.get("project_id") or "").strip()
    if not project_id:
        raise ValueError("scope request missing project_id and no active fallback")

    active_payload = build_active_payload(
        repo_root=repo_root,
        task_split_dir=task_split_dir,
        project_id=project_id,
        auto_done_policy=args.auto_done_policy,
        status_source_of_truth=args.status_source_of_truth,
        updated_by=args.updated_by,
    )
    task_key = str(active_payload.get("task_key") or "").strip()

    already_active = (
        str(current_active_payload.get("task_split_dir") or "").strip() == task_split_dir.name
        and str(current_active_payload.get("project_id") or "").strip() == project_id
        and str(current_active_payload.get("task_key") or "").strip() == task_key
    )

    action = "already_active"
    task_scoped_active_task_path = scoped_active_path
    if not already_active:
        task_scoped_active_task_path = write_active_payload(task_split_dir=task_split_dir, active_payload=active_payload, repo_root=repo_root)
        action = "scope_switched"

    write_active_index_payload(
        index_path=resolve_active_task_index_path(repo_root, getattr(args, "active_task_path", DEFAULT_ACTIVE_TASK_INDEX_PATH)),
        task_scoped_active_task_path=task_scoped_active_task_path,
        active_payload=active_payload,
    )
    mark_scope_request_applied(request_path, request_payload, action=action, task_key=task_key, updated_by=args.updated_by)

    print(json.dumps({
        "ok": True,
        "action": action,
        "task_split_dir": task_split_dir.name,
        "project_id": project_id,
        "task_key": task_key,
        "active_task": str(scoped_active_path),
        "request_path": str(request_path),
    }, ensure_ascii=False))
    return 0


def set_task_active(args: argparse.Namespace, repo_root: Path) -> int:
    locator = resolve_task_split_paths(repo_root, args.task_split_dir, must_exist=False)
    task_split_dir = locator.canonical_task_split_dir
    project_id = str(args.project_id or "").strip()
    if not project_id:
        raise ValueError("missing --project-id")

    active_payload = build_active_payload(
        repo_root=repo_root,
        task_split_dir=task_split_dir,
        project_id=project_id,
        auto_done_policy=args.auto_done_policy,
        status_source_of_truth=args.status_source_of_truth,
        updated_by=args.updated_by,
    )

    task_scoped_active_task_path = write_active_payload(task_split_dir=task_split_dir, active_payload=active_payload, repo_root=repo_root)
    active_index_path = write_active_index_payload(
        index_path=resolve_active_task_index_path(repo_root, getattr(args, "active_task_path", DEFAULT_ACTIVE_TASK_INDEX_PATH)),
        task_scoped_active_task_path=task_scoped_active_task_path,
        active_payload=active_payload,
    )

    print(f"updated task-scoped: {task_scoped_active_task_path}")
    print(f"updated active index: {active_index_path}")
    print(
        "scope:",
        f"project_id={active_payload['project_id']}",
        f"task_split_dir={active_payload['task_split_dir']}",
        f"task_key={active_payload['task_key']}",
        f"auto_done_policy={active_payload['auto_done_policy']}",
        f"status_source_of_truth={active_payload['status_source_of_truth']}",
        sep=" ",
    )
    return 0


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root(getattr(args, "repo_root", ""))
    try:
        if str(getattr(args, "scope_request", "") or "").strip():
            return apply_scope_request(args, repo_root)
        return set_task_active(args, repo_root)
    except ValueError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
