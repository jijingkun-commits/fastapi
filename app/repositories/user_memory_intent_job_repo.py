"""用户记忆意图任务仓储层（中文注释）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_memory_intent_job import (
    MEMORY_INTENT_STATUS_DEAD_LETTER,
    MEMORY_INTENT_STATUS_FAILED,
    MEMORY_INTENT_STATUS_PENDING,
    MEMORY_INTENT_STATUS_PROCESSING,
    MEMORY_INTENT_STATUS_SUCCEEDED,
    UserMemoryIntentJob,
)


DEFAULT_WORKER_LEASE_SECONDS = 60
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BASE_SECONDS = 30
DEFAULT_RETRY_RECOVER_LIMIT = 128
DEFAULT_MAX_BACKOFF_SECONDS = 15 * 60


def _safe_positive_int(value: int, default: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = int(default)
    return max(1, normalized)


def _compute_backoff_seconds(
    *,
    attempt_count: int,
    base_retry_seconds: int,
    max_backoff_seconds: int = DEFAULT_MAX_BACKOFF_SECONDS,
) -> int:
    """按指数退避计算下次重试秒数。"""

    safe_attempt = max(1, int(attempt_count))
    safe_base = _safe_positive_int(base_retry_seconds, DEFAULT_RETRY_BASE_SECONDS)
    backoff = safe_base * (2 ** (safe_attempt - 1))
    return min(int(max_backoff_seconds), int(backoff))


def build_dedupe_key(*, user_id: int, source_message_id: int) -> str:
    """构造幂等键。"""

    return f"{int(user_id)}:{int(source_message_id)}"


def get_by_source_message(
    db: Session,
    *,
    user_id: int,
    source_message_id: int,
) -> UserMemoryIntentJob | None:
    """按业务幂等主键读取任务。"""

    return (
        db.query(UserMemoryIntentJob)
        .filter(
            UserMemoryIntentJob.user_id == int(user_id),
            UserMemoryIntentJob.source_message_id == int(source_message_id),
        )
        .first()
    )


def enqueue_pending_job(
    db: Session,
    *,
    user_id: int,
    source_thread_id: str | None,
    source_message_id: int,
    payload_json: dict[str, Any] | None = None,
    event_time: datetime | None = None,
) -> tuple[UserMemoryIntentJob, bool]:
    """入队 pending 任务；若已存在则返回既有任务。"""

    existing = get_by_source_message(
        db,
        user_id=user_id,
        source_message_id=source_message_id,
    )
    if existing is not None:
        return existing, False

    now = datetime.now()
    job = UserMemoryIntentJob(
        user_id=int(user_id),
        source_thread_id=source_thread_id,
        source_message_id=int(source_message_id),
        event_time=event_time or now,
        payload_json=dict(payload_json or {}),
        dedupe_key=build_dedupe_key(user_id=user_id, source_message_id=source_message_id),
        status=MEMORY_INTENT_STATUS_PENDING,
        attempt_count=0,
        next_retry_time=now,
        create_time=now,
        update_time=now,
    )

    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
        return job, True
    except IntegrityError:
        existing = get_by_source_message(
            db,
            user_id=user_id,
            source_message_id=source_message_id,
        )
        if existing is not None:
            return existing, False
        raise


def promote_retryable_failed(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = DEFAULT_RETRY_RECOVER_LIMIT,
) -> int:
    """将到期 failed 任务回捞为 pending。"""

    current_time = now or datetime.now()
    safe_limit = _safe_positive_int(limit, DEFAULT_RETRY_RECOVER_LIMIT)
    jobs = (
        db.query(UserMemoryIntentJob)
        .filter(
            UserMemoryIntentJob.status == MEMORY_INTENT_STATUS_FAILED,
            UserMemoryIntentJob.next_retry_time <= current_time,
        )
        .order_by(UserMemoryIntentJob.next_retry_time.asc(), UserMemoryIntentJob.id.asc())
        .limit(safe_limit)
        .all()
    )

    for job in jobs:
        job.status = MEMORY_INTENT_STATUS_PENDING
        job.lease_until = None
        job.claimed_by = None
        job.claimed_at = None
        job.update_time = current_time

    return len(jobs)


def claim_pending(
    db: Session,
    *,
    worker_id: str,
    lease_seconds: int = DEFAULT_WORKER_LEASE_SECONDS,
    now: datetime | None = None,
) -> UserMemoryIntentJob | None:
    """使用 SKIP LOCKED 抢占一个 pending 任务。"""

    current_time = now or datetime.now()
    safe_worker_id = str(worker_id or "memory-intent-worker").strip() or "memory-intent-worker"
    safe_lease_seconds = _safe_positive_int(lease_seconds, DEFAULT_WORKER_LEASE_SECONDS)

    job = (
        db.query(UserMemoryIntentJob)
        .filter(
            UserMemoryIntentJob.status == MEMORY_INTENT_STATUS_PENDING,
            UserMemoryIntentJob.next_retry_time <= current_time,
        )
        .order_by(UserMemoryIntentJob.create_time.asc(), UserMemoryIntentJob.id.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if job is None:
        return None

    job.status = MEMORY_INTENT_STATUS_PROCESSING
    job.claimed_by = safe_worker_id
    job.claimed_at = current_time
    job.lease_until = current_time + timedelta(seconds=safe_lease_seconds)
    job.error_message = None
    job.update_time = current_time
    return job


def mark_succeeded(
    db: Session,
    *,
    job_id: int,
    worker_id: str,
    now: datetime | None = None,
) -> UserMemoryIntentJob | None:
    """将 processing 任务标记为 succeeded。"""

    current_time = now or datetime.now()
    job = (
        db.query(UserMemoryIntentJob)
        .filter(
            UserMemoryIntentJob.id == int(job_id),
            UserMemoryIntentJob.status == MEMORY_INTENT_STATUS_PROCESSING,
            UserMemoryIntentJob.claimed_by == str(worker_id),
        )
        .with_for_update()
        .first()
    )
    if job is None:
        return None

    job.status = MEMORY_INTENT_STATUS_SUCCEEDED
    job.lease_until = None
    job.claimed_by = None
    job.claimed_at = None
    job.error_message = None
    job.update_time = current_time
    return job


def mark_failed(
    db: Session,
    *,
    job_id: int,
    worker_id: str,
    error_message: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_retry_seconds: int = DEFAULT_RETRY_BASE_SECONDS,
    now: datetime | None = None,
) -> UserMemoryIntentJob | None:
    """将 processing 任务标记为 failed/dead_letter。"""

    current_time = now or datetime.now()
    safe_max_attempts = _safe_positive_int(max_attempts, DEFAULT_MAX_ATTEMPTS)
    safe_base_retry = _safe_positive_int(base_retry_seconds, DEFAULT_RETRY_BASE_SECONDS)
    job = (
        db.query(UserMemoryIntentJob)
        .filter(
            UserMemoryIntentJob.id == int(job_id),
            UserMemoryIntentJob.status == MEMORY_INTENT_STATUS_PROCESSING,
            UserMemoryIntentJob.claimed_by == str(worker_id),
        )
        .with_for_update()
        .first()
    )
    if job is None:
        return None

    next_attempt = int(job.attempt_count or 0) + 1
    job.attempt_count = next_attempt
    job.error_message = str(error_message or "")[:2000] or None
    job.lease_until = None
    job.claimed_by = None
    job.claimed_at = None

    if next_attempt >= safe_max_attempts:
        job.status = MEMORY_INTENT_STATUS_DEAD_LETTER
        job.next_retry_time = current_time
    else:
        job.status = MEMORY_INTENT_STATUS_FAILED
        backoff_seconds = _compute_backoff_seconds(
            attempt_count=next_attempt,
            base_retry_seconds=safe_base_retry,
        )
        job.next_retry_time = current_time + timedelta(seconds=backoff_seconds)

    job.update_time = current_time
    return job
