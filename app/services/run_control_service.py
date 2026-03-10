"""运行时取消控制服务（中文注释）。

职责：
1. 管理 run 生命周期（running/stopping/stopped/completed/failed）
2. 提供幂等 cancel 接口语义
3. 为流式输出提供快速取消判断（内存态）
4. 提供 active_run 恢复与 orphan 清理入口
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.cache_registry import get_cache_registry
from app.models.chat_run import ChatRun, ChatRunStatus
from app.models.user import User


logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {ChatRunStatus.RUNNING.value, ChatRunStatus.STOPPING.value}
TERMINAL_STATUSES = {
    ChatRunStatus.STOPPED.value,
    ChatRunStatus.COMPLETED.value,
    ChatRunStatus.FAILED.value,
}


class RunControlError(RuntimeError):
    """run 控制基础异常。"""


class RunNotFoundError(RunControlError):
    """run 不存在。"""


class RunPermissionDeniedError(RunControlError):
    """无权限取消 run。"""


class ActiveRunExistsError(RunControlError):
    """同线程已存在 active run。"""

    def __init__(self, *, thread_id: str, active_run_id: str):
        self.thread_id = thread_id
        self.active_run_id = active_run_id
        super().__init__(f"active_run_exists: thread_id={thread_id}, run_id={active_run_id}")


class ParallelLimitExceededError(RunControlError):
    """单用户 active run 超限。"""

    def __init__(self, *, active_count: int, limit: int):
        self.active_count = active_count
        self.limit = limit
        super().__init__(f"parallel_limit_exceeded: active_count={active_count}, limit={limit}")


class RunThreadMismatchError(RunControlError):
    """run 与 thread_id 不匹配。"""

    def __init__(self, *, run_id: str, expected_thread_id: str, actual_thread_id: str):
        self.run_id = run_id
        self.expected_thread_id = expected_thread_id
        self.actual_thread_id = actual_thread_id
        super().__init__(
            f"thread_id mismatch: run_id={run_id}, expected={expected_thread_id}, actual={actual_thread_id}"
        )


@dataclass
class RunSnapshot:
    """运行态快照。"""

    run_id: str
    thread_id: str
    user_id: Optional[int]
    status: str
    cancel_reason: Optional[str] = None
    cancel_mode: Optional[str] = None
    cancel_requested_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    last_activity_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class CancelRunResult:
    """取消结果。"""

    run_id: str
    thread_id: str
    status: str
    accepted: bool
    idempotent: bool
    reason: Optional[str]


def _env_flag(name: str, default: bool = False) -> bool:
    """读取布尔环境变量。"""

    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class RunControlService:
    """运行时取消控制服务。"""

    def __init__(
        self,
        *,
        enable_override: Optional[bool] = None,
        stopped_event_override: Optional[bool] = None,
        orphan_timeout_seconds: int = 600,
        parallel_limit: int = 3,
        activity_throttle_seconds: int = 2,
    ):
        self.enable_override = enable_override
        self.stopped_event_override = stopped_event_override
        self.orphan_timeout_seconds = orphan_timeout_seconds
        self.parallel_limit = parallel_limit
        self.activity_throttle_seconds = activity_throttle_seconds

        self._lock = threading.RLock()
        self._runs: Dict[str, RunSnapshot] = {}
        self._active_run_by_thread: Dict[tuple[str, Optional[int]], str] = {}
        self._stopped_event_emitted: set[str] = set()
        self._last_activity_flush_at: Dict[str, datetime] = {}

    def is_enabled(self) -> bool:
        """当前是否启用 run 控制。"""

        if self.enable_override is not None:
            return bool(self.enable_override)
        return _env_flag("ENABLE_RUN_CONTROL", default=False)

    def is_stopped_event_enabled(self) -> bool:
        """当前是否启用 stopped 兼容事件。"""

        if self.stopped_event_override is not None:
            return bool(self.stopped_event_override)
        return _env_flag("ENABLE_SSE_STOPPED_EVENT", default=False)

    def is_active_runs_query_enabled(self) -> bool:
        return _env_flag("ENABLE_ACTIVE_RUNS_QUERY", default=True)

    def is_parallel_gate_enabled(self) -> bool:
        return _env_flag("ENABLE_PER_USER_PARALLEL_GATE", default=True)

    def is_thread_id_match_check_enabled(self) -> bool:
        return _env_flag("ENABLE_THREAD_ID_MATCH_CHECK", default=True)

    def get_parallel_limit(self) -> int:
        return max(1, min(_env_int("MAX_PARALLEL_STREAMS_PER_USER", self.parallel_limit), 10))

    def _thread_key(self, thread_id: str, user_id: Optional[int]) -> tuple[str, Optional[int]]:
        return thread_id, user_id

    def _copy(self, snapshot: RunSnapshot) -> RunSnapshot:
        return replace(snapshot)

    def _new_run_id(self) -> str:
        return f"run_{uuid4().hex}"

    def _sync_memory(self, snapshot: RunSnapshot) -> RunSnapshot:
        with self._lock:
            self._runs[snapshot.run_id] = self._copy(snapshot)
            if snapshot.status in ACTIVE_STATUSES:
                self._active_run_by_thread[self._thread_key(snapshot.thread_id, snapshot.user_id)] = snapshot.run_id
            else:
                thread_key = self._thread_key(snapshot.thread_id, snapshot.user_id)
                if self._active_run_by_thread.get(thread_key) == snapshot.run_id:
                    self._active_run_by_thread.pop(thread_key, None)
        return snapshot

    def _snapshot_from_row(self, row: ChatRun) -> RunSnapshot:
        return RunSnapshot(
            run_id=row.run_id,
            thread_id=row.thread_id,
            user_id=row.user_id,
            status=row.status,
            cancel_reason=row.cancel_reason,
            cancel_mode=row.cancel_mode,
            cancel_requested_at=row.cancel_requested_at,
            stopped_at=row.stopped_at,
            completed_at=row.completed_at,
            failed_at=row.failed_at,
            error_message=row.error_message,
            last_activity_at=row.last_activity_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _effective_activity_time(self, snapshot: RunSnapshot) -> datetime:
        return snapshot.last_activity_at or snapshot.updated_at or snapshot.created_at

    def _active_run_sort_key(self, snapshot: RunSnapshot) -> tuple[bool, datetime, datetime, str]:
        activity_time = self._effective_activity_time(snapshot)
        updated_at = snapshot.updated_at or snapshot.created_at
        return (
            snapshot.last_activity_at is not None,
            activity_time,
            updated_at,
            snapshot.run_id,
        )

    def _load_from_db(self, db: Optional[Session], run_id: str) -> Optional[RunSnapshot]:
        if db is None:
            return None

        try:
            row = db.query(ChatRun).filter(ChatRun.run_id == run_id).first()
        except Exception as exc:
            logger.debug("查询 ChatRun 失败，回退内存态: run_id=%s, error=%s", run_id, exc)
            return None

        if row is None:
            return None

        snapshot = self._snapshot_from_row(row)
        self._sync_memory(snapshot)
        return snapshot

    def _persist_to_db(self, db: Optional[Session], snapshot: RunSnapshot) -> None:
        if db is None:
            return

        try:
            row = db.query(ChatRun).filter(ChatRun.run_id == snapshot.run_id).first()
            if row is None:
                row = ChatRun(
                    run_id=snapshot.run_id,
                    thread_id=snapshot.thread_id,
                    user_id=snapshot.user_id,
                    created_at=snapshot.created_at,
                )
                db.add(row)

            row.thread_id = snapshot.thread_id
            row.user_id = snapshot.user_id
            row.status = snapshot.status
            row.cancel_reason = snapshot.cancel_reason
            row.cancel_mode = snapshot.cancel_mode
            row.cancel_requested_at = snapshot.cancel_requested_at
            row.stopped_at = snapshot.stopped_at
            row.completed_at = snapshot.completed_at
            row.failed_at = snapshot.failed_at
            row.error_message = snapshot.error_message
            row.last_activity_at = snapshot.last_activity_at
            row.updated_at = snapshot.updated_at

            db.flush()
            db.commit()
        except Exception as exc:
            logger.debug("持久化 ChatRun 失败，继续以内存态运行: run_id=%s, error=%s", snapshot.run_id, exc)
            try:
                db.rollback()
            except Exception:
                pass

    def _get_memory_run(self, run_id: str) -> Optional[RunSnapshot]:
        with self._lock:
            snapshot = self._runs.get(run_id)
            if snapshot is None:
                return None
            return self._copy(snapshot)

    def _settle_hard_cancel_snapshot(
        self,
        snapshot: Optional[RunSnapshot],
        *,
        db: Optional[Session] = None,
    ) -> Optional[RunSnapshot]:
        if snapshot is None:
            return None
        if snapshot.status != ChatRunStatus.STOPPING.value or snapshot.cancel_mode != "hard":
            return snapshot

        updated = self._update_snapshot(
            snapshot,
            status=ChatRunStatus.STOPPED.value,
            cancel_reason=snapshot.cancel_reason or "user_cancelled",
            cancel_mode=snapshot.cancel_mode,
            mark_activity=False,
        )
        self._sync_memory(updated)
        self._persist_to_db(db, updated)
        return self._copy(updated)

    def get_run(self, run_id: str, db: Optional[Session] = None) -> Optional[RunSnapshot]:
        """获取 run 快照。"""

        if db is not None:
            snapshot = self._load_from_db(db, run_id)
            if snapshot is not None:
                return self._settle_hard_cancel_snapshot(snapshot, db=db)
        return self._settle_hard_cancel_snapshot(self._get_memory_run(run_id), db=db)

    def get_latest_run(
        self,
        *,
        thread_id: str,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Optional[RunSnapshot]:
        """按线程获取最近一次 run。"""

        if db is not None:
            try:
                query = db.query(ChatRun).filter(ChatRun.thread_id == thread_id)
                if user_id is not None:
                    query = query.filter(ChatRun.user_id == user_id)
                row = query.order_by(ChatRun.created_at.desc()).first()
            except Exception as exc:
                logger.debug("查询最近 run 失败: thread_id=%s, error=%s", thread_id, exc)
            else:
                if row is not None:
                    snapshot = self._settle_hard_cancel_snapshot(self._snapshot_from_row(row), db=db)
                    if snapshot is not None:
                        self._sync_memory(snapshot)
                    return snapshot

        with self._lock:
            candidates = [
                self._copy(run)
                for run in self._runs.values()
                if run.thread_id == thread_id and (user_id is None or run.user_id == user_id)
            ]

        if candidates:
            return max(candidates, key=lambda item: item.created_at)
        return None

    def _lock_user_scope(self, *, user_id: Optional[int], db: Optional[Session]) -> None:
        if db is None or user_id is None:
            return
        try:
            db.query(User).filter(User.id == user_id).with_for_update().first()
        except Exception as exc:
            logger.debug("用户级互斥锁获取失败，继续走无锁查询: user_id=%s, error=%s", user_id, exc)

    def list_active_runs_by_user(
        self,
        *,
        user_id: int,
        db: Optional[Session] = None,
    ) -> list[RunSnapshot]:
        """按用户直接查询 active runs。"""

        if db is None:
            with self._lock:
                active_runs = [
                    self._settle_hard_cancel_snapshot(self._copy(run), db=db)
                    for run in self._runs.values()
                    if run.user_id == user_id and run.status in ACTIVE_STATUSES
                ]
        else:
            rows = (
                db.query(ChatRun)
                .filter(ChatRun.user_id == user_id, ChatRun.status.in_(tuple(ACTIVE_STATUSES)))
                .all()
            )
            active_runs = [self._settle_hard_cancel_snapshot(self._snapshot_from_row(row), db=db) for row in rows]
            for snapshot in active_runs:
                if snapshot is not None:
                    self._sync_memory(snapshot)

        active_runs = [snapshot for snapshot in active_runs if snapshot is not None and snapshot.status in ACTIVE_STATUSES]
        active_runs.sort(
            key=self._active_run_sort_key,
            reverse=True,
        )
        return active_runs

    def get_active_run(
        self,
        *,
        thread_id: str,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Optional[RunSnapshot]:
        """按线程获取 active run（running/stopping）。"""

        if db is not None:
            try:
                query = db.query(ChatRun).filter(ChatRun.thread_id == thread_id, ChatRun.status.in_(tuple(ACTIVE_STATUSES)))
                if user_id is not None:
                    query = query.filter(ChatRun.user_id == user_id)
                row = query.order_by(ChatRun.updated_at.desc(), ChatRun.run_id.desc()).first()
            except Exception as exc:
                logger.debug("查询 active run 失败，回退内存态: thread_id=%s, error=%s", thread_id, exc)
            else:
                if row is not None:
                    snapshot = self._settle_hard_cancel_snapshot(self._snapshot_from_row(row), db=db)
                    if snapshot is not None:
                        self._sync_memory(snapshot)
                    if snapshot is not None and snapshot.status in ACTIVE_STATUSES:
                        return snapshot

        with self._lock:
            run_id = self._active_run_by_thread.get(self._thread_key(thread_id, user_id))

        if run_id:
            snapshot = self.get_run(run_id, db=db)
            if snapshot and snapshot.status in ACTIVE_STATUSES:
                return snapshot

        latest = self.get_latest_run(thread_id=thread_id, user_id=user_id, db=db)
        if latest and latest.status in ACTIVE_STATUSES:
            return latest
        return None

    def create_run(
        self,
        *,
        thread_id: str,
        user_id: Optional[int],
        run_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> RunSnapshot:
        """创建并注册 run；同线程 active 冲突与并发上限在此阻断。"""

        resolved_run_id = run_id or self._new_run_id()
        now = datetime.now()

        self._lock_user_scope(user_id=user_id, db=db)

        active_run = self.get_active_run(thread_id=thread_id, user_id=user_id, db=db)
        if active_run is not None:
            if active_run.run_id == resolved_run_id:
                return active_run
            raise ActiveRunExistsError(thread_id=thread_id, active_run_id=active_run.run_id)

        if self.is_parallel_gate_enabled() and user_id is not None:
            active_runs = self.list_active_runs_by_user(user_id=user_id, db=db)
            active_count = len(active_runs)
            limit = self.get_parallel_limit()
            if active_count >= limit:
                raise ParallelLimitExceededError(active_count=active_count, limit=limit)

        existing = self.get_run(resolved_run_id, db=db)
        if existing and existing.status in ACTIVE_STATUSES and existing.thread_id == thread_id and existing.user_id == user_id:
            return existing

        snapshot = RunSnapshot(
            run_id=resolved_run_id,
            thread_id=thread_id,
            user_id=user_id,
            status=ChatRunStatus.RUNNING.value,
            last_activity_at=now,
            created_at=now,
            updated_at=now,
        )
        self._sync_memory(snapshot)
        self._persist_to_db(db, snapshot)

        with self._lock:
            self._stopped_event_emitted.discard(resolved_run_id)
            self._last_activity_flush_at[resolved_run_id] = now

        return self._copy(snapshot)

    def _update_snapshot(
        self,
        snapshot: RunSnapshot,
        *,
        status: Optional[str] = None,
        cancel_reason: Optional[str] = None,
        cancel_mode: Optional[str] = None,
        error_message: Optional[str] = None,
        mark_activity: bool = True,
    ) -> RunSnapshot:
        now = datetime.now()
        updated = replace(snapshot)
        updated.updated_at = now

        if status is not None:
            updated.status = status
        if cancel_reason is not None:
            updated.cancel_reason = cancel_reason
        if cancel_mode is not None:
            updated.cancel_mode = cancel_mode
        if error_message is not None:
            updated.error_message = error_message
        if mark_activity:
            updated.last_activity_at = now

        if status == ChatRunStatus.STOPPING.value:
            updated.cancel_requested_at = now
        elif status == ChatRunStatus.STOPPED.value:
            updated.stopped_at = now
        elif status == ChatRunStatus.COMPLETED.value:
            updated.completed_at = now
        elif status == ChatRunStatus.FAILED.value:
            updated.failed_at = now

        return updated

    def cancel_run(
        self,
        *,
        run_id: str,
        requester_user_id: Optional[int],
        is_admin: bool = False,
        reason: str = "user_cancelled",
        cancel_mode: str = "soft",
        thread_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> CancelRunResult:
        """取消 run（幂等）。"""

        if not self.is_enabled():
            return CancelRunResult(
                run_id=run_id,
                thread_id="",
                status="disabled",
                accepted=False,
                idempotent=True,
                reason="run_control_disabled",
            )

        snapshot = self.get_run(run_id, db=db)
        if snapshot is None:
            raise RunNotFoundError(f"run 不存在: {run_id}")

        if (
            not is_admin
            and snapshot.user_id is not None
            and snapshot.user_id != requester_user_id
        ):
            raise RunPermissionDeniedError(f"无权限取消 run: {run_id}")

        if thread_id and snapshot.thread_id != thread_id:
            raise RunThreadMismatchError(
                run_id=run_id,
                expected_thread_id=snapshot.thread_id,
                actual_thread_id=thread_id,
            )

        idempotent = False
        if snapshot.status == ChatRunStatus.RUNNING.value:
            target_status = ChatRunStatus.STOPPED.value if cancel_mode == "hard" else ChatRunStatus.STOPPING.value
            snapshot = self._update_snapshot(
                snapshot,
                status=target_status,
                cancel_reason=reason,
                cancel_mode=cancel_mode,
            )
        else:
            idempotent = True
            if snapshot.status == ChatRunStatus.STOPPING.value and cancel_mode == "hard":
                snapshot = self._update_snapshot(
                    snapshot,
                    status=ChatRunStatus.STOPPED.value,
                    cancel_reason=snapshot.cancel_reason or reason,
                    cancel_mode=cancel_mode,
                    mark_activity=False,
                )
            elif not snapshot.cancel_reason and reason:
                snapshot = self._update_snapshot(snapshot, cancel_reason=reason, cancel_mode=cancel_mode)

        self._sync_memory(snapshot)
        self._persist_to_db(db, snapshot)

        return CancelRunResult(
            run_id=run_id,
            thread_id=snapshot.thread_id,
            status=snapshot.status,
            accepted=True,
            idempotent=idempotent,
            reason=snapshot.cancel_reason,
        )

    def mark_activity(
        self,
        run_id: Optional[str],
        *,
        db: Optional[Session] = None,
        force: bool = False,
        now: Optional[datetime] = None,
    ) -> Optional[RunSnapshot]:
        """记录 run 最近活动时间。"""

        if not run_id:
            return None

        snapshot = self.get_run(run_id, db=db)
        if snapshot is None:
            return None

        current = now or datetime.now()
        with self._lock:
            last_flush = self._last_activity_flush_at.get(run_id)
        if not force and last_flush is not None and (current - last_flush).total_seconds() < self.activity_throttle_seconds:
            return snapshot

        updated = replace(snapshot)
        updated.last_activity_at = current
        updated.updated_at = current
        self._sync_memory(updated)
        self._persist_to_db(db, updated)
        with self._lock:
            self._last_activity_flush_at[run_id] = current
        return self._copy(updated)

    def is_cancelled(self, run_id: Optional[str], db: Optional[Session] = None) -> bool:
        """是否处于取消态（stopping/stopped）。"""

        if not run_id:
            return False
        snapshot = self.get_run(run_id, db=db)
        if snapshot is None:
            return False
        return snapshot.status in {ChatRunStatus.STOPPING.value, ChatRunStatus.STOPPED.value}

    def get_cancel_reason(self, run_id: Optional[str], db: Optional[Session] = None) -> str:
        """获取取消原因。"""

        if not run_id:
            return "user_cancelled"

        snapshot = self.get_run(run_id, db=db)
        if snapshot and snapshot.cancel_reason:
            return snapshot.cancel_reason
        return "user_cancelled"

    def mark_stopped(
        self,
        *,
        run_id: str,
        reason: str = "user_cancelled",
        cancel_mode: str = "soft",
        db: Optional[Session] = None,
    ) -> Optional[RunSnapshot]:
        """标记 run 为 stopped。"""

        snapshot = self.get_run(run_id, db=db)
        if snapshot is None:
            return None

        if snapshot.status == ChatRunStatus.STOPPED.value:
            return snapshot

        if snapshot.status == ChatRunStatus.COMPLETED.value:
            return snapshot

        updated = self._update_snapshot(
            snapshot,
            status=ChatRunStatus.STOPPED.value,
            cancel_reason=snapshot.cancel_reason or reason,
            cancel_mode=snapshot.cancel_mode or cancel_mode,
        )
        self._sync_memory(updated)
        self._persist_to_db(db, updated)
        return self._copy(updated)

    def complete_run(self, run_id: str, db: Optional[Session] = None) -> Optional[RunSnapshot]:
        """标记 run 完成。"""

        snapshot = self.get_run(run_id, db=db)
        if snapshot is None:
            return None

        if snapshot.status in {
            ChatRunStatus.STOPPING.value,
            ChatRunStatus.STOPPED.value,
            ChatRunStatus.FAILED.value,
        }:
            return snapshot

        updated = self._update_snapshot(snapshot, status=ChatRunStatus.COMPLETED.value)
        self._sync_memory(updated)
        self._persist_to_db(db, updated)
        return self._copy(updated)

    def fail_run(self, run_id: str, error_message: str, db: Optional[Session] = None) -> Optional[RunSnapshot]:
        """标记 run 失败。"""

        snapshot = self.get_run(run_id, db=db)
        if snapshot is None:
            return None

        if snapshot.status in TERMINAL_STATUSES:
            return snapshot

        updated = self._update_snapshot(
            snapshot,
            status=ChatRunStatus.FAILED.value,
            error_message=error_message,
        )
        self._sync_memory(updated)
        self._persist_to_db(db, updated)
        return self._copy(updated)

    def cleanup_orphan(
        self,
        run_id: str,
        *,
        db: Optional[Session] = None,
        reason: str = "orphan_cleanup",
    ) -> Optional[RunSnapshot]:
        """清理 orphan run。"""

        return self.mark_stopped(run_id=run_id, reason=reason, cancel_mode="hard", db=db)

    def recover_active_runs(
        self,
        *,
        timeout_seconds: Optional[int] = None,
        db: Optional[Session] = None,
        now: Optional[datetime] = None,
    ) -> list[RunSnapshot]:
        """恢复 active_run，超时 run 自动清理为 orphan。"""

        if not self.is_enabled():
            return []

        current = now or datetime.now()
        timeout = timeout_seconds if timeout_seconds is not None else self.orphan_timeout_seconds
        deadline = current - timedelta(seconds=max(timeout, 1))

        with self._lock:
            candidates = [
                self._copy(snapshot)
                for snapshot in self._runs.values()
                if snapshot.status in ACTIVE_STATUSES and snapshot.updated_at <= deadline
            ]

        cleaned: list[RunSnapshot] = []
        for snapshot in candidates:
            cleaned_snapshot = self.cleanup_orphan(
                snapshot.run_id,
                db=db,
                reason="cancel_timeout" if snapshot.status == ChatRunStatus.STOPPING.value else "orphan_cleanup",
            )
            if cleaned_snapshot:
                cleaned.append(cleaned_snapshot)

        return cleaned

    def can_resume_run(self, run_id: Optional[str], db: Optional[Session] = None) -> bool:
        """run 是否允许 resume。"""

        if not run_id:
            return True

        snapshot = self.get_run(run_id, db=db)
        if snapshot is None:
            return True

        return snapshot.status not in {ChatRunStatus.STOPPING.value, ChatRunStatus.STOPPED.value}

    def has_stopped_event_emitted(self, run_id: Optional[str]) -> bool:
        """是否已经发送过 stopped 事件。"""

        if not run_id:
            return False
        with self._lock:
            return run_id in self._stopped_event_emitted

    def mark_stopped_event_emitted(self, run_id: Optional[str]) -> None:
        """记录 stopped 事件已发送。"""

        if not run_id:
            return
        with self._lock:
            self._stopped_event_emitted.add(run_id)

    def clear_stopped_event_marker(self, run_id: Optional[str]) -> None:
        """清理 stopped 事件发送标记。"""

        if not run_id:
            return
        with self._lock:
            self._stopped_event_emitted.discard(run_id)
            self._last_activity_flush_at.pop(run_id, None)

    def reset(self) -> None:
        """重置内存态（测试辅助）。"""

        with self._lock:
            self._runs.clear()
            self._active_run_by_thread.clear()
            self._stopped_event_emitted.clear()
            self._last_activity_flush_at.clear()


_RUN_CONTROL_SERVICE_KEY = "run_control_service.instance"


def reset_run_control_service() -> None:
    """清理共享 RunControlService 实例。"""

    service = get_cache_registry().get(_RUN_CONTROL_SERVICE_KEY)
    if isinstance(service, RunControlService):
        service.reset()
    get_cache_registry().clear(_RUN_CONTROL_SERVICE_KEY)


def get_run_control_service() -> RunControlService:
    """获取共享 RunControlService 实例。"""

    return get_cache_registry().get_or_create(_RUN_CONTROL_SERVICE_KEY, RunControlService)
