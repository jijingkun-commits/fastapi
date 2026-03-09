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


def test_recall_should_prefer_structured_persona_over_legacy(monkeypatch):
    """结构化 assistant.persona.* 存在时，应抑制 legacy assistant.persona。"""

    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "list_documents",
        lambda *args, **kwargs: (
            [
                {
                    "doc_key": "assistant.persona.name",
                    "summary_md": "AAA",
                },
                {
                    "doc_key": "global:assistant.persona",
                    "summary_md": "hh",
                },
            ],
            2,
        ),
    )
    monkeypatch.setattr(memory_service, "_build_retrieval_context", lambda *args, **kwargs: "")

    context = memory_service.recall(
        _DummySession(),
        user_id=2,
        query_text="你叫什么",
        max_results=3,
        max_injected_chars=1200,
    )

    assert "assistant.persona.name: AAA" in context
    assert "memory://user/2/preference/assistant.persona.name#L1-L5" in context
    assert "assistant.persona: hh" not in context
    assert "global:assistant.persona" not in context
    assert "按 AI 人设进行自称" in context


def test_recall_should_emit_response_structure_guidance(monkeypatch):
    """命中 response.structure 偏好时应注入明确总分总模板约束。"""

    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "list_documents",
        lambda *args, **kwargs: (
            [
                {
                    "doc_key": "user.preference.response.structure",
                    "summary_md": "用户偏好用详细的总分总段落结构回答",
                }
            ],
            1,
        ),
    )
    monkeypatch.setattr(memory_service, "_build_retrieval_context", lambda *args, **kwargs: "")

    context = memory_service.recall(
        _DummySession(),
        user_id=2,
        query_text="你对vibe coding怎么看",
        max_results=3,
        max_injected_chars=1200,
    )

    assert "user.preference.response.structure: 用户偏好用详细的总分总段落结构回答" in context
    assert "格式要求：若本轮无冲突指令，回答应遵循 user.preference.response.structure 偏好。" in context
    assert "输出模板：先“总”（先给结论），再“分”（分点展开依据/细节），最后“总”（总结与下一步）。" in context


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


def test_flush_canonical_memory_atomic_batch_should_reject_partial_invalid_memories(monkeypatch):
    """atomic_batch 任一 item 非法时应整批拒绝且不落库。"""

    captured = {"upserts": 0, "replace": 0}

    def _fake_upsert(*args, **kwargs):  # noqa: ANN001, ARG001
        captured["upserts"] += 1
        return _DummyDocument(id=101, content_md=kwargs["content_md"])

    def _fake_replace(*args, **kwargs):  # noqa: ANN001, ARG001
        captured["replace"] += 1
        return 1

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(memory_service.document_memory_repo, "replace_document_chunks", _fake_replace)

    decision_contract = {
        "decision": "accept",
        "reason_code": "accepted",
        "confidence": 0.93,
        "memories": [
            {
                "memory_kind": "response_preference",
                "operation": "upsert",
                "slot_key": "user.preference.response_structure",
                "normalized_value": "conclusion_first",
                "canonical_text": "用户偏好先结论后分析",
                "evidence_span": "先给结论",
            },
            {
                "memory_kind": "response_preference",
                "operation": "upsert",
                "slot_key": "custom.invalid.slot",
                "normalized_value": "short",
                "canonical_text": "用户偏好回答简短",
                "evidence_span": "回答简短",
            },
        ],
        "audit": {"detector": "llm_primary", "decision_id": "decision-1001"},
    }

    session = _DummySession()
    count = memory_service.flush_canonical_memory(
        session,
        user_id=7,
        source_thread_id="thread-atomic",
        source_message_id=1001,
        decision_contract=decision_contract,
    )

    assert count == 0
    assert session.commit_called is False
    assert captured["upserts"] == 0
    assert captured["replace"] == 0
    assert decision_contract["decision"] == "reject"
    assert decision_contract["reason_code"] == "memory_batch_atomic_reject"
    assert decision_contract["audit"]["decision_id"] == "decision-1001"
    assert decision_contract["audit"]["rejected_items_count"] == 1
    assert decision_contract["audit"]["item_errors"][0]["reason_code"] == "slot_taxonomy_invalid"


def test_flush_canonical_memory_atomic_batch_should_normalize_response_and_domain_aliases(monkeypatch):
    """slot alias 映射后的记忆项应通过 atomic_batch 并落库。"""

    captured = {"upserts": []}

    def _fake_upsert(*args, **kwargs):  # noqa: ANN001, ARG001
        captured["upserts"].append(kwargs)
        return _DummyDocument(id=300 + len(captured["upserts"]), content_md=kwargs["content_md"])

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "replace_document_chunks",
        lambda *args, **kwargs: len(kwargs["chunks"]),
    )

    decision_contract = {
        "decision": "accept",
        "reason_code": "accepted",
        "confidence": 0.86,
        "memories": [
            {
                "memory_kind": "response_preference",
                "operation": "upsert",
                "slot_key": "response.format.structure",
                "normalized_value": "detailed_zong_fen_zong_paragraphs",
                "canonical_text": "用户偏好以详细的总分总结构回答",
                "evidence_span": "永远用详细的总分总段落方式回答",
            },
            {
                "memory_kind": "profile_fact",
                "operation": "upsert",
                "slot_key": "domain.fact.jiaxing_bank.founded_year",
                "normalized_value": "2000",
                "canonical_text": "嘉兴银行成立于2000年",
                "evidence_span": "嘉兴银行成立于2000年",
            },
        ],
        "audit": {"detector": "llm_primary", "decision_id": "decision-5226"},
    }

    session = _DummySession()
    count = memory_service.flush_canonical_memory(
        session,
        user_id=8,
        source_thread_id="thread-atomic",
        source_message_id=5226,
        decision_contract=decision_contract,
    )

    assert count == 2
    assert session.commit_called is True
    assert decision_contract["decision"] == "accept"
    assert decision_contract["audit"]["decision_id"] == "decision-5226"
    assert captured["upserts"][0]["doc_key"] == "user.preference.response_structure"
    assert captured["upserts"][1]["doc_key"] == "knowledge.important.jiaxing.bank.founded.year"


def test_flush_canonical_memory_atomic_batch_should_persist_all_memories(monkeypatch):
    """atomic_batch 全部合法时应一次提交并写入所有 item。"""

    captured = {"upserts": [], "replace": []}

    def _fake_upsert(*args, **kwargs):  # noqa: ANN001, ARG001
        captured["upserts"].append(kwargs)
        return _DummyDocument(id=200 + len(captured["upserts"]), content_md=kwargs["content_md"])

    def _fake_replace(*args, **kwargs):  # noqa: ANN001, ARG001
        captured["replace"].append(kwargs)
        return len(kwargs["chunks"])

    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _fake_upsert)
    monkeypatch.setattr(memory_service.document_memory_repo, "replace_document_chunks", _fake_replace)

    decision_contract = {
        "decision": "accept",
        "reason_code": "accepted",
        "confidence": 0.95,
        "memories": [
            {
                "memory_kind": "response_preference",
                "operation": "upsert",
                "slot_key": "user.preference.response_structure",
                "normalized_value": "conclusion_first",
                "canonical_text": "用户偏好先给结论",
                "evidence_span": "先给结论",
            },
            {
                "memory_kind": "response_preference",
                "operation": "upsert",
                "slot_key": "user.preference.response_length",
                "normalized_value": "short",
                "canonical_text": "用户偏好回答简短",
                "evidence_span": "简短一点",
            },
        ],
        "audit": {"detector": "llm_primary", "decision_id": "decision-1002"},
    }

    session = _DummySession()
    count = memory_service.flush_canonical_memory(
        session,
        user_id=8,
        source_thread_id="thread-atomic",
        source_message_id=1002,
        decision_contract=decision_contract,
    )

    assert count == 2
    assert session.commit_called is True
    assert len(captured["upserts"]) == 2
    assert len(captured["replace"]) == 2
    assert decision_contract["audit"]["memories_count"] == 2
    assert decision_contract["audit"]["rejected_items_count"] == 0


def test_flush_canonical_memory_archive_should_archive_active_slot_instead_of_upsert(monkeypatch):
    """archive 操作应真正归档活跃槽位，而不是继续写成 active 文档。"""

    captured = {"archive_calls": [], "upsert_called": False, "replace_called": False}

    class _CurrentDocument:
        id = 41
        revision = 3
        last_event_time = datetime(2026, 3, 8, 10, 0, 0)

    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "get_active_slot",
        lambda *args, **kwargs: _CurrentDocument(),
    )

    def _fake_archive_slot(*args, **kwargs):  # noqa: ANN001, ARG001
        captured["archive_calls"].append(kwargs)
        return {
            "found": True,
            "changed": True,
            "status": "archived",
            "revision": 3,
            "last_event_time": kwargs["event_time"],
            "operation": "archive",
        }

    def _unexpected_upsert(*args, **kwargs):  # noqa: ANN001, ARG001
        captured["upsert_called"] = True
        raise AssertionError("archive 不应走 upsert_document")

    def _unexpected_replace(*args, **kwargs):  # noqa: ANN001, ARG001
        captured["replace_called"] = True
        raise AssertionError("archive 不应重建 chunks")

    monkeypatch.setattr(memory_service.document_memory_repo, "archive_slot", _fake_archive_slot)
    monkeypatch.setattr(memory_service.document_memory_repo, "upsert_document", _unexpected_upsert)
    monkeypatch.setattr(memory_service.document_memory_repo, "replace_document_chunks", _unexpected_replace)

    session = _DummySession()
    count = memory_service.flush_canonical_memory(
        session,
        user_id=9,
        source_thread_id="thread-archive",
        source_message_id=2002,
        decision_contract={
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.91,
            "memories": [
                {
                    "memory_kind": "response_preference",
                    "operation": "archive",
                    "slot_key": "user.preference.response_structure",
                    "normalized_value": "detailed_zong_fen_zong_paragraphs",
                    "canonical_text": "用户不再偏好总分总结构回答",
                    "evidence_span": "忘记我的总分总回复风格",
                }
            ],
            "audit": {"detector": "llm_primary", "decision_id": "decision-2002"},
        },
    )

    assert count == 1
    assert session.commit_called is True
    assert captured["upsert_called"] is False
    assert captured["replace_called"] is False
    assert len(captured["archive_calls"]) == 1
    assert captured["archive_calls"][0]["doc_id"] == 41
    assert captured["archive_calls"][0]["user_id"] == 9
    assert captured["archive_calls"][0]["operation"] == "archive"
