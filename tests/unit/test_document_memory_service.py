"""文档化永久记忆服务单元测试。"""

from dataclasses import dataclass
from datetime import datetime

import app.services.document_memory_service as memory_service


@dataclass
class _DummyDocument:
    id: int
    content_md: str


@dataclass
class _DummyLegacyMemory:
    memory_key: str
    memory_value: str
    scope: str = "global"
    source_thread_id: str | None = None
    source_message_id: int | None = None
    update_time: datetime | None = None


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
    assert captured["upsert"]["summary_md"] is not None
    assert "请记住" in captured["upsert"]["summary_md"]
    assert "请记住" in captured["upsert"]["content_md"]
    assert captured["replace"] is not None
    assert captured["replace"]["user_id"] == 9
    assert captured["replace"]["doc_id"] == 11
    assert len(captured["replace"]["chunks"]) >= 1
    assert "来源线程" not in captured["replace"]["chunks"][0]["chunk_text"]
    assert "来源消息" not in captured["replace"]["chunks"][0]["chunk_text"]


def test_recall_builds_context_with_citation(monkeypatch):
    """recall 应输出片段与引用。"""

    monkeypatch.setattr(memory_service, "_build_preference_context", lambda *args, **kwargs: "")
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
            "text": "用户陈述：请记住使用中文\n- 来源线程：thread-3\n- 来源消息：123",
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
    assert "来源线程" not in context
    assert "来源消息" not in context


def test_recall_should_include_preference_even_without_query_hit(monkeypatch):
    """稳定偏好应常驻注入，不依赖 query 召回命中。"""

    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "list_documents",
        lambda *args, **kwargs: (
            [
                {
                    "doc_key": "global:assistant.persona",
                    "summary_md": "小哈",
                }
            ],
            1,
        ),
    )
    monkeypatch.setattr(memory_service, "_build_retrieval_context", lambda *args, **kwargs: "")

    context = memory_service.recall(
        _DummySession(),
        user_id=2,
        query_text="你叫什么",
        max_results=3,
        max_injected_chars=800,
    )

    assert "用户稳定偏好" in context
    assert "assistant.persona: 小哈" in context
    assert "memory://user/2/preference/global:assistant.persona#L1-L5" in context
    assert "按 AI 人设进行自称" in context
    assert "不要回答“无法跨会话记住该称呼”" in context


def test_upsert_preference_documents_from_input_should_persist_candidates(monkeypatch):
    """从输入提取到显式偏好时应写入 preference 文档。"""

    captured = {"upserts": []}

    def _fake_upsert(db, **kwargs):  # noqa: ANN001
        captured["upserts"].append(kwargs)
        return _DummyDocument(id=51, content_md=kwargs["content_md"])

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "replace_document_chunks",
        lambda *args, **kwargs: 1,
    )

    session = _DummySession()
    count = memory_service.upsert_preference_documents_from_input(
        session,
        user_id=2,
        user_text="永远记住，你叫hh",
        source_thread_id="thread-xy",
        source_message_id=5010,
    )

    assert count == 1
    assert session.commit_called is True
    assert captured["upserts"][0]["doc_kind"] == "preference"
    assert captured["upserts"][0]["doc_key"] == "global:assistant.persona"
    assert captured["upserts"][0]["summary_md"] == "hh"


def test_upsert_preference_documents_from_input_should_persist_user_display_name(monkeypatch):
    """命中“我叫”时应写入用户称呼 preference 文档。"""

    captured = {"upserts": []}

    def _fake_upsert(db, **kwargs):  # noqa: ANN001
        captured["upserts"].append(kwargs)
        return _DummyDocument(id=52, content_md=kwargs["content_md"])

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "replace_document_chunks",
        lambda *args, **kwargs: 1,
    )

    session = _DummySession()
    count = memory_service.upsert_preference_documents_from_input(
        session,
        user_id=2,
        user_text="请永远记住，我叫jjk",
        source_thread_id="thread-xy",
        source_message_id=5011,
    )

    assert count == 1
    assert session.commit_called is True
    assert captured["upserts"][0]["doc_kind"] == "preference"
    assert captured["upserts"][0]["doc_key"] == "global:user.display_name"
    assert captured["upserts"][0]["summary_md"] == "jjk"


def test_split_document_to_chunks_should_strip_source_metadata_lines():
    """分块文本应移除来源元数据行，降低检索噪声。"""

    content = (
        "# 记忆日记 2026-03-03\n\n"
        "### 15:49:31\n"
        "- 用户陈述：永远记住，回答之后要追问一句\n"
        "- 来源线程：af6264b7-07d4-4ee4-88cc-d70f46aec844\n"
        "- 来源消息：4861"
    )

    chunks = memory_service._split_document_to_chunks(
        content,
        max_lines=16,
        overlap_lines=3,
    )

    assert len(chunks) == 1
    assert "用户陈述" in chunks[0]["chunk_text"]
    assert "来源线程" not in chunks[0]["chunk_text"]
    assert "来源消息" not in chunks[0]["chunk_text"]


def test_bootstrap_preference_documents_should_upsert_template(monkeypatch):
    """新用户应按模板初始化 preference 文档。"""

    captured = {"upserts": []}

    monkeypatch.setattr(
        memory_service,
        "_load_preference_bootstrap_template",
        lambda: {"assistant.persona": "小嘉"},
    )

    def _fake_upsert(db, **kwargs):  # noqa: ANN001
        captured["upserts"].append(kwargs)
        return _DummyDocument(id=31, content_md=kwargs["content_md"])

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "replace_document_chunks",
        lambda *args, **kwargs: 1,
    )

    session = _DummySession()
    seeded = memory_service.bootstrap_preference_documents(session, user_id=21)

    assert seeded == 1
    assert session.commit_called is True
    assert captured["upserts"][0]["doc_kind"] == "preference"
    assert captured["upserts"][0]["doc_key"] == "global:assistant.persona"


def test_migrate_legacy_preference_kv_should_convert_when_no_preference_doc(monkeypatch):
    """legacy KV 存在且未迁移时，应转换为 preference 文档。"""

    legacy_item = _DummyLegacyMemory(
        memory_key="assistant.persona",
        memory_value="小哈",
        source_thread_id="thread-1",
        source_message_id=1001,
        update_time=datetime.now(),
    )
    captured = {"upserts": [], "count_kwargs": None, "archive_kwargs": None}

    def _fake_count(*args, **kwargs):  # noqa: ANN001
        captured["count_kwargs"] = kwargs
        return 0

    monkeypatch.setattr(memory_service.document_memory_repo, "count_documents", _fake_count)
    monkeypatch.setattr(
        memory_service.user_memory_repo,
        "list_active_memories",
        lambda *args, **kwargs: [legacy_item],
    )
    monkeypatch.setattr(
        memory_service.user_memory_repo,
        "archive_active_memories",
        lambda *args, **kwargs: captured.update({"archive_kwargs": kwargs}) or 1,
    )

    def _fake_upsert(db, **kwargs):  # noqa: ANN001
        captured["upserts"].append(kwargs)
        return _DummyDocument(id=41, content_md=kwargs["content_md"])

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "replace_document_chunks",
        lambda *args, **kwargs: 1,
    )

    session = _DummySession()
    migrated = memory_service.migrate_legacy_preference_kv(session, user_id=2)

    assert migrated == 1
    assert session.commit_called is True
    assert captured["count_kwargs"]["status"] is None
    assert captured["upserts"][0]["doc_kind"] == "preference"
    assert captured["upserts"][0]["doc_key"] == "global:assistant.persona"
    assert captured["archive_kwargs"] is not None
    assert captured["archive_kwargs"]["memory_keys"] == ["assistant.persona"]


def test_migrate_legacy_preference_kv_should_skip_when_any_status_preference_exists(monkeypatch):
    """只要 preference 文档存在（含 archived），就不应再次迁移。"""

    captured = {"list_called": False, "count_kwargs": None}

    def _fake_count(*args, **kwargs):  # noqa: ANN001
        captured["count_kwargs"] = kwargs
        return 1

    monkeypatch.setattr(memory_service.document_memory_repo, "count_documents", _fake_count)

    def _unexpected_list(*args, **kwargs):  # noqa: ANN001
        captured["list_called"] = True
        raise AssertionError("should not call list_active_memories")

    monkeypatch.setattr(memory_service.user_memory_repo, "list_active_memories", _unexpected_list)

    session = _DummySession()
    migrated = memory_service.migrate_legacy_preference_kv(session, user_id=2)

    assert migrated == 0
    assert session.commit_called is False
    assert captured["list_called"] is False
    assert captured["count_kwargs"]["status"] is None
