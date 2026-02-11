"""多智能体 Supervisor 异常降级兜底测试。"""

from langchain_core.messages import HumanMessage

from app.ai.workflow.multi_agent_graph import (
    _build_stream_error_message,
    _build_supervisor_fallback_handoff,
    _is_model_access_error,
)


def test_model_access_error_detect_subscription_not_found():
    """应识别订阅缺失类错误。"""
    error_text = "Error code: 403 - {'code': 'SUBSCRIPTION_NOT_FOUND', 'message': 'No active subscription found for this group'}"
    assert _is_model_access_error(error_text) is True


def test_model_access_error_non_access_issue_should_be_false():
    """普通业务异常不应误判为模型权限错误。"""
    assert _is_model_access_error("ValueError: invalid todo id") is False


def test_supervisor_fallback_handoff_for_todo_query():
    """待办查询 + 403 时应降级路由到 todo_expert。"""
    state = {
        "messages": [HumanMessage(content="查询我的待办列表")],
    }

    handoff = _build_supervisor_fallback_handoff(
        state,
        "Error code: 403 - {'code': 'SUBSCRIPTION_NOT_FOUND'}",
    )

    assert handoff is not None
    assert handoff.get("target_agent") == "todo_expert"
    assert handoff.get("detected_intent") == "query_todo"
    assert handoff.get("frame", {}).get("todo_action") == "query"
    assert handoff.get("frame", {}).get("todo_fields", {}).get("status") == "pending"


def test_supervisor_fallback_handoff_non_todo_message_should_skip():
    """非待办输入不应触发待办兜底路由。"""
    state = {
        "messages": [HumanMessage(content="请帮我分析贷款余额趋势")],
    }

    handoff = _build_supervisor_fallback_handoff(
        state,
        "Error code: 403 - {'code': 'SUBSCRIPTION_NOT_FOUND'}",
    )

    assert handoff is None


def test_stream_error_message_should_not_leak_raw_error():
    """权限错误应返回稳定用户文案，而非底层异常原文。"""
    message = _build_stream_error_message("Error code: 403 - SUBSCRIPTION_NOT_FOUND")
    assert "模型服务当前不可用" in message
    assert "SUBSCRIPTION_NOT_FOUND" not in message

