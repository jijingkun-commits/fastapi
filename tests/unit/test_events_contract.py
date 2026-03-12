"""events 模块导出契约回归测试。"""

from __future__ import annotations

import importlib

import app.ai.events as events


def test_events_stop_contract_exports_are_stable():
    """chat_service 依赖的 stopped_event 导出必须稳定存在。"""

    required_symbols = ("stopped_event",)

    for symbol in required_symbols:
        assert hasattr(events, symbol), f"缺少导出: {symbol}"
        assert callable(getattr(events, symbol)), f"导出不可调用: {symbol}"


def test_chat_service_stopped_payload_uses_events_contract():
    """chat_service 应能通过事件契约构建 stopped 载荷。"""

    chat_service = importlib.import_module("app.services.chat_service")

    payload = chat_service._build_stopped_payload(
        thread_id="thread-debug-contract",
        run_id="run-debug-contract",
        reason="manual_stop",
    )

    assert payload == {
        "thread_id": "thread-debug-contract",
        "run_id": "run-debug-contract",
        "reason": "manual_stop",
        "version": 1,
    }
