"""v1 总路由注册（中文注释）。"""
from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.user import router as user_router
from app.api.v1.endpoints.llm import router as llm_router


api_router = APIRouter(prefix="/api/v1")

# 注册各业务路由
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(llm_router)
