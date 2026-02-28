"""planner 策略路由测试。"""

import app.ai.workflow.multi_agent_graph as graph


def test_strategy_router_prefers_tool_call_when_capability_available(monkeypatch) -> None:
    """auto 策略下，具备 tool_call 能力应走主路径。"""
    monkeypatch.delenv("PLANNER_STRUCTURED_STRATEGY", raising=False)
    monkeypatch.delenv("PLANNER_DISABLE_TOOL_CALL", raising=False)
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": True, "supports_structured_output": True},
    )

    meta = graph._resolve_planner_structured_strategy(object())

    assert meta["strategy"] == "tool_call_primary"
    assert meta["supports_tool_call"] is True
    assert meta["tool_call_disabled"] is False


def test_strategy_router_forced_legacy_overrides_capability(monkeypatch) -> None:
    """显式指定 legacy_json_object 时应强制走 legacy。"""
    monkeypatch.setenv("PLANNER_STRUCTURED_STRATEGY", "legacy_json_object")
    monkeypatch.delenv("PLANNER_DISABLE_TOOL_CALL", raising=False)
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": True, "supports_structured_output": True},
    )

    meta = graph._resolve_planner_structured_strategy(object())

    assert meta["strategy"] == "legacy_json_object"
    assert meta["forced_strategy"] == "legacy_json_object"


def test_strategy_router_disable_tool_call_has_highest_priority(monkeypatch) -> None:
    """关闭 tool_call 开关后，应直接退回 legacy。"""
    monkeypatch.setenv("PLANNER_STRUCTURED_STRATEGY", "tool_call_primary")
    monkeypatch.setenv("PLANNER_DISABLE_TOOL_CALL", "true")
    monkeypatch.setattr(
        graph,
        "get_llm_capabilities",
        lambda _llm: {"supports_tool_call": True, "supports_structured_output": True},
    )

    meta = graph._resolve_planner_structured_strategy(object())

    assert meta["strategy"] == "legacy_json_object"
    assert meta["tool_call_disabled"] is True
