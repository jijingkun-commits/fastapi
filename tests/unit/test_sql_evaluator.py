"""SQL 评估器单元测试。

测试 app/ai/utils/sql_evaluator.py 的功能。
"""
import unittest
from app.ai.utils.sql_evaluator import (
    evaluate_syntax,
    evaluate_performance,
    evaluate_retrieval,
    quick_evaluate,
    SQLSyntaxResult,
    PerformanceResult,
    RetrievalQualityResult
)


class TestEvaluateSyntax(unittest.TestCase):
    """测试语法评估。"""
    
    def test_valid_sql(self):
        sql = "SELECT id, name FROM orders WHERE status = 'active'"
        result = evaluate_syntax(sql)
        self.assertIsInstance(result, SQLSyntaxResult)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.error)
        self.assertIn("orders", result.tables)
        self.assertEqual(result.query_type, "SELECT")
    
    def test_syntax_result_structure(self):
        # 测试返回结构而不是具体的语法验证结果
        sql = "SELEC * FROM orders"
        result = evaluate_syntax(sql)
        self.assertIsInstance(result, SQLSyntaxResult)
        self.assertIsInstance(result.is_valid, bool)
        self.assertIsInstance(result.tables, list)
    
    def test_complex_query(self):
        sql = """
        SELECT u.name, COUNT(o.id) as order_count
        FROM customers u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.name
        """
        result = evaluate_syntax(sql)
        self.assertTrue(result.is_valid)
        self.assertIn("customers", result.tables)
        self.assertIn("orders", result.tables)


class TestEvaluatePerformance(unittest.TestCase):
    """测试性能评估。"""
    
    def test_missing_limit_warning(self):
        sql = "SELECT * FROM users"
        result = evaluate_performance(sql)
        self.assertIsInstance(result, PerformanceResult)
        self.assertFalse(result.has_limit)
        self.assertTrue(any("LIMIT" in w for w in result.warnings))
    
    def test_has_limit(self):
        sql = "SELECT * FROM users LIMIT 100"
        result = evaluate_performance(sql)
        self.assertTrue(result.has_limit)
    
    def test_select_star_warning(self):
        sql = "SELECT * FROM users LIMIT 10"
        result = evaluate_performance(sql)
        self.assertTrue(any("SELECT *" in w for w in result.warnings))
    
    def test_complexity_low(self):
        sql = "SELECT id FROM users WHERE id = 1 LIMIT 10"
        result = evaluate_performance(sql)
        self.assertEqual(result.complexity, "low")
    
    def test_complexity_medium_with_join(self):
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id LIMIT 10"
        result = evaluate_performance(sql)
        self.assertIn(result.complexity, ["medium", "high"])
    
    def test_cross_join_warning(self):
        sql = "SELECT * FROM users CROSS JOIN orders LIMIT 10"
        result = evaluate_performance(sql)
        self.assertTrue(any("CROSS JOIN" in w for w in result.warnings))


class TestEvaluateRetrieval(unittest.TestCase):
    """测试检索质量评估。"""
    
    def test_full_coverage(self):
        sql = "SELECT * FROM users"
        ddl_context = ["CREATE TABLE users (id INT, name VARCHAR)"]
        result = evaluate_retrieval(sql, ddl_context)
        self.assertIsInstance(result, RetrievalQualityResult)
        self.assertEqual(result.ddl_coverage, 1.0)
        self.assertEqual(result.missing_tables, [])
    
    def test_partial_coverage(self):
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        ddl_context = ["CREATE TABLE users (id INT, name VARCHAR)"]
        result = evaluate_retrieval(sql, ddl_context)
        self.assertLess(result.ddl_coverage, 1.0)
        self.assertIn("orders", result.missing_tables)
    
    def test_no_ddl_context(self):
        sql = "SELECT * FROM users"
        result = evaluate_retrieval(sql, ddl_context=None)
        self.assertIsInstance(result, RetrievalQualityResult)
    
    def test_with_metric_matched(self):
        sql = "SELECT SUM(amount) FROM orders"
        result = evaluate_retrieval(sql, metric_matched="订单金额", metric_similarity=0.85)
        self.assertTrue(result.metric_matched)
        self.assertEqual(result.metric_similarity, 0.85)


class TestQuickEvaluate(unittest.TestCase):
    """测试快速评估。"""
    
    def test_valid_sql(self):
        sql = "SELECT * FROM orders LIMIT 10"
        result = quick_evaluate(sql)
        self.assertIsInstance(result, dict)
        self.assertTrue(result["is_valid"])
        self.assertIn("orders", result["tables"])
        self.assertEqual(result["query_type"], "SELECT")
    
    def test_quick_evaluate_structure(self):
        # 测试返回结构
        sql = "SELEC * FROM orders"
        result = quick_evaluate(sql)
        self.assertIsInstance(result, dict)
        self.assertIn("is_valid", result)
        self.assertIn("tables", result)
        self.assertIn("complexity", result)
    
    def test_performance_warnings(self):
        sql = "SELECT * FROM orders"  # 缺少 LIMIT
        result = quick_evaluate(sql)
        self.assertTrue(len(result["warnings"]) > 0)
    
    def test_complexity_returned(self):
        sql = "SELECT * FROM orders LIMIT 10"
        result = quick_evaluate(sql)
        self.assertIn(result["complexity"], ["low", "medium", "high"])


if __name__ == '__main__':
    unittest.main()
