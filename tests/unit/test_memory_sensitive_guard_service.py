"""用户记忆敏感信息拦截服务测试。"""

from __future__ import annotations

import app.services.memory_intent_llm_service as llm_service
from app.services.memory_sensitive_guard_service import MemorySensitiveGuardService


def _build_decision(**overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "level": "permanent",
        "category": "user_preference",
        "slot_key": "user.preference.coffee",
        "canonical_text": "用户偏好美式咖啡",
        "confidence": 0.93,
        "operation": "upsert",
        "reason": "",
        "source_span": "",
        "reverse_intent": False,
        "audit_reason": "accepted",
    }
    decision.update(overrides)
    return decision


def test_detect_should_hit_bank_card_number() -> None:
    """银行卡号命中后应返回敏感拦截。"""

    service = MemorySensitiveGuardService()

    result = service.detect(user_text="我的银行卡是 6222 0212 3456 7890")

    assert result["sensitive_hit"] is True
    assert result["reason"] == "bank_card_detected"


def test_detect_should_hit_password_assignment() -> None:
    """显式密码赋值语句应被识别为高敏。"""

    service = MemorySensitiveGuardService()

    result = service.detect(canonical_text="系统密码是Abc12345")

    assert result["sensitive_hit"] is True
    assert result["reason"] == "password_detected"


def test_detect_should_pass_for_normal_preference_text() -> None:
    """普通偏好描述不应误命中敏感规则。"""

    service = MemorySensitiveGuardService()

    result = service.detect(user_text="记住我喜欢拿铁，不喜欢太甜")

    assert result["sensitive_hit"] is False
    assert result["reason"] == "clean"


def test_apply_sensitive_guard_should_reject_sensitive_decision() -> None:
    """命中高敏规则后应直接降级为 none。"""

    decision = _build_decision(canonical_text="客户证件号 110101199001011234")

    guarded = llm_service.apply_sensitive_guard(decision, user_text="")

    assert guarded["level"] == "none"
    assert guarded["audit_reason"] == "sensitive_info_blocked"
    assert guarded["sensitive_hit"] is True
    assert guarded["reason"] == "id_number_detected"


def test_apply_reverse_intent_should_archive_when_slot_located() -> None:
    """reverse_intent 命中且可定位 slot 时，应转换为 archive。"""

    decision = _build_decision(
        reverse_intent=True,
        slot_key="user.preference.coffee",
        operation="upsert",
    )

    result = llm_service.apply_reverse_intent(decision)

    assert result["operation"] == "archive"
    assert result["audit_reason"] == "accepted"


def test_apply_reverse_intent_should_drop_when_slot_missing() -> None:
    """reverse_intent 命中但缺少 slot_key 时，应拒绝执行并降级。"""

    decision = _build_decision(reverse_intent=True, slot_key="")

    result = llm_service.apply_reverse_intent(decision)

    assert result["level"] == "none"
    assert result["audit_reason"] == "reverse_intent_slot_missing"
    assert result["reverse_intent"] is True


def test_apply_reverse_intent_should_only_audit_when_switch_disabled() -> None:
    """关闭 reverse_intent_enabled 后，应仅审计不执行 archive。"""

    decision = _build_decision(reverse_intent=True)

    result = llm_service.apply_reverse_intent(decision, reverse_intent_enabled=False)

    assert result["level"] == "none"
    assert result["audit_reason"] == "reverse_intent_disabled"
    assert result["reverse_intent"] is True

