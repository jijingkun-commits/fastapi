"""LLM 配置服务：管理模型配置缓存与获取（中文注释）。"""
import logging
from typing import Optional, List, Dict

from sqlalchemy.orm import Session

from app.repositories import llm_repo
from app.schemas.llm import LLMModelConfig

logger = logging.getLogger(__name__)


class LLMConfigService:
    """提供 LLM 配置的内存缓存与查询服务。
    
    设计为单例或静态工具类，启动时初始化缓存。
    """
    
    _models_cache: Dict[str, LLMModelConfig] = {}  # model_code -> config
    _models_by_type: Dict[str, Dict[str, LLMModelConfig]] = {}  # model_type -> {model_code -> config}
    _providers_cache: Dict[str, dict] = {}  # code -> provider info
    _default_model_code: Optional[str] = None  # 缓存默认 chat 模型代码
    _default_by_type: Dict[str, str] = {}  # model_type -> 默认模型代码
    _initialized: bool = False
    
    @classmethod
    def load_from_db(cls, db: Session):
        """从数据库全量加载配置到内存。"""
        logger.info("开始加载 LLM 配置缓存...")
        
        # 1. 加载提供商
        providers = llm_repo.get_active_providers(db)
        cls._providers_cache = {p.code: {
            "id": p.id,
            "name": p.name,
            "base_url": p.base_url,
            "api_key": p.api_key,
            "extra_config": p.extra_config
        } for p in providers if p.code}
        
        # 2. 加载模型
        models = llm_repo.get_active_models(db)
        cls._models_cache = {}
        cls._models_by_type = {}
        cls._default_model_code = None
        cls._default_by_type = {}
        
        for m in models:
            if not m.provider or m.provider.code not in cls._providers_cache:
                logger.warning(f"模型 {m.model_code} 关联的提供商无效或未启用，跳过")
                continue
                
            provider_config = cls._providers_cache[m.provider.code]

            provider_extra = provider_config.get("extra_config")
            model_extra = m.extra_config
            # 合并优先级：provider 级默认值 < model 级覆盖值。
            merged_extra_config = {}

            if isinstance(provider_extra, dict):
                merged_extra_config.update(provider_extra)
            elif provider_extra is not None:
                logger.warning(
                    "Provider extra_config 不是 dict，忽略: provider=%s, type=%s",
                    m.provider.code,
                    type(provider_extra).__name__,
                )

            if isinstance(model_extra, dict):
                merged_extra_config.update(model_extra)
            elif model_extra is not None:
                logger.warning(
                    "Model extra_config 不是 dict，忽略: model=%s, type=%s",
                    m.model_code,
                    type(model_extra).__name__,
                )
            
            # 构建配置对象
            model_type = m.model_type or "chat"
            cfg = LLMModelConfig(
                model_code=m.model_code,
                model_name=m.model_name,
                model_type=model_type,
                provider_code=m.provider.code,
                base_url=provider_config["base_url"],
                api_key=provider_config["api_key"],
                temperature=m.default_temperature,
                supports_thinking=m.supports_thinking,
                thinking_budget=m.thinking_budget,
                max_output_tokens=m.max_output_tokens,
                context_window=m.context_window,
                # 无扩展配置时统一置 None，减少下游判空分支。
                extra_config=merged_extra_config or None,
            )
            cls._models_cache[m.model_code] = cfg
            
            # 按类型分组
            if model_type not in cls._models_by_type:
                cls._models_by_type[model_type] = {}
            cls._models_by_type[model_type][m.model_code] = cfg
            
            # 记录该类型的默认模型
            if m.is_default:
                if model_type == "chat" and not cls._default_model_code:
                    cls._default_model_code = m.model_code
                if model_type not in cls._default_by_type:
                    cls._default_by_type[model_type] = m.model_code
            
        cls._initialized = True
        logger.info(f"LLM 配置加载完成，缓存了 {len(cls._models_cache)} 个模型，默认模型: {cls._default_model_code}")

    @classmethod
    def refresh_cache(cls, db: Session):
        """刷新缓存（配置变更后调用）。"""
        cls.load_from_db(db)

    @classmethod
    def _lazy_init(cls):
        """Lazy initialization to recover from startup failures."""
        if not cls._initialized:
            from app.db.session import SessionLocal
            logger.info("Triggering lazy initialization of LLM config...")
            try:
                with SessionLocal() as db:
                    cls.load_from_db(db)
            except Exception as e:
                logger.error(f"Lazy initialization failed: {e}")

    @classmethod
    def get_model_config(cls, model_code: str) -> Optional[LLMModelConfig]:
        """获取指定模型的配置。"""
        if not cls._initialized:
            cls._lazy_init()
            
        if not cls._initialized:
            return None
            
        return cls._models_cache.get(model_code)

    @classmethod
    def get_default_model_code(cls) -> Optional[str]:
        """获取默认模型代码。"""
        if cls._default_model_code:
            return cls._default_model_code
        # 如果没有设置默认，返回第一个
        if cls._models_cache:
            return next(iter(cls._models_cache))
        return None

    @classmethod
    def list_available_models(cls) -> List[dict]:
        """列出所有可用模型（简要信息，供前端下拉选择）。"""
        return [
            {
                "model_code": cfg.model_code,
                "model_name": cfg.model_name,
                "model_type": cfg.model_type,
                "provider": cfg.provider_code,
                "supports_thinking": cfg.supports_thinking,
                "is_default": cfg.model_code == cls._default_model_code
            }
            for cfg in cls._models_cache.values()
        ]

    @classmethod
    def get_model_by_type(cls, model_type: str) -> Optional[LLMModelConfig]:
        """获取指定类型的默认模型配置。
        
        Args:
            model_type: 模型类型（chat/vision/embedding/rerank/asr/tts）
            
        Returns:
            嗨类型的默认模型配置，如果没有则返回 None
        """
        if not cls._initialized:
            cls._lazy_init()
            
        if not cls._initialized:
            return None
        
        # 查找该类型的默认模型
        default_code = cls._default_by_type.get(model_type)
        if default_code:
            return cls._models_cache.get(default_code)
        
        # 如果没有默认，返回该类型的第一个模型
        type_models = cls._models_by_type.get(model_type, {})
        if type_models:
            return next(iter(type_models.values()))
        
        return None

    @classmethod
    def list_models_by_type(cls, model_type: str) -> List[dict]:
        """列出指定类型的所有可用模型。
        
        Args:
            model_type: 模型类型
            
        Returns:
            该类型的模型列表
        """
        type_models = cls._models_by_type.get(model_type, {})
        default_code = cls._default_by_type.get(model_type)
        return [
            {
                "model_code": cfg.model_code,
                "model_name": cfg.model_name,
                "provider": cfg.provider_code,
                "is_default": cfg.model_code == default_code
            }
            for cfg in type_models.values()
        ]

    @classmethod
    def is_type_configured(cls, model_type: str) -> bool:
        """检查指定类型是否有可用模型。"""
        return bool(cls._models_by_type.get(model_type))

