"""LLM 配置数据访问层（中文注释）。"""
from typing import List
from sqlalchemy.orm import Session, joinedload

from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel


def get_active_providers(db: Session) -> List[LLMProvider]:
    """获取所有启用的提供商。"""
    return db.query(LLMProvider).filter(
        LLMProvider.is_active == True
    ).order_by(LLMProvider.sort_order).all()


def get_active_models(db: Session) -> List[LLMModel]:
    """获取所有启用的模型（包含提供商信息）。"""
    return db.query(LLMModel).options(
        joinedload(LLMModel.provider)
    ).filter(
        LLMModel.is_active == True,
        LLMModel.provider.has(is_active=True)
    ).order_by(LLMModel.sort_order).all()
