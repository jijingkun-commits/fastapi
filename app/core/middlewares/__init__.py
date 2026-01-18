"""核心中间件包：放置横切关注点，如请求ID、限流、安全头等（中文注释）。"""

from app.core.middlewares.correlation import CorrelationIdMiddleware

__all__ = ["CorrelationIdMiddleware"]
