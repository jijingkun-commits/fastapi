"""幂等键数据访问层（中文注释）。"""
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.idempotency_key import IdempotencyKey


def try_start(
    db: Session,
    *,
    key: str,
    user_id: Optional[int],
    endpoint: str,
    thread_id: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """尝试创建幂等键记录。

    Returns:
        (ok, status) ok 为 True 表示首次请求；False 表示重复请求
    """
    existing = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.key == key,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.user_id == user_id,
        )
        .first()
    )
    if existing:
        return False, existing.status

    record = IdempotencyKey(
        key=key,
        user_id=user_id,
        endpoint=endpoint,
        status="started",
        thread_id=thread_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(record)
    try:
        db.commit()
        return True, "started"
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.key == key,
                IdempotencyKey.endpoint == endpoint,
                IdempotencyKey.user_id == user_id,
            )
            .first()
        )
        return False, existing.status if existing else "started"


def mark_completed(
    db: Session,
    *,
    key: str,
    user_id: Optional[int],
    endpoint: str,
    thread_id: Optional[str] = None,
) -> None:
    """标记幂等键为 completed。"""
    record = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.key == key,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.user_id == user_id,
        )
        .first()
    )
    if not record:
        return
    record.status = "completed"
    record.updated_at = datetime.now()
    if thread_id:
        record.thread_id = thread_id
    db.commit()


def mark_failed(
    db: Session,
    *,
    key: str,
    user_id: Optional[int],
    endpoint: str,
    thread_id: Optional[str] = None,
) -> None:
    """标记幂等键为 failed。"""
    record = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.key == key,
            IdempotencyKey.endpoint == endpoint,
            IdempotencyKey.user_id == user_id,
        )
        .first()
    )
    if not record:
        return
    record.status = "failed"
    record.updated_at = datetime.now()
    if thread_id:
        record.thread_id = thread_id
    db.commit()
