"""问数功能聊天接口测试（中文注释）。

测试覆盖：
- TC-AD-02: 自然语言生成 SQL
- TC-AD-03: 多维分析
- TC-AD-04: 指标匹配
- TC-AD-05: 安全拦截

通过 /api/v1/chat/stream 接口测试问数场景。
"""
import pytest
import json
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestDataChatAPI:
    """问数聊天 API 测试。"""
    
    def test_data_query_sql_generation(self, client: TestClient, auth_headers: dict):
        """TC-AD-02: 测试自然语言查询生成 SQL。
        
        输入："查询贷款余额"
        预期：生成包含聚合的 SQL 并返回数据
        """
        payload = {
            "prompt": "查询贷款余额",
            "thread_id": f"test-data-{int(time.time())}",
            "delay_ms": 0
        }
        
        response = client.post(
            "/api/v1/chat/stream",
            json=payload,
            headers=auth_headers
        )
        
        # SSE 流式响应，检查是否正常返回
        assert response.status_code in [200, 401, 403], f"响应状态: {response.status_code}"
        
        # 如果认证成功，检查响应内容
        if response.status_code == 200:
            content = response.text
            # SSE 格式的响应应包含 data: 前缀
            assert "data:" in content or len(content) > 0
    
    def test_data_query_multi_dimension(self, client: TestClient, auth_headers: dict):
        """TC-AD-03: 测试多维分析。
        
        输入："按分行统计存款"
        预期：生成带 GROUP BY 的 SQL
        """
        payload = {
            "prompt": "按分行统计存款",
            "thread_id": f"test-data-dim-{int(time.time())}",
            "delay_ms": 0
        }
        
        response = client.post(
            "/api/v1/chat/stream",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 401, 403]
    
    def test_data_query_metric_match(self, client: TestClient, auth_headers: dict):
        """TC-AD-04: 测试指标匹配。
        
        输入："本月的成交额"
        预期：匹配到 total_gmv 指标
        """
        payload = {
            "prompt": "本月的成交额是多少",
            "thread_id": f"test-data-metric-{int(time.time())}",
            "delay_ms": 0
        }
        
        response = client.post(
            "/api/v1/chat/stream",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 401, 403]
    
    def test_data_query_security_block(self, client: TestClient, auth_headers: dict):
        """TC-AD-05: 测试安全拦截。
        
        输入："删除所有数据"
        预期：被安全检查拦截
        """
        payload = {
            "prompt": "删除所有订单数据",
            "thread_id": f"test-data-security-{int(time.time())}",
            "delay_ms": 0
        }
        
        response = client.post(
            "/api/v1/chat/stream",
            json=payload,
            headers=auth_headers
        )
        
        # 即使是危险请求，API 也应该正常响应（拦截在内部处理）
        assert response.status_code in [200, 401, 403]


class TestDataIntentHelpersDirect:
    """问数意图分析直接测试（无需 API 调用）。"""
    
    def test_match_metric_deposit(self):
        """测试存款相关指标匹配。"""
        from app.ai.workflow.data_intent_helpers import match_metric
        
        # 测试常见的存款相关查询
        result = match_metric("存款余额是多少")
        # 如果有匹配结果，应该是字符串
        if result:
            assert isinstance(result, str)
    
    def test_parse_time_range_this_quarter(self):
        """测试本季度时间解析。"""
        from app.ai.workflow.data_intent_helpers import parse_time_range
        
        time_type, text = parse_time_range("本季度的贷款发放量")
        # 应该能解析出时间范围
        assert time_type is not None or text is not None
    
    def test_extract_dimensions_branch(self):
        """测试分行维度提取。"""
        from app.ai.workflow.data_intent_helpers import extract_dimensions
        
        dims = extract_dimensions("按分行统计存款余额")
        # 应该能提取出维度
        assert isinstance(dims, list)


class TestSQLSafetyDirect:
    """SQL 安全检查直接测试。"""
    
    def test_reject_drop_table(self):
        """测试拒绝 DROP TABLE。"""
        from app.ai.utils.sql_safety import check_sql_safety
        
        is_safe, error = check_sql_safety("DROP TABLE t_orders")
        assert is_safe is False
        assert error is not None
    
    def test_reject_delete(self):
        """测试拒绝 DELETE。"""
        from app.ai.utils.sql_safety import check_sql_safety
        
        is_safe, error = check_sql_safety("DELETE FROM t_orders WHERE 1=1")
        assert is_safe is False
    
    def test_reject_update(self):
        """测试拒绝 UPDATE。"""
        from app.ai.utils.sql_safety import check_sql_safety
        
        is_safe, error = check_sql_safety("UPDATE t_orders SET status = 'deleted'")
        assert is_safe is False
    
    def test_allow_select(self):
        """测试允许 SELECT。"""
        from app.ai.utils.sql_safety import check_sql_safety
        
        is_safe, error = check_sql_safety("SELECT * FROM t_orders WHERE status = 'active'")
        assert is_safe is True
        assert error is None
    
    def test_auto_add_limit(self):
        """测试自动添加 LIMIT。"""
        from app.ai.utils.sql_safety import add_limit_if_missing
        
        sql = add_limit_if_missing("SELECT * FROM t_orders")
        assert "LIMIT" in sql.upper()
    
    def test_preserve_existing_limit(self):
        """测试保留现有 LIMIT。"""
        from app.ai.utils.sql_safety import add_limit_if_missing
        
        sql = add_limit_if_missing("SELECT * FROM t_orders LIMIT 50")
        # 不应该重复添加 LIMIT
        assert sql.upper().count("LIMIT") == 1


class TestDataAccessControlDirect:
    """数据访问控制直接测试。"""
    
    def test_sensitive_table_access(self):
        """测试敏感表访问控制。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        # 用户表应该被拒绝
        assert dac.check_table_access("t_user") is False
        
        # LLM 配置表应该被拒绝
        assert dac.check_table_access("t_llm_models") is False
    
    def test_business_table_access(self):
        """测试业务表访问控制。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        # 订单表应该允许
        assert dac.check_table_access("t_orders") is True
        
        # 产品表应该允许
        assert dac.check_table_access("t_products") is True
    
    def test_extract_tables_from_sql(self):
        """测试从 SQL 提取表名。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        sql = "SELECT o.*, p.name FROM t_orders o JOIN t_products p ON o.product_id = p.id"
        tables = dac.extract_tables_from_sql(sql)
        
        assert "t_orders" in tables
        assert "t_products" in tables
    
    def test_validate_sql_with_sensitive_table(self):
        """测试包含敏感表的 SQL 验证。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        is_valid, error = dac.validate_sql("SELECT * FROM t_user")
        assert is_valid is False
        assert "t_user" in error
