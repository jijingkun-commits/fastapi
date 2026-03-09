"""文档记忆 worker 事务测试。"""

from datetime import datetime

import app.services.document_memory_service as memory_service


class _DummySession:
    def __init__(self):
        self.commit_called = False
        self.rollback_called = False

    def commit(self):
        self.commit_called = True

    def rollback(self):
        self.rollback_called = True


class _CurrentDocument:
    id = 41
    revision = 3
    last_event_time = datetime(2026, 3, 8, 10, 0, 0)


def test_flush_canonical_memory_should_not_commit_when_worker_manages_transaction(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(memory_service.document_memory_repo, "get_active_slot", lambda *args, **kwargs: _CurrentDocument())
    monkeypatch.setattr(
        memory_service.document_memory_repo,
        "archive_slot",
        lambda *args, **kwargs: {
            "found": True,
            "changed": True,
            "status": "archived",
            "revision": 3,
            "last_event_time": kwargs["event_time"],
            "operation": "archive",
        },
    )

    session = _DummySession()
    count = memory_service.flush_canonical_memory(
        session,
        user_id=9,
        source_thread_id="thread-archive",
        source_message_id=2002,
        decision_contract={
            "decision": "accept",
            "reason_code": "accepted",
            "confidence": 0.91,
            "memories": [
                {
                    "memory_kind": "response_preference",
                    "operation": "archive",
                    "slot_key": "user.preference.response_structure",
                    "normalized_value": "detailed_zong_fen_zong_paragraphs",
                    "canonical_text": "用户不再偏好总分总结构回答",
                    "evidence_span": "忘记我的总分总回复风格",
                }
            ],
            "audit": {"detector": "llm_primary", "decision_id": "decision-2002"},
        },
        manage_transaction=False,
    )

    assert count == 1
    assert session.commit_called is False
    assert session.rollback_called is False
