"""memory intent resolver 服务（中文注释）。"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from app.core.message_content import normalize_message_content
from app.repositories import chat_repo, document_memory_repo
from app.services import memory_intent_llm_service

logger = logging.getLogger(__name__)

RESOLUTION_RESOLVED = "resolved"
RESOLUTION_REJECTED = "rejected"
RESOLUTION_NEEDS_CLARIFICATION = "needs_clarification"

_CLARIFICATION_REASON_CODES = {
    "reverse_intent_slot_missing",
    "reverse_intent_target_unresolved",
    "reverse_intent_target_ambiguous",
}


def _normalize_memory_reference_text(text: Any) -> str:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return ""
    return re.sub(r"[^0-9a-z一-鿿]+", "", normalized)



def _load_recent_thread_messages(
    db: Any,
    *,
    thread_id: str,
    exclude_message_id: int | None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    try:
        messages = chat_repo.get_messages_by_thread(db, thread_id, max(limit + 2, 8))
    except Exception as recent_error:
        logger.warning("加载最近线程消息失败，已降级跳过: thread_id=%s, error=%s", thread_id, recent_error)
        return []

    recent_messages: list[dict[str, Any]] = []
    for message in messages:
        message_id = getattr(message, "id", None)
        if exclude_message_id is not None and message_id == exclude_message_id:
            continue
        content = normalize_message_content(getattr(message, "content", None)).strip()
        if not content:
            continue
        recent_messages.append(
            {
                "message_id": int(message_id) if message_id is not None else None,
                "role": str(getattr(message, "role", "") or "").strip().lower(),
                "content": content[:160],
            }
        )

    return recent_messages[-max(1, int(limit)) :]



def _build_recent_dialogue_context(
    recent_messages: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """提取最近对话中的关键承接上下文，帮助 LLM 理解确认/指代删除。"""
    context: dict[str, dict[str, Any]] = {}
    for message in reversed(recent_messages or []):
        role = str(message.get("role") or "").strip().lower()
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        payload = {
            "message_id": message.get("message_id"),
            "role": role,
            "content": content[:240],
        }
        if role == "ai" and "latest_assistant_message" not in context:
            context["latest_assistant_message"] = payload
        elif role == "human" and "latest_user_message_before_source" not in context:
            context["latest_user_message_before_source"] = payload
        if "latest_assistant_message" in context and "latest_user_message_before_source" in context:
            break
    return context



def _select_recent_archived_preference_candidates(
    archived_candidates: list[dict[str, Any]],
    recent_messages: list[dict[str, Any]],
    *,
    thread_id: str,
    latest_user_message_before_source: dict[str, Any] | None = None,
    max_candidates: int = 3,
) -> list[dict[str, Any]]:
    """提取同线程最近刚归档成功、可供确认轮沿用的目标。"""
    if not archived_candidates or not recent_messages:
        return []

    recent_human_message_ids = {
        int(message.get("message_id"))
        for message in recent_messages
        if str(message.get("role") or "").strip().lower() == "human"
        and message.get("message_id") is not None
    }
    latest_user_message_id = None
    if isinstance(latest_user_message_before_source, dict) and latest_user_message_before_source.get("message_id") is not None:
        latest_user_message_id = int(latest_user_message_before_source.get("message_id"))

    matched: list[dict[str, Any]] = []
    for item in archived_candidates:
        slot_key = str(item.get("slot_key") or "").strip()
        summary_md = str(item.get("summary_md") or "").strip()
        source_thread_id = str(item.get("source_thread_id") or "").strip()
        source_message_id = item.get("source_message_id")
        if not slot_key or not summary_md or not source_thread_id or source_thread_id != thread_id:
            continue
        try:
            normalized_source_message_id = int(source_message_id)
        except (TypeError, ValueError):
            continue
        if normalized_source_message_id not in recent_human_message_ids:
            continue
        matched.append(
            {
                "slot_key": slot_key,
                "summary_md": summary_md,
                "source_thread_id": source_thread_id,
                "source_message_id": normalized_source_message_id,
                "match_latest_user_message": latest_user_message_id == normalized_source_message_id,
            }
        )

    matched.sort(
        key=lambda item: (
            bool(item.get("match_latest_user_message")),
            int(item.get("source_message_id") or 0),
            str(item.get("slot_key") or ""),
        ),
        reverse=True,
    )
    return matched[: max(1, int(max_candidates))]


def _select_recent_memory_reference_candidates(
    candidates: list[dict[str, str]],
    recent_messages: list[dict[str, Any]],
    *,
    max_candidates: int = 3,
) -> list[dict[str, Any]]:
    if not candidates or not recent_messages:
        return []

    scored_candidates: list[dict[str, Any]] = []
    reversed_messages = list(reversed(recent_messages))
    for candidate in candidates:
        slot_key = str(candidate.get("slot_key") or "").strip()
        summary_md = str(candidate.get("summary_md") or "").strip()
        normalized_summary = _normalize_memory_reference_text(summary_md)
        if not slot_key or not normalized_summary:
            continue

        best_score = 0
        best_message: dict[str, Any] | None = None
        for index, message in enumerate(reversed_messages):
            normalized_message = _normalize_memory_reference_text(message.get("content"))
            if not normalized_message:
                continue
            score = 0
            if normalized_summary in normalized_message or normalized_message in normalized_summary:
                score = max(1, 100 - index * 10 + min(len(normalized_summary), 20))
            if score > best_score:
                best_score = score
                best_message = message

        if best_score <= 0 or best_message is None:
            continue

        scored_candidates.append(
            {
                "slot_key": slot_key,
                "summary_md": summary_md,
                "matched_message_id": best_message.get("message_id"),
                "matched_message_role": best_message.get("role"),
                "match_score": best_score,
            }
        )

    scored_candidates.sort(
        key=lambda item: (int(item.get("match_score") or 0), str(item.get("slot_key") or "")),
        reverse=True,
    )
    return scored_candidates[: max(1, int(max_candidates))]



def build_context(
    db: Any,
    *,
    user_id: int | None,
    thread_id: str,
    source_message_id: int | None,
    max_candidates: int = 8,
) -> dict[str, Any]:
    """构建记忆意图判定上下文，供 resolver / worker 复用。"""

    context: dict[str, Any] = {
        "source_thread_id": thread_id,
        "source_message_id": source_message_id,
    }
    if not user_id:
        return context

    try:
        documents, _ = document_memory_repo.list_documents(
            db,
            user_id=int(user_id),
            doc_kind="preference",
            status="active",
            source="memory",
            page=1,
            page_size=max(1, int(max_candidates)),
        )
    except Exception as memory_error:
        logger.warning("加载记忆意图候选失败，已降级跳过: user_id=%s, error=%s", user_id, memory_error)
        return context

    candidates: list[dict[str, str]] = []
    for item in documents:
        slot_key = str(item.get("slot_key") or item.get("doc_key") or "").strip()
        summary_md = str(item.get("summary_md") or "").strip()
        if not slot_key or not summary_md:
            continue
        candidates.append(
            {
                "slot_key": slot_key,
                "summary_md": summary_md,
            }
        )

    if candidates:
        context["active_preference_candidates"] = candidates

    try:
        archived_documents, _ = document_memory_repo.list_documents(
            db,
            user_id=int(user_id),
            doc_kind="preference",
            status="archived",
            source="memory",
            page=1,
            page_size=max(1, int(max_candidates)),
            include_source_refs=True,
        )
    except Exception as archived_error:
        logger.warning("加载归档记忆候选失败，已降级跳过: user_id=%s, error=%s", user_id, archived_error)
        archived_documents = []

    archived_candidates: list[dict[str, Any]] = []
    for item in archived_documents:
        slot_key = str(item.get("slot_key") or item.get("doc_key") or "").strip()
        summary_md = str(item.get("summary_md") or "").strip()
        if not slot_key or not summary_md:
            continue
        archived_candidates.append(
            {
                "slot_key": slot_key,
                "summary_md": summary_md,
                "source_thread_id": item.get("source_thread_id"),
                "source_message_id": item.get("source_message_id"),
            }
        )

    if archived_candidates:
        context["archived_preference_candidates"] = archived_candidates

    recent_messages = _load_recent_thread_messages(
        db,
        thread_id=thread_id,
        exclude_message_id=source_message_id,
    )
    if recent_messages:
        context["recent_thread_messages"] = recent_messages
        context.update(_build_recent_dialogue_context(recent_messages))
        recent_archived_candidates = _select_recent_archived_preference_candidates(
            archived_candidates,
            recent_messages,
            thread_id=thread_id,
            latest_user_message_before_source=context.get("latest_user_message_before_source"),
        )
        if recent_archived_candidates:
            context["recent_archived_preference_candidates"] = recent_archived_candidates

    reference_candidates = _select_recent_memory_reference_candidates(candidates, recent_messages)
    if reference_candidates:
        context["recent_memory_reference_candidates"] = reference_candidates
    return context



def _ensure_audit(
    decision_contract: dict[str, Any],
    *,
    source_message_id: int | None,
    resolver_stage: str,
) -> dict[str, Any]:
    result = dict(decision_contract or {})
    audit_payload = result.get("audit")
    if isinstance(audit_payload, dict):
        audit = dict(audit_payload)
    else:
        audit = {}

    if not str(audit.get("decision_id") or "").strip():
        if source_message_id is not None:
            decision_id = f"decision-{int(source_message_id)}"
        else:
            decision_id = f"decision-{uuid4().hex}"
        audit["decision_id"] = decision_id

    audit.setdefault("detector", "llm_primary")
    audit["resolver_stage"] = resolver_stage
    result["audit"] = audit
    return result



def _has_non_empty_context_list(intent_context: dict[str, Any] | None, key: str) -> bool:
    raw_value = (intent_context or {}).get(key)
    return isinstance(raw_value, list) and bool(raw_value)



def _should_attempt_reference_resolution(intent_context: dict[str, Any] | None) -> bool:
    if _has_non_empty_context_list(intent_context, "recent_memory_reference_candidates"):
        return True
    has_recent_messages = _has_non_empty_context_list(intent_context, "recent_thread_messages")
    has_active_candidates = _has_non_empty_context_list(intent_context, "active_preference_candidates")
    has_archived_candidates = _has_non_empty_context_list(intent_context, "archived_preference_candidates")
    has_recent_archived_candidates = _has_non_empty_context_list(intent_context, "recent_archived_preference_candidates")
    return has_recent_messages and (has_active_candidates or has_archived_candidates or has_recent_archived_candidates)



def _resolution_status_for_reason(reason_code: str | None) -> str:
    normalized = str(reason_code or "").strip().lower()
    if normalized in _CLARIFICATION_REASON_CODES:
        return RESOLUTION_NEEDS_CLARIFICATION
    return RESOLUTION_REJECTED



def _build_resolution_contract(
    *,
    resolution_status: str,
    reason_code: str,
    confidence: float,
    persistence_contract: dict[str, Any] | None,
    audit: dict[str, Any],
    intent_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "resolution_status": resolution_status,
        "reason_code": str(reason_code or ""),
        "confidence": float(confidence),
        "persistence_contract": persistence_contract,
        "audit": dict(audit),
        "intent_context": intent_context,
    }



def resolve(
    db: Any,
    *,
    llm: Any,
    user_text: str,
    user_id: int | None,
    thread_id: str,
    source_message_id: int | None,
    confidence_threshold: float = 0.85,
) -> dict[str, Any]:
    """统一输出 memory intent resolver contract。"""

    intent_context = build_context(
        db,
        user_id=user_id,
        thread_id=thread_id,
        source_message_id=source_message_id,
    )
    primary_decision = memory_intent_llm_service.decide(
        llm=llm,
        user_text=user_text,
        context=intent_context,
        confidence_threshold=confidence_threshold,
    )
    primary_decision = _ensure_audit(
        primary_decision,
        source_message_id=source_message_id,
        resolver_stage="primary",
    )

    if str(primary_decision.get("decision") or "").strip().lower() == memory_intent_llm_service.DECISION_ACCEPT:
        return _build_resolution_contract(
            resolution_status=RESOLUTION_RESOLVED,
            reason_code=str(primary_decision.get("reason_code") or "accepted"),
            confidence=float(primary_decision.get("confidence") or 0.0),
            persistence_contract=primary_decision,
            audit=dict(primary_decision.get("audit") or {}),
            intent_context=intent_context,
        )

    if not _should_attempt_reference_resolution(intent_context):
        return _build_resolution_contract(
            resolution_status=_resolution_status_for_reason(primary_decision.get("reason_code")),
            reason_code=str(primary_decision.get("reason_code") or "rejected"),
            confidence=float(primary_decision.get("confidence") or 0.0),
            persistence_contract=None,
            audit=dict(primary_decision.get("audit") or {}),
            intent_context=intent_context,
        )

    reference_decision = memory_intent_llm_service.resolve_reference_archive(
        llm=llm,
        user_text=user_text,
        context=intent_context,
        confidence_threshold=confidence_threshold,
    )
    reference_decision = _ensure_audit(
        reference_decision,
        source_message_id=source_message_id,
        resolver_stage="reference_resolution",
    )
    reference_audit = dict(reference_decision.get("audit") or {})
    reference_audit["primary_reason_code"] = str(primary_decision.get("reason_code") or "")
    reference_decision["audit"] = reference_audit

    if str(reference_decision.get("decision") or "").strip().lower() == memory_intent_llm_service.DECISION_ACCEPT:
        return _build_resolution_contract(
            resolution_status=RESOLUTION_RESOLVED,
            reason_code=str(reference_decision.get("reason_code") or "reference_archive_resolved"),
            confidence=float(reference_decision.get("confidence") or 0.0),
            persistence_contract=reference_decision,
            audit=reference_audit,
            intent_context=intent_context,
        )

    return _build_resolution_contract(
        resolution_status=_resolution_status_for_reason(reference_decision.get("reason_code")),
        reason_code=str(reference_decision.get("reason_code") or "rejected"),
        confidence=float(reference_decision.get("confidence") or 0.0),
        persistence_contract=None,
        audit=reference_audit,
        intent_context=intent_context,
    )
