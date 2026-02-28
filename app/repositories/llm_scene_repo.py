"""LLM 场景治理数据访问层（中文注释）。"""
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.llm_scene import LLMScene


def list_scenes(db: Session, include_inactive: bool = True) -> List[LLMScene]:
    """获取场景列表。"""

    query = db.query(LLMScene)
    if not include_inactive:
        query = query.filter(LLMScene.is_active == True)

    return query.order_by(LLMScene.scene_key.asc()).all()


def get_scene_by_key(db: Session, scene_key: str) -> Optional[LLMScene]:
    """按 scene_key 查询场景。"""

    return db.query(LLMScene).filter(
        LLMScene.scene_key == scene_key,
    ).first()


def list_scene_keys_by_route_group(db: Session, route_group: str, include_inactive: bool = True) -> List[str]:
    """按路由分组获取场景键列表。"""

    query = db.query(LLMScene.scene_key).filter(LLMScene.route_group == route_group)
    if not include_inactive:
        query = query.filter(LLMScene.is_active == True)

    rows = query.order_by(LLMScene.scene_key.asc()).all()
    return [row[0] for row in rows]
