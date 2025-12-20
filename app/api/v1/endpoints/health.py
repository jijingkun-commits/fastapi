"""健康检查接口（中文注释）。"""
from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """返回服务健康状态。"""
    return {"status": "ok"}
