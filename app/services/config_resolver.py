"""统一配置读取器：按契约解析 DB/环境变量配置（中文注释）。"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.core.config_contract import CONFIG_SPECS, ConfigSpec
from app.services.system_config_service import SystemConfigService

logger = logging.getLogger(__name__)

_TRUTHY = {"1", "true", "yes", "on", "enabled"}
_FALSY = {"0", "false", "no", "off", "disabled"}


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
