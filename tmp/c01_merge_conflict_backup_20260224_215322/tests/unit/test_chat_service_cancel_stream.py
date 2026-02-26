"""聊天流取消路径测试骨架（中文注释）。

本文件用于 C01 红灯阶段，锁定取消路径的协议与接口契约。
"""

from __future__ import annotations

from app.ai import events
from app.main import app


def test_cancel_stream_event_type_should_include_stopped() -> None:
    """EventType 应包含 stopped 终态。"""

    allowed = set(getattr(events.EventType, "__args__", ()))
    assert "stopped" in allowed, "EventType 缺少 stopped"


def test_cancel_stream_should_define_stopped_event_helper() -> None:
    """事件层应提供 stopped_event 构造函数。"""

    assert hasattr(events, "stopped_event"), "缺少 stopped_event 事件辅助函数"


def test_cancel_api_route_should_exist() -> None:
    """应暴露 run_id 级取消接口。"""

    found = False
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        if "POST" in methods and path == "/api/v1/chat/runs/{run_id}/cancel":
            found = True
            break

    assert found, "缺少 POST /api/v1/chat/runs/{run_id}/cancel 接口"
