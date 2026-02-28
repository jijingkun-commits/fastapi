#!/usr/bin/env python3
"""Deterministic kernel for coder4 card bootstrap/dispatch decisions.

This script computes a single action for the current scoped task chain:
- preflight_blocked
- seed
- activate
- dispatch
- blocked_depends
- all_done

Optional bootstrap apply mode can create/activate one card:
- VK API mode (default)
- local-mode state file (when --local-mode is enabled)
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib import error, parse, request


DEFAULT_ACTIVE_TASK = (
    "/Users/jijingkun/bojxAI/fastapi/docs/内部参考/任务拆解/_active_task.json"
)
DEFAULT_API_BASE = "http://127.0.0.1:3001"
DEFAULT_STATE_FILE = ".omc/state/task-runner-state.json"
DEFAULT_RUN_LOCK_FILE = ".omc/state/coder4-run.lock"
DEFAULT_IDEMPOTENCY_FILE = ".omc/state/coder4-idempotency.json"
DEFAULT_IDEMPOTENCY_WINDOW_SECONDS = 120
IDEMPOTENCY_RETENTION_MULTIPLIER = 3

RUN_LOCK_DISABLE_ENV = "DISABLE_RUN_LOCK"
IDEMPOTENCY_DISABLE_ENV = "DISABLE_IDEMPOTENCY_WINDOW"

EVENT_RUN_LOCK_ACQUIRED = "RUN_LOCK_ACQUIRED"
EVENT_SKIP_DUPLICATE = "SKIP_DUPLICATE_EVENT"

STATUS_ORDER = {
    "inprogress": 0,
    "inreview": 1,
    "todo": 2,
    "done": 3,
    "cancelled": 4,
}
COUNT_STATUSES = ("todo", "inprogress", "inreview", "done")


@dataclass
class KernelContext:
    project_id: str
    task_key: str
    preflight_required: str
    preflight_ok: bool
    preflight_reason: str
    card_order: list[str]
    cards_by_id: dict[str, dict[str, Any]]
    scoped_tasks: list[dict[str, Any]]
    unscoped_tasks: list[dict[str, Any]]
    card_status_map: dict[str, str]
    card_task_map: dict[str, dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="coder4 deterministic bootstrap kernel")
    parser.add_argument("--active-task", default=DEFAULT_ACTIVE_TASK)
    parser.add_argument("--vk-api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--local-mode", action="store_true", default=False)
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    parser.add_argument("--run-lock-file", default=DEFAULT_RUN_LOCK_FILE)
    parser.add_argument("--idempotency-file", default=DEFAULT_IDEMPOTENCY_FILE)
    parser.add_argument("--apply-bootstrap", action="store_true")
    parser.add_argument("--trigger-source", default=os.getenv("CODER4_TRIGGER_SOURCE", "wake"))
    parser.add_argument("--idempotency-key", default="")
    parser.add_argument("--idempotency-window-seconds", type=int, default=DEFAULT_IDEMPOTENCY_WINDOW_SECONDS)
    parser.add_argument("--output", default="")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".kernel_", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def is_disabled_by_env(name: str) -> bool:
    raw = str(os.getenv(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def normalize_trigger_source(value: str) -> str:
    source = str(value or "").strip().lower()
    if not source:
        return "manual"
    if source in {"wake", "agent", "cron", "watchdog"}:
        return "hooks"
    return source


def _normalize_window_seconds(value: int) -> int:
    if value <= 0:
        return DEFAULT_IDEMPOTENCY_WINDOW_SECONDS
    return value


def build_idempotency_key(
    *,
    trigger_source: str,
    task_key: str,
    card_id: str | None,
    action: str,
    status: str | None,
    explicit_key: str = "",
) -> str:
    explicit = str(explicit_key or "").strip()
    if explicit:
        return hashlib.sha256(explicit.encode("utf-8")).hexdigest()

    normalized_trigger = normalize_trigger_source(trigger_source)
    raw = "|".join(
        [
            normalized_trigger,
            str(task_key or "").strip() or "-",
            str(card_id or "").strip().upper() or "-",
            str(action or "").strip() or "-",
            str(status or "").strip() or "-",
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_idempotency_state(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    try:
        data = load_json(path)
    except Exception:  # noqa: BLE001
        return {}

    parsed: dict[str, float] = {}
    for key, value in data.items():
        idempotency_key = str(key or "").strip()
        if not idempotency_key:
            continue
        try:
            ts = float(value)
        except (TypeError, ValueError):
            continue
        if ts > 0:
            parsed[idempotency_key] = ts
    return parsed


def should_skip_duplicate(
    *,
    key: str,
    now_ts: float,
    idempotency_file: Path,
    window_seconds: int,
) -> tuple[bool, float | None]:
    idempotency_file.parent.mkdir(parents=True, exist_ok=True)
    state = _load_idempotency_state(idempotency_file)

    retention_seconds = max(
        window_seconds * IDEMPOTENCY_RETENTION_MULTIPLIER,
        window_seconds + 1,
    )
    threshold = now_ts - retention_seconds

    compacted = {
        existing_key: ts for existing_key, ts in state.items() if ts >= threshold
    }

    last_ts = compacted.get(key)
    if last_ts is not None and now_ts <= (last_ts + window_seconds):
        return True, last_ts

    compacted[key] = now_ts
    atomic_write_json(idempotency_file, compacted)
    return False, last_ts


@contextmanager
def with_run_lock(lock_file: Path) -> Iterator[bool]:
    if is_disabled_by_env(RUN_LOCK_DISABLE_ENV):
        yield True
        return

    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with lock_file.open("w", encoding="utf-8") as lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return

        try:
            yield True
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def emit_event(event: str, **fields: Any) -> None:
    payload = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)


def write_output_file(output_path: str, payload: dict[str, Any]) -> None:
    if not output_path:
        return
    write_json(Path(output_path).resolve(), payload)


def build_skip_duplicate_result(
    *,
    reason: str,
    trigger_source: str,
    run_lock_file: Path,
    idempotency_file: Path,
    idempotency_window_seconds: int,
    state_file: Path,
    task_key: str,
    idempotency_key: str,
    local_mode: bool,
) -> dict[str, Any]:
    return {
        "ok": True,
        "action": "skip_duplicate_event",
        "event": EVENT_SKIP_DUPLICATE,
        "reason": reason,
        "task_key": task_key,
        "trigger_source": trigger_source,
        "run_lock_file": str(run_lock_file),
        "idempotency_file": str(idempotency_file),
        "idempotency_window_seconds": idempotency_window_seconds,
        "idempotency_key": idempotency_key,
        "applied": {"performed": False},
        "local_mode": local_mode,
        "state_file": str(state_file),
    }


def _normalize_card_status_map(raw_map: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in raw_map.items():
        cid = str(key or "").strip().upper()
        if not cid:
            continue
        normalized[cid] = normalize_status(value)
    return normalized


def load_local_state(state_path: Path, task_key: str, card_order: list[str]) -> dict[str, Any]:
    if state_path.exists():
        state = load_json(state_path)
    else:
        state = {}
    if not isinstance(state, dict):
        state = {}
    raw_map = state.get("card_status_map")
    if not isinstance(raw_map, dict):
        raw_map = state.get("card_status") if isinstance(state.get("card_status"), dict) else {}
    card_status_map = _normalize_card_status_map(raw_map if isinstance(raw_map, dict) else {})
    return {
        "schema_version": str(state.get("schema_version") or "1.0.0"),
        "task_key": str(state.get("task_key") or task_key),
        "card_order": [str(x).strip().upper() for x in (state.get("card_order") or card_order)],
        "card_status_map": card_status_map,
        "last_updated": str(state.get("last_updated") or ""),
        "created_at": str(state.get("created_at") or ""),
    }


def update_local_card_status(
    state_path: Path,
    *,
    task_key: str,
    card_order: list[str],
    card_id: str,
    status: str,
) -> dict[str, Any]:
    state = load_local_state(state_path, task_key, card_order)
    state["schema_version"] = "1.0.0"
    state["task_key"] = task_key
    state["card_order"] = card_order
    status_map = dict(state.get("card_status_map") or {})
    status_map[card_id] = status
    state["card_status_map"] = status_map
    now = datetime.now(timezone.utc).isoformat()
    if not state.get("created_at"):
        state["created_at"] = now
    state["last_updated"] = now
    atomic_write_json(state_path, state)
    return state


def normalize_status(raw: Any) -> str:
    s = str(raw or "").strip().lower().replace("-", "_")
    if s == "in_progress":
        return "inprogress"
    if s == "in_review":
        return "inreview"
    if s in {"backlog", "to_do"}:
        return "todo"
    return s


def http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=20) as resp:
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


def extract_card_id(task: dict[str, Any]) -> str | None:
    desc = str(task.get("description") or "")
    for line in desc.splitlines():
        if line.lower().startswith("card_id:"):
            cid = line.split(":", 1)[1].strip().upper()
            if re.fullmatch(r"[CG]\d{2}", cid):
                return cid
    title = str(task.get("title") or "")
    m = re.search(r"\b([CG]\d{2})\b", title.upper())
    if m:
        return m.group(1)
    return None


def parse_time(value: Any) -> str:
    return str(value or "")


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
            repo_root
            / "docs"
            / "内部参考"
            / "任务拆解"
            / task_split_dir
            / "vk_cards.json"
        )

    # backward compatibility for old layouts
    if repo_root is not None:
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


def resolve_runtime_file_path(active_task_path: Path, raw_path: str) -> Path:
    target_path = Path(raw_path).expanduser()
    if target_path.is_absolute():
        return target_path.resolve()
    for ancestor in active_task_path.parents:
        if (ancestor / ".git").exists():
            return (ancestor / target_path).resolve()
    return (Path.cwd() / target_path).resolve()


def resolve_state_file_path(active_task_path: Path, raw_state_file: str) -> Path:
    return resolve_runtime_file_path(active_task_path, raw_state_file)


def pick_task_for_card(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    def key_fn(t: dict[str, Any]) -> tuple[int, str]:
        st = normalize_status(t.get("status"))
        rank = STATUS_ORDER.get(st, 99)
        updated = parse_time(t.get("updated_at") or t.get("updatedAt"))
        return (rank, updated)

    # Lowest rank first; latest updated wins inside same rank.
    tasks_sorted = sorted(tasks, key=lambda t: (key_fn(t)[0], key_fn(t)[1]), reverse=False)
    if not tasks_sorted:
        raise ValueError("empty tasks for card")
    same_rank = [t for t in tasks_sorted if key_fn(t)[0] == key_fn(tasks_sorted[0])[0]]
    same_rank.sort(key=lambda t: parse_time(t.get("updated_at") or t.get("updatedAt")), reverse=True)
    return same_rank[0]


def list_tasks(api_base: str, project_id: str) -> list[dict[str, Any]]:
    q = parse.urlencode({"project_id": project_id})
    payload = http_json("GET", f"{api_base}/api/tasks?{q}")
    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError("invalid /api/tasks response: data is not list")
    return data


def count_statuses(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {k: 0 for k in COUNT_STATUSES}
    for task in tasks:
        st = normalize_status(task.get("status"))
        if st in counts:
            counts[st] += 1
    return counts


def build_kernel_context(
    active_task_path: Path,
    api_base: str,
    *,
    local_mode: bool = False,
    state_path: Path | None = None,
) -> KernelContext:
    active = load_json(active_task_path)
    project_id = str(active.get("project_id") or "").strip()
    task_split_dir = str(active.get("task_split_dir") or "").strip()
    task_key = str(active.get("task_key") or "").strip()
    preflight_required = str(active.get("preflight_required") or "").strip() or "C00"
    if not task_split_dir or not task_key:
        raise ValueError("active task missing task_split_dir/task_key")
    if not local_mode and not project_id:
        raise ValueError("active task missing project_id (required when local-mode is disabled)")

    vk_cards_path = resolve_vk_cards_path(active_task_path, active, task_split_dir)
    vk_cards = load_json(vk_cards_path)
    card_order = [str(x) for x in vk_cards.get("card_order") or []]
    cards = vk_cards.get("cards") or []
    cards_by_id: dict[str, dict[str, Any]] = {}
    for card in cards:
        cid = str(card.get("card_id") or "").strip().upper()
        if cid:
            cards_by_id[cid] = card

    scoped: list[dict[str, Any]] = []
    unscoped: list[dict[str, Any]] = []
    card_status_map: dict[str, str] = {}
    card_task_map: dict[str, dict[str, Any]] = {}

    if local_mode:
        if state_path is None:
            for ancestor in active_task_path.parents:
                if (ancestor / ".git").exists():
                    state_path = (ancestor / DEFAULT_STATE_FILE).resolve()
                    break
            if state_path is None:
                state_path = (Path.cwd() / DEFAULT_STATE_FILE).resolve()
        local_state = load_local_state(state_path, task_key, card_order)
        state_map = dict(local_state.get("card_status_map") or {})
        for cid in card_order:
            status = normalize_status(state_map.get(cid))
            if not status:
                card_status_map[cid] = "missing"
                continue
            card_status_map[cid] = status
            pseudo_task = {
                "id": cid,
                "title": f"{cid} [{task_key}]",
                "status": status,
                "updated_at": str(local_state.get("last_updated") or ""),
            }
            card_task_map[cid] = pseudo_task
            scoped.append(pseudo_task)
    else:
        board_tasks = list_tasks(api_base, project_id)
        for t in board_tasks:
            title = str(t.get("title") or "")
            desc = str(t.get("description") or "")
            if task_key in title or task_key in desc:
                scoped.append(t)
            else:
                unscoped.append(t)

        by_card: dict[str, list[dict[str, Any]]] = {}
        for task in scoped:
            cid = extract_card_id(task)
            if cid:
                by_card.setdefault(cid, []).append(task)

        for cid in card_order:
            tasks = by_card.get(cid, [])
            if not tasks:
                card_status_map[cid] = "missing"
                continue
            selected = pick_task_for_card(tasks)
            card_task_map[cid] = selected
            card_status_map[cid] = normalize_status(selected.get("status"))

    preflight_ok = False
    preflight_reason = f"{preflight_required}_not_done"
    if preflight_required in card_status_map and card_status_map[preflight_required] == "done":
        preflight_ok = True
        preflight_reason = "preflight_card_done"
    else:
        source = str(active.get("status_source_of_truth") or "").strip()
        if source:
            source_path = Path(source)
            if source_path.exists():
                if source_path.suffix.lower() == ".json":
                    try:
                        source_payload = load_json(source_path)
                        src_req = str(source_payload.get("preflight_required") or "").strip()
                        src_pass = bool(source_payload.get("passed"))
                        if src_pass and (not src_req or src_req == preflight_required):
                            preflight_ok = True
                            preflight_reason = "preflight_doc_passed_json"
                    except Exception:  # noqa: BLE001
                        preflight_ok = False
                else:
                    text = source_path.read_text(encoding="utf-8", errors="ignore")
                    marker = re.search(
                        rf"{re.escape(preflight_required)}\s*已通过.*可进入",
                        text,
                        flags=re.IGNORECASE | re.DOTALL,
                    )
                    if marker:
                        preflight_ok = True
                        preflight_reason = "preflight_doc_passed_text"

    return KernelContext(
        project_id=project_id,
        task_key=task_key,
        preflight_required=preflight_required,
        preflight_ok=preflight_ok,
        preflight_reason=preflight_reason,
        card_order=card_order,
        cards_by_id=cards_by_id,
        scoped_tasks=scoped,
        unscoped_tasks=unscoped,
        card_status_map=card_status_map,
        card_task_map=card_task_map,
    )


def deps_ready(card_id: str, ctx: KernelContext) -> tuple[bool, list[str]]:
    card = ctx.cards_by_id.get(card_id) or {}
    hard = card.get("hard_depends_on") or []
    missing: list[str] = []
    for dep in hard:
        dep_id = str(dep).strip().upper()
        if not dep_id:
            continue
        if ctx.card_status_map.get(dep_id) != "done":
            missing.append(dep_id)
    return (len(missing) == 0, missing)


def decide_action(ctx: KernelContext) -> tuple[str, str | None, str | None, str | None, list[dict[str, Any]]]:
    if not ctx.preflight_ok:
        return ("preflight_blocked", None, None, None, [])

    blocked_details: list[dict[str, Any]] = []
    for cid in ctx.card_order:
        status = ctx.card_status_map.get(cid, "missing")
        if status == "done":
            continue
        target_task = ctx.card_task_map.get(cid)
        target_task_id = str(target_task.get("id")) if target_task else None
        if status == "missing":
            ok, missing = deps_ready(cid, ctx)
            if ok:
                return ("seed", cid, target_task_id, "missing", blocked_details)
            blocked_details.append({"card_id": cid, "status": status, "missing_depends": missing})
            return ("blocked_depends", cid, target_task_id, status, blocked_details)
        if status == "todo":
            ok, missing = deps_ready(cid, ctx)
            if ok:
                return ("activate", cid, target_task_id, "todo", blocked_details)
            blocked_details.append({"card_id": cid, "status": status, "missing_depends": missing})
            return ("blocked_depends", cid, target_task_id, status, blocked_details)
        if status in {"inprogress", "inreview"}:
            return ("dispatch", cid, target_task_id, status, blocked_details)
        blocked_details.append({"card_id": cid, "status": status, "reason": "unsupported_status"})
        return ("blocked_depends", cid, target_task_id, status, blocked_details)

    return ("all_done", None, None, None, [])


def build_card_description(card: dict[str, Any], task_key: str) -> str:
    lines = [
        f"card_id: {card.get('card_id')}",
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


def apply_action(
    api_base: str,
    ctx: KernelContext,
    action: str,
    target_card_id: str | None,
    target_task_id: str | None,
    *,
    local_mode: bool = False,
    state_path: Path | None = None,
) -> dict[str, Any]:
    if action == "seed":
        if not target_card_id:
            raise RuntimeError("seed action missing target_card_id")
        card = ctx.cards_by_id.get(target_card_id)
        if not card:
            raise RuntimeError(f"card definition not found: {target_card_id}")
        if local_mode:
            if state_path is None:
                raise RuntimeError("state_path is required when local-mode is enabled")
            update_local_card_status(
                state_path,
                task_key=ctx.task_key,
                card_order=ctx.card_order,
                card_id=target_card_id,
                status="todo",
            )
            return {
                "performed": True,
                "action": "seed",
                "card_id": target_card_id,
                "task_id": target_card_id,
                "status": "todo",
            }
        payload = {
            "project_id": ctx.project_id,
            "title": str(card.get("title") or f"{target_card_id} [{ctx.task_key}]"),
            "description": build_card_description(card, ctx.task_key),
            "status": "todo",
        }
        resp = http_json("POST", f"{api_base}/api/tasks", payload)
        data = resp.get("data") or {}
        return {
            "performed": True,
            "action": "seed",
            "card_id": target_card_id,
            "task_id": data.get("id"),
            "status": data.get("status") or "todo",
        }

    if action == "activate":
        if not target_card_id:
            raise RuntimeError("activate action missing target identifiers")
        if local_mode:
            if state_path is None:
                raise RuntimeError("state_path is required when local-mode is enabled")
            update_local_card_status(
                state_path,
                task_key=ctx.task_key,
                card_order=ctx.card_order,
                card_id=target_card_id,
                status="inprogress",
            )
            return {
                "performed": True,
                "action": "activate",
                "card_id": target_card_id,
                "task_id": target_card_id,
                "status": "inprogress",
            }
        if not target_task_id:
            raise RuntimeError("activate action missing target identifiers")
        payload = {"status": "inprogress"}
        resp = http_json("PUT", f"{api_base}/api/tasks/{target_task_id}", payload)
        data = resp.get("data") or {}
        return {
            "performed": True,
            "action": "activate",
            "card_id": target_card_id,
            "task_id": target_task_id,
            "status": data.get("status") or "inprogress",
        }

    return {"performed": False}


def main() -> int:
    args = parse_args()
    active_task_path = Path(args.active_task).resolve()
    if not active_task_path.exists():
        payload = {
            "ok": False,
            "action": "kernel_error",
            "error": f"active task not found: {active_task_path}",
        }
        write_output_file(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    state_path = resolve_state_file_path(active_task_path, args.state_file)
    run_lock_file = resolve_runtime_file_path(active_task_path, args.run_lock_file)
    idempotency_file = resolve_runtime_file_path(active_task_path, args.idempotency_file)
    trigger_source = normalize_trigger_source(args.trigger_source)
    explicit_idempotency_key = str(args.idempotency_key or "").strip()
    idempotency_window_seconds = _normalize_window_seconds(args.idempotency_window_seconds)
    run_lock_disabled = is_disabled_by_env(RUN_LOCK_DISABLE_ENV)
    idempotency_disabled = is_disabled_by_env(IDEMPOTENCY_DISABLE_ENV)

    try:
        with with_run_lock(run_lock_file) as lock_acquired:
            if not lock_acquired:
                emit_event(
                    EVENT_SKIP_DUPLICATE,
                    reason="run_lock_busy",
                    trigger_source=trigger_source,
                    run_lock_file=str(run_lock_file),
                )
                result = build_skip_duplicate_result(
                    reason="run_lock_busy",
                    trigger_source=trigger_source,
                    run_lock_file=run_lock_file,
                    idempotency_file=idempotency_file,
                    idempotency_window_seconds=idempotency_window_seconds,
                    state_file=state_path,
                    task_key="",
                    idempotency_key="",
                    local_mode=args.local_mode,
                )
                write_output_file(args.output, result)
                print(json.dumps(result, ensure_ascii=False))
                return 0

            emit_event(
                EVENT_RUN_LOCK_ACQUIRED,
                trigger_source=trigger_source,
                run_lock_file=str(run_lock_file),
                lock_mode="disabled" if run_lock_disabled else "exclusive_nonblocking",
            )

            ctx = build_kernel_context(
                active_task_path,
                args.vk_api_base,
                local_mode=args.local_mode,
                state_path=state_path,
            )
            action, first_not_done, target_task_id, target_status, blocked_details = decide_action(ctx)

            idempotency_key = build_idempotency_key(
                trigger_source=trigger_source,
                task_key=ctx.task_key,
                card_id=first_not_done,
                action=action,
                status=target_status,
                explicit_key=explicit_idempotency_key,
            )
            should_check_idempotency = not idempotency_disabled and (
                bool(explicit_idempotency_key) or trigger_source != "manual"
            )

            if should_check_idempotency:
                now_ts = time.time()
                should_skip, previous_ts = should_skip_duplicate(
                    key=idempotency_key,
                    now_ts=now_ts,
                    idempotency_file=idempotency_file,
                    window_seconds=idempotency_window_seconds,
                )
                if should_skip:
                    emit_event(
                        EVENT_SKIP_DUPLICATE,
                        reason="idempotency_window",
                        trigger_source=trigger_source,
                        idempotency_key=idempotency_key,
                        previous_ts=previous_ts,
                        idempotency_window_seconds=idempotency_window_seconds,
                    )
                    result = build_skip_duplicate_result(
                        reason="idempotency_window",
                        trigger_source=trigger_source,
                        run_lock_file=run_lock_file,
                        idempotency_file=idempotency_file,
                        idempotency_window_seconds=idempotency_window_seconds,
                        state_file=state_path,
                        task_key=ctx.task_key,
                        idempotency_key=idempotency_key,
                        local_mode=args.local_mode,
                    )
                    result.update(
                        {
                            "project_id": ctx.project_id,
                            "preflight_required": ctx.preflight_required,
                            "preflight_ok": ctx.preflight_ok,
                            "preflight_reason": ctx.preflight_reason,
                            "target_card_id": first_not_done,
                            "target_task_id": target_task_id,
                            "target_status": target_status,
                        }
                    )
                    write_output_file(args.output, result)
                    print(json.dumps(result, ensure_ascii=False))
                    return 0

            applied = {"performed": False}
            if args.apply_bootstrap and action in {"seed", "activate"}:
                applied = apply_action(
                    args.vk_api_base,
                    ctx,
                    action,
                    first_not_done,
                    target_task_id,
                    local_mode=args.local_mode,
                    state_path=state_path,
                )

            scoped_counts = count_statuses(ctx.scoped_tasks)
            unscoped_counts = count_statuses(ctx.unscoped_tasks)
            result = {
                "ok": True,
                "project_id": ctx.project_id,
                "task_key": ctx.task_key,
                "preflight_required": ctx.preflight_required,
                "preflight_ok": ctx.preflight_ok,
                "preflight_reason": ctx.preflight_reason,
                "counts": {
                    "scoped": scoped_counts,
                    "unscoped": unscoped_counts,
                    "scoped_total": len(ctx.scoped_tasks),
                    "unscoped_total": len(ctx.unscoped_tasks),
                    "board_total": len(ctx.scoped_tasks) + len(ctx.unscoped_tasks),
                },
                "card_order": ctx.card_order,
                "action": action,
                "first_not_done": first_not_done,
                "target_card_id": first_not_done,
                "target_task_id": target_task_id,
                "target_status": target_status,
                "card_status_map": ctx.card_status_map,
                "blocked_details": blocked_details,
                "applied": applied,
                "run_lock": {
                    "enabled": not run_lock_disabled,
                    "file": str(run_lock_file),
                },
                "idempotency": {
                    "enabled": not idempotency_disabled,
                    "checked": should_check_idempotency,
                    "file": str(idempotency_file),
                    "window_seconds": idempotency_window_seconds,
                    "key": idempotency_key,
                },
                "local_mode": args.local_mode,
                "trigger_source": trigger_source,
                "state_file": str(state_path),
            }

            write_output_file(args.output, result)
            print(json.dumps(result, ensure_ascii=False))
            return 0
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "action": "kernel_error", "error": str(exc)}
        write_output_file(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
