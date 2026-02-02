"""依赖注入：解析当前用户（中文注释）。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.repositories.user_repo import get_by_id


# OAuth2 密码模式，token 获取地址为 v1 的登录接口
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """根据Bearer Token解析当前用户。"""
    try:
        payload = decode_token(token)
        uid = int(payload.get("uid"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    user = get_by_id(db, uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_admin_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """管理员权限验证，仅允许 role=admin 的用户访问。"""
    try:
        payload = decode_token(token)
        uid = int(payload.get("uid"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    user = get_by_id(db, uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


# 可选的 OAuth2 认证（不强制要求 token）
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/login", auto_error=False)


def get_current_user_optional(
    token: str = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
):
    """可选的用户认证，未提供 token 时返回 None。"""
    if not token:
        return None
    try:
        payload = decode_token(token)
        uid = int(payload.get("uid"))
        user = get_by_id(db, uid)
        return user
    except Exception:
        return None

