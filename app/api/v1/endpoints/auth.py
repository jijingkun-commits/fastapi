"""认证相关接口（中文注释）。"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.schemas.user import LoginRequest, Token, UserOut, get_data_role_label
from app.core.security import create_access_token
from app.services.user_service import authenticate
from app.services.token_service import logout as token_logout
from app.api.deps import get_current_user, get_raw_token


router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


class LogoutResponse(BaseModel):
    """登出响应。"""
    message: str


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """登录接口：用户名/手机号 + 密码。"""
    if not payload.username and not payload.mobile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username或mobile至少提供一个")
    try:
        user = authenticate(db, payload.username, payload.mobile, payload.password)
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="数据库连接失败或查询异常")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(subject=str(user.id), extra={"uid": user.id})
    return Token(access_token=token)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    db: Session = Depends(get_db),
    token: str = Depends(get_raw_token),
    current_user = Depends(get_current_user)
):
    """登出接口：将当前Token加入黑名单。"""
    success = token_logout(db, token)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="登出失败")
    return LogoutResponse(message="登出成功")


@router.get("/me", response_model=UserOut)
def me(current_user = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    user_out = UserOut(
        id=current_user.id,
        username=getattr(current_user, "username", None),
        mobile=getattr(current_user, "mobile", None),
        data_role=getattr(current_user, "data_role", None),
    )
    user_out.data_role_label = get_data_role_label(user_out.data_role)
    return user_out
