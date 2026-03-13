"""文档记忆向量补偿脚本集成测试。"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

import scripts.memory.rebuild_document_embeddings as rebuild_script

import app.services.document_memory_embedding_service as embedding_service
import app.services.document_memory_service as memory_service


class _DummyDbContext:
    """伪造 DB 上下文。"""

    def __enter__(self):
        return "dummy-db"

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False


@dataclass
class _DummyDocument:
    id: int


@dataclass
class _DummyChunk:
    id: int
    user_id: int
    chunk_text: str
    embedding_model: str | None = None


class _DummySession:
    def __init__(self) -> None:
        self.commit_called = 0
        self.rollback_called = 0

    def commit(self) -> None:
        self.commit_called += 1

    def rollback(self) -> None:
        self.rollback_called += 1


def test_main_should_process_and_output_summary(monkeypatch, capsys) -> None:  # noqa: ANN001
    """脚本应调用补偿服务并输出 JSON 结果。"""

    captured: dict = {}

    monkeypatch.setattr(rebuild_script, "get_db_context", lambda: _DummyDbContext())

    def _fake_compensate_pending_embeddings(db, **kwargs):  # noqa: ANN001
        captured["db"] = db
        captured.update(kwargs)
        return {
            "total": 2,
            "processed": 2,
            "ready": 2,
            "failed": 0,
            "elapsed_ms": 15,
        }

    monkeypatch.setattr(
        rebuild_script.document_memory_embedding_service,
        "compensate_pending_embeddings",
        _fake_compensate_pending_embeddings,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rebuild_document_embeddings.py",
            "--limit",
            "10",
            "--user-id",
            "42",
            "--doc-id",
            "9",
            "--status",
            "pending, failed",
            "--max-retry",
            "5",
        ],
    )

    exit_code = rebuild_script.main()
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert payload["ready"] == 2
    assert captured["db"] == "dummy-db"
    assert captured["limit"] == 10
    assert captured["user_id"] == 42
    assert captured["doc_id"] == 9
    assert captured["status_filter"] == ["pending", "failed"]
    assert captured["max_retry"] == 5


def test_main_should_return_two_when_failed(monkeypatch, capsys) -> None:  # noqa: ANN001
    """脚本在有失败分块时应返回 2。"""

    captured: dict = {}

    monkeypatch.setattr(rebuild_script, "get_db_context", lambda: _DummyDbContext())

    def _fake_compensate_pending_embeddings(db, **kwargs):  # noqa: ANN001
        captured["db"] = db
        captured.update(kwargs)
        return {
            "total": 1,
            "processed": 1,
            "ready": 0,
            "failed": 1,
            "elapsed_ms": 20,
        }

    monkeypatch.setattr(
        rebuild_script.document_memory_embedding_service,
        "compensate_pending_embeddings",
        _fake_compensate_pending_embeddings,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rebuild_document_embeddings.py",
            "--limit",
            "0",
            "--status",
            "failed",
            "--max-retry",
            "-3",
        ],
    )

    exit_code = rebuild_script.main()
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 2
    assert payload["failed"] == 1
    assert captured["db"] == "dummy-db"
    assert captured["limit"] == 1
    assert captured["status_filter"] == ["failed"]
    assert captured["max_retry"] == 0


def test_flush_canonical_memory_should_persist_document_and_chunks(monkeypatch) -> None:  # noqa: ANN001
    """canonical_text 应写入 document/chunk，且 chunk 默认为 pending。"""

    captured: dict = {"upsert": None, "replace": None}

    monkeypatch.setattr(memory_service.document_memory_repo, "get_active_document", lambda *args, **kwargs: None)

    def _fake_upsert(db, **kwargs):  # noqa: ANN001
        captured["upsert"] = kwargs
        return _DummyDocument(id=88)

    def _fake_replace(db, **kwargs):  # noqa: ANN001
        captured["replace"] = kwargs
        return len(kwargs["chunks"])

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(memory_service.document_memory_repo, "replace_document_chunks", _fake_replace)

    session = _DummySession()
    persisted = memory_service.flush_canonical_memory(
        session,
        user_id=42,
        canonical_text="用户偏好美式咖啡",
        doc_kind="preference",
        slot_key="user.preference.coffee",
        source_thread_id="thread-42",
        source_message_id=4201,
    )

    assert persisted == 1
    assert session.commit_called == 1
    assert captured["upsert"] is not None
    assert captured["upsert"]["content_md"].find("canonical_text: 用户偏好美式咖啡") >= 0
    assert captured["upsert"]["summary_md"] == "用户偏好美式咖啡"
    assert captured["replace"] is not None
    assert captured["replace"]["doc_id"] == 88
    assert captured["replace"]["chunks"]
    assert captured["replace"]["chunks"][0]["embedding_status"] == "pending"
    assert "canonical_text" in captured["replace"]["chunks"][0]["chunk_text"]


def test_compensate_pending_embeddings_should_mark_ready(monkeypatch) -> None:  # noqa: ANN001
    """补偿入口应将 pending 分块推进到 ready。"""

    session = _DummySession()
    monkeypatch.setattr(
        embedding_service.document_memory_repo,
        "list_chunks_for_embedding",
        lambda *args, **kwargs: [_DummyChunk(id=7, user_id=42, chunk_text="用户偏好美式咖啡")],
    )
    monkeypatch.setattr(embedding_service, "get_embedding", lambda _text: [0.11, 0.22])

    updated: dict[str, list[int]] = {"ready": []}

    def _fake_mark_ready(db, **kwargs):  # noqa: ANN001
        updated["ready"].append(kwargs["chunk_id"])
        return True

    monkeypatch.setattr(embedding_service.document_memory_repo, "mark_chunk_embedding_ready", _fake_mark_ready)
    monkeypatch.setattr(
        embedding_service.document_memory_repo,
        "mark_chunk_embedding_failed",
        lambda *args, **kwargs: False,
    )

    summary = embedding_service.compensate_pending_embeddings(session, limit=10)

    assert summary["processed"] == 1
    assert summary["ready"] == 1
    assert summary["failed"] == 0
    assert updated["ready"] == [7]
    assert session.commit_called == 1
