"""用户业务逻辑层（中文注释）。

规范说明：
- 对于需要访问内部字段（如 password）的操作，返回 ORM 对象
- 对于对外暴露的用户信息，应转换为 Pydantic Schema (UserOut)
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.repositories import user_repo
from app.core.security import verify_password, hash_password
from app.core.config import ENV
from app.models.user import User
from app.schemas.user import UserOut, UserListItem, UserListResponse, UserCreate


def authenticate(db: Session, username: Optional[str], mobile: Optional[str], password: str) -> Optional[User]:
    """认证用户：支持用户名或手机号登录。
    
    开发环境特性：当 ENV=dev 时，跳过密码验证，只要用户存在即可登录。
    
    注意：返回 ORM 对象以便调用方访问内部字段（如 user.id）。
    此函数仅供内部认证流程使用，不直接暴露给 API 响应。
    
    新增：检查用户是否被禁用，禁用用户无法登录。
    """
    user: Optional[User] = None
    if username:
        user = user_repo.get_by_username(db, username)
    elif mobile:
        user = user_repo.get_by_mobile(db, mobile)
    if not user:
        return None
    
    # 检查用户是否被禁用
    if not user.is_active:
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
    user = user_repo.get_by_id(db, user_id)
    if not user:
        return None
    return UserOut.model_validate(user)


def list_users(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None
) -> UserListResponse:
    """获取用户列表（分页）。"""
    users, total = user_repo.list_users(db, page, page_size, search)
    items = [UserListItem.model_validate(u) for u in users]
    return UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


def create_user(db: Session, data: UserCreate) -> Tuple[Optional[UserListItem], Optional[str]]:
    """创建新用户。
    
    Returns:
        (用户信息, 错误消息) - 成功时错误消息为 None
    """
    # 检查用户名是否已存在
    if user_repo.get_by_username(db, data.username):
        return None, "用户名已存在"
    
    # 检查手机号是否已存在（如果提供了手机号）
    if data.mobile and user_repo.get_by_mobile(db, data.mobile):
        return None, "手机号已被使用"
    
    # 创建用户
    password_hash = hash_password(data.password)
    user = user_repo.create_user(
        db=db,
        username=data.username,
        password_hash=password_hash,
        mobile=data.mobile,
        role=data.role,
        org_code=data.org_code,
        org_name=data.org_name,
        dept_code=data.dept_code,
        dept_name=data.dept_name
    )
    return UserListItem.model_validate(user), None


def toggle_user_status(
    db: Session,
    user_id: int,
    is_active: bool,
    current_user_id: int
) -> Tuple[Optional[UserListItem], Optional[str]]:
    """切换用户启用/禁用状态。
    
    Returns:
        (用户信息, 错误消息) - 成功时错误消息为 None
    """
    # 不能禁用自己
    if user_id == current_user_id and not is_active:
        return None, "不能禁用自己"
    
    user = user_repo.update_user_status(db, user_id, is_active)
    if not user:
        return None, "用户不存在"
    
    return UserListItem.model_validate(user), None

