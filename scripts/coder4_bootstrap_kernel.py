#!/usr/bin/env python3
"""Deterministic card-state kernel for coder4 auto-seed/auto-activate."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ACTIVE_TASK = (
    "/Users/jijingkun/bojxAI/fastapi/docs/内部参考/任务拆解/_active_task.json"
)
DEFAULT_VK_API_BASE = "http://127.0.0.1:3001"


@dataclass
class KernelContext:
    project_id: str
    task_key: str
    card_order: list[str]
    cards: dict[str, dict[str, Any]]
    preflight_required: str | None
    status_source_of_truth: str | None


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 12,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, method=method.upper(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"unexpected response shape from {url}")
    return parsed


def normalize_status(raw_status: str | None) -> str:
    if not raw_status:
        return "todo"
    status = raw_status.strip().lower()
    if status in {"done", "closed", "completed"}:
        return "done"
    if status in {"inprogress", "doing", "wip", "active"}:
        return "inprogress"
    if status in {"inreview", "review", "gate", "qa"}:
        return "inreview"
    if status in {"todo", "backlog", "open"}:
        return "todo"
    return "todo"


def normalize_labels(raw_labels: Any) -> list[str]:
    if isinstance(raw_labels, list):
        return [str(label).strip() for label in raw_labels if str(label).strip()]
    if isinstance(raw_labels, str) and raw_labels.strip():
        pieces = [piece.strip() for piece in raw_labels.split(",")]
        return [piece for piece in pieces if piece]
    return []


def is_scoped_task(task: dict[str, Any], task_key: str) -> bool:
    title = str(task.get("title") or "")
    description = str(task.get("description") or "")
    labels = normalize_labels(task.get("labels"))
    task_id = str(task.get("id") or "")
    return (
        f"[{task_key}]" in title
        or task_key in labels
        or task_id.startswith(f"{task_key}::")
        or f"task_key: {task_key}" in description
    )


def has_card_id_marker(description: str, card_id: str) -> bool:
    pattern = re.compile(
        rf"(?:^|\n)\s*card_id\s*:\s*{re.escape(card_id)}\s*(?:\n|$)",
        flags=re.IGNORECASE,
    )
    return bool(pattern.search(description))


def choose_best_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not tasks:
        return None
    return sorted(tasks, key=lambda item: str(item.get("updated_at") or ""), reverse=True)[0]


def split_tasks_by_scope(
    all_tasks: list[dict[str, Any]], task_key: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scoped: list[dict[str, Any]] = []
    unscoped: list[dict[str, Any]] = []
    for task in all_tasks:
        if is_scoped_task(task, task_key):
            scoped.append(task)
        else:
            unscoped.append(task)
    return scoped, unscoped


def map_card_status(
    card_id: str,
    task_key: str,
    scoped_tasks: list[dict[str, Any]],
) -> tuple[str, dict[str, Any] | None]:
    marker_matches: list[dict[str, Any]] = []
    title_matches: list[dict[str, Any]] = []
    for task in scoped_tasks:
        description = str(task.get("description") or "")
        title = str(task.get("title") or "")
        if has_card_id_marker(description, card_id):
            marker_matches.append(task)
            continue
        if card_id in title and f"[{task_key}]" in title:
            title_matches.append(task)
    match = choose_best_task(marker_matches) or choose_best_task(title_matches)
    if match is None:
        return "missing", None
    return normalize_status(str(match.get("status") or "")), match


def build_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"todo": 0, "inprogress": 0, "inreview": 0, "done": 0}
    for task in tasks:
        status = normalize_status(str(task.get("status") or ""))
        if status in counts:
            counts[status] += 1
    return counts


def parse_context(active_task_path: Path) -> KernelContext:
    active_task = load_json(active_task_path)
    project_id = str(active_task.get("project_id") or "").strip()
    task_key = str(active_task.get("task_key") or "").strip()
    task_split_dir = str(active_task.get("task_split_dir") or "").strip()
    if not project_id or not task_key or not task_split_dir:
        raise RuntimeError("active_task missing required fields: project_id/task_key/task_split_dir")

    vk_cards_path = (
        active_task_path.parent / task_split_dir / "vk_cards.json"
        if active_task_path.name == "_active_task.json"
        else Path("/Users/jijingkun/bojxAI/fastapi/docs/内部参考/任务拆解")
        / task_split_dir
        / "vk_cards.json"
    )
    if not vk_cards_path.exists():
        raise RuntimeError(f"vk_cards.json not found: {vk_cards_path}")

    vk_cards = load_json(vk_cards_path)
    card_order = [str(item) for item in (vk_cards.get("card_order") or [])]
    cards_raw = vk_cards.get("cards") or []
    cards: dict[str, dict[str, Any]] = {}
    for card in cards_raw:
        if isinstance(card, dict):
            card_id = str(card.get("card_id") or "").strip()
            if card_id:
                cards[card_id] = card
    if not card_order:
        card_order = list(cards.keys())
    missing_defs = [card_id for card_id in card_order if card_id not in cards]
    if missing_defs:
        raise RuntimeError(f"vk_cards missing card definition(s): {missing_defs}")

    preflight_required = active_task.get("preflight_required")
    if preflight_required is not None:
        preflight_required = str(preflight_required).strip() or None
    status_source = active_task.get("status_source_of_truth")
    if status_source is not None:
        status_source = str(status_source).strip() or None

    return KernelContext(
        project_id=project_id,
        task_key=task_key,
        card_order=card_order,
        cards=cards,
        preflight_required=preflight_required,
        status_source_of_truth=status_source,
    )


def fetch_project_tasks(vk_api_base: str, project_id: str, timeout_seconds: int) -> list[dict[str, Any]]:
    encoded_project = urllib.parse.quote(project_id, safe="")
    url = f"{vk_api_base.rstrip('/')}/api/tasks?project_id={encoded_project}"
    payload = request_json("GET", url, timeout_seconds=timeout_seconds)
    tasks = payload.get("data")
    if not isinstance(tasks, list):
        raise RuntimeError("VK /api/tasks response missing list data")
    return [item for item in tasks if isinstance(item, dict)]


def check_preflight(
    ctx: KernelContext,
    scoped_tasks: list[dict[str, Any]],
) -> tuple[bool, str]:
    if not ctx.preflight_required:
        return True, "preflight_not_required"

    preflight_card = ctx.preflight_required
    board_ok = False
    for task in scoped_tasks:
        title = str(task.get("title") or "")
        description = str(task.get("description") or "")
        status = normalize_status(str(task.get("status") or ""))
        if status != "done":
            continue
        if preflight_card in title or has_card_id_marker(description, preflight_card):
            board_ok = True
            break
    if board_ok:
        return True, "preflight_board_done"

    source = ctx.status_source_of_truth
    if not source:
        return False, f"{preflight_card}_not_done"
    source_path = Path(source)
    if not source_path.exists():
        return False, f"{preflight_card}_not_done"

    if source_path.suffix.lower() == ".json":
        try:
            content = load_json(source_path)
        except (json.JSONDecodeError, OSError):
            return False, f"{preflight_card}_not_done"
        matches = str(content.get("preflight_required") or "").strip() == preflight_card
        passed = bool(content.get("passed") is True)
        if matches and passed:
            return True, "preflight_doc_passed_json"
        return False, f"{preflight_card}_not_done"

    text = source_path.read_text(encoding="utf-8", errors="ignore")
    legacy_ok = f"{preflight_card} 已通过" in text and "可进入" in text
    return (True, "preflight_doc_passed_text") if legacy_ok else (False, f"{preflight_card}_not_done")


def build_machine_description(card: dict[str, Any], task_key: str) -> str:
    fields = [
        ("card_id", card.get("card_id")),
        ("task_key", task_key),
        ("task_mode", card.get("task_mode")),
        ("merge_required", card.get("merge_required")),
        ("feature_ids", card.get("feature_ids")),
        ("hard_depends_on", card.get("hard_depends_on")),
        ("mechanism_summary", card.get("mechanism_summary")),
        ("code_anchor_refs", card.get("code_anchor_refs")),
        ("acceptance_checks", card.get("acceptance_checks")),
        ("rollback_anchors", card.get("rollback_anchors")),
        ("evidence_entry", card.get("evidence_entry")),
        ("source_ws_file", card.get("source_ws_file")),
    ]
    lines: list[str] = []
    for key, value in fields:
        if value is None:
            continue
        if isinstance(value, (list, dict, bool)):
            rendered = json.dumps(value, ensure_ascii=False)
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    return "\n".join(lines) + "\n"


def dependencies_satisfied(depends: list[str], card_status_map: dict[str, str]) -> bool:
    return all(card_status_map.get(dep) == "done" for dep in depends)


def resolve_next_action(
    ctx: KernelContext,
    scoped_tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    card_status_map: dict[str, str] = {}
    card_task_map: dict[str, dict[str, Any] | None] = {}
    blocked_details: list[dict[str, Any]] = []
    first_not_done: str | None = None
    target_task_id: str | None = None

    for card_id in ctx.card_order:
        status, task = map_card_status(card_id, ctx.task_key, scoped_tasks)
        card_status_map[card_id] = status
        card_task_map[card_id] = task

    for card_id in ctx.card_order:
        status = card_status_map[card_id]
        if status == "done":
            continue
        first_not_done = card_id
        card = ctx.cards[card_id]
        depends = [str(item) for item in (card.get("hard_depends_on") or [])]
        deps_ok = dependencies_satisfied(depends, card_status_map)
        if status == "missing":
            if deps_ok:
                return {
                    "action": "seed",
                    "first_not_done": first_not_done,
                    "target_card_id": card_id,
                    "target_task_id": None,
                    "target_status": status,
                    "card_status_map": card_status_map,
                    "blocked_details": blocked_details,
                }
            blocked_details.append(
                {
                    "card_id": card_id,
                    "status": status,
                    "depends_on": depends,
                    "missing_done_depends": [dep for dep in depends if card_status_map.get(dep) != "done"],
                }
            )
            continue
        if status == "todo":
            if deps_ok:
                task = card_task_map.get(card_id)
                target_task_id = str(task.get("id")) if isinstance(task, dict) and task.get("id") else None
                return {
                    "action": "activate",
                    "first_not_done": first_not_done,
                    "target_card_id": card_id,
                    "target_task_id": target_task_id,
                    "target_status": status,
                    "card_status_map": card_status_map,
                    "blocked_details": blocked_details,
                }
            blocked_details.append(
                {
                    "card_id": card_id,
                    "status": status,
                    "depends_on": depends,
                    "missing_done_depends": [dep for dep in depends if card_status_map.get(dep) != "done"],
                }
            )
            continue
        if status in {"inprogress", "inreview"}:
            task = card_task_map.get(card_id)
            target_task_id = str(task.get("id")) if isinstance(task, dict) and task.get("id") else None
            return {
                "action": "dispatch",
                "first_not_done": first_not_done,
                "target_card_id": card_id,
                "target_task_id": target_task_id,
                "target_status": status,
                "card_status_map": card_status_map,
                "blocked_details": blocked_details,
            }

    if blocked_details:
        return {
            "action": "blocked_depends",
            "first_not_done": first_not_done,
            "target_card_id": None,
            "target_task_id": None,
            "target_status": None,
            "card_status_map": card_status_map,
            "blocked_details": blocked_details,
        }

    return {
        "action": "all_done",
        "first_not_done": None,
        "target_card_id": None,
        "target_task_id": None,
        "target_status": None,
        "card_status_map": card_status_map,
        "blocked_details": blocked_details,
    }


def seed_card(
    ctx: KernelContext,
    action_result: dict[str, Any],
    scoped_tasks: list[dict[str, Any]],
    vk_api_base: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    card_id = str(action_result.get("target_card_id") or "")
    if not card_id:
        return {"performed": False, "reason": "seed_missing_card_id"}

    card = ctx.cards[card_id]
    title = str(card.get("title") or "").strip()
    if not title:
        return {"performed": False, "reason": "seed_missing_title"}

    for task in scoped_tasks:
        if str(task.get("title") or "").strip() == title:
            return {
                "performed": False,
                "reason": "seed_skip_existing_title",
                "existing_task_id": task.get("id"),
            }
        if has_card_id_marker(str(task.get("description") or ""), card_id):
            return {
                "performed": False,
                "reason": "seed_skip_existing_card_id",
                "existing_task_id": task.get("id"),
            }

    labels = normalize_labels(card.get("labels"))
    if ctx.task_key not in labels:
        labels.append(ctx.task_key)

    payload: dict[str, Any] = {
        "project_id": ctx.project_id,
        "title": title,
        "description": build_machine_description(card, ctx.task_key),
        "status": "todo",
    }
    if labels:
        payload["labels"] = labels

    url = f"{vk_api_base.rstrip('/')}/api/tasks"
    created = request_json("POST", url, payload=payload, timeout_seconds=timeout_seconds)
    if created.get("success") is not True:
        return {"performed": False, "reason": "seed_api_failed", "raw": created}
    created_task = created.get("data") if isinstance(created.get("data"), dict) else {}
    return {
        "performed": True,
        "action": "seed",
        "card_id": card_id,
        "task_id": created_task.get("id"),
        "status": created_task.get("status"),
    }


def activate_card(
    action_result: dict[str, Any],
    vk_api_base: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    task_id = str(action_result.get("target_task_id") or "").strip()
    card_id = str(action_result.get("target_card_id") or "").strip()
    if not task_id:
        return {"performed": False, "reason": "activate_missing_task_id", "card_id": card_id}
    url = f"{vk_api_base.rstrip('/')}/api/tasks/{urllib.parse.quote(task_id, safe='')}"
    updated = request_json(
        "PUT",
        url,
        payload={"status": "inprogress"},
        timeout_seconds=timeout_seconds,
    )
    if updated.get("success") is not True:
        return {"performed": False, "reason": "activate_api_failed", "raw": updated}
    task = updated.get("data") if isinstance(updated.get("data"), dict) else {}
    return {
        "performed": True,
        "action": "activate",
        "card_id": card_id,
        "task_id": task.get("id"),
        "status": task.get("status"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic board kernel for coder4 automation.")
    parser.add_argument(
        "--active-task",
        default=DEFAULT_ACTIVE_TASK,
        help="Absolute path to _active_task.json",
    )
    parser.add_argument(
        "--vk-api-base",
        default=DEFAULT_VK_API_BASE,
        help="VK backend base url, e.g. http://127.0.0.1:3001",
    )
    parser.add_argument(
        "--apply-bootstrap",
        action="store_true",
        help="Execute seed/activate actions directly when action is seed/activate.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=12,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to write JSON result.",
    )
    return parser.parse_args()


def emit(payload: dict[str, Any], pretty: bool, output_path: str | None) -> None:
    json_text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json_text + "\n", encoding="utf-8")
    print(json_text)


def main() -> int:
    args = parse_args()
    active_task_path = Path(args.active_task).resolve()

    try:
        ctx = parse_context(active_task_path)
        all_tasks = fetch_project_tasks(args.vk_api_base, ctx.project_id, args.timeout_seconds)
        scoped_tasks, unscoped_tasks = split_tasks_by_scope(all_tasks, ctx.task_key)

        preflight_ok, preflight_reason = check_preflight(ctx, scoped_tasks)
        scoped_counts = build_counts(scoped_tasks)
        unscoped_counts = build_counts(unscoped_tasks)
        base_payload: dict[str, Any] = {
            "ok": True,
            "project_id": ctx.project_id,
            "task_key": ctx.task_key,
            "preflight_required": ctx.preflight_required,
            "preflight_ok": preflight_ok,
            "preflight_reason": preflight_reason,
            "counts": {
                "scoped": scoped_counts,
                "unscoped": unscoped_counts,
                "scoped_total": len(scoped_tasks),
                "unscoped_total": len(unscoped_tasks),
                "board_total": len(all_tasks),
            },
            "card_order": ctx.card_order,
        }

        if not preflight_ok:
            result = {
                **base_payload,
                "action": "preflight_blocked",
                "reason": preflight_reason,
                "card_status_map": {},
                "first_not_done": None,
                "target_card_id": None,
                "target_task_id": None,
                "target_status": None,
                "blocked_details": [],
                "applied": {"performed": False, "reason": "preflight_blocked"},
            }
            emit(result, args.pretty, args.output)
            return 0

        action_result = resolve_next_action(ctx, scoped_tasks)
        applied: dict[str, Any] = {"performed": False}
        if args.apply_bootstrap and action_result["action"] == "seed":
            applied = seed_card(
                ctx=ctx,
                action_result=action_result,
                scoped_tasks=scoped_tasks,
                vk_api_base=args.vk_api_base,
                timeout_seconds=args.timeout_seconds,
            )
        elif args.apply_bootstrap and action_result["action"] == "activate":
            applied = activate_card(
                action_result=action_result,
                vk_api_base=args.vk_api_base,
                timeout_seconds=args.timeout_seconds,
            )

        result = {
            **base_payload,
            **action_result,
            "applied": applied,
        }
        emit(result, args.pretty, args.output)
        return 0
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        error_payload = {
            "ok": False,
            "action": "error",
            "error": str(exc),
        }
        emit(error_payload, args.pretty, args.output)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
