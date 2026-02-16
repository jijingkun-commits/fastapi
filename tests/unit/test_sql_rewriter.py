"""SQL 重写器单元测试。"""
import unittest
from unittest.mock import patch, MagicMock
from app.ai.utils.permission_context import UserPermissionContext
from app.ai.utils.sql_rewriter import (
    rewrite_sql_with_permissions,
    _extract_tables_with_schema,
    _extract_tables_regex,
    _inject_where_clause_regex,
    _get_mask_expression,
)


class TestExtractTables(unittest.TestCase):
    """测试表名提取功能。"""
    
    def test_extract_simple_table(self):
        """测试简单表名提取。"""
        sql = "SELECT * FROM orders"
        tables = _extract_tables_regex(sql)
        
        self.assertEqual(len(tables), 1)
        self.assertIn(("public", "orders"), tables)
    
    def test_extract_schema_qualified_table(self):
        """测试带 Schema 的表名提取。"""
        sql = "SELECT * FROM fdmdata.f_mid_deposit"
        tables = _extract_tables_regex(sql)
        
        self.assertEqual(len(tables), 1)
        self.assertIn(("fdmdata", "f_mid_deposit"), tables)
    
    def test_extract_multiple_tables(self):
        """测试多表提取（JOIN）。"""
        sql = """
            SELECT a.*, b.name 
            FROM fdmdata.orders a 
            JOIN sdmdata.customers b ON a.customer_id = b.id
        """
        tables = _extract_tables_regex(sql)
        
        self.assertGreaterEqual(len(tables), 2)
        self.assertIn(("fdmdata", "orders"), tables)
        self.assertIn(("sdmdata", "customers"), tables)
    
    def test_extract_with_sqlglot(self):
        """测试 sqlglot 解析提取。"""
        sql = "SELECT * FROM fdmdata.orders WHERE id = 1"
        tables = _extract_tables_with_schema(sql)
        
        self.assertEqual(len(tables), 1)
        self.assertIn(("fdmdata", "orders"), tables)


class TestInjectWhereClause(unittest.TestCase):
    """测试 WHERE 条件注入。"""
    
    def test_inject_to_select_without_where(self):
        """测试向无 WHERE 的 SELECT 注入。"""
        sql = "SELECT * FROM orders"
        filter_clause = "org_code = 'ORG001'"
        
        result = _inject_where_clause_regex(sql, filter_clause)
        
        self.assertIn("WHERE", result.upper())
        self.assertIn("org_code = 'ORG001'", result)
    
    def test_inject_to_select_with_where(self):
        """测试向已有 WHERE 的 SELECT 注入。"""
        sql = "SELECT * FROM orders WHERE status = 'active'"
        filter_clause = "org_code = 'ORG001'"
        
        result = _inject_where_clause_regex(sql, filter_clause)
        
        self.assertIn("org_code = 'ORG001'", result)
        self.assertIn("status = 'active'", result)
        self.assertIn("AND", result.upper())
    
    def test_inject_before_group_by(self):
        """测试在 GROUP BY 前注入。"""
        sql = "SELECT dept, COUNT(*) FROM orders GROUP BY dept"
        filter_clause = "org_code = 'ORG001'"
        
        result = _inject_where_clause_regex(sql, filter_clause)
        
        self.assertIn("WHERE", result.upper())
        # WHERE 应该在 GROUP BY 之前
        where_pos = result.upper().find("WHERE")
        group_pos = result.upper().find("GROUP BY")
        self.assertLess(where_pos, group_pos)
    
    def test_inject_before_order_by(self):
        """测试在 ORDER BY 前注入。"""
        sql = "SELECT * FROM orders ORDER BY id"
        filter_clause = "org_code = 'ORG001'"
        
        result = _inject_where_clause_regex(sql, filter_clause)
        
        where_pos = result.upper().find("WHERE")
        order_pos = result.upper().find("ORDER BY")
        self.assertLess(where_pos, order_pos)
    
    def test_inject_before_limit(self):
        """测试在 LIMIT 前注入。"""
        sql = "SELECT * FROM orders LIMIT 10"
        filter_clause = "org_code = 'ORG001'"
        
        result = _inject_where_clause_regex(sql, filter_clause)
        
        where_pos = result.upper().find("WHERE")
        limit_pos = result.upper().find("LIMIT")
        self.assertLess(where_pos, limit_pos)


class TestMaskExpression(unittest.TestCase):
    """测试脱敏表达式生成。"""
    
    def test_hide_mask(self):
        """测试完全隐藏脱敏。"""
        expr = _get_mask_expression("mobile", "hide")
        self.assertEqual(expr, "'***'")
    
    def test_partial_mask(self):
        """测试部分脱敏。"""
        expr = _get_mask_expression("mobile", "partial")
        self.assertIn("CONCAT", expr)
        self.assertIn("LEFT", expr)
        self.assertIn("RIGHT", expr)
    
    def test_hash_mask(self):
        """测试哈希脱敏。"""
        expr = _get_mask_expression("id_card", "hash")
        self.assertIn("MD5", expr)
        self.assertIn("LEFT", expr)
    
    def test_unknown_mask_type(self):
        """测试未知脱敏类型默认隐藏。"""
        expr = _get_mask_expression("field", "unknown")
        self.assertEqual(expr, "'***'")


class TestRewriteSqlWithPermissions(unittest.TestCase):
    """测试完整的 SQL 权限重写。"""
    
    @patch('app.ai.utils.sql_rewriter.get_permission_service')
    def test_sys_admin_no_bypass(self, mock_get_service):
        """测试系统管理员不会绕过数据权限。"""
        mock_service = MagicMock()
        mock_service.validate_query_context.return_value = (True, None)
        mock_service.check_table_access.return_value = (False, "数据角色 staff 无权访问表 public.sensitive_table")
        mock_get_service.return_value = mock_service

        ctx = UserPermissionContext(user_id=1, data_role="staff", sys_role="admin", dept_code="D001")
        sql = "SELECT * FROM sensitive_table"

        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)

        self.assertFalse(allowed)
        self.assertIn("无权访问", error)
    
    def test_empty_sql(self):
        """测试空 SQL。"""
        ctx = UserPermissionContext(user_id=1, data_role="staff")
        
        rewritten, allowed, error = rewrite_sql_with_permissions("", ctx)
        
        self.assertFalse(allowed)
        self.assertIn("空", error)
    
    def test_whitespace_sql(self):
        """测试空白 SQL。"""
        ctx = UserPermissionContext(user_id=1, data_role="staff")
        
        rewritten, allowed, error = rewrite_sql_with_permissions("   ", ctx)
        
        self.assertFalse(allowed)
    
    @patch('app.ai.utils.sql_rewriter.get_permission_service')
    def test_table_access_denied(self, mock_get_service):
        """测试表访问被拒绝。"""
        mock_service = MagicMock()
        mock_service.validate_query_context.return_value = (True, None)
        mock_service.check_table_access.return_value = (False, "禁止访问 sensitive_table")
        mock_get_service.return_value = mock_service
        
        ctx = UserPermissionContext(user_id=1, data_role="staff")
        sql = "SELECT * FROM sensitive_table"
        
        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)
        
        self.assertFalse(allowed)
        self.assertIn("禁止访问", error)
    
    @patch('app.ai.utils.sql_rewriter.get_permission_service')
    def test_row_filter_injection(self, mock_get_service):
        """测试行级过滤注入。"""
        mock_service = MagicMock()
        mock_service.validate_query_context.return_value = (True, None)
        mock_service.check_table_access.return_value = (True, None)
        mock_service.get_row_filters_for_table.return_value = [("org_code", "=", "ORG001")]
        mock_service.get_masked_columns_for_table.return_value = {}
        mock_get_service.return_value = mock_service
        
        ctx = UserPermissionContext(
            user_id=1, 
            data_role="staff",
            dept_code="DEPT001",
            org_code="ORG001"
        )
        sql = "SELECT * FROM orders"
        
        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)
        
        self.assertTrue(allowed)
        self.assertIn("WHERE", rewritten.upper())
        self.assertIn("org_code", rewritten)
        self.assertIn("ORG001", rewritten)

    def test_default_dept_filter_injection(self):
        """测试默认 dept_code 隔离自动注入。"""
        ctx = UserPermissionContext(
            user_id=1,
            data_role="staff",
            dept_code="DEPT001",
            allowed_tables=["public.orders"],
        )
        sql = "SELECT * FROM orders"

        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)

        self.assertTrue(allowed)
        self.assertIsNone(error)
        self.assertIn("dept_code", rewritten)
        self.assertIn("DEPT001", rewritten)

    def test_missing_dept_code_rejected(self):
        """测试缺失 dept_code 时明确拒绝。"""
        ctx = UserPermissionContext(
            user_id=1,
            data_role="staff",
            allowed_tables=["public.orders"],
        )
        sql = "SELECT * FROM orders"

        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)

        self.assertFalse(allowed)
        self.assertEqual(rewritten, sql)
        self.assertIn("dept_code", error)


class TestEdgeCases(unittest.TestCase):
    """测试边界情况。"""
    
    def test_complex_sql_with_subquery(self):
        """测试包含子查询的复杂 SQL。"""
        sql = """
            SELECT * FROM orders 
            WHERE customer_id IN (
                SELECT id FROM customers WHERE region = 'EAST'
            )
        """
        tables = _extract_tables_regex(sql)
        
        # 应该提取到两个表
        self.assertGreaterEqual(len(tables), 2)
    
    def test_sql_with_alias(self):
        """测试带别名的 SQL。"""
        sql = "SELECT o.id FROM fdmdata.orders o"
        tables = _extract_tables_with_schema(sql)
        
        self.assertEqual(len(tables), 1)
        self.assertIn(("fdmdata", "orders"), tables)
    
    def test_case_insensitive_keywords(self):
        """测试关键字大小写不敏感。"""
        sql = "select * from Orders WHERE id = 1"
        tables = _extract_tables_regex(sql)
        
        self.assertEqual(len(tables), 1)


if __name__ == "__main__":
    unittest.main()
