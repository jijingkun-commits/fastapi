"""总览观测范围解析测试。"""

from __future__ import annotations

from app.observability.request_scope_resolver import (
    RequestMetricScope,
    resolve_request_metric_context,
)


def test_resolve_user_question_scope_for_chat_stream() -> None:
    """聊天提问入口应归类为 user_question。"""

    resolved = resolve_request_metric_context("/api/v1/chat/stream")

    assert resolved.scope is RequestMetricScope.USER_QUESTION
    assert resolved.module_key == "chat"
    assert resolved.module_label == "对话服务"
    assert resolved.is_business_request is True


def test_resolve_all_business_scope_for_data_admin() -> None:
    """业务管理接口应归类为 all_business。"""

    resolved = resolve_request_metric_context("/api/v1/data-admin/metrics/stats")

    assert resolved.scope is RequestMetricScope.ALL_BUSINESS
    assert resolved.module_key == "data"
    assert resolved.module_label == "问数管理"
    assert resolved.is_business_request is True


def test_resolve_admin_operation_scope_for_admin_overview() -> None:
    """总览自身请求应收敛为 admin_operation，不参与业务质量口径。"""

    resolved = resolve_request_metric_context("/api/v1/admin-overview/summary")

    assert resolved.scope is RequestMetricScope.ADMIN_OPERATION
    assert resolved.module_key == "admin_overview"
    assert resolved.module_label == "总览驾驶舱"
    assert resolved.is_business_request is False


def test_resolve_health_path_to_non_business_scope() -> None:
    """健康检查请求不应污染业务请求质量。"""

    resolved = resolve_request_metric_context("/api/v1/health")

    assert resolved.scope is RequestMetricScope.ADMIN_OPERATION
    assert resolved.module_key == "system"
    assert resolved.module_label == "系统接口"
    assert resolved.is_business_request is False


def test_resolve_unknown_api_path_to_stable_business_fallback() -> None:
    """未注册业务 API 也应得到稳定 fallback contract。"""

    resolved = resolve_request_metric_context("/api/v1/unknown-endpoint")

    assert resolved.scope is RequestMetricScope.ALL_BUSINESS
    assert resolved.module_key == "system"
    assert resolved.module_label == "系统接口"
    assert resolved.is_business_request is True
