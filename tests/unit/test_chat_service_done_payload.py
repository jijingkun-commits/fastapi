"""ChatService done 事件载荷约束测试。"""

import asyncio
from datetime import date
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from app.services.chat_service import ChatService, sse_resume_stream


class _FakeQuery:
    """最小化 Query 链式对象。"""

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


class _FakeCheckpoint:
    """最小化 checkpoint 对象。"""

    async def aget(self, config):
        return {"channel_values": {"enable_thinking": False, "model_id": None}}


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


def test_stream_done_payload_excludes_additional_kwargs_even_with_structured_result():
    """stream() 在 result 与 snapshot 均含结构化数据时，done 仍不应携带 additional_kwargs。"""

    fake_snapshot = SimpleNamespace(
        tasks=[],
        values={
            "messages": [
                HumanMessage(content="查询待办", id="human-old"),
                AIMessage(
                    content="找到 1 条待办",
                    additional_kwargs={"data_type": "todo_list", "data": {"todos": [{"id": 1}]}}
                ),
            ]
        },
    )
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "result",
                "data": {
                    "data_type": "todo_list",
                    "data": {"todos": [{"id": 1}]},
                    "message": "找到 1 条待办",
                },
                "node": "todo_expert",
            }
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: None
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="查一下我的待办", thread_id="thread-1", user_id=1)
        )

    done_events = [payload for event, payload in events if event == "done"]
    assert len(done_events) == 1
    done_payload = done_events[0]

    assert done_payload["thread_id"] == "thread-1"
    assert "message_id" in done_payload
    assert "additional_kwargs" not in done_payload


def test_resume_done_payload_excludes_additional_kwargs_even_with_structured_result():
    """sse_resume_stream() 在恢复流中也不应把结构化数据塞进 done。"""

    fake_snapshot = SimpleNamespace(
        tasks=[],
        values={
            "messages": [
                AIMessage(
                    content="恢复后结果",
                    additional_kwargs={"data_type": "todo_list", "data": {"todos": [{"id": 2}]}}
                )
            ]
        },
    )
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "result",
                "data": {
                    "data_type": "todo_list",
                    "data": {"todos": [{"id": 2}]},
                    "message": "恢复后找到 1 条待办",
                },
                "node": "todo_expert",
            }
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    async def _fake_get_checkpointer():
        return _FakeCheckpoint()

    with patch("app.db.postgres_checkpoint.get_checkpointer", _fake_get_checkpointer), patch.object(
        ChatService, "get_graph", _fake_get_graph
    ):
        events = _collect_events(
            sse_resume_stream(thread_id="thread-2", decision={"type": "accept"}, user_id=1)
        )

    done_events = [payload for event, payload in events if event == "done"]
    assert len(done_events) == 1
    done_payload = done_events[0]

    assert done_payload["thread_id"] == "thread-2"
    assert "message_id" in done_payload
    assert "additional_kwargs" not in done_payload


def test_result_event_payload_includes_frozen_required_fields():
    """result 事件在缺失 type/content 时应自动补齐冻结必填字段。"""

    fake_snapshot = SimpleNamespace(tasks=[], values={"messages": []})
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "result",
                "data": {
                    "data_type": "todo_list",
                    "data": {"todos": [{"id": 1, "title": "项目复盘"}]},
                },
                "node": "todo_expert",
            }
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: None
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="列出我的待办", thread_id="thread-result", user_id=1)
        )

    result_events = [payload for event, payload in events if event == "result"]
    assert len(result_events) == 1
    payload = result_events[0]

    assert payload["type"] == "todo_list"
    assert "content" in payload
    assert "meta" in payload
    assert payload["meta"]["node"] == "todo_expert"


def test_stream_forwards_final_answer_and_done_final_content() -> None:
    """stream() 收到 final_answer 事件时应透传并回填 done.final_content。"""

    final_text = "按你的问题顺序：待办已查询，嘉兴天气为多云 18-24℃。"
    fake_snapshot = SimpleNamespace(
        tasks=[],
        values={
            "messages": [
                HumanMessage(content="查待办并看天气", id="human-final"),
                AIMessage(content=final_text),
            ]
        },
    )
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "final_answer",
                "data": {"content": final_text, "meta": {"coverage_pass": True}},
                "node": "final_composer",
            }
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: None
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="查待办并看天气", thread_id="thread-final", user_id=1)
        )

    final_events = [payload for event, payload in events if event == "final_answer"]
    assert len(final_events) == 1
    assert final_events[0]["content"] == final_text
    assert final_events[0]["meta"]["coverage_pass"] is True

    done_events = [payload for event, payload in events if event == "done"]
    assert len(done_events) == 1
    assert done_events[0]["final_content"] == final_text


def test_interrupt_event_payload_includes_frozen_required_fields():
    """interrupt 事件应包含 reason/message 必填字段并保留兼容字段。"""

    fake_snapshot = SimpleNamespace(
        tasks=[
            SimpleNamespace(
                interrupts=[
                    SimpleNamespace(
                        value={
                            "action_requests": [
                                {
                                    "name": "todo_confirm",
                                    "args": {"_display_message": "请确认是否执行删除"},
                                }
                            ]
                        }
                    )
                ]
            )
        ],
        values={"messages": []},
    )
    fake_graph = _FakeGraph(chunks=[], snapshot=fake_snapshot)

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: None
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="删除今天的待办", thread_id="thread-int", user_id=1)
        )

    interrupt_events = [payload for event, payload in events if event == "interrupt"]
    assert len(interrupt_events) == 1
    payload = interrupt_events[0]

    assert payload["reason"] == "todo_confirm"
    assert payload["message"] == "请确认是否执行删除"
    assert payload["recoverable"] is True
    assert payload["thread_id"] == "thread-int"
    assert "interrupt_id" in payload
    assert isinstance(payload.get("value"), dict)


def test_stream_done_payload_handles_list_content_without_error():
    """stream() 在 AIMessage.content 为 list 时应正常补发文本，不应抛异常。"""

    fake_snapshot = SimpleNamespace(
        tasks=[],
        values={
            "messages": [
                HumanMessage(content="你好", id="human-1"),
                AIMessage(content=[{"type": "text", "text": "你好！"}]),
            ]
        },
    )
    fake_graph = _FakeGraph(chunks=[], snapshot=fake_snapshot)

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: None
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="你好", thread_id="thread-list", user_id=1)
        )

    event_types = [event for event, _ in events]
    assert "error" not in event_types

    token_payloads = [payload for event, payload in events if event == "token"]
    assert any(p.get("content") == "你好！" for p in token_payloads)

    done_events = [payload for event, payload in events if event == "done"]
    assert len(done_events) == 1
    assert done_events[0]["thread_id"] == "thread-list"


def test_format_sse_supports_date_serialization():
    """_format_sse 应能序列化 date 对象，避免 result 事件崩溃。"""

    svc = ChatService()
    raw = svc._format_sse("result", {"data_type": "sql_result", "data": [{"date": date(2025, 6, 30)}]})
    text = raw.decode("utf-8")

    assert "2025-06-30" in text
    assert text.startswith("event: result")


def test_stream_exception_fallback_does_not_duplicate_human_message():
    """stream() 进入异常兜底时，human 只应写入一次。"""

    saved_roles: list[str] = []

    def _fake_save_message(*args, **kwargs):
        saved_roles.append(kwargs.get("role"))
        return None

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        raise RuntimeError("boom")

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", _fake_save_message
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="测试异常", thread_id="thread-ex", user_id=1)
        )

    assert [event for event, _ in events] == ["init", "error"]
    assert saved_roles.count("human") == 1
    assert saved_roles.count("ai") == 1


def test_unknown_data_type_fallback_test_payload_is_forwarded_without_drop() -> None:
    """unknown_data_type_fallback_test：未知 data_type 不应在后端流中被静默丢弃。"""

    fake_snapshot = SimpleNamespace(tasks=[], values={"messages": []})
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "result",
                "data": {
                    "data_type": "custom_widget_v2",
                    "data": {"raw": "opaque-payload"},
                    "message": "未知类型结果",
                },
                "node": "custom_expert",
            }
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: None
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="返回未知类型结果", thread_id="thread-unknown", user_id=1)
        )

    result_events = [payload for event, payload in events if event == "result"]
    assert len(result_events) == 1
    payload = result_events[0]

    assert payload["data_type"] == "custom_widget_v2"
    assert payload["type"] == "custom_widget_v2"
    assert payload["content"] == "未知类型结果"
    assert payload["meta"]["node"] == "custom_expert"


def test_sse_resume_dedup_test_result_payload_exposes_event_id_and_sequence() -> None:
    """sse_resume_dedup_test：result 事件应透出 event_id/sequence_number 供前端去重排序。"""

    fake_snapshot = SimpleNamespace(tasks=[], values={"messages": []})
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "result",
                "data": {
                    "data_type": "todo_list",
                    "data": {"todos": [{"id": 1001, "title": "补齐门禁测试"}]},
                    "message": "找到 1 条待办",
                    "envelope": {
                        "id": "evt-resume-0007",
                        "source": "todo_expert",
                        "specversion": "1.0",
                        "type": "result",
                        "sequence_number": 7,
                        "timestamp": "2026-03-08T08:00:00+00:00",
                        "thread_id": "thread-resume-dedup",
                        "run_id": "run-resume-dedup",
                    },
                },
                "node": "todo_expert",
            }
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: None
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="测试去重字段", thread_id="thread-resume-dedup", user_id=1)
        )

    result_events = [payload for event, payload in events if event == "result"]
    assert len(result_events) == 1
    payload = result_events[0]

    assert "event_id" not in payload
    assert "sequence_number" not in payload
    assert payload["envelope"]["id"] == "evt-resume-0007"
    assert payload["envelope"]["sequence_number"] == 7



def test_stream_fallback_emits_final_ai_text_even_after_result_placeholder() -> None:
    """先收到 result 占位消息时，流末仍应补发最终 AI 正文。"""

    final_text = """按你的问题顺序，逐项回复如下：
1. 嘉兴天气：未来一周多云转晴，气温 12-21℃。
2. 画圆：
![生成的图表](/api/v1/assets/proxy/demo/chart.png)
以上问题已全部覆盖。"""
    fake_snapshot = SimpleNamespace(
        tasks=[],
        values={
            "messages": [
                HumanMessage(content="查询嘉兴近一周的天气，再帮我画一个圆", id="human-chart"),
                AIMessage(content=final_text),
            ]
        },
    )
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "result",
                "data": {
                    "data_type": "image",
                    "data": {"url": "/api/v1/assets/proxy/demo/chart.png"},
                    "message": "图表已生成",
                },
                "node": "fig_inter",
            }
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
        "app.repositories.chat_repo.save_message", lambda *args, **kwargs: None
    ), patch.object(ChatService, "get_graph", _fake_get_graph):
        svc = ChatService()
        events = _collect_events(
            svc.stream(prompt="查询嘉兴近一周的天气，再帮我画一个圆", thread_id="thread-chart", user_id=1)
        )

    token_events = [payload for event, payload in events if event == "token"]
    assert any(payload.get("content") == final_text for payload in token_events)

    done_events = [payload for event, payload in events if event == "done"]
    assert len(done_events) == 1
    assert done_events[0]["final_content"] == final_text


def test_resume_fallback_emits_final_ai_text_even_after_result_placeholder() -> None:
    """恢复流同样不能因为 result 占位消息而丢掉最终 AI 正文。"""

    final_text = """按你的问题顺序，逐项回复如下：
1. 嘉兴天气：未来一周多云转晴，气温 12-21℃。
2. 画圆：
![生成的图表](/api/v1/assets/proxy/demo/chart.png)
以上问题已全部覆盖。"""
    fake_snapshot = SimpleNamespace(
        tasks=[],
        values={
            "messages": [
                AIMessage(content=final_text),
            ]
        },
    )
    fake_graph = _FakeGraph(
        chunks=[
            {
                "type": "result",
                "data": {
                    "data_type": "image",
                    "data": {"url": "/api/v1/assets/proxy/demo/chart.png"},
                    "message": "图表已生成",
                },
                "node": "fig_inter",
            }
        ],
        snapshot=fake_snapshot,
    )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    async def _fake_get_checkpointer():
        return _FakeCheckpoint()

    with patch("app.db.postgres_checkpoint.get_checkpointer", _fake_get_checkpointer), patch.object(
        ChatService, "get_graph", _fake_get_graph
    ):
        events = _collect_events(
            sse_resume_stream(thread_id="thread-chart-resume", decision={"type": "accept"}, user_id=1)
        )

    token_events = [payload for event, payload in events if event == "token"]
    assert any(payload.get("content") == final_text for payload in token_events)

    done_events = [payload for event, payload in events if event == "done"]
    assert len(done_events) == 1
    assert done_events[0]["final_content"] == final_text
