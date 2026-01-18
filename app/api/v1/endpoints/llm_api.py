"""LLM 配置 API（中文注释）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.llm_config_service import LLMConfigService

router = APIRouter()


@router.get("/models", response_model=list[dict])
async def list_models():
    """获取所有可用模型列表。"""
    return LLMConfigService.list_available_models()


# 注意：目前只实现了只读接口供前端选择
# 管理接口建议放在 admin 模块或专门的管理后台
