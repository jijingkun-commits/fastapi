"""文档记忆后台运维 API（中文注释）。"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import (
    DOCUMENT_MEMORY_EMBEDDING_BATCH_SIZE,
    DOCUMENT_MEMORY_EMBEDDING_MAX_RETRY,
    ENABLE_DOCUMENT_MEMORY_ADMIN_API,
    ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER,
)
from app.db.session import SessionLocal, get_db
from app.repositories import document_memory_repo
from app.schemas.memory_admin import (
    DocumentEmbeddingRebuildRequest,
    DocumentEmbeddingRebuildResponse,
    DocumentEmbeddingStatusResponse,
    DocumentRetryFailedRequest,
)
from app.services import document_memory_embedding_service


router = APIRouter(prefix="/memory-admin", tags=["MemoryAdmin"])
logger = logging.getLogger(__name__)
_TRUE_VALUES = {"1", "true", "yes", "on"}


def _is_enabled_env(env_name: str, fallback: bool) -> bool:
    value = os.getenv(env_name)
    if value is None:
        return fallback
    return value.strip().lower() in _TRUE_VALUES


def _is_document_memory_admin_enabled() -> bool:
    try:
        from app.services.config_resolver import ConfigResolver

        resolved = ConfigResolver.get_bool(
            "feature.enable_document_memory_admin_api",
            ENABLE_DOCUMENT_MEMORY_ADMIN_API,
        )
        return _is_enabled_env("ENABLE_DOCUMENT_MEMORY_ADMIN_API", bool(resolved))
    except Exception:
        return _is_enabled_env("ENABLE_DOCUMENT_MEMORY_ADMIN_API", ENABLE_DOCUMENT_MEMORY_ADMIN_API)


def _is_embedding_worker_enabled() -> bool:
    try:
        from app.services.config_resolver import ConfigResolver

        resolved = ConfigResolver.get_bool(
            "feature.enable_document_memory_embedding_worker",
            ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER,
        )
        return _is_enabled_env("ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER", bool(resolved))
    except Exception:
        return _is_enabled_env(
            "ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER",
            ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER,
        )


def _embedding_batch_size() -> int:
    try:
        from app.services.config_resolver import ConfigResolver

        value = ConfigResolver.get_int(
            "memory.document.embedding.batch_size",
            DOCUMENT_MEMORY_EMBEDDING_BATCH_SIZE,
        )
        return max(1, int(value))
    except Exception:
        return max(1, int(DOCUMENT_MEMORY_EMBEDDING_BATCH_SIZE))


def _embedding_max_retry() -> int:
    try:
        from app.services.config_resolver import ConfigResolver

        value = ConfigResolver.get_int(
            "memory.document.embedding.max_retry",
            DOCUMENT_MEMORY_EMBEDDING_MAX_RETRY,
        )
        return max(0, int(value))
    except Exception:
        return max(0, int(DOCUMENT_MEMORY_EMBEDDING_MAX_RETRY))


def _ensure_admin_api_enabled() -> None:
    if not _is_document_memory_admin_enabled():
        raise HTTPException(
            status_code=409,
            detail="ENABLE_DOCUMENT_MEMORY_ADMIN_API 未开启",
        )


def _run_embedding_rebuild_task(
    *,
    user_id: int | None,
    doc_id: int | None,
    status_filter: list[str],
    limit: int,
) -> None:
    with SessionLocal() as db:
        summary = document_memory_embedding_service.process_pending_chunks(
            db,
            user_id=user_id,
            doc_id=doc_id,
            status_filter=status_filter,
            limit=limit,
            max_retry=_embedding_max_retry(),
        )
        logger.info("文档记忆向量重建任务完成: %s", summary)


@router.post(
    "/document/rebuild-embeddings",
    response_model=DocumentEmbeddingRebuildResponse,
)
def rebuild_document_embeddings(
    request: DocumentEmbeddingRebuildRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """触发文档记忆向量重建。"""

    _ensure_admin_api_enabled()

    target_limit = min(int(request.limit), _embedding_batch_size() * 20)
    candidate_total = document_memory_repo.count_embedding_candidates(
        db,
        user_id=request.user_id,
        doc_id=request.doc_id,
        statuses=request.status_filter,
    )
    if candidate_total <= 0:
        return DocumentEmbeddingRebuildResponse(status="idle", total=0)

    if request.run_async:
        if not _is_embedding_worker_enabled():
            raise HTTPException(
                status_code=409,
                detail="ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER 未开启",
            )
        background_tasks.add_task(
            _run_embedding_rebuild_task,
            user_id=request.user_id,
            doc_id=request.doc_id,
            status_filter=request.status_filter,
            limit=min(candidate_total, target_limit),
        )
        return DocumentEmbeddingRebuildResponse(
            status="processing",
            total=candidate_total,
            processed=0,
            ready=0,
            failed=0,
            elapsed_ms=0,
        )

    summary = document_memory_embedding_service.process_pending_chunks(
        db,
        user_id=request.user_id,
        doc_id=request.doc_id,
        status_filter=request.status_filter,
        limit=min(candidate_total, target_limit),
        max_retry=_embedding_max_retry(),
    )
    return DocumentEmbeddingRebuildResponse(
        status="completed",
        total=summary.get("total", 0),
        processed=summary.get("processed", 0),
        ready=summary.get("ready", 0),
        failed=summary.get("failed", 0),
        elapsed_ms=summary.get("elapsed_ms", 0),
    )


@router.get(
    "/document/embedding-status",
    response_model=DocumentEmbeddingStatusResponse,
)
def get_document_embedding_status(
    user_id: int | None = Query(default=None, ge=1),
    doc_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """查询文档记忆向量状态统计。"""

    _ensure_admin_api_enabled()
    status = document_memory_embedding_service.get_embedding_status(
        db,
        user_id=user_id,
        doc_id=doc_id,
    )
    return DocumentEmbeddingStatusResponse(**status)


@router.post(
    "/document/retry-failed",
    response_model=DocumentEmbeddingRebuildResponse,
)
def retry_failed_document_embeddings(
    request: DocumentRetryFailedRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """重试失败的文档向量。"""

    _ensure_admin_api_enabled()
    reset = document_memory_embedding_service.retry_failed_chunks(
        db,
        user_id=request.user_id,
        doc_id=request.doc_id,
        limit=request.limit,
    )
    if reset <= 0:
        return DocumentEmbeddingRebuildResponse(status="idle", reset=0, total=0)

    if request.run_async:
        if not _is_embedding_worker_enabled():
            raise HTTPException(
                status_code=409,
                detail="ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER 未开启",
            )
        background_tasks.add_task(
            _run_embedding_rebuild_task,
            user_id=request.user_id,
            doc_id=request.doc_id,
            status_filter=[document_memory_repo.EMBEDDING_STATUS_PENDING],
            limit=request.limit,
        )
        return DocumentEmbeddingRebuildResponse(
            status="processing",
            reset=reset,
            total=reset,
        )

    summary = document_memory_embedding_service.process_pending_chunks(
        db,
        user_id=request.user_id,
        doc_id=request.doc_id,
        status_filter=[document_memory_repo.EMBEDDING_STATUS_PENDING],
        limit=request.limit,
        max_retry=_embedding_max_retry(),
    )
    return DocumentEmbeddingRebuildResponse(
        status="completed",
        total=summary.get("total", 0),
        processed=summary.get("processed", 0),
        ready=summary.get("ready", 0),
        failed=summary.get("failed", 0),
        elapsed_ms=summary.get("elapsed_ms", 0),
        reset=reset,
    )
