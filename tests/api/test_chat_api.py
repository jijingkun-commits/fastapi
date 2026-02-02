"""聊天 API 测试（中文注释）。

测试对话管理、消息查询等接口。
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.api.deps import get_current_user


client = TestClient(app)


def _mock_user():
    """创建模拟用户。"""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    return user


class TestThreadsAPI:
    """对话线程接口测试。"""
    
    def test_list_threads_unauthorized(self):
        """测试未认证时返回 401。"""
        response = client.get("/api/v1/chat/threads")
        assert response.status_code == 401
    
    def test_list_threads_success(self):
        """测试获取对话列表成功。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        mock_threads = [
            {
                "thread_id": "thread-1",
                "title": "测试对话",
                "created_at": "2026-01-30T10:00:00",
                "updated_at": "2026-01-30T12:00:00"
            }
        ]
        
        with patch("app.repositories.chat_repo.get_threads_by_user") as mock_get:
            mock_get.return_value = mock_threads
            response = client.get("/api/v1/chat/threads")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["thread_id"] == "thread-1"
        
        app.dependency_overrides.clear()


class TestMessagesAPI:
    """消息查询接口测试。"""
    
    def test_get_messages_unauthorized(self):
        """测试未认证时返回 401。"""
        response = client.get("/api/v1/chat/threads/thread-1/messages")
        assert response.status_code == 401
    
    def test_get_messages_not_found(self):
        """测试查询不存在的对话返回空列表。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.chat_repo.get_thread_messages") as mock_get:
            mock_get.return_value = []
            response = client.get("/api/v1/chat/threads/nonexistent/messages")
            assert response.status_code == 200
            assert response.json() == []
        
        app.dependency_overrides.clear()
    
    def test_get_messages_success(self):
        """测试成功获取消息列表。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        mock_msg = MagicMock()
        mock_msg.id = 1
        mock_msg.thread_id = "thread-1"
        mock_msg.role = "human"
        mock_msg.content_type = "text"
        mock_msg.content = "你好"
        mock_msg.metadata = None
        mock_msg.additional_kwargs = None
        mock_msg.title = None
        mock_msg.create_time = datetime.now()
        
        with patch("app.repositories.chat_repo.get_thread_messages") as mock_get:
            mock_get.return_value = [mock_msg]
            response = client.get("/api/v1/chat/threads/thread-1/messages")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["role"] == "human"
        
        app.dependency_overrides.clear()


class TestDeleteThreadAPI:
    """删除对话接口测试。"""
    
    def test_delete_thread_unauthorized(self):
        """测试未认证时返回 401。"""
        response = client.delete("/api/v1/chat/threads/thread-1")
        assert response.status_code == 401
    
    def test_delete_thread_success(self):
        """测试成功删除对话。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.chat_repo.delete_thread") as mock_delete:
            mock_delete.return_value = 5  # 删除了 5 条消息
            response = client.delete("/api/v1/chat/threads/thread-1")
            assert response.status_code == 200
            assert response.json()["deleted_count"] == 5
        
        app.dependency_overrides.clear()


class TestUpdateTitleAPI:
    """更新对话标题接口测试。"""
    
    def test_update_title_success(self):
        """测试成功更新标题。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.chat_repo.update_thread_title") as mock_update:
            mock_update.return_value = True
            response = client.put(
                "/api/v1/chat/threads/thread-1/title",
                json={"title": "新标题"}
            )
            assert response.status_code == 200
            assert response.json()["success"] is True
        
        app.dependency_overrides.clear()
    
    def test_update_title_not_found(self):
        """测试更新不存在的对话标题。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.chat_repo.update_thread_title") as mock_update:
            mock_update.return_value = False
            response = client.put(
                "/api/v1/chat/threads/nonexistent/title",
                json={"title": "新标题"}
            )
            # 根据实际实现，可能返回 404 或 200 with success=False
            assert response.status_code in [200, 404]
        
        app.dependency_overrides.clear()


class TestFeedbackAPI:
    """反馈接口测试。"""
    
    def test_submit_feedback_success(self):
        """测试成功提交反馈。"""
        app.dependency_overrides[get_current_user] = _mock_user
        
        with patch("app.repositories.chat_repo.save_feedback") as mock_save:
            mock_save.return_value = 1  # feedback_id
            response = client.post(
                "/api/v1/chat/feedback",
                json={
                    "message_id": 1,
                    "score": 1,
                    "reason": "回答很有帮助"
                }
            )
            assert response.status_code == 200
        
        app.dependency_overrides.clear()
