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
