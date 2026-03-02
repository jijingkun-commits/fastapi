"""用户 Skill 初始化服务（中文注释）。

负责读取统一模板并写入用户绑定层，作为 create_user 的后置链路。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.config_resolver import ConfigResolver
from app.services.skill_service import SkillService

logger = logging.getLogger(__name__)

USER_SKILL_BOOTSTRAP_TEMPLATE_KEY = SkillService.USER_BOOTSTRAP_TEMPLATE_KEY
DEFAULT_USER_SKILL_BOOTSTRAP_TEMPLATE = {
    "default_version": SkillService.DEFAULT_VERSION,
    "skills": [],
}


def _is_bootstrap_enabled() -> bool:
    """判断是否启用用户 Skill 初始化链路。"""

    versioning_enabled = ConfigResolver.get_bool("feature.enable_skill_versioning", False)
    binding_enabled = ConfigResolver.get_bool("feature.enable_user_skill_binding", False)
    return bool(versioning_enabled and binding_enabled)


def _normalize_version(raw_value: Any, default: str) -> str:
    """标准化版本号。"""

    normalized, is_valid = SkillService._normalize_version_value(raw_value, default=default)
    if not is_valid:
        return default
    return normalized


def _normalize_priority_override(raw_value: Any) -> Optional[int]:
    """解析 priority_override，非法值返回 None。"""

    if raw_value is None:
        return None

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    if value < SkillService.PRIORITY_MIN or value > SkillService.PRIORITY_MAX:
        return None
    return value


def _normalize_config_override(raw_value: Any) -> Dict[str, Any]:
    """标准化 config_override。"""

    if isinstance(raw_value, dict):
        return dict(raw_value)
    return {}


def normalize_bootstrap_template(raw_template: Any) -> Dict[str, Any]:
    """归一化用户 Skill 初始化模板。"""

    if not isinstance(raw_template, dict):
        return dict(DEFAULT_USER_SKILL_BOOTSTRAP_TEMPLATE)

    default_version = _normalize_version(
        raw_template.get("default_version"),
        default=SkillService.DEFAULT_VERSION,
    )
    raw_skills = raw_template.get("skills")
    if not isinstance(raw_skills, list):
        raw_skills = []

    normalized_skills: List[Dict[str, Any]] = []
    for item in raw_skills:
        if not isinstance(item, dict):
            continue

        skill_id = str(item.get("skill_id") or "").strip()
        if not skill_id:
            continue

        version = _normalize_version(item.get("version"), default=default_version)
        priority_override = _normalize_priority_override(item.get("priority_override"))
        if item.get("priority_override") is not None and priority_override is None:
            continue

        normalized_item: Dict[str, Any] = {
            "skill_id": skill_id,
            "version": version,
            "enabled": bool(item.get("enabled", True)),
            "priority_override": priority_override,
            "config_override": _normalize_config_override(item.get("config_override")),
        }
        normalized_skills.append(normalized_item)

    return {
        "default_version": default_version,
        "skills": normalized_skills,
    }


def load_bootstrap_template_from_config() -> Dict[str, Any]:
    """读取并归一化模板配置。"""

    template = ConfigResolver.get_json_dict(
        USER_SKILL_BOOTSTRAP_TEMPLATE_KEY,
        DEFAULT_USER_SKILL_BOOTSTRAP_TEMPLATE,
    )
    normalized = normalize_bootstrap_template(template)
    if normalized.get("skills"):
        return normalized
    return dict(DEFAULT_USER_SKILL_BOOTSTRAP_TEMPLATE)


def bootstrap_user_skills(
    db: Session,
    *,
    user_id: int,
    template: Dict[str, Any] | None = None,
) -> int:
    """为新用户初始化 Skill 绑定。"""

    if not user_id:
        return 0

    if not _is_bootstrap_enabled():
        return 0

    template_payload = (
        load_bootstrap_template_from_config()
        if template is None
        else normalize_bootstrap_template(template)
    )
    skills = template_payload.get("skills") or []
    if not skills:
        return 0

    seeded_count = 0
    for item in skills:
        try:
            SkillService.bind_user_skill(
                db=db,
                user_id=user_id,
                skill_id=item["skill_id"],
                version=item["version"],
                is_enabled=bool(item.get("enabled", True)),
                priority_override=item.get("priority_override"),
                config_override=item.get("config_override") or {},
            )
            seeded_count += 1
        except Exception as exc:  # pragma: no cover - 异常路径仅做日志观测
            logger.warning(
                "用户 Skill 模板初始化失败，已跳过: user_id=%s skill_id=%s error=%s",
                user_id,
                item.get("skill_id"),
                exc,
            )

    return seeded_count
