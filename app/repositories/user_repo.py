"""用户数据访问层（中文注释）。"""
from typing import Optional, Tuple, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.user import User


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    """根据主键ID查询用户。"""
    return db.get(User, user_id)


def get_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名查询用户。"""
    return db.query(User).filter(User.username == username).first()


def get_by_mobile(db: Session, mobile: str) -> Optional[User]:
    """根据手机号查询用户。"""
    return db.query(User).filter(User.mobile == mobile).first()


def list_users(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None
) -> Tuple[List[User], int]:
    """分页查询用户列表。
    
    Args:
        db: 数据库会话
        page: 页码，从1开始
        page_size: 每页数量
        search: 搜索关键词（匹配用户名或手机号）
    
    Returns:
        (用户列表, 总数)
    """
    query = db.query(User)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(search_pattern),
                User.mobile.ilike(search_pattern)
            )
        )
    
    total = query.count()
    offset = (page - 1) * page_size
    users = query.order_by(User.id.desc()).offset(offset).limit(page_size).all()
    
    return users, total


def create_user(
    db: Session,
    username: str,
    password_hash: str,
    mobile: Optional[str] = None,
    role: str = "user",
    org_code: Optional[str] = None,
    org_name: Optional[str] = None,
    dept_code: Optional[str] = None,
    dept_name: Optional[str] = None
) -> User:
    """创建新用户。"""
    user = User(
        username=username,
        password=password_hash,
        mobile=mobile,
        role=role,
        org_code=org_code,
        org_name=org_name,
        dept_code=dept_code,
        dept_name=dept_name,
        is_active=True,
        create_time=datetime.now(),
        update_time=datetime.now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_status(db: Session, user_id: int, is_active: bool) -> Optional[User]:
    """更新用户启用状态。"""
    user = get_by_id(db, user_id)
    if not user:
        return None
    user.is_active = is_active
    user.update_time = datetime.now()
    db.commit()
    db.refresh(user)
    return user
