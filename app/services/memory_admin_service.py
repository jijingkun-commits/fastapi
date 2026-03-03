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
AUDIT_RESULT_COMPLETED = "completed"
AUDIT_RESULT_FAILED = "failed"


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
        db.commit()
        return True
    except Exception:
        db.rollback()
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
    items, total = document_memory_repo.list_documents(
        db,
        user_id=user_id,
        doc_kind=doc_kind,
        status=status,
        source=source,
        keyword=keyword,
        updated_from=updated_from,
        updated_to=updated_to,
        page=safe_page,
        page_size=safe_page_size,
    )
    logger.info(
        "memory-admin query list: user_id=%s status=%s page=%s page_size=%s total=%s",
        user_id,
        status,
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
    logger.info(
        "memory-admin query detail: memory_id=%s user_id=%s found=%s",
        memory_id,
        user_id,
        bool(detail),
    )
    return detail


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
        "items": items,
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
        items.append(
            {
                "doc_id": int(row.get("doc_id") or 0),
                "doc_kind": str(row.get("doc_kind") or ""),
                "doc_key": str(row.get("doc_key") or ""),
                "start_line": int(row.get("start_line") or 1),
                "end_line": int(row.get("end_line") or 1),
                "chunk_text": str(row.get("chunk_text") or ""),
                "text_score": float(row.get("text_score") or 0.0),
                "vector_score": float(row.get("vector_score") or 0.0),
                "score": score,
                "final_score": score,
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
