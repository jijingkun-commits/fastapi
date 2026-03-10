"""RunControlService runtime owner 收口测试。"""

from __future__ import annotations

import app.services.run_control_service as run_control_module
from app.core.cache_registry import reset_cache_registry


def setup_function() -> None:
    reset_cache_registry()
    run_control_module.reset_run_control_service()


def test_get_run_control_service_reuses_registry_instance() -> None:
    """同一进程内应复用 registry 中的 RunControlService 实例。"""

    service_1 = run_control_module.get_run_control_service()
    service_2 = run_control_module.get_run_control_service()

    assert service_1 is service_2


def test_reset_run_control_service_drops_shared_instance() -> None:
    """reset_run_control_service 后下次获取应重新创建实例。"""

    first = run_control_module.get_run_control_service()
    run_control_module.reset_run_control_service()
    second = run_control_module.get_run_control_service()

    assert first is not second
