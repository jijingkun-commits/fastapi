"""用户 Skill 自维护 API。"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user_skill import (
    UserSkillItem,
    UserSkillPatchRequest,
    UserSkillPatchResponse,
    UserSkillResetResponse,
)
from app.services.skill_service import SkillService

router = APIRouter(prefix="/user-skills", tags=["用户技能"])


def _resolve_effective_version(binding: Dict[str, Any]) -> str | None:
    """根据绑定状态推导生效版本。"""

    if not binding:
        return None
    if binding.get("binding_status") != SkillService.BINDING_STATUS_ENABLED:
        return None
    if not bool(binding.get("is_enabled", False)):
        return None
    version = binding.get("version")
    if version is None:
        return None
    normalized = str(version).strip()
    return normalized or None


@router.get("", response_model=List[UserSkillItem])
def list_current_user_skills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户 Skill 绑定与生效版本。"""

    try:
        bindings = SkillService.list_user_skill_bindings(db=db, user_id=current_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return [
        UserSkillItem(
            user_id=int(item["user_id"]),
            skill_id=str(item["skill_id"]),
            version=item.get("version"),
            effective_version=_resolve_effective_version(item),
            binding_status=str(item.get("binding_status") or SkillService.BINDING_STATUS_DISABLED),
            is_enabled=bool(item.get("is_enabled", False)),
            priority_override=item.get("priority_override"),
            config_override=dict(item.get("config_override") or {}),
            updated_at=item.get("updated_at"),
        )
        for item in bindings
    ]


@router.patch("/{skill_id}", response_model=UserSkillPatchResponse)
def patch_current_user_skill(
    skill_id: str,
    request: UserSkillPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新当前用户单个 Skill 绑定配置。"""

    normalized_skill_id = str(skill_id or "").strip()
    if not normalized_skill_id:
        raise HTTPException(status_code=400, detail="skill_id 不能为空")

    try:
        existing_bindings = SkillService.list_user_skill_bindings(
            db=db,
            user_id=current_user.id,
            skill_id=normalized_skill_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    existing = existing_bindings[0] if existing_bindings else {}
    resolved_version = (
        request.version
        or existing.get("version")
        or SkillService.DEFAULT_VERSION
    )
    resolved_is_enabled = (
        request.is_enabled
        if request.is_enabled is not None
        else bool(existing.get("is_enabled", True))
    )
    resolved_priority_override = (
        request.priority_override
        if request.priority_override is not None
        else existing.get("priority_override")
    )
    resolved_config_override = (
        dict(request.config_override)
        if request.config_override is not None
        else dict(existing.get("config_override") or {})
    )

    try:
        payload = SkillService.bind_user_skill(
            db=db,
            user_id=current_user.id,
            skill_id=normalized_skill_id,
            version=resolved_version,
            is_enabled=resolved_is_enabled,
            priority_override=resolved_priority_override,
            config_override=resolved_config_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return UserSkillPatchResponse(
        user_id=int(payload["user_id"]),
        skill_id=str(payload["skill_id"]),
        version=str(payload["version"]),
        binding_status=str(payload["binding_status"]),
        is_enabled=bool(payload.get("is_enabled", False)),
        priority_override=payload.get("priority_override"),
        config_override=resolved_config_override,
    )


@router.post("/{skill_id}/reset", response_model=UserSkillResetResponse)
def reset_current_user_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将当前用户单个 Skill 回滚到模板默认。"""

    normalized_skill_id = str(skill_id or "").strip()
    if not normalized_skill_id:
        raise HTTPException(status_code=400, detail="skill_id 不能为空")

    try:
        payload = SkillService.rollback_user_skill_binding(
            db=db,
            user_id=current_user.id,
            skill_id=normalized_skill_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return UserSkillResetResponse(
        user_id=int(payload["user_id"]),
        skill_id=str(payload["skill_id"]),
        rolled_back_version=payload.get("rolled_back_version"),
        binding_status=str(payload["binding_status"]),
    )
