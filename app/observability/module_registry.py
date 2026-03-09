"""总览观测模块注册表。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObservedModuleRule:
    """请求路径与模块映射规则。"""

    prefix: str
    key: str
    label: str


OBSERVED_MODULE_RULES: tuple[ObservedModuleRule, ...] = (
    ObservedModuleRule(prefix="/api/v1/admin-overview", key="admin_overview", label="总览驾驶舱"),
    ObservedModuleRule(prefix="/api/v1/access-admin", key="access", label="访问控制"),
    ObservedModuleRule(prefix="/api/v1/llm-admin", key="llm", label="LLM 模型配置"),
    ObservedModuleRule(prefix="/api/v1/skill-admin", key="skill", label="技能管理"),
    ObservedModuleRule(prefix="/api/v1/system-admin", key="system", label="系统配置"),
    ObservedModuleRule(prefix="/api/v1/data-admin", key="data", label="问数管理"),
    ObservedModuleRule(prefix="/api/v1/memory-admin", key="memory", label="记忆管理"),
    ObservedModuleRule(prefix="/api/v1/chat", key="chat", label="对话服务"),
    ObservedModuleRule(prefix="/api/v1/todo", key="todo", label="待办服务"),
    ObservedModuleRule(prefix="/api/v1/user", key="user", label="用户管理"),
    ObservedModuleRule(prefix="/api/v1/auth", key="auth", label="认证服务"),
)


def resolve_observed_module(path: str) -> tuple[str, str]:
    """将请求路径解析为稳定模块标识。"""

    normalized_path = str(path or "")
    for rule in OBSERVED_MODULE_RULES:
        if normalized_path.startswith(rule.prefix):
            return rule.key, rule.label
    return "system", "系统接口"


def get_observed_module_label(module_key: str) -> str:
    """根据模块 key 返回稳定展示文案。"""

    for rule in OBSERVED_MODULE_RULES:
        if rule.key == module_key:
            return rule.label
    return module_key or "系统接口"


__all__ = ["ObservedModuleRule", "OBSERVED_MODULE_RULES", "resolve_observed_module", "get_observed_module_label"]
