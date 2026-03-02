"""用户 Skill 自维护接口 Schema。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserSkillItem(BaseModel):
    """当前用户的 Skill 绑定详情。"""

    user_id: int
    skill_id: str
    version: Optional[str] = None
    effective_version: Optional[str] = None
    binding_status: str
    is_enabled: bool
    priority_override: Optional[int] = Field(default=None, ge=0, le=10000)
    config_override: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[str] = None


class UserSkillPatchRequest(BaseModel):
    """用户 Skill 更新请求。"""

    model_config = ConfigDict(extra="forbid")

    version: Optional[str] = Field(default=None, min_length=1, max_length=64)
    is_enabled: Optional[bool] = None
    priority_override: Optional[int] = Field(default=None, ge=0, le=10000)
    config_override: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_non_empty(self) -> "UserSkillPatchRequest":
        """至少包含一个可更新字段。"""

        if (
            self.version is None
            and self.is_enabled is None
            and self.priority_override is None
            and self.config_override is None
        ):
            raise ValueError("至少提供一个可更新字段")
        return self


class UserSkillPatchResponse(BaseModel):
    """用户 Skill 更新响应。"""

    user_id: int
    skill_id: str
    version: str
    binding_status: str
    is_enabled: bool
    priority_override: Optional[int] = None
    config_override: Dict[str, Any] = Field(default_factory=dict)


class UserSkillResetResponse(BaseModel):
    """用户 Skill 重置响应。"""

    user_id: int
    skill_id: str
    rolled_back_version: Optional[str] = None
    binding_status: str
