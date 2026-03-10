"""runtime 启动编排测试。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import app.core.runtime as runtime_module
from app.core.cache_registry import CacheRegistry


class _FakeSessionFactory:
    def __call__(self):
        return self

    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_runtime_prepares_images_dir_and_warms_resources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """build_runtime 应准备目录并完成核心/可选预热。"""

    calls: list[str] = []
    tracer = object()
    checkpointer = object()
    asset_service = object()
    graph = object()
    db_runtime = object()
    cache_registry = CacheRegistry()

    monkeypatch.setattr(runtime_module, "PUBLIC_DIR", str(tmp_path / "public"))
    monkeypatch.setattr(runtime_module, "INIT_DB_ON_STARTUP", False)
    monkeypatch.setattr(runtime_module, "setup_logging", lambda: calls.append("logging"))
    monkeypatch.setattr(runtime_module, "Settings", lambda: calls.append("settings"))
    monkeypatch.setattr(runtime_module, "SessionLocal", _FakeSessionFactory())
    monkeypatch.setattr(runtime_module.LLMConfigService, "load_from_db", lambda db: calls.append("llm"))
    monkeypatch.setattr(runtime_module.SystemConfigService, "load_from_db", lambda db: calls.append("system"))
    monkeypatch.setattr(runtime_module.LLMSceneService, "load_from_db", lambda db: calls.append("scene"))
    monkeypatch.setattr(
        runtime_module.LLMSceneService,
        "validate_startup_integrity",
        lambda: calls.append("validate"),
    )

    async def _fake_get_checkpointer():
        calls.append("checkpointer")
        return checkpointer

    monkeypatch.setattr(runtime_module, "get_checkpointer", _fake_get_checkpointer)
    monkeypatch.setattr(runtime_module, "get_tracer", lambda: calls.append("tracer") or tracer)
    monkeypatch.setattr(runtime_module, "get_database_runtime", lambda: calls.append("db") or db_runtime)
    monkeypatch.setattr(runtime_module, "close_database_runtime", lambda: calls.append("db-close"))
    monkeypatch.setattr(runtime_module, "get_cache_registry", lambda: calls.append("cache-registry") or cache_registry)
    monkeypatch.setattr(runtime_module, "reset_cache_registry", lambda: calls.append("cache-reset"))
    monkeypatch.setattr(runtime_module, "reset_run_control_service", lambda: calls.append("run-control-reset"))
    monkeypatch.setattr(runtime_module, "reset_multi_agent_graph_runtime", lambda: calls.append("graph-reset"))

    class _FakeRuleService:
        def refresh_rules(self):
            calls.append("rules")

    monkeypatch.setattr(
        runtime_module,
        "get_result_enrichment_rule_service",
        lambda: _FakeRuleService(),
    )
    monkeypatch.setattr(runtime_module, "get_asset_service", lambda: calls.append("asset") or asset_service)
    monkeypatch.setattr(runtime_module, "get_run_control_service", lambda: calls.append("run-control") or object())

    async def _fake_get_multi_agent_graph(enable_thinking: bool = False, model_id=None):
        calls.append(f"graph:{enable_thinking}:{model_id}")
        return graph

    monkeypatch.setattr(runtime_module, "get_multi_agent_graph", _fake_get_multi_agent_graph)

    runtime = asyncio.run(runtime_module.build_runtime())

    assert (tmp_path / "public" / "images").exists()
    assert runtime.db is db_runtime
    assert runtime.cache_registry is cache_registry
    assert runtime.checkpointer is checkpointer
    assert runtime.tracer is tracer
    assert runtime.asset_service is asset_service
    assert runtime.graphs.default_multi_agent_graph is graph
    assert runtime.cleanup_callbacks[0] is runtime_module.reset_cache_registry
    assert runtime.cleanup_callbacks[1] is runtime_module.reset_run_control_service
    assert runtime.cleanup_callbacks[2] is runtime_module.reset_multi_agent_graph_runtime
    assert runtime.cleanup_callbacks[3] is runtime_module.close_database_runtime
    assert calls == [
        "logging",
        "settings",
        "cache-registry",
        "run-control-reset",
        "cache-reset",
        "graph-reset",
        "db",
        "checkpointer",
        "llm",
        "system",
        "scene",
        "validate",
        "tracer",
        "rules",
        "asset",
        "run-control",
        "graph:False:None",
    ]


def test_build_runtime_degrades_when_optional_warmups_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """可选资源失败不应阻断 runtime 构建。"""

    monkeypatch.setattr(runtime_module, "PUBLIC_DIR", str(tmp_path / "public"))
    monkeypatch.setattr(runtime_module, "INIT_DB_ON_STARTUP", False)
    monkeypatch.setattr(runtime_module, "setup_logging", lambda: None)
    monkeypatch.setattr(runtime_module, "Settings", lambda: None)
    monkeypatch.setattr(runtime_module, "SessionLocal", _FakeSessionFactory())
    monkeypatch.setattr(runtime_module.LLMConfigService, "load_from_db", lambda db: None)
    monkeypatch.setattr(runtime_module.SystemConfigService, "load_from_db", lambda db: None)
    monkeypatch.setattr(runtime_module.LLMSceneService, "load_from_db", lambda db: None)
    monkeypatch.setattr(runtime_module.LLMSceneService, "validate_startup_integrity", lambda: None)
    monkeypatch.setattr(runtime_module, "get_tracer", lambda: object())
    monkeypatch.setattr(runtime_module, "get_cache_registry", lambda: CacheRegistry())
    monkeypatch.setattr(runtime_module, "reset_cache_registry", lambda: None)
    monkeypatch.setattr(runtime_module, "reset_run_control_service", lambda: None)
    monkeypatch.setattr(runtime_module, "reset_multi_agent_graph_runtime", lambda: None)
    monkeypatch.setattr(runtime_module, "get_database_runtime", lambda: object())
    monkeypatch.setattr(runtime_module, "close_database_runtime", lambda: None)

    async def _fake_get_checkpointer():
        return object()

    monkeypatch.setattr(runtime_module, "get_checkpointer", _fake_get_checkpointer)

    class _BrokenRuleService:
        def refresh_rules(self):
            raise RuntimeError("rule warmup failed")

    monkeypatch.setattr(
        runtime_module,
        "get_result_enrichment_rule_service",
        lambda: _BrokenRuleService(),
    )

    def _broken_asset_service():
        raise RuntimeError("asset failed")

    def _broken_run_control_service():
        raise RuntimeError("run control failed")

    async def _broken_graph(*args, **kwargs):
        raise RuntimeError("graph failed")

    monkeypatch.setattr(runtime_module, "get_asset_service", _broken_asset_service)
    monkeypatch.setattr(runtime_module, "get_run_control_service", _broken_run_control_service)
    monkeypatch.setattr(runtime_module, "get_multi_agent_graph", _broken_graph)

    runtime = asyncio.run(runtime_module.build_runtime())

    assert runtime.asset_service is None
    assert runtime.graphs.default_multi_agent_graph is None
