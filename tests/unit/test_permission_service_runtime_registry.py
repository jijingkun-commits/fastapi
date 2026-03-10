"""PermissionService runtime owner 收口测试。"""

from __future__ import annotations

import app.services.permission_service as permission_module
from app.core.cache_registry import reset_cache_registry


def setup_function() -> None:
    reset_cache_registry()
    permission_module.reset_permission_service()


def test_get_permission_service_reuses_registry_instance(monkeypatch) -> None:
    """同一进程内应复用 registry 中的 PermissionService 实例。"""

    created: list[str] = []

    class _FakePermissionService:
        def __init__(self) -> None:
            created.append("created")

    monkeypatch.setattr(permission_module, "PermissionService", _FakePermissionService)

    service_1 = permission_module.get_permission_service()
    service_2 = permission_module.get_permission_service()

    assert service_1 is service_2
    assert created == ["created"]


def test_reset_permission_service_drops_shared_instance(monkeypatch) -> None:
    """reset_permission_service 后下次获取应重新创建实例。"""

    created: list[object] = []

    class _FakePermissionService:
        def __init__(self) -> None:
            created.append(self)

    monkeypatch.setattr(permission_module, "PermissionService", _FakePermissionService)

    first = permission_module.get_permission_service()
    permission_module.reset_permission_service()
    second = permission_module.get_permission_service()

    assert first is not second
    assert len(created) == 2
