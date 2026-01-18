"""用户业务逻辑层（中文注释）。

规范说明：
- 对于需要访问内部字段（如 password）的操作，返回 ORM 对象
- 对于对外暴露的用户信息，应转换为 Pydantic Schema (UserOut)
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.repositories.user_repo import get_by_username, get_by_mobile, get_by_id
from app.core.security import verify_password
from app.core.config import ENV
from app.models.user import User
from app.schemas.user import UserOut


def authenticate(db: Session, username: Optional[str], mobile: Optional[str], password: str) -> Optional[User]:
    """认证用户：支持用户名或手机号登录。
    
    开发环境特性：当 ENV=dev 时，跳过密码验证，只要用户存在即可登录。
    
    注意：返回 ORM 对象以便调用方访问内部字段（如 user.id）。
    此函数仅供内部认证流程使用，不直接暴露给 API 响应。
    """
    user: Optional[User] = None
    if username:
        user = get_by_username(db, username)
    elif mobile:
        user = get_by_mobile(db, mobile)
    if not user:
        return None
    
    # 开发环境：跳过密码验证
    if ENV == "dev":
        return user
    
    # 生产环境：验证密码
    if not verify_password(password, user.password):
        return None
    return user


def get_user_profile(db: Session, user_id: int) -> Optional[UserOut]:
    """获取用户信息（对外暴露）。
    
    返回 Pydantic Schema，确保数据脱敏且与 Session 解耦。
    """
    user = get_by_id(db, user_id)
    if not user:
        return None
    return UserOut.model_validate(user)

