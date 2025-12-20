"""数据库会话与引擎管理（中文注释）。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..core.config import DATABASE_URL


# 创建数据库引擎，启用预探测连接避免失效连接
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 创建会话工厂（禁用自动提交与自动刷新）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 依赖：提供数据库会话，并在请求结束后释放。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
