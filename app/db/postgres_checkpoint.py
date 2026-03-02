"""PostgreSQL Checkpointer 管理模块（中文注释）。

用于管理 LangGraph AsyncPostgresSaver 的连接和实例。
替代原有的 sqlite_session 模块。

设计说明：
- 使用 AsyncConnectionPool 管理并发连接，避免单连接重入冲突
- 对外保持 get_checkpointer() 调用契约不变
"""
import asyncio
import logging
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.core.config import PG_CHECKPOINTER_URI

logger = logging.getLogger(__name__)

# 全局 Checkpointer 与连接池（单例）
_checkpointer: Optional[AsyncPostgresSaver] = None
_connection_pool: Optional[AsyncConnectionPool] = None
_init_lock: Optional[asyncio.Lock] = None
_setup_done = False

_CHECKPOINTER_BUSY_ERROR_MARKERS = (
    "another command is already in progress",
    "sending query and params failed",
    "sending query failed",
)


def _get_init_lock() -> asyncio.Lock:
    """惰性初始化锁，避免并发重复初始化。"""
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


def is_checkpointer_busy_error(exc: BaseException) -> bool:
    """判断异常是否属于 checkpointer 并发占用。"""
    text = str(exc).lower()
    return any(marker in text for marker in _CHECKPOINTER_BUSY_ERROR_MARKERS)


async def get_connection_pool() -> AsyncConnectionPool:
    """获取 PostgreSQL 连接池（单例模式）。"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = AsyncConnectionPool(
            conninfo=PG_CHECKPOINTER_URI,
            min_size=2,
            max_size=10,
            timeout=30,
            max_idle=300,
            max_lifetime=3600,
            kwargs={"autocommit": True, "prepare_threshold": 0},
            open=False,
        )
        await _connection_pool.open()
        logger.info("PostgreSQL Checkpointer 连接池已初始化: min=2, max=10")
    return _connection_pool


async def get_checkpointer() -> AsyncPostgresSaver:
    """获取 PostgreSQL Checkpointer 实例（单例模式，异步）。
    
    使用 async with 进入上下文管理器，setup() 会在 __aenter__ 时自动调用。
    
    Returns:
        AsyncPostgresSaver 实例
    """
    global _checkpointer, _setup_done
    async with _get_init_lock():
        if _checkpointer is None:
            pool = await get_connection_pool()
            _checkpointer = AsyncPostgresSaver(conn=pool)
        if not _setup_done:
            await _checkpointer.setup()
            _setup_done = True
            safe_uri = PG_CHECKPOINTER_URI.split("@")[-1] if "@" in PG_CHECKPOINTER_URI else PG_CHECKPOINTER_URI[:30]
            logger.info("PostgreSQL Checkpointer 已就绪: ...@%s", safe_uri)
    
    return _checkpointer


async def close_checkpointer():
    """关闭 Checkpointer 连接。"""
    global _checkpointer, _connection_pool, _setup_done
    async with _get_init_lock():
        _checkpointer = None
        _setup_done = False
        if _connection_pool is not None:
            try:
                await _connection_pool.close()
                logger.info("PostgreSQL Checkpointer 连接池已关闭")
            except Exception as e:
                logger.warning("关闭 Checkpointer 连接池时出错: %s", e)
            _connection_pool = None
