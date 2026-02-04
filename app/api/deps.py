"""依赖注入：解析当前用户（中文注释）。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.token_service import is_token_valid
from app.repositories.user_repo import get_by_id


# OAuth2 密码模式，token 获取地址为 v1 的登录接口
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """根据Bearer Token解析当前用户。
    
    验证流程：
    1. 解析Token并验证签名
    2. 检查Token是否在黑名单中
    3. 检查用户是否存在
    4. 检查用户是否被禁用
    """
    valid, payload = is_token_valid(db, token)
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    
    try:
        uid = int(payload.get("uid"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    
    user = get_by_id(db, uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户已被禁用")
    return user


def get_admin_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """管理员权限验证，仅允许 role=admin 的用户访问。"""
    valid, payload = is_token_valid(db, token)
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    
    try:
        uid = int(payload.get("uid"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    
    user = get_by_id(db, uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户已被禁用")
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
    
    valid, payload = is_token_valid(db, token)
    if not valid:
        return None
    
    try:
        uid = int(payload.get("uid"))
        user = get_by_id(db, uid)
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None


def get_raw_token(token: str = Depends(oauth2_scheme)) -> str:
    """获取原始Token字符串（用于登出）。"""
    return token

