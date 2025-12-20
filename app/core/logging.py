"""日志配置：统一日志格式与等级（中文注释）。"""
import logging


def setup_logging(level: int = logging.INFO) -> None:
    """配置基础日志格式与等级。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
