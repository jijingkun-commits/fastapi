#!/usr/bin/env python3
"""VK read-only sync and reconciliation helper.

设计目标：
- 状态变更后 fire-and-forget 推送（由调用方异步触发）
- 同步失败仅记录告警，不阻断执行链路
- 支持按卡片增量同步与全量对账（适配小时级巡检）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


DEFAULT_ACTIVE_TASK = "/Users/jijingkun/bojxAI/fastapi/docs/内部参考/任务拆解/_active_task.json"
DEFAULT_STATE_FILE = ".omc/state/task-runner-state.json"
DEFAULT_API_BASE = "http://127.0.0.1:3001"
DEFAULT_TIMEOUT_SECONDS = 8
DISABLE_VK_SYNC_ENV = "DISABLE_VK_SYNC"

VALID_SYNC_STATUSES = {"todo", "inprogress", "inreview", "done", "cancelled"}


@dataclass
class SyncContext:
    active_task_path: Path
    project_id: str
    task_key: str
    card_order: list[str]
    cards_by_id: dict[str, dict[str, Any]]
    state_path: Path
    state_status_map: dict[str, str]
    vk_api_base: str
    timeout_seconds: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="coder4 VK read-only sync")
    parser.add_argument("--active-task", default=DEFAULT_ACTIVE_TASK)
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    parser.add_argument("--vk-api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--project-id", default="")
    parser.add_argument("--task-key", default="")
    parser.add_argument("--card-id", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--sync-all", action="store_true", help="force full reconciliation mode")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict", action="store_true", help="sync failure returns non-zero exit code")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output", default="")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_status(raw: Any) -> str:
    status = str(raw or "").strip().lower().replace("-", "_")
    if status == "in_progress":
        return "inprogress"
    if status == "in_review":
        return "inreview"
    if status in {"backlog", "to_do"}:
        return "todo"
    return status


def is_disabled_by_env(name: str) -> bool:
    raw = str(os.getenv(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_warning(event: str, **fields: Any) -> None:
    payload = {"event": event, "ts": utc_now_iso()}
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)


def extract_card_id(task: dict[str, Any]) -> str | None:
    desc = str(task.get("description") or "")
    for line in desc.splitlines():
        if line.lower().startswith("card_id:"):
            card_id = line.split(":", 1)[1].strip().upper()
            if re.fullmatch(r"[CG]\d{2}", card_id):
                return card_id
    title = str(task.get("title") or "")
    match = re.search(r"\b([CG]\d{2})\b", title.upper())
    if match:
        return match.group(1)
    return None


def parse_time(value: Any) -> str:
    return str(value or "")


def pick_task_for_card(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    def key_fn(item: dict[str, Any]) -> tuple[int, str]:
        status = normalize_status(item.get("status"))
        rank_map = {"inprogress": 0, "inreview": 1, "todo": 2, "done": 3, "cancelled": 4}
        rank = rank_map.get(status, 99)
        updated = parse_time(item.get("updated_at") or item.get("updatedAt"))
        return (rank, updated)

    sorted_tasks = sorted(tasks, key=lambda item: (key_fn(item)[0], key_fn(item)[1]), reverse=False)
    if not sorted_tasks:
        raise ValueError("empty tasks for card")
    best_rank = key_fn(sorted_tasks[0])[0]
    same_rank = [task for task in sorted_tasks if key_fn(task)[0] == best_rank]
    same_rank.sort(key=lambda task: parse_time(task.get("updated_at") or task.get("updatedAt")), reverse=True)
    return same_rank[0]


def resolve_runtime_file_path(active_task_path: Path, raw_path: str) -> Path:
    target_path = Path(raw_path).expanduser()
    if target_path.is_absolute():
        return target_path.resolve()
    for ancestor in active_task_path.parents:
        if (ancestor / ".git").exists():
            return (ancestor / target_path).resolve()
    return (Path.cwd() / target_path).resolve()


def resolve_vk_cards_path(active_task_path: Path, active_payload: dict[str, Any], task_split_dir: str) -> Path:
    candidates: list[Path] = []

    split_root = active_task_path.parent
    candidates.append(split_root / task_split_dir / "vk_cards.json")

    source = str(active_payload.get("status_source_of_truth") or "").strip()
    if source:
        source_path = Path(source).expanduser()
        if not source_path.is_absolute():
            source_path = (active_task_path.parent / source_path).resolve()
        candidates.append(source_path.parent / "vk_cards.json")

    repo_root: Path | None = None
    for ancestor in active_task_path.parents:
        if (ancestor / "scripts" / "set_active_task.py").exists():
            repo_root = ancestor
            break

    if repo_root is not None:
        candidates.append(
            repo_root / "docs" / "内部参考" / "任务拆解" / task_split_dir / "vk_cards.json"
        )
        candidates.append(repo_root / "docs" / task_split_dir / "vk_cards.json")

    seen: set[str] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        key = str(resolved)
        if key not in seen:
            ordered.append(resolved)
            seen.add(key)

    for candidate in ordered:
        if candidate.exists():
            return candidate

    joined = " | ".join(str(path) for path in ordered)
    raise FileNotFoundError(f"vk_cards.json not found in candidates: {joined}")


def load_state_status_map(state_path: Path) -> dict[str, str]:
    if not state_path.exists():
        emit_warning("VK_SYNC_STATE_MISSING", state_file=str(state_path))
        return {}

    payload = load_json(state_path)
    raw_map = payload.get("card_status_map")
    if not isinstance(raw_map, dict):
        raw_map = payload.get("card_status") if isinstance(payload.get("card_status"), dict) else {}

    normalized: dict[str, str] = {}
    for key, value in raw_map.items():
        card_id = str(key or "").strip().upper()
        if not card_id:
            continue
        status = normalize_status(value)
        if status:
            normalized[card_id] = status
    return normalized


def http_json(method: str, url: str, payload: dict[str, Any] | None = None, *, timeout_seconds: int) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} {method} {url}: {body[:300]}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"HTTP {method} {url} failed: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response for {method} {url}: {raw[:200]}") from exc


def list_project_tasks(api_base: str, project_id: str, *, timeout_seconds: int) -> list[dict[str, Any]]:
    query = parse.urlencode({"project_id": project_id})
    payload = http_json("GET", f"{api_base}/api/tasks?{query}", timeout_seconds=timeout_seconds)
    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError("invalid /api/tasks response: data is not list")
    return data


def build_scoped_tasks(tasks: list[dict[str, Any]], task_key: str) -> list[dict[str, Any]]:
    scoped: list[dict[str, Any]] = []
    for task in tasks:
        title = str(task.get("title") or "")
        desc = str(task.get("description") or "")
        if task_key in title or task_key in desc:
            scoped.append(task)
    return scoped


def build_task_map(scoped_tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for task in scoped_tasks:
        card_id = extract_card_id(task)
        if not card_id:
            continue
        grouped.setdefault(card_id, []).append(task)

    selected: dict[str, dict[str, Any]] = {}
    for card_id, tasks in grouped.items():
        selected[card_id] = pick_task_for_card(tasks)
    return selected


def build_card_description(card: dict[str, Any], task_key: str, card_id: str) -> str:
    lines = [
        f"card_id: {card_id}",
        f"task_key: {task_key}",
        f"task_mode: {card.get('task_mode')}",
        f"merge_required: {str(card.get('merge_required')).lower()}",
        f"feature_ids: {json.dumps(card.get('feature_ids') or [], ensure_ascii=False)}",
        f"hard_depends_on: {json.dumps(card.get('hard_depends_on') or [], ensure_ascii=False)}",
        f"mechanism_summary: {json.dumps(card.get('mechanism_summary') or [], ensure_ascii=False)}",
        f"code_anchor_refs: {json.dumps(card.get('code_anchor_refs') or [], ensure_ascii=False)}",
        f"acceptance_checks: {json.dumps(card.get('acceptance_checks') or [], ensure_ascii=False)}",
        f"rollback_anchors: {json.dumps(card.get('rollback_anchors') or [], ensure_ascii=False)}",
        f"evidence_entry: {card.get('evidence_entry')}",
        f"source_ws_file: {card.get('source_ws_file')}",
    ]
    return "\n".join(lines) + "\n"


def load_context(args: argparse.Namespace) -> SyncContext:
    active_task_path = Path(args.active_task).expanduser().resolve()
    if not active_task_path.exists():
        raise FileNotFoundError(f"active task not found: {active_task_path}")

    active_payload = load_json(active_task_path)
    task_split_dir = str(active_payload.get("task_split_dir") or "").strip()
    if not task_split_dir:
        raise ValueError("active task missing task_split_dir")

    task_key = str(args.task_key or "").strip() or str(active_payload.get("task_key") or "").strip()
    if not task_key:
        raise ValueError("active task missing task_key")

    project_id = str(args.project_id or "").strip() or str(active_payload.get("project_id") or "").strip()

    vk_cards_path = resolve_vk_cards_path(active_task_path, active_payload, task_split_dir)
    vk_cards_payload = load_json(vk_cards_path)
    card_order = [str(card_id).strip().upper() for card_id in (vk_cards_payload.get("card_order") or [])]

    cards_by_id: dict[str, dict[str, Any]] = {}
    for card in vk_cards_payload.get("cards") or []:
        card_id = str(card.get("card_id") or "").strip().upper()
        if card_id:
            cards_by_id[card_id] = card

    state_path = resolve_runtime_file_path(active_task_path, args.state_file)
    state_status_map = load_state_status_map(state_path)

    timeout_seconds = int(args.timeout_seconds)
    if timeout_seconds <= 0:
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    return SyncContext(
        active_task_path=active_task_path,
        project_id=project_id,
        task_key=task_key,
        card_order=card_order,
        cards_by_id=cards_by_id,
        state_path=state_path,
        state_status_map=state_status_map,
        vk_api_base=str(args.vk_api_base or DEFAULT_API_BASE).rstrip("/"),
        timeout_seconds=timeout_seconds,
    )


def fetch_scoped_task_map(ctx: SyncContext) -> dict[str, dict[str, Any]]:
    if not ctx.project_id:
        return {}
    board_tasks = list_project_tasks(ctx.vk_api_base, ctx.project_id, timeout_seconds=ctx.timeout_seconds)
    scoped_tasks = build_scoped_tasks(board_tasks, ctx.task_key)
    return build_task_map(scoped_tasks)


def _sync_single_card(
    *,
    ctx: SyncContext,
    card_id: str,
    status: str,
    task_map: dict[str, dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    now = utc_now_iso()
    normalized_card_id = str(card_id or "").strip().upper()
    desired_status = normalize_status(status)

    if desired_status not in VALID_SYNC_STATUSES:
        raise ValueError(f"unsupported status for sync: {status}")

    existing_task = task_map.get(normalized_card_id)
    current_status = normalize_status(existing_task.get("status")) if existing_task else ""

    result = {
        "card_id": normalized_card_id,
        "desired_status": desired_status,
        "current_status": current_status,
        "task_id": str(existing_task.get("id")) if existing_task else "",
        "sync_result": "noop",
        "last_sync_at": now,
        "dry_run": dry_run,
        "project_id": ctx.project_id,
    }

    if not ctx.project_id:
        result["sync_result"] = "skipped_missing_project_id"
        return result

    if existing_task:
        if current_status == desired_status:
            result["sync_result"] = "noop_already_in_sync"
            return result
        if dry_run:
            result["sync_result"] = "dry_run_update"
            return result

        payload = {"status": desired_status}
        response = http_json(
            "PUT",
            f"{ctx.vk_api_base}/api/tasks/{existing_task['id']}",
            payload,
            timeout_seconds=ctx.timeout_seconds,
        )
        data = response.get("data") or {}
        existing_task["status"] = data.get("status") or desired_status
        result["sync_result"] = "updated"
        result["current_status"] = normalize_status(existing_task["status"])
        return result

    card_meta = ctx.cards_by_id.get(normalized_card_id) or {}
    payload = {
        "project_id": ctx.project_id,
        "title": str(card_meta.get("title") or f"{normalized_card_id} [{ctx.task_key}]"),
        "description": build_card_description(card_meta, ctx.task_key, normalized_card_id),
        "status": desired_status,
    }

    if dry_run:
        result["sync_result"] = "dry_run_create"
        return result

    response = http_json("POST", f"{ctx.vk_api_base}/api/tasks", payload, timeout_seconds=ctx.timeout_seconds)
    data = response.get("data") or {}
    new_task_id = str(data.get("id") or "")
    result["sync_result"] = "created"
    result["task_id"] = new_task_id
    result["current_status"] = normalize_status(data.get("status") or desired_status)
    if new_task_id:
        task_map[normalized_card_id] = {
            "id": new_task_id,
            "status": result["current_status"],
            "title": payload["title"],
            "description": payload["description"],
        }
    return result


def sync_to_vk(
    *,
    ctx: SyncContext,
    card_id: str,
    status: str,
    dry_run: bool,
    task_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_card_id = str(card_id or "").strip().upper()

    if is_disabled_by_env(DISABLE_VK_SYNC_ENV):
        return {
            "card_id": normalized_card_id,
            "desired_status": normalize_status(status),
            "task_id": "",
            "sync_result": "skipped_disabled",
            "last_sync_at": utc_now_iso(),
            "dry_run": dry_run,
            "project_id": ctx.project_id,
        }

    local_task_map = task_map
    if local_task_map is None:
        local_task_map = fetch_scoped_task_map(ctx)

    try:
        return _sync_single_card(
            ctx=ctx,
            card_id=normalized_card_id,
            status=status,
            task_map=local_task_map,
            dry_run=dry_run,
        )
    except Exception as exc:  # noqa: BLE001
        emit_warning(
            "VK_SYNC_CARD_FAILED",
            card_id=normalized_card_id,
            status=normalize_status(status),
            error=str(exc),
            dry_run=dry_run,
        )
        return {
            "card_id": normalized_card_id,
            "desired_status": normalize_status(status),
            "task_id": "",
            "sync_result": "failed",
            "last_sync_at": utc_now_iso(),
            "dry_run": dry_run,
            "project_id": ctx.project_id,
            "error": str(exc),
        }


def sync_all_cards(*, ctx: SyncContext, dry_run: bool) -> dict[str, Any]:
    disabled = is_disabled_by_env(DISABLE_VK_SYNC_ENV)
    results: list[dict[str, Any]] = []
    status_map = dict(ctx.state_status_map)

    task_map: dict[str, dict[str, Any]] = {}
    if not disabled and ctx.project_id:
        try:
            task_map = fetch_scoped_task_map(ctx)
        except Exception as exc:  # noqa: BLE001
            emit_warning("VK_SYNC_FETCH_FAILED", error=str(exc), project_id=ctx.project_id)
            task_map = {}

    for card_id in ctx.card_order:
        desired_status = normalize_status(status_map.get(card_id))
        if not desired_status:
            results.append(
                {
                    "card_id": card_id,
                    "desired_status": "",
                    "task_id": "",
                    "sync_result": "skipped_missing_local_status",
                    "last_sync_at": utc_now_iso(),
                    "dry_run": dry_run,
                    "project_id": ctx.project_id,
                }
            )
            continue
        if desired_status not in VALID_SYNC_STATUSES:
            results.append(
                {
                    "card_id": card_id,
                    "desired_status": desired_status,
                    "task_id": "",
                    "sync_result": "skipped_invalid_status",
                    "last_sync_at": utc_now_iso(),
                    "dry_run": dry_run,
                    "project_id": ctx.project_id,
                }
            )
            continue
        results.append(
            sync_to_vk(
                ctx=ctx,
                card_id=card_id,
                status=desired_status,
                dry_run=dry_run,
                task_map=task_map,
            )
        )

    counts: dict[str, int] = {}
    for item in results:
        key = str(item.get("sync_result") or "unknown")
        counts[key] = counts.get(key, 0) + 1

    has_failed = any(item.get("sync_result") == "failed" for item in results)

    return {
        "mode": "sync_all_cards",
        "task_key": ctx.task_key,
        "project_id": ctx.project_id,
        "state_file": str(ctx.state_path),
        "dry_run": dry_run,
        "disabled": disabled,
        "total_cards": len(ctx.card_order),
        "results": results,
        "counts": counts,
        "has_failed": has_failed,
        "last_sync_at": utc_now_iso(),
    }


def write_output_file(output_path: str, payload: dict[str, Any]) -> None:
    if not output_path:
        return
    write_json(Path(output_path).expanduser().resolve(), payload)


def run_sync(args: argparse.Namespace) -> dict[str, Any]:
    ctx = load_context(args)

    card_id = str(args.card_id or "").strip().upper()
    status = normalize_status(args.status)
    single_mode = bool(card_id or status) and not args.sync_all

    if single_mode:
        if not card_id or not status:
            raise ValueError("single-card mode requires both --card-id and --status")
        result = sync_to_vk(ctx=ctx, card_id=card_id, status=status, dry_run=bool(args.dry_run))
        has_failed = result.get("sync_result") == "failed"
        return {
            "mode": "sync_to_vk",
            "task_key": ctx.task_key,
            "project_id": ctx.project_id,
            "state_file": str(ctx.state_path),
            "dry_run": bool(args.dry_run),
            "disabled": is_disabled_by_env(DISABLE_VK_SYNC_ENV),
            "result": result,
            "has_failed": has_failed,
            "last_sync_at": utc_now_iso(),
        }

    return sync_all_cards(ctx=ctx, dry_run=bool(args.dry_run))


def main() -> int:
    args = parse_args()
    try:
        payload = run_sync(args)
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "error": str(exc),
            "mode": "sync_error",
            "last_sync_at": utc_now_iso(),
        }
        write_output_file(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    has_failed = bool(payload.get("has_failed"))
    exit_code = 1 if has_failed and bool(args.strict) else 0
    payload["ok"] = not has_failed or not bool(args.strict)
    payload["strict_mode"] = bool(args.strict)

    write_output_file(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
