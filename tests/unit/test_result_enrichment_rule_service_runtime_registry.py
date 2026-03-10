"""结果增强规则服务 runtime owner 收口测试。"""

from __future__ import annotations

import app.services.result_enrichment_rule_service as rule_module
from app.core.cache_registry import reset_cache_registry


def setup_function() -> None:
    reset_cache_registry()
    rule_module.reset_result_enrichment_rule_service()


def test_get_result_rule_service_reuses_registry_instance(monkeypatch) -> None:
    """同一进程内应复用 registry 中的规则服务实例。"""

    created: list[str] = []

    class _FakeResultRuleService:
        def __init__(self) -> None:
            created.append("created")

    monkeypatch.setattr(rule_module, "ResultEnrichmentRuleService", _FakeResultRuleService)

    service_1 = rule_module.get_result_enrichment_rule_service()
    service_2 = rule_module.get_result_enrichment_rule_service()

    assert service_1 is service_2
    assert created == ["created"]


def test_reset_result_rule_service_drops_shared_instance(monkeypatch) -> None:
    """reset_result_enrichment_rule_service 后下次获取应重新创建实例。"""

    created: list[object] = []

    class _FakeResultRuleService:
        def __init__(self) -> None:
            created.append(self)

    monkeypatch.setattr(rule_module, "ResultEnrichmentRuleService", _FakeResultRuleService)

    first = rule_module.get_result_enrichment_rule_service()
    rule_module.reset_result_enrichment_rule_service()
    second = rule_module.get_result_enrichment_rule_service()

    assert first is not second
    assert len(created) == 2
