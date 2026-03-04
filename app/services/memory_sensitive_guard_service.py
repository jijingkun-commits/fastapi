"""用户记忆敏感信息拦截服务（中文注释）。"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SensitiveRule:
    """敏感规则。"""

    rule_id: str
    reason: str
    pattern: re.Pattern[str]


_DEFAULT_RULES: tuple[SensitiveRule, ...] = (
    SensitiveRule(
        rule_id="id_number",
        reason="id_number_detected",
        pattern=re.compile(
            r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])"
            r"(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)"
        ),
    ),
    SensitiveRule(
        rule_id="bank_card",
        reason="bank_card_detected",
        pattern=re.compile(r"(?<!\d)(?:\d[\s-]?){16,19}(?!\d)"),
    ),
    SensitiveRule(
        rule_id="password",
        reason="password_detected",
        pattern=re.compile(
            r"(?:密码|password|passwd|pwd)\s*(?:是|为|:|=|is)\s*[^\s,，。]{4,}",
            flags=re.IGNORECASE,
        ),
    ),
    SensitiveRule(
        rule_id="verification_code",
        reason="verification_code_detected",
        pattern=re.compile(
            r"(?:验证码|校验码|otp|one[-\s]?time[-\s]?password)"
            r"\s*(?:是|为|:|=|is)?\s*\d{4,8}",
            flags=re.IGNORECASE,
        ),
    ),
)


class MemorySensitiveGuardService:
    """对记忆沉淀文本执行高敏命中检测。"""

    def __init__(
        self,
        *,
        rules: tuple[SensitiveRule, ...] = _DEFAULT_RULES,
        enabled: bool = True,
    ) -> None:
        self._rules = tuple(rules)
        self._enabled = bool(enabled)

    @staticmethod
    def _merge_text(user_text: str, canonical_text: str, source_span: str) -> str:
        parts = (
            str(user_text or "").strip(),
            str(canonical_text or "").strip(),
            str(source_span or "").strip(),
        )
        return "\n".join(part for part in parts if part)

    def detect(
        self,
        *,
        user_text: str = "",
        canonical_text: str = "",
        source_span: str = "",
    ) -> dict[str, object]:
        """检测是否命中高敏信息。"""

        if not self._enabled:
            return {
                "sensitive_hit": False,
                "reason": "guard_disabled",
                "rule_id": "",
            }

        merged_text = self._merge_text(
            user_text=user_text,
            canonical_text=canonical_text,
            source_span=source_span,
        )
        if not merged_text:
            return {
                "sensitive_hit": False,
                "reason": "empty_text",
                "rule_id": "",
            }

        for rule in self._rules:
            if rule.pattern.search(merged_text):
                return {
                    "sensitive_hit": True,
                    "reason": rule.reason,
                    "rule_id": rule.rule_id,
                }

        return {
            "sensitive_hit": False,
            "reason": "clean",
            "rule_id": "",
        }
