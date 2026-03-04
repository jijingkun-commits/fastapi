"""用户记忆意图任务服务（中文注释）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.user_memory_intent_job import UserMemoryIntentJob
from app.repositories import user_memory_intent_job_repo


def _build_chat_payload(
    *,
    user_text: str,
    source_thread_id: str | None,
    source_message_id: int,
) -> dict[str, Any]:
    """构建聊天入队载荷。"""

    return {
        "user_text": user_text,
        "source_thread_id": source_thread_id,
        "source_message_id": int(source_message_id),
    }


def enqueue_from_chat_message(
    db: Session,
    *,
    user_id: int,
    source_thread_id: str | None,
    source_message_id: int,
    user_text: str,
    event_time: datetime | None = None,
) -> tuple[UserMemoryIntentJob, bool]:
    """将聊天消息入队为记忆意图任务（幂等）。"""

    payload_json = _build_chat_payload(
        user_text=user_text,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
    )
    return user_memory_intent_job_repo.enqueue_pending_job(
        db,
        user_id=user_id,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        payload_json=payload_json,
        event_time=event_time,
    )
