from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.core.exceptions import BusinessException

logger = logging.getLogger(__name__)


async def business_exception_handler(request: Request, exc: BusinessException):
    """业务异常处理。
    
    统一的业务异常响应格式。
    """
    logger.warning(f"Business exception: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "error_code": exc.code,
            "message": exc.message,
            "data": exc.details,
        },
    )


async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理。
    
    捕获所有未处理的异常，返回统一格式。
    """
    # 先检查是否是 BusinessException
    if isinstance(exc, BusinessException):
        return await business_exception_handler(request, exc)
    
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "error_code": "INTERNAL_ERROR",
            "message": "Internal Server Error",
            "data": None,
        },
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        },
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数校验异常处理"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "Validation Error",
            "data": exc.errors()
        },
    )
