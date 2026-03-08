"""用户记忆槽位治理服务（中文注释）。"""

from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.repositories import document_memory_repo
from app.services.config_resolver import ConfigResolver

_SLOT_KEY_ALIASES: dict[str, str] = {
    "ai.personality": "assistant.persona.style",
    "ai.persona": "assistant.persona.style",
    "assistant.style": "assistant.persona.style",
    "assistant.character": "assistant.persona.style",
    "assistant.persona": "assistant.persona.style",
    "user.preference": "user.preference.general",
    "response.preference": "user.preference.general",
    "response.verbosity": "user.preference.response_detail_level",
    "response.detail": "user.preference.response_detail_level",
    "response.length": "user.preference.response_length",
    "response.structure": "user.preference.response_structure",
    "user.identity": "user.identity.display_name",
    "user.profile": "user.profile.general",
    "interaction.policy": "interaction.policy.general",
    "knowledge.important": "knowledge.important.general",
}
_SLOT_KEY_PREFIXES: tuple[str, ...] = (
    "assistant.persona.",
    "user.identity.",
    "user.preference.",
    "knowledge.important.",
    "user.profile.",
    "interaction.policy.",
)
_SLOT_KEY_SEGMENT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class MemorySlotGovernanceService:
    """槽位归一化、覆盖归档与乱序保护服务。"""

    def __init__(
        self,
        *,
        repo: Any = document_memory_repo,
        slot_governance_enabled: bool | None = None,
    ) -> None:
        if slot_governance_enabled is None:
            slot_governance_enabled = ConfigResolver.get_bool("memory.slot_governance_enabled", True)

        self._repo = repo
        self.slot_governance_enabled = bool(slot_governance_enabled)

    @staticmethod
    def normalize_slot_key(slot_key: str) -> str:
        """归一化并校验 slot_key。"""

        normalized = str(slot_key or "").strip().lower()
        if not normalized:
            return ""

        normalized = normalized.replace(" ", "")
        normalized = normalized.replace("/", ".")
        normalized = normalized.replace(":", ".")
        normalized = normalized.replace("_", ".")
        normalized = re.sub(r"[^a-z0-9.\-]", "", normalized)
        normalized = re.sub(r"\.{2,}", ".", normalized).strip(".")
        normalized = _SLOT_KEY_ALIASES.get(normalized, normalized)
        if not normalized:
            return ""

        if not any(normalized.startswith(prefix) for prefix in _SLOT_KEY_PREFIXES):
            return ""

        segments = normalized.split(".")
        if len(segments) < 3:
            return ""
        if any(not _SLOT_KEY_SEGMENT_PATTERN.fullmatch(segment) for segment in segments):
            return ""
        return normalized

    @staticmethod
    def _normalize_operation(operation: str | None) -> str:
        normalized = str(operation or "upsert").strip().lower()
        if normalized in {"upsert", "archive", "drop"}:
            return normalized
        return "upsert"

    @staticmethod
    def _resolve_doc_kind(level: str | None) -> str:
        normalized = str(level or "permanent").strip().lower()
        if normalized == "daily":
            return "daily"
        return "preference"

    @staticmethod
    def _build_slot_content(
        *,
        slot_key: str,
        canonical_text: str,
        memory_kind: str | None,
        normalized_value: str | None,
        evidence_span: str | None,
        decision_id: str | None,
        confidence: float | None,
        reason_code: str | None,
        memories_count: int | None,
        rejected_items_count: int | None,
        item_errors: list[dict[str, Any]] | None,
        operation: str,
        event_time: datetime,
        source_thread_id: str | None,
        source_message_id: int | None,
    ) -> str:
        lines = [
            f"# 槽位记忆 {slot_key}",
            "",
            f"- slot_key: {slot_key}",
            f"- operation: {operation}",
            f"- canonical_text: {canonical_text}",
            f"- event_time: {event_time.isoformat()}",
        ]
        if memory_kind:
            lines.append(f"- memory_kind: {memory_kind}")
        if normalized_value:
            lines.append(f"- normalized_value: {normalized_value}")
        if evidence_span:
            lines.append(f"- evidence_span: {evidence_span}")
        if decision_id:
            lines.append(f"- decision_id: {decision_id}")
        if reason_code:
            lines.append(f"- reason_code: {reason_code}")
        if confidence is not None:
            lines.append(f"- confidence: {float(confidence):.4f}")
        if memories_count is not None:
            lines.append(f"- memories_count: {int(memories_count)}")
        if rejected_items_count is not None:
            lines.append(f"- rejected_items_count: {int(rejected_items_count)}")
        if item_errors is not None:
            lines.append(f"- item_errors_json: {json.dumps(item_errors, ensure_ascii=False)}")
        if source_thread_id:
            lines.append(f"- source_thread_id: {source_thread_id}")
        if source_message_id is not None:
            lines.append(f"- source_message_id: {int(source_message_id)}")
        return "\n".join(lines)

    @staticmethod
    def _is_out_of_order(*, current: Any, incoming_event_time: datetime) -> bool:
        current_event_time = getattr(current, "last_event_time", None)
        if current_event_time is None:
            return False
        return incoming_event_time < current_event_time

    @staticmethod
    def _build_append_only_doc_key(
        *,
        slot_key: str,
        event_time: datetime,
        source_message_id: int | None,
    ) -> str:
        suffix = event_time.strftime("%Y%m%d%H%M%S%f")
        if source_message_id is not None:
            return f"{slot_key}:{int(source_message_id)}:{suffix}"
        return f"{slot_key}:{suffix}"

    def upsert_slot(
        self,
        db: Session,
        *,
        user_id: int,
        slot_key: str,
        canonical_text: str,
        level: str = "permanent",
        operation: str = "upsert",
        event_time: datetime | None = None,
        source_thread_id: str | None = None,
        source_message_id: int | None = None,
        source: str = "memory",
        scope: str = "private",
        scope_ref: str | None = None,
        memory_kind: str | None = None,
        normalized_value: str | None = None,
        evidence_span: str | None = None,
        decision_id: str | None = None,
        confidence: float | None = None,
        reason_code: str | None = None,
        memories_count: int | None = None,
        rejected_items_count: int | None = None,
        item_errors: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """执行槽位治理写入：归一化、冲突覆盖、归档审计。"""

        normalized_slot_key = self.normalize_slot_key(slot_key)
        if not normalized_slot_key:
            return {
                "status": "skipped",
                "reason": "slot_key_invalid",
                "slot_key": "",
                "operation": "drop",
            }

        normalized_operation = self._normalize_operation(operation)
        incoming_event_time = event_time or datetime.now()
        doc_kind = self._resolve_doc_kind(level)

        if normalized_operation == "drop":
            return {
                "status": "skipped",
                "reason": "operation_drop",
                "slot_key": normalized_slot_key,
                "operation": "drop",
            }

        if normalized_operation == "archive":
            current = self._repo.get_active_slot(
                db,
                user_id=user_id,
                slot_key=normalized_slot_key,
                doc_kind=doc_kind,
                source=source,
                for_update=self.slot_governance_enabled,
            )
            if current is None:
                return {
                    "status": "skipped",
                    "reason": "slot_not_found",
                    "slot_key": normalized_slot_key,
                    "operation": "archive",
                }
            if self._is_out_of_order(current=current, incoming_event_time=incoming_event_time):
                return {
                    "status": "skipped",
                    "reason": "out_of_order",
                    "slot_key": normalized_slot_key,
                    "operation": "archive",
                    "revision": int(getattr(current, "revision", 1) or 1),
                    "last_event_time": getattr(current, "last_event_time", None),
                }

            archived = self._repo.archive_slot(
                db,
                doc_id=int(current.id),
                user_id=user_id,
                event_time=incoming_event_time,
                operation="archive",
            )
            return {
                "status": "archived",
                "reason": "slot_archived",
                "slot_key": normalized_slot_key,
                "operation": "archive",
                "document_id": int(getattr(current, "id", 0) or 0),
                "revision": int(getattr(current, "revision", 1) or 1),
                "last_event_time": incoming_event_time,
                "changed": bool(archived.get("changed")),
            }

        content_md = self._build_slot_content(
            slot_key=normalized_slot_key,
            canonical_text=str(canonical_text or "").strip(),
            memory_kind=str(memory_kind or "").strip().lower() or None,
            normalized_value=str(normalized_value or "").strip() or None,
            evidence_span=str(evidence_span or "").strip() or None,
            decision_id=str(decision_id or "").strip() or None,
            confidence=confidence,
            reason_code=str(reason_code or "").strip() or None,
            memories_count=memories_count,
            rejected_items_count=rejected_items_count,
            item_errors=item_errors,
            operation="upsert",
            event_time=incoming_event_time,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )
        summary_md = str(canonical_text or "").strip()[:200] or None

        if not self.slot_governance_enabled:
            append_only_doc_key = self._build_append_only_doc_key(
                slot_key=normalized_slot_key,
                event_time=incoming_event_time,
                source_message_id=source_message_id,
            )
            document = self._repo.upsert_document(
                db,
                user_id=user_id,
                doc_kind=doc_kind,
                doc_key=append_only_doc_key,
                slot_key=normalized_slot_key,
                title=f"槽位记忆 {normalized_slot_key}",
                content_md=content_md,
                summary_md=summary_md,
                source=source,
                scope=scope,
                scope_ref=scope_ref,
                content_hash=hashlib.sha256(content_md.encode("utf-8")).hexdigest(),
                source_thread_id=source_thread_id,
                source_message_id=source_message_id,
                operation="upsert",
                last_event_time=incoming_event_time,
                revision=1,
            )
            return {
                "status": "upserted_append_only",
                "reason": "slot_governance_disabled",
                "slot_key": normalized_slot_key,
                "operation": "upsert",
                "document_id": int(document.id),
                "revision": int(getattr(document, "revision", 1) or 1),
                "last_event_time": incoming_event_time,
            }

        current = self._repo.get_active_slot(
            db,
            user_id=user_id,
            slot_key=normalized_slot_key,
            doc_kind=doc_kind,
            source=source,
            for_update=True,
        )
        if current is not None and self._is_out_of_order(
            current=current,
            incoming_event_time=incoming_event_time,
        ):
            return {
                "status": "skipped",
                "reason": "out_of_order",
                "slot_key": normalized_slot_key,
                "operation": "upsert",
                "revision": int(getattr(current, "revision", 1) or 1),
                "last_event_time": getattr(current, "last_event_time", None),
            }

        archived_doc_id: int | None = None
        next_revision = 1
        if current is not None:
            archived_doc_id = int(current.id)
            next_revision = int(getattr(current, "revision", 1) or 1) + 1
            self._repo.archive_slot(
                db,
                doc_id=archived_doc_id,
                user_id=user_id,
                event_time=incoming_event_time,
                operation="archive",
            )

        document = self._repo.upsert_slot(
            db,
            user_id=user_id,
            doc_kind=doc_kind,
            slot_key=normalized_slot_key,
            title=f"槽位记忆 {normalized_slot_key}",
            content_md=content_md,
            summary_md=summary_md,
            source=source,
            scope=scope,
            scope_ref=scope_ref,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
            operation="upsert",
            last_event_time=incoming_event_time,
            revision=next_revision,
        )
        return {
            "status": "upserted",
            "reason": "slot_upserted",
            "slot_key": normalized_slot_key,
            "operation": "upsert",
            "document_id": int(document.id),
            "revision": int(getattr(document, "revision", next_revision) or next_revision),
            "last_event_time": incoming_event_time,
            "archived_doc_id": archived_doc_id,
        }
