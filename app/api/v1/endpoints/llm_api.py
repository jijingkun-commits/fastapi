"""LLM 配置 API（中文注释）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.llm_config_service import LLMConfigService
from app.core.config import ENV

router = APIRouter()


@router.get("/models", response_model=list[dict])
async def list_models(db: Session = Depends(get_db)):
    """获取所有可用模型列表。"""
    # 开发/测试环境下，便于后台改模型后立即生效（无需重启服务）
    if ENV != "prod":
        LLMConfigService.refresh_cache(db)
    return LLMConfigService.list_available_models()


# 注意：目前只实现了只读接口供前端选择
# 管理接口建议放在 admin 模块或专门的管理后台
