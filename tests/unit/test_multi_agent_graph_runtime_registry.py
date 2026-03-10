"""多智能体图 runtime owner 收口测试。"""

from __future__ import annotations

import asyncio

from app.core.cache_registry import reset_cache_registry
import app.ai.workflow.runtime_graph_provider as graph_module


def setup_function() -> None:
    reset_cache_registry()
    graph_module.reset_multi_agent_graph_runtime()


def test_get_multi_agent_graph_reuses_registry_cache(monkeypatch) -> None:
    """同一事件循环内应复用 registry 中的图实例。"""

    created: list[tuple[bool, str | None]] = []

    async def _fake_create_multi_agent_graph(enable_thinking: bool = False, model_id: str = None):
        created.append((enable_thinking, model_id))
        return {"enable_thinking": enable_thinking, "model_id": model_id, "seq": len(created)}

    monkeypatch.setattr(graph_module, "create_multi_agent_graph", _fake_create_multi_agent_graph)

    async def _exercise():
        graph_1 = await graph_module.get_multi_agent_graph(enable_thinking=False, model_id=None)
        graph_2 = await graph_module.get_multi_agent_graph(enable_thinking=False, model_id=None)
        return graph_1, graph_2

    graph_1, graph_2 = asyncio.run(_exercise())

    assert graph_1 is graph_2
    assert created == [(False, None)]


def test_reset_multi_agent_graph_runtime_clears_registry_cache(monkeypatch) -> None:
    """reset_multi_agent_graph_runtime 后应重新创建图实例。"""

    created: list[object] = []

    async def _fake_create_multi_agent_graph(enable_thinking: bool = False, model_id: str = None):
        graph = object()
        created.append(graph)
        return graph

    monkeypatch.setattr(graph_module, "create_multi_agent_graph", _fake_create_multi_agent_graph)

    async def _exercise():
        graph_1 = await graph_module.get_multi_agent_graph()
        graph_module.reset_multi_agent_graph_runtime()
        graph_2 = await graph_module.get_multi_agent_graph()
        return graph_1, graph_2

    graph_1, graph_2 = asyncio.run(_exercise())

    assert graph_1 is not graph_2
    assert len(created) == 2
