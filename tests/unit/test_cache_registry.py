"""共享 cache registry 测试。"""

from __future__ import annotations

from app.core.cache_registry import CacheRegistry



def test_registry_reuses_named_dict_cache() -> None:
    """同名 dict cache 应复用同一实例。"""

    registry = CacheRegistry()

    cache_1 = registry.get_dict_cache("data_graph.intent_policy", {"payload": {}})
    cache_2 = registry.get_dict_cache("data_graph.intent_policy", {"payload": {"x": 1}})

    assert cache_1 is cache_2
    assert cache_2 == {"payload": {}}



def test_registry_clear_named_cache() -> None:
    """clear(name) 应清空命名缓存槽。"""

    registry = CacheRegistry()
    cache = registry.get_dict_cache("askdata.config", {"k": (set(), 0.0)})
    cache["other"] = ({"fdmdata"}, 1.0)

    registry.clear("askdata.config")

    assert cache == {}



def test_registry_reset_all_clears_caches_and_statuses() -> None:
    """reset_all() 应同时清空缓存内容和状态。"""

    registry = CacheRegistry()
    registry.get_dict_cache("slot", {"k": 1})
    registry.set_status("slot", "warmed")

    registry.reset_all()

    assert registry.get_dict_cache("slot", {}) == {}
    assert registry.get_status("slot") is None



def test_registry_get_or_create_reuses_generic_slot() -> None:
    """get_or_create 应复用同名通用槽位。"""

    registry = CacheRegistry()
    created: list[str] = []

    def _factory() -> object:
        created.append("created")
        return object()

    value_1 = registry.get_or_create("asset_service.instance", _factory)
    value_2 = registry.get_or_create("asset_service.instance", _factory)

    assert value_1 is value_2
    assert created == ["created"]



def test_registry_set_and_get_generic_slot() -> None:
    """set/get 应支持非 dict 共享资源。"""

    registry = CacheRegistry()
    marker = object()

    assert registry.get("missing") is None
    assert registry.set("shared.object", marker) is marker
    assert registry.get("shared.object") is marker
