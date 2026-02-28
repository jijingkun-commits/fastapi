"""LLM 场景治理服务（中文注释）。"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.ai.scene_registry import SCENE_DEFINITION_MAP, get_required_scene_keys
from app.models.llm_model import LLMModel
from app.repositories import config_repo, llm_scene_repo
from app.services.llm_config_service import LLMConfigService

logger = logging.getLogger(__name__)


class SceneConfigError(ValueError):
    """场景配置异常。"""


@dataclass(frozen=True)
class SceneRuntimeConfig:
    """运行时场景缓存对象。"""

    scene_key: str
    scene_name: str
    route_group: str
    scene_type: str
    default_model_id: Optional[int]
    default_model_code: Optional[str]
    default_model_type: Optional[str]
    is_active: bool
    description: Optional[str]


class LLMSceneService:
    """维护场景配置缓存与运行时解析。"""

    _scene_cache: Dict[str, SceneRuntimeConfig] = {}
    _route_group_model_id_cache: Dict[str, Optional[int]] = {}
    _initialized: bool = False

    # route_group -> t_system_config.config_key
    _ROUTE_GROUP_CONFIG_KEY: dict[str, str] = {
        "default_chat": "model_routing.default_chat",
        "lightweight": "model_routing.lightweight",
        "sql_generation": "model_routing.sql_generation",
        "embedding": "embedding",
        "vision": "vision",
    }

    # route_group -> 可绑定模型类型
    _ROUTE_GROUP_MODEL_COMPATIBILITY: dict[str, set[str]] = {
        "default_chat": {"chat"},
        "lightweight": {"chat"},
        "sql_generation": {"chat"},
        "embedding": {"embedding"},
        "vision": {"vision", "chat", "reasoning"},
    }

    # 场景类型兼容（仅 route_group 不可识别时兜底）
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
    def _normalize_route_group(cls, route_group: Optional[str], scene_key: str) -> str:
        """规范化路由分组，缺失时回退注册表定义。"""

        normalized = (route_group or "").strip().lower()
        if normalized:
            return normalized

        scene_def = SCENE_DEFINITION_MAP.get(scene_key)
        if scene_def:
            return scene_def.route_group

        return ""

    @classmethod
    def _ensure_initialized(cls):
        if not cls._initialized:
            cls._lazy_init()

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
    def _resolve_model_id_from_config_value(
        cls,
        raw_value: Optional[str],
        model_by_id: dict[int, LLMModel],
        model_by_code: dict[str, LLMModel],
    ) -> Optional[int]:
        """将 t_system_config 的值解析为模型 ID。"""

        if raw_value is None:
            return None

        normalized = str(raw_value).strip()
        if not normalized:
            return None

        # 新格式：直接存 model_id
        if normalized.isdigit():
            model_id = int(normalized)
            if model_id in model_by_id:
                return model_id
            return None

        # 兼容旧格式：存 model_code
        model = model_by_code.get(normalized)
        if model:
            return model.id
        return None

    @classmethod
    def load_from_db(cls, db: Session):
        """从数据库加载场景缓存。"""

        scenes = llm_scene_repo.list_scenes(db, include_inactive=True)
        active_models = db.query(LLMModel).filter(LLMModel.is_active == True).all()
        model_by_id = {m.id: m for m in active_models}
        model_by_code = {m.model_code: m for m in active_models if m.model_code}

        route_group_model_ids: dict[str, Optional[int]] = {}
        for route_group, config_key in cls._ROUTE_GROUP_CONFIG_KEY.items():
            conf = config_repo.get_config_by_key(db, config_key)
            model_id = cls._resolve_model_id_from_config_value(
                conf.config_value if conf else None,
                model_by_id,
                model_by_code,
            )
            route_group_model_ids[route_group] = model_id

            if conf and model_id is None and str(conf.config_value).strip():
                logger.warning(
                    "路由分组配置无法解析为启用模型: route_group=%s, config_key=%s, config_value=%s",
                    route_group,
                    config_key,
                    conf.config_value,
                )

        cache: Dict[str, SceneRuntimeConfig] = {}
        for scene in scenes:
            scene_key = cls.normalize_scene_key(scene.scene_key)
            route_group = cls._normalize_route_group(getattr(scene, "route_group", None), scene_key)
            scene_type = (scene.scene_type or "text").strip().lower()

            default_model_id = route_group_model_ids.get(route_group)
            model = model_by_id.get(default_model_id) if default_model_id else None
            default_model_code = model.model_code if model else None
            default_model_type = (model.model_type or "chat").strip().lower() if model else None

            cache[scene_key] = SceneRuntimeConfig(
                scene_key=scene_key,
                scene_name=scene.scene_name,
                route_group=route_group,
                scene_type=scene_type,
                default_model_id=default_model_id,
                default_model_code=default_model_code,
                default_model_type=default_model_type,
                is_active=bool(scene.is_active),
                description=scene.description,
            )

        cls._scene_cache = cache
        cls._route_group_model_id_cache = route_group_model_ids
        cls._initialized = True
        logger.info("LLM 场景缓存加载完成: scenes=%d", len(cache))

    @classmethod
    def refresh_cache(cls, db: Session):
        """刷新场景缓存。"""

        cls.load_from_db(db)

    @classmethod
    def _expected_model_types(cls, scene: SceneRuntimeConfig) -> set[str]:
        by_group = cls._ROUTE_GROUP_MODEL_COMPATIBILITY.get(scene.route_group)
        if by_group:
            return by_group
        return cls._SCENE_MODEL_COMPATIBILITY.get(scene.scene_type, set())

    @classmethod
    def _is_type_compatible(cls, scene: SceneRuntimeConfig, model_type: str) -> bool:
        expected_types = cls._expected_model_types(scene)
        if not expected_types:
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
        if not cls._is_type_compatible(scene, model_type):
            raise SceneConfigError(
                "场景模型类型不兼容: "
                f"scene_key={scene.scene_key}, route_group={scene.route_group}, "
                f"scene_type={scene.scene_type}, model_type={model_type}"
            )

    @classmethod
    def _upsert_route_group_model_id(cls, db: Session, route_group: str, model_id: int):
        """写入 route_group -> model_id 到 t_system_config。"""

        config_key = cls._ROUTE_GROUP_CONFIG_KEY.get(route_group)
        if not config_key:
            raise SceneConfigError(f"未知路由分组: route_group={route_group}")

        config_repo.upsert_config(
            db=db,
            key=config_key,
            value=str(model_id),
            value_type="number",
            category="model_routing",
            description=f"模型路由分组绑定: {route_group}",
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

            if not scene.route_group:
                errors.append(f"场景缺失 route_group: {key}")
                continue

            if scene.route_group not in cls._ROUTE_GROUP_CONFIG_KEY:
                errors.append(f"场景 route_group 非法: {key} -> {scene.route_group}")
                continue

            if scene.default_model_id is None:
                errors.append(f"路由未绑定模型: route_group={scene.route_group}, scene_key={key}")
                continue

            if not scene.default_model_code:
                errors.append(f"路由绑定模型不可用: route_group={scene.route_group}, scene_key={key}")
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
    def _scene_keys_by_route_group(cls, route_group: str) -> tuple[str, ...]:
        cls._ensure_initialized()
        normalized = (route_group or "").strip().lower()
        if normalized not in cls._ROUTE_GROUP_CONFIG_KEY:
            return ()
        return tuple(
            sorted(
                scene.scene_key
                for scene in cls._scene_cache.values()
                if scene.route_group == normalized
            )
        )

    @classmethod
    def get_route_group_default_model_code(cls, route_group: str) -> Optional[str]:
        """返回指定 route_group 当前生效模型代码。"""

        cls._ensure_initialized()
        normalized = (route_group or "").strip().lower()
        if normalized not in cls._ROUTE_GROUP_CONFIG_KEY:
            raise SceneConfigError(f"未知路由分组: route_group={route_group}")

        scene_keys = cls._scene_keys_by_route_group(normalized)
        if not scene_keys:
            raise SceneConfigError(f"路由分组未绑定场景: route_group={route_group}")

        model_codes: list[str] = []
        for scene_key in scene_keys:
            scene = cls._scene_cache.get(scene_key)
            if scene and scene.is_active and scene.default_model_code:
                model_codes.append(scene.default_model_code)

        if not model_codes:
            return None

        counter = Counter(model_codes)
        model_code, _ = counter.most_common(1)[0]
        if len(counter) > 1:
            logger.warning(
                "路由分组模型不一致，按多数派返回: route_group=%s, bindings=%s",
                route_group,
                dict(counter),
            )
        return model_code

    @classmethod
    def update_route_group_default_model(
        cls,
        db: Session,
        route_group: str,
        default_model_code: str,
    ) -> list[SceneRuntimeConfig]:
        """批量更新指定 route_group 的模型绑定。"""

        normalized = (route_group or "").strip().lower()
        if normalized not in cls._ROUTE_GROUP_CONFIG_KEY:
            raise SceneConfigError(f"未知路由分组: route_group={route_group}")

        model_row = db.query(LLMModel).filter(
            LLMModel.model_code == default_model_code,
            LLMModel.is_active == True,
        ).first()
        if model_row is None:
            raise SceneConfigError(f"模型不存在或未启用: {default_model_code}")

        scene_rows = [
            scene
            for scene in llm_scene_repo.list_scenes(db, include_inactive=True)
            if cls._normalize_route_group(getattr(scene, "route_group", None), scene.scene_key) == normalized
        ]
        if not scene_rows:
            raise SceneConfigError(f"路由分组未绑定场景: route_group={route_group}")

        model_type = (model_row.model_type or "chat").strip().lower()
        for scene_row in scene_rows:
            runtime_scene = SceneRuntimeConfig(
                scene_key=scene_row.scene_key,
                scene_name=scene_row.scene_name,
                route_group=normalized,
                scene_type=(scene_row.scene_type or "text").strip().lower(),
                default_model_id=model_row.id,
                default_model_code=model_row.model_code,
                default_model_type=model_type,
                is_active=bool(scene_row.is_active),
                description=scene_row.description,
            )
            if not cls._is_type_compatible(runtime_scene, model_type):
                raise SceneConfigError(
                    "模型类型与路由分组不兼容: "
                    f"route_group={normalized}, scene_key={scene_row.scene_key}, "
                    f"scene_type={runtime_scene.scene_type}, model_type={model_type}"
                )

        cls._upsert_route_group_model_id(db, normalized, model_row.id)

        try:
            db.flush()
            cls.load_from_db(db)
            cls.validate_startup_integrity()
            db.commit()
        except Exception:
            db.rollback()
            raise

        cls.load_from_db(db)
        return [cls.get_scene(scene.scene_key) for scene in scene_rows]

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

        route_group = cls._normalize_route_group(getattr(scene_row, "route_group", None), normalized_key)
        if getattr(scene_row, "route_group", None) != route_group:
            scene_row.route_group = route_group

        if default_model_code is not None:
            model_row = db.query(LLMModel).filter(
                LLMModel.model_code == default_model_code,
                LLMModel.is_active == True,
            ).first()
            if model_row is None:
                raise SceneConfigError(f"模型不存在或未启用: {default_model_code}")

            group_rows = [
                scene
                for scene in llm_scene_repo.list_scenes(db, include_inactive=True)
                if cls._normalize_route_group(getattr(scene, "route_group", None), scene.scene_key) == route_group
            ]
            model_type = (model_row.model_type or "chat").strip().lower()
            for row in group_rows:
                runtime_scene = SceneRuntimeConfig(
                    scene_key=row.scene_key,
                    scene_name=row.scene_name,
                    route_group=route_group,
                    scene_type=(row.scene_type or "text").strip().lower(),
                    default_model_id=model_row.id,
                    default_model_code=model_row.model_code,
                    default_model_type=model_type,
                    is_active=bool(row.is_active),
                    description=row.description,
                )
                if not cls._is_type_compatible(runtime_scene, model_type):
                    raise SceneConfigError(
                        "模型类型与路由分组不兼容: "
                        f"route_group={route_group}, scene_key={row.scene_key}, "
                        f"scene_type={runtime_scene.scene_type}, model_type={model_type}"
                    )

            cls._upsert_route_group_model_id(db, route_group, model_row.id)

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
                    "route_group": scene.route_group,
                    "scene_type": scene.scene_type,
                    "default_model_id": scene.default_model_id,
                    "default_model_code": scene.default_model_code,
                    "is_active": scene.is_active,
                    "description": scene.description,
                }
            )

        return rows

