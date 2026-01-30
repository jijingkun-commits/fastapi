"""LLM 配置管理 API（中文注释）。

提供：
- 提供商管理（CRUD）
- 模型管理（CRUD）
- 默认模型设置
- API Key 更新
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.services.llm_config_service import LLMConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-admin", tags=["LLM 配置管理"])


# ==================== Schemas ====================

class ProviderResponse(BaseModel):
    """提供商响应。"""
    id: int
    code: str
    name: str
    base_url: Optional[str]
    api_key_masked: str  # 脱敏的 API Key
    is_active: bool
    sort_order: int
    model_count: int
    
    class Config:
        from_attributes = True


class ProviderCreateRequest(BaseModel):
    """创建提供商请求。"""
    code: str
    name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class ProviderUpdateRequest(BaseModel):
    """更新提供商请求。"""
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ModelResponse(BaseModel):
    """模型响应。"""
    id: int
    provider_id: int
    provider_code: str
    provider_name: str
    model_code: str
    model_name: str
    model_type: str
    supports_thinking: bool
    supports_tool_call: bool
    supports_streaming: bool
    max_output_tokens: int
    context_window: int
    default_temperature: float
    is_default: bool
    is_active: bool
    sort_order: int
    description: Optional[str]
    
    class Config:
        from_attributes = True


class ModelCreateRequest(BaseModel):
    """创建模型请求。"""
    provider_id: int
    model_code: str
    model_name: str
    model_type: str = "chat"
    supports_thinking: bool = False
    supports_tool_call: bool = True
    supports_streaming: bool = True
    max_output_tokens: int = 4096
    context_window: int = 32000
    default_temperature: float = 0.7
    thinking_budget: int = 4096
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 0
    description: Optional[str] = None


class ModelUpdateRequest(BaseModel):
    """更新模型请求。"""
    model_name: Optional[str] = None
    model_type: Optional[str] = None
    supports_thinking: Optional[bool] = None
    supports_tool_call: Optional[bool] = None
    supports_streaming: Optional[bool] = None
    max_output_tokens: Optional[int] = None
    context_window: Optional[int] = None
    default_temperature: Optional[float] = None
    thinking_budget: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None


# ==================== 辅助函数 ====================

def _mask_api_key(api_key: Optional[str]) -> str:
    """脱敏 API Key。"""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]


def _provider_to_response(provider: LLMProvider) -> ProviderResponse:
    """转换提供商为响应格式。"""
    return ProviderResponse(
        id=provider.id,
        code=provider.code,
        name=provider.name,
        base_url=provider.base_url,
        api_key_masked=_mask_api_key(provider.api_key),
        is_active=provider.is_active,
        sort_order=provider.sort_order,
        model_count=len(provider.models) if provider.models else 0
    )


def _model_to_response(model: LLMModel) -> ModelResponse:
    """转换模型为响应格式。"""
    return ModelResponse(
        id=model.id,
        provider_id=model.provider_id,
        provider_code=model.provider.code if model.provider else "",
        provider_name=model.provider.name if model.provider else "",
        model_code=model.model_code,
        model_name=model.model_name,
        model_type=model.model_type or "chat",
        supports_thinking=model.supports_thinking,
        supports_tool_call=model.supports_tool_call,
        supports_streaming=model.supports_streaming,
        max_output_tokens=model.max_output_tokens,
        context_window=model.context_window,
        default_temperature=model.default_temperature,
        is_default=model.is_default,
        is_active=model.is_active,
        sort_order=model.sort_order,
        description=model.description
    )


# ==================== 提供商管理 ====================

@router.get("/providers", response_model=List[ProviderResponse])
def list_providers(db: Session = Depends(get_db)):
    """获取所有提供商列表。"""
    providers = db.query(LLMProvider).order_by(LLMProvider.sort_order).all()
    return [_provider_to_response(p) for p in providers]


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """获取单个提供商详情。"""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")
    return _provider_to_response(provider)


@router.post("/providers", response_model=ProviderResponse)
def create_provider(request: ProviderCreateRequest, db: Session = Depends(get_db)):
    """创建新提供商。"""
    # 检查代码是否重复
    existing = db.query(LLMProvider).filter(LLMProvider.code == request.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"提供商代码 {request.code} 已存在")
    
    provider = LLMProvider(
        code=request.code,
        name=request.name,
        base_url=request.base_url,
        api_key=request.api_key,
        is_active=request.is_active,
        sort_order=request.sort_order
    )
    
    db.add(provider)
    db.commit()
    db.refresh(provider)
    
    logger.info(f"创建提供商: {request.code}")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return _provider_to_response(provider)


@router.put("/providers/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, request: ProviderUpdateRequest, db: Session = Depends(get_db)):
    """更新提供商。"""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")
    
    if request.name is not None:
        provider.name = request.name
    if request.base_url is not None:
        provider.base_url = request.base_url
    if request.api_key is not None:
        provider.api_key = request.api_key
    if request.is_active is not None:
        provider.is_active = request.is_active
    if request.sort_order is not None:
        provider.sort_order = request.sort_order
    
    db.commit()
    db.refresh(provider)
    
    logger.info(f"更新提供商: {provider.code}")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return _provider_to_response(provider)


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    """删除提供商（级联删除关联的模型）。"""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")
    
    code = provider.code
    db.delete(provider)
    db.commit()
    
    logger.info(f"删除提供商: {code}")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return {"message": "提供商已删除", "code": code}


@router.put("/providers/{provider_id}/api-key")
def update_provider_api_key(provider_id: int, api_key: str, db: Session = Depends(get_db)):
    """单独更新提供商 API Key。"""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="提供商不存在")
    
    provider.api_key = api_key
    db.commit()
    
    logger.info(f"更新提供商 API Key: {provider.code}")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return {"message": "API Key 已更新", "code": provider.code}


# ==================== 模型管理 ====================

@router.get("/models", response_model=List[ModelResponse])
def list_models(
    provider_id: Optional[int] = None,
    model_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取模型列表。
    
    支持筛选：
    - provider_id: 按提供商筛选
    - model_type: 按模型类型筛选
    - is_active: 按启用状态筛选
    """
    query = db.query(LLMModel)
    
    if provider_id is not None:
        query = query.filter(LLMModel.provider_id == provider_id)
    if model_type is not None:
        query = query.filter(LLMModel.model_type == model_type)
    if is_active is not None:
        query = query.filter(LLMModel.is_active == is_active)
    
    models = query.order_by(LLMModel.sort_order).all()
    return [_model_to_response(m) for m in models]


@router.get("/models/{model_id}", response_model=ModelResponse)
def get_model(model_id: int, db: Session = Depends(get_db)):
    """获取单个模型详情。"""
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return _model_to_response(model)


@router.post("/models", response_model=ModelResponse)
def create_model(request: ModelCreateRequest, db: Session = Depends(get_db)):
    """创建新模型。"""
    # 检查提供商是否存在
    provider = db.query(LLMProvider).filter(LLMProvider.id == request.provider_id).first()
    if not provider:
        raise HTTPException(status_code=400, detail="提供商不存在")
    
    # 检查模型代码是否重复
    existing = db.query(LLMModel).filter(LLMModel.model_code == request.model_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"模型代码 {request.model_code} 已存在")
    
    # 如果设为默认，取消同类型其他模型的默认状态
    if request.is_default:
        db.query(LLMModel).filter(
            LLMModel.model_type == request.model_type,
            LLMModel.is_default == True
        ).update({"is_default": False})
    
    model = LLMModel(
        provider_id=request.provider_id,
        model_code=request.model_code,
        model_name=request.model_name,
        model_type=request.model_type,
        supports_thinking=request.supports_thinking,
        supports_tool_call=request.supports_tool_call,
        supports_streaming=request.supports_streaming,
        max_output_tokens=request.max_output_tokens,
        context_window=request.context_window,
        default_temperature=request.default_temperature,
        thinking_budget=request.thinking_budget,
        is_default=request.is_default,
        is_active=request.is_active,
        sort_order=request.sort_order,
        description=request.description
    )
    
    db.add(model)
    db.commit()
    db.refresh(model)
    
    logger.info(f"创建模型: {request.model_code}")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return _model_to_response(model)


@router.put("/models/{model_id}", response_model=ModelResponse)
def update_model(model_id: int, request: ModelUpdateRequest, db: Session = Depends(get_db)):
    """更新模型。"""
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    # 如果设为默认，取消同类型其他模型的默认状态
    if request.is_default is True:
        model_type = request.model_type or model.model_type
        db.query(LLMModel).filter(
            LLMModel.model_type == model_type,
            LLMModel.is_default == True,
            LLMModel.id != model_id
        ).update({"is_default": False})
    
    # 更新字段
    for field in ["model_name", "model_type", "supports_thinking", "supports_tool_call",
                  "supports_streaming", "max_output_tokens", "context_window",
                  "default_temperature", "thinking_budget", "is_default", "is_active",
                  "sort_order", "description"]:
        value = getattr(request, field)
        if value is not None:
            setattr(model, field, value)
    
    db.commit()
    db.refresh(model)
    
    logger.info(f"更新模型: {model.model_code}")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return _model_to_response(model)


@router.delete("/models/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_db)):
    """删除模型。"""
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    code = model.model_code
    db.delete(model)
    db.commit()
    
    logger.info(f"删除模型: {code}")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return {"message": "模型已删除", "code": code}


@router.put("/models/{model_id}/set-default")
def set_default_model(model_id: int, db: Session = Depends(get_db)):
    """设置模型为默认。"""
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    # 取消同类型其他模型的默认状态
    db.query(LLMModel).filter(
        LLMModel.model_type == model.model_type,
        LLMModel.is_default == True
    ).update({"is_default": False})
    
    # 设置当前模型为默认
    model.is_default = True
    db.commit()
    
    logger.info(f"设置默认模型: {model.model_code} (类型: {model.model_type})")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return {
        "message": "已设为默认模型",
        "model_code": model.model_code,
        "model_type": model.model_type
    }


@router.put("/models/{model_id}/toggle-active")
def toggle_model_active(model_id: int, db: Session = Depends(get_db)):
    """切换模型启用状态。"""
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    model.is_active = not model.is_active
    db.commit()
    
    status = "启用" if model.is_active else "禁用"
    logger.info(f"切换模型状态: {model.model_code} -> {status}")
    
    # 刷新缓存
    LLMConfigService.refresh_cache(db)
    
    return {
        "message": f"模型已{status}",
        "model_code": model.model_code,
        "is_active": model.is_active
    }


# ==================== 模型类型 ====================

@router.get("/model-types")
def list_model_types(db: Session = Depends(get_db)):
    """获取所有模型类型及其默认模型。"""
    types = {}
    models = db.query(LLMModel).filter(LLMModel.is_active == True).all()
    
    for model in models:
        model_type = model.model_type or "chat"
        if model_type not in types:
            types[model_type] = {"count": 0, "default": None}
        types[model_type]["count"] += 1
        if model.is_default:
            types[model_type]["default"] = model.model_code
    
    return [
        {"type": t, "count": info["count"], "default_model": info["default"]}
        for t, info in sorted(types.items())
    ]
