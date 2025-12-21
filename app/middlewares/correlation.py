"""请求关联ID中间件：生成或透传 X-Request-ID，并记录处理耗时。"""
import uuid
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """将请求ID挂载到 ``request.state.correlation_id``，并在响应头写回；同时记录耗时。

    - 若调用方已设置 ``X-Request-ID``，则透传该值；否则自动生成随机ID。
    - 在响应中添加两个头：``X-Request-ID`` 与 ``X-Process-Time``（毫秒）。
    - 在日志中输出方法、路径、关联ID与耗时，便于追踪与定位。
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name
        self.logger = logging.getLogger("app.middlewares.correlation")

    async def dispatch(self, request: Request, call_next):
        """生成/透传请求ID，调用下游应用，回写响应头并记录耗时与日志。"""
        # 1) 从请求头读取已有的请求ID，若不存在则生成一个新的
        cid = request.headers.get(self.header_name)
        if not cid:
            cid = uuid.uuid4().hex
        # 将ID放入 request.state，便于在业务代码或集成层中访问与透传
        request.state.correlation_id = cid
        # 2) 进入下一个处理环节前记录起始时间
        start = time.perf_counter()
        response: Response = await call_next(request)
        # 3) 计算耗时（毫秒），并通过响应头暴露给调用方
        duration_ms = (time.perf_counter() - start) * 1000.0
        response.headers[self.header_name] = cid
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        # 4) 记录调试级日志，便于问题定位
        self.logger.debug(f"{request.method} {request.url.path} cid={cid} time_ms={duration_ms:.2f}")
        return response
