"""ChatService 取消流式输出测试。"""

from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.chat_service import ChatService
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


class _ActivityGraph:
    """产生可见输出与状态事件的 Graph。"""

    def __init__(self) -> None:
        self._snapshot = SimpleNamespace(tasks=[], values={"messages": []})

    async def astream(self, *args, **kwargs):
        yield {
            "type": "token",
            "data": {"content": "第一段输出"},
            "node": "supervisor",
        }
        yield {
            "type": "status",
            "data": {"message": "继续处理中"},
            "node": "planner",
        }
        yield {
            "type": "result",
            "data": {
                "result_type": "todo_list",
                "message": "已整理待办",
                "todos": [],
            },
            "node": "planner",
        }

    async def aget_state(self, config):
        return self._snapshot


class _CancelableGraph:
    """在首个 token 后触发取消的 Graph。"""

    def __init__(self, run_id: str):
        self._run_id = run_id
        self._snapshot = SimpleNamespace(tasks=[], values={"messages": []})

    async def astream(self, *args, **kwargs):
        yield {
            "type": "token",
            "data": {"content": "第一段输出"},
            "node": "supervisor",
        }
        get_run_control_service().cancel_run(
            run_id=self._run_id,
            requester_user_id=1,
            reason="user_cancelled",
        )
        yield {
            "type": "token",
            "data": {"content": "取消后不应回灌"},
            "node": "supervisor",
        }

    async def aget_state(self, config):
        return self._snapshot


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


def test_stream_marks_activity_for_visible_output_and_status_progress():
    """流式输出应把首个可见输出与状态进度同步到 run activity。"""

    run_id = "run_activity_stream_001"
    graph = _ActivityGraph()

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return graph

    service = get_run_control_service()
    with patch("app.services.chat_service.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: SimpleNamespace(id=1)
    ), patch.object(ChatService, "get_graph", _fake_get_graph), patch.object(
        service,
        "mark_activity",
    ) as mock_mark_activity:
        svc = ChatService()
        _collect_events(
            svc.stream(
                prompt="查询贷款余额",
                thread_id="thread-activity-stream",
                user_id=1,
                run_id=run_id,
            )
        )

    assert any(call.args == (run_id,) and call.kwargs.get("force") is True for call in mock_mark_activity.call_args_list)
    assert any(call.args == (run_id,) and call.kwargs.get("force") is False for call in mock_mark_activity.call_args_list)


def test_stream_cancel_stops_token_backfill_and_emits_stopped_event():
    """取消后应阻断 token 回灌并发送 stopped + done。"""

    run_id = "run_cancel_stream_001"
    graph = _CancelableGraph(run_id)

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return graph

    with patch("app.services.chat_service.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: SimpleNamespace(id=1)
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(
                prompt="查询贷款余额",
                thread_id="thread-cancel-stream",
                user_id=1,
                run_id=run_id,
            )
        )

    event_types = [event for event, _ in events]
    token_payloads = [payload for event, payload in events if event == "token"]

    assert event_types[0] == "init"
    assert any(event == "stopped" for event in event_types)
    assert token_payloads == [{"content": "第一段输出", "node": "supervisor"}]

    stopped_payload = next(payload for event, payload in events if event == "stopped")
    assert stopped_payload["thread_id"] == "thread-cancel-stream"
    assert stopped_payload["run_id"] == run_id
    assert stopped_payload["reason"] == "user_cancelled"

    done_payload = next(payload for event, payload in events if event == "done")
    assert done_payload["run_id"] == run_id
    assert done_payload["meta"]["status"] == "stopped"
    assert done_payload["meta"]["cancel_after_token_count"] == 0
