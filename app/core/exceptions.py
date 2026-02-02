"""自定义异常类（中文注释）。

提供统一的业务异常定义和错误响应格式。
"""
from typing import Optional, Any


class BusinessException(Exception):
    """业务异常基类。
    
    所有业务逻辑异常都应继承此类，确保统一的错误响应格式。
    """
    def __init__(
        self,
        message: str,
        code: str = "BUSINESS_ERROR",
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """转换为 API 响应格式。"""
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


class NotFoundException(BusinessException):
    """资源不存在异常。"""
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} 不存在: {identifier}",
            code="NOT_FOUND",
            status_code=404,
        )


class PermissionDeniedException(BusinessException):
    """权限不足异常。"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=403,
        )


class ValidationException(BusinessException):
    """数据验证失败异常。"""
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class ConflictException(BusinessException):
    """资源冲突异常。"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
        )


class RateLimitException(BusinessException):
    """请求频率限制异常。"""
    def __init__(self, message: str = "请求过于频繁，请稍后重试"):
        super().__init__(
            message=message,
            code="RATE_LIMITED",
            status_code=429,
        )


# ==================== 待办相关异常 ====================

class TodoException(BusinessException):
    """待办相关异常基类。"""
    def __init__(self, message: str, code: str = "TODO_ERROR", status_code: int = 400):
        super().__init__(message=message, code=code, status_code=status_code)


class TodoNotFoundException(TodoException):
    """待办不存在异常。"""
    def __init__(self, todo_id: int):
        self.todo_id = todo_id
        super().__init__(
            message=f"待办 {todo_id} 不存在",
            code="TODO_NOT_FOUND",
            status_code=404,
        )


class TodoPermissionDeniedException(TodoException):
    """无权限操作待办异常。"""
    def __init__(self, todo_id: int, user_id: int):
        self.todo_id = todo_id
        self.user_id = user_id
        super().__init__(
            message=f"用户 {user_id} 无权操作待办 {todo_id}",
            code="TODO_PERMISSION_DENIED",
            status_code=403,
        )


class TodoValidationException(TodoException):
    """待办数据验证失败异常。"""
    def __init__(self, message: str):
        super().__init__(
            message=f"数据验证失败: {message}",
            code="TODO_VALIDATION_ERROR",
            status_code=422,
        )


class RecurringTaskException(TodoException):
    """重复任务相关异常。"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="RECURRING_TASK_ERROR",
            status_code=400,
        )
