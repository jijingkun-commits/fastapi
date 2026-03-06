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
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib import error, parse, request


def detect_repo_root(start: Path) -> Path:
    resolved = start.resolve()
    for ancestor in (resolved, *resolved.parents):
        if (ancestor / ".git").exists():
            return ancestor
    return resolved.parents[2]


SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from check_plan_vk_coverage import CoverageCheckError, run_check as run_plan_vk_coverage_check
import wtimp_dispatch_bridge


DEFAULT_REPO_ROOT = detect_repo_root(Path(__file__))
DEFAULT_API_BASE = "http://127.0.0.1:3001"
DEFAULT_STATE_FILE = ".state/{task_key}/task-runner-state.json"
DEFAULT_RUN_LOCK_FILE = ".state/{task_key}/coder4-run.lock"
DEFAULT_IDEMPOTENCY_FILE = ".state/{task_key}/coder4-idempotency.json"
DEFAULT_TASK_LEDGER_FILE = ".state/{task_key}/task-ledger.jsonl"
DEFAULT_IDEMPOTENCY_WINDOW_SECONDS = 120
IDEMPOTENCY_RETENTION_MULTIPLIER = 3
STATE_LOCK_SUFFIX = ".lock"
STATE_BACKUP_SUFFIX = ".bak"
DEFAULT_DIRTY_POLICY_VERSION = "v1_docs_templates"
DEFAULT_DISPATCH_EXECUTOR = "wtimp"
DEFAULT_DISPATCH_EXECUTOR_MODE = "cardrun_dispatch"
DEFAULT_DIRTY_WHITELIST = (
    "docs/plans/",
    "docs/内部参考/迭代需求/",
)

RUN_LOCK_DISABLE_ENV = "DISABLE_RUN_LOCK"
IDEMPOTENCY_DISABLE_ENV = "DISABLE_IDEMPOTENCY_WINDOW"
AUTO_WAKE_DISABLE_ENV = "DISABLE_AUTO_WAKE"
VK_SYNC_DISABLE_ENV = "DISABLE_VK_SYNC"
DIRTY_WHITELIST_ENV = "CODER4_DIRTY_WHITELIST"
OPENCLAW_GATEWAY_ENV = "OPENCLAW_GATEWAY"
OPENCLAW_HOOKS_TOKEN_ENV = "OPENCLAW_HOOKS_TOKEN"

DEFAULT_OPENCLAW_GATEWAY = "http://localhost:18789"
DEFAULT_OPENCLAW_CONFIG = Path("~/.openclaw-dev/openclaw.json").expanduser()
DEFAULT_AUTO_WAKE_TIMEOUT_SECONDS = 5

EVENT_RUN_LOCK_ACQUIRED = "RUN_LOCK_ACQUIRED"
EVENT_SKIP_DUPLICATE = "SKIP_DUPLICATE_EVENT"
EVENT_AUTO_WAKE_TRIGGERED = "AUTO_WAKE_TRIGGERED"
EVENT_AUTO_WAKE_FAILED = "AUTO_WAKE_FAILED"
EVENT_VK_SYNC_TRIGGERED = "VK_SYNC_TRIGGERED"
EVENT_VK_SYNC_FAILED = "VK_SYNC_FAILED"

STATUS_ORDER = {
    "inprogress": 0,
    "inreview": 1,
    "verified": 2,
    "todo": 3,
    "done": 4,
    "cancelled": 5,
}
COUNT_STATUSES = ("todo", "inprogress", "inreview", "verified", "done")


@dataclass
class KernelContext:
    project_id: str
    task_key: str
    execution_mode: str
    single_active_card: bool
    preflight_required: str
    preflight_ok: bool
    preflight_reason: str
    card_order: list[str]
    cards_by_id: dict[str, dict[str, Any]]
    scoped_tasks: list[dict[str, Any]]
    unscoped_tasks: list[dict[str, Any]]
    card_status_map: dict[str, str]
    card_task_map: dict[str, dict[str, Any]]
    scope_guard_ok: bool
    scope_guard_reason: str
    scope_guard_details: list[dict[str, Any]]
    main_repo_path: str
    main_repo_clean: bool
    main_repo_dirty_preview: list[str]
    main_repo_dirty_ignored_preview: list[str] = field(default_factory=list)
    main_repo_error: str | None = None
    dirty_policy_version: str = DEFAULT_DIRTY_POLICY_VERSION
    dirty_whitelist: list[str] = field(default_factory=lambda: list(DEFAULT_DIRTY_WHITELIST))
    dispatch_executor: str = DEFAULT_DISPATCH_EXECUTOR
    dispatch_executor_mode: str = DEFAULT_DISPATCH_EXECUTOR_MODE


class CardrunContractError(RuntimeError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="coder4 deterministic bootstrap kernel")
    parser.add_argument("--active-task", default=os.getenv("CODER4_ACTIVE_TASK_FILE", ""))
    parser.add_argument("--vk-api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--local-mode", action="store_true", default=False)
    parser.add_argument("--sync-vk-in-local-mode", action="store_true", default=False)
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    parser.add_argument("--task-ledger-file", default=DEFAULT_TASK_LEDGER_FILE)
    parser.add_argument("--run-lock-file", default=DEFAULT_RUN_LOCK_FILE)
    parser.add_argument("--idempotency-file", default=DEFAULT_IDEMPOTENCY_FILE)
    parser.add_argument("--apply-bootstrap", action="store_true")
    parser.add_argument("--trigger-source", default=os.getenv("CODER4_TRIGGER_SOURCE", "wake"))
    parser.add_argument("--idempotency-key", default="")
    parser.add_argument("--idempotency-window-seconds", type=int, default=DEFAULT_IDEMPOTENCY_WINDOW_SECONDS)
    parser.add_argument("--subagent-id", default="")
    parser.add_argument("--ws-file", default="")
    parser.add_argument("--commit-sha", default="")
    parser.add_argument("--merge-sha", default="")
    parser.add_argument("--dispatch-executor", default=os.getenv("CODER4_DISPATCH_EXECUTOR", ""))
    parser.add_argument("--dirty-whitelist", default=os.getenv(DIRTY_WHITELIST_ENV, ""))
    parser.add_argument("--dirty-policy-version", default=DEFAULT_DIRTY_POLICY_VERSION)
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


def _state_lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}{STATE_LOCK_SUFFIX}")


def _state_backup_path(path: Path) -> Path:
    return path.with_name(f"{path.name}{STATE_BACKUP_SUFFIX}")


@contextmanager
def with_file_lock(lock_file: Path, *, blocking: bool = True) -> Iterator[None]:
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with lock_file.open("a+", encoding="utf-8") as lock_fd:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        fcntl.flock(lock_fd, flags)
        try:
            yield
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
    *,
    backup_path: Path | None = None,
    create_backup: bool = True,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup_path is not None:
        backup_path.parent.mkdir(parents=True, exist_ok=True)

    backup_ready = False
    if backup_path is not None and create_backup and path.exists():
        shutil.copy2(path, backup_path)
        backup_ready = True

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
        if backup_ready and backup_path is not None and backup_path.exists():
            shutil.copy2(backup_path, path)
        raise


def _sanitize_path_segment(value: str, *, fallback: str) -> str:
    segment = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    segment = segment.strip("._")
    return segment or fallback


def render_task_scoped_path(raw_path: str, *, task_key: str) -> str:
    template = str(raw_path or "")
    if "{task_key}" not in template:
        return template
    scoped_task_key = _sanitize_path_segment(task_key, fallback="unknown_task")
    return template.replace("{task_key}", scoped_task_key)


def _normalize_attempt_card_id(card_id: str | None) -> str:
    normalized = str(card_id or "").strip().upper()
    if not normalized:
        return "SYSTEM"
    return _sanitize_path_segment(normalized, fallback="SYSTEM")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _state_lock_path(path)
    with with_file_lock(lock_path):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())


def _derive_attempt_result(action: str, *, applied_performed: bool, reason: str | None = None) -> str:
    if reason:
        return reason
    if action == "seed":
        return "card_seeded" if applied_performed else "seed_pending_apply"
    if action == "activate":
        return "card_activated" if applied_performed else "activate_pending_apply"
    if action == "dispatch":
        return "dispatch_executed" if applied_performed else "dispatch_pending"
    if action == "awaiting_merge":
        return "verified_waiting_merge"
    if action == "blocked_depends":
        return "blocked_depends"
    if action == "preflight_blocked":
        return "preflight_blocked"
    if action == "all_done":
        return "all_done"
    return action or "unknown"


def record_attempt_evidence(
    *,
    ledger_file: Path,
    task_key: str,
    card_id: str | None,
    action: str,
    result: str,
    trigger_source: str,
    started_at: datetime,
    ended_at: datetime,
    target_status: str | None = None,
    applied: dict[str, Any] | None = None,
    auto_wake: dict[str, Any] | None = None,
    blocked_details: list[dict[str, Any]] | None = None,
    idempotency_key: str = "",
    execution_mode: str = "serial",
    worktree_path: str | None = None,
    commit_sha: str | None = None,
    merge_sha: str | None = None,
    subagent_id: str | None = None,
    ws_file: str | None = None,
    executor_mode: str | None = None,
) -> dict[str, Any]:
    normalized_card_id = _normalize_attempt_card_id(card_id)

    if not commit_sha and isinstance(applied, dict):
        raw_sha = str(applied.get("commit_sha") or "").strip()
        commit_sha = raw_sha or None
    if not merge_sha and isinstance(applied, dict):
        raw_merge_sha = str(applied.get("merge_sha") or "").strip()
        merge_sha = raw_merge_sha or None
    if not subagent_id and isinstance(applied, dict):
        raw_subagent_id = str(applied.get("subagent_id") or "").strip()
        subagent_id = raw_subagent_id or None
    if not ws_file and isinstance(applied, dict):
        raw_ws_file = str(applied.get("ws_file") or "").strip()
        ws_file = raw_ws_file or None
    if not executor_mode and isinstance(applied, dict):
        raw_executor_mode = str(applied.get("executor_mode") or "").strip()
        executor_mode = raw_executor_mode or None

    execution_evidence = {
        "executor_mode": executor_mode,
        "subagent_id": subagent_id,
        "ws_file": ws_file,
        "commit_sha": commit_sha,
        "merge_sha": merge_sha,
    }

    evidence = {
        "target_status": target_status,
        "applied": applied or {"performed": False},
        "auto_wake": auto_wake or {},
        "blocked_details": blocked_details or [],
        "idempotency_key": idempotency_key,
    }

    duration_seconds = max(0, int((ended_at - started_at).total_seconds()))
    attempt_payload = {
        "attempt_id": f"attempt_{int(time.time_ns())}",
        "task_key": str(task_key or ""),
        "card_id": normalized_card_id,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "result": result,
        "action": action,
        "evidence": evidence,
        "worktree_path": str(worktree_path or Path.cwd().resolve()),
        "commit_sha": commit_sha,
        "merge_sha": merge_sha,
        "subagent_id": subagent_id,
        "ws_file": ws_file,
        "execution_evidence": execution_evidence,
        "execution_mode": str(execution_mode or "serial"),
        "trigger": str(trigger_source or "manual"),
        "duration_seconds": duration_seconds,
    }

    ledger_entry = {
        "ts": ended_at.isoformat(),
        "event": "kernel_round",
        "task_key": str(task_key or ""),
        "card_id": normalized_card_id,
        "attempt_id": attempt_payload["attempt_id"],
        "action": action,
        "result": result,
        "target_status": target_status,
        "trigger_source": str(trigger_source or "manual"),
        "execution_mode": str(execution_mode or "serial"),
        "worktree_path": attempt_payload["worktree_path"],
        "commit_sha": commit_sha,
        "merge_sha": merge_sha,
        "subagent_id": subagent_id,
        "ws_file": ws_file,
        "execution_evidence": execution_evidence,
        "evidence": evidence,
    }
    append_jsonl(ledger_file, ledger_entry)
    return {
        "attempt": attempt_payload,
        "ledger_entry": ledger_entry,
    }


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


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return load_json(path)
    except Exception:  # noqa: BLE001
        return None


def _recover_local_state_from_backup(
    state_path: Path,
    backup_path: Path,
    backup_state: dict[str, Any],
    *,
    lock_held: bool,
) -> dict[str, Any]:
    def _restore() -> dict[str, Any]:
        current_state = _safe_load_json(state_path)
        if current_state is not None:
            return current_state
        atomic_write_json(
            state_path,
            backup_state,
            backup_path=backup_path,
            create_backup=False,
        )
        return backup_state

    if lock_held:
        return _restore()

    with with_file_lock(_state_lock_path(state_path)):
        return _restore()


def load_local_state(
    state_path: Path,
    task_key: str,
    card_order: list[str],
    *,
    lock_held: bool = False,
) -> dict[str, Any]:
    backup_path = _state_backup_path(state_path)
    state = _safe_load_json(state_path)
    if state is None:
        backup_state = _safe_load_json(backup_path)
        if backup_state is not None:
            state = _recover_local_state_from_backup(
                state_path,
                backup_path,
                backup_state,
                lock_held=lock_held,
            )
        else:
            state = {}
    if not isinstance(state, dict):
        state = {}

    normalized_state = dict(state)
    raw_map = normalized_state.get("card_status_map")
    if not isinstance(raw_map, dict):
        raw_map = normalized_state.get("card_status") if isinstance(normalized_state.get("card_status"), dict) else {}
    card_status_map = _normalize_card_status_map(raw_map if isinstance(raw_map, dict) else {})

    normalized_state["schema_version"] = str(normalized_state.get("schema_version") or "1.0.0")
    normalized_state["task_key"] = str(normalized_state.get("task_key") or task_key)
    normalized_state["card_order"] = [str(x).strip().upper() for x in (normalized_state.get("card_order") or card_order)]
    normalized_state["card_status_map"] = card_status_map
    normalized_state["card_status"] = dict(card_status_map)
    normalized_state["last_updated"] = str(normalized_state.get("last_updated") or "")
    normalized_state["created_at"] = str(normalized_state.get("created_at") or "")
    return normalized_state


def update_local_card_status(
    state_path: Path,
    *,
    task_key: str,
    card_order: list[str],
    card_id: str,
    status: str,
    action: str | None = None,
    action_result: str | None = None,
    current_card: str | None = None,
) -> dict[str, Any]:
    lock_path = _state_lock_path(state_path)
    backup_path = _state_backup_path(state_path)
    normalized_card_id = str(card_id or "").strip().upper()
    if not normalized_card_id:
        raise ValueError("card_id is required")
    normalized_status = normalize_status(status)

    with with_file_lock(lock_path):
        state = load_local_state(state_path, task_key, card_order, lock_held=True)
        state["schema_version"] = "1.0.0"
        state["task_key"] = task_key
        state["card_order"] = card_order
        status_map = dict(state.get("card_status_map") or {})
        status_map[normalized_card_id] = normalized_status
        state["card_status_map"] = status_map
        state["card_status"] = dict(status_map)
        state["current_card"] = str(current_card or normalized_card_id).strip().upper()
        if action:
            state["last_action"] = str(action).strip().lower()
        if action_result:
            state["last_action_result"] = str(action_result).strip()
        now = datetime.now(timezone.utc).isoformat()
        if not state.get("created_at"):
            state["created_at"] = now
        state["last_updated"] = now
        atomic_write_json(state_path, state, backup_path=backup_path)
        return state


def pick_pending_auto_wake_card(local_state: dict[str, Any], card_order: list[str]) -> str | None:
    status_map = dict(local_state.get("card_status_map") or {})
    done_cards = [
        str(cid).strip().upper()
        for cid in card_order
        if normalize_status(status_map.get(cid)) == "done"
    ]
    if not done_cards:
        return None

    latest_done_card = done_cards[-1]
    last_auto_wake_card = str(local_state.get("last_auto_wake_card") or "").strip().upper()
    if last_auto_wake_card == latest_done_card:
        return None
    return latest_done_card


def mark_local_auto_wake(
    state_path: Path,
    *,
    task_key: str,
    card_order: list[str],
    card_id: str,
) -> dict[str, Any]:
    lock_path = _state_lock_path(state_path)
    backup_path = _state_backup_path(state_path)

    with with_file_lock(lock_path):
        state = load_local_state(state_path, task_key, card_order, lock_held=True)
        now = datetime.now(timezone.utc).isoformat()
        state["last_auto_wake_card"] = str(card_id).strip().upper()
        state["last_auto_wake_at"] = now
        if not state.get("created_at"):
            state["created_at"] = now
        state["last_updated"] = now
        atomic_write_json(state_path, state, backup_path=backup_path)
        return state


def resolve_openclaw_gateway() -> str:
    env_gateway = str(os.getenv(OPENCLAW_GATEWAY_ENV) or "").strip()
    if env_gateway:
        return env_gateway.rstrip("/")

    if DEFAULT_OPENCLAW_CONFIG.exists():
        try:
            payload = load_json(DEFAULT_OPENCLAW_CONFIG)
            port_raw = payload.get("gateway", {}).get("port")
            port = int(port_raw)
            if port > 0:
                return f"http://localhost:{port}"
        except Exception:  # noqa: BLE001
            pass

    return DEFAULT_OPENCLAW_GATEWAY


def _build_hooks_headers() -> dict[str, str]:
    token = str(os.getenv(OPENCLAW_HOOKS_TOKEN_ENV) or "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def trigger_next_round(
    reason: str,
    *,
    timeout_seconds: int = DEFAULT_AUTO_WAKE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    gateway = resolve_openclaw_gateway()
    normalized_reason = str(reason or "").strip() or "card_done"
    if is_disabled_by_env(AUTO_WAKE_DISABLE_ENV):
        return {
            "attempted": False,
            "ok": False,
            "disabled": True,
            "reason": "disabled_by_env",
            "gateway": gateway,
        }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    headers.update(_build_hooks_headers())
    body = json.dumps({"text": normalized_reason, "mode": "now"}, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{gateway}/hooks/wake",
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            status_code = int(getattr(resp, "status", 200))
            resp.read()
        wake_result = {
            "attempted": True,
            "ok": 200 <= status_code < 300,
            "disabled": False,
            "status_code": status_code,
            "reason": normalized_reason,
            "gateway": gateway,
        }
        event_name = EVENT_AUTO_WAKE_TRIGGERED if wake_result["ok"] else EVENT_AUTO_WAKE_FAILED
        emit_event(event_name, reason=normalized_reason, status_code=status_code, gateway=gateway)
        return wake_result
    except error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="ignore")
        emit_event(
            EVENT_AUTO_WAKE_FAILED,
            reason=normalized_reason,
            status_code=exc.code,
            gateway=gateway,
            error=body_text[:300],
        )
        return {
            "attempted": True,
            "ok": False,
            "disabled": False,
            "status_code": exc.code,
            "reason": normalized_reason,
            "gateway": gateway,
            "error": body_text[:300],
        }
    except Exception as exc:  # noqa: BLE001
        emit_event(
            EVENT_AUTO_WAKE_FAILED,
            reason=normalized_reason,
            gateway=gateway,
            error=str(exc),
        )
        return {
            "attempted": True,
            "ok": False,
            "disabled": False,
            "reason": normalized_reason,
            "gateway": gateway,
            "error": str(exc),
        }


def _try_sync_vk(
    *,
    active_task_path: Path,
    state_path: Path | None,
    vk_api_base: str,
    project_id: str,
    task_key: str,
    card_id: str,
    status: str,
) -> dict[str, Any]:
    normalized_card_id = str(card_id or "").strip().upper()
    normalized_status = normalize_status(status)
    api_base = str(vk_api_base or "").strip().rstrip("/")

    if is_disabled_by_env(VK_SYNC_DISABLE_ENV):
        return {
            "attempted": False,
            "ok": False,
            "disabled": True,
            "reason": "disabled_by_env",
            "card_id": normalized_card_id,
            "status": normalized_status,
        }

    if not api_base:
        return {
            "attempted": False,
            "ok": False,
            "disabled": False,
            "reason": "missing_vk_api_base",
            "card_id": normalized_card_id,
            "status": normalized_status,
        }

    sync_script = resolve_runtime_file_path(active_task_path, "scripts/coder4/coder4_vk_sync.py")
    if not sync_script.exists():
        emit_event(
            EVENT_VK_SYNC_FAILED,
            reason="sync_script_missing",
            sync_script=str(sync_script),
            card_id=normalized_card_id,
            status=normalized_status,
        )
        return {
            "attempted": False,
            "ok": False,
            "disabled": False,
            "reason": "sync_script_missing",
            "sync_script": str(sync_script),
            "card_id": normalized_card_id,
            "status": normalized_status,
        }

    cmd = [
        sys.executable,
        str(sync_script),
        "--active-task",
        str(active_task_path),
        "--vk-api-base",
        api_base,
        "--card-id",
        normalized_card_id,
        "--status",
        normalized_status,
    ]

    if state_path is not None:
        cmd.extend(["--state-file", str(state_path)])
    if project_id:
        cmd.extend(["--project-id", str(project_id)])
    if task_key:
        cmd.extend(["--task-key", str(task_key)])

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:  # noqa: BLE001
        emit_event(
            EVENT_VK_SYNC_FAILED,
            reason="spawn_failed",
            sync_script=str(sync_script),
            card_id=normalized_card_id,
            status=normalized_status,
            error=str(exc),
        )
        return {
            "attempted": True,
            "ok": False,
            "disabled": False,
            "reason": "spawn_failed",
            "sync_script": str(sync_script),
            "card_id": normalized_card_id,
            "status": normalized_status,
            "error": str(exc),
        }

    emit_event(
        EVENT_VK_SYNC_TRIGGERED,
        sync_script=str(sync_script),
        card_id=normalized_card_id,
        status=normalized_status,
        pid=process.pid,
        api_base=api_base,
    )
    return {
        "attempted": True,
        "ok": True,
        "disabled": False,
        "reason": "spawned",
        "sync_script": str(sync_script),
        "card_id": normalized_card_id,
        "status": normalized_status,
        "pid": process.pid,
    }


def normalize_status(raw: Any) -> str:
    s = str(raw or "").strip().lower().replace("-", "_")
    if s == "in_progress":
        return "inprogress"
    if s == "in_review":
        return "inreview"
    if s in {"backlog", "to_do"}:
        return "todo"
    return s


def _normalize_contract_id(raw: Any) -> str:
    return str(raw or "").strip().upper()


def _normalize_contract_cmd(raw: Any) -> str:
    return " ".join(str(raw or "").strip().split())


def resolve_dispatch_executor(*, active_payload: dict[str, Any], cli_override: str = "") -> tuple[str, str]:
    raw_executor = str(cli_override or "").strip().lower()
    if not raw_executor:
        raw_executor = str(active_payload.get("dispatch_executor") or "").strip().lower()
    executor = raw_executor or DEFAULT_DISPATCH_EXECUTOR

    raw_mode = str(active_payload.get("dispatch_executor_mode") or "").strip().lower()
    mode = raw_mode or DEFAULT_DISPATCH_EXECUTOR_MODE
    return executor, mode


def _validate_vk_cards_contract(vk_cards: dict[str, Any], *, task_split_dir: str) -> None:
    execution_mode = str(vk_cards.get("execution_mode") or "").strip().lower()
    if execution_mode != "serial":
        raise CardrunContractError(
            "CARDRUN_NOT_SERIAL",
            f"task_split_dir={task_split_dir} execution_mode={execution_mode or 'missing'}，要求 serial",
            {"task_split_dir": task_split_dir, "execution_mode": execution_mode or "missing"},
        )

    card_order_raw = vk_cards.get("card_order")
    if not isinstance(card_order_raw, list) or not card_order_raw:
        raise CardrunContractError(
            "CARDRUN_CARD_ORDER_EMPTY",
            f"task_split_dir={task_split_dir} card_order 为空",
            {"task_split_dir": task_split_dir, "card_order": card_order_raw},
        )

    cards_raw = vk_cards.get("cards")
    if not isinstance(cards_raw, list) or not cards_raw:
        raise CardrunContractError(
            "CARDRUN_CARD_MAPPING_BROKEN",
            f"task_split_dir={task_split_dir} cards 为空",
            {"task_split_dir": task_split_dir, "cards_type": type(cards_raw).__name__},
        )

    cards_by_id: dict[str, dict[str, Any]] = {}
    duplicated_cards: list[str] = []
    for item in cards_raw:
        if not isinstance(item, dict):
            continue
        card_id = _normalize_contract_id(item.get("card_id"))
        if not card_id:
            continue
        if card_id in cards_by_id:
            duplicated_cards.append(card_id)
        cards_by_id[card_id] = item
    if duplicated_cards:
        raise CardrunContractError(
            "CARDRUN_CARD_MAPPING_BROKEN",
            f"task_split_dir={task_split_dir} 存在重复 card_id",
            {"task_split_dir": task_split_dir, "duplicate_card_ids": sorted(set(duplicated_cards))},
        )

    normalized_order = [_normalize_contract_id(cid) for cid in card_order_raw if _normalize_contract_id(cid)]
    missing_cards = [card_id for card_id in normalized_order if card_id not in cards_by_id]
    if missing_cards:
        raise CardrunContractError(
            "CARDRUN_CARD_MAPPING_BROKEN",
            f"task_split_dir={task_split_dir} card_order 与 cards 不一致",
            {"task_split_dir": task_split_dir, "missing_cards": missing_cards},
        )

    mapping_raw = vk_cards.get("task_to_pr_mapping")
    if not isinstance(mapping_raw, list) or not mapping_raw:
        raise CardrunContractError(
            "CARDRUN_PR_MAPPING_MISSING",
            f"task_split_dir={task_split_dir} 缺少 task_to_pr_mapping",
            {"task_split_dir": task_split_dir, "task_to_pr_mapping": mapping_raw},
        )

    task_to_pr: dict[str, str] = {}
    for item in mapping_raw:
        if not isinstance(item, dict):
            continue
        task_id = _normalize_contract_id(item.get("task_id"))
        pr_id = _normalize_contract_id(item.get("pr_id"))
        if task_id and pr_id:
            task_to_pr[task_id] = pr_id

    if not task_to_pr:
        raise CardrunContractError(
            "CARDRUN_PR_MAPPING_MISSING",
            f"task_split_dir={task_split_dir} task_to_pr_mapping 无有效 task_id/pr_id",
            {"task_split_dir": task_split_dir},
        )

    missing_task_ids: list[str] = []
    pr_mapping_issues: list[dict[str, Any]] = []
    for card_id in normalized_order:
        card = cards_by_id.get(card_id) or {}
        task_ids_raw = card.get("task_ids")
        task_ids = [
            _normalize_contract_id(task_id)
            for task_id in (task_ids_raw if isinstance(task_ids_raw, list) else [])
            if _normalize_contract_id(task_id)
        ]
        if not task_ids:
            missing_task_ids.append(card_id)
            continue

        card_pr_id = _normalize_contract_id(card.get("pr_id"))
        if not card_pr_id:
            pr_mapping_issues.append({"card_id": card_id, "reason": "missing_card_pr_id", "task_ids": task_ids})
            continue

        for task_id in task_ids:
            expected_pr_id = task_to_pr.get(task_id)
            if not expected_pr_id:
                pr_mapping_issues.append(
                    {
                        "card_id": card_id,
                        "task_id": task_id,
                        "reason": "missing_task_to_pr_mapping",
                    }
                )
                continue
            if expected_pr_id != card_pr_id:
                pr_mapping_issues.append(
                    {
                        "card_id": card_id,
                        "task_id": task_id,
                        "card_pr_id": card_pr_id,
                        "expected_pr_id": expected_pr_id,
                        "reason": "task_pr_mismatch",
                    }
                )

    if missing_task_ids:
        raise CardrunContractError(
            "CARDRUN_CONTRACT_INVALID",
            f"task_split_dir={task_split_dir} 存在缺失 task_ids 的卡片",
            {"task_split_dir": task_split_dir, "missing_task_ids_cards": missing_task_ids},
        )

    if pr_mapping_issues:
        raise CardrunContractError(
            "CARDRUN_CARD_MAPPING_BROKEN",
            f"task_split_dir={task_split_dir} card_id/task_ids/pr_id 映射不一致",
            {"task_split_dir": task_split_dir, "issues": pr_mapping_issues},
        )

    illegal_checks: list[dict[str, Any]] = []
    for card_id in normalized_order:
        card = cards_by_id.get(card_id) or {}
        acceptance_checks = card.get("acceptance_checks")
        if not isinstance(acceptance_checks, list):
            continue
        for check in acceptance_checks:
            normalized_check = _normalize_contract_cmd(check)
            if not normalized_check:
                continue
            if "active-session.json" in normalized_check:
                illegal_checks.append({"card_id": card_id, "check": normalized_check})
    if illegal_checks:
        raise CardrunContractError(
            "CARDRUN_CONTRACT_INVALID",
            f"task_split_dir={task_split_dir} acceptance_checks 命中旧会话文件路径",
            {"task_split_dir": task_split_dir, "illegal_checks": illegal_checks},
        )


def _run_coverage_gate(*, repo_root: Path, task_split_dir: str) -> dict[str, Any]:
    try:
        report = run_plan_vk_coverage_check(repo_root=repo_root, task_split_dir_raw=task_split_dir)
    except CoverageCheckError as exc:
        raise CardrunContractError(
            "CARDRUN_CONTRACT_INVALID",
            f"check_plan_vk_coverage 执行失败: {exc}",
            {"task_split_dir": task_split_dir},
        ) from exc

    if not bool(report.get("ok")):
        raise CardrunContractError(
            "CARDRUN_CONTRACT_INVALID",
            "check_plan_vk_coverage 未通过，阻断 cardrun 推进",
            {
                "task_split_dir": task_split_dir,
                "errors": report.get("errors") or report.get("error") or [],
                "missing_task_ids": report.get("missing_task_ids") or [],
                "missing_task_id_fields": report.get("missing_task_id_fields") or [],
                "empty_task_ids": report.get("empty_task_ids") or [],
            },
        )

    for field in ("missing_task_ids", "missing_task_id_fields", "empty_task_ids"):
        values = report.get(field)
        if isinstance(values, list) and values:
            raise CardrunContractError(
                "CARDRUN_CONTRACT_INVALID",
                f"coverage 命中 {field}，阻断 cardrun 推进",
                {"task_split_dir": task_split_dir, field: values},
            )

    clarify = report.get("clarify_plan_alignment")
    if isinstance(clarify, dict) and not bool(clarify.get("ok")):
        raise CardrunContractError(
            "CARDRUN_CONTRACT_INVALID",
            "coverage 命中 CLARIFY_PLAN_ALIGNMENT_FAILED，阻断 cardrun 推进",
            {
                "task_split_dir": task_split_dir,
                "clarify_plan_alignment": clarify,
            },
        )

    return report


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


def resolve_default_active_task(repo_root: Path) -> Path:
    split_root = repo_root / "docs" / "内部参考" / "任务拆解"
    candidates = [path for path in split_root.glob("*/_active_task.json") if path.is_file()]
    if not candidates:
        raise FileNotFoundError(
            "未找到任务级 _active_task.json，请显式传 --active-task 或设置 CODER4_ACTIVE_TASK_FILE"
        )
    if len(candidates) > 1:
        raise FileNotFoundError(
            f"检测到多个任务级 _active_task.json（{len(candidates)} 个），请显式传 --active-task 或设置 CODER4_ACTIVE_TASK_FILE"
        )
    return candidates[0].resolve()


def resolve_active_task_path(raw_active_task: str, repo_root: Path) -> Path:
    candidate = str(raw_active_task or "").strip()
    if candidate:
        path = Path(candidate).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"active task not found: {path}")
        return path
    return resolve_default_active_task(repo_root)


def resolve_vk_cards_path(active_task_path: Path) -> Path:
    vk_cards_path = (active_task_path.parent / "vk_cards.json").resolve()
    if vk_cards_path.exists():
        return vk_cards_path

    try:
        active_payload = load_json(active_task_path)
    except Exception:  # noqa: BLE001
        active_payload = {}

    task_split_dir = str(active_payload.get("task_split_dir") or "").strip()
    if task_split_dir:
        candidate = (active_task_path.parent / task_split_dir / "vk_cards.json").resolve()
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"vk_cards.json not found: {vk_cards_path}")


def resolve_runtime_file_path(active_task_path: Path, raw_path: str) -> Path:
    target_path = Path(raw_path).expanduser()
    if target_path.is_absolute():
        return target_path.resolve()
    normalized = str(raw_path or "").strip()
    if normalized == ".state" or normalized.startswith(".state/") or normalized.startswith("./.state/"):
        return (active_task_path.parent / target_path).resolve()
    for ancestor in active_task_path.parents:
        if (ancestor / ".git").exists():
            return (ancestor / target_path).resolve()
    return (Path.cwd() / target_path).resolve()


def sanitize_task_key_segment(task_key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", str(task_key or "").strip())
    normalized = normalized.strip("._")
    return normalized or "unknown_task"


def resolve_state_file_path(active_task_path: Path, raw_state_file: str) -> Path:
    return resolve_runtime_file_path(active_task_path, raw_state_file)


def resolve_repo_root(active_task_path: Path) -> Path:
    for ancestor in active_task_path.parents:
        if (ancestor / ".git").exists():
            return ancestor.resolve()
    return Path.cwd().resolve()


def resolve_task_scoped_active_task_path(active_task_path: Path, active_payload: dict[str, Any]) -> Path:
    task_split_dir = str(active_payload.get("task_split_dir") or "").strip()
    if not task_split_dir:
        raise ValueError(f"active task missing task_split_dir: {active_task_path}")
    if active_task_path.name != "_active_task.json":
        raise ValueError(f"active task file name invalid: {active_task_path}")
    if active_task_path.parent.name == task_split_dir:
        return active_task_path.resolve()

    candidate = (active_task_path.parent / task_split_dir / "_active_task.json").resolve()
    if candidate.exists():
        return candidate

    return active_task_path.resolve()


def resolve_card_source_ws_file(
    active_task_path: Path,
    *,
    target_card_id: str,
    card: dict[str, Any],
    ws_file_override: str | None = None,
) -> str:
    raw_ws_file = str(ws_file_override or card.get("source_ws_file") or "").strip()
    if not raw_ws_file:
        raise CardrunContractError(
            "CARDRUN_WS_MAPPING_BROKEN",
            f"card_id={target_card_id} 缺少 source_ws_file 映射",
            {"card_id": target_card_id},
        )

    repo_root = resolve_repo_root(active_task_path)
    ws_path = Path(raw_ws_file)
    resolved = ws_path.resolve() if ws_path.is_absolute() else (repo_root / ws_path).resolve()
    if not resolved.exists():
        raise CardrunContractError(
            "CARDRUN_WS_MAPPING_BROKEN",
            f"card_id={target_card_id} source_ws_file 不存在: {raw_ws_file}",
            {"card_id": target_card_id, "ws_file": raw_ws_file},
        )

    try:
        return str(resolved.relative_to(repo_root))
    except ValueError:
        return str(resolved)


def resolve_active_session_state_file(active_task_path: Path, *, task_key: str) -> Path:
    session_dir = active_task_path.parent / ".state" / sanitize_task_key_segment(task_key)
    session_id = str(os.getenv("WT_FLOW_SESSION_ID") or "").strip()
    if session_id:
        candidate = session_dir / f"active-session-{session_id}.json"
        if not candidate.exists():
            raise CardrunContractError(
                "CARDRUN_CONTEXT_INVALID",
                f"未找到指定会话状态文件: {candidate}",
                {"task_key": task_key, "session_id": session_id, "session_dir": str(session_dir)},
            )
        return candidate.resolve()

    session_files = sorted(session_dir.glob("active-session-*.json"))
    if len(session_files) == 1:
        return session_files[0].resolve()
    if len(session_files) > 1:
        raise CardrunContractError(
            "CARDRUN_CONTEXT_INVALID",
            f"检测到多个会话状态文件（{len(session_files)} 个），请显式设置 WT_FLOW_SESSION_ID",
            {"task_key": task_key, "session_dir": str(session_dir), "session_files": [str(path) for path in session_files]},
        )
    raise CardrunContractError(
        "CARDRUN_CONTEXT_INVALID",
        f"未找到会话状态文件: {session_dir}",
        {"task_key": task_key, "session_dir": str(session_dir)},
    )


def resolve_active_session_worktree_path(active_task_path: Path, *, task_key: str, expected_card_id: str) -> str:
    session_file = resolve_active_session_state_file(active_task_path, task_key=task_key)
    payload = load_json(session_file)
    worktree_path = str(payload.get("worktree") or "").strip()
    branch = str(payload.get("branch") or "").strip()
    if not worktree_path:
        raise CardrunContractError(
            "CARDRUN_CONTEXT_INVALID",
            f"会话状态缺少 worktree: {session_file}",
            {"task_key": task_key, "session_file": str(session_file)},
        )

    match = re.fullmatch(r"feature/(.+)/(.+)/(.+)", branch)
    if match:
        branch_task_key = sanitize_task_key_segment(match.group(1))
        branch_card_id = _normalize_contract_id(match.group(2))
        expected_task_key = sanitize_task_key_segment(task_key)
        normalized_expected_card_id = _normalize_contract_id(expected_card_id)
        if branch_task_key != expected_task_key or branch_card_id != normalized_expected_card_id:
            raise CardrunContractError(
                "CARDRUN_CONTEXT_INVALID",
                "会话分支卡片与当前 dispatch 卡片不一致",
                {
                    "task_key": task_key,
                    "expected_card_id": normalized_expected_card_id,
                    "branch": branch,
                    "session_file": str(session_file),
                },
            )

    resolved_worktree_path = Path(worktree_path).expanduser().resolve()
    if not resolved_worktree_path.exists():
        raise CardrunContractError(
            "CARDRUN_CONTEXT_INVALID",
            f"会话 worktree 不存在: {resolved_worktree_path}",
            {"task_key": task_key, "expected_card_id": expected_card_id, "session_file": str(session_file)},
        )
    return str(resolved_worktree_path)


def build_wtimp_dispatch_request(
    ctx: KernelContext,
    target_card_id: str,
    *,
    active_task_path: Path,
    ws_file_override: str | None = None,
) -> wtimp_dispatch_bridge.WtimpDispatchRequest:
    if not target_card_id:
        raise CardrunContractError(
            "CARDRUN_WS_MAPPING_BROKEN",
            "dispatch 缺少 card_id，无法构建 wtimp request",
            {},
        )
    card = ctx.cards_by_id.get(target_card_id) or {}
    ws_file = resolve_card_source_ws_file(
        active_task_path,
        target_card_id=target_card_id,
        card=card,
        ws_file_override=ws_file_override,
    )
    worktree_path = resolve_active_session_worktree_path(
        active_task_path,
        task_key=ctx.task_key,
        expected_card_id=target_card_id,
    )
    return wtimp_dispatch_bridge.WtimpDispatchRequest(
        task_key=ctx.task_key,
        card_id=target_card_id,
        ws_file=ws_file,
        worktree_path=worktree_path,
        executor_mode=str(ctx.dispatch_executor_mode or DEFAULT_DISPATCH_EXECUTOR_MODE),
    )


def run_wtimp_dispatch(
    request: wtimp_dispatch_bridge.WtimpDispatchRequest,
) -> wtimp_dispatch_bridge.WtimpDispatchResult:
    try:
        return wtimp_dispatch_bridge.run_dispatch(request)
    except wtimp_dispatch_bridge.WtimpDispatchError as exc:
        raise CardrunContractError(exc.code, str(exc), exc.details) from exc


def parse_dirty_whitelist(raw: str | None) -> list[str]:
    value = str(raw or "").strip()
    if not value:
        return list(DEFAULT_DIRTY_WHITELIST)

    parsed: list[str] = []
    for segment in value.split(","):
        prefix = segment.strip().strip("/")
        if not prefix:
            continue
        parsed.append(f"{prefix}/")
    return parsed or list(DEFAULT_DIRTY_WHITELIST)


def _extract_dirty_path(status_line: str) -> str:
    body = status_line[3:] if len(status_line) >= 3 else status_line
    if " -> " in body:
        body = body.split(" -> ", 1)[1]
    return body.strip()


def _is_whitelisted_dirty_path(path: str, whitelist: list[str]) -> bool:
    normalized = path.strip().lstrip("./")
    return any(normalized.startswith(prefix) for prefix in whitelist)


def inspect_repo_clean(
    repo_root: Path,
    *,
    dirty_whitelist: list[str],
) -> tuple[bool, list[str], list[str], str | None]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        detail = stderr or stdout or f"returncode={proc.returncode}"
        return False, [], [], f"git_status_failed:{detail}"

    disallowed_dirty: list[str] = []
    allowed_dirty: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = _extract_dirty_path(line)
        if path and _is_whitelisted_dirty_path(path, dirty_whitelist):
            allowed_dirty.append(line.rstrip())
        else:
            disallowed_dirty.append(line.rstrip())
    return len(disallowed_dirty) == 0, disallowed_dirty[:8], allowed_dirty[:8], None


def _task_preview(task: dict[str, Any]) -> dict[str, str]:
    title = str(task.get("title") or "").replace("\n", " ")
    return {
        "task_id": str(task.get("id") or ""),
        "status": normalize_status(task.get("status")),
        "title": title[:120],
    }


def evaluate_scope_guard(
    *,
    scoped_tasks: list[dict[str, Any]],
    unscoped_tasks: list[dict[str, Any]],
    single_active_card: bool,
) -> tuple[bool, str, list[dict[str, Any]]]:
    active_statuses = {"inprogress", "inreview", "verified"}
    unscoped_active = [
        task for task in unscoped_tasks if normalize_status(task.get("status")) in active_statuses
    ]
    if unscoped_active:
        return (
            False,
            "scope_conflict_unscoped_active",
            [
                {
                    "reason": "scope_conflict_unscoped_active",
                    "active_count": len(unscoped_active),
                    "tasks": [_task_preview(task) for task in unscoped_active[:6]],
                }
            ],
        )

    scoped_active = [
        task for task in scoped_tasks if normalize_status(task.get("status")) in active_statuses
    ]
    if single_active_card and len(scoped_active) > 1:
        return (
            False,
            "scope_conflict_multi_active_scoped",
            [
                {
                    "reason": "scope_conflict_multi_active_scoped",
                    "active_count": len(scoped_active),
                    "tasks": [_task_preview(task) for task in scoped_active[:6]],
                }
            ],
        )

    return True, "scope_guard_passed", []


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


def _preflight_passed_from_json(
    source_payload: dict[str, Any],
    *,
    preflight_required: str,
    task_key: str,
) -> bool:
    src_required = str(
        source_payload.get("preflight_required")
        or source_payload.get("card_id")
        or ""
    ).strip()
    if src_required and src_required != preflight_required:
        return False

    src_task_key = str(source_payload.get("task_key") or "").strip()
    if src_task_key and src_task_key != task_key:
        return False

    if bool(source_payload.get("passed")):
        return True

    status = normalize_status(source_payload.get("status"))
    return status in {"ready", "done", "passed", "pass"}


def build_kernel_context(
    active_task_path: Path,
    api_base: str,
    *,
    local_mode: bool = False,
    state_path: Path | None = None,
    dirty_whitelist: list[str] | None = None,
    dirty_policy_version: str = DEFAULT_DIRTY_POLICY_VERSION,
    dispatch_executor_override: str = "",
) -> KernelContext:
    active_task_path = active_task_path.resolve()
    active = load_json(active_task_path)
    scoped_active_task_path = resolve_task_scoped_active_task_path(active_task_path, active)
    if scoped_active_task_path != active_task_path:
        active_task_path = scoped_active_task_path
        active = load_json(active_task_path)
    dispatch_executor, dispatch_executor_mode = resolve_dispatch_executor(
        active_payload=active,
        cli_override=dispatch_executor_override,
    )
    project_id = str(active.get("project_id") or "").strip()
    task_split_dir = str(active.get("task_split_dir") or "").strip()
    task_key = str(active.get("task_key") or "").strip()
    execution_mode = str(active.get("execution_mode") or "serial").strip().lower() or "serial"
    single_active_card = bool(active.get("single_active_card", True))
    preflight_required = str(active.get("preflight_required") or "").strip() or "C00"
    if not task_split_dir or not task_key:
        raise ValueError("active task missing task_split_dir/task_key")
    if not local_mode and not project_id:
        raise ValueError("active task missing project_id (required when local-mode is disabled)")

    repo_root = resolve_repo_root(active_task_path)
    vk_cards_path = resolve_vk_cards_path(active_task_path)
    vk_cards = load_json(vk_cards_path)
    _validate_vk_cards_contract(vk_cards, task_split_dir=task_split_dir)
    _run_coverage_gate(repo_root=repo_root, task_split_dir=task_split_dir)

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
    scope_guard_ok = True
    scope_guard_reason = "scope_guard_passed"
    scope_guard_details: list[dict[str, Any]] = []

    if local_mode:
        if state_path is None:
            default_state_file = render_task_scoped_path(DEFAULT_STATE_FILE, task_key=task_key)
            for ancestor in active_task_path.parents:
                if (ancestor / ".git").exists():
                    state_path = (ancestor / default_state_file).resolve()
                    break
            if state_path is None:
                state_path = (Path.cwd() / default_state_file).resolve()
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

        scope_guard_ok, scope_guard_reason, scope_guard_details = evaluate_scope_guard(
            scoped_tasks=scoped,
            unscoped_tasks=unscoped,
            single_active_card=single_active_card,
        )

    effective_dirty_whitelist = list(dirty_whitelist or DEFAULT_DIRTY_WHITELIST)
    (
        main_repo_clean,
        main_repo_dirty_preview,
        main_repo_dirty_ignored_preview,
        main_repo_error,
    ) = inspect_repo_clean(
        repo_root,
        dirty_whitelist=effective_dirty_whitelist,
    )

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
                        if _preflight_passed_from_json(
                            source_payload,
                            preflight_required=preflight_required,
                            task_key=task_key,
                        ):
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
        execution_mode=execution_mode,
        single_active_card=single_active_card,
        preflight_required=preflight_required,
        preflight_ok=preflight_ok,
        preflight_reason=preflight_reason,
        card_order=card_order,
        cards_by_id=cards_by_id,
        scoped_tasks=scoped,
        unscoped_tasks=unscoped,
        card_status_map=card_status_map,
        card_task_map=card_task_map,
        scope_guard_ok=scope_guard_ok,
        scope_guard_reason=scope_guard_reason,
        scope_guard_details=scope_guard_details,
        main_repo_path=str(repo_root),
        main_repo_clean=main_repo_clean,
        main_repo_dirty_preview=main_repo_dirty_preview,
        main_repo_dirty_ignored_preview=main_repo_dirty_ignored_preview,
        main_repo_error=main_repo_error,
        dirty_policy_version=str(dirty_policy_version or DEFAULT_DIRTY_POLICY_VERSION),
        dirty_whitelist=effective_dirty_whitelist,
        dispatch_executor=dispatch_executor,
        dispatch_executor_mode=dispatch_executor_mode,
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
    if not ctx.main_repo_clean:
        detail: dict[str, Any] = {
            "reason": "main_repo_dirty",
            "repo_root": ctx.main_repo_path,
            "dirty_preview": ctx.main_repo_dirty_preview,
            "dirty_ignored_preview": ctx.main_repo_dirty_ignored_preview,
            "dirty_policy_version": ctx.dirty_policy_version,
            "dirty_whitelist": ctx.dirty_whitelist,
        }
        if ctx.main_repo_error:
            detail["error"] = ctx.main_repo_error
        return ("preflight_blocked", None, None, None, [detail])

    if not ctx.scope_guard_ok:
        if ctx.scope_guard_details:
            return ("preflight_blocked", None, None, None, ctx.scope_guard_details)
        return ("preflight_blocked", None, None, None, [{"reason": ctx.scope_guard_reason}])

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
        if status == "verified":
            blocked_details.append(
                {
                    "card_id": cid,
                    "status": status,
                    "reason": "verified_waiting_merge",
                }
            )
            return ("awaiting_merge", cid, target_task_id, status, blocked_details)
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


def advance_card(
    state_path: Path,
    *,
    task_key: str,
    card_order: list[str],
    card_id: str,
    new_status: str,
    action: str,
    action_result: str,
) -> dict[str, Any]:
    return update_local_card_status(
        state_path,
        task_key=task_key,
        card_order=card_order,
        card_id=card_id,
        status=new_status,
        action=action,
        action_result=action_result,
        current_card=card_id,
    )


def apply_action(
    api_base: str,
    ctx: KernelContext,
    action: str,
    target_card_id: str | None,
    target_task_id: str | None,
    *,
    active_task_path: Path,
    local_mode: bool = False,
    state_path: Path | None = None,
    sync_vk_in_local_mode: bool = False,
    commit_sha: str | None = None,
    merge_sha: str | None = None,
    subagent_id: str | None = None,
    ws_file: str | None = None,
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
            advance_card(
                state_path,
                task_key=ctx.task_key,
                card_order=ctx.card_order,
                card_id=target_card_id,
                new_status="todo",
                action="seed",
                action_result=f"CARD_SEEDED:{target_card_id}",
            )
            if sync_vk_in_local_mode:
                vk_sync = _try_sync_vk(
                    active_task_path=active_task_path,
                    state_path=state_path,
                    vk_api_base=api_base,
                    project_id=ctx.project_id,
                    task_key=ctx.task_key,
                    card_id=target_card_id,
                    status="todo",
                )
            else:
                vk_sync = {
                    "attempted": False,
                    "ok": False,
                    "disabled": True,
                    "reason": "local_mode_vk_sync_disabled",
                    "card_id": target_card_id,
                    "status": "todo",
                }
            return {
                "performed": True,
                "action": "seed",
                "card_id": target_card_id,
                "task_id": target_card_id,
                "status": "todo",
                "vk_sync": vk_sync,
            }
        payload = {
            "project_id": ctx.project_id,
            "title": str(card.get("title") or f"{target_card_id} [{ctx.task_key}]"),
            "description": build_card_description(card, ctx.task_key),
            "status": "todo",
        }
        resp = http_json("POST", f"{api_base}/api/tasks", payload)
        data = resp.get("data") or {}
        vk_sync = _try_sync_vk(
            active_task_path=active_task_path,
            state_path=state_path,
            vk_api_base=api_base,
            project_id=ctx.project_id,
            task_key=ctx.task_key,
            card_id=target_card_id,
            status=data.get("status") or "todo",
        )
        return {
            "performed": True,
            "action": "seed",
            "card_id": target_card_id,
            "task_id": data.get("id"),
            "status": data.get("status") or "todo",
            "vk_sync": vk_sync,
        }

    if action == "activate":
        if not target_card_id:
            raise RuntimeError("activate action missing target identifiers")
        if local_mode:
            if state_path is None:
                raise RuntimeError("state_path is required when local-mode is enabled")
            advance_card(
                state_path,
                task_key=ctx.task_key,
                card_order=ctx.card_order,
                card_id=target_card_id,
                new_status="inprogress",
                action="activate",
                action_result=f"CARD_ACTIVATED:{target_card_id}",
            )
            if sync_vk_in_local_mode:
                vk_sync = _try_sync_vk(
                    active_task_path=active_task_path,
                    state_path=state_path,
                    vk_api_base=api_base,
                    project_id=ctx.project_id,
                    task_key=ctx.task_key,
                    card_id=target_card_id,
                    status="inprogress",
                )
            else:
                vk_sync = {
                    "attempted": False,
                    "ok": False,
                    "disabled": True,
                    "reason": "local_mode_vk_sync_disabled",
                    "card_id": target_card_id,
                    "status": "inprogress",
                }
            return {
                "performed": True,
                "action": "activate",
                "card_id": target_card_id,
                "task_id": target_card_id,
                "status": "inprogress",
                "vk_sync": vk_sync,
            }
        if not target_task_id:
            raise RuntimeError("activate action missing target identifiers")
        payload = {"status": "inprogress"}
        resp = http_json("PUT", f"{api_base}/api/tasks/{target_task_id}", payload)
        data = resp.get("data") or {}
        vk_sync = _try_sync_vk(
            active_task_path=active_task_path,
            state_path=state_path,
            vk_api_base=api_base,
            project_id=ctx.project_id,
            task_key=ctx.task_key,
            card_id=target_card_id,
            status=data.get("status") or "inprogress",
        )
        return {
            "performed": True,
            "action": "activate",
            "card_id": target_card_id,
            "task_id": target_task_id,
            "status": data.get("status") or "inprogress",
            "vk_sync": vk_sync,
        }

    if action == "dispatch":
        if not target_card_id:
            raise RuntimeError("dispatch action missing target identifiers")
        executor_mode = str(ctx.dispatch_executor or DEFAULT_DISPATCH_EXECUTOR).strip().lower()
        if executor_mode != "wtimp":
            raise CardrunContractError(
                "CARDRUN_EXECUTOR_UNSUPPORTED",
                f"不支持的 dispatch 执行器: {executor_mode}",
                {
                    "dispatch_executor": executor_mode,
                    "expected": DEFAULT_DISPATCH_EXECUTOR,
                },
            )

        dispatch_request = build_wtimp_dispatch_request(
            ctx,
            target_card_id,
            active_task_path=active_task_path,
            ws_file_override=str(ws_file or "").strip() or None,
        )
        dispatch_result = run_wtimp_dispatch(dispatch_request)
        normalized_commit_sha = str(dispatch_result.commit_sha or "").strip()
        if not normalized_commit_sha:
            raise CardrunContractError(
                "CARDRUN_NO_COMMIT_EVIDENCE",
                f"card_id={target_card_id} dispatch 缺少 commit_sha 证据",
                {
                    "card_id": target_card_id,
                    "action": "dispatch",
                    "dispatch_executor": executor_mode,
                },
            )

        return {
            "performed": True,
            "action": "dispatch",
            "card_id": target_card_id,
            "task_id": target_task_id,
            "executor_mode": executor_mode,
            "executor_dispatch_mode": str(ctx.dispatch_executor_mode or DEFAULT_DISPATCH_EXECUTOR_MODE),
            "subagent_id": dispatch_result.subagent_id,
            "ws_file": dispatch_result.ws_file,
            "commit_sha": normalized_commit_sha,
            "merge_sha": dispatch_result.merge_sha,
            "merge_owner": "wt_flow",
            "worktree_path": dispatch_result.worktree_path,
        }

    return {"performed": False}


def main() -> int:
    args = parse_args()
    try:
        active_task_path = resolve_active_task_path(args.active_task, DEFAULT_REPO_ROOT)
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "action": "kernel_error",
            "error": str(exc),
        }
        write_output_file(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    active_payload = load_json(active_task_path)
    scoped_active_task_path = resolve_task_scoped_active_task_path(active_task_path, active_payload)
    active_payload = load_json(scoped_active_task_path)
    active_task_key = str(active_payload.get("task_key") or "").strip()
    if active_task_key:
        args.state_file = render_task_scoped_path(args.state_file, task_key=active_task_key)
        args.task_ledger_file = render_task_scoped_path(args.task_ledger_file, task_key=active_task_key)
        args.run_lock_file = render_task_scoped_path(args.run_lock_file, task_key=active_task_key)
        args.idempotency_file = render_task_scoped_path(args.idempotency_file, task_key=active_task_key)

    state_path = resolve_state_file_path(scoped_active_task_path, args.state_file)
    task_ledger_file = resolve_runtime_file_path(scoped_active_task_path, args.task_ledger_file)
    run_lock_file = resolve_runtime_file_path(scoped_active_task_path, args.run_lock_file)
    idempotency_file = resolve_runtime_file_path(scoped_active_task_path, args.idempotency_file)
    trigger_source = normalize_trigger_source(args.trigger_source)
    explicit_idempotency_key = str(args.idempotency_key or "").strip()
    idempotency_window_seconds = _normalize_window_seconds(args.idempotency_window_seconds)
    run_lock_disabled = is_disabled_by_env(RUN_LOCK_DISABLE_ENV)
    idempotency_disabled = is_disabled_by_env(IDEMPOTENCY_DISABLE_ENV)
    dirty_whitelist = parse_dirty_whitelist(getattr(args, "dirty_whitelist", ""))
    dirty_policy_version = str(
        getattr(args, "dirty_policy_version", DEFAULT_DIRTY_POLICY_VERSION)
        or DEFAULT_DIRTY_POLICY_VERSION
    )
    subagent_id = str(getattr(args, "subagent_id", "") or "").strip() or None
    ws_file = str(getattr(args, "ws_file", "") or "").strip() or None
    commit_sha = str(getattr(args, "commit_sha", "") or "").strip() or None
    merge_sha = str(getattr(args, "merge_sha", "") or "").strip() or None

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
            round_started_at = datetime.now(timezone.utc)

            ctx = build_kernel_context(
                scoped_active_task_path,
                args.vk_api_base,
                local_mode=args.local_mode,
                state_path=state_path,
                dirty_whitelist=dirty_whitelist,
                dirty_policy_version=dirty_policy_version,
                dispatch_executor_override=str(getattr(args, "dispatch_executor", "") or ""),
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
                            "execution_mode": ctx.execution_mode,
                            "single_active_card": ctx.single_active_card,
                            "preflight_required": ctx.preflight_required,
                            "preflight_ok": ctx.preflight_ok,
                            "preflight_reason": ctx.preflight_reason,
                            "target_card_id": first_not_done,
                            "target_task_id": target_task_id,
                            "target_status": target_status,
                            "scope_guard": {
                                "ok": ctx.scope_guard_ok,
                                "reason": ctx.scope_guard_reason,
                                "details": ctx.scope_guard_details,
                            },
                            "main_repo_guard": {
                                "ok": ctx.main_repo_clean,
                                "repo_root": ctx.main_repo_path,
                                "dirty_preview": ctx.main_repo_dirty_preview,
                                "dirty_ignored_preview": ctx.main_repo_dirty_ignored_preview,
                                "error": ctx.main_repo_error,
                                "dirty_policy_version": ctx.dirty_policy_version,
                                "dirty_whitelist": ctx.dirty_whitelist,
                            },
                        }
                    )
                    attempt_result = _derive_attempt_result(
                        action,
                        applied_performed=False,
                        reason="idempotency_window",
                    )
                    attempt_evidence = record_attempt_evidence(
                        ledger_file=task_ledger_file,
                        task_key=ctx.task_key,
                        card_id=first_not_done,
                        action=action,
                        result=attempt_result,
                        trigger_source=trigger_source,
                        started_at=round_started_at,
                        ended_at=datetime.now(timezone.utc),
                        target_status=target_status,
                        applied={"performed": False, "reason": "idempotency_window"},
                        auto_wake={"attempted": False, "ok": False},
                        blocked_details=blocked_details,
                        idempotency_key=idempotency_key,
                        execution_mode=ctx.execution_mode,
                        subagent_id=subagent_id,
                        ws_file=ws_file,
                        commit_sha=commit_sha,
                        merge_sha=merge_sha,
                        executor_mode=ctx.dispatch_executor,
                    )
                    result.update(
                        {
                            "attempt": {
                                "attempt_id": attempt_evidence["attempt"]["attempt_id"],
                                "result": attempt_result,
                            },
                            "task_ledger_file": str(task_ledger_file),
                        }
                    )
                    write_output_file(args.output, result)
                    print(json.dumps(result, ensure_ascii=False))
                    return 0

            applied = {"performed": False}
            if args.apply_bootstrap and action in {"seed", "activate", "dispatch"}:
                applied = apply_action(
                    args.vk_api_base,
                    ctx,
                    action,
                    first_not_done,
                    target_task_id,
                    active_task_path=scoped_active_task_path,
                    local_mode=args.local_mode,
                    state_path=state_path,
                    sync_vk_in_local_mode=args.sync_vk_in_local_mode,
                    commit_sha=commit_sha,
                    merge_sha=merge_sha,
                    subagent_id=subagent_id,
                    ws_file=ws_file,
                )

            auto_wake = {
                "attempted": False,
                "ok": False,
                "disabled": is_disabled_by_env(AUTO_WAKE_DISABLE_ENV),
            }
            if args.local_mode and args.apply_bootstrap:
                local_state = load_local_state(state_path, ctx.task_key, ctx.card_order)
                done_card = pick_pending_auto_wake_card(local_state, ctx.card_order)
                if done_card:
                    wake_reason = f"CARD_DONE:{done_card}"
                    auto_wake = trigger_next_round(wake_reason)
                    if auto_wake.get("ok"):
                        mark_local_auto_wake(
                            state_path,
                            task_key=ctx.task_key,
                            card_order=ctx.card_order,
                            card_id=done_card,
                        )

            worktree_path = str(applied.get("worktree_path") or "").strip() or None
            if not worktree_path and first_not_done:
                worktree_path = str((Path.cwd() / ".worktrees" / first_not_done).resolve())
            attempt_result = _derive_attempt_result(
                action,
                applied_performed=bool(applied.get("performed")),
            )
            attempt_evidence = record_attempt_evidence(
                ledger_file=task_ledger_file,
                task_key=ctx.task_key,
                card_id=first_not_done,
                action=action,
                result=attempt_result,
                trigger_source=trigger_source,
                started_at=round_started_at,
                ended_at=datetime.now(timezone.utc),
                target_status=target_status,
                applied=applied,
                auto_wake=auto_wake,
                blocked_details=blocked_details,
                idempotency_key=idempotency_key,
                execution_mode=ctx.execution_mode,
                worktree_path=worktree_path,
                subagent_id=subagent_id,
                ws_file=ws_file,
                commit_sha=commit_sha or str(applied.get("commit_sha") or "").strip() or None,
                merge_sha=merge_sha or str(applied.get("merge_sha") or "").strip() or None,
                executor_mode=ctx.dispatch_executor,
            )

            scoped_counts = count_statuses(ctx.scoped_tasks)
            unscoped_counts = count_statuses(ctx.unscoped_tasks)
            result = {
                "ok": True,
                "project_id": ctx.project_id,
                "task_key": ctx.task_key,
                "execution_mode": ctx.execution_mode,
                "dispatch_executor": ctx.dispatch_executor,
                "dispatch_executor_mode": ctx.dispatch_executor_mode,
                "single_active_card": ctx.single_active_card,
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
                "scope_guard": {
                    "ok": ctx.scope_guard_ok,
                    "reason": ctx.scope_guard_reason,
                    "details": ctx.scope_guard_details,
                },
                "main_repo_guard": {
                    "ok": ctx.main_repo_clean,
                    "repo_root": ctx.main_repo_path,
                    "dirty_preview": ctx.main_repo_dirty_preview,
                    "dirty_ignored_preview": ctx.main_repo_dirty_ignored_preview,
                    "error": ctx.main_repo_error,
                    "dirty_policy_version": ctx.dirty_policy_version,
                    "dirty_whitelist": ctx.dirty_whitelist,
                },
                "applied": applied,
                "auto_wake": auto_wake,
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
                "attempt": {
                    "attempt_id": attempt_evidence["attempt"]["attempt_id"],
                    "result": attempt_result,
                },
                "execution_evidence": {
                    "executor_mode": attempt_evidence["attempt"]
                    .get("execution_evidence", {})
                    .get("executor_mode"),
                    "subagent_id": attempt_evidence["attempt"].get("subagent_id"),
                    "ws_file": attempt_evidence["attempt"].get("ws_file"),
                    "commit_sha": attempt_evidence["attempt"].get("commit_sha"),
                    "merge_sha": attempt_evidence["attempt"].get("merge_sha"),
                },
                "task_ledger_file": str(task_ledger_file),
                "local_mode": args.local_mode,
                "trigger_source": trigger_source,
                "state_file": str(state_path),
            }

            write_output_file(args.output, result)
            print(json.dumps(result, ensure_ascii=False))
            return 0
    except CardrunContractError as exc:
        payload = {
            "ok": False,
            "action": "preflight_blocked",
            "error": {
                "code": exc.code,
                "message": str(exc),
                "details": exc.details or {},
            },
        }
        write_output_file(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 2
    except Exception as exc:  # noqa: BLE001
        payload = {"ok": False, "action": "kernel_error", "error": str(exc)}
        write_output_file(args.output, payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
