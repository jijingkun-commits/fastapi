"""ChatService 断连后续跑语义测试。"""

from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from psycopg import OperationalError

from app.services.chat_service import ChatService
from app.services.run_control_service import run_control_service


class _FakeQuery:
    """最小化 Query 链式对象。"""

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return None


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


class _SimpleGraph:
    """最小化图执行器，输出两段 token。"""

    def __init__(self) -> None:
        self._snapshot = SimpleNamespace(
            tasks=[],
            values={
                "messages": [
                    HumanMessage(content="查询贷款余额", id="human-disconnect"),
                    AIMessage(content="最终回复"),
                ]
            },
        )

    async def astream(self, *args, **kwargs):
        yield {
            "type": "token",
            "data": {"content": "第一段输出"},
            "node": "supervisor",
        }
        yield {
            "type": "token",
            "data": {"content": "第二段输出"},
            "node": "supervisor",
        }

    async def aget_state(self, config):
        return self._snapshot


class _BusySnapshotGraph(_SimpleGraph):
    """断连后若仍回读状态会触发 busy 异常的图执行器。"""

    def __init__(self) -> None:
        super().__init__()
        self.state_called = False

    async def aget_state(self, config):
        self.state_called = True
        raise OperationalError("sending query and params failed: another command is already in progress")


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
    prev_enable = run_control_service.enable_override
    prev_stopped = run_control_service.stopped_event_override

    run_control_service.enable_override = True
    run_control_service.stopped_event_override = True
    run_control_service.reset()

    yield

    run_control_service.reset()
    run_control_service.enable_override = prev_enable
    run_control_service.stopped_event_override = prev_stopped


def test_stream_disconnect_does_not_cancel_run():
    """SSE 断连后 run 不应被取消，应继续收口为 completed。"""

    run_id = "run_disconnect_continue_001"
    graph = _SimpleGraph()

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return graph

    with patch("app.services.chat_service.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: SimpleNamespace(id=1)
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        original_format_sse = svc._format_sse
        disconnected_once = {"value": False}

        def _format_sse_with_disconnect(event_type: str, data: dict) -> bytes:
            if event_type == "token" and not disconnected_once["value"]:
                disconnected_once["value"] = True
                raise asyncio.CancelledError()
            return original_format_sse(event_type, data)

        svc._format_sse = _format_sse_with_disconnect  # type: ignore[method-assign]
        events = _collect_events(
            svc.stream(
                prompt="查询贷款余额",
                thread_id="thread-disconnect-continue",
                user_id=1,
                run_id=run_id,
            )
        )

    event_types = [event for event, _ in events]
    assert event_types[0] == "init"
    assert "stopped" not in event_types

    snapshot = run_control_service.get_run(run_id)
    assert snapshot is not None
    assert snapshot.status == "completed"
    assert snapshot.cancel_reason is None


def test_stream_disconnect_skips_snapshot_readback_on_busy_error():
    """断连后应跳过状态回读，避免触发 checkpointer busy 异常。"""

    run_id = "run_disconnect_skip_snapshot_001"
    graph = _BusySnapshotGraph()

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return graph

    with patch("app.services.chat_service.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: SimpleNamespace(id=1)
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        original_format_sse = svc._format_sse
        disconnected_once = {"value": False}

        def _format_sse_with_disconnect(event_type: str, data: dict) -> bytes:
            if event_type == "token" and not disconnected_once["value"]:
                disconnected_once["value"] = True
                raise asyncio.CancelledError()
            return original_format_sse(event_type, data)

        svc._format_sse = _format_sse_with_disconnect  # type: ignore[method-assign]
        events = _collect_events(
            svc.stream(
                prompt="查询贷款余额",
                thread_id="thread-disconnect-skip-snapshot",
                user_id=1,
                run_id=run_id,
            )
        )

    assert not graph.state_called
    event_types = [event for event, _ in events]
    assert event_types[0] == "init"
    assert "error" not in event_types

    snapshot = run_control_service.get_run(run_id)
    assert snapshot is not None
    assert snapshot.status == "completed"
