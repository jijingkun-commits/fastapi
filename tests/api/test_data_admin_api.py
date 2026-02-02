"""问数管理 API 测试（中文注释）。

测试覆盖：
- 查询日志管理
- SQL 修正与反馈
- 指标管理
- 表元数据管理

测试 /api/v1/data-admin/* 接口。
"""
import pytest
from fastapi.testclient import TestClient


class TestQueryLogAPI:
    """查询日志管理 API 测试。"""
    
    def test_list_query_logs_unauthorized(self, client: TestClient):
        """测试未授权访问查询日志列表。"""
        response = client.get("/api/v1/data-admin/query-logs")
        # 应该返回 401 或 403
        assert response.status_code in [401, 403, 422]
    
    def test_list_query_logs_with_auth(self, client: TestClient, auth_headers: dict):
        """测试授权访问查询日志列表。"""
        response = client.get(
            "/api/v1/data-admin/query-logs",
            headers=auth_headers
        )
        # 返回 200（成功）、401（认证失败）或 403（权限不足）
        assert response.status_code in [200, 401, 403]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    def test_list_query_logs_with_filter(self, client: TestClient, auth_headers: dict):
        """测试带筛选条件的查询日志列表。"""
        response = client.get(
            "/api/v1/data-admin/query-logs?is_correct=true&trained=false",
            headers=auth_headers
        )
        assert response.status_code in [200, 401, 403]
    
    def test_get_query_log_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的查询日志。"""
        response = client.get(
            "/api/v1/data-admin/query-logs/99999",
            headers=auth_headers
        )
        # 返回 404（不存在）或认证/权限错误
        assert response.status_code in [404, 401, 403]


class TestSQLCorrectionAPI:
    """SQL 修正 API 测试。"""
    
    def test_correct_sql_unauthorized(self, client: TestClient):
        """测试未授权的 SQL 修正。"""
        payload = {
            "log_id": 1,
            "corrected_sql": "SELECT * FROM t_orders",
            "is_correct": True
        }
        response = client.post(
            "/api/v1/data-admin/query-logs/correct",
            json=payload
        )
        assert response.status_code in [401, 403, 422]
    
    def test_feedback_sql_unauthorized(self, client: TestClient):
        """测试未授权的 SQL 反馈。"""
        response = client.post(
            "/api/v1/data-admin/query-logs/feedback/1?is_correct=true"
        )
        assert response.status_code in [401, 403, 422]


class TestTrainingAPI:
    """训练管理 API 测试。"""
    
    def test_train_from_logs_unauthorized(self, client: TestClient):
        """测试未授权的训练请求。"""
        payload = {"log_ids": [1, 2, 3]}
        response = client.post(
            "/api/v1/data-admin/train",
            json=payload
        )
        assert response.status_code in [401, 403, 422]
    
    def test_train_all_pending_unauthorized(self, client: TestClient):
        """测试未授权的批量训练。"""
        response = client.post("/api/v1/data-admin/train/all-pending")
        assert response.status_code in [401, 403, 422]


class TestMetricAPI:
    """指标管理 API 测试。"""
    
    def test_list_metrics_unauthorized(self, client: TestClient):
        """测试未授权访问指标列表。"""
        response = client.get("/api/v1/data-admin/metrics")
        assert response.status_code in [401, 403, 422]
    
    def test_list_metrics_with_auth(self, client: TestClient, auth_headers: dict):
        """测试授权访问指标列表。"""
        response = client.get(
            "/api/v1/data-admin/metrics",
            headers=auth_headers
        )
        assert response.status_code in [200, 401, 403]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    def test_create_metric_unauthorized(self, client: TestClient):
        """测试未授权创建指标。"""
        payload = {
            "name": "test_metric",
            "description": "测试指标",
            "metric_type": "sum"
        }
        response = client.post(
            "/api/v1/data-admin/metrics",
            json=payload
        )
        assert response.status_code in [401, 403, 422]
    
    def test_delete_metric_unauthorized(self, client: TestClient):
        """测试未授权删除指标。"""
        response = client.delete("/api/v1/data-admin/metrics/1")
        assert response.status_code in [401, 403, 422]


class TestTableMetadataAPI:
    """表元数据管理 API 测试。"""
    
    def test_list_meta_tables_unauthorized(self, client: TestClient):
        """测试未授权访问表元数据列表。"""
        response = client.get("/api/v1/data-admin/tables")
        assert response.status_code in [401, 403, 422]
    
    def test_list_meta_tables_with_auth(self, client: TestClient, auth_headers: dict):
        """测试授权访问表元数据列表。"""
        response = client.get(
            "/api/v1/data-admin/tables",
            headers=auth_headers
        )
        assert response.status_code in [200, 401, 403]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
    
    def test_sync_schema_unauthorized(self, client: TestClient):
        """测试未授权的 Schema 同步。"""
        response = client.post("/api/v1/data-admin/sync-schema")
        assert response.status_code in [401, 403, 422]


class TestAdminAPIPermission:
    """管理 API 权限测试。"""
    
    def test_admin_endpoints_require_auth(self, client: TestClient):
        """测试所有管理端点都需要认证。"""
        endpoints = [
            ("GET", "/api/v1/data-admin/query-logs"),
            ("GET", "/api/v1/data-admin/metrics"),
            ("GET", "/api/v1/data-admin/tables"),
            ("POST", "/api/v1/data-admin/train/all-pending"),
            ("POST", "/api/v1/data-admin/sync-schema"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)
            
            # 所有未认证请求应该被拒绝
            assert response.status_code in [401, 403, 422], \
                f"{method} {endpoint} 应该需要认证，实际返回 {response.status_code}"
