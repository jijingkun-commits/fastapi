"""记忆管理查询服务（中文注释）。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.repositories import document_memory_repo, memory_admin_audit_repo
from app.services import document_memory_service


logger = logging.getLogger(__name__)

_DEFAULT_MAX_PAGE_SIZE = 200
_DEFAULT_LIST_PAGE_SIZE = 20
_DEFAULT_CHUNK_PAGE_SIZE = 50
_DEFAULT_DEBUG_LIMIT = 10

AUDIT_ACTION_ARCHIVE_MEMORY = "archive_memory"
AUDIT_ACTION_DELETE_MEMORY = "delete_memory"
AUDIT_ACTION_SEARCH_DEBUG = "search_memory_debug"
AUDIT_ACTION_REBUILD_EMBEDDINGS = "rebuild_memory_embeddings"
AUDIT_ACTION_RETRY_FAILED_EMBEDDINGS = "retry_failed_memory_embeddings"
AUDIT_RESULT_ACCEPTED = "accepted"
AUDIT_RESULT_COMPLETED = "completed"
AUDIT_RESULT_FAILED = "failed"

_LEVEL_PERMANENT = "permanent"
_LEVEL_DAILY = "daily"
_LEVEL_NONE = "none"

_DOC_KIND_LEVEL_MAPPING: dict[str, str] = {
    "long_term": _LEVEL_PERMANENT,
    "permanent": _LEVEL_PERMANENT,
    "daily": _LEVEL_DAILY,
    "session": _LEVEL_DAILY,
}

_LEVEL_DOC_KIND_MAPPING: dict[str, str] = {
    _LEVEL_PERMANENT: "long_term",
    _LEVEL_DAILY: "daily",
}

_SLOT_PREFIX_CATEGORY_MAPPING: tuple[tuple[str, str], ...] = (
    ("assistant.persona.", "ai_persona"),
    ("user.preference.", "user_preference"),
    ("knowledge.important.", "important_knowledge"),
    ("user.profile.", "profile_fact"),
    ("interaction.policy.", "interaction_policy"),
)


def _resolve_max_page_size() -> int:
    """读取管理接口最大分页大小配置。"""

    try:
        from app.services.config_resolver import ConfigResolver

        value = ConfigResolver.get_int(
            "memory.document.admin.max_page_size",
            _DEFAULT_MAX_PAGE_SIZE,
        )
        return max(1, min(int(value), 1000))
    except Exception:
        return _DEFAULT_MAX_PAGE_SIZE


def _normalize_page(page: int, page_size: int, *, default_page_size: int) -> tuple[int, int]:
    safe_page = max(1, int(page))
    max_page_size = _resolve_max_page_size()
    requested_page_size = int(page_size or default_page_size)
    safe_page_size = min(max(1, requested_page_size), max_page_size)
    return safe_page, safe_page_size


def _normalize_debug_limit(limit: int) -> int:
    max_page_size = _resolve_max_page_size()
    requested = int(limit or _DEFAULT_DEBUG_LIMIT)
    return min(max(1, requested), max_page_size)


def _resolve_operator_user_id(operator_user_id: int | None, target_user_id: int | None) -> int:
    for candidate in (operator_user_id, target_user_id):
        if candidate is None:
            continue
        try:
            resolved = int(candidate)
        except (TypeError, ValueError):
            continue
        if resolved > 0:
            return resolved
    return 0


def _normalize_error_message(error_message: str | None) -> str | None:
    if error_message is None:
        return None
    cleaned = str(error_message).strip()
    if not cleaned:
        return None
    return cleaned[:2000]


def _normalize_semantic_filter(value: str | None) -> str | None:
    cleaned = str(value or "").strip().lower()
    return cleaned or None


def _resolve_memory_level(doc_kind: str | None, level: str | None = None) -> str:
    normalized_level = _normalize_semantic_filter(level)
    if normalized_level in {_LEVEL_PERMANENT, _LEVEL_DAILY, _LEVEL_NONE}:
        return normalized_level
    normalized_doc_kind = _normalize_semantic_filter(doc_kind)
    if not normalized_doc_kind:
        return _LEVEL_NONE
    return _DOC_KIND_LEVEL_MAPPING.get(normalized_doc_kind, normalized_doc_kind)


def _resolve_slot_key(*, slot_key: str | None = None, doc_key: str | None = None) -> str:
    for candidate in (slot_key, doc_key):
        cleaned = str(candidate or "").strip().lower()
        if cleaned:
            return cleaned
    return ""


def _resolve_memory_category(*, category: str | None = None, slot_key: str | None = None) -> str:
    normalized_category = _normalize_semantic_filter(category)
    if normalized_category:
        return normalized_category
    normalized_slot_key = _normalize_semantic_filter(slot_key)
    if not normalized_slot_key:
        return ""
    for prefix, mapped in _SLOT_PREFIX_CATEGORY_MAPPING:
        if normalized_slot_key.startswith(prefix):
            return mapped
    return ""


def _match_memory_filters(
    item: dict[str, Any],
    *,
    slot_key: str | None,
    category: str | None,
    level: str | None,
) -> bool:
    expected_slot_key = _normalize_semantic_filter(slot_key)
    expected_category = _normalize_semantic_filter(category)
    expected_level = _normalize_semantic_filter(level)

    resolved_slot_key = _resolve_slot_key(
        slot_key=item.get("slot_key"),
        doc_key=item.get("doc_key"),
    )
    resolved_category = _resolve_memory_category(
        category=item.get("category"),
        slot_key=resolved_slot_key,
    )
    resolved_level = _resolve_memory_level(
        doc_kind=item.get("doc_kind"),
        level=item.get("level"),
    )

    if expected_slot_key and expected_slot_key != resolved_slot_key:
        return False
    if expected_category and expected_category != resolved_category:
        return False
    if expected_level and expected_level != resolved_level:
        return False
    return True


def _enrich_memory_semantics(item: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(item)
    resolved_slot_key = _resolve_slot_key(
        slot_key=enriched.get("slot_key"),
        doc_key=enriched.get("doc_key"),
    )
    if resolved_slot_key and not enriched.get("slot_key"):
        enriched["slot_key"] = resolved_slot_key

    resolved_level = _resolve_memory_level(
        doc_kind=enriched.get("doc_kind"),
        level=enriched.get("level"),
    )
    if resolved_level and not enriched.get("level"):
        enriched["level"] = resolved_level

    resolved_category = _resolve_memory_category(
        category=enriched.get("category"),
        slot_key=resolved_slot_key,
    )
    if resolved_category and not enriched.get("category"):
        enriched["category"] = resolved_category

    memory_id = enriched.get("memory_id")
    if memory_id in (None, 0, "") and enriched.get("doc_id") not in (None, 0, ""):
        enriched["memory_id"] = int(enriched.get("doc_id"))
    return enriched


def _build_source_span(start_line: int, end_line: int) -> str:
    safe_start = max(1, int(start_line or 1))
    safe_end = max(safe_start, int(end_line or safe_start))
    return f"L{safe_start}-L{safe_end}"


def record_admin_audit(
    db: Session,
    *,
    operator_user_id: int | None,
    target_user_id: int | None,
    memory_id: int | None,
    action: str,
    action_payload: dict[str, Any] | None,
    result_status: str,
    error_message: str | None = None,
) -> bool:
    """写入记忆管理审计，不抛出异常。"""

    try:
        memory_admin_audit_repo.create_audit_log(
            db,
            operator_user_id=_resolve_operator_user_id(operator_user_id, target_user_id),
            target_user_id=target_user_id,
            memory_id=memory_id,
            action=action,
            action_payload=action_payload,
            result_status=result_status,
            error_message=_normalize_error_message(error_message),
        )
        commit = getattr(db, "commit", None)
        if callable(commit):
            commit()
        return True
    except Exception:
        rollback = getattr(db, "rollback", None)
        if callable(rollback):
            try:
                rollback()
            except Exception:
                logger.warning(
                    "memory-admin audit rollback failed: action=%s operator=%s target=%s memory_id=%s",
                    action,
                    operator_user_id,
                    target_user_id,
                    memory_id,
                    exc_info=True,
                )
        logger.warning(
            "memory-admin audit write failed: action=%s operator=%s target=%s memory_id=%s status=%s",
            action,
            operator_user_id,
            target_user_id,
            memory_id,
            result_status,
            exc_info=True,
        )
        return False


def list_memories(
    db: Session,
    *,
    user_id: int | None = None,
    doc_kind: str | None = None,
    slot_key: str | None = None,
    category: str | None = None,
    level: str | None = None,
    status: str | None = document_memory_repo.ACTIVE_STATUS,
    source: str | None = None,
    keyword: str | None = None,
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    page: int = 1,
    page_size: int = _DEFAULT_LIST_PAGE_SIZE,
) -> dict[str, Any]:
    """分页查询记忆列表。"""

    safe_page, safe_page_size = _normalize_page(page, page_size, default_page_size=_DEFAULT_LIST_PAGE_SIZE)

    normalized_slot_key = _normalize_semantic_filter(slot_key)
    normalized_category = _normalize_semantic_filter(category)
    normalized_level = _normalize_semantic_filter(level)
    semantic_filter_enabled = any((normalized_slot_key, normalized_category, normalized_level))

    effective_doc_kind = doc_kind
    if not effective_doc_kind and normalized_level:
        effective_doc_kind = _LEVEL_DOC_KIND_MAPPING.get(normalized_level)

    effective_keyword = keyword
    if not effective_keyword and normalized_slot_key:
        effective_keyword = normalized_slot_key

    fetch_page = 1 if semantic_filter_enabled else safe_page
    fetch_page_size = _resolve_max_page_size() if semantic_filter_enabled else safe_page_size

    raw_items, total = document_memory_repo.list_documents(
        db,
        user_id=user_id,
        doc_kind=effective_doc_kind,
        status=status,
        source=source,
        keyword=effective_keyword,
        updated_from=updated_from,
        updated_to=updated_to,
        page=fetch_page,
        page_size=fetch_page_size,
    )

    if semantic_filter_enabled:
        all_items = list(raw_items)
        collected = len(all_items)
        while collected < int(total):
            fetch_page += 1
            page_items, _ = document_memory_repo.list_documents(
                db,
                user_id=user_id,
                doc_kind=effective_doc_kind,
                status=status,
                source=source,
                keyword=effective_keyword,
                updated_from=updated_from,
                updated_to=updated_to,
                page=fetch_page,
                page_size=fetch_page_size,
            )
            if not page_items:
                break
            all_items.extend(page_items)
            collected += len(page_items)

        filtered_items = [
            _enrich_memory_semantics(item)
            for item in all_items
            if _match_memory_filters(
                item,
                slot_key=normalized_slot_key,
                category=normalized_category,
                level=normalized_level,
            )
        ]
        total = len(filtered_items)
        offset = (safe_page - 1) * safe_page_size
        items = filtered_items[offset : offset + safe_page_size]
    else:
        items = [_enrich_memory_semantics(item) for item in raw_items]

    logger.info(
        "memory-admin query list: user_id=%s status=%s slot_key=%s category=%s level=%s page=%s page_size=%s total=%s",
        user_id,
        status,
        normalized_slot_key,
        normalized_category,
        normalized_level,
        safe_page,
        safe_page_size,
        total,
    )
    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def get_memory_detail(
    db: Session,
    *,
    memory_id: int,
    user_id: int | None = None,
) -> dict[str, Any] | None:
    """查询单条记忆详情。"""

    detail = document_memory_repo.get_document_detail(
        db,
        doc_id=memory_id,
        user_id=user_id,
    )
    payload = _enrich_memory_semantics(detail) if detail else None
    logger.info(
        "memory-admin query detail: memory_id=%s user_id=%s found=%s",
        memory_id,
        user_id,
        bool(payload),
    )
    return payload


def get_memory_chunks(
    db: Session,
    *,
    memory_id: int,
    user_id: int | None = None,
    embedding_status: str | None = None,
    page: int = 1,
    page_size: int = _DEFAULT_CHUNK_PAGE_SIZE,
) -> dict[str, Any] | None:
    """分页查询单条记忆分块状态。"""

    detail = document_memory_repo.get_document_detail(
        db,
        doc_id=memory_id,
        user_id=user_id,
    )
    if detail is None:
        logger.info(
            "memory-admin query chunks: memory_id=%s user_id=%s found=false",
            memory_id,
            user_id,
        )
        return None

    safe_page, safe_page_size = _normalize_page(page, page_size, default_page_size=_DEFAULT_CHUNK_PAGE_SIZE)
    items, total = document_memory_repo.list_document_chunks(
        db,
        doc_id=memory_id,
        user_id=user_id,
        embedding_status=embedding_status,
        page=safe_page,
        page_size=safe_page_size,
    )
    logger.info(
        "memory-admin query chunks: memory_id=%s user_id=%s status=%s page=%s page_size=%s total=%s",
        memory_id,
        user_id,
        embedding_status,
        safe_page,
        safe_page_size,
        total,
    )
    return {
        "memory_id": int(detail["memory_id"]),
        "user_id": int(detail["user_id"]),
        "status": str(detail["status"]),
        "items": [_enrich_memory_semantics(item) for item in items],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def run_memory_search_debug(
    db: Session,
    *,
    user_id: int,
    query_text: str,
    max_results: int = _DEFAULT_DEBUG_LIMIT,
    min_score: float = 0.0,
    vector_weight: float = 0.7,
    text_weight: float = 0.3,
) -> dict[str, Any]:
    """执行记忆召回调试，返回分数与引用信息。"""

    safe_limit = _normalize_debug_limit(max_results)
    cleaned_query = str(query_text or "").strip()
    if not cleaned_query:
        return {
            "user_id": int(user_id),
            "query_text": cleaned_query,
            "items": [],
            "total": 0,
        }

    raw_items = document_memory_service.memory_search(
        db,
        user_id=int(user_id),
        query_text=cleaned_query,
        max_results=safe_limit,
        min_score=float(min_score),
        vector_weight=float(vector_weight),
        text_weight=float(text_weight),
    )

    items: list[dict[str, Any]] = []
    for row in raw_items:
        score = float(row.get("score") or 0.0)
        start_line = int(row.get("start_line") or 1)
        end_line = int(row.get("end_line") or 1)
        resolved_slot_key = _resolve_slot_key(
            slot_key=row.get("slot_key"),
            doc_key=row.get("doc_key"),
        )
        resolved_level = _resolve_memory_level(
            doc_kind=row.get("doc_kind"),
            level=row.get("level"),
        )
        resolved_category = _resolve_memory_category(
            category=row.get("category"),
            slot_key=resolved_slot_key,
        )
        items.append(
            {
                "doc_id": int(row.get("doc_id") or 0),
                "memory_id": int(row.get("doc_id") or 0),
                "doc_kind": str(row.get("doc_kind") or ""),
                "doc_key": str(row.get("doc_key") or ""),
                "slot_key": resolved_slot_key,
                "category": resolved_category,
                "level": resolved_level,
                "start_line": start_line,
                "end_line": end_line,
                "source_span": _build_source_span(start_line, end_line),
                "chunk_text": str(row.get("chunk_text") or ""),
                "text_score": float(row.get("text_score") or 0.0),
                "vector_score": float(row.get("vector_score") or 0.0),
                "score": score,
                "final_score": score,
                "final_status": "matched",
                "citation": str(row.get("citation") or ""),
            }
        )

    logger.info(
        "memory-admin search-debug: user_id=%s query=%s limit=%s total=%s",
        user_id,
        cleaned_query[:80],
        safe_limit,
        len(items),
    )
    return {
        "user_id": int(user_id),
        "query_text": cleaned_query,
        "items": items,
        "total": len(items),
    }


def archive_memory(
    db: Session,
    *,
    memory_id: int,
    user_id: int | None = None,
    operator_id: int | None = None,
) -> dict[str, Any]:
    """归档记忆文档（幂等）。"""

    audit_payload: dict[str, Any] = {
        "memory_id": int(memory_id),
        "user_id": user_id,
        "operator_id": operator_id,
    }
    try:
        result = document_memory_repo.archive_document(
            db,
            doc_id=memory_id,
            user_id=user_id,
        )
        changed = bool(result.get("changed"))
        if changed:
            db.commit()

        payload = {
            "memory_id": int(memory_id),
            "user_id": user_id,
            "operator_id": operator_id,
            "status": str(result.get("status") or "missing"),
            "found": bool(result.get("found")),
            "changed": changed,
        }
        audit_payload.update(
            {
                "status": payload["status"],
                "found": payload["found"],
                "changed": payload["changed"],
            }
        )
        record_admin_audit(
            db,
            operator_user_id=operator_id,
            target_user_id=user_id,
            memory_id=memory_id,
            action=AUDIT_ACTION_ARCHIVE_MEMORY,
            action_payload=audit_payload,
            result_status=AUDIT_RESULT_COMPLETED,
        )
        logger.info(
            "memory-admin archive: memory_id=%s user_id=%s operator_id=%s found=%s changed=%s",
            memory_id,
            user_id,
            operator_id,
            payload["found"],
            changed,
        )
        return payload
    except Exception as exc:
        db.rollback()
        record_admin_audit(
            db,
            operator_user_id=operator_id,
            target_user_id=user_id,
            memory_id=memory_id,
            action=AUDIT_ACTION_ARCHIVE_MEMORY,
            action_payload=audit_payload,
            result_status=AUDIT_RESULT_FAILED,
            error_message=str(exc),
        )
        logger.exception(
            "memory-admin archive failed: memory_id=%s user_id=%s operator_id=%s",
            memory_id,
            user_id,
            operator_id,
        )
        raise


def delete_memory(
    db: Session,
    *,
    memory_id: int,
    user_id: int | None = None,
    operator_id: int | None = None,
) -> dict[str, Any]:
    """删除记忆文档（幂等硬删）。"""

    audit_payload: dict[str, Any] = {
        "memory_id": int(memory_id),
        "user_id": user_id,
        "operator_id": operator_id,
    }
    try:
        result = document_memory_repo.delete_document(
            db,
            doc_id=memory_id,
            user_id=user_id,
        )
        deleted = bool(result.get("deleted"))
        if deleted:
            db.commit()

        payload = {
            "memory_id": int(memory_id),
            "user_id": user_id,
            "operator_id": operator_id,
            "status": "deleted" if deleted else "missing",
            "found": bool(result.get("found")),
            "deleted": deleted,
            "deleted_chunks": int(result.get("deleted_chunks") or 0),
        }
        audit_payload.update(
            {
                "status": payload["status"],
                "found": payload["found"],
                "deleted": payload["deleted"],
                "deleted_chunks": payload["deleted_chunks"],
            }
        )
        record_admin_audit(
            db,
            operator_user_id=operator_id,
            target_user_id=user_id,
            memory_id=memory_id,
            action=AUDIT_ACTION_DELETE_MEMORY,
            action_payload=audit_payload,
            result_status=AUDIT_RESULT_COMPLETED,
        )
        logger.info(
            "memory-admin delete: memory_id=%s user_id=%s operator_id=%s found=%s deleted=%s deleted_chunks=%s",
            memory_id,
            user_id,
            operator_id,
            payload["found"],
            deleted,
            payload["deleted_chunks"],
        )
        return payload
    except Exception as exc:
        db.rollback()
        record_admin_audit(
            db,
            operator_user_id=operator_id,
            target_user_id=user_id,
            memory_id=memory_id,
            action=AUDIT_ACTION_DELETE_MEMORY,
            action_payload=audit_payload,
            result_status=AUDIT_RESULT_FAILED,
            error_message=str(exc),
        )
        logger.exception(
            "memory-admin delete failed: memory_id=%s user_id=%s operator_id=%s",
            memory_id,
            user_id,
            operator_id,
        )
        raise
