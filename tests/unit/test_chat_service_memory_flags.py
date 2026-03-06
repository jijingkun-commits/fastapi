"""聊天文档记忆单开关解析测试。"""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from app.services import chat_service
from app.services.chat_service import ChatService


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return None


class _FakeDB:
    def query(self, *args, **kwargs):
        return _FakeQuery()


@contextmanager
def _fake_get_db_context():
    yield _FakeDB()


def test_document_memory_recall_switch_should_follow_master_config(monkeypatch) -> None:  # noqa: ANN001
    """召回开关应统一跟随 feature.enable_document_memory。"""

    monkeypatch.delenv("ENABLE_DOCUMENT_MEMORY", raising=False)
    captured: list[str] = []

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            captured.append(key)
            return True

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_recall_enabled(False) is True
    assert captured == ["feature.enable_document_memory"]


def test_document_memory_flush_switch_should_follow_master_env_override(monkeypatch) -> None:  # noqa: ANN001
    """写入开关应统一跟随 ENABLE_DOCUMENT_MEMORY 环境变量。"""

    monkeypatch.setenv("ENABLE_DOCUMENT_MEMORY", "false")

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            return True

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_flush_enabled(True) is False


def test_document_memory_hybrid_switch_should_follow_master_config(monkeypatch) -> None:  # noqa: ANN001
    """混合检索开关应统一跟随 feature.enable_document_memory。"""

    monkeypatch.delenv("ENABLE_DOCUMENT_MEMORY", raising=False)
    captured: list[str] = []

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            captured.append(key)
            return False

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_hybrid_enabled(True) is False
    assert captured == ["feature.enable_document_memory"]


def test_memory_intent_async_switch_should_follow_config(monkeypatch) -> None:  # noqa: ANN001
    """异步入队开关应读取 memory.intent_async_enabled。"""

    monkeypatch.delenv("MEMORY_INTENT_ASYNC_ENABLED", raising=False)
    captured: list[str] = []

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            captured.append(key)
            return True

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_memory_intent_async_enabled(False) is True
    assert captured == ["memory.intent_async_enabled"]


def test_persist_memory_should_enqueue_only_when_async_enabled(monkeypatch) -> None:  # noqa: ANN001
    """异步模式应只入队，不执行同步 flush 判定。"""

    called: dict[str, object] = {}

    class _Job:
        id = 88
        status = "pending"

    def _fake_enqueue(*args, **kwargs):  # noqa: ANN001
        called.update(kwargs)
        return _Job(), True

    def _unexpected_flush(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("async 模式不应调用 flush_document_memory")

    def _unexpected_recall(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("async 模式不应调用 recall_document_memory")

    monkeypatch.setattr(chat_service, "enqueue_memory_intent_job", _fake_enqueue)
    monkeypatch.setattr(chat_service, "flush_document_memory", _unexpected_flush)
    monkeypatch.setattr(chat_service, "recall_document_memory", _unexpected_recall)

    context = chat_service._persist_document_memory_context(
        object(),
        user_id=7,
        prompt="记住我喜欢美式",
        thread_id="thread-async",
        source_message_id=1001,
        document_memory_context="",
        document_memory_flush_enabled=True,
        document_memory_recall_enabled=True,
        memory_intent_async_enabled=True,
        document_memory_max_results=6,
        document_memory_max_injected_chars=1200,
        document_hybrid_min_score=0.05,
        document_vector_weight=0.7,
        document_text_weight=0.3,
    )

    assert context == ""
    assert called["user_id"] == 7
    assert called["source_thread_id"] == "thread-async"
    assert called["source_message_id"] == 1001
    assert called["user_text"] == "记住我喜欢美式"


def test_persist_memory_should_flush_when_async_disabled(monkeypatch) -> None:  # noqa: ANN001
    """异步开关关闭时应沿用同步 flush 路径。"""

    called = {"flush": 0, "recall": 0}

    def _unexpected_enqueue(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("sync 模式不应调用 enqueue_memory_intent_job")

    def _fake_flush(*args, **kwargs):  # noqa: ANN001
        called["flush"] += 1
        return 1

    def _fake_recall(*args, **kwargs):  # noqa: ANN001
        called["recall"] += 1
        return "最新记忆上下文"

    monkeypatch.setattr(chat_service, "enqueue_memory_intent_job", _unexpected_enqueue)
    monkeypatch.setattr(chat_service, "flush_document_memory", _fake_flush)
    monkeypatch.setattr(chat_service, "recall_document_memory", _fake_recall)

    context = chat_service._persist_document_memory_context(
        object(),
        user_id=7,
        prompt="记住我喜欢美式",
        thread_id="thread-sync",
        source_message_id=1002,
        document_memory_context="",
        document_memory_flush_enabled=True,
        document_memory_recall_enabled=True,
        memory_intent_async_enabled=False,
        document_memory_max_results=6,
        document_memory_max_injected_chars=1200,
        document_hybrid_min_score=0.05,
        document_vector_weight=0.7,
        document_text_weight=0.3,
    )

    assert context == "最新记忆上下文"
    assert called == {"flush": 1, "recall": 1}


def test_persist_memory_should_upsert_preference_and_recall_when_sync(monkeypatch) -> None:  # noqa: ANN001
    """同步模式下命中偏好时应写入 preference 并触发 recall。"""

    called = {"flush": 0, "preference": 0, "recall": 0}

    def _unexpected_enqueue(*args, **kwargs):  # noqa: ANN001
        raise AssertionError("sync 模式不应调用 enqueue_memory_intent_job")

    def _fake_flush(*args, **kwargs):  # noqa: ANN001
        called["flush"] += 1
        return 0

    def _fake_upsert_preference(*args, **kwargs):  # noqa: ANN001
        called["preference"] += 1
        return 1

    def _fake_recall(*args, **kwargs):  # noqa: ANN001
        called["recall"] += 1
        return "偏好已更新后的上下文"

    monkeypatch.setattr(chat_service, "enqueue_memory_intent_job", _unexpected_enqueue)
    monkeypatch.setattr(chat_service, "flush_document_memory", _fake_flush)
    monkeypatch.setattr(
        chat_service,
        "upsert_preference_document_memory",
        _fake_upsert_preference,
        raising=False,
    )
    monkeypatch.setattr(chat_service, "recall_document_memory", _fake_recall)

    context = chat_service._persist_document_memory_context(
        object(),
        user_id=7,
        prompt="永远记住，你叫hh",
        thread_id="thread-sync",
        source_message_id=1003,
        document_memory_context="",
        document_memory_flush_enabled=True,
        document_memory_recall_enabled=True,
        memory_intent_async_enabled=False,
        document_memory_max_results=6,
        document_memory_max_injected_chars=1200,
        document_hybrid_min_score=0.05,
        document_vector_weight=0.7,
        document_text_weight=0.3,
    )

    assert context == "偏好已更新后的上下文"
    assert called == {"flush": 1, "preference": 1, "recall": 1}


def test_stream_should_pass_memory_context_without_system_message_persistence(monkeypatch) -> None:  # noqa: ANN001
    """stream 输入应只保留 human 消息，记忆通过 memory_context 字段传递。"""

    captured: dict[str, object] = {}

    class _FakeGraph:
        async def astream(self, input_state, config, stream_mode):  # noqa: ANN001, ARG002
            captured["input_state"] = input_state
            yield {
                "type": "result",
                "data": {"data_type": "text", "data": None, "message": "ok"},
                "node": "supervisor",
            }

        async def aget_state(self, config):  # noqa: ANN001, ARG002
            return SimpleNamespace(
                tasks=[],
                values={"messages": [HumanMessage(content="hi"), AIMessage(content="ok")]},
            )

    async def _fake_get_graph(self, enable_thinking=False, model_id=None):  # noqa: ANN001, ARG002
        return _FakeGraph()

    monkeypatch.setattr(chat_service, "_is_document_memory_enabled", lambda fallback: True)
    monkeypatch.setattr(chat_service, "_is_document_memory_recall_enabled", lambda fallback: True)
    monkeypatch.setattr(chat_service, "_is_document_memory_flush_enabled", lambda fallback: False)
    monkeypatch.setattr(
        chat_service,
        "recall_document_memory",
        lambda *args, **kwargs: "以下是用户稳定偏好（跨会话生效，若与本轮明确指令冲突则以本轮为准）：\n- assistant.persona: 小哈",
    )

    async def _drain_stream():
        with patch("app.db.session.get_db_context", _fake_get_db_context), patch(
            "app.repositories.chat_repo.save_message",
            lambda *args, **kwargs: SimpleNamespace(id=123),
        ), patch.object(ChatService, "get_graph", _fake_get_graph):
            svc = ChatService()
            async for _ in svc.stream(prompt="你是谁", thread_id="thread-memory", user_id=2):
                pass

    asyncio.run(_drain_stream())

    input_state = captured["input_state"]
    assert input_state["memory_context"].startswith("以下是用户稳定偏好")
    assert len(input_state["messages"]) == 1
    assert isinstance(input_state["messages"][0], HumanMessage)
