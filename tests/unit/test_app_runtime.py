"""应用级 runtime 生命周期测试。"""

from __future__ import annotations

import asyncio

from app.core.runtime import AppRuntime, GraphRuntime


async def _close_marker(bucket: list[str]) -> None:
    bucket.append("closed")


def test_app_runtime_aclose_executes_registered_cleanup() -> None:
    """AppRuntime 应按注册顺序的逆序执行清理回调。"""

    events: list[str] = []
    runtime = AppRuntime(
        db=None,
        checkpointer=None,
        tracer=None,
        asset_service=None,
        graphs=GraphRuntime(default_multi_agent_graph=None),
        cache_registry={},
        cleanup_callbacks=[lambda: _close_marker(events)],
    )

    asyncio.run(runtime.aclose())

    assert events == ["closed"]
