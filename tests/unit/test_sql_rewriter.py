"""SQL 重写器单元测试。"""
import unittest
from unittest.mock import patch, MagicMock
from app.ai.utils.permission_context import UserPermissionContext
from app.ai.utils.sql_rewriter import (
    rewrite_sql_with_permissions,
    _extract_table_qualifiers,
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

    @patch('app.ai.utils.sql_rewriter._load_table_columns_map')
    @patch('app.ai.utils.sql_rewriter.get_permission_service')
    def test_row_filter_injection_uses_alias_qualifier(self, mock_get_service, mock_load_columns):
        """测试行级过滤在表有别名时使用别名，避免 FROM-clause 报错。"""
        mock_service = MagicMock()
        mock_service.validate_query_context.return_value = (True, None)
        mock_service.check_table_access.return_value = (True, None)
        mock_service.get_row_filters_for_table.return_value = [("dept_code", "=", "DEPT001")]
        mock_service.get_masked_columns_for_table.return_value = {}
        mock_get_service.return_value = mock_service
        mock_load_columns.return_value = {("fdmdata", "orders"): {"dept_code", "bal"}}

        ctx = UserPermissionContext(
            user_id=1,
            data_role="staff",
            dept_code="DEPT001",
        )
        sql = "SELECT t.dept_code, SUM(t.bal) FROM fdmdata.orders t GROUP BY t.dept_code"

        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)

        self.assertTrue(allowed)
        self.assertIsNone(error)
        self.assertIn("t.dept_code = 'DEPT001'", rewritten)
        self.assertNotIn("orders.dept_code = 'DEPT001'", rewritten)

    @patch('app.ai.utils.sql_rewriter._load_table_columns_map')
    @patch('app.ai.utils.sql_rewriter.get_permission_service')
    def test_row_filter_injection_maps_compatible_column(self, mock_get_service, mock_load_columns):
        """测试过滤列不存在时自动映射到兼容字段。"""
        mock_service = MagicMock()
        mock_service.validate_query_context.return_value = (True, None)
        mock_service.check_table_access.return_value = (True, None)
        mock_service.get_row_filters_for_table.return_value = [("dept_cd", "=", "00808")]
        mock_service.get_masked_columns_for_table.return_value = {}
        mock_get_service.return_value = mock_service
        mock_load_columns.return_value = {("fdmdata", "f_mid_loan_tb"): {"org_cd", "data_dt", "prin_bal"}}

        ctx = UserPermissionContext(user_id=1, data_role="staff", dept_code="00808")
        sql = "SELECT l.data_dt, SUM(l.prin_bal) FROM fdmdata.f_mid_loan_tb l GROUP BY l.data_dt"

        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)

        self.assertTrue(allowed)
        self.assertIsNone(error)
        self.assertIn("l.org_cd = '00808'", rewritten)
        self.assertNotIn("dept_cd", rewritten)

    @patch('app.ai.utils.sql_rewriter._load_table_columns_map')
    @patch('app.ai.utils.sql_rewriter.get_permission_service')
    def test_row_filter_injection_rejects_when_no_compatible_column(self, mock_get_service, mock_load_columns):
        """测试过滤列缺失且无兼容字段时直接拒绝，避免 SQL 运行时报错。"""
        mock_service = MagicMock()
        mock_service.validate_query_context.return_value = (True, None)
        mock_service.check_table_access.return_value = (True, None)
        mock_service.get_row_filters_for_table.return_value = [("dept_cd", "=", "00808")]
        mock_service.get_masked_columns_for_table.return_value = {}
        mock_get_service.return_value = mock_service
        mock_load_columns.return_value = {("fdmdata", "f_mid_loan_tb"): {"data_dt", "prin_bal"}}

        ctx = UserPermissionContext(user_id=1, data_role="staff", dept_code="00808")
        sql = "SELECT l.data_dt, SUM(l.prin_bal) FROM fdmdata.f_mid_loan_tb l GROUP BY l.data_dt"

        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)

        self.assertFalse(allowed)
        self.assertEqual(rewritten, sql)
        self.assertIn("缺少过滤字段", error)
        self.assertIn("dept_cd", error)

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


class TestCTEExclusion(unittest.TestCase):
    """测试 CTE 名称排除逻辑。"""

    def test_extract_tables_excludes_cte_names(self):
        """CTE 名称不应被当作真实表。"""
        sql = """
        WITH params AS (SELECT DATE '2025-06-30' AS dt),
             cust_bal AS (SELECT * FROM fdmdata.f_mid_loan_tb)
        SELECT * FROM cust_bal
        """
        tables = _extract_tables_with_schema(sql)
        self.assertIn(("fdmdata", "f_mid_loan_tb"), tables)
        self.assertNotIn(("public", "params"), tables)
        self.assertNotIn(("public", "cust_bal"), tables)

    def test_extract_tables_no_cte(self):
        """无 CTE 的普通查询应正常提取。"""
        sql = "SELECT * FROM fdmdata.f_mid_loan_tb WHERE data_dt = '20250630'"
        tables = _extract_tables_with_schema(sql)
        self.assertEqual(len(tables), 1)
        self.assertIn(("fdmdata", "f_mid_loan_tb"), tables)

    def test_extract_tables_nested_cte(self):
        """嵌套 CTE 引用不应被当作真实表。"""
        sql = """
        WITH a AS (SELECT 1), b AS (SELECT * FROM a)
        SELECT * FROM fdmdata.f_mid_dep_tb, b
        """
        tables = _extract_tables_with_schema(sql)
        self.assertIn(("fdmdata", "f_mid_dep_tb"), tables)
        self.assertNotIn(("public", "a"), tables)
        self.assertNotIn(("public", "b"), tables)

    def test_cte_name_same_as_real_table_with_schema(self):
        """带 schema 的同名表不应被 CTE 排除误伤。"""
        sql = """
        WITH params AS (SELECT 1 AS x)
        SELECT * FROM fdmdata.params, params
        """
        tables = _extract_tables_with_schema(sql)
        # fdmdata.params 是真实表，应保留
        self.assertIn(("fdmdata", "params"), tables)
        # 无 schema 的 params 是 CTE 引用，应排除
        self.assertNotIn(("public", "params"), tables)

    def test_real_world_cte_sql(self):
        """真实场景：LLM 生成的贷款余额分布查询。"""
        sql = """
        WITH params AS (
            SELECT DATE '2025-06-30' AS data_dt
        ),
        cust_bal AS (
            SELECT l.org_cd, SUM(l.prin_bal) AS total_bal
            FROM fdmdata.f_mid_loan_tb l, params p
            WHERE l.data_dt = p.data_dt
            GROUP BY l.org_cd
        ),
        ranked AS (
            SELECT * FROM cust_bal ORDER BY total_bal DESC
        )
        SELECT * FROM ranked LIMIT 20
        """
        tables = _extract_tables_with_schema(sql)
        self.assertIn(("fdmdata", "f_mid_loan_tb"), tables)
        self.assertNotIn(("public", "params"), tables)
        self.assertNotIn(("public", "cust_bal"), tables)
        self.assertNotIn(("public", "ranked"), tables)

    def test_nested_cte_same_name_keeps_outer_real_table(self):
        """内层 CTE 同名不应遮蔽外层真实表。"""
        sql = """
        SELECT *
        FROM real_orders o
        JOIN (
          WITH real_orders AS (SELECT 1 AS id)
          SELECT * FROM real_orders
        ) x ON 1=1
        """
        tables = _extract_tables_with_schema(sql)
        self.assertIn(("public", "real_orders"), tables)
        qualifiers = _extract_table_qualifiers(sql)
        self.assertIn(("public", "real_orders"), qualifiers)


class TestCTEScopePermission(unittest.TestCase):
    """测试 CTE 作用域下的权限检查防回归。"""

    @patch('app.ai.utils.sql_rewriter.get_permission_service')
    def test_nested_cte_same_name_still_checks_outer_table_permission(self, mock_get_service):
        """外层真实表与内层 CTE 同名时，仍应命中外层表权限检查。"""
        mock_service = MagicMock()
        mock_service.validate_query_context.return_value = (True, None)

        def check_access(_, schema, table):
            if schema == "public" and table == "sensitive_table":
                return (False, "禁止访问 sensitive_table")
            return (True, None)

        mock_service.check_table_access.side_effect = check_access
        mock_service.get_row_filters_for_table.return_value = []
        mock_service.get_masked_columns_for_table.return_value = {}
        mock_get_service.return_value = mock_service

        ctx = UserPermissionContext(user_id=1, data_role="staff", dept_code="D001")
        sql = """
        SELECT *
        FROM sensitive_table s
        JOIN (
          WITH sensitive_table AS (SELECT 1 AS id)
          SELECT * FROM sensitive_table
        ) c ON 1=1
        """

        rewritten, allowed, error = rewrite_sql_with_permissions(sql, ctx)

        self.assertFalse(allowed)
        self.assertEqual(rewritten.strip(), sql.strip())
        self.assertIn("禁止访问 sensitive_table", error)


if __name__ == "__main__":
    unittest.main()
