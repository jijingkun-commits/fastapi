"""请求观测范围解析器。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.observability.module_registry import resolve_observed_module


class RequestMetricScope(str, Enum):
    """总览分钟桶的观测范围。"""

    ALL_BUSINESS = "all_business"
    USER_QUESTION = "user_question"
    ADMIN_OPERATION = "admin_operation"


@dataclass(frozen=True)
class ResolvedRequestMetricContext:
    """请求观测结构化 contract。"""

    scope: RequestMetricScope
    module_key: str
    module_label: str
    is_business_request: bool


ADMIN_OPERATION_PREFIXES: tuple[str, ...] = (
    "/api/v1/admin-overview",
    "/api/v1/health",
)
QUESTION_REQUEST_PREFIXES: tuple[str, ...] = (
    "/api/v1/chat/stream",
    "/api/v1/chat/completions",
)


def resolve_request_metric_context(path: str) -> ResolvedRequestMetricContext:
    """把请求路径解析为分钟桶写入口径。"""

    normalized_path = str(path or "")
    module_key, module_label = resolve_observed_module(normalized_path)

    if any(normalized_path.startswith(prefix) for prefix in ADMIN_OPERATION_PREFIXES):
        return ResolvedRequestMetricContext(
            scope=RequestMetricScope.ADMIN_OPERATION,
            module_key=module_key,
            module_label=module_label,
            is_business_request=False,
        )

    if any(normalized_path.startswith(prefix) for prefix in QUESTION_REQUEST_PREFIXES):
        return ResolvedRequestMetricContext(
            scope=RequestMetricScope.USER_QUESTION,
            module_key=module_key,
            module_label=module_label,
            is_business_request=True,
        )

    return ResolvedRequestMetricContext(
        scope=RequestMetricScope.ALL_BUSINESS,
        module_key=module_key,
        module_label=module_label,
        is_business_request=True,
    )


__all__ = [
    "RequestMetricScope",
    "ResolvedRequestMetricContext",
    "resolve_request_metric_context",
]
