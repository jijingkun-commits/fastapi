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
from app.models.chat_run import ChatRun


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

    def test_get_latest_thread_unauthorized(self):
        """测试未认证时获取最近会话返回 401。"""
        response = client.get("/api/v1/chat/threads/latest")
        assert response.status_code == 401

    def test_get_latest_thread_success(self):
        """测试获取最近会话成功。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        try:
            with patch("app.repositories.chat_repo.get_latest_thread_by_user") as mock_get_latest:
                mock_get_latest.return_value = {
                    "thread_id": "thread-latest-1",
                    "title": "最近会话",
                    "created_at": "2026-03-01T17:00:00",
                    "updated_at": "2026-03-01T17:05:00",
                }
                response = client.get("/api/v1/chat/threads/latest")
                assert response.status_code == 200
                assert response.json()["thread_id"] == "thread-latest-1"
        finally:
            app.dependency_overrides.clear()

    def test_get_latest_thread_empty(self):
        """测试用户无历史会话时返回 null。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        try:
            with patch("app.repositories.chat_repo.get_latest_thread_by_user") as mock_get_latest:
                mock_get_latest.return_value = None
                response = client.get("/api/v1/chat/threads/latest")
                assert response.status_code == 200
                assert response.json() is None
        finally:
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


    def test_get_messages_should_preserve_multimodal_blocks(self):
        """multimodal 历史消息应返回 block 数组，不应被打平成纯文本。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        mock_msg = MagicMock()
        mock_msg.id = 3
        mock_msg.thread_id = "thread-multimodal"
        mock_msg.role = "ai"
        mock_msg.content_type = "multimodal"
        mock_msg.content = '[{"type": "markdown", "data": {"text": "第一段"}}, {"type": "image", "data": {"url": "/api/v1/assets/proxy/ragflow/img-0", "source": "knowledge"}}]'
        mock_msg.extra_data = {}
        mock_msg.title = None
        mock_msg.create_time = datetime.now()

        try:
            with patch("app.repositories.chat_repo.get_messages_by_thread") as mock_get, patch(
                "app.repositories.chat_repo.get_feedback_scores_batch"
            ) as mock_feedback:
                mock_get.return_value = [mock_msg]
                mock_feedback.return_value = {}

                response = client.get("/api/v1/chat/threads/thread-multimodal/messages")
                assert response.status_code == 200

                data = response.json()
                assert len(data) == 1
                assert isinstance(data[0]["content"], list)
                assert data[0]["content"][0]["type"] == "markdown"
                assert data[0]["content"][1]["type"] == "image"
        finally:
            app.dependency_overrides.clear()

    def test_get_messages_should_compile_legacy_kb_images_into_multimodal_blocks(self):
        """legacy markdown + kb_images 应在接口层编译成 canonical blocks，前端不再参与 placeholder 编译。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db
        mock_msg = MagicMock()
        mock_msg.id = 4
        mock_msg.thread_id = "thread-legacy-kb"
        mock_msg.role = "ai"
        mock_msg.content_type = "markdown"
        mock_msg.content = "第一段 [IMG-0] 第二段"
        mock_msg.extra_data = {
            "kb_images": {
                "0": "/api/v1/assets/proxy/ragflow/img-0",
            }
        }
        mock_msg.title = None
        mock_msg.create_time = datetime.now()

        try:
            with patch("app.repositories.chat_repo.get_messages_by_thread") as mock_get, patch(
                "app.repositories.chat_repo.get_feedback_scores_batch"
            ) as mock_feedback:
                mock_get.return_value = [mock_msg]
                mock_feedback.return_value = {}

                response = client.get("/api/v1/chat/threads/thread-legacy-kb/messages")
                assert response.status_code == 200

                data = response.json()
                assert len(data) == 1
                assert data[0]["content_type"] == "multimodal"
                assert isinstance(data[0]["content"], list)
                assert data[0]["content"][1]["type"] == "image"
                assert data[0]["content"][1]["data"]["url"] == "/api/v1/assets/proxy/ragflow/img-0"
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


class TestStreamAPI:
    """流式对话接口测试。"""

    def test_stream_preflight_returns_409_for_same_thread_active_run(self):
        from app.services.run_control_service import ActiveRunExistsError

        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        with patch("app.api.v1.endpoints.chat_api.get_run_control_service") as mock_get_run_control_service, patch(
            "app.api.v1.endpoints.chat_api.sse_stream"
        ) as mock_sse_stream:
            mock_run_control_service = mock_get_run_control_service.return_value
            mock_run_control_service.is_enabled.return_value = True
            mock_run_control_service.create_run.side_effect = ActiveRunExistsError(thread_id="thread-dup", active_run_id="run-active")

            response = client.post(
                "/api/v1/chat/stream",
                json={"prompt": "hello", "thread_id": "thread-dup", "delay_ms": 0},
            )

            assert response.status_code == 409
            assert response.json()["message"]["error_code"] == "active_run_exists"
            assert response.json()["message"]["thread_id"] == "thread-dup"
            assert response.json()["message"]["run_id"] == "run-active"
            assert mock_sse_stream.call_count == 0

        app.dependency_overrides.clear()

    def test_stream_preflight_returns_429_for_parallel_limit(self):
        from app.services.run_control_service import ParallelLimitExceededError

        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        with patch("app.api.v1.endpoints.chat_api.get_run_control_service") as mock_get_run_control_service, patch(
            "app.api.v1.endpoints.chat_api.sse_stream"
        ) as mock_sse_stream:
            mock_run_control_service = mock_get_run_control_service.return_value
            mock_run_control_service.is_enabled.return_value = True
            mock_run_control_service.create_run.side_effect = ParallelLimitExceededError(active_count=3, limit=3)

            response = client.post(
                "/api/v1/chat/stream",
                json={"prompt": "hello", "thread_id": "thread-overflow", "delay_ms": 0},
            )

            assert response.status_code == 429
            assert response.json()["message"]["error_code"] == "parallel_limit_exceeded"
            assert response.json()["message"]["active_count"] == 3
            assert response.json()["message"]["limit"] == 3
            assert mock_sse_stream.call_count == 0

        app.dependency_overrides.clear()


class TestActiveRunsAPI:
    """active runs 查询接口测试。"""

    def test_active_runs_contract_returns_current_user_items(self):
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        with patch("app.api.v1.endpoints.chat_api.get_run_control_service") as mock_get_run_control_service:
            mock_run_control_service = mock_get_run_control_service.return_value
            mock_run_control_service.is_active_runs_query_enabled.return_value = True
            mock_run_control_service.list_active_runs_by_user.return_value = [
                MagicMock(
                    run_id="run-1",
                    thread_id="thread-1",
                    status="running",
                    updated_at=datetime(2026, 3, 8, 12, 0, 0),
                    last_activity_at=datetime(2026, 3, 8, 12, 0, 5),
                )
            ]

            response = client.get("/api/v1/chat/runs/active")

            assert response.status_code == 200
            data = response.json()
            assert list(data.keys()) == ["items", "active_count", "poll_hint_seconds", "server_time"]
            assert data["active_count"] == 1
            assert data["items"][0]["run_id"] == "run-1"
            assert data["items"][0]["thread_id"] == "thread-1"
            assert data["items"][0]["status"] == "running"
            assert "messages" not in data["items"][0]
            mock_run_control_service.list_active_runs_by_user.assert_called_once()

        app.dependency_overrides.clear()


class TestCancelRunAPI:
    """运行时取消接口测试。"""

    def test_cancel_run_unauthorized(self):
        """未认证请求应返回 401。"""
        response = client.post("/api/v1/chat/runs/run-1/cancel", json={"thread_id": "thread-1"})
        assert response.status_code == 401

    def test_cancel_run_success(self):
        """取消 run 成功时返回 accepted 语义。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        with patch("app.api.v1.endpoints.chat_api.get_run_control_service") as mock_get_run_control_service, patch(
            "app.api.v1.endpoints.chat_api.cancel_checkpoint", new_callable=AsyncMock
        ) as mock_checkpoint:
            mock_run_control_service = mock_get_run_control_service.return_value
            mock_run_control_service.cancel_run.return_value = MagicMock(
                accepted=True,
                run_id="run-1",
                thread_id="thread-1",
                status="stopped",
                idempotent=False,
                reason="user_cancelled",
            )

            response = client.post(
                "/api/v1/chat/runs/run-1/cancel",
                json={"thread_id": "thread-1"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["accepted"] is True
            assert data["run_id"] == "run-1"
            assert data["status"] == "stopped"
            mock_run_control_service.cancel_run.assert_called_once_with(
                run_id="run-1",
                requester_user_id=1,
                is_admin=False,
                reason="user_cancelled",
                cancel_mode="hard",
                thread_id="thread-1",
                db=mock_db,
            )
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

        with patch("app.api.v1.endpoints.chat_api.get_run_control_service") as mock_get_run_control_service:
            mock_run_control_service = mock_get_run_control_service.return_value
            mock_run_control_service.cancel_run.side_effect = RunNotFoundError("run 不存在: run-missing")

            response = client.post(
                "/api/v1/chat/runs/run-missing/cancel",
                json={"thread_id": "thread-missing"},
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

        with patch("app.api.v1.endpoints.chat_api.get_run_control_service") as mock_get_run_control_service:
            mock_run_control_service = mock_get_run_control_service.return_value
            mock_run_control_service.cancel_run.side_effect = RunPermissionDeniedError("无权限取消 run: run-locked")

            response = client.post(
                "/api/v1/chat/runs/run-locked/cancel",
                json={"thread_id": "thread-locked"},
            )

            assert response.status_code == 403

        app.dependency_overrides.clear()

    def test_multi_session_contract_matrix_cancel_missing_thread_id_returns_400(self):
        """cancel 请求缺少 thread_id 时固定返回 400。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        with patch("app.api.v1.endpoints.chat_api.get_run_control_service") as mock_get_run_control_service:
            mock_run_control_service = mock_get_run_control_service.return_value
            response = client.post("/api/v1/chat/runs/run-1/cancel", json={})

            assert response.status_code == 400
            assert mock_run_control_service.cancel_run.call_count == 0

        app.dependency_overrides.clear()

    def test_multi_session_contract_matrix_cancel_thread_mismatch_returns_400(self):
        """cancel 请求 thread_id 不匹配时固定返回 400。"""
        app.dependency_overrides[get_current_user] = _mock_user
        mock_db = MagicMock()

        def _mock_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _mock_get_db

        isolated_client = TestClient(app, raise_server_exceptions=False)
        with patch("app.api.v1.endpoints.chat_api.get_run_control_service") as mock_get_run_control_service:
            mock_run_control_service = mock_get_run_control_service.return_value
            mock_run_control_service.cancel_run.side_effect = ValueError("thread_id mismatch")

            response = isolated_client.post(
                "/api/v1/chat/runs/run-1/cancel",
                json={"thread_id": "thread-other"},
            )

            assert response.status_code == 400

        app.dependency_overrides.clear()


def test_multi_worker_active_runs_reads_directly_from_db(db_session):
    """active runs 接口应以 DB 为真理源，而非依赖本 worker 内存态。"""

    from app.services.run_control_service import get_run_control_service, reset_run_control_service

    app.dependency_overrides[get_current_user] = _mock_user

    def _mock_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _mock_get_db
    db_session.add(
        ChatRun(
            run_id="run-db-only",
            thread_id="thread-db",
            user_id=1,
            status="running",
            created_at=datetime(2026, 3, 8, 12, 0, 0),
            updated_at=datetime(2026, 3, 8, 12, 0, 1),
            last_activity_at=datetime(2026, 3, 8, 12, 0, 2),
        )
    )
    db_session.commit()

    run_control_service = get_run_control_service()

    try:
        with patch("app.api.v1.endpoints.chat_api.get_run_control_service", return_value=run_control_service), patch.object(
            run_control_service,
            "is_active_runs_query_enabled",
            return_value=True,
        ), patch.dict(run_control_service._runs, {}, clear=True), patch.dict(
            run_control_service._active_run_by_thread,
            {},
            clear=True,
        ):
            response = client.get("/api/v1/chat/runs/active")

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 1
        assert data["items"][0]["run_id"] == "run-db-only"
        assert data["items"][0]["thread_id"] == "thread-db"
        assert data["items"][0]["status"] == "running"
    finally:
        reset_run_control_service()
        app.dependency_overrides.clear()
