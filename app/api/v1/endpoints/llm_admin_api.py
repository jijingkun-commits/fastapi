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
from app.ai.scene_registry import (
    ROUTE_GROUP_DEFAULT_CHAT,
    ROUTE_GROUP_EMBEDDING,
    ROUTE_GROUP_LIGHTWEIGHT,
    ROUTE_GROUP_SQL_GENERATION,
    ROUTE_GROUP_VISION,
)
from app.services.llm_config_service import LLMConfigService
from app.services.llm_scene_service import LLMSceneService, SceneConfigError

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
    extra_config: Optional[dict] = None
    
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
    extra_config: Optional[dict] = None


class ProviderUpdateRequest(BaseModel):
    """更新提供商请求。"""
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    extra_config: Optional[dict] = None


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
    extra_config: Optional[dict] = None
    
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
    extra_config: Optional[dict] = None


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
    extra_config: Optional[dict] = None


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
        model_count=len(provider.models) if provider.models else 0,
        extra_config=provider.extra_config
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
        description=model.description,
        extra_config=model.extra_config
    )


def _refresh_llm_runtime_cache(db: Session):
    """刷新 LLM 运行时缓存。"""

    LLMConfigService.refresh_cache(db)
    LLMSceneService.refresh_cache(db)


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
        sort_order=request.sort_order,
        # 透传扩展配置，供实验型 provider/model 使用。
        extra_config=request.extra_config
    )
    
    db.add(provider)
    db.commit()
    db.refresh(provider)
    
    logger.info(f"创建提供商: {request.code}")
    
    # 刷新缓存
    _refresh_llm_runtime_cache(db)
    
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
    if request.extra_config is not None:
        # 更新时允许直接覆盖扩展配置。
        provider.extra_config = request.extra_config
    
    db.commit()
    db.refresh(provider)
    
    logger.info(f"更新提供商: {provider.code}")
    
    # 刷新缓存
    _refresh_llm_runtime_cache(db)
    
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
    _refresh_llm_runtime_cache(db)
    
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
    _refresh_llm_runtime_cache(db)
    
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
        description=request.description,
        # 透传扩展配置，供运行时按 provider 特性注入参数。
        extra_config=request.extra_config
    )
    
    db.add(model)
    db.commit()
    db.refresh(model)
    
    logger.info(f"创建模型: {request.model_code}")
    
    # 刷新缓存
    _refresh_llm_runtime_cache(db)
    
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
                  "sort_order", "description", "extra_config"]:
        value = getattr(request, field)
        if value is not None:
            setattr(model, field, value)
    
    db.commit()
    db.refresh(model)
    
    logger.info(f"更新模型: {model.model_code}")
    
    # 刷新缓存
    _refresh_llm_runtime_cache(db)
    
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
    _refresh_llm_runtime_cache(db)
    
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
    _refresh_llm_runtime_cache(db)
    
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
    _refresh_llm_runtime_cache(db)
    
    return {
        "message": f"模型已{status}",
        "model_code": model.model_code,
        "is_active": model.is_active
    }


# ==================== 模型路由 ====================

class ModelRouteItem(BaseModel):
    """模型路由项。"""
    scene: str           # 场景名称
    call_point: str      # 调用点
    source: str          # 模型来源：scene_binding / user_select
    config_key: Optional[str] = None  # 配置键名
    current_model: str   # 当前使用的模型代码
    recommended: str     # 推荐模型
    editable: bool       # 是否可在此编辑


class ModelRoutingUpdateRequest(BaseModel):
    """更新模型路由请求。"""
    config_key: str      # 配置键名
    model_code: str      # 新的模型代码


class SceneItem(BaseModel):
    """场景治理项。"""

    scene_key: str
    scene_name: str
    route_group: str
    scene_type: str
    default_model_id: Optional[int] = None
    default_model_code: Optional[str] = None
    is_active: bool
    description: Optional[str] = None


class SceneUpdateRequest(BaseModel):
    """场景更新请求。"""

    default_model_code: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/scenes", response_model=List[SceneItem])
def list_llm_scenes(db: Session = Depends(get_db)):
    """获取 LLM 场景治理列表。"""

    LLMSceneService.refresh_cache(db)
    payload = LLMSceneService.export_scene_payload()
    return [SceneItem(**item) for item in payload]


@router.put("/scenes/{scene_key}")
def update_llm_scene(scene_key: str, request: SceneUpdateRequest, db: Session = Depends(get_db)):
    """更新场景默认模型或状态。"""

    if request.default_model_code is None and request.is_active is None:
        raise HTTPException(status_code=400, detail="至少提供一个可更新字段")

    try:
        scene = LLMSceneService.update_scene(
            db,
            scene_key,
            default_model_code=request.default_model_code,
            is_active=request.is_active,
        )
    except SceneConfigError as exc:
        detail = str(exc)
        status = 404 if "场景不存在" in detail else 400
        raise HTTPException(status_code=status, detail=detail)

    return {
        "message": "场景配置已更新",
        "scene_key": scene.scene_key,
        "default_model_code": scene.default_model_code,
        "is_active": scene.is_active,
    }


def _get_route_group_model_for_routing(
    db: Session,
    route_group: str,
    *,
    fallback_model_type: Optional[str] = "chat",
) -> str:
    """获取路由分组当前模型（scene->model 绑定来源：t_system_config）。"""

    try:
        model_code = LLMSceneService.get_route_group_default_model_code(route_group)
    except SceneConfigError as exc:
        logger.warning("路由分组读取失败，回退类型默认模型: group=%s, error=%s", route_group, exc)
        model_code = None

    if model_code:
        return model_code

    if fallback_model_type:
        return _get_type_default_model(db, fallback_model_type)

    return "未配置"


def _get_type_default_model(db: Session, model_type: str) -> str:
    """获取指定类型的默认模型代码。"""
    default = db.query(LLMModel).filter(
        LLMModel.model_type == model_type,
        LLMModel.is_default == True,
        LLMModel.is_active == True
    ).first()
    if default:
        return default.model_code
    first = db.query(LLMModel).filter(
        LLMModel.model_type == model_type,
        LLMModel.is_active == True
    ).first()
    return first.model_code if first else "未配置"


def _is_supported_vision_route_model(model: LLMModel) -> bool:
    """判断模型是否可绑定到 Vision 路由。"""
    return (model.model_type or "chat") in {"vision", "chat", "reasoning"}


@router.get("/model-routing", response_model=List[ModelRouteItem])
def get_model_routing(db: Session = Depends(get_db)):
    """获取模型路由总览表（按能力分层，5 行）。
    
    分层策略：
    1. 主对话：默认模型可配置，用户可在聊天页按需覆盖
    2. SQL 生成 / 内部分析：标准模型，需理解 schema 和业务语义
    3. 轻量任务：意图分类、参数提取、评估，轻量模型即可
    4. Embedding：向量化专用
    5. Vision：图像理解专用
    """
    from app.core.config import (
        MODEL_ROUTING_DEFAULT_CHAT,
        MODEL_ROUTING_EMBEDDING,
        MODEL_ROUTING_INTENT_CLASSIFIER,
        MODEL_ROUTING_SQL_GENERATION,
        MODEL_ROUTING_VISION,
    )

    # 单一来源：路由分组场景绑定（t_llm_scene）
    LLMSceneService.refresh_cache(db)
    default_chat_model = _get_route_group_model_for_routing(db, ROUTE_GROUP_DEFAULT_CHAT, fallback_model_type="chat")
    sql_gen_model = _get_route_group_model_for_routing(db, ROUTE_GROUP_SQL_GENERATION, fallback_model_type="chat")
    lightweight_model = _get_route_group_model_for_routing(db, ROUTE_GROUP_LIGHTWEIGHT, fallback_model_type="chat")
    embedding_model = _get_route_group_model_for_routing(
        db,
        ROUTE_GROUP_EMBEDDING,
        fallback_model_type="embedding",
    )
    vision_model = _get_route_group_model_for_routing(
        db,
        ROUTE_GROUP_VISION,
        fallback_model_type="vision",
    )

    routes = [
        ModelRouteItem(
            scene="主对话",
            call_point="Supervisor / Agent 回复",
            source="scene_binding",
            config_key=MODEL_ROUTING_DEFAULT_CHAT,
            current_model=default_chat_model,
            recommended="qwen-plus / deepseek-chat",
            editable=True
        ),
        ModelRouteItem(
            scene="SQL 生成 / 内部分析",
            call_point="vanna_client, analyze_data_intent, todo analyze_intent",
            source="scene_binding",
            config_key=MODEL_ROUTING_SQL_GENERATION,
            current_model=sql_gen_model,
            recommended="qwen-plus / deepseek-chat",
            editable=True
        ),
        ModelRouteItem(
            scene="轻量任务（意图分类 / 参数提取 / 评估）",
            call_point="intent_classifier, parameter_extractor, llm_judge, sql_evaluator",
            source="scene_binding",
            config_key=MODEL_ROUTING_INTENT_CLASSIFIER,
            current_model=lightweight_model,
            recommended="glm-4.5-air / qwen-flash",
            editable=True
        ),
        ModelRouteItem(
            scene="Embedding",
            call_point="embedding_util.get_embedding",
            source="scene_binding",
            config_key=MODEL_ROUTING_EMBEDDING,
            current_model=embedding_model,
            recommended="embedding-3",
            editable=True
        ),
        ModelRouteItem(
            scene="Vision",
            call_point="vision_tool.analyze_image",
            source="scene_binding",
            config_key=MODEL_ROUTING_VISION,
            current_model=vision_model,
            recommended="glm-4v-flash / gpt-5.2",
            editable=True
        ),
    ]
    
    return routes


@router.put("/model-routing")
def update_model_routing(request: ModelRoutingUpdateRequest, db: Session = Depends(get_db)):
    """更新模型路由配置。

    数据来源拆分：
    - t_llm_scene: scene_key -> route_group
    - t_system_config: route_group(config_key) -> model_id
    """
    from app.core.config import (
        MODEL_ROUTING_DEFAULT_CHAT,
        MODEL_ROUTING_EMBEDDING,
        MODEL_ROUTING_INTENT_CLASSIFIER,
        MODEL_ROUTING_LLM_JUDGE,
        MODEL_ROUTING_SQL_GENERATION,
        MODEL_ROUTING_VISION,
    )

    # 验证 config_key 合法性（INTENT_CLASSIFIER 和 LLM_JUDGE 共享同一配置键 model_routing.lightweight）
    allowed_keys = {
        MODEL_ROUTING_DEFAULT_CHAT,
        MODEL_ROUTING_INTENT_CLASSIFIER,
        MODEL_ROUTING_LLM_JUDGE,
        MODEL_ROUTING_SQL_GENERATION,
        MODEL_ROUTING_EMBEDDING,
        MODEL_ROUTING_VISION,
    }
    if request.config_key not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"不支持修改此配置项: {request.config_key}")

    # 验证模型代码是否存在且启用
    model = db.query(LLMModel).filter(
        LLMModel.model_code == request.model_code,
        LLMModel.is_active == True
    ).first()
    if not model:
        raise HTTPException(status_code=400, detail=f"模型不存在或未启用: {request.model_code}")

    if request.config_key == MODEL_ROUTING_DEFAULT_CHAT and model.model_type != "chat":
        raise HTTPException(status_code=400, detail="默认对话模型必须是对话类型模型")
    if request.config_key == MODEL_ROUTING_EMBEDDING and model.model_type != "embedding":
        raise HTTPException(status_code=400, detail="向量模型路由仅支持向量类型模型")
    if request.config_key == MODEL_ROUTING_VISION and not _is_supported_vision_route_model(model):
        raise HTTPException(
            status_code=400,
            detail="视觉模型路由仅支持视觉、对话或推理类型模型",
        )

    route_group_by_key = {
        MODEL_ROUTING_DEFAULT_CHAT: ROUTE_GROUP_DEFAULT_CHAT,
        MODEL_ROUTING_INTENT_CLASSIFIER: ROUTE_GROUP_LIGHTWEIGHT,
        MODEL_ROUTING_LLM_JUDGE: ROUTE_GROUP_LIGHTWEIGHT,
        MODEL_ROUTING_SQL_GENERATION: ROUTE_GROUP_SQL_GENERATION,
        MODEL_ROUTING_EMBEDDING: ROUTE_GROUP_EMBEDDING,
        MODEL_ROUTING_VISION: ROUTE_GROUP_VISION,
    }

    route_group = route_group_by_key.get(request.config_key)
    if route_group is None:
        raise HTTPException(status_code=400, detail=f"不支持修改此配置项: {request.config_key}")

    try:
        LLMSceneService.update_route_group_default_model(
            db=db,
            route_group=route_group,
            default_model_code=request.model_code,
        )
    except SceneConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _refresh_llm_runtime_cache(db)
    logger.info(
        "更新模型路由(路由分组绑定): config_key=%s, route_group=%s, model=%s",
        request.config_key,
        route_group,
        request.model_code,
    )

    return {
        "message": "模型路由已更新",
        "config_key": request.config_key,
        "model_code": request.model_code
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
