"""认证 API 测试（中文注释）。

测试登录、获取用户信息等认证相关接口。
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.api.deps import get_current_user


client = TestClient(app)


class TestLoginAPI:
    """登录接口测试。"""
    
    def test_login_missing_credentials(self):
        """测试缺少凭据时返回 400。"""
        response = client.post("/api/v1/login", json={"password": "test123"})
        assert response.status_code == 400
        data = response.json()
        # 统一响应格式: {"code", "message", "data"}
        assert "username或mobile至少提供一个" in data.get("message", data.get("detail", ""))
    
    def test_login_invalid_credentials(self):
        """测试无效凭据时返回 401。"""
        with patch("app.api.v1.endpoints.auth.authenticate") as mock_auth:
            mock_auth.return_value = None
            response = client.post(
                "/api/v1/login", 
                json={"username": "testuser", "password": "wrongpass"}
            )
            assert response.status_code == 401
            data = response.json()
            assert "用户名或密码错误" in data.get("message", data.get("detail", ""))
    
    def test_login_success(self):
        """测试登录成功返回令牌。"""
        mock_user = MagicMock()
        mock_user.id = 1
        
        with patch("app.api.v1.endpoints.auth.authenticate") as mock_auth:
            mock_auth.return_value = mock_user
            response = client.post(
                "/api/v1/login", 
                json={"username": "testuser", "password": "correct"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
    
    def test_login_db_error(self):
        """测试数据库异常返回 500（不泄露细节）。"""
        with patch("app.api.v1.endpoints.auth.authenticate") as mock_auth:
            mock_auth.side_effect = Exception("DB connection failed")
            response = client.post(
                "/api/v1/login", 
                json={"username": "testuser", "password": "test123"}
            )
            assert response.status_code == 500
            data = response.json()
            assert "数据库连接失败或查询异常" in data.get("message", data.get("detail", ""))


class TestMeAPI:
    """获取当前用户接口测试。"""
    
    def test_me_unauthorized(self):
        """测试未认证时返回 401。"""
        response = client.get("/api/v1/me")
        assert response.status_code == 401
    
    def test_me_returns_configured_data_role_label(self):
        """测试配置存在时返回配置化数据角色文案。"""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.username = "manager"
        mock_user.mobile = "13900139000"
        mock_user.role = "user"
        mock_user.data_role = "department_gm"

        def override_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_current_user

        try:
            with patch(
                "app.api.v1.endpoints.auth.SystemConfigService.get",
                return_value={"department_gm": "部门总经理"},
            ):
                response = client.get("/api/v1/me")

            assert response.status_code == 200
            data = response.json()
            assert data["data_role"] == "department_gm"
            assert data["data_role_label"] == "部门总经理"
        finally:
            app.dependency_overrides.clear()

    def test_me_success(self):
        """测试认证成功返回用户信息。"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.mobile = "13800138000"
        mock_user.role = "user"
        mock_user.data_role = "staff"
        mock_user.created_at = None
        
        def override_current_user():
            return mock_user
        
        app.dependency_overrides[get_current_user] = override_current_user
        
        try:
            response = client.get("/api/v1/me")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["username"] == "testuser"
            assert data["data_role"] == "staff"
            assert data["data_role_label"] == "staff"
        finally:
            app.dependency_overrides.clear()
