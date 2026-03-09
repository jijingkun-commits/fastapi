"""用户记忆意图 LLM 合同判定服务（中文注释）。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai.prompts.agent_prompts import (
    MEMORY_INTENT_DECISION_PROMPT,
    MEMORY_REFERENCE_RESOLUTION_PROMPT,
)
from app.services.memory_sensitive_guard_service import MemorySensitiveGuardService


logger = logging.getLogger(__name__)

DECISION_ACCEPT = "accept"
DECISION_REJECT = "reject"

_VALID_DECISIONS = {DECISION_ACCEPT, DECISION_REJECT}
_VALID_MEMORY_KINDS = {
    "user_identity",
    "response_preference",
    "assistant_persona",
    "profile_fact",
}
_VALID_OPERATIONS = {"upsert", "archive"}
_TEMPLATE_PATTERNS = (
    "我记住了你",
    "我会记住你",
    "我已经记住",
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


def _clamp_confidence(value: Any, default: float = 0.0) -> float:
    confidence = _safe_float(value, default=default)
    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return confidence


def _normalize_sentence(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip().lower())


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


def _build_reject_decision(
    reason_code: str,
    *,
    confidence: float = 0.0,
    detector: str = "llm_primary",
    audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "decision": DECISION_REJECT,
        "reason_code": str(reason_code or "contract_invalid"),
        "confidence": _clamp_confidence(confidence),
        "memories": [],
    }
    audit_payload: dict[str, Any] = {"detector": detector}
    if isinstance(audit, dict):
        audit_payload.update(audit)
    payload["audit"] = audit_payload
    return payload


def _extract_json_object_from_text(raw_text: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if not text:
        raise ValueError("empty_output")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

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


def _has_decision_contract_keys(payload: dict[str, Any]) -> bool:
    return any(
        key in payload
        for key in (
            "decision",
            "reason_code",
            "confidence",
            "memories",
        )
    )


def _coerce_contract_payload(raw_output: Any) -> dict[str, Any]:
    if isinstance(raw_output, dict):
        if _has_decision_contract_keys(raw_output):
            return raw_output
        content = raw_output.get("content")
    else:
        content = getattr(raw_output, "content", None)

    if isinstance(content, dict):
        if _has_decision_contract_keys(content):
            return content
        text_part = content.get("text")
        if isinstance(text_part, str):
            return _extract_json_object_from_text(text_part)
    if isinstance(content, list):
        pieces: list[str] = []
        for item in content:
            if isinstance(item, str):
                pieces.append(item)
                continue
            if isinstance(item, dict):
                if _has_decision_contract_keys(item):
                    return item
                text_part = item.get("text")
                if isinstance(text_part, str):
                    pieces.append(text_part)
        if pieces:
            return _extract_json_object_from_text("\n".join(piece for piece in pieces if piece))
    if isinstance(content, str):
        return _extract_json_object_from_text(content)

    if isinstance(raw_output, str):
        return _extract_json_object_from_text(raw_output)

    if hasattr(raw_output, "model_dump"):
        dumped = raw_output.model_dump()
        if isinstance(dumped, dict):
            return _coerce_contract_payload(dumped)

    raise ValueError("unsupported_output_type")


def _build_prompt(*, user_text: str, context: dict[str, Any] | None = None) -> str:
    return MEMORY_INTENT_DECISION_PROMPT.format(
        user_text=str(user_text or "").strip(),
        context_json=json.dumps(context or {}, ensure_ascii=False),
    )


def _build_reference_resolution_prompt(*, user_text: str, context: dict[str, Any] | None = None) -> str:
    return MEMORY_REFERENCE_RESOLUTION_PROMPT.format(
        user_text=str(user_text or "").strip(),
        context_json=json.dumps(context or {}, ensure_ascii=False),
    )


def _invoke_contract_prompt(
    *,
    llm: Any,
    prompt: str,
    user_text: str,
    confidence_threshold: float = 0.85,
) -> dict[str, Any]:
    normalized_user_text = str(user_text or "").strip()
    if not normalized_user_text:
        return _build_reject_decision("contract_missing_required")

    threshold = _clamp_confidence(confidence_threshold, default=0.85)

    try:
        raw_output = llm.invoke(prompt)
    except Exception as exc:
        logger.warning("memory_intent_decide_llm_invoke_failed: %s", exc)
        return _build_reject_decision("llm_invoke_failed")

    try:
        payload = _coerce_contract_payload(raw_output)
    except Exception as exc:
        logger.warning("memory_intent_decide_parse_failed: %s", exc)
        return _build_reject_decision("contract_parse_failed")

    decision = _normalize_decision_contract(
        payload,
        user_text=normalized_user_text,
        confidence_threshold=threshold,
    )
    decision = apply_reverse_intent(decision)
    decision = apply_sensitive_guard(decision, user_text=normalized_user_text)
    return decision


def _collect_reference_candidate_slot_keys(context: dict[str, Any] | None) -> set[str]:
    slot_keys: set[str] = set()
    for key in ("recent_memory_reference_candidates", "active_preference_candidates", "archived_preference_candidates", "recent_archived_preference_candidates"):
        raw_candidates = (context or {}).get(key)
        if not isinstance(raw_candidates, list):
            continue
        for item in raw_candidates:
            if not isinstance(item, dict):
                continue
            slot_key = str(item.get("slot_key") or "").strip().lower()
            if slot_key:
                slot_keys.add(slot_key)
    return slot_keys


def _normalize_memory_item(
    item: dict[str, Any],
    *,
    user_text: str,
    item_index: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    normalized: dict[str, Any] = {}

    required_fields = (
        "memory_kind",
        "operation",
        "slot_key",
        "canonical_text",
        "evidence_span",
    )
    for field in required_fields:
        value = item.get(field)
        if value is None:
            return None, {
                "item_index": item_index,
                "slot_key": str(item.get("slot_key") or ""),
                "reason_code": "contract_missing_required",
                "memory_kind": str(item.get("memory_kind") or ""),
            }
        if isinstance(value, str) and not value.strip():
            return None, {
                "item_index": item_index,
                "slot_key": str(item.get("slot_key") or ""),
                "reason_code": "contract_missing_required",
                "memory_kind": str(item.get("memory_kind") or ""),
            }
        normalized[field] = value

    memory_kind = str(normalized["memory_kind"]).strip().lower()
    operation = str(normalized["operation"]).strip().lower()
    slot_key = str(normalized["slot_key"]).strip().lower()
    canonical_text = str(normalized["canonical_text"]).strip()
    evidence_span = str(normalized["evidence_span"]).strip()
    raw_normalized_value = item.get("normalized_value")
    normalized_value = "" if raw_normalized_value is None else str(raw_normalized_value).strip()

    if operation != "archive" and not normalized_value:
        return None, {
            "item_index": item_index,
            "slot_key": slot_key,
            "reason_code": "contract_missing_required",
            "memory_kind": memory_kind,
        }

    if memory_kind not in _VALID_MEMORY_KINDS:
        return None, {
            "item_index": item_index,
            "slot_key": slot_key,
            "reason_code": "contract_invalid_memory_kind",
            "memory_kind": memory_kind,
            "normalized_value": normalized_value,
            "canonical_text": canonical_text,
        }
    if operation not in _VALID_OPERATIONS:
        return None, {
            "item_index": item_index,
            "slot_key": slot_key,
            "reason_code": "contract_invalid_operation",
            "memory_kind": memory_kind,
            "normalized_value": normalized_value,
            "canonical_text": canonical_text,
        }
    if not _passes_canonical_text_quality(canonical_text=canonical_text, user_text=user_text):
        return None, {
            "item_index": item_index,
            "slot_key": slot_key,
            "reason_code": "canonical_text_quality_failed",
            "memory_kind": memory_kind,
            "normalized_value": normalized_value,
            "canonical_text": canonical_text,
        }

    normalized_payload: dict[str, Any] = {
        "memory_kind": memory_kind,
        "operation": operation,
        "slot_key": slot_key,
        "normalized_value": normalized_value,
        "canonical_text": canonical_text,
        "evidence_span": evidence_span,
    }
    durability = item.get("durability")
    if durability is not None:
        normalized_payload["durability"] = _clamp_confidence(durability, default=0.0)
    return normalized_payload, None


def _normalize_decision_contract(
    payload: dict[str, Any],
    *,
    user_text: str,
    confidence_threshold: float,
) -> dict[str, Any]:
    decision = str(payload.get("decision") or "").strip().lower()
    reason_code = str(payload.get("reason_code") or "").strip()
    confidence = _clamp_confidence(payload.get("confidence"), default=-1.0)

    if not decision or not reason_code or confidence < 0.0:
        return _build_reject_decision("contract_missing_required")
    if decision not in _VALID_DECISIONS:
        return _build_reject_decision("contract_invalid_decision")
    if _safe_float(payload.get("confidence"), default=-1.0) < 0.0:
        return _build_reject_decision("contract_invalid_confidence")

    if confidence < confidence_threshold:
        return _build_reject_decision("low_confidence", confidence=confidence)

    if decision == DECISION_REJECT:
        return _build_reject_decision(reason_code, confidence=confidence)

    raw_memories = payload.get("memories")
    memories_input: list[dict[str, Any]]
    if isinstance(raw_memories, list):
        memories_input = [item for item in raw_memories if isinstance(item, dict)]
    elif isinstance(raw_memories, dict):
        memories_input = [raw_memories]
    else:
        return _build_reject_decision("contract_missing_required", confidence=confidence)

    if not memories_input:
        return _build_reject_decision("contract_missing_required", confidence=confidence)

    normalized_memories: list[dict[str, Any]] = []
    item_errors: list[dict[str, Any]] = []
    for index, memory_item in enumerate(memories_input):
        normalized_item, error = _normalize_memory_item(
            memory_item,
            user_text=user_text,
            item_index=index,
        )
        if error is not None:
            item_errors.append(error)
            continue
        normalized_memories.append(normalized_item or {})

    if item_errors:
        return _build_reject_decision(
            "contract_invalid_memory_item",
            confidence=confidence,
            audit={
                "rejected_items_count": len(item_errors),
                "item_errors": item_errors,
            },
        )

    normalized_contract: dict[str, Any] = {
        "decision": DECISION_ACCEPT,
        "reason_code": reason_code,
        "confidence": confidence,
        "memories": normalized_memories,
    }
    if "reverse_intent" in payload:
        normalized_contract["reverse_intent"] = _safe_bool(payload.get("reverse_intent"), default=False)
    if "reverse_intent_enabled" in payload:
        normalized_contract["reverse_intent_enabled"] = _safe_bool(
            payload.get("reverse_intent_enabled"),
            default=True,
        )
    raw_audit = payload.get("audit")
    if isinstance(raw_audit, dict):
        audit_payload = {"detector": "llm_primary", **raw_audit}
    else:
        audit_payload = {"detector": "llm_primary"}
    normalized_contract["audit"] = audit_payload
    return normalized_contract


def decide(
    *,
    llm: Any,
    user_text: str,
    context: dict[str, Any] | None = None,
    confidence_threshold: float = 0.85,
) -> dict[str, Any]:
    """执行用户记忆意图合同判定，统一返回 DecisionContract。"""

    normalized_user_text = str(user_text or "").strip()
    if not normalized_user_text:
        return _build_reject_decision("contract_missing_required")

    threshold = _clamp_confidence(confidence_threshold, default=0.85)
    prompt = _build_prompt(user_text=normalized_user_text, context=context)

    try:
        raw_output = llm.invoke(prompt)
    except Exception as exc:
        logger.warning("memory_intent_decide_llm_invoke_failed: %s", exc)
        return _build_reject_decision("llm_invoke_failed")

    try:
        payload = _coerce_contract_payload(raw_output)
    except Exception as exc:
        logger.warning("memory_intent_decide_parse_failed: %s", exc)
        return _build_reject_decision("contract_parse_failed")

    decision = _normalize_decision_contract(
        payload,
        user_text=normalized_user_text,
        confidence_threshold=threshold,
    )
    decision = apply_reverse_intent(decision)
    decision = apply_sensitive_guard(decision, user_text=normalized_user_text)
    return decision


def apply_reverse_intent(
    decision: dict[str, Any],
    *,
    reverse_intent_enabled: bool = True,
) -> dict[str, Any]:
    """反向指令处理：可选将记忆项统一转为 archive。"""

    result = dict(decision or {})
    if str(result.get("decision") or DECISION_REJECT) != DECISION_ACCEPT:
        return result

    reverse_intent = _safe_bool(result.get("reverse_intent"), default=False)
    if not reverse_intent:
        return result

    resolved_enabled = _safe_bool(
        result.get("reverse_intent_enabled"),
        default=reverse_intent_enabled,
    )
    if not resolved_enabled:
        return _build_reject_decision("reverse_intent_disabled", confidence=result.get("confidence", 0.0))

    memories = result.get("memories")
    if not isinstance(memories, list) or not memories:
        return _build_reject_decision(
            "reverse_intent_slot_missing",
            confidence=result.get("confidence", 0.0),
        )

    for memory in memories:
        if not isinstance(memory, dict) or not str(memory.get("slot_key") or "").strip():
            return _build_reject_decision(
                "reverse_intent_slot_missing",
                confidence=result.get("confidence", 0.0),
            )
        memory["operation"] = "archive"

    return result


def apply_sensitive_guard(
    decision: dict[str, Any],
    *,
    user_text: str,
    guard_service: MemorySensitiveGuardService | None = None,
) -> dict[str, Any]:
    """高敏信息命中时统一拒绝，防止沉淀入库。"""

    result = dict(decision or {})
    if str(result.get("decision") or DECISION_REJECT) != DECISION_ACCEPT:
        return result

    memories = result.get("memories")
    if not isinstance(memories, list) or not memories:
        return _build_reject_decision("contract_missing_required", confidence=result.get("confidence", 0.0))

    sensitive_guard = guard_service or MemorySensitiveGuardService()
    for index, memory_item in enumerate(memories):
        if not isinstance(memory_item, dict):
            return _build_reject_decision(
                "contract_invalid_memory_item",
                confidence=result.get("confidence", 0.0),
            )

        detected = sensitive_guard.detect(
            user_text=str(user_text or ""),
            canonical_text=str(memory_item.get("canonical_text") or ""),
            source_span=str(memory_item.get("evidence_span") or ""),
        )
        if not _safe_bool(detected.get("sensitive_hit"), default=False):
            continue

        return _build_reject_decision(
            "sensitive_info_blocked",
            confidence=result.get("confidence", 0.0),
            audit={
                "blocked_item_index": index,
                "sensitive_reason": str(detected.get("reason") or "sensitive_detected"),
            },
        )

    audit_payload = result.get("audit")
    if isinstance(audit_payload, dict):
        merged_audit = dict(audit_payload)
    else:
        merged_audit = {"detector": "llm_primary"}
    merged_audit["sensitive_hit"] = False
    result["audit"] = merged_audit
    return result


def resolve_reference_archive(
    *,
    llm: Any,
    user_text: str,
    context: dict[str, Any] | None = None,
    confidence_threshold: float = 0.85,
) -> dict[str, Any]:
    """根据候选记忆解析撤销/归档目标，输出最终 archive 合同。"""

    candidate_slot_keys = _collect_reference_candidate_slot_keys(context)
    if not candidate_slot_keys:
        return _build_reject_decision("reverse_intent_target_unresolved")

    prompt = _build_reference_resolution_prompt(user_text=user_text, context=context)
    decision = _invoke_contract_prompt(
        llm=llm,
        prompt=prompt,
        user_text=user_text,
        confidence_threshold=confidence_threshold,
    )
    if str(decision.get("decision") or DECISION_REJECT) != DECISION_ACCEPT:
        return decision

    memories = decision.get("memories")
    if not isinstance(memories, list) or len(memories) != 1:
        return _build_reject_decision(
            "reverse_intent_target_ambiguous",
            confidence=decision.get("confidence", 0.0),
        )

    memory_item = memories[0]
    if not isinstance(memory_item, dict):
        return _build_reject_decision(
            "contract_invalid_memory_item",
            confidence=decision.get("confidence", 0.0),
        )

    slot_key = str(memory_item.get("slot_key") or "").strip().lower()
    if slot_key not in candidate_slot_keys:
        return _build_reject_decision(
            "reverse_intent_slot_missing",
            confidence=decision.get("confidence", 0.0),
        )

    memory_item["operation"] = "archive"
    memory_item["normalized_value"] = ""
    reason_code = str(decision.get("reason_code") or "").strip().lower()
    if not reason_code or reason_code == "accepted":
        decision["reason_code"] = "reference_archive_resolved"
    return decision
