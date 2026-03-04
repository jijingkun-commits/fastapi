"""文档记忆向量补偿服务（中文注释）。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from app.ai.utils.embedding_util import get_embedding
from app.repositories import document_memory_repo


logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 32
DEFAULT_MAX_RETRY = 3
DEFAULT_SOURCE = "memory"


def _normalize_limit(limit: int, default: int = DEFAULT_BATCH_SIZE) -> int:
    return max(1, int(limit or default))


def _normalize_status_filter(status_filter: Iterable[str] | None) -> tuple[str, ...]:
    normalized = [
        str(item or "").strip().lower()
        for item in (status_filter or [])
        if str(item or "").strip()
    ]
    if not normalized:
        return (
            document_memory_repo.EMBEDDING_STATUS_PENDING,
            document_memory_repo.EMBEDDING_STATUS_FAILED,
        )
    return tuple(dict.fromkeys(normalized))


def compensate_pending_embeddings(
    db: Session,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    user_id: int | None = None,
    doc_id: int | None = None,
    status_filter: Iterable[str] | None = None,
    max_retry: int = DEFAULT_MAX_RETRY,
    source: str = DEFAULT_SOURCE,
) -> dict[str, int]:
    """处理待向量化分块。"""

    started_at = datetime.now()
    safe_limit = _normalize_limit(limit)
    statuses = _normalize_status_filter(status_filter)
    chunks = document_memory_repo.list_chunks_for_embedding(
        db,
        limit=safe_limit,
        user_id=user_id,
        doc_id=doc_id,
        statuses=statuses,
        max_retry=max_retry,
        source=source,
    )
    if not chunks:
        return {
            "total": 0,
            "processed": 0,
            "ready": 0,
            "failed": 0,
            "elapsed_ms": 0,
        }

    processed = 0
    ready = 0
    failed = 0
    for chunk in chunks:
        processed += 1
        try:
            embedding = get_embedding(chunk.chunk_text)
            if embedding:
                document_memory_repo.mark_chunk_embedding_ready(
                    db,
                    chunk_id=int(chunk.id),
                    embedding=embedding,
                    embedding_model=getattr(chunk, "embedding_model", None) or "embedding_route",
                )
                ready += 1
                continue

            document_memory_repo.mark_chunk_embedding_failed(
                db,
                chunk_id=int(chunk.id),
                error_message="embedding_empty",
            )
            failed += 1
        except Exception as embedding_error:  # pragma: no cover - 外部依赖异常
            logger.warning(
                "文档记忆向量化失败: chunk_id=%s, user_id=%s, error=%s",
                chunk.id,
                chunk.user_id,
                embedding_error,
            )
            document_memory_repo.mark_chunk_embedding_failed(
                db,
                chunk_id=int(chunk.id),
                error_message=str(embedding_error),
            )
            failed += 1

    db.commit()
    elapsed_ms = int((datetime.now() - started_at).total_seconds() * 1000)
    return {
        "total": len(chunks),
        "processed": processed,
        "ready": ready,
        "failed": failed,
        "elapsed_ms": elapsed_ms,
    }


def process_pending_chunks(
    db: Session,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    user_id: int | None = None,
    doc_id: int | None = None,
    status_filter: Iterable[str] | None = None,
    max_retry: int = DEFAULT_MAX_RETRY,
    source: str = DEFAULT_SOURCE,
) -> dict[str, int]:
    """兼容旧入口：转发到 compensate_pending_embeddings。"""

    return compensate_pending_embeddings(
        db,
        limit=limit,
        user_id=user_id,
        doc_id=doc_id,
        status_filter=status_filter,
        max_retry=max_retry,
        source=source,
    )


def retry_failed_chunks(
    db: Session,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    user_id: int | None = None,
    doc_id: int | None = None,
    source: str = DEFAULT_SOURCE,
) -> int:
    """重置失败分块为待处理。"""

    reset_count = document_memory_repo.retry_failed_chunks(
        db,
        limit=_normalize_limit(limit),
        user_id=user_id,
        doc_id=doc_id,
        source=source,
    )
    if reset_count:
        db.commit()
    return int(reset_count)


def get_embedding_status(
    db: Session,
    *,
    user_id: int | None = None,
    doc_id: int | None = None,
    source: str = DEFAULT_SOURCE,
) -> dict[str, int]:
    """查询向量状态统计。"""

    return document_memory_repo.get_embedding_status_counts(
        db,
        user_id=user_id,
        doc_id=doc_id,
        source=source,
    )
