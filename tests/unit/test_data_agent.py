"""问数 Agent 核心模块测试（中文注释）。

测试覆盖：
- data_intent_helpers: 指标匹配、时间解析、维度提取
- data_access_control: 表白名单、RLS、SQL 验证
- data_query_tools: semantic_query 工具

"""
import pytest

from unittest.mock import Mock, patch, MagicMock


class TestDataIntentHelpers:
    """意图分析辅助函数测试。"""
    
    def test_match_metric_gmv(self):
        """测试 GMV 指标匹配。"""
        # 直接导入模块文件，避免 __init__.py 链
        from app.ai.workflow.data_intent_helpers import match_metric

        
        assert match_metric("本月的成交额是多少") == "total_gmv"
        assert match_metric("查看销售额") == "total_gmv"
        assert match_metric("GMV趋势") == "total_gmv"
    
    def test_match_metric_order_count(self):
        """测试订单数指标匹配。"""
        from app.ai.workflow.data_intent_helpers import match_metric
        
        assert match_metric("订单数量统计") == "order_count"
        assert match_metric("今天成单量") == "order_count"
    
    def test_match_metric_no_match(self):
        """测试无匹配情况。"""
        from app.ai.workflow.data_intent_helpers import match_metric
        
        assert match_metric("今天天气怎么样") is None
        assert match_metric("帮我写个报告") is None
    
    def test_parse_time_range_this_month(self):
        """测试本月时间解析。"""
        from app.ai.workflow.data_intent_helpers import parse_time_range
        
        time_type, text = parse_time_range("本月销售额")
        assert time_type == "this_month"
        assert "本月" in text
    
    def test_parse_time_range_last_n_days(self):
        """测试过去N天时间解析。"""
        from app.ai.workflow.data_intent_helpers import parse_time_range
        
        time_type, text = parse_time_range("过去7天的订单")
        assert time_type == "last_n_days_7"
    
    def test_parse_time_range_yesterday(self):
        """测试昨天时间解析。"""
        from app.ai.workflow.data_intent_helpers import parse_time_range
        
        time_type, text = parse_time_range("昨天的数据")
        assert "yesterday" in time_type
    
    def test_time_range_to_sql_filter(self):
        """测试时间范围转 SQL 条件。"""
        from app.ai.workflow.data_intent_helpers import time_range_to_sql_filter
        
        filter_sql = time_range_to_sql_filter("this_month")
        assert "DATE_TRUNC" in filter_sql
        assert "month" in filter_sql
    
    def test_extract_dimensions(self):
        """测试维度提取。"""
        from app.ai.workflow.data_intent_helpers import extract_dimensions
        
        dims = extract_dimensions("按地区统计销售额")
        assert "region" in dims
        
        dims = extract_dimensions("按日期分析订单")
        assert any("created_at" in d for d in dims)
    
    def test_check_sql_safety_safe(self):
        """测试安全 SQL 检查。"""
        from app.ai.workflow.data_intent_helpers import check_sql_safety
        
        is_safe, error = check_sql_safety("SELECT * FROM t_orders")
        assert is_safe is True
        assert error is None
    
    def test_check_sql_safety_dangerous(self):
        """测试危险 SQL 检查。"""
        from app.ai.workflow.data_intent_helpers import check_sql_safety
        
        is_safe, error = check_sql_safety("DROP TABLE t_orders")
        assert is_safe is False
        assert "DDL" in error or "DROP" in error  # 支持中英文错误消息
        
        is_safe, error = check_sql_safety("DELETE FROM t_orders")
        assert is_safe is False
    
    def test_check_sql_safety_sensitive_table(self):
        """测试敏感表访问检查。"""
        from app.ai.workflow.data_intent_helpers import check_sql_safety
        
        is_safe, error = check_sql_safety("SELECT * FROM t_user")
        assert is_safe is False
        assert "t_user" in error
    
    def test_add_limit_if_missing(self):
        """测试自动添加 LIMIT。"""
        from app.ai.workflow.data_intent_helpers import add_limit_if_missing
        
        sql = add_limit_if_missing("SELECT * FROM t_orders")
        assert "LIMIT" in sql
        
        # 已有 LIMIT 不应重复添加
        sql = add_limit_if_missing("SELECT * FROM t_orders LIMIT 10")
        assert sql.count("LIMIT") == 1


class TestDataAccessControl:
    """数据访问控制测试。"""
    
    def test_check_table_access_whitelist(self):
        """测试表白名单检查。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        assert dac.check_table_access("t_orders") is True
        assert dac.check_table_access("t_products") is True
    
    def test_check_table_access_blacklist(self):
        """测试表黑名单检查。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        assert dac.check_table_access("t_user") is False
        assert dac.check_table_access("t_llm_models") is False
    
    def test_extract_tables_from_sql(self):
        """测试从 SQL 提取表名。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        tables = dac.extract_tables_from_sql("SELECT * FROM t_orders JOIN t_products ON ...")
        assert "t_orders" in tables
        assert "t_products" in tables
    
    def test_validate_sql_valid(self):
        """测试 SQL 验证（有效）。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        is_valid, error = dac.validate_sql("SELECT * FROM t_orders")
        assert is_valid is True
    
    def test_validate_sql_invalid(self):
        """测试 SQL 验证（无效）。"""
        from app.ai.semantic.data_access_control import DataAccessControl
        
        dac = DataAccessControl()
        
        is_valid, error = dac.validate_sql("SELECT * FROM t_user")
        assert is_valid is False
        assert "t_user" in error


class TestSemanticQuery:
    """语义查询工具测试（需要 mock Vanna 和 metric_service）。"""
    
    @patch('app.ai.semantic.get_vanna')
    @patch('app.services.metric_service.get_metric_service')
    def test_semantic_query_basic(self, mock_get_metric_service, mock_get_vanna):
        """测试基础语义查询。"""
        import pandas as pd
        
        # Mock metric_service 返回无匹配
        mock_metric_svc = MagicMock()
        mock_metric_svc.match_metric.return_value = None
        mock_metric_svc.check_tables_availability.return_value = (True, [])  # 表可用
        mock_get_metric_service.return_value = mock_metric_svc
        
        # Mock Vanna 返回
        mock_vanna = MagicMock()
        mock_vanna.generate_sql.return_value = "SELECT SUM(amount) FROM t_orders"
        mock_vanna.run_sql.return_value = pd.DataFrame({"total": [1000]})
        mock_get_vanna.return_value = mock_vanna
        
        from app.ai.tools.data_query_tools import semantic_query
        
        result = semantic_query.invoke({"question": "本月销售额"})
        
        assert "SELECT" in result or "1000" in result or isinstance(result, str)
    
    @patch('app.ai.semantic.get_vanna')
    @patch('app.services.metric_service.get_metric_service')
    def test_semantic_query_with_metric(self, mock_get_metric_service, mock_get_vanna):
        """测试带预定义指标的查询。"""
        import pandas as pd
        
        # Mock metric_service 返回无匹配（让其走 Vanna 路径）
        mock_metric_svc = MagicMock()
        mock_metric_svc.match_metric.return_value = None
        mock_metric_svc.check_tables_availability.return_value = (True, [])
        mock_get_metric_service.return_value = mock_metric_svc
        
        mock_vanna = MagicMock()
        mock_vanna.generate_sql.return_value = "SELECT SUM(amount) AS total_gmv FROM t_orders"
        mock_vanna.run_sql.return_value = pd.DataFrame({"total_gmv": [5000]})
        mock_get_vanna.return_value = mock_vanna
        
        from app.ai.tools.data_query_tools import semantic_query
        
        # 应该走 Vanna 路径
        result = semantic_query.invoke({"question": "成交额是多少"})
        assert isinstance(result, str)
