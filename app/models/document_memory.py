"""文档化永久记忆模型（中文注释）。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserMemoryDocument(Base):
    """文档化永久记忆主表。"""

    __tablename__ = "t_user_memory_document"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    doc_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="daily",
        comment="文档类型: long_term/daily/session",
    )
    doc_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="文档键")
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="文档标题")
    content_md: Mapped[str] = mapped_column(Text, nullable=False, comment="文档正文")
    summary_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="文档摘要")
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="memory",
        comment="来源: memory/sessions",
    )
    scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="private",
        comment="作用域: private/shared",
    )
    scope_ref: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="作用域引用",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        comment="状态: active/archived",
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="文档版本号",
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="内容哈希")
    source_thread_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="来源线程ID",
    )
    source_message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="来源消息ID",
    )
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_user_memory_document_user_update", "user_id", "update_time"),
        Index("idx_user_memory_document_user_scope", "user_id", "source", "scope", "status"),
        Index(
            "idx_user_memory_document_active_unique",
            "user_id",
            "doc_kind",
            "doc_key",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


class UserMemoryChunk(Base):
    """文档化永久记忆分块检索表。"""

    __tablename__ = "t_user_memory_chunk"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("t_user_memory_document.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联文档ID",
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="用户ID")
    chunk_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="分块序号")
    start_line: Mapped[int] = mapped_column(Integer, nullable=False, comment="起始行号")
    end_line: Mapped[int] = mapped_column(Integer, nullable=False, comment="结束行号")
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False, comment="分块文本")
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="分块哈希")
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(2048),
        nullable=True,
        comment="向量嵌入（可空）",
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="向量模型",
    )
    embedding_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        comment="向量状态: pending/ready/failed",
    )
    embedding_retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="向量重试次数",
    )
    embedding_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="最近一次向量失败摘要",
    )
    embedding_updated_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="向量更新时间",
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="memory",
        comment="来源: memory/sessions",
    )
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_user_memory_chunk_user_doc_no", "user_id", "doc_id", "chunk_no"),
        Index("idx_user_memory_chunk_doc", "doc_id"),
        Index(
            "idx_user_memory_chunk_embedding_status",
            "user_id",
            "embedding_status",
            "update_time",
        ),
        Index("idx_user_memory_chunk_unique_hash", "user_id", "doc_id", "chunk_hash", unique=True),
    )
