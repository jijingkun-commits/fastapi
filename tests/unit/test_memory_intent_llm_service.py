"""用户记忆意图 LLM 合同判定测试。"""

from __future__ import annotations

from dataclasses import dataclass

import app.services.memory_intent_llm_service as llm_service


@dataclass
class _Message:
    content: object


class _FakeLLM:
    def __init__(self, response: object, *, should_raise: bool = False):
        self._response = response
        self._should_raise = should_raise
        self.calls: list[str] = []

    def invoke(self, prompt: str):
        self.calls.append(prompt)
        if self._should_raise:
            raise RuntimeError("mock-llm-error")
        return self._response


def test_decide_should_accept_valid_contract_and_fill_optional_defaults() -> None:
    """合法合同应保留核心字段并补齐非核心默认值。"""

    llm = _FakeLLM(
        {
            "level": "permanent",
            "category": "user_preference",
            "slot_key": "user.preference.coffee",
            "canonical_text": "用户偏好美式咖啡",
            "confidence": 0.93,
        }
    )

    decision = llm_service.decide(llm=llm, user_text="记住我喜欢美式咖啡")

    assert decision["level"] == "permanent"
    assert decision["category"] == "user_preference"
    assert decision["slot_key"] == "user.preference.coffee"
    assert decision["canonical_text"] == "用户偏好美式咖啡"
    assert decision["confidence"] == 0.93
    assert decision["durability_score"] == 0.0
    assert decision["operation"] == "upsert"
    assert decision["source_span"] == ""
    assert decision["reverse_intent"] is False
    assert decision["audit_reason"] == "accepted"


def test_decide_should_parse_markdown_json_block() -> None:
    """模型输出 markdown json 代码块时也应能解析。"""

    llm = _FakeLLM(
        _Message(
            content=(
                "```json\n"
                "{\"level\":\"daily\",\"category\":\"profile_fact\","
                "\"slot_key\":\"user.profile.city\","
                "\"canonical_text\":\"用户常驻上海\",\"confidence\":0.9}\n"
                "```"
            )
        )
    )

    decision = llm_service.decide(llm=llm, user_text="我现在常住上海")

    assert decision["level"] == "daily"
    assert decision["category"] == "profile_fact"
    assert decision["slot_key"] == "user.profile.city"
    assert decision["audit_reason"] == "accepted"


def test_decide_should_downgrade_to_none_when_required_field_missing() -> None:
    """核心字段缺失时应降级为 none 并输出审计原因。"""

    llm = _FakeLLM(
        {
            "level": "permanent",
            "category": "user_preference",
            "slot_key": "user.preference.coffee",
            "confidence": 0.92,
        }
    )

    decision = llm_service.decide(llm=llm, user_text="记住我喜欢美式")

    assert decision["level"] == "none"
    assert decision["audit_reason"] == "contract_missing_required"


def test_decide_should_downgrade_to_none_when_enum_invalid() -> None:
    """level/category 枚举非法时应降级为 none。"""

    llm = _FakeLLM(
        {
            "level": "forever",
            "category": "user_preference",
            "slot_key": "user.preference.coffee",
            "canonical_text": "用户偏好美式咖啡",
            "confidence": 0.95,
        }
    )

    decision = llm_service.decide(llm=llm, user_text="记住我喜欢美式")

    assert decision["level"] == "none"
    assert decision["audit_reason"] == "contract_invalid_enum"


def test_decide_should_downgrade_to_none_when_confidence_below_threshold() -> None:
    """低于阈值时应降级为 none。"""

    llm = _FakeLLM(
        {
            "level": "permanent",
            "category": "user_preference",
            "slot_key": "user.preference.coffee",
            "canonical_text": "用户偏好美式咖啡",
            "confidence": 0.64,
        }
    )

    decision = llm_service.decide(llm=llm, user_text="记住我喜欢美式")

    assert decision["level"] == "none"
    assert decision["audit_reason"] == "low_confidence"


def test_decide_should_downgrade_to_none_when_canonical_text_is_template() -> None:
    """无信息模板句应被质量门禁拦截。"""

    llm = _FakeLLM(
        {
            "level": "daily",
            "category": "interaction_policy",
            "slot_key": "interaction.policy.reply_style",
            "canonical_text": "我记住了你喜欢这种方式",
            "confidence": 0.9,
        }
    )

    decision = llm_service.decide(llm=llm, user_text="以后说话简短一点")

    assert decision["level"] == "none"
    assert decision["audit_reason"] == "canonical_text_quality_failed"


def test_decide_should_downgrade_to_none_when_canonical_text_replays_user_text() -> None:
    """canonical_text 机械复述原句时应按 none 丢弃。"""

    llm = _FakeLLM(
        {
            "level": "daily",
            "category": "profile_fact",
            "slot_key": "user.profile.location",
            "canonical_text": "我现在住在上海",
            "confidence": 0.92,
        }
    )

    decision = llm_service.decide(llm=llm, user_text="我现在住在上海")

    assert decision["level"] == "none"
    assert decision["audit_reason"] == "canonical_text_quality_failed"


def test_decide_should_downgrade_to_none_when_llm_invoke_failed() -> None:
    """模型调用异常应可容错并降级为 none。"""

    llm = _FakeLLM(response={}, should_raise=True)

    decision = llm_service.decide(llm=llm, user_text="记住我喜欢美式")

    assert decision["level"] == "none"
    assert decision["audit_reason"] == "llm_invoke_failed"

