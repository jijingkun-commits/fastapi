"""用户业务逻辑层（中文注释）。"""
from typing import Optional
from sqlalchemy.orm import Session

from app.repositories.user_repo import get_by_username, get_by_mobile
from app.core.security import verify_password
from app.models.user import User


def authenticate(db: Session, username: Optional[str], mobile: Optional[str], password: str) -> Optional[User]:
    """认证用户：支持用户名或手机号登录。"""
    user: Optional[User] = None
    if username:
        user = get_by_username(db, username)
    elif mobile:
        user = get_by_mobile(db, mobile)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user
