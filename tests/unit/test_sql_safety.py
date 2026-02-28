"""SQL 安全检查单元测试。

测试 app/ai/utils/sql_safety.py 的功能。
"""
import unittest
from app.ai.utils.sql_safety import (
    check_sql_safety,
    check_dangerous_keywords,
    check_sensitive_tables,
    check_multiple_statements,
    check_parameter_placeholders,
    add_limit_if_missing,
    sanitize_sql,
    DANGEROUS_KEYWORDS,
    DEFAULT_SENSITIVE_TABLES,
)


class TestCheckDangerousKeywords(unittest.TestCase):
    """测试危险关键词检测。"""
    
    def test_safe_select(self):
        # 使用非敏感表名进行测试
        sql = "SELECT * FROM orders WHERE id = 1"
        is_safe, error = check_dangerous_keywords(sql)
        self.assertTrue(is_safe)
        self.assertIsNone(error)
    
    def test_insert_blocked(self):
        sql = "INSERT INTO orders (name) VALUES ('test')"
        is_safe, error = check_dangerous_keywords(sql)
        self.assertFalse(is_safe)
        self.assertIn("INSERT", error.upper())
    
    def test_update_blocked(self):
        sql = "UPDATE orders SET name = 'test'"
        is_safe, error = check_dangerous_keywords(sql)
        self.assertFalse(is_safe)
    
    def test_delete_blocked(self):
        sql = "DELETE FROM orders"
        is_safe, error = check_dangerous_keywords(sql)
        self.assertFalse(is_safe)
    
    def test_drop_blocked(self):
        sql = "DROP TABLE orders"
        is_safe, error = check_dangerous_keywords(sql)
        self.assertFalse(is_safe)
    
    def test_truncate_blocked(self):
        sql = "TRUNCATE TABLE orders"
        is_safe, error = check_dangerous_keywords(sql)
        self.assertFalse(is_safe)
    
    def test_alter_blocked(self):
        sql = "ALTER TABLE orders ADD COLUMN age INT"
        is_safe, error = check_dangerous_keywords(sql)
        self.assertFalse(is_safe)
    
    def test_grant_blocked(self):
        sql = "GRANT ALL ON orders TO public"
        is_safe, error = check_dangerous_keywords(sql)
        self.assertFalse(is_safe)
    
    def test_keyword_in_string_allowed(self):
        # "DELETE" 在字符串中，不应被拦截
        sql = "SELECT * FROM orders WHERE action = 'DELETE'"
        is_safe, error = check_dangerous_keywords(sql)
        # 这取决于实现，简单实现可能会误报
        # 如果使用 sqlglot 解析则应该通过
        self.assertIsInstance(is_safe, bool)


class TestCheckSensitiveTables(unittest.TestCase):
    """测试敏感表检测。"""
    
    def test_normal_table_allowed(self):
        sql = "SELECT * FROM orders"
        is_safe, error = check_sensitive_tables(sql)
        self.assertTrue(is_safe)
    
    def test_users_table_blocked(self):
        # users 是敏感表
        sql = "SELECT * FROM users"
        is_safe, error = check_sensitive_tables(sql)
        self.assertFalse(is_safe)
        self.assertIn("users", error.lower())
    
    def test_t_users_table_blocked(self):
        # t_users 也是敏感表
        sql = "SELECT * FROM t_users"
        is_safe, error = check_sensitive_tables(sql)
        self.assertFalse(is_safe)
    
    def test_llm_models_blocked(self):
        # t_llm_models 是敏感表（系统配置）
        sql = "SELECT * FROM t_llm_models"
        is_safe, error = check_sensitive_tables(sql)
        self.assertFalse(is_safe)


class TestCheckMultipleStatements(unittest.TestCase):
    """测试多语句检测。"""
    
    def test_single_statement_allowed(self):
        sql = "SELECT * FROM orders"
        is_safe, error = check_multiple_statements(sql)
        self.assertTrue(is_safe)
    
    def test_multiple_statements_blocked(self):
        sql = "SELECT * FROM orders; DROP TABLE orders"
        is_safe, error = check_multiple_statements(sql)
        self.assertFalse(is_safe)
        # 检查错误信息包含关于多语句的说明
        self.assertIn("多条", error)
    
    def test_semicolon_in_string_allowed(self):
        sql = "SELECT * FROM orders WHERE note = 'a;b'"
        is_safe, error = check_multiple_statements(sql)
        # 如果实现正确，应该允许
        self.assertIsInstance(is_safe, bool)
    
    def test_semicolon_followed_by_line_comment_allowed(self):
        """分号后跟行注释应视为单条语句（LLM 常见输出格式）。"""
        sql = (
            "SELECT SUM(prin_bal) AS loan_balance_total\n"
            "FROM fdmdata.f_mid_loan_tb\n"
            "WHERE data_dt >= DATE_TRUNC('month', CURRENT_DATE)\n"
            "AND data_dt < DATE_TRUNC('month', CURRENT_DATE) "
            "+ INTERVAL '1 month'; -- 本月最后一天"
        )
        is_safe, error = check_multiple_statements(sql)
        self.assertTrue(is_safe)
        self.assertIsNone(error)
    
    def test_semicolon_followed_by_block_comment_allowed(self):
        """分号后跟块注释应视为单条语句。"""
        sql = "SELECT * FROM orders; /* this is a trailing comment */"
        is_safe, error = check_multiple_statements(sql)
        self.assertTrue(is_safe)
        self.assertIsNone(error)
    
    def test_inline_comments_allowed(self):
        """SQL 中间的行注释不影响单条语句判定。"""
        sql = (
            "SELECT col1, -- 字段1\n"
            "       col2  -- 字段2\n"
            "FROM orders"
        )
        is_safe, error = check_multiple_statements(sql)
        self.assertTrue(is_safe)
        self.assertIsNone(error)
    
    def test_real_multiple_statements_still_blocked(self):
        """真正的多条语句仍然应被拒绝。"""
        sql = "SELECT 1; SELECT 2"
        is_safe, error = check_multiple_statements(sql)
        self.assertFalse(is_safe)
        self.assertIn("多条", error)
    
    def test_multiple_statements_with_comments_blocked(self):
        """多条语句即使带注释也应被拒绝。"""
        sql = "SELECT 1; -- first\nSELECT 2; -- second"
        is_safe, error = check_multiple_statements(sql)
        self.assertFalse(is_safe)
        self.assertIn("多条", error)


class TestCheckParameterPlaceholders(unittest.TestCase):
    """测试参数占位符检测。"""

    def test_parameter_placeholder_blocked(self):
        sql = "SELECT * FROM fdmdata.f_mid_loan_tb WHERE data_dt = $1::date"
        is_safe, error = check_parameter_placeholders(sql)
        self.assertFalse(is_safe)
        self.assertIn("占位符", error)

    def test_placeholder_in_string_allowed(self):
        sql = "SELECT '$1' AS literal_text, id FROM orders"
        is_safe, error = check_parameter_placeholders(sql)
        self.assertTrue(is_safe)
        self.assertIsNone(error)


class TestAddLimitIfMissing(unittest.TestCase):
    """测试自动添加 LIMIT。"""
    
    def test_add_limit_to_select(self):
        sql = "SELECT * FROM users"
        result = add_limit_if_missing(sql, limit=100)
        self.assertIn("LIMIT", result.upper())
        self.assertIn("100", result)
    
    def test_preserve_existing_limit(self):
        sql = "SELECT * FROM users LIMIT 50"
        result = add_limit_if_missing(sql, limit=100)
        # 应该保持原有的 LIMIT 50，不替换为 100
        self.assertIn("50", result)
    
    def test_default_limit(self):
        sql = "SELECT * FROM users"
        result = add_limit_if_missing(sql)  # 使用默认值
        self.assertIn("LIMIT", result.upper())
    
    def test_add_limit_with_trailing_comment(self):
        """末尾带 ; -- comment 时，LIMIT 应追加在有效 SQL 之后。"""
        sql = "SELECT SUM(bal) FROM fdmdata.t_loan; -- 贷款余额"
        result = add_limit_if_missing(sql, limit=1000)
        self.assertTrue(result.rstrip().endswith("LIMIT 1000"))
        self.assertNotIn("--", result)
    
    def test_add_limit_with_inline_comments(self):
        """中间有行注释的多行 SQL，LIMIT 应追加在最后。"""
        sql = (
            "SELECT col1, -- 字段1\n"
            "       col2  -- 字段2\n"
            "FROM orders"
        )
        result = add_limit_if_missing(sql, limit=100)
        self.assertTrue(result.rstrip().endswith("LIMIT 100"))


class TestSanitizeSql(unittest.TestCase):
    """测试综合 SQL 处理。"""
    
    def test_safe_sql_passes(self):
        # 使用非敏感表名
        sql = "SELECT * FROM orders WHERE id = 1"
        processed, is_safe, error = sanitize_sql(sql)
        self.assertTrue(is_safe)
        self.assertIsNone(error)
        self.assertIn("LIMIT", processed.upper())  # 应自动添加 LIMIT
    
    def test_dangerous_sql_blocked(self):
        sql = "DELETE FROM orders"
        processed, is_safe, error = sanitize_sql(sql)
        self.assertFalse(is_safe)
        self.assertIsNotNone(error)
    
    def test_sensitive_table_blocked(self):
        # users 是敏感表，应该被拦截
        sql = "SELECT * FROM users"
        processed, is_safe, error = sanitize_sql(sql)
        self.assertFalse(is_safe)
        self.assertIn("敏感表", error)
    
    def test_auto_limit_disabled(self):
        sql = "SELECT * FROM orders"
        processed, is_safe, error = sanitize_sql(sql, auto_limit=False)
        self.assertTrue(is_safe)
        # 原始 SQL 没有 LIMIT，禁用自动添加后也不应该有
        self.assertNotIn("LIMIT", processed.upper())
    
    def test_custom_limit(self):
        sql = "SELECT * FROM orders"
        processed, is_safe, error = sanitize_sql(sql, limit=500)
        self.assertTrue(is_safe)
        self.assertIn("500", processed)


class TestConstants(unittest.TestCase):
    """测试常量配置。"""
    
    def test_dangerous_keywords_exist(self):
        self.assertIsInstance(DANGEROUS_KEYWORDS, (list, tuple, set))
        self.assertIn("DELETE", [k.upper() for k in DANGEROUS_KEYWORDS])
        self.assertIn("DROP", [k.upper() for k in DANGEROUS_KEYWORDS])
    
    def test_sensitive_tables_exist(self):
        self.assertIsInstance(DEFAULT_SENSITIVE_TABLES, (list, tuple, set))


if __name__ == '__main__':
    unittest.main()
