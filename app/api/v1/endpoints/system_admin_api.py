"""系统配置管理 API（中文注释）。

提供：
- 配置列表查询
- 配置更新
- 配置分类管理
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.system_config import SystemConfig
from app.services.system_config_service import SystemConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system-admin", tags=["系统配置管理"])


# ==================== Schemas ====================

class ConfigResponse(BaseModel):
    """配置响应。"""
    id: int
    config_key: str
    config_value: str
    value_type: str
    category: Optional[str]
    description: Optional[str]
    is_secret: bool
    is_readonly: bool
    
    class Config:
        from_attributes = True


class ConfigUpdateRequest(BaseModel):
    """更新配置请求。"""
    config_value: str


class ConfigCreateRequest(BaseModel):
    """创建配置请求。"""
    config_key: str
    config_value: str
    value_type: str = "string"
    category: Optional[str] = None
    description: Optional[str] = None
    is_secret: bool = False
    is_readonly: bool = False


class CategoryResponse(BaseModel):
    """分类响应。"""
    category: str
    count: int


# ==================== 辅助函数 ====================

def _mask_secret(config: SystemConfig) -> str:
    """脱敏敏感配置值。"""
    if not config.is_secret:
        return config.config_value
    
    value = config.config_value
    if len(value) <= 6:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def _config_to_response(config: SystemConfig) -> ConfigResponse:
    """转换配置为响应格式。"""
    return ConfigResponse(
        id=config.id,
        config_key=config.config_key,
        config_value=_mask_secret(config),
        value_type=config.value_type or "string",
        category=config.category,
        description=config.description,
        is_secret=config.is_secret,
        is_readonly=config.is_readonly
    )


# ==================== API 端点 ====================

@router.get("/configs", response_model=List[ConfigResponse])
def list_configs(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取配置列表。
    
    支持按分类筛选。
    """
    query = db.query(SystemConfig)
    
    if category:
        query = query.filter(SystemConfig.category == category)
    
    configs = query.order_by(SystemConfig.category, SystemConfig.config_key).all()
    
    return [_config_to_response(c) for c in configs]


@router.get("/configs/{config_key}", response_model=ConfigResponse)
def get_config(config_key: str, db: Session = Depends(get_db)):
    """获取单个配置详情。"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    return _config_to_response(config)


@router.put("/configs/{config_key}")
def update_config(config_key: str, request: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """更新配置值。"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    if config.is_readonly:
        raise HTTPException(status_code=400, detail="该配置为只读，无法修改")
    
    old_value = config.config_value
    config.config_value = request.config_value
    db.commit()
    
    logger.info(f"更新配置: {config_key} = {request.config_value[:50]}...")
    
    # 刷新缓存
    SystemConfigService.refresh_cache(db)
    
    return {
        "message": "配置已更新",
        "key": config_key,
        "old_value": "***" if config.is_secret else old_value,
        "new_value": "***" if config.is_secret else request.config_value
    }


@router.post("/configs", response_model=ConfigResponse)
def create_config(request: ConfigCreateRequest, db: Session = Depends(get_db)):
    """创建新配置。"""
    # 检查是否已存在
    existing = db.query(SystemConfig).filter(SystemConfig.config_key == request.config_key).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"配置 {request.config_key} 已存在")
    
    config = SystemConfig(
        config_key=request.config_key,
        config_value=request.config_value,
        value_type=request.value_type,
        category=request.category,
        description=request.description,
        is_secret=request.is_secret,
        is_readonly=request.is_readonly
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    logger.info(f"创建配置: {request.config_key}")
    
    # 刷新缓存
    SystemConfigService.refresh_cache(db)
    
    return _config_to_response(config)


@router.delete("/configs/{config_key}")
def delete_config(config_key: str, db: Session = Depends(get_db)):
    """删除配置。"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    if config.is_readonly:
        raise HTTPException(status_code=400, detail="该配置为只读，无法删除")
    
    db.delete(config)
    db.commit()
    
    logger.info(f"删除配置: {config_key}")
    
    # 刷新缓存
    SystemConfigService.refresh_cache(db)
    
    return {"message": "配置已删除", "key": config_key}


@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """获取所有配置分类。"""
    from sqlalchemy import func
    
    result = db.query(
        SystemConfig.category,
        func.count(SystemConfig.id).label("count")
    ).group_by(SystemConfig.category).all()
    
    return [
        CategoryResponse(
            category=r.category or "未分类",
            count=r.count
        )
        for r in result
    ]


@router.post("/refresh-cache")
def refresh_cache(db: Session = Depends(get_db)):
    """手动刷新配置缓存。"""
    SystemConfigService.refresh_cache(db)
    
    return {
        "message": "缓存已刷新",
        "count": len(SystemConfigService._cache)
    }
