"""对话消息模型，对应表 t_chat_message（中文注释）。

用于统一存储对话历史，支持多种内容类型（markdown/mixed/multimodal等）。
"""
from typing import Optional, Any
from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, Text, DateTime, JSON, Column, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatMessage(Base):
    """对话消息模型。
    
    对应数据库表 t_chat_message，用于持久化对话历史。
    支持混合内容块，便于前端统一渲染。
    title 字段用于存储对话标题（通常只在第一条 human 消息中设置）。
    
    注意：数据库字段 metadata 映射到 Python 属性 extra_data（避免与 SQLAlchemy 保留字冲突）。
    """
    __tablename__ = "t_chat_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, comment="用户ID")
    thread_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="对话线程ID")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="ai", comment="消息角色: human/ai")
    content_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="markdown", 
        comment="内容类型: text/markdown/mixed/multimodal"
    )
    content: Mapped[Optional[str]] = mapped_column(Text, comment="内容（纯文本或 JSON 字符串）")
    # 使用 Column 并指定 name 参数映射到数据库的 metadata 列
    extra_data = Column("metadata", JSON, comment="元数据（附件URL等）")
    create_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        default=datetime.now,
        comment="创建时间"
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), comment="对话标题")
    
    # 复合索引定义
    __table_args__ = (
        # 按用户+时间排序查询（获取用户对话列表）
        Index("idx_chat_message_user_time", "user_id", "create_time"),
        # 按线程+时间排序查询（获取线程内消息）
        Index("idx_chat_message_thread_time", "thread_id", "create_time"),
    )
