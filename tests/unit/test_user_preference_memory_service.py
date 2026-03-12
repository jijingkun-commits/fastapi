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


def test_extract_explicit_preference_candidates_supports_user_display_name():
    """命中触发词并包含“我叫”时，应提取用户称呼偏好。"""

    text = "请永远记住，我叫jjk"
    candidates = memory_service.extract_explicit_preference_candidates(text)

    candidate_map = {item.memory_key: item.memory_value for item in candidates}

    assert candidate_map["user.display_name"] == "jjk"


def test_extract_explicit_preference_candidates_supports_yongyuan_trigger():
    """“永远”应作为触发词，支持详细回复偏好提取。"""

    text = "永远给我详细的回答"
    candidates = memory_service.extract_explicit_preference_candidates(text)

    candidate_map = {item.memory_key: item.memory_value for item in candidates}

    assert candidate_map["response.length"] == "detailed"


def test_extract_explicit_preference_candidates_ignores_non_trigger_text():
    """未命中触发词时，不应写入偏好。"""

    text = "中文回复就行，谢谢。"
    candidates = memory_service.extract_explicit_preference_candidates(text)

    assert candidates == []


class _DummySession:
    def __init__(self):
        self.commit_called = False
        self.rollback_called = False

    def commit(self):
        self.commit_called = True

    def rollback(self):
        self.rollback_called = True


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
