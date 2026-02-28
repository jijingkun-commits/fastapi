"""运行时恢复策略（中文注释）。

统一管理以下能力，避免 ChatService 与 workflow 层重复维护：
- 特性开关读取（环境变量）
- 插件注册表故障判定
- 插件链路降级触发条件
"""

from __future__ import annotations

import os

_TRUE_VALUES = {"1", "true", "yes", "on"}

PLUGIN_REGISTRY_ERROR_HINTS: tuple[str, ...] = (
    "plugin registry",
    "plugin_registry",
    "plugin init",
    "plugin load",
    "插件注册",
    "插件加载",
)


def is_feature_flag_enabled(env_name: str, fallback: bool = False) -> bool:
    """读取布尔开关，支持环境变量覆盖。"""

    raw_value = os.getenv(env_name)
    if raw_value is None:
        return fallback
    return raw_value.strip().lower() in _TRUE_VALUES


def is_runtime_recovery_enabled() -> bool:
    """运行时恢复开关（默认开启）。"""

    return is_feature_flag_enabled("ENABLE_RUNTIME_RECOVERY", True)


def is_plugin_registry_enabled() -> bool:
    """插件注册表开关（默认关闭）。"""

    return is_feature_flag_enabled("ENABLE_PLUGIN_REGISTRY", False)


def is_plugin_registry_error(error_text: str) -> bool:
    """判断异常是否命中插件注册表故障关键词。"""

    lowered = str(error_text or "").strip().lower()
    if not lowered:
        return False
    return any(hint in lowered for hint in PLUGIN_REGISTRY_ERROR_HINTS)


def should_degrade_on_plugin_failure(error_text: str) -> bool:
    """是否应触发插件链路降级。"""

    if not is_runtime_recovery_enabled():
        return False
    if not is_plugin_registry_enabled():
        return False
    return is_plugin_registry_error(error_text)
