"""LLM 调用重试装饰器。

提供智能重试逻辑，区分可重试和不可重试错误。
"""
import asyncio
import functools
import logging
from typing import Callable, TypeVar, Optional, Type
from langchain_core.language_models import BaseChatModel

from app.ai.exceptions import RetryableError, NonRetryableError, LLMInvocationError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def with_llm_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (RetryableError,)
):
    """LLM 调用重试装饰器（支持同步和异步函数）。
    
    使用指数退避策略重试 LLM 调用。自动区分可重试错误和不可重试错误。
    
    Args:
        max_retries: 最大重试次数（不包括首次调用）
        initial_delay: 初始重试延迟（秒）
        max_delay: 最大重试延迟（秒）
        backoff_factor: 退避因子（每次重试延迟 *= backoff_factor）
        retryable_exceptions: 需要重试的异常类型元组
    
    Examples:
        ```python
        @with_llm_retry(max_retries=3)
        def call_llm(prompt: str):
            return llm.invoke(prompt)
        
        @with_llm_retry(max_retries=2, initial_delay=0.5)
        async def call_llm_async(prompt: str):
            return await llm.ainvoke(prompt)
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # 检测是否为异步函数
        is_async = asyncio.iscoroutinefunction(func)
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                last_exception = None
                delay = initial_delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    
                    except NonRetryableError as e:
                        # 不可重试错误，直接抛出
                        logger.error(
                            f"LLM 调用失败（不可重试）: {e}, "
                            f"函数: {func.__name__}"
                        )
                        raise
                    
                    except retryable_exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(
                                f"LLM 调用失败（第 {attempt + 1}/{max_retries + 1} 次尝试）: {e}, "
                                f"函数: {func.__name__}, "
                                f"{delay:.1f}秒后重试"
                            )
                            await asyncio.sleep(delay)
                            delay = min(delay * backoff_factor, max_delay)
                        else:
                            logger.error(
                                f"LLM 调用失败（已达最大重试次数 {max_retries}）: {e}, "
                                f"函数: {func.__name__}"
                            )
                    
                    except Exception as e:
                        # 未预期的异常，判断是否可重试
                        # 常见的可重试错误模式
                        error_msg = str(e).lower()
                        is_retryable = any(
                            keyword in error_msg 
                            for keyword in [
                                "timeout", "connection", "network", 
                                "429", "503", "rate limit", "quota"
                            ]
                        )
                        
                        if is_retryable and attempt < max_retries:
                            logger.warning(
                                f"LLM 调用遇到可重试错误（第 {attempt + 1}/{max_retries + 1} 次尝试）: {e}, "
                                f"函数: {func.__name__}, "
                                f"{delay:.1f}秒后重试"
                            )
                            last_exception = LLMInvocationError(
                                f"LLM 调用失败: {e}",
                                original_error=e,
                                is_retryable=True
                            )
                            await asyncio.sleep(delay)
                            delay = min(delay * backoff_factor, max_delay)
                        else:
                            logger.error(
                                f"LLM 调用遇到不可重试错误: {e}, "
                                f"函数: {func.__name__}"
                            )
                            raise LLMInvocationError(
                                f"LLM 调用失败: {e}",
                                original_error=e,
                                is_retryable=False
                            )
                
                # 所有重试都失败了
                if last_exception:
                    raise last_exception
                
            return async_wrapper
        
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                last_exception = None
                delay = initial_delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    
                    except NonRetryableError as e:
                        logger.error(
                            f"LLM 调用失败（不可重试）: {e}, "
                            f"函数: {func.__name__}"
                        )
                        raise
                    
                    except retryable_exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            logger.warning(
                                f"LLM 调用失败（第 {attempt + 1}/{max_retries + 1} 次尝试）: {e}, "
                                f"函数: {func.__name__}, "
                                f"{delay:.1f}秒后重试"
                            )
                            import time
                            time.sleep(delay)
                            delay = min(delay * backoff_factor, max_delay)
                        else:
                            logger.error(
                                f"LLM 调用失败（已达最大重试次数 {max_retries}）: {e}, "
                                f"函数: {func.__name__}"
                            )
                    
                    except Exception as e:
                        error_msg = str(e).lower()
                        is_retryable = any(
                            keyword in error_msg 
                            for keyword in [
                                "timeout", "connection", "network", 
                                "429", "503", "rate limit", "quota"
                            ]
                        )
                        
                        if is_retryable and attempt < max_retries:
                            logger.warning(
                                f"LLM 调用遇到可重试错误（第 {attempt + 1}/{max_retries + 1} 次尝试）: {e}, "
                                f"函数: {func.__name__}, "
                                f"{delay:.1f}秒后重试"
                            )
                            last_exception = LLMInvocationError(
                                f"LLM 调用失败: {e}",
                                original_error=e,
                                is_retryable=True
                            )
                            import time
                            time.sleep(delay)
                            delay = min(delay * backoff_factor, max_delay)
                        else:
                            logger.error(
                                f"LLM 调用遇到不可重试错误: {e}, "
                                f"函数: {func.__name__}"
                            )
                            raise LLMInvocationError(
                                f"LLM 调用失败: {e}",
                                original_error=e,
                                is_retryable=False
                            )
                
                if last_exception:
                    raise last_exception
                
            return sync_wrapper
    
    return decorator
