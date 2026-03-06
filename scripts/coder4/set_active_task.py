#!/usr/bin/env python3
"""Manage task-scoped _active_task.json (direct set + scope request apply)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ACTIVE_FILENAME = "_active_task.json"
TASK_SPLIT_BASE = Path("docs/内部参考/任务拆解")


def detect_repo_root(start: Path) -> Path:
    for ancestor in start.resolve().parents:
        if (ancestor / ".git").exists():
            return ancestor
    return start.resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"json root must be object: {path}")
    return payload


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write task-scoped _active_task.json (or apply scope request) for coder automation scope lock."
    )
    parser.add_argument(
        "--task-split-dir",
        default="",
        help="Task split directory name under docs/内部参考/任务拆解",
    )
    parser.add_argument(
        "--project-id",
        default="",
        help="VK project id used by this task",
    )
    parser.add_argument(
        "--auto-done-policy",
        choices=["manual_gate", "hard_gate"],
        default="hard_gate",
        help="Fallback policy when vk_cards.json has no top-level auto_done_policy",
    )
    parser.add_argument(
        "--status-source-of-truth",
        default=None,
        help=(
            "Canonical status source document path. "
            "If omitted, prefer docs/内部参考/任务拆解/<task_split_dir>/preflight_status.json "
            "when it exists; otherwise fallback to "
            "docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md."
        ),
    )
    parser.add_argument(
        "--updated-by",
        default="scripts/set_active_task.py",
        help="Audit field for who wrote the file",
    )
    parser.add_argument(
        "--repo-root",
        default="",
        help="Repository root path (optional, defaults to script parent repo root)",
    )
    parser.add_argument(
        "--scope-request",
        default="",
        help="Apply pending scope request json (optional).",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resolve_repo_root(raw_repo_root: str) -> Path:
    if raw_repo_root:
        repo_root = Path(raw_repo_root).expanduser()
        if not repo_root.is_absolute():
            repo_root = (Path.cwd() / repo_root).resolve()
        else:
            repo_root = repo_root.resolve()
        return repo_root
    return detect_repo_root(Path(__file__))


def resolve_task_split_dir(repo_root: Path, raw_task_split_dir: str) -> Path:
    raw = str(raw_task_split_dir or "").strip()
    if not raw:
        raise ValueError("missing --task-split-dir")

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


def resolve_status_source_path(
    *,
    repo_root: Path,
    task_split_dir: Path,
    raw_status_source_of_truth: str | None,
) -> Path:
    if raw_status_source_of_truth:
        status_source_path = Path(raw_status_source_of_truth)
    else:
        preferred = task_split_dir / "preflight_status.json"
        fallback = repo_root / "docs" / "内部参考" / "迭代需求" / "迁移执行波次_implementation_plan.md"
        status_source_path = preferred if preferred.exists() else fallback

    if not status_source_path.is_absolute():
        status_source_path = (repo_root / status_source_path).resolve()
    else:
        status_source_path = status_source_path.resolve()

    if not status_source_path.exists():
        raise ValueError(f"status_source_of_truth not found: {status_source_path}")
    return status_source_path


def build_active_payload(
    *,
    repo_root: Path,
    task_split_dir: Path,
    project_id: str,
    auto_done_policy: str,
    status_source_of_truth: str | None,
    updated_by: str,
) -> dict[str, Any]:
    vk_cards_path = task_split_dir / "vk_cards.json"
    if not vk_cards_path.exists():
        raise ValueError(f"vk_cards.json not found: {vk_cards_path}")

    vk_cards = load_json(vk_cards_path)
    task_key = vk_cards.get("task_key")
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


def write_active_payload(
    *,
    task_split_dir: Path,
    active_payload: dict[str, Any],
) -> Path:
    task_scoped_active_task_path = task_split_dir / TASK_ACTIVE_FILENAME
    write_json(task_scoped_active_task_path, active_payload)
    return task_scoped_active_task_path


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
    if not request_path.is_absolute():
        request_path = (repo_root / request_path).resolve()
    else:
        request_path = request_path.resolve()

    if not request_path.exists():
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

    request_payload = load_json(request_path)
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

    task_split_raw = str(request_payload.get("task_split_dir") or args.task_split_dir or "").strip()
    if not task_split_raw:
        raise ValueError("scope request missing task_split_dir")
    task_split_dir = resolve_task_split_dir(repo_root, task_split_raw)

    scoped_active_path = task_split_dir / TASK_ACTIVE_FILENAME
    current_active_payload = load_optional_json(scoped_active_path) or {}
    project_id = str(request_payload.get("project_id") or args.project_id or "").strip()
    if not project_id:
        project_id = str(current_active_payload.get("project_id") or "").strip()
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
    if not already_active:
        write_active_payload(
            task_split_dir=task_split_dir,
            active_payload=active_payload,
        )
        action = "scope_switched"

    mark_scope_request_applied(
        request_path,
        request_payload,
        action=action,
        task_key=task_key,
        updated_by=args.updated_by,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "action": action,
                "task_split_dir": task_split_dir.name,
                "project_id": project_id,
                "task_key": task_key,
                "active_task": str(scoped_active_path),
                "request_path": str(request_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def set_task_active(args: argparse.Namespace, repo_root: Path) -> int:
    task_split_dir = resolve_task_split_dir(repo_root, args.task_split_dir)
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

    task_scoped_active_task_path = write_active_payload(
        task_split_dir=task_split_dir,
        active_payload=active_payload,
    )

    print(f"updated task-scoped: {task_scoped_active_task_path}")
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
    repo_root = resolve_repo_root(args.repo_root)
    try:
        if str(args.scope_request or "").strip():
            return apply_scope_request(args, repo_root)
        return set_task_active(args, repo_root)
    except ValueError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
