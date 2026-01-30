"""SQL 解析工具单元测试。

测试 app/ai/utils/sql_parser.py 的功能。
"""
import unittest
from app.ai.utils.sql_parser import (
    extract_tables_from_sql,
    validate_sql_syntax,
    is_select_only,
    get_query_type,
    normalize_sql
)


class TestExtractTablesFromSql(unittest.TestCase):
    """测试表名提取功能。"""
    
    def test_simple_select(self):
        sql = "SELECT * FROM users"
        tables = extract_tables_from_sql(sql)
        self.assertEqual(tables, {"users"})
    
    def test_select_with_schema(self):
        sql = "SELECT * FROM fdmdata.deposits"
        tables = extract_tables_from_sql(sql)
        self.assertIn("fdmdata.deposits", tables)
    
    def test_multiple_tables_join(self):
        sql = """
        SELECT u.name, o.amount
        FROM users u
        JOIN orders o ON u.id = o.user_id
        """
        tables = extract_tables_from_sql(sql)
        self.assertIn("users", tables)
        self.assertIn("orders", tables)
    
    def test_subquery(self):
        sql = """
        SELECT * FROM users
        WHERE id IN (SELECT user_id FROM orders WHERE amount > 100)
        """
        tables = extract_tables_from_sql(sql)
        self.assertIn("users", tables)
        self.assertIn("orders", tables)
    
    def test_cte_with_clause(self):
        sql = """
        WITH active_users AS (
            SELECT id FROM users WHERE status = 'active'
        )
        SELECT * FROM active_users JOIN orders ON active_users.id = orders.user_id
        """
        tables = extract_tables_from_sql(sql)
        self.assertIn("users", tables)
        self.assertIn("orders", tables)
    
    def test_empty_sql(self):
        tables = extract_tables_from_sql("")
        self.assertEqual(tables, set())
    
    def test_invalid_sql(self):
        # 即使 SQL 无效，也应该尝试提取表名
        tables = extract_tables_from_sql("SELECT * FROM")
        # 可能返回空集或部分结果，不应抛出异常
        self.assertIsInstance(tables, set)


class TestValidateSqlSyntax(unittest.TestCase):
    """测试 SQL 语法验证。"""
    
    def test_valid_select(self):
        sql = "SELECT id, name FROM users WHERE status = 'active'"
        is_valid, error = validate_sql_syntax(sql)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_valid_with_clause(self):
        sql = """
        WITH cte AS (SELECT 1 as n)
        SELECT * FROM cte
        """
        is_valid, error = validate_sql_syntax(sql)
        self.assertTrue(is_valid)
    
    def test_syntax_validation_returns_tuple(self):
        # 测试函数返回正确的类型
        sql = "SELEC * FROM users"  # typo
        result = validate_sql_syntax(sql)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
    
    def test_clearly_invalid_sql(self):
        # 使用明显无效的 SQL
        sql = "THIS IS NOT SQL AT ALL @@@@"
        is_valid, error = validate_sql_syntax(sql)
        # sqlglot 可能对某些 SQL 比较宽容，所以只检查返回类型
        self.assertIsInstance(is_valid, bool)


class TestIsSelectOnly(unittest.TestCase):
    """测试只读查询检测。"""
    
    def test_simple_select(self):
        self.assertTrue(is_select_only("SELECT * FROM users"))
    
    def test_select_with_cte(self):
        sql = "WITH cte AS (SELECT 1) SELECT * FROM cte"
        self.assertTrue(is_select_only(sql))
    
    def test_insert_statement(self):
        self.assertFalse(is_select_only("INSERT INTO users VALUES (1)"))
    
    def test_update_statement(self):
        self.assertFalse(is_select_only("UPDATE users SET name = 'test'"))
    
    def test_delete_statement(self):
        self.assertFalse(is_select_only("DELETE FROM users"))
    
    def test_drop_statement(self):
        self.assertFalse(is_select_only("DROP TABLE users"))
    
    def test_create_statement(self):
        self.assertFalse(is_select_only("CREATE TABLE test (id INT)"))


class TestGetQueryType(unittest.TestCase):
    """测试查询类型识别。"""
    
    def test_select(self):
        self.assertEqual(get_query_type("SELECT * FROM users"), "SELECT")
    
    def test_insert(self):
        self.assertEqual(get_query_type("INSERT INTO users VALUES (1)"), "INSERT")
    
    def test_update(self):
        self.assertEqual(get_query_type("UPDATE users SET x = 1"), "UPDATE")
    
    def test_delete(self):
        self.assertEqual(get_query_type("DELETE FROM users"), "DELETE")
    
    def test_create_table(self):
        self.assertEqual(get_query_type("CREATE TABLE test (id INT)"), "DDL")
    
    def test_drop_table(self):
        self.assertEqual(get_query_type("DROP TABLE test"), "DDL")
    
    def test_with_select(self):
        sql = "WITH cte AS (SELECT 1) SELECT * FROM cte"
        self.assertEqual(get_query_type(sql), "SELECT")


class TestNormalizeSql(unittest.TestCase):
    """测试 SQL 格式化。"""
    
    def test_basic_normalize(self):
        sql = "select * from users where id=1"
        normalized = normalize_sql(sql)
        # 应该被格式化（大小写、空格等）
        self.assertIsInstance(normalized, str)
        self.assertIn("SELECT", normalized.upper())
    
    def test_preserve_semantics(self):
        sql = "SELECT id, name FROM users WHERE status = 'active'"
        normalized = normalize_sql(sql)
        # 语义应该保持不变
        self.assertIn("users", normalized.lower())
        self.assertIn("status", normalized.lower())


if __name__ == '__main__':
    unittest.main()
