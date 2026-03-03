"""用户偏好记忆数据访问层（中文注释）。"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user_memory import UserMemory


ACTIVE_STATUS = "active"
ARCHIVED_STATUS = "archived"


def list_active_memories(
    db: Session,
    *,
    user_id: int,
    scope: str = "global",
    limit: int = 20,
) -> list[UserMemory]:
    """按用户查询活跃偏好记忆。"""

    query = (
        db.query(UserMemory)
        .filter(
            UserMemory.user_id == user_id,
            UserMemory.status == ACTIVE_STATUS,
        )
        .order_by(UserMemory.update_time.desc(), UserMemory.id.desc())
    )

    if scope:
        query = query.filter(UserMemory.scope == scope)

    return query.limit(limit).all()


def get_active_memory_by_key(
    db: Session,
    *,
    user_id: int,
    memory_key: str,
    scope: str = "global",
) -> Optional[UserMemory]:
    """按 key 查询活跃偏好。"""

    return (
        db.query(UserMemory)
        .filter(
            UserMemory.user_id == user_id,
            UserMemory.scope == scope,
            UserMemory.memory_key == memory_key,
            UserMemory.status == ACTIVE_STATUS,
        )
        .first()
    )


def upsert_active_memory(
    db: Session,
    *,
    user_id: int,
    memory_key: str,
    memory_value: str,
    scope: str = "global",
    confidence: Decimal = Decimal("1.000"),
    source_thread_id: Optional[str] = None,
    source_message_id: Optional[int] = None,
) -> UserMemory:
    """按 key 覆盖更新（仅 active 记录）。"""

    now = datetime.now()
    memory = get_active_memory_by_key(
        db,
        user_id=user_id,
        scope=scope,
        memory_key=memory_key,
    )

    if memory is None:
        memory = UserMemory(
            user_id=user_id,
            scope=scope,
            memory_key=memory_key,
            memory_value=memory_value,
            confidence=confidence,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
            status=ACTIVE_STATUS,
            create_time=now,
            update_time=now,
            last_seen_at=now,
        )
        db.add(memory)
        db.flush()
        return memory

    memory.memory_value = memory_value
    memory.confidence = confidence
    memory.source_thread_id = source_thread_id
    memory.source_message_id = source_message_id
    memory.update_time = now
    memory.last_seen_at = now
    db.flush()
    return memory


def touch_last_seen(db: Session, memories: list[UserMemory]) -> None:
    """批量刷新最近命中时间。"""

    if not memories:
        return

    now = datetime.now()
    for memory in memories:
        memory.last_seen_at = now
    db.flush()


def archive_active_memories(
    db: Session,
    *,
    user_id: int,
    scope: str = "global",
    memory_keys: list[str] | None = None,
) -> int:
    """将活跃 KV 记忆归档，避免重复迁移。"""

    now = datetime.now()
    query = db.query(UserMemory).filter(
        UserMemory.user_id == user_id,
        UserMemory.status == ACTIVE_STATUS,
    )
    if scope:
        query = query.filter(UserMemory.scope == scope)
    if memory_keys:
        keys = [str(item).strip() for item in memory_keys if str(item).strip()]
        if not keys:
            return 0
        query = query.filter(UserMemory.memory_key.in_(keys))

    affected = query.update(
        {
            UserMemory.status: ARCHIVED_STATUS,
            UserMemory.update_time: now,
        },
        synchronize_session=False,
    )
    db.flush()
    return int(affected or 0)
