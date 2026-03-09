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


def test_memories_list_should_return_items(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """记忆列表接口应返回分页数据。"""

    captured: dict[str, object] = {}

    def _fake_list_memories(*_args, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {
            "items": [
                {
                    "memory_id": 11,
                    "user_id": 1001,
                    "doc_kind": "daily",
                    "doc_key": "2026-03-01",
                    "title": "记忆日记 2026-03-01",
                    "summary_md": None,
                    "source": "memory",
                    "scope": "private",
                    "scope_ref": "thread-1",
                    "status": "active",
                    "decision_id": "decision-11",
                    "reason_code": "accepted",
                    "confidence": 0.93,
                    "memories_count": 2,
                    "rejected_items_count": 0,
                    "item_errors": [],
                    "revision": 2,
                    "chunk_total": 3,
                    "ready_chunks": 2,
                    "failed_chunks": 0,
                    "create_time": "2026-03-01T10:00:00",
                    "update_time": "2026-03-01T10:30:00",
                }
            ],
            "total": 1,
            "page": 2,
            "page_size": 10,
        }

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(memory_admin_api.memory_admin_service, "list_memories", _fake_list_memories)

    response = memory_admin_client.get(
        "/api/v1/memory-admin/memories",
        params={
            "user_id": 1001,
            "status": "active",
            "page": 2,
            "page_size": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["page"] == 2
    assert payload["items"][0]["memory_id"] == 11
    assert payload["items"][0]["decision_id"] == "decision-11"
    assert payload["items"][0]["confidence"] == pytest.approx(0.93)
    assert payload["items"][0]["reason_code"] == "accepted"
    assert captured["user_id"] == 1001
    assert captured["page"] == 2
    assert captured["page_size"] == 10


def test_memory_detail_should_return_payload(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """记忆详情接口应返回详情结构。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.memory_admin_service,
        "get_memory_detail",
        lambda *_args, **_kwargs: {
            "memory_id": 11,
            "user_id": 1001,
            "doc_kind": "daily",
            "doc_key": "2026-03-01",
            "title": "记忆日记 2026-03-01",
            "content_md": "# 记忆日记 2026-03-01",
            "summary_md": None,
            "source": "memory",
            "scope": "private",
            "scope_ref": "thread-1",
            "status": "active",
            "decision_id": "decision-11",
            "reason_code": "memory_batch_atomic_reject",
            "confidence": 0.88,
            "memories_count": 2,
            "rejected_items_count": 1,
            "item_errors": [
                {
                    "item_index": 1,
                    "slot_key": "custom.invalid.slot",
                    "reason_code": "slot_taxonomy_invalid",
                }
            ],
            "revision": 2,
            "source_thread_id": "thread-1",
            "source_message_id": 101,
            "chunk_total": 3,
            "ready_chunks": 2,
            "failed_chunks": 0,
            "create_time": "2026-03-01T10:00:00",
            "update_time": "2026-03-01T10:30:00",
        },
    )

    response = memory_admin_client.get(
        "/api/v1/memory-admin/memories/11",
        params={"user_id": 1001},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["memory_id"] == 11
    assert payload["content_md"].startswith("# 记忆日记")
    assert payload["decision_id"] == "decision-11"
    assert payload["reason_code"] == "memory_batch_atomic_reject"
    assert payload["rejected_items_count"] == 1
    assert payload["item_errors"][0]["reason_code"] == "slot_taxonomy_invalid"


def test_memory_detail_should_return_404_when_not_found(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """记忆详情不存在时应返回 404。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.memory_admin_service,
        "get_memory_detail",
        lambda *_args, **_kwargs: None,
    )

    response = memory_admin_client.get("/api/v1/memory-admin/memories/999", params={"user_id": 1001})

    assert response.status_code == 404
    assert response.json()["detail"] == "记忆不存在"


def test_memory_detail_chunks_should_return_items(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """记忆分块接口应返回分页数据。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.memory_admin_service,
        "get_memory_chunks",
        lambda *_args, **_kwargs: {
            "memory_id": 11,
            "user_id": 1001,
            "status": "active",
            "items": [
                {
                    "chunk_id": 1,
                    "doc_id": 11,
                    "user_id": 1001,
                    "chunk_no": 1,
                    "start_line": 1,
                    "end_line": 5,
                    "chunk_text": "foo",
                    "chunk_hash": "hash",
                    "embedding_status": "ready",
                    "embedding_retry_count": 0,
                    "embedding_model": "text-embedding-3-large",
                    "embedding_error": None,
                    "embedding_updated_time": "2026-03-01T10:20:00",
                    "source": "memory",
                    "create_time": "2026-03-01T10:00:00",
                    "update_time": "2026-03-01T10:20:00",
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 50,
        },
    )

    response = memory_admin_client.get(
        "/api/v1/memory-admin/memories/11/chunks",
        params={"user_id": 1001, "page": 1, "page_size": 50},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["memory_id"] == 11
    assert payload["items"][0]["embedding_status"] == "ready"


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


def test_search_debug_should_return_scores_and_citation(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """search-debug 应返回分数与引用。"""

    captured: dict[str, object] = {}

    def _fake_run_memory_search_debug(*_args, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {
            "user_id": 1001,
            "query_text": "退款进度",
            "total": 1,
            "items": [
                {
                    "doc_id": 11,
                    "doc_kind": "daily",
                    "doc_key": "2026-03-01",
                    "start_line": 3,
                    "end_line": 6,
                    "chunk_text": "用户询问退款进度",
                    "text_score": 0.52,
                    "vector_score": 0.81,
                    "final_score": 0.72,
                    "citation": "memory://user/1001/daily/2026-03-01#L3-L6",
                }
            ],
        }

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(memory_admin_api.memory_admin_service, "run_memory_search_debug", _fake_run_memory_search_debug)

    response = memory_admin_client.post(
        "/api/v1/memory-admin/memories/search-debug",
        json={
            "user_id": 1001,
            "query_text": "退款进度",
            "limit": 5,
            "min_score": 0.2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["final_score"] == pytest.approx(0.72)
    assert payload["items"][0]["citation"].startswith("memory://user/1001/")
    assert captured["max_results"] == 5


def test_archive_should_return_archived(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """archive 首次操作应返回 changed=true。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.memory_admin_service,
        "archive_memory",
        lambda *_args, **_kwargs: {
            "memory_id": 11,
            "status": "archived",
            "found": True,
            "changed": True,
        },
    )

    response = memory_admin_client.post(
        "/api/v1/memory-admin/memories/11/archive",
        params={"user_id": 1001},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "archived"
    assert payload["changed"] is True


def test_archive_should_be_idempotent(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """重复 archive 不应产生脏状态。"""

    state = {"called": 0}

    def _fake_archive_memory(*_args, **_kwargs):  # noqa: ANN001
        state["called"] += 1
        if state["called"] == 1:
            return {
                "memory_id": 11,
                "status": "archived",
                "found": True,
                "changed": True,
            }
        return {
            "memory_id": 11,
            "status": "archived",
            "found": True,
            "changed": False,
        }

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(memory_admin_api.memory_admin_service, "archive_memory", _fake_archive_memory)

    first = memory_admin_client.post("/api/v1/memory-admin/memories/11/archive")
    second = memory_admin_client.post("/api/v1/memory-admin/memories/11/archive")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["changed"] is True
    assert second.json()["changed"] is False
    assert second.json()["status"] == "archived"


def test_delete_should_return_deleted(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """delete 首次操作应返回 deleted=true。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.memory_admin_service,
        "delete_memory",
        lambda *_args, **_kwargs: {
            "memory_id": 11,
            "status": "deleted",
            "found": True,
            "deleted": True,
            "deleted_chunks": 3,
        },
    )

    response = memory_admin_client.delete(
        "/api/v1/memory-admin/memories/11",
        params={"user_id": 1001},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "deleted"
    assert payload["deleted"] is True
    assert payload["deleted_chunks"] == 3


def test_delete_should_be_idempotent(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """重复 delete 不应产生脏状态。"""

    state = {"called": 0}

    def _fake_delete_memory(*_args, **_kwargs):  # noqa: ANN001
        state["called"] += 1
        if state["called"] == 1:
            return {
                "memory_id": 11,
                "status": "deleted",
                "found": True,
                "deleted": True,
                "deleted_chunks": 2,
            }
        return {
            "memory_id": 11,
            "status": "missing",
            "found": False,
            "deleted": False,
            "deleted_chunks": 0,
        }

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(memory_admin_api.memory_admin_service, "delete_memory", _fake_delete_memory)

    first = memory_admin_client.delete("/api/v1/memory-admin/memories/11")
    second = memory_admin_client.delete("/api/v1/memory-admin/memories/11")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["deleted"] is True
    assert second.json()["deleted"] is False
    assert second.json()["deleted_chunks"] == 0


def test_embedding_status_should_support_dimension_grouping(
    memory_admin_client: TestClient,
    monkeypatch,
) -> None:  # noqa: ANN001
    """状态接口应支持按维度聚合。"""

    captured: dict[str, object] = {}

    def _fake_get_embedding_status_counts(*args, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {
            "total": 12,
            "pending": 2,
            "ready": 9,
            "failed": 1,
            "dimension": "user",
            "limit": 5,
            "offset": 1,
            "group_total": 2,
            "groups": [
                {
                    "user_id": 1001,
                    "document_total": 3,
                    "total": 7,
                    "pending": 1,
                    "ready": 6,
                    "failed": 0,
                },
                {
                    "user_id": 1002,
                    "document_total": 2,
                    "total": 5,
                    "pending": 1,
                    "ready": 3,
                    "failed": 1,
                },
            ],
        }

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.document_memory_repo,
        "get_embedding_status_counts",
        _fake_get_embedding_status_counts,
    )

    response = memory_admin_client.get(
        "/api/v1/memory-admin/document/embedding-status",
        params={"dimension": "user", "limit": 5, "offset": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dimension"] == "user"
    assert payload["group_total"] == 2
    assert payload["groups"][0]["user_id"] == 1001
    assert captured["dimension"] == "user"
    assert captured["limit"] == 5
    assert captured["offset"] == 1


def test_memory_overview_should_return_summary(memory_admin_client: TestClient, monkeypatch) -> None:  # noqa: ANN001
    """总览接口应返回规模与聚合统计。"""

    captured: dict[str, object] = {}

    def _fake_get_memory_overview_stats(*args, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {
            "totals": {
                "users": 2,
                "documents": 5,
                "chunks": 12,
            },
            "embedding_status": {
                "total": 12,
                "pending": 2,
                "ready": 9,
                "failed": 1,
            },
            "top_users": [
                {
                    "user_id": 1001,
                    "document_total": 3,
                    "total": 7,
                    "pending": 1,
                    "ready": 6,
                    "failed": 0,
                }
            ],
            "top_documents": [
                {
                    "doc_id": 501,
                    "user_id": 1001,
                    "doc_kind": "daily",
                    "doc_key": "2026-03-01",
                    "title": "日报",
                    "total": 4,
                    "pending": 1,
                    "ready": 3,
                    "failed": 0,
                }
            ],
        }

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.document_memory_repo,
        "get_memory_overview_stats",
        _fake_get_memory_overview_stats,
    )

    response = memory_admin_client.get(
        "/api/v1/memory-admin/memory-overview",
        params={"top_n": 8},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["totals"]["users"] == 2
    assert payload["embedding_status"]["ready"] == 9
    assert payload["top_users"][0]["user_id"] == 1001
    assert payload["top_documents"][0]["doc_id"] == 501
    assert captured["top_n"] == 8


def test_rebuild_embeddings_should_reject_when_admin_api_disabled(
    memory_admin_client: TestClient,
    monkeypatch,  # noqa: ANN001
) -> None:
    """管理开关关闭时应返回 409。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: False)

    response = memory_admin_client.post(
        "/api/v1/memory-admin/document/rebuild-embeddings",
        json={"user_id": 1001, "limit": 10, "run_async": True},
    )

    assert response.status_code == 409
    assert "ENABLE_DOCUMENT_MEMORY" in response.json()["detail"]


def test_retry_failed_async_should_return_processing_when_admin_enabled(
    memory_admin_client: TestClient,
    monkeypatch,  # noqa: ANN001
) -> None:
    """单开关开启时，异步重试应直接受理。"""

    monkeypatch.setattr(memory_admin_api, "_is_document_memory_admin_enabled", lambda: True)
    monkeypatch.setattr(
        memory_admin_api.document_memory_embedding_service,
        "retry_failed_chunks",
        lambda *args, **kwargs: 2,
    )

    response = memory_admin_client.post(
        "/api/v1/memory-admin/document/retry-failed",
        json={"user_id": 1001, "limit": 10, "run_async": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "processing"
    assert payload["reset"] == 2
