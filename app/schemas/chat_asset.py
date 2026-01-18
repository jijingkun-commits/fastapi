"""对话资产相关的 Pydantic 模型（中文注释）。"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.chat_asset import AssetType


class ChatAssetBase(BaseModel):
    """资产基础模型：共享字段。"""
    qa_record_id: int
    chat_id: str
    user_id: Optional[int] = None
    asset_type: AssetType = AssetType.IMAGE
    object_key: str
    original_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None


class ChatAssetCreate(ChatAssetBase):
    """创建资产时使用的模型。"""
    pass


class ChatAssetOut(ChatAssetBase):
    """资产响应模型：包含预签名 URL。"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    # 前端使用的预签名 URL（动态生成，不存数据库）
    presigned_url: Optional[str] = None
