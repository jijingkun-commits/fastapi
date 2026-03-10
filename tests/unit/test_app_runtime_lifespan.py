"""lifespan 与 runtime 绑定测试。"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI

import app.main as main_module


class _FakeRuntime:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


def test_lifespan_sets_runtime_on_app_state_and_closes(monkeypatch) -> None:
    """lifespan 应挂载 runtime，并在退出时统一清理。"""

    runtime = _FakeRuntime()

    async def _fake_build_runtime():
        return runtime

    monkeypatch.setattr(main_module, "build_runtime", _fake_build_runtime, raising=False)

    app = FastAPI()

    async def _run() -> None:
        async with main_module.lifespan(app):
            assert app.state.runtime is runtime
            assert runtime.closed is False
        assert runtime.closed is True

    asyncio.run(_run())
