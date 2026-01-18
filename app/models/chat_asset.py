"""对话资产模型，对应表 t_chat_assets（中文注释）。

用于存储 MinIO 中资产的元数据，支持动态 URL 替换方案。
目录结构: chat-assets/{username}/{chat_id}/{asset_type}/{uuid}.ext
"""
from typing import Optional
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Integer, String, Text, DateTime, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class AssetType(str, PyEnum):
    """资产类型枚举。"""
    CHART = "chart"
    IMAGE = "image"
    EXPORT = "export"
    ATTACHMENT = "attachment"


class ChatAsset(Base):
    """对话资产模型。
    
    对应数据库表 t_chat_assets，用于存储 MinIO 资源的元数据。
    通过 object_key 可生成预签名 URL 供前端访问。
    """
    __tablename__ = "t_chat_assets"
    
    # 主键
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # 关联字段
    qa_record_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="关联问答记录ID"
    )
    chat_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="对话ID（冗余，方便查询）"
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, index=True, comment="用户ID（冗余，方便查询）"
    )
    
    # 资产信息
    asset_type: Mapped[str] = mapped_column(
        Enum(
            AssetType,
            name="asset_type",  # PostgreSQL 枚举名称
            create_type=False,   # 不自动创建枚举（已存在）
            values_callable=lambda x: [e.value for e in x],  # 使用小写 value
        ),
        default=AssetType.IMAGE,
        comment="资产类型: chart/image/export/attachment"
    )
    object_key: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="MinIO 存储路径"
    )
    original_url: Mapped[Optional[str]] = mapped_column(
        Text, comment="原始 URL（外部来源时）"
    )
    file_name: Mapped[Optional[str]] = mapped_column(
        String(255), comment="文件名"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="文件大小（bytes）"
    )
    content_type: Mapped[Optional[str]] = mapped_column(
        String(100), comment="MIME 类型"
    )
    
    # 时间信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), comment="创建时间"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="预签名URL过期时间（可选）"
    )
    
    # 复合索引（按用户和对话查询）
    __table_args__ = (
        Index("idx_user_chat", "user_id", "chat_id"),
    )
