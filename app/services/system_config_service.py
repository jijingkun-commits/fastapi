"""系统配置服务：管理系统配置缓存与获取（中文注释）。"""
import json
import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.repositories import config_repo

logger = logging.getLogger(__name__)


class SystemConfigService:
    """提供系统配置的内存缓存与查询服务。"""
    
    _cache: Dict[str, Any] = {}  # key -> parsed value
    _raw_cache: Dict[str, dict] = {}  # key -> {value, type, category, description}
    _initialized: bool = False
    
    @classmethod
    def load_from_db(cls, db: Session):
        """从数据库全量加载配置到内存。"""
        logger.info("开始加载系统配置缓存...")
        
        configs = config_repo.get_all_configs(db)
        cls._cache = {}
        cls._raw_cache = {}
        
        for c in configs:
            parsed = cls._parse_value(c.config_value, c.value_type)
            cls._cache[c.config_key] = parsed
            cls._raw_cache[c.config_key] = {
                "value": c.config_value,
                "type": c.value_type,
                "category": c.category,
                "description": c.description,
                "is_secret": c.is_secret
            }
            
        cls._initialized = True
        logger.info(f"系统配置加载完成，缓存了 {len(cls._cache)} 个配置项")

    @classmethod
    def _parse_value(cls, value: str, value_type: str) -> Any:
        """根据类型解析配置值。"""
        if value_type == "number":
            return float(value) if "." in value else int(value)
        elif value_type == "boolean":
            return value.lower() in {"true", "1", "yes"}
        elif value_type == "json":
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"JSON 解析失败，返回原始字符串: {value}")
                return value
        else:
            return value

    @classmethod
    def refresh_cache(cls, db: Session):
        """刷新缓存。"""
        cls.load_from_db(db)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """获取配置值（已解析）。"""
        if not cls._initialized:
            logger.warning("SystemConfigService 未初始化")
            return default
        return cls._cache.get(key, default)

    @classmethod
    def get_string(cls, key: str, default: str = "") -> str:
        """获取字符串配置。"""
        return str(cls.get(key, default))

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        """获取整数配置。"""
        val = cls.get(key, default)
        return int(val) if val is not None else default

    @classmethod
    def get_float(cls, key: str, default: float = 0.0) -> float:
        """获取浮点数配置。"""
        val = cls.get(key, default)
        return float(val) if val is not None else default

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        """获取布尔配置。"""
        val = cls.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in {"true", "1", "yes"}
        return bool(val)

    @classmethod
    def list_configs(cls, category: str = None) -> List[dict]:
        """列出配置项（用于 API）。"""
        result = []
        for key, meta in cls._raw_cache.items():
            if category and meta.get("category") != category:
                continue
            result.append({
                "key": key,
                "value": "***" if meta.get("is_secret") else meta["value"],
                "type": meta["type"],
                "category": meta.get("category"),
                "description": meta.get("description")
            })
        return result
