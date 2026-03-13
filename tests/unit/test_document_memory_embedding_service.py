"""文档记忆向量补偿服务测试。"""

from dataclasses import dataclass

import app.services.document_memory_embedding_service as embedding_service


@dataclass
class _Chunk:
    id: int
    user_id: int
    chunk_text: str
    embedding_model: str | None = None


class _DummySession:
    def __init__(self):
        self.commit_called = 0

    def commit(self):
        self.commit_called += 1


def test_compensate_pending_embeddings_should_mark_ready_and_failed(monkeypatch) -> None:  # noqa: ANN001
    """补偿任务应按结果分别更新 ready/failed。"""

    session = _DummySession()
    chunks = [
        _Chunk(id=1, user_id=9, chunk_text="first chunk"),
        _Chunk(id=2, user_id=9, chunk_text="second chunk"),
    ]
    monkeypatch.setattr(
        embedding_service.document_memory_repo,
        "list_chunks_for_embedding",
        lambda *args, **kwargs: chunks,
    )

    monkeypatch.setattr(
        embedding_service,
        "get_embedding",
        lambda text: [0.1, 0.2] if "first" in text else None,
    )

    stats = {"ready": [], "failed": []}

    def _mark_ready(db, **kwargs):  # noqa: ANN001
        stats["ready"].append(kwargs["chunk_id"])
        return True

    def _mark_failed(db, **kwargs):  # noqa: ANN001
        stats["failed"].append(kwargs["chunk_id"])
        return True

    monkeypatch.setattr(embedding_service.document_memory_repo, "mark_chunk_embedding_ready", _mark_ready)
    monkeypatch.setattr(embedding_service.document_memory_repo, "mark_chunk_embedding_failed", _mark_failed)

    summary = embedding_service.compensate_pending_embeddings(session, limit=10)

    assert summary["processed"] == 2
    assert summary["ready"] == 1
    assert summary["failed"] == 1
    assert stats["ready"] == [1]
    assert stats["failed"] == [2]
    assert session.commit_called == 1


def test_retry_failed_chunks_should_commit_when_rows_reset(monkeypatch) -> None:  # noqa: ANN001
    """重试失败分块后应提交事务。"""

    session = _DummySession()
    monkeypatch.setattr(
        embedding_service.document_memory_repo,
        "retry_failed_chunks",
        lambda *args, **kwargs: 3,
    )

    reset_count = embedding_service.retry_failed_chunks(session, limit=20)

    assert reset_count == 3
    assert session.commit_called == 1
