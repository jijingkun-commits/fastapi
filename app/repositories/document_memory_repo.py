"""文档化永久记忆数据访问层（中文注释）。"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Iterable, Optional

from sqlalchemy import case, func, or_, text
from sqlalchemy.orm import Session

from app.models.document_memory import UserMemoryChunk, UserMemoryDocument


ACTIVE_STATUS = "active"
ARCHIVED_STATUS = "archived"
EMBEDDING_STATUS_PENDING = "pending"
EMBEDDING_STATUS_READY = "ready"
EMBEDDING_STATUS_FAILED = "failed"
EMBEDDING_DIMENSION_USER = "user"
EMBEDDING_DIMENSION_DOC = "doc"


def count_documents(
    db: Session,
    *,
    user_id: int | None = None,
    doc_kind: str | None = None,
    status: str | None = ACTIVE_STATUS,
    source: str | None = None,
) -> int:
    """统计文档条数。"""

    query = db.query(func.count(UserMemoryDocument.id))

    if user_id is not None:
        query = query.filter(UserMemoryDocument.user_id == int(user_id))
    if status:
        query = query.filter(UserMemoryDocument.status == str(status))
    if doc_kind:
        query = query.filter(UserMemoryDocument.doc_kind == str(doc_kind))
    if source:
        query = query.filter(UserMemoryDocument.source == str(source))

    return int(query.scalar() or 0)


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


def get_active_slot(
    db: Session,
    *,
    user_id: int,
    slot_key: str,
    doc_kind: str | None = None,
    source: str = "memory",
    for_update: bool = False,
) -> Optional[UserMemoryDocument]:
    """按槽位查询活跃文档，支持行级锁。"""

    normalized_slot_key = str(slot_key or "").strip()
    if not normalized_slot_key:
        return None

    query = db.query(UserMemoryDocument).filter(
        UserMemoryDocument.user_id == int(user_id),
        UserMemoryDocument.status == ACTIVE_STATUS,
        UserMemoryDocument.source == str(source),
        or_(
            UserMemoryDocument.slot_key == normalized_slot_key,
            UserMemoryDocument.doc_key == normalized_slot_key,
        ),
    )
    if doc_kind:
        query = query.filter(UserMemoryDocument.doc_kind == str(doc_kind))
    if for_update:
        query = query.with_for_update()

    return (
        query.order_by(
            UserMemoryDocument.update_time.desc(),
            UserMemoryDocument.id.desc(),
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
    slot_key: str | None = None,
    operation: str | None = None,
    last_event_time: datetime | None = None,
    revision: int | None = None,
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
            slot_key=slot_key,
            title=title,
            content_md=content_md,
            summary_md=summary_md,
            source=source,
            scope=scope,
            scope_ref=scope_ref,
            status=ACTIVE_STATUS,
            revision=max(1, int(revision or 1)),
            operation=str(operation or "upsert"),
            content_hash=content_hash,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
            last_event_time=last_event_time,
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
    if slot_key is not None:
        document.slot_key = slot_key
    if operation is not None:
        document.operation = str(operation)
    if last_event_time is not None:
        document.last_event_time = last_event_time
    document.content_hash = content_hash
    document.source_thread_id = source_thread_id
    document.source_message_id = source_message_id
    document.update_time = now
    if revision is not None:
        document.revision = max(1, int(revision))
    elif changed:
        document.revision = int(document.revision or 1) + 1
    db.flush()
    return document


def upsert_slot(
    db: Session,
    *,
    user_id: int,
    doc_kind: str,
    slot_key: str,
    title: str | None,
    content_md: str,
    summary_md: str | None = None,
    source: str = "memory",
    scope: str = "private",
    scope_ref: str | None = None,
    source_thread_id: str | None = None,
    source_message_id: int | None = None,
    operation: str = "upsert",
    last_event_time: datetime | None = None,
    revision: int | None = None,
) -> UserMemoryDocument:
    """按槽位 upsert 文档。"""

    normalized_slot_key = str(slot_key or "").strip()
    if not normalized_slot_key:
        raise ValueError("slot_key_required")

    return upsert_document(
        db,
        user_id=user_id,
        doc_kind=doc_kind,
        doc_key=normalized_slot_key,
        slot_key=normalized_slot_key,
        title=title,
        content_md=content_md,
        summary_md=summary_md,
        source=source,
        scope=scope,
        scope_ref=scope_ref,
        content_hash=hashlib.sha256(content_md.encode("utf-8")).hexdigest(),
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        operation=operation,
        last_event_time=last_event_time,
        revision=revision,
    )


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


def _normalize_embedding_dimension(dimension: str | None) -> str | None:
    normalized = str(dimension or "").strip().lower()
    if normalized in {EMBEDDING_DIMENSION_USER, EMBEDDING_DIMENSION_DOC}:
        return normalized
    return None


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
    dimension: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
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
          AND c.user_id = COALESCE(CAST(:user_id AS int), c.user_id)
          AND c.doc_id = COALESCE(CAST(:doc_id AS bigint), c.doc_id)
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
    status = {
        "total": int((row or {}).get("total") or 0),
        "pending": int((row or {}).get("pending") or 0),
        "ready": int((row or {}).get("ready") or 0),
        "failed": int((row or {}).get("failed") or 0),
    }

    normalized_dimension = _normalize_embedding_dimension(dimension)
    if normalized_dimension is None:
        return status

    safe_limit = max(1, int(limit))
    safe_offset = max(0, int(offset))
    params = {
        "source": source,
        "user_id": user_id,
        "doc_id": doc_id,
        "limit": safe_limit,
        "offset": safe_offset,
    }

    if normalized_dimension == EMBEDDING_DIMENSION_USER:
        group_sql = text(
            """
            SELECT
                c.user_id::int AS user_id,
                COUNT(1)::int AS total,
                COUNT(1) FILTER (WHERE c.embedding_status = 'pending')::int AS pending,
                COUNT(1) FILTER (WHERE c.embedding_status = 'ready')::int AS ready,
                COUNT(1) FILTER (WHERE c.embedding_status = 'failed')::int AS failed,
                COUNT(DISTINCT c.doc_id)::int AS document_total
            FROM t_user_memory_chunk c
            JOIN t_user_memory_document d ON d.id = c.doc_id
            WHERE d.status = 'active'
              AND c.source = :source
              AND c.user_id = COALESCE(CAST(:user_id AS int), c.user_id)
              AND c.doc_id = COALESCE(CAST(:doc_id AS bigint), c.doc_id)
            GROUP BY c.user_id
            ORDER BY total DESC, c.user_id ASC
            OFFSET :offset
            LIMIT :limit
            """
        )
        group_total_sql = text(
            """
            SELECT COUNT(1)::int AS group_total
            FROM (
                SELECT c.user_id
                FROM t_user_memory_chunk c
                JOIN t_user_memory_document d ON d.id = c.doc_id
                WHERE d.status = 'active'
                  AND c.source = :source
                  AND c.user_id = COALESCE(CAST(:user_id AS int), c.user_id)
                  AND c.doc_id = COALESCE(CAST(:doc_id AS bigint), c.doc_id)
                GROUP BY c.user_id
            ) grouped
            """
        )
    else:
        group_sql = text(
            """
            SELECT
                c.doc_id::bigint AS doc_id,
                c.user_id::int AS user_id,
                d.doc_kind,
                d.doc_key,
                d.title,
                COUNT(1)::int AS total,
                COUNT(1) FILTER (WHERE c.embedding_status = 'pending')::int AS pending,
                COUNT(1) FILTER (WHERE c.embedding_status = 'ready')::int AS ready,
                COUNT(1) FILTER (WHERE c.embedding_status = 'failed')::int AS failed
            FROM t_user_memory_chunk c
            JOIN t_user_memory_document d ON d.id = c.doc_id
            WHERE d.status = 'active'
              AND c.source = :source
              AND c.user_id = COALESCE(CAST(:user_id AS int), c.user_id)
              AND c.doc_id = COALESCE(CAST(:doc_id AS bigint), c.doc_id)
            GROUP BY c.doc_id, c.user_id, d.doc_kind, d.doc_key, d.title
            ORDER BY total DESC, c.doc_id ASC
            OFFSET :offset
            LIMIT :limit
            """
        )
        group_total_sql = text(
            """
            SELECT COUNT(1)::int AS group_total
            FROM (
                SELECT c.doc_id, c.user_id
                FROM t_user_memory_chunk c
                JOIN t_user_memory_document d ON d.id = c.doc_id
                WHERE d.status = 'active'
                  AND c.source = :source
                  AND c.user_id = COALESCE(CAST(:user_id AS int), c.user_id)
                  AND c.doc_id = COALESCE(CAST(:doc_id AS bigint), c.doc_id)
                GROUP BY c.doc_id, c.user_id
            ) grouped
            """
        )

    group_rows = db.execute(group_sql, params).mappings().all()
    group_total_row = db.execute(group_total_sql, params).mappings().first()

    groups: list[dict[str, Any]] = []
    for group_row in group_rows:
        group_item: dict[str, Any] = {
            "total": int(group_row.get("total") or 0),
            "pending": int(group_row.get("pending") or 0),
            "ready": int(group_row.get("ready") or 0),
            "failed": int(group_row.get("failed") or 0),
        }
        if normalized_dimension == EMBEDDING_DIMENSION_USER:
            group_item.update(
                user_id=int(group_row.get("user_id") or 0),
                document_total=int(group_row.get("document_total") or 0),
            )
        else:
            group_item.update(
                doc_id=int(group_row.get("doc_id") or 0),
                user_id=int(group_row.get("user_id") or 0),
                doc_kind=str(group_row.get("doc_kind") or ""),
                doc_key=str(group_row.get("doc_key") or ""),
                title=group_row.get("title"),
            )
        groups.append(group_item)

    return {
        **status,
        "dimension": normalized_dimension,
        "limit": safe_limit,
        "offset": safe_offset,
        "group_total": int((group_total_row or {}).get("group_total") or 0),
        "groups": groups,
    }


def get_memory_overview_stats(
    db: Session,
    *,
    source: str = "memory",
    top_n: int = 10,
) -> dict[str, Any]:
    """读取文档记忆总览统计。"""

    safe_top_n = max(1, int(top_n))
    totals_sql = text(
        """
        WITH active_documents AS (
            SELECT id, user_id
            FROM t_user_memory_document
            WHERE status = 'active'
              AND source = :source
        ),
        source_chunks AS (
            SELECT c.id
            FROM t_user_memory_chunk c
            JOIN active_documents d ON d.id = c.doc_id
            WHERE c.source = :source
        )
        SELECT
            (SELECT COUNT(1) FROM active_documents)::int AS total_documents,
            (SELECT COUNT(DISTINCT user_id) FROM active_documents)::int AS total_users,
            (SELECT COUNT(1) FROM source_chunks)::int AS total_chunks
        """
    )
    totals_row = db.execute(totals_sql, {"source": source}).mappings().first()

    embedding_status = get_embedding_status_counts(db, source=source)
    user_groups = get_embedding_status_counts(
        db,
        source=source,
        dimension=EMBEDDING_DIMENSION_USER,
        limit=safe_top_n,
    )
    doc_groups = get_embedding_status_counts(
        db,
        source=source,
        dimension=EMBEDDING_DIMENSION_DOC,
        limit=safe_top_n,
    )

    return {
        "totals": {
            "users": int((totals_row or {}).get("total_users") or 0),
            "documents": int((totals_row or {}).get("total_documents") or 0),
            "chunks": int((totals_row or {}).get("total_chunks") or 0),
        },
        "embedding_status": embedding_status,
        "top_users": list(user_groups.get("groups") or []),
        "top_documents": list(doc_groups.get("groups") or []),
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


def _normalize_optional_filter(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    if not cleaned:
        return None
    return cleaned


def list_documents(
    db: Session,
    *,
    user_id: int | None = None,
    doc_kind: str | None = None,
    status: str | None = ACTIVE_STATUS,
    source: str | None = None,
    keyword: str | None = None,
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """分页查询记忆文档列表（含分块状态聚合）。"""

    safe_page = max(1, int(page))
    safe_page_size = max(1, int(page_size))
    offset = (safe_page - 1) * safe_page_size

    chunk_stats_subquery = (
        db.query(
            UserMemoryChunk.doc_id.label("doc_id"),
            func.count(UserMemoryChunk.id).label("chunk_total"),
            func.sum(
                case(
                    (UserMemoryChunk.embedding_status == EMBEDDING_STATUS_READY, 1),
                    else_=0,
                )
            ).label("ready_chunks"),
            func.sum(
                case(
                    (UserMemoryChunk.embedding_status == EMBEDDING_STATUS_FAILED, 1),
                    else_=0,
                )
            ).label("failed_chunks"),
        )
        .group_by(UserMemoryChunk.doc_id)
        .subquery()
    )

    query = (
        db.query(
            UserMemoryDocument,
            chunk_stats_subquery.c.chunk_total,
            chunk_stats_subquery.c.ready_chunks,
            chunk_stats_subquery.c.failed_chunks,
        )
        .outerjoin(
            chunk_stats_subquery,
            chunk_stats_subquery.c.doc_id == UserMemoryDocument.id,
        )
    )

    if user_id is not None:
        query = query.filter(UserMemoryDocument.user_id == int(user_id))

    normalized_status = _normalize_optional_filter(status)
    if normalized_status and normalized_status.lower() != "all":
        query = query.filter(UserMemoryDocument.status == normalized_status.lower())

    normalized_doc_kind = _normalize_optional_filter(doc_kind)
    if normalized_doc_kind:
        query = query.filter(func.lower(UserMemoryDocument.doc_kind) == normalized_doc_kind.lower())

    normalized_source = _normalize_optional_filter(source)
    if normalized_source:
        query = query.filter(func.lower(UserMemoryDocument.source) == normalized_source.lower())

    normalized_keyword = _normalize_optional_filter(keyword)
    if normalized_keyword:
        like_value = f"%{normalized_keyword}%"
        query = query.filter(
            or_(
                UserMemoryDocument.title.ilike(like_value),
                UserMemoryDocument.doc_key.ilike(like_value),
                UserMemoryDocument.content_md.ilike(like_value),
            )
        )

    if updated_from is not None:
        query = query.filter(UserMemoryDocument.update_time >= updated_from)
    if updated_to is not None:
        query = query.filter(UserMemoryDocument.update_time <= updated_to)

    total = int(query.with_entities(func.count(UserMemoryDocument.id)).scalar() or 0)
    rows = (
        query.order_by(
            UserMemoryDocument.update_time.desc(),
            UserMemoryDocument.id.desc(),
        )
        .offset(offset)
        .limit(safe_page_size)
        .all()
    )

    items: list[dict[str, Any]] = []
    for document, chunk_total, ready_chunks, failed_chunks in rows:
        items.append(
            {
                "memory_id": int(document.id),
                "user_id": int(document.user_id),
                "doc_kind": str(document.doc_kind),
                "doc_key": str(document.doc_key),
                "title": document.title,
                "summary_md": document.summary_md,
                "source": str(document.source),
                "scope": str(document.scope),
                "scope_ref": document.scope_ref,
                "status": str(document.status),
                "revision": int(document.revision or 1),
                "chunk_total": int(chunk_total or 0),
                "ready_chunks": int(ready_chunks or 0),
                "failed_chunks": int(failed_chunks or 0),
                "create_time": document.create_time,
                "update_time": document.update_time,
            }
        )
    return items, total


def get_document_detail(
    db: Session,
    *,
    doc_id: int,
    user_id: int | None = None,
) -> Optional[dict[str, Any]]:
    """查询单条记忆文档详情。"""

    chunk_stats_subquery = (
        db.query(
            UserMemoryChunk.doc_id.label("doc_id"),
            func.count(UserMemoryChunk.id).label("chunk_total"),
            func.sum(
                case(
                    (UserMemoryChunk.embedding_status == EMBEDDING_STATUS_READY, 1),
                    else_=0,
                )
            ).label("ready_chunks"),
            func.sum(
                case(
                    (UserMemoryChunk.embedding_status == EMBEDDING_STATUS_FAILED, 1),
                    else_=0,
                )
            ).label("failed_chunks"),
        )
        .group_by(UserMemoryChunk.doc_id)
        .subquery()
    )

    query = (
        db.query(
            UserMemoryDocument,
            chunk_stats_subquery.c.chunk_total,
            chunk_stats_subquery.c.ready_chunks,
            chunk_stats_subquery.c.failed_chunks,
        )
        .outerjoin(
            chunk_stats_subquery,
            chunk_stats_subquery.c.doc_id == UserMemoryDocument.id,
        )
        .filter(UserMemoryDocument.id == int(doc_id))
    )
    if user_id is not None:
        query = query.filter(UserMemoryDocument.user_id == int(user_id))

    row = query.first()
    if row is None:
        return None

    document, chunk_total, ready_chunks, failed_chunks = row
    return {
        "memory_id": int(document.id),
        "user_id": int(document.user_id),
        "doc_kind": str(document.doc_kind),
        "doc_key": str(document.doc_key),
        "title": document.title,
        "content_md": document.content_md,
        "summary_md": document.summary_md,
        "source": str(document.source),
        "scope": str(document.scope),
        "scope_ref": document.scope_ref,
        "status": str(document.status),
        "revision": int(document.revision or 1),
        "source_thread_id": document.source_thread_id,
        "source_message_id": document.source_message_id,
        "chunk_total": int(chunk_total or 0),
        "ready_chunks": int(ready_chunks or 0),
        "failed_chunks": int(failed_chunks or 0),
        "create_time": document.create_time,
        "update_time": document.update_time,
    }


def list_document_chunks(
    db: Session,
    *,
    doc_id: int,
    user_id: int | None = None,
    embedding_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """分页查询文档分块列表。"""

    safe_page = max(1, int(page))
    safe_page_size = max(1, int(page_size))
    offset = (safe_page - 1) * safe_page_size

    query = db.query(UserMemoryChunk).filter(UserMemoryChunk.doc_id == int(doc_id))
    if user_id is not None:
        query = query.filter(UserMemoryChunk.user_id == int(user_id))

    normalized_embedding_status = _normalize_optional_filter(embedding_status)
    if normalized_embedding_status and normalized_embedding_status.lower() != "all":
        query = query.filter(UserMemoryChunk.embedding_status == normalized_embedding_status.lower())

    total = int(query.with_entities(func.count(UserMemoryChunk.id)).scalar() or 0)
    rows = (
        query.order_by(
            UserMemoryChunk.chunk_no.asc(),
            UserMemoryChunk.id.asc(),
        )
        .offset(offset)
        .limit(safe_page_size)
        .all()
    )

    items: list[dict[str, Any]] = []
    for chunk in rows:
        items.append(
            {
                "chunk_id": int(chunk.id),
                "doc_id": int(chunk.doc_id),
                "user_id": int(chunk.user_id),
                "chunk_no": int(chunk.chunk_no),
                "start_line": int(chunk.start_line),
                "end_line": int(chunk.end_line),
                "chunk_text": str(chunk.chunk_text or ""),
                "chunk_hash": str(chunk.chunk_hash or ""),
                "embedding_status": str(chunk.embedding_status or EMBEDDING_STATUS_PENDING),
                "embedding_retry_count": int(chunk.embedding_retry_count or 0),
                "embedding_model": chunk.embedding_model,
                "embedding_error": chunk.embedding_error,
                "embedding_updated_time": chunk.embedding_updated_time,
                "source": str(chunk.source or "memory"),
                "create_time": chunk.create_time,
                "update_time": chunk.update_time,
            }
        )
    return items, total


def archive_document(
    db: Session,
    *,
    doc_id: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    """将记忆文档归档为 archived（幂等）。"""

    query = db.query(UserMemoryDocument).filter(UserMemoryDocument.id == int(doc_id))
    if user_id is not None:
        query = query.filter(UserMemoryDocument.user_id == int(user_id))

    document = query.first()
    if document is None:
        return {
            "found": False,
            "changed": False,
            "status": "missing",
            "update_time": None,
        }

    current_status = str(document.status or "").lower()
    if current_status == ARCHIVED_STATUS:
        return {
            "found": True,
            "changed": False,
            "status": ARCHIVED_STATUS,
            "update_time": document.update_time,
        }

    now = datetime.now()
    document.status = ARCHIVED_STATUS
    document.update_time = now
    db.flush()
    return {
        "found": True,
        "changed": True,
        "status": ARCHIVED_STATUS,
        "update_time": now,
    }


def archive_slot(
    db: Session,
    *,
    doc_id: int,
    user_id: int | None = None,
    event_time: datetime | None = None,
    operation: str = "archive",
) -> dict[str, Any]:
    """按文档 ID 归档槽位记录。"""

    result = archive_document(
        db,
        doc_id=doc_id,
        user_id=user_id,
    )
    if not result.get("found"):
        return result

    document = db.query(UserMemoryDocument).filter(UserMemoryDocument.id == int(doc_id)).first()
    if document is None:
        return result

    changed = bool(result.get("changed"))
    changed_state = False
    if document.operation != str(operation):
        document.operation = str(operation)
        changed_state = True
    if event_time is not None and (
        document.last_event_time is None or event_time >= document.last_event_time
    ):
        document.last_event_time = event_time
        changed_state = True
    if changed_state and not changed:
        document.update_time = datetime.now()
    if changed_state:
        db.flush()

    return {
        **result,
        "slot_key": str(document.slot_key or document.doc_key or ""),
        "revision": int(document.revision or 1),
        "last_event_time": document.last_event_time,
        "operation": str(document.operation or operation),
    }


def delete_document(
    db: Session,
    *,
    doc_id: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    """硬删除记忆文档（幂等）。"""

    query = db.query(UserMemoryDocument).filter(UserMemoryDocument.id == int(doc_id))
    if user_id is not None:
        query = query.filter(UserMemoryDocument.user_id == int(user_id))

    document = query.first()
    if document is None:
        return {
            "found": False,
            "deleted": False,
            "deleted_chunks": 0,
        }

    deleted_chunks = int(
        db.query(UserMemoryChunk)
        .filter(UserMemoryChunk.doc_id == int(document.id))
        .delete(synchronize_session=False)
    )
    db.delete(document)
    db.flush()
    return {
        "found": True,
        "deleted": True,
        "deleted_chunks": deleted_chunks,
    }


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
