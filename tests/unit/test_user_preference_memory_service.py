"""用户偏好记忆服务单元测试。"""

from dataclasses import dataclass
from decimal import Decimal

import app.services.user_preference_memory_service as memory_service


def test_extract_explicit_preference_candidates_returns_rules_when_triggered():
    """命中触发词时，应提取白名单偏好。"""

    text = "请记住：以后都用中文回复，并且先给结论，尽量简短。"
    candidates = memory_service.extract_explicit_preference_candidates(text)

    candidate_map = {item.memory_key: item.memory_value for item in candidates}

    assert candidate_map["response.language"] == "zh-CN"
    assert candidate_map["response.structure"] == "conclusion_first"
    assert candidate_map["response.length"] == "short"


def test_extract_explicit_preference_candidates_supports_ai_persona():
    """命中触发词并包含称呼约束时，应提取 AI 人设偏好。"""

    text = "永久记住你叫“小哈”"
    candidates = memory_service.extract_explicit_preference_candidates(text)

    candidate_map = {item.memory_key: item.memory_value for item in candidates}

    assert candidate_map["assistant.persona"] == "小哈"


def test_extract_explicit_preference_candidates_ignores_non_trigger_text():
    """未命中触发词时，不应写入偏好。"""

    text = "中文回复就行，谢谢。"
    candidates = memory_service.extract_explicit_preference_candidates(text)

    assert candidates == []


@dataclass
class _DummyMemory:
    memory_key: str
    memory_value: str


class _DummySession:
    def __init__(self):
        self.commit_called = False
        self.rollback_called = False

    def commit(self):
        self.commit_called = True

    def rollback(self):
        self.rollback_called = True


def test_build_user_preference_context_formats_readable_lines(monkeypatch):
    """偏好上下文应使用可读标签输出。"""

    records = [
        _DummyMemory("response.language", "zh-CN"),
        _DummyMemory("response.length", "short"),
        _DummyMemory("assistant.persona", "小哈"),
    ]

    monkeypatch.setattr(
        memory_service.user_memory_repo,
        "list_active_memories",
        lambda db, user_id, scope, limit: records[:limit],
    )

    context = memory_service.build_user_preference_context(_DummySession(), user_id=7, max_items=3)

    assert "跨会话偏好" in context
    assert "回复语言: 中文" in context
    assert "回复长度: 简短" in context
    assert "AI人设: 小哈" in context
    assert "按 AI 人设进行自称" in context
    assert "不要回答“无法跨会话记住该称呼”" in context


def test_build_user_preference_context_dedupes_conflicting_keys(monkeypatch):
    """冲突 key 应按最近顺序去重，仅保留首条。"""

    records = [
        _DummyMemory("response.length", "short"),
        _DummyMemory("response.length", "detailed"),
        _DummyMemory("response.language", "zh-CN"),
    ]

    monkeypatch.setattr(
        memory_service.user_memory_repo,
        "list_active_memories",
        lambda db, user_id, scope, limit: records[:limit],
    )

    context = memory_service.build_user_preference_context(_DummySession(), user_id=7, max_items=8)

    assert "回复长度: 简短" in context
    assert "回复长度: 详细" not in context


def test_build_user_preference_context_compresses_when_too_long(monkeypatch):
    """上下文超阈值时应输出摘要压缩文本。"""

    records = [
        _DummyMemory("response.language", "zh-CN"),
        _DummyMemory("response.length", "short"),
        _DummyMemory("response.structure", "conclusion_first"),
        _DummyMemory("response.style", "professional"),
    ]

    monkeypatch.setattr(
        memory_service.user_memory_repo,
        "list_active_memories",
        lambda db, user_id, scope, limit: records[:limit],
    )

    context = memory_service.build_user_preference_context(
        _DummySession(),
        user_id=7,
        max_items=8,
        max_context_chars=42,
    )

    assert context.startswith("用户偏好摘要")
    assert "省略" in context
    assert len(context) <= 42


def test_build_user_preference_context_returns_empty_when_user_missing(monkeypatch):
    """无 user_id 时应直接返回空上下文，避免越权召回。"""

    called = {"list": False}

    def _fake_list(*args, **kwargs):
        called["list"] = True
        return []

    monkeypatch.setattr(memory_service.user_memory_repo, "list_active_memories", _fake_list)

    context = memory_service.build_user_preference_context(_DummySession(), user_id=0)

    assert context == ""
    assert called["list"] is False


def test_build_user_preference_context_recall_refreshes_last_seen(monkeypatch):
    """recall 命中后应刷新 last_seen 并提交事务。"""

    records = [
        _DummyMemory("response.language", "zh-CN"),
        _DummyMemory("response.length", "short"),
    ]
    touch_calls = []

    monkeypatch.setattr(
        memory_service.user_memory_repo,
        "list_active_memories",
        lambda db, user_id, scope, limit: records[:limit],
    )

    def _fake_touch(db, memories):
        touch_calls.append(list(memories))

    monkeypatch.setattr(memory_service.user_memory_repo, "touch_last_seen", _fake_touch)

    session = _DummySession()
    context = memory_service.recall(session, user_id=7, max_items=2)

    assert "跨会话偏好" in context
    assert len(touch_calls) == 1
    assert len(touch_calls[0]) == 2
    assert session.commit_called is True


def test_persist_explicit_preferences_from_input_upserts_all_candidates(monkeypatch):
    """持久化应按候选条数执行 upsert，并提交事务。"""

    captured = []

    def _fake_upsert(db, **kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(memory_service.user_memory_repo, "upsert_active_memory", _fake_upsert)

    session = _DummySession()
    count = memory_service.persist_explicit_preferences_from_input(
        session,
        user_id=9,
        user_text="记住：以后都用英文回复，并且默认详细一点。",
        source_thread_id="thread-1",
        source_message_id=1001,
    )

    assert count == 2
    assert session.commit_called is True
    assert {item["memory_key"] for item in captured} == {"response.language", "response.length"}
    assert all(isinstance(item["confidence"], Decimal) for item in captured)


def test_persist_explicit_preferences_from_input_flush_alias(monkeypatch):
    """flush 应复用 persist 逻辑并保持提交行为。"""

    captured = []

    def _fake_upsert(db, **kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(memory_service.user_memory_repo, "upsert_active_memory", _fake_upsert)

    session = _DummySession()
    count = memory_service.flush(
        session,
        user_id=9,
        user_text="记住：以后都用英文回复，并且默认详细一点。",
        source_thread_id="thread-1",
        source_message_id=1001,
    )

    assert count == 2
    assert session.commit_called is True
    assert {item["memory_key"] for item in captured} == {"response.language", "response.length"}


def test_normalize_controlled_memory_template_filters_unknown_keys():
    """初始化模板应只保留受控记忆项并规范化值。"""

    normalized = memory_service.normalize_controlled_memory_template(
        {
            "assistant.persona": "  小嘉。 ",
            "response.language": "中文",
            "unknown.key": "value",
            "response.length": "LONG",
        }
    )

    assert normalized == {
        "assistant.persona": "小嘉",
        "response.language": "zh-CN",
    }


def test_bootstrap_user_preferences_upserts_template(monkeypatch):
    """新用户初始化模板应写入受控记忆并提交事务。"""

    captured = []

    def _fake_upsert(db, **kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(memory_service.user_memory_repo, "upsert_active_memory", _fake_upsert)
    monkeypatch.setattr(
        "app.services.config_resolver.ConfigResolver.get_json_dict",
        lambda key, default: {"assistant.persona": "小嘉", "response.structure": "conclusion_first"},
    )

    session = _DummySession()
    count = memory_service.bootstrap_user_preferences(session, user_id=11)

    assert count == 2
    assert session.commit_called is True
    assert {item["memory_key"] for item in captured} == {"assistant.persona", "response.structure"}
    assert all(item["source_thread_id"] == "system.user_bootstrap" for item in captured)
