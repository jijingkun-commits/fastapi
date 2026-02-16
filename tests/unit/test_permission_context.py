"""权限上下文单元测试。"""
import unittest
from app.ai.utils.permission_context import UserPermissionContext, PermissionCheckResult


class TestUserPermissionContext(unittest.TestCase):
    """测试 UserPermissionContext 类。"""
    
    def test_default_values(self):
        """测试默认值。"""
        ctx = UserPermissionContext(user_id=1)
        
        self.assertEqual(ctx.user_id, 1)
        self.assertEqual(ctx.role, "staff")
        self.assertEqual(ctx.data_role, "staff")
        self.assertTrue(ctx.default_dept_scope)
        self.assertIsNone(ctx.org_code)
        self.assertIsNone(ctx.dept_code)
        self.assertEqual(ctx.allowed_schemas, [])
        self.assertEqual(ctx.allowed_tables, [])
        self.assertEqual(ctx.row_filters, {})
        self.assertEqual(ctx.masked_columns, {})
    
    def test_is_admin(self):
        """测试管理员判断。"""
        admin_ctx = UserPermissionContext(user_id=1, data_role="admin")
        sys_admin_ctx = UserPermissionContext(user_id=2, data_role="staff", sys_role="admin")
        staff_ctx = UserPermissionContext(user_id=3, data_role="staff")

        self.assertTrue(admin_ctx.is_admin())
        self.assertFalse(sys_admin_ctx.is_admin())
        self.assertFalse(staff_ctx.is_admin())

    def test_data_role_priority(self):
        """测试 data_role 优先于兼容 role 字段。"""
        ctx = UserPermissionContext(user_id=1, role="legacy_user", data_role="staff")

        self.assertEqual(ctx.data_role, "staff")
        self.assertEqual(ctx.role, "staff")

    def test_fallback_to_role_when_data_role_missing(self):
        """测试 data_role 缺失时回退到 role。"""
        ctx = UserPermissionContext(user_id=1, role="department_gm")

        self.assertEqual(ctx.data_role, "department_gm")
        self.assertEqual(ctx.role, "department_gm")

    def test_has_dept_code(self):
        """测试部门编码存在性判断。"""
        has_dept_ctx = UserPermissionContext(user_id=1, dept_code="D001")
        no_dept_ctx = UserPermissionContext(user_id=2, dept_code="  ")

        self.assertTrue(has_dept_ctx.has_dept_code())
        self.assertFalse(no_dept_ctx.has_dept_code())
    
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
            data_role="department_gm",
            sys_role="admin",
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
        
        self.assertEqual(ctx.role, "department_gm")
        self.assertEqual(ctx.data_role, "department_gm")
        self.assertEqual(ctx.sys_role, "admin")
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
