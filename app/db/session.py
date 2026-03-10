"""数据库会话与引擎管理（中文注释）。"""
from contextlib import contextmanager
from dataclasses import dataclass
import logging

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

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DatabaseRuntime:
    """共享数据库运行时契约。"""

    engine: object
    analytics_engine: object
    session_factory: object


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


def get_database_runtime() -> DatabaseRuntime:
    """返回共享数据库运行时。"""

    return DatabaseRuntime(
        engine=engine,
        analytics_engine=analytics_engine,
        session_factory=SessionLocal,
    )


def close_database_runtime() -> None:
    """释放共享数据库引擎连接池。"""

    for target, name in ((analytics_engine, "analytics_engine"), (engine, "engine")):
        try:
            target.dispose()
        except Exception:
            logger.exception("关闭数据库引擎失败: %s", name)


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
