"""统一配置读取器：按契约解析 DB/环境变量配置（中文注释）。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.core.config_contract import CONFIG_SPECS, ConfigSpec, TOOL_POLICY_CONTRACT
from app.services.system_config_service import SystemConfigService

logger = logging.getLogger(__name__)

_TRUTHY = {"1", "true", "yes", "on", "enabled"}
_FALSY = {"0", "false", "no", "off", "disabled"}
_POLICY_FAIL_MODES = {"compat", "allow", "deny", "minimal"}
_EXECUTION_TASK_MODES = {
    "execute",
    "execution",
    "implementation",
    "implementation-card",
    "operation",
    "workflow",
}

_UNSET = object()


class ConfigResolver:
    """统一配置解析入口。"""

    @classmethod
    def get_spec(cls, key: str) -> ConfigSpec | None:
        """获取配置契约定义。"""

        return CONFIG_SPECS.get(key)

    @classmethod
    def get(cls, key: str, default: Any = _UNSET) -> Any:
        """按契约读取并解析配置值。"""

        spec = cls.get_spec(key)
        if spec is None:
            return None if default is _UNSET else default

        effective_default = spec.default if default is _UNSET else default
        raw_value = cls._read_raw(spec)
        return cls._coerce_value(raw_value, spec.value_type, effective_default)

    @classmethod
    def get_string(cls, key: str, default: str = "") -> str:
        """获取字符串配置。"""

        value = cls.get(key, default)
        return str(value) if value is not None else default

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        """获取整数配置。"""

        value = cls.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def get_float(cls, key: str, default: float = 0.0) -> float:
        """获取浮点配置。"""

        value = cls.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        """获取布尔配置。"""

        value = cls.get(key, default)
        if isinstance(value, bool):
            return value
        return cls._to_bool(value, default)

    @classmethod
    def get_json_dict(cls, key: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        """获取 JSON 字典配置，非字典值自动降级。"""

        fallback: dict[str, Any] = dict(default or {})
        value = cls.get(key, fallback)
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return fallback
            try:
                parsed = json.loads(normalized)
            except json.JSONDecodeError:
                logger.warning("配置解析失败(json-dict): key=%s", key)
                return fallback
            if isinstance(parsed, dict):
                return parsed
        return fallback

    @classmethod
    def get_tool_governance_settings(
        cls,
        *,
        task_mode: str | None = None,
        requires_evidence: bool | None = None,
    ) -> dict[str, Any]:
        """读取工具治理核心配置，统一 settings+DB 覆盖口径。"""

        resolved_task_mode = str(
            task_mode if task_mode is not None else cls.get_string(TOOL_POLICY_CONTRACT.task_mode_key, "chat")
        ).strip().lower()
        if not resolved_task_mode:
            resolved_task_mode = "chat"

        if isinstance(requires_evidence, bool):
            resolved_requires_evidence = requires_evidence
        else:
            resolved_requires_evidence = cls.get_bool(TOOL_POLICY_CONTRACT.requires_evidence_key, False)

        enabled = cls.get_bool(TOOL_POLICY_CONTRACT.enabled_key, False)
        fail_mode_raw = cls.get_string(TOOL_POLICY_CONTRACT.fail_mode_key, "compat").strip().lower()
        fail_mode = fail_mode_raw if fail_mode_raw in _POLICY_FAIL_MODES else "compat"

        evidence_gate_enabled = resolved_requires_evidence and resolved_task_mode in _EXECUTION_TASK_MODES

        return {
            "enabled": enabled,
            "fail_mode": fail_mode,
            "task_mode": resolved_task_mode,
            "requires_evidence": resolved_requires_evidence,
            "evidence_gate_enabled": evidence_gate_enabled,
        }

    @classmethod
    def get_tool_policy_layers(cls, agent_name: str) -> dict[str, dict[str, Any]]:
        """读取工具策略层级（global + agent），并返回合并结果。"""

        normalized_agent = str(agent_name or "").strip().lower() or "common"
        global_policy = cls.get_json_dict(TOOL_POLICY_CONTRACT.global_policy_key, {})
        agent_policy_key = TOOL_POLICY_CONTRACT.agent_policy_key(normalized_agent)
        agent_policy = cls.get_json_dict(agent_policy_key, {})

        merged = cls._merge_policy(global_policy, agent_policy)
        return {
            "global_policy": global_policy,
            "agent_policy": agent_policy,
            "merged_policy": merged,
            "agent_policy_key": agent_policy_key,
        }

    @classmethod
    def _read_raw(cls, spec: ConfigSpec) -> Any:
        """按来源读取原始配置值。"""

        if spec.source == "db-dynamic":
            db_value = cls._read_db(spec)
            if db_value not in (None, ""):
                return db_value
            env_value = cls._read_env(spec)
            if env_value not in (None, ""):
                return env_value
            return None

        env_value = cls._read_env(spec)
        if env_value not in (None, ""):
            return env_value
        return None

    @classmethod
    def _read_db(cls, spec: ConfigSpec) -> Any:
        """从系统配置缓存读取 DB 动态配置（支持别名）。"""

        for db_key in spec.all_db_keys():
            value = SystemConfigService.get(db_key, None)
            if value not in (None, ""):
                return value
        return None

    @classmethod
    def _read_env(cls, spec: ConfigSpec) -> str | None:
        """读取环境变量值。"""

        if not spec.env_key:
            return None
        return os.getenv(spec.env_key)

    @classmethod
    def _coerce_value(cls, value: Any, value_type: str, default: Any) -> Any:
        """按契约类型执行值转换。"""

        if value is None:
            return default

        if value_type == "string":
            return str(value)

        if value_type == "number":
            if isinstance(value, bool):
                return default
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                normalized = value.strip()
                if not normalized:
                    return default
                try:
                    return float(normalized) if "." in normalized else int(normalized)
                except ValueError:
                    logger.warning("配置解析失败(number): value=%r", value)
                    return default
            return default

        if value_type == "boolean":
            return cls._to_bool(value, default)

        if value_type == "json":
            if isinstance(value, (dict, list)):
                return value
            if isinstance(value, str):
                normalized = value.strip()
                if not normalized:
                    return default
                try:
                    return json.loads(normalized)
                except json.JSONDecodeError:
                    logger.warning("配置解析失败(json): value=%r", value)
                    return default
            return default

        return value

    @classmethod
    def _to_bool(cls, value: Any, default: bool) -> bool:
        """统一布尔解析。"""

        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in _TRUTHY:
                return True
            if normalized in _FALSY:
                return False
        return default

    @classmethod
    def _merge_policy(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """递归合并策略，列表按顺序去重拼接。"""

        merged: dict[str, Any] = dict(base or {})
        for key, value in (override or {}).items():
            if key not in merged:
                merged[key] = value
                continue

            current = merged[key]
            if isinstance(current, dict) and isinstance(value, dict):
                merged[key] = cls._merge_policy(current, value)
                continue

            if isinstance(current, list) and isinstance(value, list):
                deduped: list[Any] = []
                for item in [*current, *value]:
                    if item not in deduped:
                        deduped.append(item)
                merged[key] = deduped
                continue

            merged[key] = value

        return merged
