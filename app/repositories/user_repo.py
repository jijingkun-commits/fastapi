"""用户数据访问层（中文注释）。"""
from typing import Optional
from sqlalchemy.orm import Session

from ..models.user import User


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    """根据主键ID查询用户。"""
    return db.get(User, user_id)


def get_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名查询用户。"""
    return db.query(User).filter(User.userName == username).first()


def get_by_mobile(db: Session, mobile: str) -> Optional[User]:
    """根据手机号查询用户。"""
    return db.query(User).filter(User.mobile == mobile).first()
