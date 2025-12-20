"""用户相关接口（中文注释）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.user_repo import get_by_id
from app.schemas.user import UserOut


router = APIRouter(tags=["user"])


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """根据ID获取用户信息。"""
    user = get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserOut.model_validate(user)
