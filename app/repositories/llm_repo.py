"""LLM 配置数据访问层（中文注释）。"""
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel


def get_active_providers(db: Session) -> List[LLMProvider]:
    """获取所有启用的提供商。"""
    return db.query(LLMProvider).filter(
        LLMProvider.is_active == True
    ).order_by(LLMProvider.sort_order).all()


def get_provider_by_code(db: Session, code: str) -> Optional[LLMProvider]:
    """根据代码获取提供商。"""
    return db.query(LLMProvider).filter(LLMProvider.code == code).first()


def get_active_models(db: Session) -> List[LLMModel]:
    """获取所有启用的模型（包含提供商信息）。"""
    return db.query(LLMModel).options(
        joinedload(LLMModel.provider)
    ).filter(
        LLMModel.is_active == True,
        LLMModel.provider.has(is_active=True)
    ).order_by(LLMModel.sort_order).all()


def get_model_by_code(db: Session, model_code: str) -> Optional[LLMModel]:
    """根据代码获取模型（包含提供商信息）。"""
    return db.query(LLMModel).options(
        joinedload(LLMModel.provider)
    ).filter(LLMModel.model_code == model_code).first()


def get_default_model(db: Session) -> Optional[LLMModel]:
    """获取默认模型。"""
    return db.query(LLMModel).options(
        joinedload(LLMModel.provider)
    ).filter(
        LLMModel.is_default == True,
        LLMModel.is_active == True
    ).first()


def get_default_model_by_type(db: Session, model_type: str) -> Optional[LLMModel]:
    """获取指定类型的默认模型。
    
    Args:
        db: 数据库会话
        model_type: 模型类型（chat/vision/embedding/rerank/asr/tts）
        
    Returns:
        默认模型，如果没有设置默认则返回该类型的第一个启用模型
    """
    # 先找该类型的默认模型
    model = db.query(LLMModel).options(
        joinedload(LLMModel.provider)
    ).filter(
        LLMModel.model_type == model_type,
        LLMModel.is_default == True,
        LLMModel.is_active == True,
        LLMModel.provider.has(is_active=True)
    ).first()
    
    # 如果没有默认，返回该类型第一个启用的模型
    if not model:
        model = db.query(LLMModel).options(
            joinedload(LLMModel.provider)
        ).filter(
            LLMModel.model_type == model_type,
            LLMModel.is_active == True,
            LLMModel.provider.has(is_active=True)
        ).order_by(LLMModel.sort_order).first()
    
    return model


def get_models_by_type(db: Session, model_type: str) -> List[LLMModel]:
    """获取指定类型的所有启用模型。
    
    Args:
        db: 数据库会话
        model_type: 模型类型
        
    Returns:
        该类型的所有启用模型列表
    """
    return db.query(LLMModel).options(
        joinedload(LLMModel.provider)
    ).filter(
        LLMModel.model_type == model_type,
        LLMModel.is_active == True,
        LLMModel.provider.has(is_active=True)
    ).order_by(LLMModel.sort_order).all()

