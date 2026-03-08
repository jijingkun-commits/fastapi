"""技能服务：管理 Agent Skills 的导入、同步和检索（中文注释）。"""

import ast
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import Session

from app.ai.utils.embedding_util import get_embedding
from app.core.config import SKILL_SIMILARITY_THRESHOLD
from app.db.session import get_db_context
from app.models.agent_skill import AgentSkill, AgentSkillDefinition, AgentSkillVersion, UserSkillBinding
from app.repositories import config_repo
from app.services.config_resolver import ConfigResolver

logger = logging.getLogger(__name__)


class SkillService:
    """技能管理服务。"""

    DEFAULT_SCOPE = "global"
    DEFAULT_PRIORITY = 100
    PRIORITY_MIN = 0
    PRIORITY_MAX = 10000
    VALID_SCOPES = {DEFAULT_SCOPE, "data", "todo", "admin"}
    FRONTMATTER_ALIASES = {
        "name": ("name",),
        "description": ("description",),
        "scope": ("scope",),
        "priority": ("priority",),
        "version": ("version", "skill_version", "skill-version"),
        "auto_enabled": ("auto_enabled", "auto-enabled", "autoEnabled"),
        "is_enabled": ("is_enabled", "is-enabled", "enabled"),
        "trigger_phrases": ("trigger_phrases", "trigger-phrases"),
        "conflicts_with": ("conflicts_with", "conflicts-with"),
    }

    DEFAULT_VERSION = "v1"
    VERSION_STATUS_DRAFT = "draft"
    VERSION_STATUS_PUBLISHED = "published"
    VERSION_STATUS_ROLLBACKED = "rollbacked"
    VERSION_STATUS_DEPRECATED = "deprecated"
    VERSION_STATUS_ORDER = {
        VERSION_STATUS_PUBLISHED: 3,
        VERSION_STATUS_ROLLBACKED: 2,
        VERSION_STATUS_DRAFT: 1,
        VERSION_STATUS_DEPRECATED: 0,
    }
    VALID_VERSION_STATUS = {
        VERSION_STATUS_DRAFT,
        VERSION_STATUS_PUBLISHED,
        VERSION_STATUS_ROLLBACKED,
        VERSION_STATUS_DEPRECATED,
    }

    BINDING_STATUS_ENABLED = "enabled"
    BINDING_STATUS_DISABLED = "disabled"
    BINDING_STATUS_ROLLBACKED = "rollbacked"
    VALID_BINDING_STATUS = {
        BINDING_STATUS_ENABLED,
        BINDING_STATUS_DISABLED,
        BINDING_STATUS_ROLLBACKED,
    }
    RUNTIME_SOURCE_MODE_COMPAT = "compat"
    RUNTIME_SOURCE_MODE_STRICT_USER = "strict_user"
    VALID_RUNTIME_SOURCE_MODES = {
        RUNTIME_SOURCE_MODE_COMPAT,
        RUNTIME_SOURCE_MODE_STRICT_USER,
    }
    SKILL_RUNTIME_MODE_PROGRESSIVE = "progressive_loader"
    SKILL_RUNTIME_MODE_HYBRID = "hybrid_rag"
    SKILL_RUNTIME_MODE_CATALOG_TOOL = "catalog_tool"
    VALID_SKILL_RUNTIME_MODES = {
        SKILL_RUNTIME_MODE_PROGRESSIVE,
        SKILL_RUNTIME_MODE_HYBRID,
        SKILL_RUNTIME_MODE_CATALOG_TOOL,
    }
    SKILL_CATALOG_SOURCE = "definition_version_runtime_view"
    SKILL_CATALOG_HEADER = (
        "可用技能目录（仅暴露用途；确需正文时请调用 load_skills，单次最多 3 个 skill_id）："
    )
    MAX_LOAD_SKILLS_COUNT = 3
    USER_BOOTSTRAP_TEMPLATE_KEY = "skill.user_bootstrap_template"
    USER_BOOTSTRAP_TEMPLATE_DEFAULT = {
        "default_version": DEFAULT_VERSION,
        "skills": [],
    }
    LOCAL_SKILL_FILE_SOURCE_RETIRED_MESSAGE = "本地 SKILL.md / skills 目录导入链已退役；技能定义与版本请直接维护数据库真理源。"

    @classmethod
    def _raise_local_skill_file_source_retired(cls) -> None:
        """显式阻断本地文件导入链，避免重新长出第二真理源。"""

        raise RuntimeError(cls.LOCAL_SKILL_FILE_SOURCE_RETIRED_MESSAGE)

    @staticmethod
    def _compute_file_hash(content: str) -> str:
        """计算内容 MD5。"""

        return hashlib.md5(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_query_hash(query: str) -> str:
        """计算查询哈希，避免明文写入检索日志。"""

        normalized = " ".join(query.strip().lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _normalize_trace_key(raw_value: Optional[str]) -> str:
        """标准化 thread/trace 标识值，空值统一为 `-`。"""

        if raw_value is None:
            return "-"

        normalized = str(raw_value).strip()
        if not normalized:
            return "-"

        return normalized[:128]

    @staticmethod
    def _format_warning(field: str, message: str, raw_value: Any = None) -> str:
        """构造字段级 warning 文本，便于日志检索。"""

        if raw_value is None:
            return f"field={field} message={message}"

        normalized = str(raw_value).strip().replace("\n", "\\n")
        if len(normalized) > 80:
            normalized = f"{normalized[:77]}..."
        return f"field={field} value={normalized!r} message={message}"

    @staticmethod
    def _normalize_version_value(raw_value: Any, default: str = DEFAULT_VERSION) -> Tuple[str, bool]:
        """标准化版本号。"""

        if raw_value is None:
            return default, True

        normalized = str(raw_value).strip()
        if not normalized:
            return default, False

        if len(normalized) > 64:
            return default, False

        return normalized, True

    @classmethod
    def _is_skill_versioning_enabled(cls) -> bool:
        """判断是否启用 Skill 版本治理。"""

        return ConfigResolver.get_bool("feature.enable_skill_versioning", False)

    @classmethod
    def _is_user_skill_binding_enabled(cls) -> bool:
        """判断是否启用用户级 Skill 绑定。"""

        return ConfigResolver.get_bool("feature.enable_user_skill_binding", False)

    @classmethod
    def _is_versioning_runtime_enabled(cls) -> bool:
        """运行时固定使用 definition/version 视图。"""

        return True

    @classmethod
    def _is_progressive_skill_loading_enabled(cls) -> bool:
        """判断是否启用渐进式 Skill 加载主路径。"""

        return ConfigResolver.get_bool("feature.enable_progressive_skill_loading", True)

    @classmethod
    def _is_skill_runtime_trace_enabled(cls) -> bool:
        """判断是否启用 Skill runtime canonical trace。"""

        return ConfigResolver.get_bool("feature.enable_skill_runtime_trace", True)

    @classmethod
    def _is_skill_catalog_metadata_normalization_enabled(cls) -> bool:
        """判断是否启用 catalog metadata 归一化。"""

        return ConfigResolver.get_bool("feature.enable_skill_catalog_metadata_normalization", True)

    @classmethod
    def resolve_runtime_mode(cls) -> str:
        """解析聊天主运行时模式，统一返回 canonical 值。"""

        if not cls._is_progressive_skill_loading_enabled():
            return cls.SKILL_RUNTIME_MODE_HYBRID

        raw_value = ConfigResolver.get_string("skill.runtime_mode", cls.SKILL_RUNTIME_MODE_CATALOG_TOOL)
        normalized = str(raw_value or "").strip().lower() or cls.SKILL_RUNTIME_MODE_CATALOG_TOOL

        if normalized == cls.SKILL_RUNTIME_MODE_HYBRID:
            return cls.SKILL_RUNTIME_MODE_HYBRID
        if normalized in {cls.SKILL_RUNTIME_MODE_CATALOG_TOOL, cls.SKILL_RUNTIME_MODE_PROGRESSIVE}:
            return cls.SKILL_RUNTIME_MODE_PROGRESSIVE

        logger.warning("未知 skill.runtime_mode=%s，已回退 progressive_loader", normalized)
        return cls.SKILL_RUNTIME_MODE_PROGRESSIVE

    @classmethod
    def _get_runtime_source_mode(cls) -> str:
        """读取并标准化 Skill 运行时来源模式。"""

        if not cls._is_versioning_runtime_enabled():
            return cls.RUNTIME_SOURCE_MODE_COMPAT

        raw_value = ConfigResolver.get_string("skill.runtime_source_mode", cls.RUNTIME_SOURCE_MODE_COMPAT)
        normalized = str(raw_value or "").strip().lower()
        if normalized in cls.VALID_RUNTIME_SOURCE_MODES:
            return normalized
        return cls.RUNTIME_SOURCE_MODE_COMPAT

    @classmethod
    def _is_strict_user_runtime_enabled(cls) -> bool:
        """判断是否启用 strict_user 运行模式。"""

        return cls._get_runtime_source_mode() == cls.RUNTIME_SOURCE_MODE_STRICT_USER

    @staticmethod
    def _normalize_binding_status(raw_value: Any, default: str = BINDING_STATUS_ENABLED) -> str:
        """标准化绑定状态值。"""

        normalized = str(raw_value or "").strip().lower()
        if not normalized:
            return default
        if normalized in SkillService.VALID_BINDING_STATUS:
            return normalized
        return default

    @staticmethod
    def _get_frontmatter_value(frontmatter: Dict[str, Any], aliases: Tuple[str, ...]) -> Tuple[Any, bool]:
        """按别名顺序读取 frontmatter 字段值。"""

        for alias in aliases:
            if alias in frontmatter:
                return frontmatter[alias], True
        return None, False

    @classmethod
    def _parse_legacy_frontmatter(cls, frontmatter_text: str) -> Dict[str, Any]:
        """兼容旧版逐行解析，作为非法 YAML 的降级兜底。"""

        parsed: Dict[str, Any] = {}
        for line in frontmatter_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue

            key, raw_value = stripped.split(":", 1)
            parsed[key.strip()] = raw_value.strip().strip("\"'")

        return parsed

    @classmethod
    def _load_frontmatter(cls, frontmatter_text: str) -> Tuple[Dict[str, Any], str, List[str]]:
        """解析 frontmatter，返回结构化结果、状态与 warning。"""

        if not frontmatter_text.strip():
            return {}, "valid", []

        warnings: List[str] = []
        try:
            loaded = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as exc:
            fallback = cls._parse_legacy_frontmatter(frontmatter_text)
            warnings.append(
                cls._format_warning(
                    "frontmatter",
                    "YAML 解析失败，已按宽松模式降级",
                    exc.__class__.__name__,
                )
            )
            return fallback, "invalid", warnings

        if loaded is None:
            return {}, "valid", warnings

        if isinstance(loaded, dict):
            return loaded, "valid", warnings

        warnings.append(
            cls._format_warning(
                "frontmatter",
                "顶层结构必须是对象，已忽略",
                type(loaded).__name__,
            )
        )
        return {}, "invalid", warnings

    @staticmethod
    def _parse_list_value(raw_value: Any) -> Tuple[List[str], bool]:
        """将 frontmatter 中的列表字段解析为字符串列表。"""

        if raw_value is None:
            return [], True

        parsed: Any = raw_value
        parse_ok = True

        if isinstance(parsed, str):
            value = parsed.strip()
            if not value:
                return [], True

            parsed = value
            if value.startswith("[") and value.endswith("]"):
                try:
                    parsed = ast.literal_eval(value)
                except (SyntaxError, ValueError):
                    parse_ok = False
                    parsed = value

        if isinstance(parsed, (list, tuple, set)):
            values = [str(item).strip() for item in parsed if str(item).strip()]
            return list(dict.fromkeys(values)), parse_ok

        if isinstance(parsed, str):
            if "," in parsed:
                values = [item.strip() for item in parsed.split(",") if item.strip()]
                return list(dict.fromkeys(values)), parse_ok
            return ([parsed] if parsed else []), parse_ok

        return [], False

    @staticmethod
    def _parse_bool_value(raw_value: Any, default: bool = True) -> Tuple[bool, bool]:
        """解析 frontmatter 布尔值。"""

        if isinstance(raw_value, bool):
            return raw_value, True

        if isinstance(raw_value, (int, float)) and raw_value in {0, 1}:
            return bool(raw_value), True

        if isinstance(raw_value, str):
            value = raw_value.strip().lower()
            if value in {"true", "1", "yes", "on"}:
                return True, True
            if value in {"false", "0", "no", "off"}:
                return False, True

        return default, False

    @staticmethod
    def _parse_int_value(
        raw_value: Any,
        default: int = DEFAULT_PRIORITY,
        min_value: int = PRIORITY_MIN,
        max_value: int = PRIORITY_MAX,
    ) -> Tuple[int, bool]:
        """解析 frontmatter 整数值。"""

        try:
            value = int(str(raw_value).strip())
        except (TypeError, ValueError):
            return default, False

        if value < min_value or value > max_value:
            return default, False

        return value, True

    @classmethod
    def _normalize_scope(cls, raw_value: Any, default: str = DEFAULT_SCOPE) -> Tuple[str, bool]:
        """标准化作用域值。"""

        if raw_value is None:
            return default, True

        normalized = str(raw_value).strip().lower()
        if not normalized:
            return default, True

        if normalized not in cls.VALID_SCOPES:
            return default, False

        return normalized, True

    @classmethod
    def _parse_skill_file(cls, skill_path: Path) -> Optional[dict]:
        """解析 SKILL.md 文件，提取元数据和内容。"""

        if not skill_path.exists():
            return None

        content = skill_path.read_text(encoding="utf-8")
        skill_id = skill_path.parent.name

        warnings: List[str] = []
        frontmatter_status = "missing"

        name = skill_id.replace("-", " ").title()
        description = ""
        scope = cls.DEFAULT_SCOPE
        priority = cls.DEFAULT_PRIORITY
        version = cls.DEFAULT_VERSION
        auto_enabled = True
        is_enabled = True
        trigger_phrases: List[str] = []
        conflicts_with: List[str] = []

        body_content = content
        frontmatter_data: Dict[str, Any] = {}

        lines = content.splitlines()
        if lines and lines[0].strip() == "---":
            end_idx = -1
            for idx, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    end_idx = idx
                    break

            if end_idx > 0:
                frontmatter_text = "\n".join(lines[1:end_idx])
                body_content = "\n".join(lines[end_idx + 1 :])
                frontmatter_data, frontmatter_status, frontmatter_warnings = cls._load_frontmatter(frontmatter_text)
                warnings.extend(frontmatter_warnings)
            else:
                frontmatter_status = "invalid"
                warnings.append(
                    cls._format_warning(
                        "frontmatter",
                        "缺少结束分隔符，已按默认值回退",
                    )
                )

        name_value, has_name = cls._get_frontmatter_value(frontmatter_data, cls.FRONTMATTER_ALIASES["name"])
        if has_name:
            normalized_name = str(name_value).strip()
            if normalized_name:
                name = normalized_name
            else:
                warnings.append(
                    cls._format_warning(
                        "name",
                        "值为空，已回退为目录名",
                        name_value,
                    )
                )

        description_value, has_description = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["description"],
        )
        if has_description:
            normalized_description = str(description_value).strip()
            if normalized_description:
                description = normalized_description
            else:
                warnings.append(
                    cls._format_warning(
                        "description",
                        "值为空，已回退为正文摘要",
                        description_value,
                    )
                )

        scope_value, has_scope = cls._get_frontmatter_value(frontmatter_data, cls.FRONTMATTER_ALIASES["scope"])
        if has_scope:
            scope, valid_scope = cls._normalize_scope(scope_value, default=cls.DEFAULT_SCOPE)
            if not valid_scope:
                warnings.append(
                    cls._format_warning(
                        "scope",
                        f"仅支持 {sorted(cls.VALID_SCOPES)}，已回退默认值",
                        scope_value,
                    )
                )

        priority_value, has_priority = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["priority"],
        )
        if has_priority:
            priority, valid_priority = cls._parse_int_value(
                priority_value,
                default=cls.DEFAULT_PRIORITY,
                min_value=cls.PRIORITY_MIN,
                max_value=cls.PRIORITY_MAX,
            )
            if not valid_priority:
                warnings.append(
                    cls._format_warning(
                        "priority",
                        f"需为 {cls.PRIORITY_MIN}-{cls.PRIORITY_MAX} 的整数，已回退默认值",
                        priority_value,
                    )
                )

        version_value, has_version = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["version"],
        )
        if has_version:
            version, valid_version = cls._normalize_version_value(version_value, default=cls.DEFAULT_VERSION)
            if not valid_version:
                warnings.append(
                    cls._format_warning(
                        "version",
                        "需为 1-64 字符字符串，已回退默认值",
                        version_value,
                    )
                )

        auto_enabled_value, has_auto_enabled = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["auto_enabled"],
        )
        if has_auto_enabled:
            auto_enabled, valid_auto_enabled = cls._parse_bool_value(auto_enabled_value, default=True)
            if not valid_auto_enabled:
                warnings.append(
                    cls._format_warning(
                        "auto_enabled",
                        "需为布尔值，已回退默认值 true",
                        auto_enabled_value,
                    )
                )

        is_enabled_value, has_is_enabled = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["is_enabled"],
        )
        if has_is_enabled:
            is_enabled, valid_is_enabled = cls._parse_bool_value(is_enabled_value, default=True)
            if not valid_is_enabled:
                warnings.append(
                    cls._format_warning(
                        "is_enabled",
                        "需为布尔值，已回退默认值 true",
                        is_enabled_value,
                    )
                )

        trigger_phrases_value, has_trigger_phrases = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["trigger_phrases"],
        )
        if has_trigger_phrases:
            trigger_phrases, valid_trigger_phrases = cls._parse_list_value(trigger_phrases_value)
            if not valid_trigger_phrases:
                warnings.append(
                    cls._format_warning(
                        "trigger_phrases",
                        "需为字符串列表或逗号分隔字符串，已回退为空数组",
                        trigger_phrases_value,
                    )
                )

        conflicts_with_value, has_conflicts_with = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["conflicts_with"],
        )
        if has_conflicts_with:
            parsed_conflicts, valid_conflicts_with = cls._parse_list_value(conflicts_with_value)
            if not valid_conflicts_with:
                warnings.append(
                    cls._format_warning(
                        "conflicts_with",
                        "需为字符串列表或逗号分隔字符串，已回退为空数组",
                        conflicts_with_value,
                    )
                )
            conflicts_with = list(
                dict.fromkeys([item.strip().lower() for item in parsed_conflicts if item and item.strip()])
            )

            if skill_id in conflicts_with:
                conflicts_with = [item for item in conflicts_with if item != skill_id]
                warnings.append(
                    cls._format_warning(
                        "conflicts_with",
                        "包含自身 skill_id，已自动移除",
                        skill_id,
                    )
                )

        if not description:
            clean_content = re.sub(r"^#+\s*", "", body_content, flags=re.MULTILINE).strip()
            description = clean_content[:200] if len(clean_content) > 200 else clean_content

        if warnings and frontmatter_status == "valid":
            frontmatter_status = "invalid"

        return {
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "content": content,
            "scope": scope,
            "priority": priority,
            "version": version,
            "auto_enabled": auto_enabled,
            "is_enabled": is_enabled,
            "trigger_phrases": trigger_phrases,
            "conflicts_with": conflicts_with,
            "frontmatter_status": frontmatter_status,
            "warnings": warnings,
        }

    @classmethod
    def _sync_versioned_records(
        cls,
        db: Session,
        parsed: Dict[str, Any],
        file_hash: str,
        embedding: Optional[List[float]],
    ) -> bool:
        """同步 Skill 定义层与版本层记录。"""

        skill_id = str(parsed["skill_id"])
        normalized_scope = parsed.get("scope") or cls.DEFAULT_SCOPE
        normalized_is_enabled = bool(parsed.get("is_enabled", True))
        normalized_auto_enabled = bool(parsed.get("auto_enabled", True))
        normalized_priority = int(parsed.get("priority", cls.DEFAULT_PRIORITY))
        normalized_trigger_phrases = parsed.get("trigger_phrases") or []
        normalized_conflicts_with = parsed.get("conflicts_with") or []
        changed = False

        definition = db.execute(
            select(AgentSkillDefinition).where(AgentSkillDefinition.skill_id == skill_id)
        ).scalar_one_or_none()
        default_catalog_order = int(parsed.get("priority", cls.DEFAULT_PRIORITY) or cls.DEFAULT_PRIORITY)
        default_catalog_path = cls._normalize_catalog_path(skill_id, None)

        if definition is None:
            definition = AgentSkillDefinition(
                skill_id=skill_id,
                name=parsed["name"],
                description=parsed.get("description"),
                scope=normalized_scope,
                is_enabled=normalized_is_enabled,
                catalog_path=default_catalog_path,
                catalog_order=default_catalog_order,
            )
            db.add(definition)
            db.flush()
            changed = True
        else:
            if definition.name != parsed["name"]:
                definition.name = parsed["name"]
                changed = True
            if definition.description != parsed.get("description"):
                definition.description = parsed.get("description")
                changed = True
            if definition.scope != normalized_scope:
                definition.scope = normalized_scope
                changed = True
            if bool(definition.is_enabled) != normalized_is_enabled:
                definition.is_enabled = normalized_is_enabled
                changed = True
            if not getattr(definition, "catalog_path", None):
                definition.catalog_path = default_catalog_path
                changed = True
            if getattr(definition, "catalog_order", None) is None:
                definition.catalog_order = default_catalog_order
                changed = True

        version_value, _ = cls._normalize_version_value(parsed.get("version"), default=cls.DEFAULT_VERSION)
        catalog_description, _ = cls._derive_catalog_description(
            name=parsed.get("name"),
            description=parsed.get("description"),
            content=parsed.get("content"),
        )
        when_to_use = cls._derive_when_to_use(
            when_to_use=None,
            catalog_description=catalog_description,
            description=parsed.get("description"),
            content=parsed.get("content"),
        )

        version_record = db.execute(
            select(AgentSkillVersion).where(
                AgentSkillVersion.skill_id == skill_id,
                AgentSkillVersion.version == version_value,
            )
        ).scalar_one_or_none()

        if version_record is None:
            existing_published = db.execute(
                select(AgentSkillVersion.id).where(
                    AgentSkillVersion.skill_id == skill_id,
                    AgentSkillVersion.status == cls.VERSION_STATUS_PUBLISHED,
                )
            ).first()
            initial_status = cls.VERSION_STATUS_PUBLISHED if existing_published is None else cls.VERSION_STATUS_DRAFT
            published_at = datetime.now(timezone.utc) if initial_status == cls.VERSION_STATUS_PUBLISHED else None

            version_record = AgentSkillVersion(
                definition_id=definition.id,
                skill_id=skill_id,
                version=version_value,
                status=initial_status,
                name=parsed["name"],
                description=parsed.get("description"),
                content=parsed["content"],
                file_hash=file_hash,
                embedding=embedding,
                is_enabled=normalized_is_enabled,
                auto_enabled=normalized_auto_enabled,
                priority=normalized_priority,
                scope=normalized_scope,
                trigger_phrases=normalized_trigger_phrases,
                conflicts_with=normalized_conflicts_with,
                catalog_description=catalog_description,
                when_to_use=when_to_use,
                published_at=published_at,
            )
            db.add(version_record)
            return True

        if version_record.definition_id != definition.id:
            version_record.definition_id = definition.id
            changed = True
        if version_record.name != parsed["name"]:
            version_record.name = parsed["name"]
            changed = True
        if version_record.description != parsed.get("description"):
            version_record.description = parsed.get("description")
            changed = True
        if version_record.content != parsed["content"]:
            version_record.content = parsed["content"]
            changed = True
        if version_record.file_hash != file_hash:
            version_record.file_hash = file_hash
            changed = True
        if version_record.embedding != embedding:
            version_record.embedding = embedding
            changed = True
        if bool(version_record.is_enabled) != normalized_is_enabled:
            version_record.is_enabled = normalized_is_enabled
            changed = True
        if bool(version_record.auto_enabled) != normalized_auto_enabled:
            version_record.auto_enabled = normalized_auto_enabled
            changed = True
        if int(version_record.priority or cls.DEFAULT_PRIORITY) != normalized_priority:
            version_record.priority = normalized_priority
            changed = True
        if version_record.scope != normalized_scope:
            version_record.scope = normalized_scope
            changed = True
        if list(version_record.trigger_phrases or []) != list(normalized_trigger_phrases):
            version_record.trigger_phrases = list(normalized_trigger_phrases)
            changed = True
        if list(version_record.conflicts_with or []) != list(normalized_conflicts_with):
            version_record.conflicts_with = list(normalized_conflicts_with)
            changed = True
        if version_record.catalog_description != catalog_description:
            version_record.catalog_description = catalog_description
            changed = True
        if version_record.when_to_use != when_to_use:
            version_record.when_to_use = when_to_use
            changed = True

        published_record = db.execute(
            select(AgentSkillVersion.id).where(
                AgentSkillVersion.skill_id == skill_id,
                AgentSkillVersion.status == cls.VERSION_STATUS_PUBLISHED,
            )
        ).first()
        if published_record is None and version_record.status != cls.VERSION_STATUS_PUBLISHED:
            version_record.status = cls.VERSION_STATUS_PUBLISHED
            changed = True

        if version_record.status == cls.VERSION_STATUS_PUBLISHED and version_record.published_at is None:
            version_record.published_at = datetime.now(timezone.utc)
            changed = True

        return changed

    @classmethod
    def _build_user_bootstrap_template(cls, db: Session) -> Dict[str, Any]:
        """按已发布版本构建用户初始化模板。"""

        default_version = cls.DEFAULT_VERSION
        template_items: List[Dict[str, Any]] = []

        version_records = db.execute(
            select(AgentSkillVersion).where(AgentSkillVersion.status == cls.VERSION_STATUS_PUBLISHED)
        ).scalars().all()

        picked_versions: Dict[str, AgentSkillVersion] = {}
        for record in sorted(version_records, key=cls._version_sort_key, reverse=True):
            if record.skill_id in picked_versions:
                continue
            picked_versions[record.skill_id] = record

        for skill_id in sorted(picked_versions):
            record = picked_versions[skill_id]
            item: Dict[str, Any] = {
                "skill_id": record.skill_id,
                "version": record.version or default_version,
                "enabled": bool(record.is_enabled),
                "priority_override": int(record.priority or cls.DEFAULT_PRIORITY),
            }
            config_override: Dict[str, Any] = {}
            if record.scope and record.scope != cls.DEFAULT_SCOPE:
                config_override["scope"] = record.scope
            if record.trigger_phrases:
                config_override["trigger_phrases"] = list(record.trigger_phrases)
            if record.conflicts_with:
                config_override["conflicts_with"] = list(record.conflicts_with)
            if config_override:
                item["config_override"] = config_override
            template_items.append(item)

        return {
            "default_version": default_version,
            "skills": template_items,
        }

    @classmethod
    def _ensure_user_bootstrap_template_config(cls, db: Session, force: bool = False) -> bool:
        """确保用户 Skill 初始化模板配置存在。"""

        existing = config_repo.get_config_by_key(db, cls.USER_BOOTSTRAP_TEMPLATE_KEY)
        if existing is not None and not force:
            return False

        template_payload = cls._build_user_bootstrap_template(db)
        if not template_payload.get("skills"):
            logger.warning("技能模板初始化配置未写入：未发现可用技能记录")
            return False

        config_repo.upsert_config(
            db=db,
            key=cls.USER_BOOTSTRAP_TEMPLATE_KEY,
            value=json.dumps(template_payload, ensure_ascii=False),
            value_type="json",
            category="skill",
            description="用户 Skill 初始化模板（默认版本 + 技能列表）",
        )
        db.commit()
        return True

    @classmethod
    def import_skill(cls, skill_path: Path, db: Session, force: bool = False) -> bool:
        """本地文件导入链已退役，禁止再作为正式写入路径。"""

        _ = skill_path, db, force
        cls._raise_local_skill_file_source_retired()

    @classmethod
    def import_all_skills(
        cls,
        skills_dir: Path,
        force: bool = False,
        whitelist: Optional[List[str]] = None,
    ) -> int:
        """本地目录导入链已退役，禁止再作为正式写入路径。"""

        _ = skills_dir, force, whitelist
        cls._raise_local_skill_file_source_retired()

    @classmethod
    def sync_changed_skills(cls, skills_dir: Path) -> int:
        """本地目录增量同步已退役，禁止再作为正式写入路径。"""

        _ = skills_dir
        cls._raise_local_skill_file_source_retired()

    @staticmethod
    def _version_sort_key(version_record: AgentSkillVersion) -> Tuple[int, float, int]:
        """版本排序键：状态优先，其次发布时间与主键。"""

        status_rank = SkillService.VERSION_STATUS_ORDER.get(
            str(version_record.status or SkillService.VERSION_STATUS_DRAFT).lower(),
            0,
        )
        ts_source = version_record.published_at or version_record.updated_at or version_record.created_at
        ts_value = ts_source.timestamp() if ts_source is not None else 0.0
        return status_rank, ts_value, int(version_record.id or 0)

    @classmethod
    def list_skill_versions(cls, db: Session, skill_id: str) -> List[Dict[str, Any]]:
        """列出技能版本信息。"""

        versions = db.execute(
            select(AgentSkillVersion).where(AgentSkillVersion.skill_id == skill_id)
        ).scalars().all()
        sorted_versions = sorted(versions, key=cls._version_sort_key, reverse=True)
        return [
            {
                "skill_id": item.skill_id,
                "version": item.version,
                "status": item.status,
                "name": item.name,
                "description": item.description,
                "is_enabled": bool(item.is_enabled),
                "auto_enabled": bool(item.auto_enabled),
                "priority": int(item.priority or cls.DEFAULT_PRIORITY),
                "scope": item.scope or cls.DEFAULT_SCOPE,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in sorted_versions
        ]

    @classmethod
    def publish_skill_version(cls, db: Session, skill_id: str, version: str) -> Dict[str, Any]:
        """发布指定技能版本。"""

        if not cls._is_skill_versioning_enabled():
            raise RuntimeError("ENABLE_SKILL_VERSIONING 未开启")

        target_version, valid_version = cls._normalize_version_value(version, default="")
        if not valid_version or not target_version:
            raise ValueError("version 非法")

        versions = db.execute(
            select(AgentSkillVersion).where(AgentSkillVersion.skill_id == skill_id)
        ).scalars().all()
        if not versions:
            raise ValueError(f"技能不存在: {skill_id}")

        target = next((item for item in versions if item.version == target_version), None)
        if target is None:
            raise ValueError(f"版本不存在: {target_version}")

        previous = next((item for item in versions if item.status == cls.VERSION_STATUS_PUBLISHED), None)
        now = datetime.now(timezone.utc)

        for item in versions:
            if item.version == target.version:
                item.status = cls.VERSION_STATUS_PUBLISHED
                item.published_at = now
            elif item.status == cls.VERSION_STATUS_PUBLISHED:
                item.status = cls.VERSION_STATUS_ROLLBACKED

        db.commit()

        return {
            "skill_id": skill_id,
            "published_version": target.version,
            "previous_version": previous.version if previous and previous.version != target.version else None,
        }

    @classmethod
    def rollback_skill_version(
        cls,
        db: Session,
        skill_id: str,
        target_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """回滚技能版本到指定版本或最近候选版本。"""

        if not cls._is_skill_versioning_enabled():
            raise RuntimeError("ENABLE_SKILL_VERSIONING 未开启")

        versions = db.execute(
            select(AgentSkillVersion).where(AgentSkillVersion.skill_id == skill_id)
        ).scalars().all()
        if not versions:
            raise ValueError(f"技能不存在: {skill_id}")

        current = next((item for item in versions if item.status == cls.VERSION_STATUS_PUBLISHED), None)

        target: Optional[AgentSkillVersion] = None
        if target_version:
            normalized_version, valid_version = cls._normalize_version_value(target_version, default="")
            if not valid_version or not normalized_version:
                raise ValueError("target_version 非法")
            target = next((item for item in versions if item.version == normalized_version), None)
            if target is None:
                raise ValueError(f"版本不存在: {normalized_version}")
        else:
            candidates = [
                item for item in versions
                if item.status != cls.VERSION_STATUS_DEPRECATED and (current is None or item.version != current.version)
            ]
            if not candidates:
                raise ValueError("没有可回滚的目标版本")
            candidates.sort(key=cls._version_sort_key, reverse=True)
            target = candidates[0]

        if current is not None and current.version != target.version:
            current.status = cls.VERSION_STATUS_ROLLBACKED

        target.status = cls.VERSION_STATUS_PUBLISHED
        target.published_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "skill_id": skill_id,
            "active_version": target.version,
            "rolled_back_from": current.version if current and current.version != target.version else None,
        }

    @classmethod
    def bind_user_skill(
        cls,
        db: Session,
        user_id: int,
        skill_id: str,
        version: str,
        is_enabled: bool = True,
        priority_override: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """绑定用户技能版本。"""

        if not cls._is_skill_versioning_enabled():
            raise RuntimeError("ENABLE_SKILL_VERSIONING 未开启")
        if not cls._is_user_skill_binding_enabled():
            raise RuntimeError("ENABLE_USER_SKILL_BINDING 未开启")

        normalized_version, valid_version = cls._normalize_version_value(version, default="")
        if not valid_version or not normalized_version:
            raise ValueError("version 非法")

        version_record = db.execute(
            select(AgentSkillVersion).where(
                AgentSkillVersion.skill_id == skill_id,
                AgentSkillVersion.version == normalized_version,
            )
        ).scalar_one_or_none()
        if version_record is None:
            raise ValueError(f"版本不存在: {normalized_version}")

        binding = db.execute(
            select(UserSkillBinding).where(
                UserSkillBinding.user_id == user_id,
                UserSkillBinding.skill_id == skill_id,
            )
        ).scalar_one_or_none()

        if binding is None:
            binding = UserSkillBinding(user_id=user_id, skill_id=skill_id)
            db.add(binding)

        binding.version = normalized_version
        binding.binding_status = cls.BINDING_STATUS_ENABLED if is_enabled else cls.BINDING_STATUS_DISABLED
        binding.is_enabled = bool(is_enabled)
        binding.priority_override = priority_override
        binding.config_override = dict(config_override or {})

        db.commit()

        return {
            "user_id": user_id,
            "skill_id": skill_id,
            "version": normalized_version,
            "binding_status": binding.binding_status,
            "is_enabled": binding.is_enabled,
            "priority_override": binding.priority_override,
        }

    @classmethod
    def rollback_user_skill_binding(
cls, db: Session, user_id: int, skill_id: str) -> Dict[str, Any]:
        """回滚用户绑定，使其回退到平台发布版本。"""

        if not cls._is_user_skill_binding_enabled():
            raise RuntimeError("ENABLE_USER_SKILL_BINDING 未开启")

        binding = db.execute(
            select(UserSkillBinding).where(
                UserSkillBinding.user_id == user_id,
                UserSkillBinding.skill_id == skill_id,
            )
        ).scalar_one_or_none()
        if binding is None:
            raise ValueError("用户绑定不存在")

        previous_version = binding.version
        binding.version = None
        binding.is_enabled = False
        binding.binding_status = cls.BINDING_STATUS_ROLLBACKED
        binding.priority_override = None

        db.commit()

        return {
            "user_id": user_id,
            "skill_id": skill_id,
            "rolled_back_version": previous_version,
            "binding_status": binding.binding_status,
        }

    @classmethod
    def list_user_skill_bindings(
        cls,
        db: Session,
        user_id: Optional[int] = None,
        skill_id: Optional[str] = None,
        binding_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """查询用户技能绑定。"""

        if not cls._is_user_skill_binding_enabled():
            return []

        query = select(UserSkillBinding)
        if user_id is not None:
            query = query.where(UserSkillBinding.user_id == user_id)
        if skill_id:
            query = query.where(UserSkillBinding.skill_id == skill_id)
        if binding_status:
            query = query.where(
                UserSkillBinding.binding_status == cls._normalize_binding_status(binding_status, default="")
            )

        bindings = db.execute(query).scalars().all()
        bindings.sort(key=lambda item: (int(item.user_id), str(item.skill_id)))

        return [
            {
                "user_id": int(item.user_id),
                "skill_id": item.skill_id,
                "version": item.version,
                "binding_status": item.binding_status,
                "is_enabled": bool(item.is_enabled),
                "priority_override": item.priority_override,
                "config_override": item.config_override or {},
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in bindings
        ]

    @classmethod
    def get_user_binding_map(cls, db: Session, user_id: int, skill_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """构造用户绑定映射。"""

        if not cls._is_user_skill_binding_enabled():
            return {}

        query = select(UserSkillBinding).where(UserSkillBinding.user_id == user_id)
        if skill_ids:
            query = query.where(UserSkillBinding.skill_id.in_(skill_ids))

        bindings = db.execute(query).scalars().all()
        return {
            item.skill_id: {
                "version": item.version,
                "binding_status": item.binding_status,
                "is_enabled": bool(item.is_enabled),
                "priority_override": item.priority_override,
                "config_override": item.config_override or {},
            }
            for item in bindings
        }

    @classmethod
    def _list_admin_skill_records(
        cls,
        db: Session,
        *,
        skill_ids: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        preserve_input_order: bool = False,
    ) -> List[Dict[str, Any]]:
        """按 definition/version/binding 聚合管理面技能视图。"""

        normalized_skill_ids: Optional[List[str]] = None
        if skill_ids is not None:
            normalized_skill_ids = []
            seen_skill_ids = set()
            for item in skill_ids:
                normalized = str(item or '').strip()
                if not normalized or normalized in seen_skill_ids:
                    continue
                normalized_skill_ids.append(normalized)
                seen_skill_ids.add(normalized)
            if not normalized_skill_ids:
                return []

        definition_query = select(AgentSkillDefinition)
        if normalized_skill_ids is not None:
            definition_query = definition_query.where(AgentSkillDefinition.skill_id.in_(normalized_skill_ids))

        definitions = db.execute(definition_query).scalars().all()
        if not definitions:
            return []

        definition_map = {item.skill_id: item for item in definitions}
        if preserve_input_order and normalized_skill_ids is not None:
            ordered_definitions = [definition_map[skill_id] for skill_id in normalized_skill_ids if skill_id in definition_map]
        else:
            ordered_definitions = sorted(
                definitions,
                key=lambda item: (
                    str(item.name or item.skill_id or '').lower(),
                    str(item.skill_id or '').lower(),
                ),
            )

        ordered_skill_ids = [item.skill_id for item in ordered_definitions]
        version_rows: List[AgentSkillVersion] = []
        if ordered_skill_ids:
            version_rows = db.execute(
                select(AgentSkillVersion).where(AgentSkillVersion.skill_id.in_(ordered_skill_ids))
            ).scalars().all()

        versions_by_skill: Dict[str, List[AgentSkillVersion]] = {}
        for row in version_rows:
            versions_by_skill.setdefault(row.skill_id, []).append(row)
        for rows in versions_by_skill.values():
            rows.sort(key=cls._version_sort_key, reverse=True)

        binding_map: Dict[str, UserSkillBinding] = {}
        if user_id is not None and ordered_skill_ids and cls._is_user_skill_binding_enabled():
            binding_rows = db.execute(
                select(UserSkillBinding).where(
                    UserSkillBinding.user_id == user_id,
                    UserSkillBinding.skill_id.in_(ordered_skill_ids),
                )
            ).scalars().all()
            binding_map = {row.skill_id: row for row in binding_rows}

        records: List[Dict[str, Any]] = []
        for definition in ordered_definitions:
            versions = versions_by_skill.get(definition.skill_id, [])
            published_version = next(
                (item for item in versions if item.status == cls.VERSION_STATUS_PUBLISHED),
                None,
            )
            latest_version = versions[0] if versions else None
            binding = binding_map.get(definition.skill_id)
            bound_version = binding.version if binding is not None else None
            bound_version_record = None
            binding_status = binding.binding_status if binding is not None else None
            if (
                binding is not None
                and binding.binding_status == cls.BINDING_STATUS_ENABLED
                and bool(binding.is_enabled)
                and binding.version
            ):
                bound_version_record = next((item for item in versions if item.version == binding.version), None)

            effective_version = bound_version_record or published_version or latest_version
            records.append(
                {
                    'definition': definition,
                    'versions': versions,
                    'published_version_record': published_version,
                    'latest_version_record': latest_version,
                    'binding': binding,
                    'bound_version': bound_version,
                    'binding_status': binding_status,
                    'effective_version_record': effective_version,
                }
            )

        return records

    @classmethod
    def _serialize_admin_skill_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """序列化管理面技能聚合记录。"""

        definition = record['definition']
        effective_version = record.get('effective_version_record')
        published_version = record.get('published_version_record')
        embedding = getattr(effective_version, 'embedding', None) if effective_version is not None else None
        content = str(getattr(effective_version, 'content', '') or '') if effective_version is not None else ''
        created_at = (
            getattr(effective_version, 'created_at', None)
            if effective_version is not None and getattr(effective_version, 'created_at', None) is not None
            else getattr(definition, 'created_at', None)
        )
        updated_at = (
            getattr(effective_version, 'updated_at', None)
            if effective_version is not None and getattr(effective_version, 'updated_at', None) is not None
            else getattr(definition, 'updated_at', None)
        )

        effective_is_enabled = getattr(effective_version, 'is_enabled', None) if effective_version is not None else None
        effective_auto_enabled = getattr(effective_version, 'auto_enabled', None) if effective_version is not None else None
        effective_priority = getattr(effective_version, 'priority', None) if effective_version is not None else None

        return {
            'id': int(getattr(effective_version, 'id', None) or getattr(definition, 'id', 0) or 0),
            'skill_id': definition.skill_id,
            'name': getattr(effective_version, 'name', None) or definition.name,
            'description': getattr(effective_version, 'description', None) if effective_version is not None else definition.description,
            'content': content,
            'content_preview': content[:200] + '...' if len(content) > 200 else content,
            'file_hash': getattr(effective_version, 'file_hash', None) if effective_version is not None else None,
            'has_embedding': embedding is not None,
            'embedding_dim': len(embedding) if embedding is not None else None,
            'is_enabled': bool(definition.is_enabled if effective_is_enabled is None else effective_is_enabled),
            'auto_enabled': bool(True if effective_auto_enabled is None else effective_auto_enabled),
            'priority': int(cls.DEFAULT_PRIORITY if effective_priority is None else effective_priority),
            'scope': getattr(effective_version, 'scope', None) or definition.scope or cls.DEFAULT_SCOPE,
            'trigger_phrases': [str(item) for item in (getattr(effective_version, 'trigger_phrases', None) or [])]
            if effective_version is not None
            else [],
            'conflicts_with': [str(item) for item in (getattr(effective_version, 'conflicts_with', None) or [])]
            if effective_version is not None
            else [],
            'published_version': getattr(published_version, 'version', None) if published_version is not None else None,
            'bound_version': record.get('bound_version'),
            'binding_status': record.get('binding_status'),
            'effective_version': getattr(effective_version, 'version', None) if effective_version is not None else None,
            'catalog_path': definition.catalog_path,
            'catalog_order': int(definition.catalog_order or cls.DEFAULT_PRIORITY),
            'catalog_description': getattr(effective_version, 'catalog_description', None) if effective_version is not None else None,
            'when_to_use': getattr(effective_version, 'when_to_use', None) if effective_version is not None else None,
            'created_at': created_at.isoformat() if created_at else None,
            'updated_at': updated_at.isoformat() if updated_at else None,
        }

    @classmethod
    def list_admin_skills(
        cls,
        db: Session,
        *,
        skip: int = 0,
        limit: Optional[int] = 50,
        search: Optional[str] = None,
        has_embedding: Optional[bool] = None,
        user_id: Optional[int] = None,
        skill_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """查询管理面技能列表，真理源固定为 definition/version/binding。"""

        records = cls._list_admin_skill_records(
            db,
            skill_ids=skill_ids,
            user_id=user_id,
            preserve_input_order=False,
        )
        items = [cls._serialize_admin_skill_record(record) for record in records]

        normalized_search = str(search or '').strip().lower()
        if normalized_search:
            items = [
                item
                for item in items
                if normalized_search in str(item.get('skill_id') or '').lower()
                or normalized_search in str(item.get('name') or '').lower()
                or normalized_search in str(item.get('description') or '').lower()
                or normalized_search in str(item.get('catalog_description') or '').lower()
                or normalized_search in str(item.get('when_to_use') or '').lower()
            ]

        if has_embedding is not None:
            items = [item for item in items if bool(item.get('has_embedding')) is has_embedding]

        if skip > 0:
            items = items[skip:]
        if limit is not None:
            items = items[:limit]
        return items

    @classmethod
    def get_admin_skill(
        cls,
        db: Session,
        skill_id: str,
        *,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """读取单个管理面技能详情。"""

        records = cls._list_admin_skill_records(
            db,
            skill_ids=[skill_id],
            user_id=user_id,
            preserve_input_order=True,
        )
        if not records:
            raise ValueError('技能不存在')
        return cls._serialize_admin_skill_record(records[0])

    @classmethod
    def get_admin_vector_status(cls, db: Session) -> Dict[str, Any]:
        """统计管理面向量状态，口径为 published 优先，否则 latest。"""

        records = cls._list_admin_skill_records(db)
        total_skills = len(records)
        with_embedding = 0
        embedding_dim: Optional[int] = None

        for record in records:
            target = record.get('published_version_record') or record.get('latest_version_record')
            embedding = getattr(target, 'embedding', None) if target is not None else None
            if embedding is None:
                continue
            with_embedding += 1
            if embedding_dim is None:
                embedding_dim = len(embedding)

        try:
            test_embedding = get_embedding('test')
            current_model_dim = len(test_embedding) if test_embedding else None
        except Exception:
            current_model_dim = None

        return {
            'total_skills': total_skills,
            'with_embedding': with_embedding,
            'without_embedding': total_skills - with_embedding,
            'embedding_dim': embedding_dim,
            'dimension_mismatch': (
                embedding_dim is not None
                and current_model_dim is not None
                and embedding_dim != current_model_dim
            ),
            'current_model_dim': current_model_dim,
        }

    @classmethod
    def _regenerate_admin_embedding_for_record(cls, record: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[int]]:
        """为管理面技能记录重新生成向量。"""

        definition = record['definition']
        skill_id = str(definition.skill_id)
        target = record.get('published_version_record') or record.get('latest_version_record')
        if target is None:
            return False, f'{skill_id}: 技能缺少可写版本记录', None

        seed_text = str(
            getattr(target, 'description', None)
            or getattr(target, 'name', None)
            or getattr(definition, 'description', None)
            or getattr(definition, 'name', None)
            or ''
        ).strip()
        if not seed_text:
            return False, f'{skill_id}: 技能缺少可向量化描述', None

        embedding = get_embedding(seed_text)
        if not embedding:
            return False, f'{skill_id}: 向量生成失败', None

        target.embedding = embedding
        return True, None, len(embedding)

    @classmethod
    def regenerate_admin_skill_embeddings(
        cls,
        db: Session,
        *,
        skill_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """批量重建管理面技能向量，目标版本为 published 优先，否则 latest。"""

        records = cls._list_admin_skill_records(
            db,
            skill_ids=skill_ids,
            preserve_input_order=skill_ids is not None,
        )
        if not records:
            raise ValueError('没有找到技能')

        success_count = 0
        errors: List[str] = []
        processed_skill_ids: List[str] = []
        for record in records:
            definition = record['definition']
            processed_skill_ids.append(str(definition.skill_id))
            try:
                updated, error_message, _ = cls._regenerate_admin_embedding_for_record(record)
            except Exception as exc:  # pragma: no cover - 外部依赖异常
                errors.append(f'{definition.skill_id}: {str(exc)}')
                continue
            if not updated:
                if error_message:
                    errors.append(error_message)
                continue
            success_count += 1

        if success_count > 0:
            db.commit()

        return {
            'success_count': success_count,
            'total': len(records),
            'errors': errors,
            'skill_ids': processed_skill_ids,
        }

    @classmethod
    def regenerate_single_admin_skill_embedding(cls, db: Session, skill_id: str) -> Dict[str, Any]:
        """重建单个管理面技能向量。"""

        records = cls._list_admin_skill_records(
            db,
            skill_ids=[skill_id],
            preserve_input_order=True,
        )
        if not records:
            raise ValueError('技能不存在')

        updated, error_message, embedding_dim = cls._regenerate_admin_embedding_for_record(records[0])
        if not updated:
            raise RuntimeError(error_message or '向量生成失败')

        db.commit()
        return {
            'message': '向量已重新生成',
            'skill_id': skill_id,
            'embedding_dim': embedding_dim,
        }

    @classmethod
    def delete_admin_skill(cls, db: Session, skill_id: str) -> Dict[str, Any]:
        """删除技能定义，并级联删除其版本与绑定。"""

        definition = db.execute(
            select(AgentSkillDefinition).where(AgentSkillDefinition.skill_id == skill_id)
        ).scalar_one_or_none()
        if definition is None:
            raise ValueError('技能不存在')

        db.delete(definition)
        db.commit()
        return {
            'message': '技能已删除',
            'skill_id': skill_id,
        }

    @staticmethod
    def _normalize_score(raw_score: Optional[float]) -> float:
        """归一化分数到 0-1。"""

        if raw_score is None:
            return 0.0
        return max(0.0, min(1.0, float(raw_score)))

    @staticmethod
    def _scope_matched(skill_scope: Optional[str], request_scope: str) -> bool:
        """判断技能作用域是否匹配。"""

        normalized_skill_scope = (skill_scope or SkillService.DEFAULT_SCOPE).strip().lower()
        normalized_request_scope = (request_scope or SkillService.DEFAULT_SCOPE).strip().lower()

        if normalized_request_scope in {"", SkillService.DEFAULT_SCOPE}:
            return True

        return normalized_skill_scope in {SkillService.DEFAULT_SCOPE, normalized_request_scope}

    @staticmethod
    def _tokenize_query(query: str) -> List[str]:
        """提取查询关键词。"""

        tokens: List[str] = []
        for raw_token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_]+", query):
            token = raw_token.lower()
            tokens.append(token)

            if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) >= 3:
                for idx in range(len(token) - 1):
                    tokens.append(token[idx : idx + 2])
                if len(token) >= 4:
                    for idx in range(len(token) - 2):
                        tokens.append(token[idx : idx + 3])

        # 去重后保持顺序，减少重复匹配开销
        return list(dict.fromkeys(tokens))

    @classmethod
    def _split_markdown_sections(cls, content: str) -> List[Tuple[str, str]]:
        """按 Markdown 标题切分技能内容。"""

        sections: List[Tuple[str, str]] = []
        current_title = "概要"
        buffer: List[str] = []

        for line in content.splitlines():
            if line.startswith("#"):
                if buffer:
                    body = "\n".join(buffer).strip()
                    if body:
                        sections.append((current_title, body))
                current_title = line.lstrip("#").strip() or "未命名章节"
                buffer = []
            else:
                buffer.append(line)

        if buffer:
            body = "\n".join(buffer).strip()
            if body:
                sections.append((current_title, body))

        if not sections and content.strip():
            sections.append(("内容", content.strip()))

        return sections

    @classmethod
    def _pick_sections(cls, content: str, query: str, max_sections: int) -> List[Tuple[str, str]]:
        """按查询相关性选择章节。"""

        sections = cls._split_markdown_sections(content)
        if not sections:
            return []

        tokens = cls._tokenize_query(query)
        if not tokens:
            return sections[:max_sections]

        scored: List[Tuple[int, int, str, str]] = []
        for idx, (title, body) in enumerate(sections):
            haystack = f"{title}\n{body}".lower()
            score = sum(1 for token in tokens if token in haystack)
            scored.append((score, -idx, title, body))

        scored.sort(reverse=True)
        selected = [(title, body) for score, _, title, body in scored if score > 0]
        if not selected:
            selected = sections

        return selected[:max_sections]

    @classmethod
    def _build_skill_fragment_with_meta(
        cls,
        skill: AgentSkill,
        query: str,
        max_sections: int = 2,
    ) -> Tuple[str, int]:
        """生成单个技能的章节级上下文片段，并返回命中章节数。"""

        selected_sections = cls._pick_sections(skill.content or "", query=query, max_sections=max_sections)
        if not selected_sections:
            fallback = f"### {skill.name}\n{(skill.description or '').strip()}\n"
            return fallback, 1 if (skill.description or "").strip() else 0

        parts: List[str] = []
        for section_title, body in selected_sections:
            snippet = body.strip()
            if len(snippet) > 400:
                snippet = f"{snippet[:400]}..."
            parts.append(f"### {skill.name} · {section_title}\n{snippet}\n")

        return "\n".join(parts), len(selected_sections)

    @classmethod
    def _build_skill_fragment(cls, skill: AgentSkill, query: str, max_sections: int = 2) -> str:
        """生成单个技能的章节级上下文片段。"""

        fragment, _ = cls._build_skill_fragment_with_meta(skill, query=query, max_sections=max_sections)
        return fragment

    @classmethod
    def _build_runtime_source_sql(cls, user_id: Optional[int]) -> Tuple[str, Dict[str, Any]]:
        """构建以 definition/version/binding 为真理源的技能运行时数据源 SQL。"""

        binding_enabled = cls._is_user_skill_binding_enabled() and user_id is not None
        params: Dict[str, Any] = {
            "binding_enabled": binding_enabled,
            "binding_user_id": int(user_id) if user_id is not None else -1,
            "default_version": cls.DEFAULT_VERSION,
        }

        source_sql = """
            WITH published_versions AS (
                SELECT DISTINCT ON (v.skill_id)
                    v.id AS version_id,
                    v.definition_id,
                    v.skill_id,
                    v.version,
                    v.name,
                    v.description,
                    v.content,
                    v.file_hash,
                    v.embedding,
                    v.is_enabled,
                    v.auto_enabled,
                    v.priority,
                    v.scope,
                    v.trigger_phrases,
                    v.conflicts_with,
                    v.status,
                    v.published_at,
                    v.updated_at,
                    v.created_at
                FROM t_agent_skill_versions v
                WHERE v.status = 'published'
                ORDER BY v.skill_id, COALESCE(v.published_at, v.updated_at, v.created_at) DESC, v.id DESC
            ),
            active_bindings AS (
                SELECT
                    b.user_id,
                    b.skill_id,
                    b.version,
                    b.binding_status,
                    b.is_enabled,
                    b.priority_override,
                    b.config_override
                FROM t_user_skill_bindings b
                WHERE (:binding_enabled = true)
                  AND b.user_id = :binding_user_id
                  AND b.binding_status = 'enabled'
                  AND b.is_enabled = true
            ),
            binding_versions AS (
                SELECT
                    b.user_id,
                    b.skill_id,
                    b.version AS bound_version,
                    b.binding_status,
                    b.priority_override,
                    b.config_override,
                    v.id AS version_id,
                    v.definition_id,
                    v.name,
                    v.description,
                    v.content,
                    v.file_hash,
                    v.embedding,
                    v.is_enabled AS version_is_enabled,
                    v.auto_enabled,
                    v.priority,
                    v.scope,
                    v.trigger_phrases,
                    v.conflicts_with,
                    CASE
                        WHEN jsonb_typeof(b.config_override -> 'scope') = 'string'
                        THEN lower(trim(both '"' from (b.config_override -> 'scope')::text))
                        ELSE NULL
                    END AS scope_override,
                    CASE
                        WHEN jsonb_typeof(b.config_override -> 'trigger_phrases') = 'array'
                        THEN b.config_override -> 'trigger_phrases'
                        ELSE NULL
                    END AS trigger_phrases_override,
                    CASE
                        WHEN jsonb_typeof(b.config_override -> 'conflicts_with') = 'array'
                        THEN b.config_override -> 'conflicts_with'
                        ELSE NULL
                    END AS conflicts_with_override
                FROM active_bindings b
                JOIN t_agent_skill_versions v
                  ON v.skill_id = b.skill_id
                 AND v.version = b.version
            )
            SELECT
                COALESCE(bv.version_id, pv.version_id, -d.id) AS id,
                d.skill_id,
                COALESCE(bv.name, pv.name, d.name) AS name,
                COALESCE(bv.description, pv.description, d.description) AS description,
                COALESCE(bv.content, pv.content, '') AS content,
                CASE
                    WHEN bv.version_id IS NOT NULL THEN COALESCE(bv.version_is_enabled, true)
                    WHEN pv.version_id IS NOT NULL THEN COALESCE(pv.is_enabled, true)
                    ELSE true
                END AS is_enabled,
                COALESCE(bv.auto_enabled, pv.auto_enabled, true) AS auto_enabled,
                COALESCE(bv.priority_override, bv.priority, pv.priority, 100) AS priority,
                COALESCE(bv.scope_override, bv.scope, pv.scope, d.scope, 'global') AS scope,
                COALESCE(
                    bv.trigger_phrases_override,
                    bv.trigger_phrases,
                    pv.trigger_phrases,
                    '[]'::jsonb
                ) AS trigger_phrases,
                COALESCE(
                    bv.conflicts_with_override,
                    bv.conflicts_with,
                    pv.conflicts_with,
                    '[]'::jsonb
                ) AS conflicts_with,
                COALESCE(bv.embedding, pv.embedding) AS embedding,
                COALESCE(bv.bound_version, pv.version, :default_version) AS effective_version,
                COALESCE(bv.binding_status, 'default') AS binding_status
            FROM t_agent_skill_definitions d
            LEFT JOIN published_versions pv
              ON pv.skill_id = d.skill_id
            LEFT JOIN binding_versions bv
              ON bv.skill_id = d.skill_id
            WHERE d.is_enabled = true
        """

        return source_sql, params

    @classmethod
    def _build_candidate_from_row(cls, row: Any) -> Dict[str, Any]:
        """将 SQL 行映射为统一候选结构。"""

        return {
            "id": row.id,
            "skill_id": row.skill_id,
            "name": row.name,
            "description": row.description,
            "content": row.content,
            "is_enabled": row.is_enabled,
            "auto_enabled": row.auto_enabled,
            "priority": row.priority,
            "scope": row.scope,
            "trigger_phrases": row.trigger_phrases or [],
            "conflicts_with": row.conflicts_with or [],
            "effective_version": getattr(row, "effective_version", None),
            "binding_status": getattr(row, "binding_status", None),
        }

    @classmethod
    def _fetch_vector_candidates(
        cls,
        db: Session,
        query_embedding: List[float],
        limit: int,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """召回向量候选。"""

        source_sql, base_params = cls._build_runtime_source_sql(user_id)

        sql = text(
            f"""
            WITH runtime_skills AS (
                {source_sql}
            )
            SELECT
                id,
                skill_id,
                name,
                description,
                content,
                is_enabled,
                auto_enabled,
                priority,
                scope,
                trigger_phrases,
                conflicts_with,
                effective_version,
                binding_status,
                1 - (embedding <=> CAST(:query_vec AS vector)) AS vector_score
            FROM runtime_skills
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :limit
            """
        )

        params = {
            **base_params,
            "query_vec": query_embedding,
            "limit": limit,
        }
        try:
            rows = db.execute(sql, params)
        except Exception as exc:  # pragma: no cover - 数据库检索异常
            logger.warning("技能检索: definition/version 向量召回失败 - %s", exc)
            raise

        candidates: List[Dict[str, Any]] = []
        for row in rows:
            candidate = cls._build_candidate_from_row(row)
            candidate.update(
                {
                    "vector_score": cls._normalize_score(row.vector_score),
                    "lexical_score": 0.0,
                    "trigger_hit": 0.0,
                }
            )
            candidates.append(candidate)

        return candidates

    @classmethod
    def _fetch_lexical_candidates(
        cls,
        db: Session,
        query: str,
        limit: int,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """召回关键词候选。"""

        source_sql, base_params = cls._build_runtime_source_sql(user_id)

        sql = text(
            f"""
            WITH runtime_skills AS (
                {source_sql}
            )
            SELECT
                id,
                skill_id,
                name,
                description,
                content,
                is_enabled,
                auto_enabled,
                priority,
                scope,
                trigger_phrases,
                conflicts_with,
                effective_version,
                binding_status,
                ts_rank_cd(
                    to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, '') || ' ' || coalesce(content, '')),
                    plainto_tsquery('simple', :query)
                ) AS lexical_score,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements_text(coalesce(trigger_phrases, '[]'::jsonb)) AS phrase
                        WHERE lower(:raw_query) LIKE '%' || lower(phrase) || '%'
                    ) THEN 1.0
                    ELSE 0.0
                END AS trigger_hit
            FROM runtime_skills
            WHERE
                to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, '') || ' ' || coalesce(content, ''))
                @@ plainto_tsquery('simple', :query)
                OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(coalesce(trigger_phrases, '[]'::jsonb)) AS phrase
                    WHERE lower(:raw_query) LIKE '%' || lower(phrase) || '%'
                )
            ORDER BY lexical_score DESC, priority ASC
            LIMIT :limit
            """
        )

        params = {
            **base_params,
            "query": query,
            "raw_query": query.lower(),
            "limit": limit,
        }
        try:
            rows = db.execute(sql, params)
        except Exception as exc:  # pragma: no cover - 数据库检索异常
            logger.warning("技能检索: definition/version 关键词召回失败 - %s", exc)
            raise

        candidates: List[Dict[str, Any]] = []
        for row in rows:
            candidate = cls._build_candidate_from_row(row)
            candidate.update(
                {
                    "vector_score": 0.0,
                    "lexical_score": max(0.0, float(row.lexical_score or 0.0)),
                    "trigger_hit": cls._normalize_score(row.trigger_hit),
                }
            )
            candidates.append(candidate)

        return candidates

    @classmethod
    def _merge_candidates(

        cls,
        vector_candidates: List[Dict[str, Any]],
        lexical_candidates: List[Dict[str, Any]],
        mode: str,
    ) -> List[Dict[str, Any]]:
        """合并向量和关键词候选。"""

        merged: Dict[str, Dict[str, Any]] = {}

        for candidate in vector_candidates + lexical_candidates:
            skill_id = candidate["skill_id"]
            if skill_id not in merged:
                merged[skill_id] = candidate.copy()
                continue

            existing = merged[skill_id]
            existing["vector_score"] = max(existing.get("vector_score", 0.0), candidate.get("vector_score", 0.0))
            existing["lexical_score"] = max(existing.get("lexical_score", 0.0), candidate.get("lexical_score", 0.0))
            existing["trigger_hit"] = max(existing.get("trigger_hit", 0.0), candidate.get("trigger_hit", 0.0))

        candidates = list(merged.values())
        max_lexical = max((item.get("lexical_score", 0.0) for item in candidates), default=0.0)

        vector_weight = ConfigResolver.get_float("skill.hybrid.vector_weight", 0.65)
        lexical_weight = ConfigResolver.get_float("skill.hybrid.lexical_weight", 0.25)
        trigger_weight = ConfigResolver.get_float("skill.hybrid.trigger_weight", 0.10)

        for item in candidates:
            lexical_score = item.get("lexical_score", 0.0)
            lexical_norm = (lexical_score / max_lexical) if max_lexical > 0 else 0.0
            item["lexical_score"] = cls._normalize_score(lexical_norm)
            item["vector_score"] = cls._normalize_score(item.get("vector_score", 0.0))
            item["trigger_hit"] = cls._normalize_score(item.get("trigger_hit", 0.0))

            if mode == "vector":
                item["final_score"] = item["vector_score"]
            else:
                item["final_score"] = cls._normalize_score(
                    vector_weight * item["vector_score"]
                    + lexical_weight * item["lexical_score"]
                    + trigger_weight * item["trigger_hit"]
                )

        candidates.sort(key=lambda x: (x.get("final_score", 0.0), -int(x.get("priority", 100))), reverse=True)
        return candidates

    @classmethod
    def _apply_policy_filters(
        cls,
        candidates: List[Dict[str, Any]],
        top_k: int,
        threshold: float,
        scope: str,
        auto_only: bool,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """执行启用状态、作用域和冲突裁决过滤。"""

        selected: List[Dict[str, Any]] = []
        dropped: List[Dict[str, Any]] = []

        ranked = sorted(
            candidates,
            key=lambda x: (x.get("final_score", 0.0), -int(x.get("priority", 100))),
            reverse=True,
        )

        for item in ranked:
            score = item.get("final_score", 0.0)
            trigger_hit = item.get("trigger_hit", 0.0)
            if score < threshold and trigger_hit < 1.0:
                dropped.append({"skill_id": item["skill_id"], "reason": "below_threshold", "score": round(score, 4)})
                continue

            if not item.get("is_enabled", True):
                dropped.append({"skill_id": item["skill_id"], "reason": "disabled"})
                continue

            if auto_only and not item.get("auto_enabled", True):
                dropped.append({"skill_id": item["skill_id"], "reason": "auto_disabled"})
                continue

            if not cls._scope_matched(item.get("scope"), scope):
                dropped.append({"skill_id": item["skill_id"], "reason": "scope_mismatch"})
                continue

            conflict_index = None
            for idx, selected_item in enumerate(selected):
                current_conflicts = {str(v) for v in (item.get("conflicts_with") or [])}
                selected_conflicts = {str(v) for v in (selected_item.get("conflicts_with") or [])}
                if item["skill_id"] in selected_conflicts or selected_item["skill_id"] in current_conflicts:
                    conflict_index = idx
                    break

            if conflict_index is None:
                selected.append(item)
                continue

            conflict_item = selected[conflict_index]
            current_priority = int(item.get("priority", 100))
            conflict_priority = int(conflict_item.get("priority", 100))
            current_score = float(item.get("final_score", 0.0))
            conflict_score = float(conflict_item.get("final_score", 0.0))

            if current_priority < conflict_priority or (
                current_priority == conflict_priority and current_score > conflict_score
            ):
                dropped.append(
                    {
                        "skill_id": conflict_item["skill_id"],
                        "reason": "conflict_replaced",
                        "replaced_by": item["skill_id"],
                    }
                )
                selected[conflict_index] = item
            else:
                dropped.append(
                    {
                        "skill_id": item["skill_id"],
                        "reason": "conflict",
                        "conflict_with": conflict_item["skill_id"],
                    }
                )

        selected.sort(
            key=lambda x: (x.get("final_score", 0.0), -int(x.get("priority", 100))),
            reverse=True,
        )
        if len(selected) > top_k:
            for overflow in selected[top_k:]:
                dropped.append({"skill_id": overflow["skill_id"], "reason": "top_k_overflow"})
            selected = selected[:top_k]

        return selected, dropped

    @classmethod
    def _build_retrieval_log(
        cls,
        query: str,
        thread_id: Optional[str],
        trace_id: Optional[str],
        user_id: Optional[int],
        retrieval_mode: str,
        runtime_source_mode: str,
        strict_user_mode: bool,
        scope: str,
        top_k: int,
        base_threshold: float,
        effective_threshold: float,
        vector_candidates: List[Dict[str, Any]],
        lexical_candidates: List[Dict[str, Any]],
        merged_candidates: List[Dict[str, Any]],
        selected_candidates: List[Dict[str, Any]],
        dropped_candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """构建结构化检索日志，支撑 query->candidates->final 追踪。"""

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thread_id": cls._normalize_trace_key(thread_id),
            "trace_id": cls._normalize_trace_key(trace_id),
            "user_id": user_id,
            "query_hash": cls._compute_query_hash(query),
            "query_length": len(query.strip()),
            "mode": retrieval_mode,
            "runtime_source_mode": runtime_source_mode,
            "strict_user_mode": bool(strict_user_mode),
            "scope": scope,
            "top_k": top_k,
            "threshold": round(base_threshold, 4),
            "effective_threshold": round(effective_threshold, 4),
            "vector_candidate_count": len(vector_candidates),
            "lexical_candidate_count": len(lexical_candidates),
            "candidate_count": len(merged_candidates),
            "candidate_skill_ids": [item["skill_id"] for item in merged_candidates[: min(20, len(merged_candidates))]],
            "selected_skill_ids": [item["skill_id"] for item in selected_candidates],
            "selected_count": len(selected_candidates),
            "dropped_count": len(dropped_candidates),
            "dropped_preview": dropped_candidates[: min(6, len(dropped_candidates))],
        }

    @classmethod
    def _search_skills_internal(
        cls,
        query: str,
        top_k: int,
        threshold: Optional[float],
        scope: str,
        auto_only: bool,
        thread_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Tuple[List[AgentSkill], Dict[str, Any]]:
        """统一检索入口，返回技能列表和调试信息。"""

        runtime_source_mode = cls._get_runtime_source_mode()
        strict_user_mode = runtime_source_mode == cls.RUNTIME_SOURCE_MODE_STRICT_USER

        if not query.strip():
            retrieval_log = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thread_id": cls._normalize_trace_key(thread_id),
                "trace_id": cls._normalize_trace_key(trace_id),
                "user_id": user_id,
                "query_hash": cls._compute_query_hash(query),
                "query_length": 0,
                "mode": "none",
                "runtime_source_mode": runtime_source_mode,
                "strict_user_mode": strict_user_mode,
                "scope": scope,
                "top_k": max(1, top_k),
                "threshold": None,
                "effective_threshold": None,
                "vector_candidate_count": 0,
                "lexical_candidate_count": 0,
                "candidate_count": 0,
                "candidate_skill_ids": [],
                "selected_skill_ids": [],
                "selected_count": 0,
                "dropped_count": 0,
                "dropped_preview": [],
                "reason": "empty_query",
            }
            logger.info("技能检索日志: %s", json.dumps(retrieval_log, ensure_ascii=False, sort_keys=True))
            return [], {"reason": "empty_query", "retrieval_log": retrieval_log}

        configured_top_k = ConfigResolver.get_int("skill.top_k", top_k)
        final_top_k = top_k if top_k > 0 else max(1, configured_top_k)

        base_threshold = (
            float(threshold)
            if threshold is not None
            else ConfigResolver.get_float("skill_similarity_threshold", SKILL_SIMILARITY_THRESHOLD)
        )
        retrieval_mode = ConfigResolver.get_string("skill.retrieval_mode", "hybrid").lower()
        candidate_multiplier = max(2, ConfigResolver.get_int("skill.hybrid.candidate_multiplier", 3))
        section_max_count = max(1, ConfigResolver.get_int("skill.section_max_count", 2))

        vector_candidates: List[Dict[str, Any]] = []
        lexical_candidates: List[Dict[str, Any]] = []

        query_embedding: Optional[List[float]] = None
        if retrieval_mode in {"hybrid", "vector"}:
            try:
                query_embedding = get_embedding(query)
            except Exception as exc:  # pragma: no cover - 外部依赖异常
                logger.warning("技能检索: 生成 embedding 失败，降级关键词检索 - %s", exc)
                query_embedding = None

        with get_db_context() as db:
            if query_embedding:
                try:
                    vector_candidates = cls._fetch_vector_candidates(
                        db,
                        query_embedding=query_embedding,
                        limit=final_top_k * candidate_multiplier,
                        user_id=user_id,
                    )
                except Exception as exc:  # pragma: no cover - 数据库检索异常
                    logger.warning(
                        "技能检索: runtime_source_mode=%s 向量召回失败，降级关键词检索 - %s",
                        runtime_source_mode,
                        exc,
                    )
                    vector_candidates = []
            elif retrieval_mode == "vector":
                logger.warning("技能检索: vector 模式下 embedding 不可用，回退到 hybrid")
                retrieval_mode = "hybrid"

            if retrieval_mode == "hybrid" or not vector_candidates:
                try:
                    lexical_candidates = cls._fetch_lexical_candidates(
                        db,
                        query=query,
                        limit=final_top_k * candidate_multiplier,
                        user_id=user_id,
                    )
                except Exception as exc:  # pragma: no cover - 数据库检索异常
                    logger.warning(
                        "技能检索: runtime_source_mode=%s 关键词召回失败 - %s",
                        runtime_source_mode,
                        exc,
                    )
                    lexical_candidates = []

        merged = cls._merge_candidates(vector_candidates, lexical_candidates, mode=retrieval_mode)
        effective_threshold = min(base_threshold, 0.35) if retrieval_mode == "hybrid" else base_threshold
        selected, dropped = cls._apply_policy_filters(
            merged,
            top_k=final_top_k,
            threshold=effective_threshold,
            scope=scope,
            auto_only=auto_only,
        )

        skills: List[AgentSkill] = []
        context_max_length = max(800, ConfigResolver.get_int("skill.context_max_length", 2400))

        for item in selected:
            skill = AgentSkill(
                id=item["id"],
                skill_id=item["skill_id"],
                name=item["name"],
                description=item.get("description"),
                content=item.get("content") or "",
                is_enabled=item.get("is_enabled", True),
                auto_enabled=item.get("auto_enabled", True),
                priority=item.get("priority", 100),
                scope=item.get("scope") or cls.DEFAULT_SCOPE,
                trigger_phrases=item.get("trigger_phrases") or [],
                conflicts_with=item.get("conflicts_with") or [],
            )
            skill._effective_version = item.get("effective_version")
            skill._binding_status = item.get("binding_status")
            skill._retrieval_score = item.get("final_score", 0.0)
            skill._vector_score = item.get("vector_score", 0.0)
            skill._lexical_score = item.get("lexical_score", 0.0)
            skill._trigger_hit = item.get("trigger_hit", 0.0)
            fragment, section_count = cls._build_skill_fragment_with_meta(
                skill,
                query=query,
                max_sections=section_max_count,
            )
            skill._lazy_context_fragment = fragment
            skill._lazy_section_count = section_count
            skills.append(skill)

        retrieval_log = cls._build_retrieval_log(
            query=query,
            thread_id=thread_id,
            trace_id=trace_id,
            user_id=user_id,
            retrieval_mode=retrieval_mode,
            runtime_source_mode=runtime_source_mode,
            strict_user_mode=strict_user_mode,
            scope=scope,
            top_k=final_top_k,
            base_threshold=base_threshold,
            effective_threshold=effective_threshold,
            vector_candidates=vector_candidates,
            lexical_candidates=lexical_candidates,
            merged_candidates=merged,
            selected_candidates=selected,
            dropped_candidates=dropped,
        )

        debug_info = {
            "query": query,
            "mode": retrieval_mode,
            "runtime_source_mode": runtime_source_mode,
            "strict_user_mode": strict_user_mode,
            "scope": scope,
            "user_id": user_id,
            "threshold": base_threshold,
            "effective_threshold": effective_threshold,
            "vector_candidates": [
                {"skill_id": item["skill_id"], "vector_score": round(item.get("vector_score", 0.0), 4)}
                for item in vector_candidates[: min(10, len(vector_candidates))]
            ],
            "lexical_candidates": [
                {
                    "skill_id": item["skill_id"],
                    "lexical_score": round(item.get("lexical_score", 0.0), 4),
                    "trigger_hit": round(item.get("trigger_hit", 0.0), 4),
                }
                for item in lexical_candidates[: min(10, len(lexical_candidates))]
            ],
            "merged_candidates": [
                {
                    "skill_id": item["skill_id"],
                    "vector_score": round(item.get("vector_score", 0.0), 4),
                    "lexical_score": round(item.get("lexical_score", 0.0), 4),
                    "trigger_hit": round(item.get("trigger_hit", 0.0), 4),
                    "final_score": round(item.get("final_score", 0.0), 4),
                    "priority": item.get("priority", 100),
                    "scope": item.get("scope") or cls.DEFAULT_SCOPE,
                    "is_enabled": item.get("is_enabled", True),
                    "auto_enabled": item.get("auto_enabled", True),
                    "effective_version": item.get("effective_version"),
                    "binding_status": item.get("binding_status"),
                }
                for item in merged[: min(20, len(merged))]
            ],
            "final_candidates": [
                {
                    "skill_id": item["skill_id"],
                    "final_score": round(item.get("final_score", 0.0), 4),
                    "priority": item.get("priority", 100),
                    "effective_version": item.get("effective_version"),
                }
                for item in selected
            ],
            "dropped": dropped,
            "selected_skill_ids": [item["skill_id"] for item in selected],
            "context_budget": context_max_length,
            "retrieval_log": retrieval_log,
        }

        merged_preview = ", ".join(
            [
                f"{item['skill_id']}(f={item.get('final_score', 0.0):.3f},v={item.get('vector_score', 0.0):.3f},l={item.get('lexical_score', 0.0):.3f})"
                for item in merged[: min(6, len(merged))]
            ]
        )
        logger.info(
            "技能检索: mode=%s, runtime_source_mode=%s, strict_user=%s, scope=%s, 阈值=%.3f/%.3f, 候选=[%s], 入选=%s, 淘汰=%s",
            retrieval_mode,
            runtime_source_mode,
            strict_user_mode,
            scope,
            base_threshold,
            effective_threshold,
            merged_preview,
            [item["skill_id"] for item in selected],
            dropped[:4],
        )
        logger.info("技能检索日志: %s", json.dumps(retrieval_log, ensure_ascii=False, sort_keys=True))

        return skills, debug_info

    @classmethod
    def search_skills(
        cls,
        query: str,
        top_k: int = 2,
        threshold: float = None,
        scope: str = DEFAULT_SCOPE,
        auto_only: bool = True,
        thread_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> List[AgentSkill]:
        """检索相关技能（支持 hybrid/vector 策略）。"""

        search_kwargs: Dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "threshold": threshold,
            "scope": scope,
            "auto_only": auto_only,
            "thread_id": thread_id,
            "trace_id": trace_id,
        }
        if user_id is not None:
            search_kwargs["user_id"] = user_id

        skills, _ = cls._search_skills_internal(**search_kwargs)
        return skills

    @classmethod
    def search_skills_debug(
        cls,
        query: str,
        top_k: int = 5,
        threshold: float = None,
        scope: str = DEFAULT_SCOPE,
        auto_only: bool = False,
        thread_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """检索技能并返回调试信息。"""

        search_kwargs: Dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "threshold": threshold,
            "scope": scope,
            "auto_only": auto_only,
            "thread_id": thread_id,
            "trace_id": trace_id,
        }
        if user_id is not None:
            search_kwargs["user_id"] = user_id

        skills, debug = cls._search_skills_internal(**search_kwargs)

        context_budget = int(debug.get("context_budget") or 1200)
        context_preview, injection_meta = cls.format_skills_as_context_with_meta(skills, max_length=context_budget)

        results = [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "score": round(float(getattr(skill, "_retrieval_score", 0.0)), 4),
                "vector_score": round(float(getattr(skill, "_vector_score", 0.0)), 4),
                "lexical_score": round(float(getattr(skill, "_lexical_score", 0.0)), 4),
                "trigger_hit": round(float(getattr(skill, "_trigger_hit", 0.0)), 4),
                "effective_version": getattr(skill, "_effective_version", None),
                "binding_status": getattr(skill, "_binding_status", None),
            }
            for skill in skills
        ]

        selected_skill_ids = [skill.skill_id for skill in skills]
        dropped_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for dropped_item in debug.get("dropped", []):
            skill_id = str(dropped_item.get("skill_id", "")).strip()
            if not skill_id:
                continue
            dropped_by_skill.setdefault(skill_id, []).append(dropped_item)

        merged_candidates = debug.get("merged_candidates", [])
        if merged_candidates:
            skill_candidates = [
                {
                    **candidate,
                    "selected": candidate.get("skill_id") in selected_skill_ids,
                    "drop_reasons": dropped_by_skill.get(candidate.get("skill_id", ""), []),
                }
                for candidate in merged_candidates
            ]
        else:
            skill_candidates = [
                {
                    "skill_id": item["skill_id"],
                    "vector_score": item["vector_score"],
                    "lexical_score": item["lexical_score"],
                    "trigger_hit": item["trigger_hit"],
                    "final_score": item["score"],
                    "selected": True,
                    "drop_reasons": [],
                }
                for item in results
            ]

        retrieval_log = debug.get("retrieval_log")
        if not isinstance(retrieval_log, dict):
            runtime_source_mode = str(
                debug.get("runtime_source_mode") or cls._get_runtime_source_mode()
            )
            retrieval_log = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thread_id": cls._normalize_trace_key(thread_id),
                "trace_id": cls._normalize_trace_key(trace_id),
                "user_id": user_id,
                "query_hash": cls._compute_query_hash(query),
                "query_length": len(query.strip()),
                "mode": str(debug.get("mode") or "unknown"),
                "runtime_source_mode": runtime_source_mode,
                "strict_user_mode": bool(
                    debug.get("strict_user_mode")
                    if debug.get("strict_user_mode") is not None
                    else runtime_source_mode == cls.RUNTIME_SOURCE_MODE_STRICT_USER
                ),
                "scope": str(debug.get("scope") or scope),
                "top_k": top_k,
                "threshold": debug.get("threshold"),
                "effective_threshold": debug.get("effective_threshold"),
                "vector_candidate_count": len(debug.get("vector_candidates") or []),
                "lexical_candidate_count": len(debug.get("lexical_candidates") or []),
                "candidate_count": len(skill_candidates),
                "candidate_skill_ids": [item.get("skill_id") for item in skill_candidates if item.get("skill_id")],
                "selected_skill_ids": selected_skill_ids,
                "selected_count": len(selected_skill_ids),
                "dropped_count": len(debug.get("dropped") or []),
                "dropped_preview": (debug.get("dropped") or [])[:6],
            }

        debug["results"] = results
        debug["count"] = len(skills)
        debug["context_preview"] = context_preview
        debug["skill_candidates"] = skill_candidates
        debug["selected_skill_ids"] = selected_skill_ids
        debug["retrieval_log"] = retrieval_log
        debug["skill_injection_meta"] = {
            **injection_meta,
            "mode": debug.get("mode"),
            "scope": debug.get("scope"),
            "top_k": top_k,
            "selected_count": len(selected_skill_ids),
        }
        return debug

    @classmethod
    def get_by_id(cls, skill_id: str) -> Optional[AgentSkill]:
        """根据 skill_id 获取技能，来源固定为 definition/version 真理源。"""

        with get_db_context() as db:
            payload = cls.get_admin_skill(db, skill_id)

        skill = AgentSkill(
            id=payload["id"],
            skill_id=payload["skill_id"],
            name=payload["name"],
            description=payload.get("description"),
            content=payload.get("content") or "",
            file_hash=payload.get("file_hash"),
            is_enabled=payload.get("is_enabled", True),
            auto_enabled=payload.get("auto_enabled", True),
            priority=payload.get("priority", cls.DEFAULT_PRIORITY),
            scope=payload.get("scope") or cls.DEFAULT_SCOPE,
            trigger_phrases=payload.get("trigger_phrases") or [],
            conflicts_with=payload.get("conflicts_with") or [],
        )
        skill.embedding = [0.0] * int(payload["embedding_dim"]) if payload.get("has_embedding") and payload.get("embedding_dim") else None
        skill._effective_version = payload.get("effective_version")
        skill._binding_status = payload.get("binding_status")
        return skill

    @classmethod
    def format_skills_as_context_with_meta(
        cls,
        skills: List[AgentSkill],
        max_length: int = 2000,
    ) -> Tuple[str, Dict[str, Any]]:
        """将技能列表格式化为注入上下文，并返回预算使用元信息。"""

        configured_max_length = ConfigResolver.get_int("skill.context_max_length", max_length)
        final_limit = min(max_length, configured_max_length) if max_length > 0 else configured_max_length
        if final_limit <= 0:
            final_limit = configured_max_length if configured_max_length > 0 else 2000

        if not skills:
            return "", {
                "budget_chars": final_limit,
                "used_chars": 0,
                "truncated": False,
                "included_skill_ids": [],
                "excluded_skill_ids": [],
                "sections_used": 0,
            }

        context_parts: List[str] = []
        total_length = 0
        sections_used = 0
        included_skill_ids: List[str] = []
        excluded_skill_ids: List[str] = []
        truncated = False

        for index, skill in enumerate(skills):
            fragment = getattr(skill, "_lazy_context_fragment", None)
            if not fragment:
                fragment, section_count = cls._build_skill_fragment_with_meta(
                    skill,
                    query=skill.description or "",
                    max_sections=1,
                )
            else:
                section_count = int(getattr(skill, "_lazy_section_count", 0) or 0)
                if section_count <= 0:
                    section_count = fragment.count("### ") or 1

            if total_length + len(fragment) > final_limit:
                truncated = True
                excluded_skill_ids.extend([item.skill_id for item in skills[index:]])
                break

            context_parts.append(fragment)
            total_length += len(fragment)
            sections_used += section_count
            included_skill_ids.append(skill.skill_id)

        return "\n".join(context_parts), {
            "budget_chars": final_limit,
            "used_chars": total_length,
            "truncated": truncated,
            "included_skill_ids": included_skill_ids,
            "excluded_skill_ids": excluded_skill_ids,
            "sections_used": sections_used,
        }

    @classmethod
    def format_skills_as_context(cls, skills: List[AgentSkill], max_length: int = 2000) -> str:
        """将技能列表格式化为注入上下文。"""

        context, _ = cls.format_skills_as_context_with_meta(skills, max_length=max_length)
        return context

    @classmethod
    def _build_definition_runtime_source_sql(cls, user_id: Optional[int]) -> Tuple[str, Dict[str, Any]]:
        """构建以 definition/version/binding 为真理源的运行时视图 SQL。"""

        binding_enabled = cls._is_user_skill_binding_enabled() and user_id is not None
        params: Dict[str, Any] = {
            "binding_enabled": binding_enabled,
            "binding_user_id": int(user_id) if user_id is not None else -1,
            "default_version": cls.DEFAULT_VERSION,
        }

        source_sql = """
            WITH published_versions AS (
                SELECT DISTINCT ON (v.skill_id)
                    v.id AS version_id,
                    v.definition_id,
                    v.skill_id,
                    v.version,
                    v.name,
                    v.description,
                    v.content,
                    v.file_hash,
                    v.embedding,
                    v.is_enabled,
                    v.auto_enabled,
                    v.priority,
                    v.scope,
                    v.trigger_phrases,
                    v.conflicts_with,
                    v.catalog_description,
                    v.when_to_use,
                    v.status,
                    v.published_at,
                    v.updated_at,
                    v.created_at
                FROM t_agent_skill_versions v
                WHERE v.status = 'published'
                ORDER BY v.skill_id, COALESCE(v.published_at, v.updated_at, v.created_at) DESC, v.id DESC
            ),
            active_bindings AS (
                SELECT
                    b.user_id,
                    b.skill_id,
                    b.version,
                    b.binding_status,
                    b.is_enabled,
                    b.priority_override,
                    b.config_override
                FROM t_user_skill_bindings b
                WHERE (:binding_enabled = true)
                  AND b.user_id = :binding_user_id
                  AND b.binding_status = 'enabled'
                  AND b.is_enabled = true
            ),
            binding_versions AS (
                SELECT
                    b.user_id,
                    b.skill_id,
                    b.version AS bound_version,
                    b.binding_status,
                    b.priority_override,
                    b.config_override,
                    v.id AS version_id,
                    v.definition_id,
                    v.name,
                    v.description,
                    v.content,
                    v.file_hash,
                    v.embedding,
                    v.is_enabled AS version_is_enabled,
                    v.auto_enabled,
                    v.priority,
                    v.scope,
                    v.trigger_phrases,
                    v.conflicts_with,
                    v.catalog_description,
                    v.when_to_use,
                    CASE
                        WHEN jsonb_typeof(b.config_override -> 'scope') = 'string'
                        THEN lower(trim(both '"' from (b.config_override -> 'scope')::text))
                        ELSE NULL
                    END AS scope_override,
                    CASE
                        WHEN jsonb_typeof(b.config_override -> 'trigger_phrases') = 'array'
                        THEN b.config_override -> 'trigger_phrases'
                        ELSE NULL
                    END AS trigger_phrases_override,
                    CASE
                        WHEN jsonb_typeof(b.config_override -> 'conflicts_with') = 'array'
                        THEN b.config_override -> 'conflicts_with'
                        ELSE NULL
                    END AS conflicts_with_override
                FROM active_bindings b
                JOIN t_agent_skill_versions v
                  ON v.skill_id = b.skill_id
                 AND v.version = b.version
            )
            SELECT
                COALESCE(bv.version_id, pv.version_id, -d.id) AS id,
                d.skill_id,
                COALESCE(bv.name, pv.name, d.name) AS name,
                COALESCE(bv.description, pv.description, d.description) AS description,
                COALESCE(bv.content, pv.content, '') AS content,
                CASE
                    WHEN bv.version_id IS NOT NULL THEN COALESCE(bv.version_is_enabled, true)
                    WHEN pv.version_id IS NOT NULL THEN COALESCE(pv.is_enabled, true)
                    ELSE true
                END AS is_enabled,
                COALESCE(bv.auto_enabled, pv.auto_enabled, true) AS auto_enabled,
                COALESCE(bv.priority_override, bv.priority, pv.priority, 100) AS priority,
                COALESCE(bv.scope_override, bv.scope, pv.scope, d.scope, 'global') AS scope,
                COALESCE(
                    bv.trigger_phrases_override,
                    bv.trigger_phrases,
                    pv.trigger_phrases,
                    '[]'::jsonb
                ) AS trigger_phrases,
                COALESCE(
                    bv.conflicts_with_override,
                    bv.conflicts_with,
                    pv.conflicts_with,
                    '[]'::jsonb
                ) AS conflicts_with,
                COALESCE(bv.embedding, pv.embedding) AS embedding,
                COALESCE(bv.bound_version, pv.version, :default_version) AS effective_version,
                COALESCE(bv.binding_status, 'default') AS binding_status,
                COALESCE(d.catalog_path, replace(d.skill_id, '.', '/')) AS catalog_path,
                COALESCE(d.catalog_order, COALESCE(bv.priority_override, bv.priority, pv.priority, 100)) AS catalog_order,
                COALESCE(
                    NULLIF(bv.catalog_description, ''),
                    NULLIF(pv.catalog_description, ''),
                    NULLIF(bv.description, ''),
                    NULLIF(pv.description, ''),
                    NULLIF(d.description, '')
                ) AS catalog_description,
                COALESCE(
                    NULLIF(bv.when_to_use, ''),
                    NULLIF(pv.when_to_use, ''),
                    NULLIF(bv.catalog_description, ''),
                    NULLIF(pv.catalog_description, ''),
                    NULLIF(bv.description, ''),
                    NULLIF(pv.description, ''),
                    NULLIF(d.description, '')
                ) AS when_to_use
            FROM t_agent_skill_definitions d
            LEFT JOIN published_versions pv
              ON pv.skill_id = d.skill_id
            LEFT JOIN binding_versions bv
              ON bv.skill_id = d.skill_id
            WHERE d.is_enabled = true
        """
        return source_sql, params

    @staticmethod
    def _rows_from_execute_result(result: Any) -> List[Any]:
        """统一拉平 execute 返回，兼容 SQLAlchemy Result 与测试假对象。"""

        if result is None:
            return []
        if hasattr(result, 'fetchall'):
            return list(result.fetchall())
        return list(result)

    @staticmethod
    def _clean_catalog_text(raw_value: Any, max_length: int) -> str:
        """压缩 catalog 文本，避免首轮 prompt 出现长正文。"""

        normalized = re.sub(r"\s+", " ", str(raw_value or '').strip())
        if not normalized:
            return ''
        if len(normalized) <= max_length:
            return normalized
        return f"{normalized[: max_length - 1].rstrip()}…"

    @staticmethod
    def _extract_skill_summary(content: Any) -> str:
        """从 SKILL 正文提取可读摘要，用于派生 catalog 描述。"""

        text_content = str(content or '').strip()
        if not text_content:
            return ''

        text_content = re.sub(r"^---\s*\n.*?\n---\s*\n", '', text_content, flags=re.S)
        for line in text_content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            return re.sub(r"\s+", ' ', stripped)
        return ''

    @classmethod
    def _derive_catalog_description(cls, *, name: Any, description: Any, content: Any) -> Tuple[str, str]:
        """派生首轮 catalog description，并返回来源标签。"""

        raw_description = cls._clean_catalog_text(description, 240)
        if raw_description and len(raw_description) <= 180:
            return raw_description, 'description'

        summary = cls._clean_catalog_text(cls._extract_skill_summary(content), 240)
        if summary:
            return summary, 'derived_catalog_description'

        display_name = cls._clean_catalog_text(name, 80) or '当前技能'
        return f'在需要 {display_name} 专业能力时加载该技能。', 'fallback'

    @classmethod
    def _derive_when_to_use(
        cls,
        *,
        when_to_use: Any,
        catalog_description: Any,
        description: Any,
        content: Any,
    ) -> str:
        """派生 when_to_use 短句。"""

        for candidate in (when_to_use, catalog_description, description, cls._extract_skill_summary(content)):
            normalized = cls._clean_catalog_text(candidate, 160)
            if normalized:
                return normalized
        return '当问题明确需要该技能的专门流程、规则或模板时使用。'

    @classmethod
    def _normalize_catalog_path(cls, skill_id: str, raw_value: Any) -> str:
        """标准化 catalog_path。"""

        normalized = str(raw_value or '').strip().strip('/')
        if not normalized:
            normalized = skill_id.replace('.', '/')
        normalized = re.sub(r'/+', '/', normalized)
        return normalized.lower()

    @classmethod
    def _normalize_catalog_order(cls, raw_value: Any, default: int) -> int:
        """标准化 catalog_order。"""

        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return int(default)

    @classmethod
    def _list_definition_runtime_rows(
        cls,
        db: Session,
        *,
        user_id: Optional[int],
        skill_ids: Optional[List[str]] = None,
        require_content: bool = False,
    ) -> List[Any]:
        """查询 definition/version/binding 运行时视图行。"""

        if skill_ids is not None and not skill_ids:
            return []

        source_sql, params = cls._build_definition_runtime_source_sql(user_id)
        where_clauses: List[str] = []
        if require_content:
            where_clauses.append("COALESCE(content, '') <> ''")
        if skill_ids is not None:
            where_clauses.append('skill_id IN :skill_ids')
            params['skill_ids'] = list(skill_ids)

        where_sql = ''
        if where_clauses:
            where_sql = 'WHERE ' + ' AND '.join(where_clauses)

        statement = text(
            f"""
            WITH runtime_skills AS (
                {source_sql}
            )
            SELECT *
            FROM runtime_skills
            {where_sql}
            ORDER BY COALESCE(catalog_order, priority, 100), COALESCE(catalog_path, replace(skill_id, '.', '/')), skill_id
            """
        )
        if skill_ids is not None:
            statement = statement.bindparams(bindparam('skill_ids', expanding=True))
        result = db.execute(statement, params)
        return cls._rows_from_execute_result(result)

    @classmethod
    def build_catalog_descriptor(cls, row: Any) -> Dict[str, Any]:
        """将 runtime 行转换为首轮 catalog descriptor。"""

        skill_id = str(getattr(row, 'skill_id', '') or '').strip()
        if not skill_id:
            raise ValueError('catalog row 缺少 skill_id')

        display_name = cls._clean_catalog_text(getattr(row, 'name', None) or skill_id, 120) or skill_id
        raw_catalog_description = ''
        description_source = 'derived_catalog_description'
        if cls._is_skill_catalog_metadata_normalization_enabled():
            raw_catalog_description = cls._clean_catalog_text(getattr(row, 'catalog_description', None), 240)
            if raw_catalog_description:
                description_source = 'catalog_description'
        if not raw_catalog_description:
            raw_catalog_description, description_source = cls._derive_catalog_description(
                name=display_name,
                description=getattr(row, 'description', None),
                content=getattr(row, 'content', None),
            )

        when_to_use = cls._derive_when_to_use(
            when_to_use=getattr(row, 'when_to_use', None),
            catalog_description=raw_catalog_description,
            description=getattr(row, 'description', None),
            content=getattr(row, 'content', None),
        )

        effective_version = str(getattr(row, 'effective_version', None) or cls.DEFAULT_VERSION)
        priority_default = int(getattr(row, 'priority', cls.DEFAULT_PRIORITY) or cls.DEFAULT_PRIORITY)
        catalog_path = cls._normalize_catalog_path(skill_id, getattr(row, 'catalog_path', None))
        catalog_order = cls._normalize_catalog_order(getattr(row, 'catalog_order', None), default=priority_default)

        return {
            'skill_id': skill_id,
            'display_name': display_name,
            'description': raw_catalog_description,
            'effective_version': effective_version,
            'when_to_use': when_to_use,
            'catalog_path': catalog_path,
            'catalog_order': catalog_order,
            'scope': str(getattr(row, 'scope', None) or cls.DEFAULT_SCOPE),
            'binding_status': getattr(row, 'binding_status', None),
            'description_source': description_source,
            'description_length': len(raw_catalog_description),
        }

    @classmethod
    def _compute_catalog_version(cls, manifest: List[Dict[str, Any]]) -> str:
        """根据 manifest 计算稳定版本号。"""

        stable_payload = [
            {
                'skill_id': item['skill_id'],
                'effective_version': item.get('effective_version'),
                'catalog_path': item.get('catalog_path'),
                'catalog_order': item.get('catalog_order'),
                'description': item.get('description'),
                'when_to_use': item.get('when_to_use'),
            }
            for item in manifest
        ]
        raw_payload = json.dumps(stable_payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()[:16]

    @classmethod
    def build_skill_catalog_manifest(cls, user_id: Optional[int] = None) -> Dict[str, Any]:
        """构建当前用户可见的 Skill catalog manifest。"""

        with get_db_context() as db:
            rows = cls._list_definition_runtime_rows(
                db,
                user_id=user_id,
                require_content=True,
            )

        manifest: List[Dict[str, Any]] = []
        seen_skill_ids: set[str] = set()
        for row in rows:
            if not bool(getattr(row, 'is_enabled', True)):
                continue
            skill_id = str(getattr(row, 'skill_id', '') or '').strip()
            if not skill_id or skill_id in seen_skill_ids:
                continue
            manifest.append(cls.build_catalog_descriptor(row))
            seen_skill_ids.add(skill_id)

        manifest.sort(
            key=lambda item: (
                int(item.get('catalog_order', cls.DEFAULT_PRIORITY)),
                str(item.get('catalog_path') or item['skill_id']),
                item['skill_id'],
            )
        )
        catalog_version = cls._compute_catalog_version(manifest)
        return {
            'manifest': manifest,
            'catalog_version': catalog_version,
            'visible_skill_count': len(manifest),
            'catalog_build_source': cls.SKILL_CATALOG_SOURCE,
        }

    @classmethod
    def format_skill_catalog_as_context_with_meta(
        cls,
        manifest: List[Dict[str, Any]],
        max_length: int = 2400,
    ) -> Tuple[str, Dict[str, Any]]:
        """将 catalog manifest 渲染为首轮 prompt 上下文。"""

        configured_max_length = ConfigResolver.get_int('skill.context_max_length', max_length)
        final_limit = min(max_length, configured_max_length) if max_length > 0 else configured_max_length
        if final_limit <= 0:
            final_limit = configured_max_length if configured_max_length > 0 else 2400

        if not manifest:
            return '', {
                'budget_chars': final_limit,
                'used_chars': 0,
                'truncated': False,
                'included_skill_ids': [],
                'excluded_skill_ids': [],
                'visible_skill_count': 0,
            }

        context_parts: List[str] = [cls.SKILL_CATALOG_HEADER]
        total_length = len(cls.SKILL_CATALOG_HEADER)
        included_skill_ids: List[str] = []
        excluded_skill_ids: List[str] = []
        truncated = False

        for index, item in enumerate(manifest):
            line = (
                f"- {item.get('catalog_path') or item['skill_id']} | {item.get('display_name') or item['skill_id']} "
                f"| {item.get('effective_version') or cls.DEFAULT_VERSION} | {item.get('when_to_use') or item.get('description') or ''}"
            )
            line = cls._clean_catalog_text(line, 320)
            candidate = f"\n{line}"
            if total_length + len(candidate) > final_limit:
                truncated = True
                excluded_skill_ids.extend([entry['skill_id'] for entry in manifest[index:]])
                break
            context_parts.append(candidate)
            total_length += len(candidate)
            included_skill_ids.append(item['skill_id'])

        return ''.join(context_parts), {
            'budget_chars': final_limit,
            'used_chars': total_length,
            'truncated': truncated,
            'included_skill_ids': included_skill_ids,
            'excluded_skill_ids': excluded_skill_ids,
            'visible_skill_count': len(manifest),
        }

    @classmethod
    def format_skill_catalog_as_context(cls, manifest: List[Dict[str, Any]], max_length: int = 2400) -> str:
        """将 catalog manifest 渲染为首轮 prompt 文本。"""

        context, _ = cls.format_skill_catalog_as_context_with_meta(manifest, max_length=max_length)
        return context

    @classmethod
    def validate_visible_skill_ids(
        cls,
        skill_ids: List[str],
        *,
        user_id: Optional[int] = None,
        loaded_skill_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """校验本轮请求的 skill_id 是否属于当前 catalog 或已在会话中加载。"""

        normalized_skill_ids: List[str] = []
        seen: set[str] = set()
        for raw_value in skill_ids or []:
            skill_id = str(raw_value or '').strip()
            if not skill_id or skill_id in seen:
                continue
            normalized_skill_ids.append(skill_id)
            seen.add(skill_id)

        if len(normalized_skill_ids) > cls.MAX_LOAD_SKILLS_COUNT:
            return {
                'normalized_skill_ids': normalized_skill_ids,
                'valid_skill_ids': [],
                'errors': [{
                    'code': 'over_limit',
                    'message': f'单次最多加载 {cls.MAX_LOAD_SKILLS_COUNT} 个 skill_id',
                    'requested_count': len(normalized_skill_ids),
                }],
                'visible_by_id': {},
                'catalog_version': None,
                'visible_skill_count': 0,
            }

        manifest_payload = cls.build_skill_catalog_manifest(user_id=user_id)
        visible_by_id = {item['skill_id']: item for item in manifest_payload['manifest']}
        registry = loaded_skill_registry or {}
        valid_skill_ids: List[str] = []
        errors: List[Dict[str, Any]] = []

        for skill_id in normalized_skill_ids:
            if skill_id in registry or skill_id in visible_by_id:
                valid_skill_ids.append(skill_id)
                continue
            errors.append({
                'skill_id': skill_id,
                'code': 'not_visible',
                'message': 'skill_id 不属于当前用户可见 catalog',
            })

        return {
            'normalized_skill_ids': normalized_skill_ids,
            'valid_skill_ids': valid_skill_ids,
            'errors': errors,
            'visible_by_id': visible_by_id,
            'catalog_version': manifest_payload['catalog_version'],
            'visible_skill_count': manifest_payload['visible_skill_count'],
        }

    @classmethod
    def _load_version_records(
        cls,
        db: Session,
        requested_versions: Dict[str, str],
    ) -> Dict[Tuple[str, str], AgentSkillVersion]:
        """按 skill_id/version 批量加载版本记录。"""

        if not requested_versions:
            return {}

        records = db.execute(
            select(AgentSkillVersion).where(AgentSkillVersion.skill_id.in_(list(requested_versions.keys())))
        ).scalars().all()
        version_map: Dict[Tuple[str, str], AgentSkillVersion] = {}
        for record in records:
            normalized_version = str(record.version or cls.DEFAULT_VERSION)
            if requested_versions.get(record.skill_id) != normalized_version:
                continue
            version_map[(record.skill_id, normalized_version)] = record
        return version_map

    @classmethod
    def _build_loaded_skill_context_payload(
        cls,
        db: Session,
        loaded_skill_registry: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """根据 loaded_skill_registry 重建后续轮次所需的 Skill 正文上下文。"""

        requested_versions = {
            skill_id: str((payload or {}).get('version') or cls.DEFAULT_VERSION)
            for skill_id, payload in loaded_skill_registry.items()
            if str(skill_id or '').strip()
        }
        version_map = cls._load_version_records(db, requested_versions)
        context_parts: List[str] = []
        loaded_skills: List[Dict[str, Any]] = []
        missing_skills: List[Dict[str, Any]] = []

        for skill_id, payload in loaded_skill_registry.items():
            version = str((payload or {}).get('version') or cls.DEFAULT_VERSION)
            record = version_map.get((skill_id, version))
            if record is None or not str(record.content or '').strip():
                missing_skills.append({'skill_id': skill_id, 'version': version})
                continue

            loaded_skills.append({
                'skill_id': skill_id,
                'version': version,
                'truncated': bool((payload or {}).get('truncated', False)),
            })
            context_parts.append(
                f"### {record.name or skill_id} | skill_id={skill_id} | version={version}\n{str(record.content or '').strip()}"
            )

        loaded_skill_context = None
        if context_parts:
            loaded_skill_context = '以下技能正文已加载到当前会话，可直接复用：\n\n' + '\n\n'.join(context_parts)

        return {
            'loaded_skill_context': loaded_skill_context,
            'loaded_skills': loaded_skills,
            'missing_skills': missing_skills,
        }

    @classmethod
    def build_loaded_skill_context_from_registry(
        cls,
        loaded_skill_registry: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """从 registry 直接回源重建 loaded_skill_context。"""

        if not loaded_skill_registry:
            return {
                'loaded_skill_context': None,
                'loaded_skills': [],
                'missing_skills': [],
            }

        with get_db_context() as db:
            return cls._build_loaded_skill_context_payload(db, loaded_skill_registry)

    @classmethod
    def load_skills_for_session(
        cls,
        *,
        skill_ids: List[str],
        user_id: Optional[int] = None,
        loaded_skill_registry: Optional[Dict[str, Dict[str, Any]]] = None,
        source_turn_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """按当前 catalog 与会话 registry 加载 Skill 正文。"""

        existing_registry = {
            str(skill_id): dict(payload or {})
            for skill_id, payload in (loaded_skill_registry or {}).items()
            if str(skill_id or '').strip()
        }
        validation = cls.validate_visible_skill_ids(
            skill_ids,
            user_id=user_id,
            loaded_skill_registry=existing_registry,
        )
        errors = list(validation['errors'])
        if any(item.get('code') == 'over_limit' for item in errors):
            return {
                'requested_skill_ids': validation['normalized_skill_ids'],
                'loaded_skills': [],
                'errors': errors,
                'truncated_count': 0,
                'loaded_skill_registry': existing_registry,
                'loaded_skill_context': None,
                'catalog_version': validation['catalog_version'],
                'visible_skill_count': validation['visible_skill_count'],
            }

        visible_by_id = validation['visible_by_id']
        requested_versions: Dict[str, str] = {}
        for skill_id in validation['valid_skill_ids']:
            existing = existing_registry.get(skill_id)
            if existing and existing.get('version'):
                requested_versions[skill_id] = str(existing['version'])
                continue
            descriptor = visible_by_id.get(skill_id)
            requested_versions[skill_id] = str(
                (descriptor or {}).get('effective_version') or cls.DEFAULT_VERSION
            )

        with get_db_context() as db:
            version_map = cls._load_version_records(db, requested_versions)
            updated_registry = {skill_id: dict(payload) for skill_id, payload in existing_registry.items()}
            loaded_skills: List[Dict[str, Any]] = []

            for skill_id in validation['valid_skill_ids']:
                version = requested_versions[skill_id]
                record = version_map.get((skill_id, version))
                if record is None:
                    errors.append({
                        'skill_id': skill_id,
                        'code': 'not_found',
                        'message': f'未找到 skill_id={skill_id} version={version} 的版本记录',
                    })
                    continue

                content = str(record.content or '').strip()
                if not content:
                    errors.append({
                        'skill_id': skill_id,
                        'code': 'load_failed',
                        'message': 'Skill 正文为空，无法加载',
                    })
                    continue

                if skill_id not in updated_registry:
                    updated_registry[skill_id] = {
                        'skill_id': skill_id,
                        'version': version,
                        'truncated': False,
                        'source_turn_id': source_turn_id,
                    }
                elif not updated_registry[skill_id].get('source_turn_id') and source_turn_id:
                    updated_registry[skill_id]['source_turn_id'] = source_turn_id

                loaded_skills.append({
                    'skill_id': skill_id,
                    'effective_version': version,
                    'content': content,
                    'truncated': False,
                })

            context_payload = cls._build_loaded_skill_context_payload(db, updated_registry)

        return {
            'requested_skill_ids': validation['normalized_skill_ids'],
            'loaded_skills': loaded_skills,
            'errors': errors,
            'truncated_count': 0,
            'loaded_skill_registry': updated_registry,
            'loaded_skill_context': context_payload['loaded_skill_context'],
            'catalog_version': validation['catalog_version'],
            'visible_skill_count': validation['visible_skill_count'],
            'missing_skills': context_payload['missing_skills'],
        }

    @classmethod
    def update_skill_catalog_metadata(
        cls,
        db: Session,
        *,
        skill_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """将 catalog/runtime metadata 写入 definition/version 真理源。"""

        definition = db.execute(
            select(AgentSkillDefinition).where(AgentSkillDefinition.skill_id == skill_id)
        ).scalar_one_or_none()
        if definition is None:
            raise ValueError('技能不存在')

        version_records = db.execute(
            select(AgentSkillVersion).where(AgentSkillVersion.skill_id == skill_id)
        ).scalars().all()
        target_version = None
        if version_records:
            target_version = sorted(version_records, key=cls._version_sort_key, reverse=True)[0]

        version_scoped_fields = {
            'auto_enabled',
            'priority',
            'trigger_phrases',
            'conflicts_with',
            'catalog_description',
            'when_to_use',
        }
        if target_version is None and version_scoped_fields.intersection(updates.keys()):
            raise ValueError('技能缺少可写版本记录，无法更新版本级 metadata')

        updated_fields: List[str] = []
        if 'catalog_path' in updates:
            definition.catalog_path = cls._normalize_catalog_path(skill_id, updates['catalog_path'])
            updated_fields.append('catalog_path')
        if 'catalog_order' in updates:
            definition.catalog_order = cls._normalize_catalog_order(updates['catalog_order'], cls.DEFAULT_PRIORITY)
            updated_fields.append('catalog_order')
        if 'is_enabled' in updates:
            definition.is_enabled = bool(updates['is_enabled'])
            updated_fields.append('is_enabled')
            if target_version is not None:
                target_version.is_enabled = bool(updates['is_enabled'])
        if 'scope' in updates:
            normalized_scope = str(updates['scope'] or cls.DEFAULT_SCOPE).strip().lower() or cls.DEFAULT_SCOPE
            definition.scope = normalized_scope
            updated_fields.append('scope')
            if target_version is not None:
                target_version.scope = normalized_scope

        if target_version is not None:
            if 'auto_enabled' in updates:
                target_version.auto_enabled = bool(updates['auto_enabled'])
                updated_fields.append('auto_enabled')
            if 'priority' in updates:
                target_version.priority = int(updates['priority'])
                updated_fields.append('priority')
            if 'trigger_phrases' in updates:
                target_version.trigger_phrases = list(updates['trigger_phrases'] or [])
                updated_fields.append('trigger_phrases')
            if 'conflicts_with' in updates:
                target_version.conflicts_with = list(updates['conflicts_with'] or [])
                updated_fields.append('conflicts_with')
            if 'catalog_description' in updates:
                target_version.catalog_description = cls._clean_catalog_text(updates['catalog_description'], 240) or None
                updated_fields.append('catalog_description')
            if 'when_to_use' in updates:
                target_version.when_to_use = cls._clean_catalog_text(updates['when_to_use'], 160) or None
                updated_fields.append('when_to_use')

        db.commit()
        return {
            'skill_id': skill_id,
            'updated': bool(updated_fields),
            'updated_fields': updated_fields,
        }
