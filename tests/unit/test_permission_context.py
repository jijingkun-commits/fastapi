"""权限上下文单元测试。"""
import unittest
from app.ai.utils.permission_context import UserPermissionContext, PermissionCheckResult


class TestUserPermissionContext(unittest.TestCase):
    """测试 UserPermissionContext 类。"""
    
    def test_default_values(self):
        """测试默认值。"""
        ctx = UserPermissionContext(user_id=1)
        
        self.assertEqual(ctx.user_id, 1)
        self.assertEqual(ctx.role, "user")
        self.assertIsNone(ctx.org_code)
        self.assertIsNone(ctx.dept_code)
        self.assertEqual(ctx.allowed_schemas, [])
        self.assertEqual(ctx.allowed_tables, [])
        self.assertEqual(ctx.row_filters, {})
        self.assertEqual(ctx.masked_columns, {})
    
    def test_is_admin(self):
        """测试管理员判断。"""
        admin_ctx = UserPermissionContext(user_id=1, role="admin")
        user_ctx = UserPermissionContext(user_id=2, role="user")
        analyst_ctx = UserPermissionContext(user_id=3, role="analyst")
        
        self.assertTrue(admin_ctx.is_admin())
        self.assertFalse(user_ctx.is_admin())
        self.assertFalse(analyst_ctx.is_admin())
    
    def test_get_row_filter_value_org_code(self):
        """测试获取机构代码过滤值。"""
        ctx = UserPermissionContext(
            user_id=1,
            org_code="ORG001",
            dept_code="DEPT001"
        )
        
        self.assertEqual(ctx.get_row_filter_value("user.org_code"), "ORG001")
    
    def test_get_row_filter_value_dept_code(self):
        """测试获取部门代码过滤值。"""
        ctx = UserPermissionContext(
            user_id=1,
            org_code="ORG001",
            dept_code="DEPT001"
        )
        
        self.assertEqual(ctx.get_row_filter_value("user.dept_code"), "DEPT001")
    
    def test_get_row_filter_value_fixed(self):
        """测试固定值来源返回 None。"""
        ctx = UserPermissionContext(user_id=1, org_code="ORG001")
        
        self.assertIsNone(ctx.get_row_filter_value("fixed"))
        self.assertIsNone(ctx.get_row_filter_value("unknown"))
    
    def test_with_all_fields(self):
        """测试完整字段初始化。"""
        ctx = UserPermissionContext(
            user_id=1,
            role="analyst",
            org_code="ORG001",
            org_name="总行",
            dept_code="DEPT001",
            dept_name="风险部",
            allowed_schemas=["fdmdata", "sdmdata"],
            allowed_tables=["fdmdata.*", "sdmdata.dim_*"],
            denied_tables={"fdmdata.sensitive_table"},
            row_filters={"fdmdata.*": [("org_code", "=", "ORG001")]},
            masked_columns={"fdmdata.*.mobile": "partial"}
        )
        
        self.assertEqual(ctx.role, "analyst")
        self.assertEqual(len(ctx.allowed_schemas), 2)
        self.assertEqual(len(ctx.allowed_tables), 2)
        self.assertIn("fdmdata.sensitive_table", ctx.denied_tables)


class TestPermissionCheckResult(unittest.TestCase):
    """测试 PermissionCheckResult 类。"""
    
    def test_allowed_result(self):
        """测试允许的结果。"""
        result = PermissionCheckResult(allowed=True)
        
        self.assertTrue(result.allowed)
        self.assertIsNone(result.reason)
        self.assertIsNone(result.rewritten_sql)
    
    def test_denied_result(self):
        """测试拒绝的结果。"""
        result = PermissionCheckResult(
            allowed=False,
            reason="无权访问表 fdmdata.sensitive"
        )
        
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "无权访问表 fdmdata.sensitive")
    
    def test_rewritten_result(self):
        """测试带重写 SQL 的结果。"""
        result = PermissionCheckResult(
            allowed=True,
            rewritten_sql="SELECT * FROM users WHERE org_code = 'ORG001'"
        )
        
        self.assertTrue(result.allowed)
        self.assertIsNotNone(result.rewritten_sql)


if __name__ == "__main__":
    unittest.main()
