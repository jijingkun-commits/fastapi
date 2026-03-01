"""对话资产数据访问层（中文注释）。"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.chat_asset import ChatAsset, AssetType
from app.schemas.chat_asset import ChatAssetCreate


def create_asset(db: Session, asset_data: ChatAssetCreate) -> ChatAsset:
    """创建一条资产记录。"""
    asset = ChatAsset(**asset_data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_by_id(db: Session, asset_id: int) -> Optional[ChatAsset]:
    """根据主键ID查询资产。"""
    return db.get(ChatAsset, asset_id)


def get_assets_by_chat_id(db: Session, chat_id: str) -> List[ChatAsset]:
    """根据对话ID查询所有资产。"""
    return db.query(ChatAsset).filter(ChatAsset.chat_id == chat_id).all()


def get_assets_by_user_id(db: Session, user_id: int, limit: int = 100) -> List[ChatAsset]:
    """根据用户ID查询资产（分页）。"""
    return db.query(ChatAsset).filter(ChatAsset.user_id == user_id).limit(limit).all()
