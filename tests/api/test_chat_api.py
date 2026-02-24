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
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        try:
            with patch("app.repositories.chat_repo.get_messages_by_thread") as mock_get:
                mock_get.return_value = []
                response = client.get("/api/v1/chat/threads/nonexistent/messages")
                assert response.status_code == 200
                assert response.json() == []
        finally:
            app.dependency_overrides.clear()
    
    def test_get_messages_success(self):
        """测试成功获取消息列表。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        mock_msg = MagicMock()
        mock_msg.id = 1
        mock_msg.thread_id = "thread-1"
        mock_msg.role = "human"
        mock_msg.content_type = "text"
        mock_msg.content = "你好"
        mock_msg.extra_data = None
        mock_msg.title = None
        mock_msg.create_time = datetime.now()
        try:
            with patch("app.repositories.chat_repo.get_messages_by_thread") as mock_get:
                mock_get.return_value = [mock_msg]
                response = client.get("/api/v1/chat/threads/thread-1/messages")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["role"] == "human"
        finally:
            app.dependency_overrides.clear()

    def test_get_messages_normalizes_legacy_structured_content(self):
        """测试历史结构串会在接口层归一化为可读文本。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        mock_msg = MagicMock()
        mock_msg.id = 2
        mock_msg.thread_id = "thread-legacy"
        mock_msg.role = "ai"
        mock_msg.content_type = "markdown"
        mock_msg.content = "[{'type': 'text', 'text': '历史格式已归一化'}]"
        mock_msg.extra_data = {}
        mock_msg.title = None
        mock_msg.create_time = datetime.now()

        try:
            with patch("app.repositories.chat_repo.get_messages_by_thread") as mock_get, patch(
                "app.repositories.chat_repo.get_feedback_scores_batch"
            ) as mock_feedback:
                mock_get.return_value = [mock_msg]
                mock_feedback.return_value = {}

                response = client.get("/api/v1/chat/threads/thread-legacy/messages")
                assert response.status_code == 200

                data = response.json()
                assert len(data) == 1
                assert data[0]["content"] == "历史格式已归一化"
        finally:
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
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        try:
            with patch("app.repositories.chat_repo.delete_thread_with_assets") as mock_delete:
                mock_delete.return_value = {"messages": 5, "assets": 0}
                response = client.delete("/api/v1/chat/threads/thread-1")
                assert response.status_code == 200
                data = response.json()
                assert data["stats"]["messages"] == 5
        finally:
            app.dependency_overrides.clear()


class TestUpdateTitleAPI:
    """更新对话标题接口测试。"""
    
    def test_update_title_success(self):
        """测试成功更新标题。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        try:
            with patch("app.repositories.chat_repo.update_thread_title") as mock_update:
                mock_update.return_value = True
                response = client.patch(
                    "/api/v1/chat/threads/thread-1/title",
                    json={"title": "新标题"}
                )
                assert response.status_code == 200
                assert response.json()["title"] == "新标题"
        finally:
            app.dependency_overrides.clear()

    def test_update_title_not_found(self):
        """测试更新不存在的对话标题。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        try:
            with patch("app.repositories.chat_repo.update_thread_title") as mock_update:
                mock_update.return_value = False
                response = client.patch(
                    "/api/v1/chat/threads/nonexistent/title",
                    json={"title": "新标题"}
                )
                assert response.status_code == 404
        finally:
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


class TestCancelRunAPI:
    """运行时取消接口测试。"""

    def test_cancel_run_unauthorized(self):
        """未认证请求应返回 401。"""
        response = client.post("/api/v1/chat/runs/run-1/cancel", json={"reason": "user_cancelled"})
        assert response.status_code == 401

    def test_cancel_run_success(self):
        """取消 run 成功时返回 accepted 语义。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        with patch("app.api.v1.endpoints.chat_api.run_control_service.cancel_run") as mock_cancel, patch(
            "app.api.v1.endpoints.chat_api.cancel_checkpoint", new_callable=AsyncMock
        ) as mock_checkpoint:
            mock_cancel.return_value = MagicMock(
                accepted=True,
                run_id="run-1",
                thread_id="thread-1",
                status="stopping",
                idempotent=False,
                reason="user_cancelled",
            )

            response = client.post(
                "/api/v1/chat/runs/run-1/cancel",
                json={"reason": "user_cancelled", "cancel_mode": "soft"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["accepted"] is True
            assert data["run_id"] == "run-1"
            assert data["status"] == "stopping"
            mock_checkpoint.assert_awaited_once_with("thread-1", run_id="run-1")

        app.dependency_overrides.clear()

    def test_cancel_run_not_found(self):
        """取消不存在的 run 返回 404。"""
        from app.services.run_control_service import RunNotFoundError

        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        with patch("app.api.v1.endpoints.chat_api.run_control_service.cancel_run") as mock_cancel:
            mock_cancel.side_effect = RunNotFoundError("run 不存在: run-missing")

            response = client.post(
                "/api/v1/chat/runs/run-missing/cancel",
                json={"reason": "user_cancelled"},
            )

            assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_cancel_run_forbidden(self):
        """取消他人 run 返回 403。"""
        from app.services.run_control_service import RunPermissionDeniedError

        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        with patch("app.api.v1.endpoints.chat_api.run_control_service.cancel_run") as mock_cancel:
            mock_cancel.side_effect = RunPermissionDeniedError("无权限取消 run: run-locked")

            response = client.post(
                "/api/v1/chat/runs/run-locked/cancel",
                json={"reason": "user_cancelled"},
            )

            assert response.status_code == 403

        app.dependency_overrides.clear()
