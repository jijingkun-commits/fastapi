"""文档记忆后台运维 API（中文注释）。"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
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
    MemoryChunksResponse,
    MemoryDetailResponse,
    MemoryListResponse,
    MemoryOverviewResponse,
)
from app.services import document_memory_embedding_service, memory_admin_service


router = APIRouter(prefix="/memory-admin", tags=["MemoryAdmin"])
logger = logging.getLogger(__name__)
_TRUE_VALUES = {"1", "true", "yes", "on"}


class MemorySearchDebugRequest(BaseModel):
    """记忆召回调试请求。"""

    user_id: int = Field(..., ge=1, description="目标用户 ID")
    query_text: str = Field(..., min_length=1, max_length=2000, description="调试查询词")
    max_results: int | None = Field(default=None, ge=1, le=200, description="最大返回条数")
    limit: int | None = Field(default=None, ge=1, le=200, description="兼容字段，等价 max_results")
    min_score: float = Field(default=0.0, ge=0.0, description="最低命中分")
    vector_weight: float = Field(default=0.7, ge=0.0, description="向量权重")
    text_weight: float = Field(default=0.3, ge=0.0, description="文本权重")


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


@router.get(
    "/memories",
    response_model=MemoryListResponse,
)
def list_memories(
    user_id: int | None = Query(default=None, ge=1),
    doc_kind: str | None = Query(default=None, max_length=32),
    status: str = Query(default=document_memory_repo.ACTIVE_STATUS, max_length=16),
    source: str | None = Query(default=None, max_length=32),
    keyword: str | None = Query(default=None, max_length=200),
    updated_from: datetime | None = Query(default=None),
    updated_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """分页查询用户个性化永久记忆列表。"""

    _ensure_admin_api_enabled()
    if updated_from and updated_to and updated_from > updated_to:
        raise HTTPException(status_code=422, detail="updated_from 不能晚于 updated_to")

    payload = memory_admin_service.list_memories(
        db,
        user_id=user_id,
        doc_kind=doc_kind,
        status=status,
        source=source,
        keyword=keyword,
        updated_from=updated_from,
        updated_to=updated_to,
        page=page,
        page_size=page_size,
    )
    return MemoryListResponse(**payload)


@router.get(
    "/memories/{memory_id}",
    response_model=MemoryDetailResponse,
)
def get_memory_detail(
    memory_id: int = Path(..., ge=1),
    user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """查询单条用户个性化永久记忆详情。"""

    _ensure_admin_api_enabled()
    detail = memory_admin_service.get_memory_detail(
        db,
        memory_id=memory_id,
        user_id=user_id,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return MemoryDetailResponse(**detail)


@router.get(
    "/memories/{memory_id}/chunks",
    response_model=MemoryChunksResponse,
)
def get_memory_chunks(
    memory_id: int = Path(..., ge=1),
    user_id: int | None = Query(default=None, ge=1),
    embedding_status: str | None = Query(default=None, max_length=16),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """查询单条记忆分块及向量状态。"""

    _ensure_admin_api_enabled()
    payload = memory_admin_service.get_memory_chunks(
        db,
        memory_id=memory_id,
        user_id=user_id,
        embedding_status=embedding_status,
        page=page,
        page_size=page_size,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return MemoryChunksResponse(**payload)


@router.post("/memories/search-debug")
def search_memory_debug(
    request: MemorySearchDebugRequest,
    db: Session = Depends(get_db),
):
    """召回调试：返回分数与引用。"""

    _ensure_admin_api_enabled()
    max_results = request.max_results or request.limit or 10
    return memory_admin_service.run_memory_search_debug(
        db,
        user_id=request.user_id,
        query_text=request.query_text,
        max_results=max_results,
        min_score=request.min_score,
        vector_weight=request.vector_weight,
        text_weight=request.text_weight,
    )


@router.post("/memories/{memory_id}/archive")
def archive_memory(
    memory_id: int = Path(..., ge=1),
    user_id: int | None = Query(default=None, ge=1),
    operator_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """归档记忆（active -> archived）。"""

    _ensure_admin_api_enabled()
    return memory_admin_service.archive_memory(
        db,
        memory_id=memory_id,
        user_id=user_id,
        operator_id=operator_id,
    )


@router.delete("/memories/{memory_id}")
def delete_memory(
    memory_id: int = Path(..., ge=1),
    user_id: int | None = Query(default=None, ge=1),
    operator_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """删除记忆（物理删除，幂等）。"""

    _ensure_admin_api_enabled()
    return memory_admin_service.delete_memory(
        db,
        memory_id=memory_id,
        user_id=user_id,
        operator_id=operator_id,
    )


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
    response_model_exclude_none=True,
)
def get_document_embedding_status(
    user_id: int | None = Query(default=None, ge=1),
    doc_id: int | None = Query(default=None, ge=1),
    dimension: str | None = Query(default=None, pattern="^(user|doc)$"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """查询文档记忆向量状态统计。"""

    _ensure_admin_api_enabled()
    if dimension:
        status = document_memory_repo.get_embedding_status_counts(
            db,
            user_id=user_id,
            doc_id=doc_id,
            dimension=dimension,
            limit=limit,
            offset=offset,
        )
    else:
        status = document_memory_embedding_service.get_embedding_status(
            db,
            user_id=user_id,
            doc_id=doc_id,
        )
    return DocumentEmbeddingStatusResponse(**status)


@router.get(
    "/memory-overview",
    response_model=MemoryOverviewResponse,
)
def get_memory_overview(
    top_n: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """查询文档记忆总览统计。"""

    _ensure_admin_api_enabled()
    overview = document_memory_repo.get_memory_overview_stats(
        db,
        top_n=top_n,
    )
    return MemoryOverviewResponse(**overview)


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
