"""访问控制管理 API Schema（中文注释）。"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class DataRole(str, Enum):
    """数据角色枚举（G0 冻结）。"""

    HEAD_PRESIDENT = "head_president"
    DEPARTMENT_GM = "department_gm"
    DEPARTMENT_VGM = "department_vgm"
    STAFF = "staff"


def _normalize_identifier(value: str) -> str:
    """规范化标识符输入。"""

    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("字段不能为空")
    return normalized


class TablePolicyRuleSchema(BaseModel):
    """表级权限规则。"""

    schema_name: str = Field(description="Schema 名称")
    table_name: str = Field(description="表名，支持 * 通配符")
    allow_access: bool = Field(default=True, description="是否允许访问")
    description: str | None = Field(default=None, description="规则描述")

    @field_validator("schema_name", "table_name")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        """统一规范化 schema/table 标识符。"""

        return _normalize_identifier(value)


class RowPolicyRuleSchema(BaseModel):
    """行级权限规则。"""

    schema_name: str = Field(description="Schema 名称")
    table_name: str = Field(description="表名，支持 * 通配符")
    filter_column: str = Field(description="过滤列")
    filter_source: Literal["user.org_code", "user.dept_code", "fixed"] = Field(
        description="过滤值来源"
    )
    filter_value: str | None = Field(default=None, description="固定过滤值")
    filter_operator: str = Field(default="=", description="过滤操作符")
    description: str | None = Field(default=None, description="规则描述")

    @field_validator("schema_name", "table_name", "filter_column")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        """统一规范化 schema/table/column 标识符。"""

        return _normalize_identifier(value)

    @field_validator("filter_operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        """规范化操作符。"""

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("filter_operator 不能为空")
        return normalized

    @model_validator(mode="after")
    def validate_fixed_source(self) -> "RowPolicyRuleSchema":
        """fixed 来源必须提供 filter_value。"""

        if self.filter_source == "fixed" and not (self.filter_value or "").strip():
            raise ValueError("filter_source=fixed 时必须提供 filter_value")
        return self


class ColumnPolicyRuleSchema(BaseModel):
    """列级权限规则。"""

    schema_name: str = Field(description="Schema 名称")
    table_name: str = Field(description="表名")
    column_name: str = Field(description="列名")
    mask_type: Literal["hide", "partial", "hash"] = Field(description="脱敏类型")
    description: str | None = Field(default=None, description="规则描述")

    @field_validator("schema_name", "table_name", "column_name")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        """统一规范化 schema/table/column 标识符。"""

        return _normalize_identifier(value)


class DataRolePolicyUpsertRequest(BaseModel):
    """数据角色策略更新请求。"""

    table_rules: list[TablePolicyRuleSchema] = Field(default_factory=list)
    row_rules: list[RowPolicyRuleSchema] = Field(default_factory=list)
    column_rules: list[ColumnPolicyRuleSchema] = Field(default_factory=list)


class DataRolePolicySummary(BaseModel):
    """数据角色策略摘要。"""

    table_rule_count: int
    row_rule_count: int
    column_rule_count: int


class DataRolePolicyResponse(BaseModel):
    """数据角色策略响应。"""

    data_role: DataRole
    table_rules: list[TablePolicyRuleSchema] = Field(default_factory=list)
    row_rules: list[RowPolicyRuleSchema] = Field(default_factory=list)
    column_rules: list[ColumnPolicyRuleSchema] = Field(default_factory=list)
    summary: DataRolePolicySummary


class DataRolePolicyListResponse(BaseModel):
    """数据角色策略列表响应。"""

    items: list[DataRolePolicyResponse] = Field(default_factory=list)


class DataRolePolicyDeleteResponse(BaseModel):
    """删除数据角色策略响应。"""

    data_role: DataRole
    deleted: dict[str, int]
    total_deleted: int


class SQLDryRunRequest(BaseModel):
    """SQL 试跑请求。"""

    user_id: int = Field(description="目标用户 ID")
    sql: str = Field(description="待评估 SQL")
    auto_limit: bool = Field(default=True, description="是否自动追加 LIMIT")
    limit: int = Field(default=1000, ge=1, le=10000, description="自动 LIMIT 行数")


class PermissionHitSchema(BaseModel):
    """策略命中明细。"""

    schema_name: str
    table_name: str
    full_name: str
    allowed: bool
    hit_rule_type: str
    matched_rule: str | None = None
    reason: str | None = None


class SQLDryRunResponse(BaseModel):
    """SQL 试跑响应。"""

    user_id: int
    data_role: str
    is_allowed: bool
    original_sql: str
    rewritten_sql: str
    reason: str | None = None
    reason_code: str
    denied_stage: str | None = None
    policy_hits: list[PermissionHitSchema] = Field(default_factory=list)


__all__ = [
    "DataRole",
    "TablePolicyRuleSchema",
    "RowPolicyRuleSchema",
    "ColumnPolicyRuleSchema",
    "DataRolePolicyUpsertRequest",
    "DataRolePolicySummary",
    "DataRolePolicyResponse",
    "DataRolePolicyListResponse",
    "DataRolePolicyDeleteResponse",
    "SQLDryRunRequest",
    "PermissionHitSchema",
    "SQLDryRunResponse",
]
