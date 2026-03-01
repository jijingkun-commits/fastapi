"""PostgreSQL Checkpointer 管理模块（中文注释）。

用于管理 LangGraph AsyncPostgresSaver 的连接和实例。
替代原有的 sqlite_session 模块。

注意：AsyncPostgresSaver.from_conn_string() 返回异步上下文管理器，
需要使用 async with 进入上下文后才能使用。
"""
import logging
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import PG_CHECKPOINTER_URI

logger = logging.getLogger(__name__)

# 全局 Checkpointer 实例和上下文管理器
_checkpointer = None
_context_manager = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """获取 PostgreSQL Checkpointer 实例（单例模式，异步）。
    
    使用 async with 进入上下文管理器，setup() 会在 __aenter__ 时自动调用。
    
    Returns:
        AsyncPostgresSaver 实例
    """
    global _checkpointer, _context_manager
    if _checkpointer is None:
        # from_conn_string 返回异步上下文管理器
        _context_manager = AsyncPostgresSaver.from_conn_string(PG_CHECKPOINTER_URI)
        # 进入上下文
        _checkpointer = await _context_manager.__aenter__()
        # 显式调用 setup() 创建 Checkpoint 表
        await _checkpointer.setup()
        
        # 隐藏连接串中的密码
        safe_uri = PG_CHECKPOINTER_URI.split("@")[-1] if "@" in PG_CHECKPOINTER_URI else PG_CHECKPOINTER_URI[:30]
        logger.info("PostgreSQL Checkpointer 已初始化: ...@%s", safe_uri)
    
    return _checkpointer


async def close_checkpointer():
    """关闭 Checkpointer 连接。"""
    global _checkpointer, _context_manager
    if _context_manager is not None:
        try:
            await _context_manager.__aexit__(None, None, None)
        except Exception as e:
            logger.warning("关闭 Checkpointer 时出错: %s", e)
        _context_manager = None
        _checkpointer = None
        logger.info("PostgreSQL Checkpointer 连接已关闭")
