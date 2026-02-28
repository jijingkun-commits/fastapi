"""文档记忆后台管理 API 测试。"""

from typing import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.v1.endpoints import memory_admin_api
from app.db.session import get_db


@pytest.fixture
def memory_admin_client() -> Generator[TestClient, None, None]:
    """构造 memory-admin 测试客户端。"""

    app = FastAPI()
    app.include_router(memory_admin_api.router, prefix="/api/v1")

    def _override_get_db():
        yield object()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_rebuild_embeddings_async_should_return_processing(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """异步重建请求应返回 processing。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(memory_admin_api, "_is_embedding_worker_enabled", lambda: True)
    monkeypatch.setattr(memory_admin_api, "_run_embedding_rebuild_task", lambda **kwargs: None)
    monkeypatch.setattr(
        memory_admin_api.document_memory_repo,
        "count_embedding_candidates",
        lambda *args, **kwargs: 12,
    )

    response = memory_admin_client.post(
        "/api/v1/memory-admin/document/rebuild-embeddings",
        json={
            "user_id": 1001,
            "status_filter": ["pending"],
            "limit": 50,
            "run_async": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "processing"
    assert payload["total"] == 12


def test_embedding_status_should_return_counts(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """状态接口应返回统计信息。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.document_memory_embedding_service,
        "get_embedding_status",
        lambda *args, **kwargs: {
            "total": 20,
            "pending": 5,
            "ready": 13,
            "failed": 2,
        },
    )

    response = memory_admin_client.get(
        "/api/v1/memory-admin/document/embedding-status",
        params={"user_id": 1001},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 20,
        "pending": 5,
        "ready": 13,
        "failed": 2,
    }


def test_retry_failed_sync_should_return_completed(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """同步重试应返回 completed 与处理统计。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.document_memory_embedding_service,
        "retry_failed_chunks",
        lambda *args, **kwargs: 3,
    )
    monkeypatch.setattr(
        memory_admin_api.document_memory_embedding_service,
        "process_pending_chunks",
        lambda *args, **kwargs: {
            "total": 3,
            "processed": 3,
            "ready": 3,
            "failed": 0,
            "elapsed_ms": 12,
        },
    )

    response = memory_admin_client.post(
        "/api/v1/memory-admin/document/retry-failed",
        json={"user_id": 1001, "limit": 10, "run_async": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["reset"] == 3
    assert payload["ready"] == 3
