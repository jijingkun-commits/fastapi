"""文档化永久记忆数据访问层（中文注释）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.document_memory import UserMemoryChunk, UserMemoryDocument


ACTIVE_STATUS = "active"
EMBEDDING_STATUS_PENDING = "pending"
EMBEDDING_STATUS_READY = "ready"
EMBEDDING_STATUS_FAILED = "failed"


def get_active_document(
    db: Session,
    *,
    user_id: int,
    doc_kind: str,
    doc_key: str,
) -> Optional[UserMemoryDocument]:
    """按用户 + 文档键查询活跃文档。"""

    return (
        db.query(UserMemoryDocument)
        .filter(
            UserMemoryDocument.user_id == user_id,
            UserMemoryDocument.doc_kind == doc_kind,
            UserMemoryDocument.doc_key == doc_key,
            UserMemoryDocument.status == ACTIVE_STATUS,
        )
        .first()
    )


def upsert_document(
    db: Session,
    *,
    user_id: int,
    doc_kind: str,
    doc_key: str,
    title: str | None,
    content_md: str,
    content_hash: str,
    summary_md: str | None = None,
    source: str = "memory",
    scope: str = "private",
    scope_ref: str | None = None,
    source_thread_id: str | None = None,
    source_message_id: int | None = None,
) -> UserMemoryDocument:
    """按文档键执行幂等 upsert。"""

    now = datetime.now()
    document = get_active_document(
        db,
        user_id=user_id,
        doc_kind=doc_kind,
        doc_key=doc_key,
    )

    if document is None:
        document = UserMemoryDocument(
            user_id=user_id,
            doc_kind=doc_kind,
            doc_key=doc_key,
            title=title,
            content_md=content_md,
            summary_md=summary_md,
            source=source,
            scope=scope,
            scope_ref=scope_ref,
            status=ACTIVE_STATUS,
            revision=1,
            content_hash=content_hash,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
            create_time=now,
            update_time=now,
        )
        db.add(document)
        db.flush()
        return document

    changed = document.content_hash != content_hash or document.content_md != content_md
    document.title = title
    document.content_md = content_md
    document.summary_md = summary_md
    document.source = source
    document.scope = scope
    document.scope_ref = scope_ref
    document.content_hash = content_hash
    document.source_thread_id = source_thread_id
    document.source_message_id = source_message_id
    document.update_time = now
    if changed:
        document.revision = int(document.revision or 1) + 1
    db.flush()
    return document


def replace_document_chunks(
    db: Session,
    *,
    user_id: int,
    doc_id: int,
    chunks: list[dict[str, Any]],
    source: str = "memory",
) -> int:
    """替换文档所有分块。"""

    (
        db.query(UserMemoryChunk)
        .filter(
            UserMemoryChunk.user_id == user_id,
            UserMemoryChunk.doc_id == doc_id,
        )
        .delete(synchronize_session=False)
    )

    inserted = 0
    for chunk in chunks:
        embedding = chunk.get("embedding")
        embedding_status = str(
            chunk.get("embedding_status")
            or (EMBEDDING_STATUS_READY if embedding is not None else EMBEDDING_STATUS_PENDING)
        )
        row = UserMemoryChunk(
            doc_id=doc_id,
            user_id=user_id,
            chunk_no=int(chunk.get("chunk_no") or 0),
            start_line=int(chunk.get("start_line") or 1),
            end_line=int(chunk.get("end_line") or 1),
            chunk_text=str(chunk.get("chunk_text") or ""),
            chunk_hash=str(chunk.get("chunk_hash") or ""),
            embedding=embedding,
            embedding_model=chunk.get("embedding_model"),
            embedding_status=embedding_status,
            embedding_retry_count=int(chunk.get("embedding_retry_count") or 0),
            embedding_error=chunk.get("embedding_error"),
            embedding_updated_time=chunk.get("embedding_updated_time"),
            source=str(chunk.get("source") or source),
        )
        db.add(row)
        inserted += 1

    db.flush()
    return inserted


def search_chunks(
    db: Session,
    *,
    user_id: int,
    query_text: str,
    limit: int = 6,
    source: str = "memory",
    query_embedding: list[float] | None = None,
    text_weight: float = 0.3,
    vector_weight: float = 0.7,
) -> list[dict[str, Any]]:
    """按混合检索召回文档分块（FTS + 向量）。"""

    cleaned_query = str(query_text or "").strip()
    if not cleaned_query:
        return []

    sql = text(
        """
        SELECT
            c.id AS chunk_id,
            c.doc_id,
            c.chunk_no,
            c.start_line,
            c.end_line,
            c.chunk_text,
            c.source,
            d.doc_kind,
            d.doc_key,
            d.title AS doc_title,
            ts_rank(c.chunk_tsv, plainto_tsquery('simple', :query_text)) AS text_score,
            CASE
              WHEN :query_embedding IS NULL OR c.embedding IS NULL THEN 0.0::float
              ELSE (1 - (c.embedding <=> CAST(:query_embedding AS vector)))::float
            END AS vector_score,
            (
              :text_weight * ts_rank(c.chunk_tsv, plainto_tsquery('simple', :query_text))
              + :vector_weight * CASE
                WHEN :query_embedding IS NULL OR c.embedding IS NULL THEN 0.0::float
                ELSE (1 - (c.embedding <=> CAST(:query_embedding AS vector)))::float
              END
            )::float AS final_score
        FROM t_user_memory_chunk c
        JOIN t_user_memory_document d ON d.id = c.doc_id
        WHERE c.user_id = :user_id
          AND d.user_id = :user_id
          AND d.status = 'active'
          AND c.source = :source
          AND (
            c.chunk_tsv @@ plainto_tsquery('simple', :query_text)
            OR (:query_embedding IS NOT NULL AND c.embedding IS NOT NULL)
          )
        ORDER BY final_score DESC, text_score DESC, c.update_time DESC, c.id DESC
        LIMIT :limit
        """
    )
    rows = db.execute(
        sql,
        {
            "user_id": user_id,
            "query_text": cleaned_query,
            "limit": max(1, int(limit)),
            "source": source,
            "query_embedding": query_embedding,
            "text_weight": float(text_weight),
            "vector_weight": float(vector_weight),
        },
    ).mappings().all()

    results = [dict(row) for row in rows]
    if results:
        return results

    fallback_sql = text(
        """
        SELECT
            c.id AS chunk_id,
            c.doc_id,
            c.chunk_no,
            c.start_line,
            c.end_line,
            c.chunk_text,
            c.source,
            d.doc_kind,
            d.doc_key,
            d.title AS doc_title,
            0.0::float AS text_score,
            0.0::float AS vector_score,
            0.0::float AS final_score
        FROM t_user_memory_chunk c
        JOIN t_user_memory_document d ON d.id = c.doc_id
        WHERE c.user_id = :user_id
          AND d.user_id = :user_id
          AND d.status = 'active'
          AND c.source = :source
        ORDER BY c.update_time DESC, c.id DESC
        LIMIT :limit
        """
    )
    fallback_rows = db.execute(
        fallback_sql,
        {
            "user_id": user_id,
            "limit": max(1, int(limit)),
            "source": source,
        },
    ).mappings().all()
    return [dict(row) for row in fallback_rows]


def _normalize_embedding_statuses(statuses: Iterable[str] | None) -> tuple[str, ...]:
    normalized = [
        str(status or "").strip().lower()
        for status in (statuses or [])
        if str(status or "").strip()
    ]
    if not normalized:
        return (EMBEDDING_STATUS_PENDING, EMBEDDING_STATUS_FAILED)
    return tuple(dict.fromkeys(normalized))


def list_chunks_for_embedding(
    db: Session,
    *,
    limit: int = 200,
    user_id: int | None = None,
    doc_id: int | None = None,
    statuses: Iterable[str] | None = None,
    max_retry: int = 3,
    source: str = "memory",
) -> list[UserMemoryChunk]:
    """查询待向量化分块。"""

    query = (
        db.query(UserMemoryChunk)
        .join(UserMemoryDocument, UserMemoryDocument.id == UserMemoryChunk.doc_id)
        .filter(
            UserMemoryDocument.status == ACTIVE_STATUS,
            UserMemoryChunk.source == source,
        )
    )

    if user_id:
        query = query.filter(UserMemoryChunk.user_id == user_id)
    if doc_id:
        query = query.filter(UserMemoryChunk.doc_id == doc_id)

    status_tuple = _normalize_embedding_statuses(statuses)
    query = query.filter(UserMemoryChunk.embedding_status.in_(status_tuple))
    if max_retry >= 0:
        query = query.filter(UserMemoryChunk.embedding_retry_count < int(max_retry))

    return (
        query.order_by(
            UserMemoryChunk.update_time.asc(),
            UserMemoryChunk.id.asc(),
        )
        .limit(max(1, int(limit)))
        .all()
    )


def mark_chunk_embedding_ready(
    db: Session,
    *,
    chunk_id: int,
    embedding: list[float],
    embedding_model: str | None,
) -> bool:
    """标记分块向量生成成功。"""

    chunk = db.query(UserMemoryChunk).filter(UserMemoryChunk.id == chunk_id).first()
    if chunk is None:
        return False

    now = datetime.now()
    chunk.embedding = embedding
    chunk.embedding_model = embedding_model
    chunk.embedding_status = EMBEDDING_STATUS_READY
    chunk.embedding_error = None
    chunk.embedding_updated_time = now
    chunk.update_time = now
    db.flush()
    return True


def mark_chunk_embedding_failed(
    db: Session,
    *,
    chunk_id: int,
    error_message: str,
) -> bool:
    """标记分块向量生成失败。"""

    chunk = db.query(UserMemoryChunk).filter(UserMemoryChunk.id == chunk_id).first()
    if chunk is None:
        return False

    now = datetime.now()
    chunk.embedding_status = EMBEDDING_STATUS_FAILED
    chunk.embedding_retry_count = int(chunk.embedding_retry_count or 0) + 1
    chunk.embedding_error = str(error_message or "")[:500]
    chunk.embedding_updated_time = now
    chunk.update_time = now
    db.flush()
    return True


def retry_failed_chunks(
    db: Session,
    *,
    limit: int = 200,
    user_id: int | None = None,
    doc_id: int | None = None,
    source: str = "memory",
) -> int:
    """将失败分块重置为 pending。"""

    query = db.query(UserMemoryChunk).filter(
        UserMemoryChunk.embedding_status == EMBEDDING_STATUS_FAILED,
        UserMemoryChunk.source == source,
    )
    if user_id:
        query = query.filter(UserMemoryChunk.user_id == user_id)
    if doc_id:
        query = query.filter(UserMemoryChunk.doc_id == doc_id)

    rows = (
        query.order_by(UserMemoryChunk.update_time.asc(), UserMemoryChunk.id.asc())
        .limit(max(1, int(limit)))
        .all()
    )
    if not rows:
        return 0

    now = datetime.now()
    for chunk in rows:
        chunk.embedding_status = EMBEDDING_STATUS_PENDING
        chunk.embedding_error = None
        chunk.update_time = now
    db.flush()
    return len(rows)


def get_embedding_status_counts(
    db: Session,
    *,
    user_id: int | None = None,
    doc_id: int | None = None,
    source: str = "memory",
) -> dict[str, int]:
    """查询向量状态统计。"""

    sql = text(
        """
        SELECT
            COUNT(1)::int AS total,
            COUNT(1) FILTER (WHERE c.embedding_status = 'pending')::int AS pending,
            COUNT(1) FILTER (WHERE c.embedding_status = 'ready')::int AS ready,
            COUNT(1) FILTER (WHERE c.embedding_status = 'failed')::int AS failed
        FROM t_user_memory_chunk c
        JOIN t_user_memory_document d ON d.id = c.doc_id
        WHERE d.status = 'active'
          AND c.source = :source
          AND (:user_id::int IS NULL OR c.user_id = :user_id)
          AND (:doc_id::bigint IS NULL OR c.doc_id = :doc_id)
        """
    )
    row = db.execute(
        sql,
        {
            "source": source,
            "user_id": user_id,
            "doc_id": doc_id,
        },
    ).mappings().first()
    if row is None:
        return {"total": 0, "pending": 0, "ready": 0, "failed": 0}
    return {
        "total": int(row.get("total") or 0),
        "pending": int(row.get("pending") or 0),
        "ready": int(row.get("ready") or 0),
        "failed": int(row.get("failed") or 0),
    }


def count_embedding_candidates(
    db: Session,
    *,
    user_id: int | None = None,
    doc_id: int | None = None,
    statuses: Iterable[str] | None = None,
    source: str = "memory",
) -> int:
    """统计待处理分块数量。"""

    status_tuple = _normalize_embedding_statuses(statuses)
    query = (
        db.query(UserMemoryChunk)
        .join(UserMemoryDocument, UserMemoryDocument.id == UserMemoryChunk.doc_id)
        .filter(
            UserMemoryDocument.status == ACTIVE_STATUS,
            UserMemoryChunk.source == source,
            UserMemoryChunk.embedding_status.in_(status_tuple),
        )
    )
    if user_id:
        query = query.filter(UserMemoryChunk.user_id == user_id)
    if doc_id:
        query = query.filter(UserMemoryChunk.doc_id == doc_id)
    return int(query.count())


def get_document_excerpt(
    db: Session,
    *,
    user_id: int,
    doc_id: int,
    from_line: int = 1,
    lines: int = 40,
) -> Optional[dict[str, Any]]:
    """读取文档局部内容。"""

    document = (
        db.query(UserMemoryDocument)
        .filter(
            UserMemoryDocument.id == doc_id,
            UserMemoryDocument.user_id == user_id,
            UserMemoryDocument.status == ACTIVE_STATUS,
        )
        .first()
    )
    if document is None:
        return None

    all_lines = (document.content_md or "").splitlines()
    start_line = max(1, int(from_line))
    line_count = max(1, int(lines))
    segment = all_lines[start_line - 1: start_line - 1 + line_count]
    end_line = start_line + max(0, len(segment) - 1)

    return {
        "doc_id": document.id,
        "doc_kind": document.doc_kind,
        "doc_key": document.doc_key,
        "title": document.title,
        "start_line": start_line,
        "end_line": end_line,
        "text": "\n".join(segment),
    }
