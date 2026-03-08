"""槽位治理服务单测。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.services.memory_slot_governance_service import MemorySlotGovernanceService


@dataclass
class _Document:
    id: int
    revision: int = 1
    last_event_time: datetime | None = None


class _Repo:
    def __init__(self, current: _Document | None) -> None:
        self.current = current
        self.get_calls: list[dict[str, object]] = []
        self.archive_calls: list[dict[str, object]] = []
        self.upsert_slot_calls: list[dict[str, object]] = []
        self.upsert_document_calls: list[dict[str, object]] = []

    def get_active_slot(self, db, **kwargs):  # noqa: ANN001
        self.get_calls.append(kwargs)
        return self.current

    def archive_slot(self, db, **kwargs):  # noqa: ANN001
        self.archive_calls.append(kwargs)
        return {"found": True, "changed": True}

    def upsert_slot(self, db, **kwargs):  # noqa: ANN001
        self.upsert_slot_calls.append(kwargs)
        return _Document(
            id=801,
            revision=int(kwargs.get("revision") or 1),
            last_event_time=kwargs.get("last_event_time"),
        )

    def upsert_document(self, db, **kwargs):  # noqa: ANN001
        self.upsert_document_calls.append(kwargs)
        return _Document(
            id=901,
            revision=int(kwargs.get("revision") or 1),
            last_event_time=kwargs.get("last_event_time"),
        )


def test_normalize_slot_key_should_map_alias_and_enforce_prefix() -> None:
    """slot_key 应先归一化并拦截非法前缀。"""

    service = MemorySlotGovernanceService(repo=_Repo(None), slot_governance_enabled=True)

    assert service.normalize_slot_key(" AI.Personality ") == "assistant.persona.style"
    assert service.normalize_slot_key("User/Preference/Coffee") == "user.preference.coffee"
    assert service.normalize_slot_key("user.identity.display-name") == "user.identity.display-name"
    assert service.normalize_slot_key("custom.free.text") == ""


def test_upsert_slot_should_archive_previous_record_and_bump_revision() -> None:
    """同槽位写入新值时，应先归档旧值并递增 revision。"""

    current = _Document(
        id=11,
        revision=4,
        last_event_time=datetime(2026, 3, 4, 9, 0, 0),
    )
    repo = _Repo(current)
    service = MemorySlotGovernanceService(repo=repo, slot_governance_enabled=True)

    result = service.upsert_slot(
        db=object(),
        user_id=7,
        slot_key="user.preference.coffee",
        canonical_text="用户偏好美式咖啡",
        level="permanent",
        event_time=datetime(2026, 3, 4, 10, 0, 0),
        source_message_id=123,
    )

    assert result["status"] == "upserted"
    assert result["archived_doc_id"] == 11
    assert result["revision"] == 5
    assert len(repo.archive_calls) == 1
    assert repo.archive_calls[0]["doc_id"] == 11
    assert len(repo.upsert_slot_calls) == 1
    assert repo.upsert_slot_calls[0]["slot_key"] == "user.preference.coffee"
    assert repo.upsert_slot_calls[0]["revision"] == 5


def test_upsert_slot_should_skip_out_of_order_event() -> None:
    """旧事件不应覆盖新事件。"""

    current = _Document(
        id=21,
        revision=2,
        last_event_time=datetime(2026, 3, 4, 11, 0, 0),
    )
    repo = _Repo(current)
    service = MemorySlotGovernanceService(repo=repo, slot_governance_enabled=True)

    result = service.upsert_slot(
        db=object(),
        user_id=8,
        slot_key="user.profile.city",
        canonical_text="用户常驻上海",
        level="daily",
        event_time=datetime(2026, 3, 4, 10, 0, 0),
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "out_of_order"
    assert repo.archive_calls == []
    assert repo.upsert_slot_calls == []


def test_upsert_slot_should_archive_when_operation_archive() -> None:
    """反向操作为 archive 时，应仅归档槽位。"""

    current = _Document(
        id=31,
        revision=3,
        last_event_time=datetime(2026, 3, 4, 9, 0, 0),
    )
    repo = _Repo(current)
    service = MemorySlotGovernanceService(repo=repo, slot_governance_enabled=True)

    result = service.upsert_slot(
        db=object(),
        user_id=9,
        slot_key="interaction.policy.reply_style",
        canonical_text="回复保持简短",
        operation="archive",
        event_time=datetime(2026, 3, 4, 10, 0, 0),
    )

    assert result["status"] == "archived"
    assert len(repo.archive_calls) == 1
    assert repo.upsert_slot_calls == []


def test_upsert_slot_should_fallback_to_append_only_when_switch_off() -> None:
    """关闭槽位治理时应走 append-only。"""

    repo = _Repo(None)
    service = MemorySlotGovernanceService(repo=repo, slot_governance_enabled=False)

    result = service.upsert_slot(
        db=object(),
        user_id=10,
        slot_key="knowledge.important.framework",
        canonical_text="用户项目长期使用 FastAPI",
        level="permanent",
        event_time=datetime(2026, 3, 4, 10, 0, 0),
    )

    assert result["status"] == "upserted_append_only"
    assert repo.archive_calls == []
    assert repo.upsert_slot_calls == []
    assert len(repo.upsert_document_calls) == 1
    assert repo.upsert_document_calls[0]["slot_key"] == "knowledge.important.framework"
