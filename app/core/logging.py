"""日志配置：通过控制台+按日滚动文件输出，并可选彩色日志。"""
import os
import sys
import logging
import logging.handlers

from app.core.config import (
    LOG_LEVEL,
    LOG_FILE,
    LOG_ROTATE_WHEN,
    LOG_ROTATE_INTERVAL,
    LOG_BACKUP_COUNT,
    LOG_COLORIZE,
)

_CONFIGURED = False


def _level_from_str(level_name: str) -> int:
    """根据文本等级返回数值等级。"""
    mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return mapping.get(level_name.upper(), logging.INFO)


def setup_logging() -> None:
    """初始化日志：
    - 根日志器输出到控制台与文件（按日滚动，保留备份）。
    - 若安装了 ``colorlog`` 且开启彩色，则控制台使用彩色格式。
    - 将 ``uvicorn`` 相关日志写入文件并避免重复输出。
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    # 解析等级与创建目录
    level = _level_from_str(LOG_LEVEL)
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # 格式定义（与提供的配置一致）
    datefmt = "%Y-%m-%d %H:%M:%S"
    file_format = (
        "%(levelname)-8s | %(asctime)s | %(filename)s:%(lineno)d | "
        "%(funcName)s() | %(message)s"
    )
    colored_format = (
        "%(log_color)s%(levelname)-8s | %(asctime)s | %(filename)s:%(lineno)d | "
        "%(funcName)s() | %(message)s"
    )

    # 控制台处理器（彩色优先）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter_console: logging.Formatter
    if LOG_COLORIZE:
        try:
            import colorlog  # type: ignore

            formatter_console = colorlog.ColoredFormatter(
                colored_format,
                datefmt=datefmt,
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "white",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            )
        except Exception:
            formatter_console = logging.Formatter(file_format, datefmt=datefmt)
    else:
        formatter_console = logging.Formatter(file_format, datefmt=datefmt)
    console_handler.setFormatter(formatter_console)

    # 文件处理器（按日滚动，UTF-8 编码）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_FILE,
        when=LOG_ROTATE_WHEN,
        interval=LOG_ROTATE_INTERVAL,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(file_format, datefmt=datefmt))

    # 根日志器：绑定两个处理器
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # uvicorn 相关日志器：仅写入文件，避免重复控制台输出
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.addHandler(file_handler)
        lg.setLevel(level)
        lg.propagate = False

    # 第三方依赖库日志等级配置：屏蔽过多的 DEBUG/INFO 日志
    noisy_loggers = [
        # SQLAlchemy 相关
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.engine.Engine",
        "sqlalchemy.pool",
        "sqlalchemy.dialects",
        "sqlalchemy.orm",
        # LangChain 相关（不含 LangGraph）
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langsmith",
        # HTTP 客户端相关
        "httpx",
        "httpcore",
        "urllib3",
        # 其他常见噪音源
        "openai",
        "asyncio",
        "watchfiles",
    ]
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)

    # LangGraph 及其依赖库的日志等级设置为 INFO（保留重要信息，屏蔽 DEBUG）
    langgraph_loggers = [
        "langgraph",
        "langgraph.checkpoint",
        "langgraph.checkpoint.sqlite",
        "langgraph.checkpoint.sqlite.aio",
        # aiosqlite 是 langgraph checkpoint 的底层依赖，core.py 中的 _connection_worker_thread 日志来自这里
        "aiosqlite",
    ]
    for name in langgraph_loggers:
        logging.getLogger(name).setLevel(logging.INFO)

    _CONFIGURED = True
