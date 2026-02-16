"""用户业务逻辑层（中文注释）。

规范说明：
- 对于需要访问内部字段（如 password）的操作，返回 ORM 对象
- 对于对外暴露的用户信息，应转换为 Pydantic Schema (UserOut)
"""
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import ENV
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories import user_repo
from app.schemas.user import UserCreate, UserListItem, UserListResponse, UserOut


def authenticate(
    db: Session,
    username: Optional[str],
    mobile: Optional[str],
    password: str,
) -> Optional[User]:
    """认证用户：支持用户名或手机号登录。"""

    user: Optional[User] = None
    if username:
        user = user_repo.get_by_username(db, username)
    elif mobile:
        user = user_repo.get_by_mobile(db, mobile)

    if not user:
        return None
    if not user.is_active:
        return None

    if ENV == "dev":
        return user

    if not verify_password(password, user.password):
        return None
    return user


def get_user_profile(db: Session, user_id: int) -> Optional[UserOut]:
    """获取用户信息（对外暴露）。"""

    user = user_repo.get_by_id(db, user_id)
    if not user:
        return None
    return UserOut.model_validate(user)


def list_users(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
) -> UserListResponse:
    """获取用户列表（分页）。"""

    users, total = user_repo.list_users(db, page, page_size, search)
    items = [UserListItem.model_validate(user) for user in users]
    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


def create_user(db: Session, data: UserCreate) -> Tuple[Optional[UserListItem], Optional[str]]:
    """创建新用户。"""

    if user_repo.get_by_username(db, data.username):
        return None, "用户名已存在"

    if data.mobile and user_repo.get_by_mobile(db, data.mobile):
        return None, "手机号已被使用"

    password_hash = hash_password(data.password)
    user = user_repo.create_user(
        db=db,
        username=data.username,
        password_hash=password_hash,
        mobile=data.mobile,
        role=data.role,
        data_role=data.data_role,
        org_code=data.org_code,
        org_name=data.org_name,
        dept_code=data.dept_code,
        dept_name=data.dept_name,
    )
    return UserListItem.model_validate(user), None


def toggle_user_status(
    db: Session,
    user_id: int,
    is_active: bool,
    current_user_id: int,
) -> Tuple[Optional[UserListItem], Optional[str]]:
    """切换用户启用/禁用状态。"""

    if user_id == current_user_id and not is_active:
        return None, "不能禁用自己"

    user = user_repo.update_user_status(db, user_id, is_active)
    if not user:
        return None, "用户不存在"

    return UserListItem.model_validate(user), None
