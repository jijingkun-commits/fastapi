#!/usr/bin/env python3
"""Set task-scoped _active_task.json and active index file from a split task directory."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ACTIVE_FILENAME = "_active_task.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write task-scoped _active_task.json and active index file for coder automation scope lock."
    )
    parser.add_argument(
        "--task-split-dir",
        required=True,
        help="Task split directory name under docs/内部参考/任务拆解",
    )
    parser.add_argument(
        "--project-id",
        required=True,
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
        "--active-task-path",
        default="docs/内部参考/任务拆解/_active_task.json",
        help="Target active index json path relative to repo root",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    split_root = repo_root / "docs" / "内部参考" / "任务拆解"
    task_split_dir = split_root / args.task_split_dir
    vk_cards_path = task_split_dir / "vk_cards.json"
    if not vk_cards_path.exists():
        raise SystemExit(f"vk_cards.json not found: {vk_cards_path}")

    vk_cards = load_json(vk_cards_path)
    task_key = vk_cards.get("task_key")
    if not task_key:
        raise SystemExit(f"task_key missing in {vk_cards_path}")

    execution_mode = vk_cards.get("execution_mode", "serial")
    single_active_card = bool(vk_cards.get("single_active_card", True))

    auto_done = args.auto_done_policy
    top_policy = vk_cards.get("auto_done_policy")
    if isinstance(top_policy, dict):
        auto_done = str(top_policy.get("implementation-card", auto_done))

    preflight_required = "C00"
    preflight = vk_cards.get("preflight")
    if isinstance(preflight, dict):
        preflight_required = str(preflight.get("card_id", preflight_required))

    status_source_path: Path
    if args.status_source_of_truth:
        status_source_path = Path(args.status_source_of_truth)
    else:
        preferred = task_split_dir / "preflight_status.json"
        fallback = repo_root / "docs" / "内部参考" / "迭代需求" / "迁移执行波次_implementation_plan.md"
        status_source_path = preferred if preferred.exists() else fallback

    if not status_source_path.is_absolute():
        status_source_path = (repo_root / status_source_path).resolve()

    if not status_source_path.exists():
        raise SystemExit(f"status_source_of_truth not found: {status_source_path}")

    active_payload = {
        "project_id": args.project_id,
        "task_split_dir": args.task_split_dir,
        "task_key": task_key,
        "execution_mode": execution_mode,
        "single_active_card": single_active_card,
        "auto_done_policy": auto_done,
        "preflight_required": preflight_required,
        "status_source_of_truth": str(status_source_path),
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "updated_by": args.updated_by,
    }

    task_scoped_active_task_path = task_split_dir / TASK_ACTIVE_FILENAME
    write_json(task_scoped_active_task_path, active_payload)

    active_index_path = repo_root / args.active_task_path
    active_index_payload = dict(active_payload)
    active_index_payload["active_task_path"] = str(task_scoped_active_task_path.resolve())
    write_json(active_index_path, active_index_payload)

    print(f"updated task-scoped: {task_scoped_active_task_path}")
    print(f"updated active-index: {active_index_path}")
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


if __name__ == "__main__":
    raise SystemExit(main())
