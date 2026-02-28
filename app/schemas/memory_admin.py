"""文档记忆后台管理 Schema（中文注释）。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DocumentEmbeddingRebuildRequest(BaseModel):
    """触发文档记忆向量重建请求。"""

    user_id: Optional[int] = Field(default=None, ge=1, description="用户 ID（可选）")
    doc_id: Optional[int] = Field(default=None, ge=1, description="文档 ID（可选）")
    status_filter: list[str] = Field(
        default_factory=lambda: ["pending", "failed"],
        description="待处理状态过滤",
    )
    limit: int = Field(default=200, ge=1, le=5000, description="处理上限")
    run_async: bool = Field(default=True, description="是否后台异步执行")


class DocumentRetryFailedRequest(BaseModel):
    """重试失败分块请求。"""

    user_id: Optional[int] = Field(default=None, ge=1, description="用户 ID（可选）")
    doc_id: Optional[int] = Field(default=None, ge=1, description="文档 ID（可选）")
    limit: int = Field(default=200, ge=1, le=5000, description="重置上限")
    run_async: bool = Field(default=True, description="是否重置后立即异步处理")


class DocumentEmbeddingStatusResponse(BaseModel):
    """文档向量状态统计响应。"""

    total: int = Field(default=0, description="总分块数")
    pending: int = Field(default=0, description="待向量化分块数")
    ready: int = Field(default=0, description="已向量化分块数")
    failed: int = Field(default=0, description="失败分块数")


class DocumentEmbeddingRebuildResponse(BaseModel):
    """文档向量重建响应。"""

    status: str = Field(description="任务状态")
    total: int = Field(default=0, description="命中分块总数")
    processed: int = Field(default=0, description="本次处理总数")
    ready: int = Field(default=0, description="成功写回数量")
    failed: int = Field(default=0, description="失败数量")
    reset: int = Field(default=0, description="失败重置数量")
    elapsed_ms: int = Field(default=0, description="处理耗时（毫秒）")
