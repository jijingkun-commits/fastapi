"""PostgreSQL checkpoint 线程清理测试。"""

import asyncio

import pytest

from app.db import postgres_checkpoint


class _FakeCheckpointer:
    def __init__(self, checkpoint_found: bool):
        self.checkpoint_found = checkpoint_found
        self.deleted_thread_id = None
        self.configs = []

    async def aget_tuple(self, config):
        self.configs.append(config)
        return object() if self.checkpoint_found else None

    async def adelete_thread(self, thread_id: str):
        self.deleted_thread_id = thread_id


def test_delete_thread_checkpoint_should_delete_and_close(monkeypatch) -> None:  # noqa: ANN001
    """清理线程 checkpoint 时应调用官方 delete_thread 并关闭连接。"""

    fake = _FakeCheckpointer(checkpoint_found=True)
    closed = []

    async def _fake_get_checkpointer():
        return fake

    async def _fake_close_checkpointer():
        closed.append(True)

    monkeypatch.setattr(postgres_checkpoint, "get_checkpointer", _fake_get_checkpointer)
    monkeypatch.setattr(postgres_checkpoint, "close_checkpointer", _fake_close_checkpointer)

    result = asyncio.run(postgres_checkpoint.delete_thread_checkpoint("  thread-1  "))

    assert result == {"thread_id": "thread-1", "checkpoint_found": True}
    assert fake.deleted_thread_id == "thread-1"
    assert fake.configs == [{"configurable": {"thread_id": "thread-1"}}]
    assert closed == [True]


def test_delete_thread_checkpoint_should_reject_empty_thread_id() -> None:
    """空 thread_id 应 fail fast，避免误删全表。"""

    with pytest.raises(ValueError, match="thread_id"):
        asyncio.run(postgres_checkpoint.delete_thread_checkpoint("   "))
