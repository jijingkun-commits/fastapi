"""LLM 场景治理数据访问层（中文注释）。"""
from typing import Optional, List

from sqlalchemy.orm import Session, joinedload

from app.models.llm_scene import LLMScene
from app.models.llm_model import LLMModel


def list_scenes(db: Session, include_inactive: bool = True) -> List[LLMScene]:
    """获取场景列表。"""

    query = db.query(LLMScene).options(
        joinedload(LLMScene.default_model).joinedload(LLMModel.provider)
    )
    if not include_inactive:
        query = query.filter(LLMScene.is_active == True)

    return query.order_by(LLMScene.scene_key.asc()).all()


def get_scene_by_key(db: Session, scene_key: str) -> Optional[LLMScene]:
    """按 scene_key 查询场景。"""

    return db.query(LLMScene).options(
        joinedload(LLMScene.default_model).joinedload(LLMModel.provider)
    ).filter(
        LLMScene.scene_key == scene_key,
    ).first()
