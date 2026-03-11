import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from app.services.chat_service import ChatService


class _FakeGraph:
    def __init__(self):
        self.seen_input_state = None

    async def astream(self, input_state, config=None, stream_mode=None):
        self.seen_input_state = input_state
        if False:
            yield None

    async def aget_state(self, config):
        return SimpleNamespace(tasks=[], values={"messages": []})


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
