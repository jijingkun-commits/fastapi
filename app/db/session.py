"""数据库会话与引擎管理（中文注释）。"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import (
    DATABASE_URL,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_TIMEOUT,
    DB_ECHO,
    ANALYTICS_DATABASE_URL,
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


# ==========================================
# 分析库连接 (Analytics DB)
# ==========================================
analytics_engine = create_engine(
    ANALYTICS_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    echo=DB_ECHO,
)

# 分析库会话工厂
AnalyticsSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=analytics_engine)


def get_db():
    """FastAPI 依赖注入：提供数据库会话。
    
    用法：
        @app.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...
    
    注意：此函数是生成器，专为 FastAPI Depends 设计。
    如需在非 FastAPI 场景使用，请用 get_db_context()。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """上下文管理器：用于非 FastAPI 场景获取数据库会话。
    
    用法：
        with get_db_context() as db:
            chat_repo.save_message(db, ...)
    
    适用场景：LangGraph 节点、Celery 任务、后台线程等。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_analytics_db():
    """FastAPI 依赖注入：提供分析库会话 (Read-Only)。"""
    db = AnalyticsSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_analytics_db_context():
    """上下文管理器：获取分析库会话。"""
    db = AnalyticsSessionLocal()
    try:
        yield db
    finally:
        db.close()
