"""LLM 场景治理服务（中文注释）。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.ai.scene_registry import get_required_scene_keys
from app.models.llm_model import LLMModel
from app.repositories import llm_scene_repo
from app.services.llm_config_service import LLMConfigService

logger = logging.getLogger(__name__)


class SceneConfigError(ValueError):
    """场景配置异常。"""


@dataclass(frozen=True)
class SceneRuntimeConfig:
    """运行时场景缓存对象。"""

    scene_key: str
    scene_name: str
    scene_type: str
    default_model_id: int
    default_model_code: Optional[str]
    default_model_type: Optional[str]
    is_active: bool
    description: Optional[str]


class LLMSceneService:
    """维护场景配置缓存与运行时解析。"""

    _scene_cache: Dict[str, SceneRuntimeConfig] = {}
    _initialized: bool = False

    # 场景类型 -> 可绑定模型类型
    _SCENE_MODEL_COMPATIBILITY: dict[str, set[str]] = {
        "text": {"chat", "reasoning", "vision"},
        "image": {"vision", "chat"},
        "video": {"video", "vision", "chat", "reasoning"},
        "audio": {"audio", "asr", "tts", "chat", "reasoning"},
        "embedding": {"embedding"},
        "vision": {"vision", "chat", "reasoning"},
        "rerank": {"rerank"},
        "asr": {"asr", "audio"},
        "tts": {"tts", "audio"},
    }

    @classmethod
    def is_valid_scene_key(cls, scene_key: str) -> bool:
        """校验场景键格式（模块.函数名）。"""

        if not isinstance(scene_key, str):
            return False

        normalized = scene_key.strip()
        if not normalized:
            return False

        if " " in normalized:
            return False

        parts = normalized.split(".")
        if len(parts) < 2:
            return False

        return all(part.strip() for part in parts)

    @classmethod
    def normalize_scene_key(cls, scene_key: str) -> str:
        """规范化场景键并校验。"""

        normalized = (scene_key or "").strip()
        if not cls.is_valid_scene_key(normalized):
            raise SceneConfigError(f"非法 scene_key: {scene_key!r}，必须是 `模块.函数名`")

        return normalized

    @classmethod
    def load_from_db(cls, db: Session):
        """从数据库加载场景缓存。"""

        scenes = llm_scene_repo.list_scenes(db, include_inactive=True)
        cache: Dict[str, SceneRuntimeConfig] = {}

        for scene in scenes:
            scene_key = cls.normalize_scene_key(scene.scene_key)
            scene_type = (scene.scene_type or "text").strip().lower()

            default_model_code = None
            default_model_type = None
            if scene.default_model is not None:
                default_model_code = scene.default_model.model_code
                default_model_type = (scene.default_model.model_type or "chat").strip().lower()

            cache[scene_key] = SceneRuntimeConfig(
                scene_key=scene_key,
                scene_name=scene.scene_name,
                scene_type=scene_type,
                default_model_id=scene.default_model_id,
                default_model_code=default_model_code,
                default_model_type=default_model_type,
                is_active=bool(scene.is_active),
                description=scene.description,
            )

        cls._scene_cache = cache
        cls._initialized = True
        logger.info("LLM 场景缓存加载完成: scenes=%d", len(cache))

    @classmethod
    def refresh_cache(cls, db: Session):
        """刷新场景缓存。"""

        cls.load_from_db(db)

    @classmethod
    def _lazy_init(cls):
        """懒加载初始化。"""

        if cls._initialized:
            return

        from app.db.session import SessionLocal

        logger.info("触发 LLM 场景缓存懒加载")
        with SessionLocal() as db:
            cls.load_from_db(db)

    @classmethod
    def _ensure_initialized(cls):
        if not cls._initialized:
            cls._lazy_init()

    @classmethod
    def _is_type_compatible(cls, scene_type: str, model_type: str) -> bool:
        expected_types = cls._SCENE_MODEL_COMPATIBILITY.get(scene_type)
        if expected_types is None:
            return False

        return model_type in expected_types

    @classmethod
    def _validate_scene_model(cls, scene: SceneRuntimeConfig, model_code: str):
        model_cfg = LLMConfigService.get_model_config(model_code)
        if not model_cfg:
            raise SceneConfigError(
                f"场景 {scene.scene_key} 绑定模型不可用: model_code={model_code}"
            )

        model_type = (model_cfg.model_type or "chat").strip().lower()
        if not cls._is_type_compatible(scene.scene_type, model_type):
            raise SceneConfigError(
                f"场景 {scene.scene_key} 类型不兼容: scene_type={scene.scene_type}, model_type={model_type}"
            )

    @classmethod
    def get_scene(cls, scene_key: str) -> SceneRuntimeConfig:
        """获取场景缓存对象。"""

        cls._ensure_initialized()

        normalized_key = cls.normalize_scene_key(scene_key)
        scene = cls._scene_cache.get(normalized_key)
        if scene is None:
            raise SceneConfigError(f"场景未配置: scene_key={normalized_key}")

        return scene

    @classmethod
    def resolve_model_code(cls, scene_key: str, model_id: Optional[str] = None) -> str:
        """按场景解析目标模型代码。"""

        scene = cls.get_scene(scene_key)

        if not scene.is_active:
            raise SceneConfigError(f"场景已停用: scene_key={scene.scene_key}")

        if model_id:
            cls._validate_scene_model(scene, model_id)
            return model_id

        if not scene.default_model_code:
            raise SceneConfigError(f"场景未绑定默认模型: scene_key={scene.scene_key}")

        cls._validate_scene_model(scene, scene.default_model_code)
        return scene.default_model_code

    @classmethod
    def validate_startup_integrity(cls, required_scene_keys: Optional[set[str]] = None):
        """启动期完整性校验。"""

        cls._ensure_initialized()

        required_keys = required_scene_keys or get_required_scene_keys()
        errors: list[str] = []

        missing_keys = sorted(required_keys - set(cls._scene_cache))
        for key in missing_keys:
            errors.append(f"缺失场景配置: {key}")

        for key in sorted(required_keys & set(cls._scene_cache)):
            scene = cls._scene_cache[key]
            if not scene.is_active:
                errors.append(f"场景已停用: {key}")
                continue

            if not scene.default_model_code:
                errors.append(f"场景默认模型为空: {key}")
                continue

            try:
                cls._validate_scene_model(scene, scene.default_model_code)
            except SceneConfigError as exc:
                errors.append(str(exc))

        if errors:
            joined = "\n - ".join(errors)
            raise SceneConfigError(f"LLM 场景配置校验失败:\n - {joined}")

        logger.info("LLM 场景配置校验通过: required=%d", len(required_keys))

    @classmethod
    def list_scene_items(cls) -> list[SceneRuntimeConfig]:
        """返回缓存中的场景列表。"""

        cls._ensure_initialized()
        return [cls._scene_cache[k] for k in sorted(cls._scene_cache)]

    @classmethod
    def update_scene(
        cls,
        db: Session,
        scene_key: str,
        *,
        default_model_code: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> SceneRuntimeConfig:
        """更新场景默认模型或状态。"""

        normalized_key = cls.normalize_scene_key(scene_key)
        scene_row = llm_scene_repo.get_scene_by_key(db, normalized_key)
        if scene_row is None:
            raise SceneConfigError(f"场景不存在: scene_key={normalized_key}")

        if default_model_code is not None:
            model_row = db.query(LLMModel).filter(
                LLMModel.model_code == default_model_code,
                LLMModel.is_active == True,
            ).first()
            if model_row is None:
                raise SceneConfigError(f"模型不存在或未启用: {default_model_code}")

            model_type = (model_row.model_type or "chat").strip().lower()
            scene_type = (scene_row.scene_type or "text").strip().lower()
            if not cls._is_type_compatible(scene_type, model_type):
                raise SceneConfigError(
                    f"模型类型与场景不兼容: scene_type={scene_type}, model_type={model_type}"
                )

            scene_row.default_model_id = model_row.id

        if is_active is False and normalized_key in get_required_scene_keys():
            raise SceneConfigError(f"核心场景禁止停用: scene_key={normalized_key}")

        if is_active is not None:
            scene_row.is_active = bool(is_active)

        try:
            db.flush()
            cls.load_from_db(db)
            cls.validate_startup_integrity()
            db.commit()
        except Exception:
            db.rollback()
            raise

        cls.load_from_db(db)
        return cls.get_scene(normalized_key)

    @classmethod
    def export_scene_payload(cls) -> list[dict[str, Any]]:
        """导出场景列表响应结构。"""

        rows = []
        for scene in cls.list_scene_items():
            rows.append(
                {
                    "scene_key": scene.scene_key,
                    "scene_name": scene.scene_name,
                    "scene_type": scene.scene_type,
                    "default_model_id": scene.default_model_id,
                    "default_model_code": scene.default_model_code,
                    "is_active": scene.is_active,
                    "description": scene.description,
                }
            )

        return rows
