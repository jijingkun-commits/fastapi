"""系统级幂等中间件：防止重复提交（中文注释）。

设计：
- 从请求头 `Idempotency-Key` 读取幂等键
- 仅对写操作（POST/PUT/PATCH/DELETE）生效
- 未提供幂等键时直接放行
- 重复请求返回 409 Conflict
- 支持 StreamingResponse（如 SSE），在流结束后标记状态
"""
import logging
from typing import Optional, AsyncIterator

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse, JSONResponse

from app.core.security import decode_token
from app.db.session import get_db_context
from app.repositories import idempotency_repo


logger = logging.getLogger("app.core.middlewares.idempotency")

# 需要幂等检查的 HTTP 方法
IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# 不需要幂等检查的路径前缀（登录、健康检查等）
EXCLUDED_PATHS = {
    "/api/v1/login",
    "/api/v1/auth/login",
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """系统级幂等中间件。
    
    - 从 `Idempotency-Key` 请求头读取幂等键
    - 结合 endpoint 和 user_id 进行唯一性判定
    - 对 StreamingResponse 包装 body_iterator 以追踪状态
    """

    def __init__(self, app: ASGIApp, header_name: str = "Idempotency-Key"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求，检查幂等性。"""
        # 1. 只对写方法生效
        if request.method not in IDEMPOTENT_METHODS:
            return await call_next(request)
        
        # 2. 排除特定路径
        path = request.url.path
        if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
            return await call_next(request)
        
        # 3. 读取幂等键，未提供则放行
        idempotency_key = request.headers.get(self.header_name)
        if not idempotency_key:
            return await call_next(request)
        
        # 4. 解析用户 ID（可选）
        user_id = self._extract_user_id(request)
        endpoint = path
        
        # 5. 检查幂等性
        try:
            with get_db_context() as db:
                ok, status = idempotency_repo.try_start(
                    db,
                    key=idempotency_key,
                    user_id=user_id,
                    endpoint=endpoint,
                )
            
            if not ok:
                logger.info(
                    "幂等拦截: key=%s, endpoint=%s, user_id=%s, status=%s",
                    idempotency_key, endpoint, user_id, status
                )
                return JSONResponse(
                    status_code=409,
                    content={"detail": f"重复请求: status={status}"}
                )
        except Exception as e:
            logger.error("幂等检查异常: %s", e)
            # 检查失败时放行，避免阻塞正常请求
            return await call_next(request)
        
        # 6. 放行请求
        logger.debug(
            "幂等放行: key=%s, endpoint=%s, user_id=%s",
            idempotency_key, endpoint, user_id
        )
        
        response = await call_next(request)
        
        # 7. 处理响应状态
        if isinstance(response, StreamingResponse):
            # 对流式响应，包装 body_iterator 以追踪完成/失败状态
            response.body_iterator = self._wrap_streaming(
                response.body_iterator,
                idempotency_key,
                user_id,
                endpoint,
            )
        else:
            # 非流式响应，直接标记状态
            self._mark_response_status(
                idempotency_key, user_id, endpoint,
                is_success=200 <= response.status_code < 400
            )
        
        return response

    def _extract_user_id(self, request: Request) -> Optional[int]:
        """从 Authorization 头解析用户 ID。"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # 去掉 "Bearer " 前缀
        try:
            payload = decode_token(token)
            # 优先使用 uid 字段（本项目 token 结构）
            uid = payload.get("uid")
            if uid is not None:
                return int(uid)
            # 回退：尝试从 sub 解析（sub 通常是 user_id 的字符串形式）
            sub = payload.get("sub")
            if sub and str(sub).isdigit():
                return int(sub)
            return None
        except Exception:
            return None

    async def _wrap_streaming(
        self,
        iterator: AsyncIterator[bytes],
        key: str,
        user_id: Optional[int],
        endpoint: str,
    ) -> AsyncIterator[bytes]:
        """包装流式响应迭代器，在完成/异常时标记状态。"""
        is_success = True
        try:
            async for chunk in iterator:
                yield chunk
        except Exception as e:
            is_success = False
            logger.error("流式响应异常: %s", e)
            raise
        finally:
            self._mark_response_status(key, user_id, endpoint, is_success)

    def _mark_response_status(
        self,
        key: str,
        user_id: Optional[int],
        endpoint: str,
        is_success: bool,
    ) -> None:
        """标记幂等键的最终状态。"""
        try:
            with get_db_context() as db:
                if is_success:
                    idempotency_repo.mark_completed(
                        db, key=key, user_id=user_id, endpoint=endpoint
                    )
                else:
                    idempotency_repo.mark_failed(
                        db, key=key, user_id=user_id, endpoint=endpoint
                    )
            logger.debug(
                "幂等状态更新: key=%s, status=%s",
                key, "completed" if is_success else "failed"
            )
        except Exception as e:
            logger.error("幂等状态更新失败: %s", e)
