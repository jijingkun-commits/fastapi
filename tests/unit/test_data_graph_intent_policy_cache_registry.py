"""data_graph 意图策略缓存注册表测试。"""

from __future__ import annotations

from unittest.mock import patch

import app.ai.workflow.data_graph as data_graph
from app.core.cache_registry import reset_cache_registry



def test_data_graph_intent_policy_cache_reuses_registry_slot() -> None:
    """第二次加载应命中 registry cache，不重复读配置。"""

    reset_cache_registry()

    with patch(
        "app.services.system_config_service.SystemConfigService.get",
        side_effect=[{"mode": "strict"}, {"mode": "loose"}],
    ) as mocked_get:
        first = data_graph._load_data_graph_intent_policy(force_refresh=False)
        second = data_graph._load_data_graph_intent_policy(force_refresh=False)

    assert first == {"mode": "strict"}
    assert second == {"mode": "strict"}
    assert mocked_get.call_count == 1
    assert data_graph._get_data_graph_intent_policy_cache_meta()["cache_hit"] is True



def test_invalidate_data_graph_intent_policy_cache_forces_reload() -> None:
    """显式失效后应重新读取配置。"""

    reset_cache_registry()

    with patch(
        "app.services.system_config_service.SystemConfigService.get",
        side_effect=[{"mode": "strict"}, {"mode": "loose"}],
    ) as mocked_get:
        first = data_graph._load_data_graph_intent_policy(force_refresh=False)
        data_graph.invalidate_data_graph_intent_policy_cache()
        second = data_graph._load_data_graph_intent_policy(force_refresh=False)

    assert first == {"mode": "strict"}
    assert second == {"mode": "loose"}
    assert mocked_get.call_count == 2
