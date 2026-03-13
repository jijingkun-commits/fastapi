"""AssetService runtime owner 收口测试。"""

from __future__ import annotations

import app.services.asset_service as asset_module
from app.core.cache_registry import reset_cache_registry


def setup_function() -> None:
    reset_cache_registry()


def test_get_asset_service_reuses_registry_instance(monkeypatch) -> None:
    """同一进程内应复用 registry 中的 AssetService 实例。"""

    created: list[str] = []

    class _FakeAssetService:
        def __init__(self) -> None:
            created.append("created")

    monkeypatch.setattr(asset_module, "AssetService", _FakeAssetService)

    service_1 = asset_module.get_asset_service()
    service_2 = asset_module.get_asset_service()

    assert service_1 is service_2
    assert created == ["created"]


def test_reset_cache_registry_drops_shared_asset_instance(monkeypatch) -> None:
    """清空公共 cache registry 后，下次获取应重新创建 AssetService。"""

    created: list[object] = []

    class _FakeAssetService:
        def __init__(self) -> None:
            created.append(self)

    monkeypatch.setattr(asset_module, "AssetService", _FakeAssetService)

    first = asset_module.get_asset_service()
    reset_cache_registry()
    second = asset_module.get_asset_service()

    assert first is not second
    assert len(created) == 2
