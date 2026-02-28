"""文档化永久记忆服务单元测试。"""

from dataclasses import dataclass

import app.services.document_memory_service as memory_service


@dataclass
class _DummyDocument:
    id: int
    content_md: str


class _DummySession:
    def __init__(self):
        self.commit_called = False
        self.rollback_called = False

    def commit(self):
        self.commit_called = True

    def rollback(self):
        self.rollback_called = True


def test_flush_returns_zero_when_text_not_memory_candidate(monkeypatch):
    """未命中记忆触发条件时不应写入。"""

    called = {"upsert": False}

    def _never_call(*args, **kwargs):  # noqa: ANN001, ARG001
        called["upsert"] = True
        raise AssertionError("should not be called")

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _never_call)

    session = _DummySession()
    count = memory_service.flush(
        session,
        user_id=2,
        user_text="你好，今天帮我看看天气。",
        source_thread_id="thread-1",
        source_message_id=100,
    )

    assert count == 0
    assert called["upsert"] is False
    assert session.commit_called is False


def test_flush_persists_daily_document_and_chunks(monkeypatch):
    """命中触发条件时应写入文档并刷新分块。"""

    captured = {"upsert": None, "replace": None}

    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "get_active_document",
        lambda *args, **kwargs: None,
    )

    def _fake_upsert(db, **kwargs):  # noqa: ANN001
        captured["upsert"] = kwargs
        return _DummyDocument(id=11, content_md=kwargs["content_md"])

    def _fake_replace(db, **kwargs):  # noqa: ANN001
        captured["replace"] = kwargs
        return len(kwargs["chunks"])

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(memory_service.document_memory_repo, "replace_document_chunks", _fake_replace)

    session = _DummySession()
    count = memory_service.flush(
        session,
        user_id=9,
        user_text="请记住：我之后都要先结论后分析。",
        source_thread_id="thread-2",
        source_message_id=2001,
    )

    assert count == 1
    assert session.commit_called is True
    assert captured["upsert"] is not None
    assert captured["upsert"]["user_id"] == 9
    assert captured["upsert"]["doc_kind"] == "daily"
    assert "请记住" in captured["upsert"]["content_md"]
    assert captured["replace"] is not None
    assert captured["replace"]["user_id"] == 9
    assert captured["replace"]["doc_id"] == 11
    assert len(captured["replace"]["chunks"]) >= 1


def test_recall_builds_context_with_citation(monkeypatch):
    """recall 应输出片段与引用。"""

    monkeypatch.setattr(
        memory_service,
        "memory_search",
        lambda *args, **kwargs: [
            {
                "doc_id": 7,
                "doc_kind": "daily",
                "doc_key": "2026-02-28",
                "start_line": 3,
                "end_line": 5,
                "chunk_text": "用户陈述：请记住使用中文",
                "score": 0.8,
                "citation": "memory://user/2/daily/2026-02-28#L3-L5",
            }
        ],
    )
    monkeypatch.setattr(
        memory_service,
        "memory_get",
        lambda *args, **kwargs: {
            "text": "用户陈述：请记住使用中文\n来源线程：thread-3",
        },
    )

    context = memory_service.recall(
        _DummySession(),
        user_id=2,
        query_text="以后都用中文",
        max_results=3,
        max_injected_chars=800,
    )

    assert "用户长期记忆片段" in context
    assert "引用: memory://user/2/daily/2026-02-28#L3-L5" in context
