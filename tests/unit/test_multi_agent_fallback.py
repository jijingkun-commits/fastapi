"""多智能体 Supervisor 异常降级兜底测试。"""

from langchain_core.messages import HumanMessage

from app.ai.workflow.multi_agent_graph import (
    _build_stream_error_message,
    _is_model_access_error,
    fallback_router,
)


def test_model_access_error_detect_subscription_not_found() -> None:
    """应识别订阅缺失类错误。"""
    error_text = "Error code: 403 - {'code': 'SUBSCRIPTION_NOT_FOUND', 'message': 'No active subscription found for this group'}"
    assert _is_model_access_error(error_text) is True


def test_model_access_error_non_access_issue_should_be_false() -> None:
    """普通业务异常不应误判为模型权限错误。"""
    assert _is_model_access_error("ValueError: invalid todo id") is False


def test_fallback_router_supervisor_should_not_delegate_to_expert(monkeypatch) -> None:
    """Supervisor 权限异常应回到 supervisor_fallback，不允许专家兜底。"""
    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "true")
    monkeypatch.delenv("ENABLE_PLUGIN_REGISTRY", raising=False)

    route = fallback_router(
        node_name="supervisor",
        state={"messages": [HumanMessage(content="查询我的待办列表")]},
        error_text="Error code: 403 - {'code': 'SUBSCRIPTION_NOT_FOUND'}",
    )

    assert route["route"] == "friendly_error"
    assert route["runtime_recovery_state"]["fallback_route"] == "supervisor_fallback"
    assert "pending_handoff" not in route


def test_stream_error_message_should_not_leak_raw_error() -> None:
    """权限错误应返回稳定用户文案，而非底层异常原文。"""
    message = _build_stream_error_message("Error code: 403 - SUBSCRIPTION_NOT_FOUND")
    assert "模型服务当前不可用" in message
    assert "SUBSCRIPTION_NOT_FOUND" not in message
