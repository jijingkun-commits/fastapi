"""用户相关接口（中文注释）。"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_admin_user
from app.repositories.user_repo import get_by_id
from app.services import user_service
from app.schemas.user import (
    UserOut,
    UserCreate,
    UserListItem,
    UserListResponse,
    UserStatusUpdate
)
from app.models.user import User


router = APIRouter(tags=["user"])


@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词（用户名/手机号）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """获取用户列表（分页）。仅管理员可访问。"""
    return user_service.list_users(db, page, page_size, search)


@router.post("/users", response_model=UserListItem, status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """创建新用户。仅管理员可访问。"""
    user, error = user_service.create_user(db, data)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return user


@router.patch("/users/{user_id}/status", response_model=UserListItem)
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """更新用户启用/禁用状态。仅管理员可访问。"""
    user, error = user_service.toggle_user_status(
        db, user_id, data.is_active, current_user.id
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    return user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """根据ID获取用户信息。"""
    user = get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserOut.model_validate(user)
