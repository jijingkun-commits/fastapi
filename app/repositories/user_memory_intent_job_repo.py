"""用户记忆意图任务仓储层（中文注释）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_memory_intent_job import (
    MEMORY_INTENT_STATUS_PENDING,
    UserMemoryIntentJob,
)


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
