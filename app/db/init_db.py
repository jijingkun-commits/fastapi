"""初始化数据库与开发环境数据（中文注释）。"""
from sqlalchemy.orm import Session

from .session import SessionLocal
from ..repositories.user_repo import get_by_username
from ..models.user import User
from ..core.security import hash_password


def init_db(seed_admin: bool = True) -> None:
    """初始化数据库：可选插入开发用管理员用户。"""
    db: Session = SessionLocal()
    try:
        if seed_admin:
            admin = get_by_username(db, "admin")
            if not admin:
                user = User(
                    userName="admin",
                    password=hash_password("secret"),
                    mobile="13800000000",
                )
                db.add(user)
                db.commit()
    finally:
        db.close()
