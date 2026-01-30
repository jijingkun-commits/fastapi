"""可观测性模块单元测试。

测试 app/ai/utils/observability.py 的功能。
"""
import unittest
import os
from unittest.mock import patch
from app.ai.utils.observability import (
    is_observability_enabled,
    get_langfuse_config,
    get_tracer,
    reset_tracer,
    trace_node,
    trace_sql_execution,
    trace_retrieval_result,
    get_observability_stats,
    NoopTracer,
    LoggingTracer,
    BaseTracer
)


class TestConfiguration(unittest.TestCase):
    """测试配置函数。"""
    
    def test_observability_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_observability_enabled())
    
    def test_observability_enabled(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "true"}):
            self.assertTrue(is_observability_enabled())
    
    def test_observability_disabled_explicit(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "false"}):
            self.assertFalse(is_observability_enabled())
    
    def test_langfuse_config_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            config = get_langfuse_config()
            self.assertIsNone(config)
    
    def test_langfuse_config_present(self):
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test"
        }):
            config = get_langfuse_config()
            self.assertIsNotNone(config)
            self.assertEqual(config["public_key"], "pk-test")
            self.assertEqual(config["secret_key"], "sk-test")


class TestTracerFactory(unittest.TestCase):
    """测试追踪器工厂。"""
    
    def setUp(self):
        reset_tracer()
    
    def tearDown(self):
        reset_tracer()
    
    def test_noop_tracer_when_disabled(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "false"}):
            reset_tracer()
            tracer = get_tracer()
            self.assertIsInstance(tracer, NoopTracer)
    
    def test_logging_tracer_when_enabled_no_langfuse(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "true"}, clear=True):
            reset_tracer()
            tracer = get_tracer()
            self.assertIsInstance(tracer, LoggingTracer)
    
    def test_tracer_singleton(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "true"}, clear=True):
            reset_tracer()
            tracer1 = get_tracer()
            tracer2 = get_tracer()
            self.assertIs(tracer1, tracer2)


class TestNoopTracer(unittest.TestCase):
    """测试空操作追踪器。"""
    
    def test_trace_node_does_nothing(self):
        tracer = NoopTracer()
        with tracer.trace_node("test"):
            pass  # 不应抛出异常
    
    def test_trace_sql_does_nothing(self):
        tracer = NoopTracer()
        tracer.trace_sql("SELECT 1", True, 100.0)  # 不应抛出异常
    
    def test_trace_retrieval_does_nothing(self):
        tracer = NoopTracer()
        tracer.trace_retrieval("test query", 5)  # 不应抛出异常


class TestLoggingTracer(unittest.TestCase):
    """测试日志追踪器。"""
    
    def test_trace_node_records_stats(self):
        tracer = LoggingTracer()
        with tracer.trace_node("test_node"):
            pass
        
        stats = tracer.get_stats()
        self.assertIn("test_node", stats["nodes"])
        self.assertEqual(stats["nodes"]["test_node"]["count"], 1)
    
    def test_trace_sql_records_stats(self):
        tracer = LoggingTracer()
        tracer.trace_sql("SELECT 1", True, 100.0)
        tracer.trace_sql("SELECT 2", False, 50.0, "error")
        
        stats = tracer.get_stats()
        self.assertEqual(stats["sql_executions"], 2)
        self.assertEqual(stats["sql_errors"], 1)
    
    def test_trace_retrieval_records_stats(self):
        tracer = LoggingTracer()
        tracer.trace_retrieval("test query", 5)
        
        stats = tracer.get_stats()
        self.assertEqual(stats["retrievals"], 1)


class TestConvenienceFunctions(unittest.TestCase):
    """测试便捷函数。"""
    
    def setUp(self):
        reset_tracer()
    
    def tearDown(self):
        reset_tracer()
    
    def test_trace_node_context_manager(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "false"}):
            reset_tracer()
            # 即使禁用，也不应抛出异常
            with trace_node("test"):
                pass
    
    def test_trace_sql_execution(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "false"}):
            reset_tracer()
            # 即使禁用，也不应抛出异常
            trace_sql_execution("SELECT 1", True, 100.0)
    
    def test_trace_retrieval_result(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "false"}):
            reset_tracer()
            # 即使禁用，也不应抛出异常
            trace_retrieval_result("query", 5, ["source1"])


class TestObservabilityStats(unittest.TestCase):
    """测试统计信息。"""
    
    def setUp(self):
        reset_tracer()
    
    def tearDown(self):
        reset_tracer()
    
    def test_stats_with_logging_tracer(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "true"}, clear=True):
            reset_tracer()
            tracer = get_tracer()
            
            with tracer.trace_node("node1"):
                pass
            tracer.trace_sql("SELECT 1", True, 100.0)
            
            stats = get_observability_stats()
            self.assertIn("nodes", stats)
            self.assertIn("sql_executions", stats)
    
    def test_stats_empty_when_disabled(self):
        with patch.dict(os.environ, {"ENABLE_OBSERVABILITY": "false"}):
            reset_tracer()
            stats = get_observability_stats()
            self.assertEqual(stats, {})


if __name__ == '__main__':
    unittest.main()
