"""用户记忆意图 LLM 合同判定服务（中文注释）。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai.prompts.agent_prompts import MEMORY_INTENT_DECISION_PROMPT

logger = logging.getLogger(__name__)

_VALID_LEVELS = {"permanent", "daily", "none"}
_VALID_CATEGORIES = {
    "ai_persona",
    "user_preference",
    "important_knowledge",
    "profile_fact",
    "interaction_policy",
}
_TEMPLATE_PATTERNS = (
    "我记住了你",
    "我会记住你",
    "我已经记住",
)
_NONE_DEFAULTS: dict[str, Any] = {
    "level": "none",
    "category": "",
    "slot_key": "",
    "canonical_text": "",
    "confidence": 0.0,
    "durability_score": 0.0,
    "operation": "drop",
    "reason": "",
    "source_span": "",
    "reverse_intent": False,
}
_CORE_FIELDS = (
    "level",
    "category",
    "slot_key",
    "canonical_text",
    "confidence",
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return bool(default)


def _build_none_decision(audit_reason: str, *, reason: str = "") -> dict[str, Any]:
    decision = dict(_NONE_DEFAULTS)
    decision["reason"] = str(reason or "")
    decision["audit_reason"] = str(audit_reason)
    return decision


def _extract_json_object_from_text(raw_text: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if not text:
        raise ValueError("empty_output")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\\s*```$", "", text).strip()

    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("output_not_object")

    if last_error is not None:
        raise ValueError("invalid_json") from last_error
    raise ValueError("invalid_json")


def _coerce_contract_payload(raw_output: Any) -> dict[str, Any]:
    if isinstance(raw_output, dict):
        return raw_output

    if hasattr(raw_output, "model_dump"):
        dumped = raw_output.model_dump()
        if isinstance(dumped, dict):
            return dumped

    content = getattr(raw_output, "content", None)
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        pieces: list[str] = []
        for item in content:
            if isinstance(item, str):
                pieces.append(item)
                continue
            if isinstance(item, dict):
                text_part = item.get("text")
                if isinstance(text_part, str):
                    pieces.append(text_part)
        return _extract_json_object_from_text("\n".join(piece for piece in pieces if piece))
    if isinstance(content, str):
        return _extract_json_object_from_text(content)

    if isinstance(raw_output, str):
        return _extract_json_object_from_text(raw_output)

    raise ValueError("unsupported_output_type")


def _validate_contract_core(contract: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    normalized: dict[str, Any] = {}

    for field in _CORE_FIELDS:
        value = contract.get(field)
        if value is None:
            return None, "contract_missing_required"
        if isinstance(value, str) and not value.strip():
            return None, "contract_missing_required"
        normalized[field] = value

    level = str(normalized["level"]).strip().lower()
    category = str(normalized["category"]).strip()
    slot_key = str(normalized["slot_key"]).strip()
    canonical_text = str(normalized["canonical_text"]).strip()
    confidence = _safe_float(normalized["confidence"], default=-1.0)

    if level not in _VALID_LEVELS or category not in _VALID_CATEGORIES:
        return None, "contract_invalid_enum"
    if confidence < 0.0 or confidence > 1.0:
        return None, "contract_invalid_confidence"

    normalized.update(
        {
            "level": level,
            "category": category,
            "slot_key": slot_key,
            "canonical_text": canonical_text,
            "confidence": confidence,
            "durability_score": _safe_float(contract.get("durability_score"), default=0.0),
            "operation": str(contract.get("operation") or "upsert").strip().lower(),
            "reason": str(contract.get("reason") or "").strip(),
            "source_span": str(contract.get("source_span") or "").strip(),
            "reverse_intent": _safe_bool(contract.get("reverse_intent"), default=False),
        }
    )
    if not normalized["operation"]:
        normalized["operation"] = "upsert"

    return normalized, None


def _normalize_sentence(text: str) -> str:
    return re.sub(r"\\s+", "", str(text or "").strip().lower())


def _passes_canonical_text_quality(*, canonical_text: str, user_text: str) -> bool:
    normalized_canonical = _normalize_sentence(canonical_text)
    if not normalized_canonical:
        return False

    normalized_user = _normalize_sentence(user_text)
    if normalized_user and normalized_canonical == normalized_user:
        return False

    raw_text = str(canonical_text or "").strip()
    if any(pattern in raw_text for pattern in _TEMPLATE_PATTERNS):
        return False

    return True


def _build_prompt(*, user_text: str, context: dict[str, Any] | None = None) -> str:
    return MEMORY_INTENT_DECISION_PROMPT.format(
        user_text=str(user_text or "").strip(),
        context_json=json.dumps(context or {}, ensure_ascii=False),
    )


def decide(
    *,
    llm: Any,
    user_text: str,
    context: dict[str, Any] | None = None,
    confidence_threshold: float = 0.85,
) -> dict[str, Any]:
    """执行用户记忆意图合同判定，失败时统一降级为 none。"""

    normalized_user_text = str(user_text or "").strip()
    if not normalized_user_text:
        return _build_none_decision("contract_missing_required", reason="empty_user_text")

    threshold = _safe_float(confidence_threshold, default=0.85)
    prompt = _build_prompt(user_text=normalized_user_text, context=context)

    try:
        raw_output = llm.invoke(prompt)
    except Exception as exc:
        logger.warning("memory_intent_decide_llm_invoke_failed: %s", exc)
        return _build_none_decision("llm_invoke_failed", reason=str(exc))

    try:
        payload = _coerce_contract_payload(raw_output)
    except Exception as exc:
        logger.warning("memory_intent_decide_parse_failed: %s", exc)
        return _build_none_decision("contract_parse_failed")

    normalized, error_code = _validate_contract_core(payload)
    if normalized is None:
        return _build_none_decision(str(error_code or "contract_invalid"))

    if _safe_float(normalized.get("confidence"), default=0.0) < threshold:
        return _build_none_decision("low_confidence")

    if not _passes_canonical_text_quality(
        canonical_text=str(normalized.get("canonical_text") or ""),
        user_text=normalized_user_text,
    ):
        return _build_none_decision("canonical_text_quality_failed")

    normalized["audit_reason"] = "accepted"
    return normalized


def apply_reverse_intent(decision: dict[str, Any]) -> dict[str, Any]:
    """反向指令基础处理：仅在可定位槽位时转为 archive。"""

    result = dict(decision or {})
    if str(result.get("level") or "none") == "none":
        return result
    if not _safe_bool(result.get("reverse_intent"), default=False):
        return result

    if not str(result.get("slot_key") or "").strip():
        return _build_none_decision("reverse_intent_slot_missing")

    result["operation"] = "archive"
    result["audit_reason"] = str(result.get("audit_reason") or "reverse_intent_archive")
    return result

