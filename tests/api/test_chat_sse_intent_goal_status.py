"""chat SSE 目标口径兼容测试。"""

import asyncio
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from app.services.chat_service import ChatService


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


@contextmanager
def _fake_get_db_context():
    """返回最小可用数据库上下文。"""
    yield _FakeDB()


class _FakeGraph:
    """最小化 Graph 实现。"""

    def __init__(self, chunks, snapshot):
        self._chunks = chunks
        self._snapshot = snapshot

    async def astream(self, *args, **kwargs):
        for chunk in self._chunks:
            yield chunk

    async def aget_state(self, config):
        return self._snapshot


def _decode_sse_event(chunk: bytes) -> tuple[str, dict]:
    """解析单条 SSE chunk。"""
    text = chunk.decode("utf-8").strip()
    lines = text.split("\n")
    event_type = lines[0].removeprefix("event: ")
    data = json.loads(lines[1].removeprefix("data: "))
    return event_type, data


def _collect_events(async_gen):
    """收集异步生成器输出。"""

    async def _inner():
        events = []
        async for chunk in async_gen:
            events.append(_decode_sse_event(chunk))
        return events

    return asyncio.run(_inner())


def test_stream_enriches_goal_status_fields_for_plan_and_coverage_events() -> None:
    """plan_ready/coverage_check/final_answer 应补齐双口径计数字段。"""
    final_text = "正在补齐缺失目标，请稍候。"
    fake_snapshot = SimpleNamespace(
        tasks=[],
        values={
            "messages": [
                HumanMessage(content="先查待办再看天气", id="human-goal"),
                AIMessage(content=final_text),
            ]
        },
    )
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "plan_ready",
                "data": {
                    "plan": {
                        "goals": [
                            {"goal_id": "GOAL-01", "kind": "todo.query"},
                            {"goal_id": "GOAL-02", "kind": "external.lookup"},
                        ]
                    }
                },
                "node": "planner",
            },
            {
                "type": "coverage_check",
                "data": {
                    "report": {
                        "pass": False,
                        "total_goals": 2,
                        "answered_goals": 1,
                        "missing_goals": [
                            {"goal_id": "GOAL-02", "title": "外部信息", "reason": "missing_deliverable"}
                        ],
                        "matched_goal_ids": ["GOAL-01"],
                        "goal_results": {},
                    }
                },
                "node": "coverage_gate",
            },
            {
                "type": "final_answer",
                "data": {
                    "content": final_text,
                    "meta": {"coverage_pass": False, "goal_count": 2, "missing_goals": 1},
                },
                "node": "final_composer",
            },
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message",
        lambda *args, **kwargs: SimpleNamespace(id=1),
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="先查待办再看天气", thread_id="thread-goal-v2", user_id=1)
        )

    plan_payload = next(payload for event, payload in events if event == "plan_ready")
    assert plan_payload["goal_count_initial"] == 2
    assert plan_payload["meta"]["goal_count_initial"] == 2

    coverage_payload = next(payload for event, payload in events if event == "coverage_check")
    assert coverage_payload["goal_count_initial"] == 2
    assert coverage_payload["goal_count_confirmed"] == 1
    assert coverage_payload["missing_goal_count"] == 1
    assert coverage_payload["meta"]["goal_count_confirmed"] == 1

    final_payload = next(payload for event, payload in events if event == "final_answer")
    assert final_payload["meta"]["goal_count_initial"] == 2
    assert final_payload["meta"]["goal_count_confirmed"] == 1
    assert final_payload["meta"]["missing_goal_count"] == 1


def test_stream_keeps_legacy_payload_when_goal_status_v2_disabled(monkeypatch) -> None:
    """关闭开关后，不应注入新增的双口径字段。"""
    monkeypatch.setenv("ENABLE_SSE_INTENT_GOAL_STATUS_V2", "false")
    final_text = "旧口径事件流。"
    fake_snapshot = SimpleNamespace(
        tasks=[],
        values={
            "messages": [
                HumanMessage(content="查待办", id="human-legacy"),
                AIMessage(content=final_text),
            ]
        },
    )
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "plan_ready",
                "data": {"plan": {"goals": [{"goal_id": "GOAL-01", "kind": "todo.query"}]}},
                "node": "planner",
            },
            {
                "type": "coverage_check",
                "data": {
                    "report": {
                        "pass": True,
                        "total_goals": 1,
                        "answered_goals": 1,
                        "missing_goals": [],
                        "matched_goal_ids": ["GOAL-01"],
                        "goal_results": {},
                    }
                },
                "node": "coverage_gate",
            },
            {
                "type": "final_answer",
                "data": {"content": final_text, "meta": {"coverage_pass": True, "goal_count": 1}},
                "node": "final_composer",
            },
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message",
        lambda *args, **kwargs: SimpleNamespace(id=1),
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="查待办", thread_id="thread-goal-legacy", user_id=1)
        )

    plan_payload = next(payload for event, payload in events if event == "plan_ready")
    assert "goal_count_initial" not in plan_payload
    assert "meta" not in plan_payload

    coverage_payload = next(payload for event, payload in events if event == "coverage_check")
    assert "goal_count_initial" not in coverage_payload
    assert "goal_count_confirmed" not in coverage_payload
    assert "missing_goal_count" not in coverage_payload
    assert "meta" not in coverage_payload

    final_payload = next(payload for event, payload in events if event == "final_answer")
    assert final_payload["meta"] == {"coverage_pass": True, "goal_count": 1}
