"""AI 模块自定义异常类型。

定义可重试和不可重试的异常类型，用于错误处理和重试逻辑。
"""
from typing import Optional


class AIException(Exception):
    """AI 模块基础异常类。"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class RetryableError(AIException):
    """可重试的错误。
    
    用于临时性故障，如网络超时、API 限流、临时性服务不可用等。
    系统应自动重试这类错误。
    
    Examples:
        - 网络连接超时
        - API 429 Too Many Requests
        - 数据库连接池满
        - LLM 服务临时不可用 (503)
    """
    pass


class NonRetryableError(AIException):
    """不可重试的错误。
    
    用于永久性故障，如认证失败、权限不足、无效参数等。
    系统不应重试这类错误，而应直接返回错误给用户。
    
    Examples:
        - API Key 无效 (401)
        - 权限不足 (403)
        - 资源不存在 (404)
        - 请求参数无效 (400)
        - LLM 输入超过最大 Token 限制
    """
    pass


class LLMInvocationError(RetryableError):
    """LLM 调用错误（默认可重试）。
    
    封装 LLM 调用过程中的各类错误。
    """
    
    def __init__(
        self, 
        message: str, 
        original_error: Optional[Exception] = None,
        is_retryable: bool = True
    ):
        super().__init__(
            message, 
            details={
                "original_error": str(original_error) if original_error else None,
                "is_retryable": is_retryable
            }
        )
        self.original_error = original_error
        self.is_retryable = is_retryable


class HandoffValidationError(NonRetryableError):
    """Handoff 校验错误（不可重试）。
    
    当检测到无效的 Agent 目标或 Handoff 协议错误时抛出。
    """
    
    def __init__(self, message: str, invalid_target: Optional[str] = None):
        super().__init__(
            message,
            details={"invalid_target": invalid_target}
        )
        self.invalid_target = invalid_target
