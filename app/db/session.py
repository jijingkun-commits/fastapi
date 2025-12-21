"""数据库会话与引擎管理（中文注释）。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import (
    DATABASE_URL,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_TIMEOUT,
    DB_ECHO,
)


# 创建数据库引擎，启用连接池参数与预探测
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
    echo=DB_ECHO,
)

# 创建会话工厂（禁用自动提交与自动刷新）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖：提供数据库会话，并在请求结束后释放。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
