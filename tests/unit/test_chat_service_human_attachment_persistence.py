import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from app.ai.utils.message_factory import create_ai_message
from app.services.chat_service import ChatService


class _FakeGraph:
    def __init__(self, *, snapshot_messages=None):
        self.seen_input_state = None
        self.snapshot_messages = list(snapshot_messages or [])

    async def astream(self, input_state, config=None, stream_mode=None):
        self.seen_input_state = input_state
        if False:
            yield None

    async def aget_state(self, config):
        return SimpleNamespace(tasks=[], values={"messages": self.snapshot_messages})


@contextmanager
def _fake_get_db_context():
    yield object()


async def _collect(async_gen):
    events = []
    async for chunk in async_gen:
        events.append(chunk)
    return events


def test_stream_should_persist_display_content_but_send_raw_prompt_to_runtime() -> None:
    fake_graph = _FakeGraph()
    saved_calls = []
    created_contents = []

    def _fake_save_message(*args, **kwargs):
        saved_calls.append(kwargs)
        return SimpleNamespace(id=123)

    def _fake_create_human_message(content, **kwargs):
        created_contents.append(content)
        return HumanMessage(content=content, id="human-test")

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.services.chat_service.get_db_context", _fake_get_db_context), patch(
        "app.services.chat_service._is_document_memory_enabled", lambda fallback: False
    ), patch(
        "app.services.chat_service._persist_document_memory_context",
        lambda *args, **kwargs: ("", False, None),
    ), patch(
        "app.services.chat_service.chat_repo.save_message", _fake_save_message
    ), patch(
        "app.services.chat_service.create_human_message", _fake_create_human_message
    ), patch.object(
        ChatService, "get_graph", _fake_get_graph
    ):
        svc = ChatService()
        asyncio.run(
            _collect(
                svc.stream(
                    prompt="请处理附件",
                    thread_id="thread-attach-1",
                    user_id=1,
                    attachments=[
                        {
                            "name": "e2e-note.txt",
                            "url": "/api/v1/assets/e2e-note.txt",
                            "mime_type": "text/plain",
                            "size": 12,
                            "object_key": "obj-note",
                        }
                    ],
                )
            )
        )

    assert created_contents == ["请处理附件"]
    assert saved_calls[0]["role"] == "human"
    assert saved_calls[0]["content"] == "请处理附件\n\n- [e2e-note.txt](/api/v1/assets/e2e-note.txt)"
    assert fake_graph.seen_input_state["semantic_payload"]["user_query"] == "请处理附件"
    assert fake_graph.seen_input_state["attachment_manifest"][0]["attachment_id"] == "obj-note"

def test_stream_done_fallback_should_use_current_turn_human_anchor() -> None:
    current_human = HumanMessage(content="当前轮问题", id="human-test")
    fake_graph = _FakeGraph(
        snapshot_messages=[
            HumanMessage(content="上一轮问题", id="human-old"),
            create_ai_message("上一轮结构化结果"),
            current_human,
            create_ai_message("当前轮结构化结果"),
        ]
    )

    def _fake_save_message(*args, **kwargs):
        return SimpleNamespace(id=123)

    def _fake_create_human_message(content, **kwargs):
        return current_human

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):
        return fake_graph

    with patch("app.services.chat_service.get_db_context", _fake_get_db_context), patch(
        "app.services.chat_service._is_document_memory_enabled", lambda fallback: False
    ), patch(
        "app.services.chat_service._persist_document_memory_context",
        lambda *args, **kwargs: ("", False, None),
    ), patch(
        "app.services.chat_service.chat_repo.save_message", _fake_save_message
    ), patch(
        "app.services.chat_service.create_human_message", _fake_create_human_message
    ), patch.object(
        ChatService, "get_graph", _fake_get_graph
    ), patch.object(
        ChatService, "_get_latest_ai_message_id", lambda self, thread_id: None
    ):
        svc = ChatService()
        chunks = asyncio.run(
            _collect(
                svc.stream(
                    prompt="当前轮问题",
                    thread_id="thread-done-fallback-1",
                    user_id=1,
                )
            )
        )

    payload = b"".join(chunks).decode("utf-8")
    assert "当前轮结构化结果" in payload
    assert "上一轮结构化结果" not in payload
