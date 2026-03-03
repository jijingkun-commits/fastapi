"""文档记忆后台管理 Schema（中文注释）。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class MemoryListItem(BaseModel):
    """记忆列表项。"""

    memory_id: int = Field(description="记忆 ID")
    user_id: int = Field(description="用户 ID")
    doc_kind: str = Field(description="记忆文档类型")
    doc_key: str = Field(description="记忆文档键")
    title: Optional[str] = Field(default=None, description="记忆标题")
    summary_md: Optional[str] = Field(default=None, description="记忆摘要")
    source: str = Field(description="来源类型")
    scope: str = Field(description="作用域")
    scope_ref: Optional[str] = Field(default=None, description="作用域引用")
    status: str = Field(description="记忆状态")
    revision: int = Field(description="修订版本")
    chunk_total: int = Field(default=0, description="分块总数")
    ready_chunks: int = Field(default=0, description="向量就绪分块数")
    failed_chunks: int = Field(default=0, description="向量失败分块数")
    create_time: Optional[datetime] = Field(default=None, description="创建时间")
    update_time: Optional[datetime] = Field(default=None, description="更新时间")


class MemoryListResponse(BaseModel):
    """记忆列表响应。"""

    items: list[MemoryListItem] = Field(default_factory=list, description="列表数据")
    total: int = Field(default=0, description="总条数")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=20, description="分页大小")


class MemoryDetailResponse(BaseModel):
    """记忆详情响应。"""

    memory_id: int = Field(description="记忆 ID")
    user_id: int = Field(description="用户 ID")
    doc_kind: str = Field(description="记忆文档类型")
    doc_key: str = Field(description="记忆文档键")
    title: Optional[str] = Field(default=None, description="记忆标题")
    content_md: str = Field(description="记忆正文")
    summary_md: Optional[str] = Field(default=None, description="记忆摘要")
    source: str = Field(description="来源类型")
    scope: str = Field(description="作用域")
    scope_ref: Optional[str] = Field(default=None, description="作用域引用")
    status: str = Field(description="记忆状态")
    revision: int = Field(description="修订版本")
    source_thread_id: Optional[str] = Field(default=None, description="来源线程 ID")
    source_message_id: Optional[int] = Field(default=None, description="来源消息 ID")
    chunk_total: int = Field(default=0, description="分块总数")
    ready_chunks: int = Field(default=0, description="向量就绪分块数")
    failed_chunks: int = Field(default=0, description="向量失败分块数")
    create_time: Optional[datetime] = Field(default=None, description="创建时间")
    update_time: Optional[datetime] = Field(default=None, description="更新时间")


class MemoryChunkItem(BaseModel):
    """记忆分块项。"""

    chunk_id: int = Field(description="分块 ID")
    doc_id: int = Field(description="所属文档 ID")
    user_id: int = Field(description="用户 ID")
    chunk_no: int = Field(description="分块序号")
    start_line: int = Field(description="起始行")
    end_line: int = Field(description="结束行")
    chunk_text: str = Field(description="分块文本")
    chunk_hash: str = Field(description="分块哈希")
    embedding_status: str = Field(description="向量状态")
    embedding_retry_count: int = Field(default=0, description="重试次数")
    embedding_model: Optional[str] = Field(default=None, description="向量模型")
    embedding_error: Optional[str] = Field(default=None, description="最近失败摘要")
    embedding_updated_time: Optional[datetime] = Field(default=None, description="向量更新时间")
    source: str = Field(description="来源")
    create_time: Optional[datetime] = Field(default=None, description="创建时间")
    update_time: Optional[datetime] = Field(default=None, description="更新时间")


class MemoryChunksResponse(BaseModel):
    """记忆分块查询响应。"""

    memory_id: int = Field(description="记忆 ID")
    user_id: int = Field(description="用户 ID")
    status: str = Field(description="记忆状态")
    items: list[MemoryChunkItem] = Field(default_factory=list, description="分块列表")
    total: int = Field(default=0, description="总条数")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=50, description="分页大小")


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


class EmbeddingStatusSummary(BaseModel):
    """向量状态统计摘要。"""

    total: int = Field(default=0, description="总分块数")
    pending: int = Field(default=0, description="待向量化分块数")
    ready: int = Field(default=0, description="已向量化分块数")
    failed: int = Field(default=0, description="失败分块数")


class EmbeddingStatusGroupItem(EmbeddingStatusSummary):
    """按维度聚合后的分组统计。"""

    user_id: Optional[int] = Field(default=None, description="用户 ID（user/doc 维度）")
    doc_id: Optional[int] = Field(default=None, description="文档 ID（doc 维度）")
    doc_kind: Optional[str] = Field(default=None, description="文档类型（doc 维度）")
    doc_key: Optional[str] = Field(default=None, description="文档键（doc 维度）")
    title: Optional[str] = Field(default=None, description="文档标题（doc 维度）")
    document_total: Optional[int] = Field(default=None, description="文档数量（user 维度）")


class DocumentEmbeddingStatusResponse(EmbeddingStatusSummary):
    """文档向量状态统计响应。"""

    dimension: Optional[Literal["user", "doc"]] = Field(default=None, description="聚合维度")
    limit: Optional[int] = Field(default=None, description="分页大小")
    offset: Optional[int] = Field(default=None, description="分页偏移")
    group_total: Optional[int] = Field(default=None, description="分组总数")
    groups: Optional[list[EmbeddingStatusGroupItem]] = Field(default=None, description="聚合分组")


class DocumentEmbeddingRebuildResponse(BaseModel):
    """文档向量重建响应。"""

    status: str = Field(description="任务状态")
    total: int = Field(default=0, description="命中分块总数")
    processed: int = Field(default=0, description="本次处理总数")
    ready: int = Field(default=0, description="成功写回数量")
    failed: int = Field(default=0, description="失败数量")
    reset: int = Field(default=0, description="失败重置数量")
    elapsed_ms: int = Field(default=0, description="处理耗时（毫秒）")


class MemoryOverviewTotals(BaseModel):
    """记忆总览规模统计。"""

    users: int = Field(default=0, description="活跃用户数")
    documents: int = Field(default=0, description="活跃文档数")
    chunks: int = Field(default=0, description="分块总数")


class MemoryOverviewResponse(BaseModel):
    """记忆总览统计响应。"""

    totals: MemoryOverviewTotals = Field(default_factory=MemoryOverviewTotals, description="规模统计")
    embedding_status: EmbeddingStatusSummary = Field(
        default_factory=EmbeddingStatusSummary,
        description="向量状态汇总",
    )
    top_users: list[EmbeddingStatusGroupItem] = Field(
        default_factory=list,
        description="按用户聚合 Top 列表",
    )
    top_documents: list[EmbeddingStatusGroupItem] = Field(
        default_factory=list,
        description="按文档聚合 Top 列表",
    )
