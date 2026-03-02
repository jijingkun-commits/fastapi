"""PostgreSQL checkpointer 连接池化行为测试。"""

from __future__ import annotations

import asyncio

import pytest

import app.db.postgres_checkpoint as checkpoint_module


class _FakePool:
    """最小化异步连接池实现。"""

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.open_calls = 0
        self.close_calls = 0

    async def open(self) -> None:
        self.open_calls += 1

    async def close(self) -> None:
        self.close_calls += 1


class _FakeSaver:
    """最小化 checkpointer。"""

    def __init__(self, conn) -> None:
        self.conn = conn
        self.setup_calls = 0

    async def setup(self) -> None:
        self.setup_calls += 1


@pytest.fixture(autouse=True)
def _reset_checkpoint_state():
    checkpoint_module._checkpointer = None
    checkpoint_module._connection_pool = None
    checkpoint_module._init_lock = None
    checkpoint_module._setup_done = False
    yield
    checkpoint_module._checkpointer = None
    checkpoint_module._connection_pool = None
    checkpoint_module._init_lock = None
    checkpoint_module._setup_done = False


def test_get_checkpointer_initializes_pool_and_setup_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """重复获取 checkpointer 时只应初始化一次池和 setup。"""

    monkeypatch.setattr(checkpoint_module, "AsyncConnectionPool", _FakePool)
    monkeypatch.setattr(checkpoint_module, "AsyncPostgresSaver", _FakeSaver)

    checkpointer_1 = asyncio.run(checkpoint_module.get_checkpointer())
    checkpointer_2 = asyncio.run(checkpoint_module.get_checkpointer())

    assert checkpointer_1 is checkpointer_2
    assert isinstance(checkpoint_module._connection_pool, _FakePool)
    assert checkpoint_module._connection_pool.open_calls == 1
    assert checkpointer_1.setup_calls == 1


def test_close_checkpointer_releases_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    """关闭时应释放连接池并重置全局状态。"""

    monkeypatch.setattr(checkpoint_module, "AsyncConnectionPool", _FakePool)
    monkeypatch.setattr(checkpoint_module, "AsyncPostgresSaver", _FakeSaver)

    checkpointer = asyncio.run(checkpoint_module.get_checkpointer())
    pool = checkpoint_module._connection_pool

    asyncio.run(checkpoint_module.close_checkpointer())

    assert isinstance(checkpointer, _FakeSaver)
    assert isinstance(pool, _FakePool)
    assert pool.close_calls == 1
    assert checkpoint_module._connection_pool is None
    assert checkpoint_module._checkpointer is None


def test_is_checkpointer_busy_error_detection() -> None:
    """busy 错误识别应稳定。"""

    assert checkpoint_module.is_checkpointer_busy_error(RuntimeError("another command is already in progress"))
    assert checkpoint_module.is_checkpointer_busy_error(RuntimeError("sending query and params failed"))
    assert not checkpoint_module.is_checkpointer_busy_error(RuntimeError("query timeout"))
