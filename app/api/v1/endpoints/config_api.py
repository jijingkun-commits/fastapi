"""系统配置 API（中文注释）。"""
from fastapi import APIRouter
from typing import Optional

from app.services.system_config_service import SystemConfigService

router = APIRouter()


@router.get("/configs", response_model=list[dict])
async def list_configs(category: Optional[str] = None):
    """获取系统配置列表。"""
    return SystemConfigService.list_configs(category=category)
