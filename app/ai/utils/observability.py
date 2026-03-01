"""Data Agent 可观测性模块（中文注释）。

提供 LangGraph 工作流的可观测性支持：
1. LLM 调用追踪
2. 节点执行时间统计
3. SQL 生成/执行统计
4. 错误率追踪

支持多种后端：
- Langfuse（推荐，需要配置 LANGFUSE_* 环境变量）
- 本地日志（默认，无需额外配置）

使用方式：
    from app.ai.utils.observability import get_tracer, trace_node, trace_llm_call
    
    tracer = get_tracer()
    
    with trace_node(tracer, "sql_generate"):
        # 节点逻辑
        ...
    
    # 或使用装饰器
    @trace_node_decorator("sql_execute")
    def sql_execute(state):
        ...

环境变量：
    LANGFUSE_PUBLIC_KEY: Langfuse 公钥
    LANGFUSE_SECRET_KEY: Langfuse 密钥
    LANGFUSE_HOST: Langfuse 服务地址（可选，默认 cloud）
    ENABLE_OBSERVABILITY: 是否启用（true/false，默认 false）
"""
import os
import time
import logging
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


# ==================== 配置 ====================

def is_observability_enabled() -> bool:
    """检查是否启用可观测性。"""
    return os.getenv("ENABLE_OBSERVABILITY", "false").lower() == "true"


def get_langfuse_config() -> Optional[Dict[str, str]]:
    """获取 Langfuse 配置。"""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    
    if public_key and secret_key:
        return {
            "public_key": public_key,
            "secret_key": secret_key,
            "host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        }
    return None


# ==================== Tracer 抽象 ====================

class BaseTracer:
    """追踪器基类。"""
    
    def trace_node(self, name: str, metadata: Dict = None):
        """追踪节点执行。"""
        raise NotImplementedError
    
    def trace_llm(self, name: str, model: str, input_tokens: int = 0, output_tokens: int = 0):
        """追踪 LLM 调用。"""
        raise NotImplementedError
    
    def trace_sql(self, sql: str, success: bool, duration_ms: float, error: str = None):
        """追踪 SQL 执行。"""
        raise NotImplementedError
    
    def trace_retrieval(self, query: str, num_results: int, sources: list = None):
        """追踪检索操作。"""
        raise NotImplementedError
    
    def flush(self):
        """刷新追踪数据。"""
        pass


class NoopTracer(BaseTracer):
    """空操作追踪器（禁用时使用）。"""
    
    @contextmanager
    def trace_node(self, name: str, metadata: Dict = None):
        yield
    
    @contextmanager
    def trace_llm(self, name: str, model: str, input_tokens: int = 0, output_tokens: int = 0):
        yield
    
    def trace_sql(self, sql: str, success: bool, duration_ms: float, error: str = None):
        pass
    
    def trace_retrieval(self, query: str, num_results: int, sources: list = None):
        pass


class LoggingTracer(BaseTracer):
    """基于日志的追踪器（本地调试用）。"""
    
    def __init__(self):
        self.stats = {
            "nodes": {},
            "llm_calls": 0,
            "sql_executions": 0,
            "sql_errors": 0,
            "retrievals": 0,
            "total_tokens": 0,
        }
    
    @contextmanager
    def trace_node(self, name: str, metadata: Dict = None):
        start = time.time()
        logger.info(f"[TRACE] Node '{name}' started")
        try:
            yield
        finally:
            duration = (time.time() - start) * 1000
            logger.info(f"[TRACE] Node '{name}' completed in {duration:.2f}ms")
            
            # 更新统计
            if name not in self.stats["nodes"]:
                self.stats["nodes"][name] = {"count": 0, "total_ms": 0}
            self.stats["nodes"][name]["count"] += 1
            self.stats["nodes"][name]["total_ms"] += duration
    
    @contextmanager
    def trace_llm(self, name: str, model: str, input_tokens: int = 0, output_tokens: int = 0):
        start = time.time()
        logger.info(f"[TRACE] LLM call '{name}' to {model}")
        try:
            yield
        finally:
            duration = (time.time() - start) * 1000
            logger.info(f"[TRACE] LLM call '{name}' completed in {duration:.2f}ms, tokens: {input_tokens}+{output_tokens}")
            self.stats["llm_calls"] += 1
            self.stats["total_tokens"] += input_tokens + output_tokens
    
    def trace_sql(self, sql: str, success: bool, duration_ms: float, error: str = None):
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"[TRACE] SQL {status} in {duration_ms:.2f}ms: {sql[:100]}...")
        self.stats["sql_executions"] += 1
        if not success:
            self.stats["sql_errors"] += 1
            logger.warning(f"[TRACE] SQL error: {error}")
    
    def trace_retrieval(self, query: str, num_results: int, sources: list = None):
        logger.info(f"[TRACE] Retrieval: '{query[:50]}...' -> {num_results} results")
        self.stats["retrievals"] += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息。"""
        return self.stats


class LangfuseTracer(BaseTracer):
    """Langfuse 追踪器。"""
    
    def __init__(self, config: Dict[str, str]):
        try:
            from langfuse import Langfuse
            self.client = Langfuse(
                public_key=config["public_key"],
                secret_key=config["secret_key"],
                host=config.get("host", "https://cloud.langfuse.com")
            )
            self._trace = None
            logger.info("Langfuse tracer initialized")
        except ImportError:
            logger.warning("Langfuse not installed, falling back to logging tracer")
            raise
    
    def start_trace(self, name: str, user_id: str = None, session_id: str = None):
        """开始一个新的追踪。"""
        self._trace = self.client.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata={"start_time": datetime.now().isoformat()}
        )
        return self._trace
    
    @contextmanager
    def trace_node(self, name: str, metadata: Dict = None):
        if not self._trace:
            yield
            return
        
        span = self._trace.span(
            name=name,
            metadata=metadata or {}
        )
        try:
            yield span
        except Exception as e:
            span.update(status_message=str(e), level="ERROR")
            raise
        finally:
            span.end()
    
    @contextmanager
    def trace_llm(self, name: str, model: str, input_tokens: int = 0, output_tokens: int = 0):
        if not self._trace:
            yield
            return
        
        generation = self._trace.generation(
            name=name,
            model=model,
            usage={
                "input": input_tokens,
                "output": output_tokens
            }
        )
        try:
            yield generation
        finally:
            generation.end()
    
    def trace_sql(self, sql: str, success: bool, duration_ms: float, error: str = None):
        if not self._trace:
            return
        
        self._trace.event(
            name="sql_execution",
            metadata={
                "sql": sql[:500],
                "success": success,
                "duration_ms": duration_ms,
                "error": error
            },
            level="DEFAULT" if success else "WARNING"
        )
    
    def trace_retrieval(self, query: str, num_results: int, sources: list = None):
        if not self._trace:
            return
        
        self._trace.event(
            name="retrieval",
            metadata={
                "query": query[:200],
                "num_results": num_results,
                "sources": sources[:5] if sources else []
            }
        )
    
    def flush(self):
        """刷新追踪数据到 Langfuse。"""
        if self.client:
            self.client.flush()


# ==================== 工厂函数 ====================

_tracer_instance: Optional[BaseTracer] = None


def get_tracer() -> BaseTracer:
    """获取追踪器单例。
    
    优先级：
    1. 如果禁用观测性 → NoopTracer
    2. 如果配置了 Langfuse → LangfuseTracer
    3. 否则 → LoggingTracer
    """
    global _tracer_instance
    
    if _tracer_instance is not None:
        return _tracer_instance
    
    if not is_observability_enabled():
        logger.debug("Observability disabled, using NoopTracer")
        _tracer_instance = NoopTracer()
        return _tracer_instance
    
    langfuse_config = get_langfuse_config()
    if langfuse_config:
        try:
            _tracer_instance = LangfuseTracer(langfuse_config)
            logger.info("Using LangfuseTracer for observability")
            return _tracer_instance
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}, falling back to LoggingTracer")
    
    _tracer_instance = LoggingTracer()
    logger.info("Using LoggingTracer for observability")
    return _tracer_instance


def reset_tracer():
    """重置追踪器（测试用）。"""
    global _tracer_instance
    _tracer_instance = None


# ==================== 便捷函数和装饰器 ====================

@contextmanager
def trace_node(name: str, metadata: Dict = None):
    """追踪节点执行的上下文管理器。
    
    用法：
        with trace_node("sql_generate"):
            # 节点逻辑
            ...
    """
    tracer = get_tracer()
    with tracer.trace_node(name, metadata):
        yield


def trace_node_decorator(name: str = None):
    """追踪节点执行的装饰器。
    
    用法：
        @trace_node_decorator("sql_generate")
        def sql_generate(state):
            ...
    """
    def decorator(func: Callable):
        node_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with trace_node(node_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def trace_sql_execution(sql: str, success: bool, duration_ms: float, error: str = None):
    """追踪 SQL 执行。"""
    tracer = get_tracer()
    tracer.trace_sql(sql, success, duration_ms, error)


def trace_retrieval_result(query: str, num_results: int, sources: list = None):
    """追踪检索结果。"""
    tracer = get_tracer()
    tracer.trace_retrieval(query, num_results, sources)


# ==================== 统计接口 ====================

def get_observability_stats() -> Dict[str, Any]:
    """获取可观测性统计信息。
    
    仅在使用 LoggingTracer 时有效。
    """
    tracer = get_tracer()
    if isinstance(tracer, LoggingTracer):
        return tracer.get_stats()
    return {}
