"""取消后 resume 语义测试。"""

from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager

import pytest

from app.services.chat_service import sse_resume_stream
from app.services.run_control_service import get_run_control_service, reset_run_control_service


class _FakeQuery:
    """最小化 Query 对象。"""

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []


class _FakeDB:
    """最小化 DB 对象。"""

    def query(self, *args, **kwargs):
        return _FakeQuery()

    def add(self, *args, **kwargs):
        return None

    def flush(self, *args, **kwargs):
        return None

    def commit(self, *args, **kwargs):
        return None

    def rollback(self, *args, **kwargs):
        return None


@contextmanager
def _fake_get_db_context():
    yield _FakeDB()


def _decode_sse_event(chunk: bytes) -> tuple[str, dict]:
    text = chunk.decode("utf-8").strip()
    lines = text.split("\n")
    event_type = lines[0].removeprefix("event: ")
    data = json.loads(lines[1].removeprefix("data: "))
    return event_type, data


def _collect_events(async_gen):
    async def _inner():
        events = []
        async for chunk in async_gen:
            events.append(_decode_sse_event(chunk))
        return events

    return asyncio.run(_inner())


@pytest.fixture(autouse=True)
def _reset_run_control_state():
    service = get_run_control_service()
    service.enable_override = True
    service.stopped_event_override = True
    service.reset()

    yield

    reset_run_control_service()


def test_resume_after_cancel_returns_stopped_and_done(monkeypatch: pytest.MonkeyPatch) -> None:
    """已取消 run 不应继续 resume 到原执行上下文。"""

    run_id = "run_resume_cancel_001"
    service = get_run_control_service()
    service.create_run(thread_id="thread-resume-cancel", user_id=1, run_id=run_id)
    service.cancel_run(run_id=run_id, requester_user_id=1, reason="user_cancelled")
    service.mark_stopped(run_id=run_id, reason="user_cancelled")

    monkeypatch.setattr("app.services.chat_service.get_db_context", _fake_get_db_context)

    events = _collect_events(
        sse_resume_stream(
            thread_id="thread-resume-cancel",
            decision={"type": "accept"},
            user_id=1,
            run_id=run_id,
        )
    )

    event_types = [event for event, _ in events]
    assert event_types == ["stopped", "done"]

    stopped_payload = events[0][1]
    assert stopped_payload["run_id"] == run_id
    assert stopped_payload["reason"] == "user_cancelled"

    done_payload = events[1][1]
    assert done_payload["run_id"] == run_id
    assert done_payload["meta"]["status"] == "stopped"
