"""MetricService 共享 engine 与 runtime owner 契约测试。"""

from __future__ import annotations

import app.services.metric_service as metric_module
from app.core.cache_registry import reset_cache_registry


def setup_function() -> None:
    reset_cache_registry()
    metric_module.reset_metric_service()


def test_metric_service_reuses_shared_session_engines(monkeypatch) -> None:
    """MetricService 默认应复用 app.db.session 的共享 engine。"""

    chat_engine = object()
    analytics_engine = object()

    monkeypatch.setattr(metric_module, "engine", chat_engine)
    monkeypatch.setattr(metric_module, "analytics_engine", analytics_engine)

    service = metric_module.MetricService()

    assert service.chat_engine is chat_engine
    assert service.data_engine is analytics_engine


def test_get_metric_service_reuses_registry_instance(monkeypatch) -> None:
    """get_metric_service 应复用 registry 中的共享实例。"""

    chat_engine = object()
    analytics_engine = object()
    monkeypatch.setattr(metric_module, "engine", chat_engine)
    monkeypatch.setattr(metric_module, "analytics_engine", analytics_engine)

    service_1 = metric_module.get_metric_service()
    service_2 = metric_module.get_metric_service()

    assert service_1 is service_2
    assert service_1.chat_engine is chat_engine
    assert service_1.data_engine is analytics_engine


def test_reset_metric_service_drops_shared_instance(monkeypatch) -> None:
    """reset_metric_service 后下次获取应重新创建实例。"""

    created: list[object] = []

    class _FakeMetricService:
        def __init__(self) -> None:
            created.append(self)
            self.chat_engine = object()
            self.data_engine = object()

    monkeypatch.setattr(metric_module, "MetricService", _FakeMetricService)

    first = metric_module.get_metric_service()
    metric_module.reset_metric_service()
    second = metric_module.get_metric_service()

    assert first is not second
    assert len(created) == 2
