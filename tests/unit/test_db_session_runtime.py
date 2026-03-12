"""数据库 runtime 生命周期测试。"""

from __future__ import annotations

import importlib

import app.core.config as config_module
import app.db.session as session_module


class _FakeEngine:
    def __init__(self) -> None:
        self.dispose_calls = 0

    def dispose(self) -> None:
        self.dispose_calls += 1


def test_get_database_runtime_returns_shared_contract(monkeypatch) -> None:
    """共享 DB contract 应暴露当前 engine 与 session factory。"""

    chat_engine = object()
    analytics_engine = object()
    session_factory = object()

    monkeypatch.setattr(session_module, "engine", chat_engine)
    monkeypatch.setattr(session_module, "analytics_engine", analytics_engine)
    monkeypatch.setattr(session_module, "SessionLocal", session_factory)

    runtime = session_module.get_database_runtime()

    assert runtime.engine is chat_engine
    assert runtime.analytics_engine is analytics_engine
    assert runtime.session_factory is session_factory


def test_close_database_runtime_disposes_both_engines(monkeypatch) -> None:
    """关闭 DB runtime 时应释放 chat/analytics 两个 engine。"""

    chat_engine = _FakeEngine()
    analytics_engine = _FakeEngine()

    monkeypatch.setattr(session_module, "engine", chat_engine)
    monkeypatch.setattr(session_module, "analytics_engine", analytics_engine)

    session_module.close_database_runtime()

    assert chat_engine.dispose_calls == 1
    assert analytics_engine.dispose_calls == 1


def test_db_echo_should_default_to_false_when_env_missing(monkeypatch) -> None:
    """未显式配置时，DB_ECHO 应保持关闭，避免常驻服务打印原始 SQL。"""

    with monkeypatch.context() as scoped:
        scoped.setenv("ENV", "test")
        scoped.delenv("DB_ECHO", raising=False)
        reloaded = importlib.reload(config_module)
        assert reloaded.DB_ECHO is False

    importlib.reload(config_module)
