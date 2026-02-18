"""用户相关的 Pydantic 模型（中文注释）。"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SysRole = Literal["user", "analyst", "admin"]
DataRole = Literal["head_president", "department_gm", "department_vgm", "staff"]


class LoginRequest(BaseModel):
    """登录请求体：支持用户名或手机号+密码。"""

    username: Optional[str] = None
    mobile: Optional[str] = None
    password: str


class Token(BaseModel):
    """访问令牌响应。"""

    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """用户对外展示模型（基础版）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: Optional[str] = None
    mobile: Optional[str] = None
    data_role: Optional[DataRole] = "staff"
    data_role_label: Optional[str] = None


class UserCreate(BaseModel):
    """创建用户请求体。"""

    username: str = Field(..., min_length=1, max_length=200, description="用户名（必填，唯一）")
    password: str = Field(..., min_length=6, max_length=100, description="密码（必填，至少6位）")
    mobile: Optional[str] = Field(None, max_length=100, description="手机号")
    role: SysRole = Field("user", description="系统角色（兼容字段）")
    data_role: DataRole = Field("staff", description="数据角色（问数权限主体）")
    org_code: Optional[str] = Field(None, max_length=100, description="机构代码")
    org_name: Optional[str] = Field(None, max_length=200, description="机构名称")
    dept_code: Optional[str] = Field(None, max_length=100, description="部门代码")
    dept_name: Optional[str] = Field(None, max_length=200, description="部门名称")


class UserListItem(BaseModel):
    """用户列表项（完整信息）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: Optional[str] = None
    mobile: Optional[str] = None
    role: Optional[SysRole] = None
    data_role: Optional[DataRole] = "staff"
    org_code: Optional[str] = None
    org_name: Optional[str] = None
    dept_code: Optional[str] = None
    dept_name: Optional[str] = None
    is_active: bool = True
    create_time: Optional[datetime] = None


class UserListResponse(BaseModel):
    """用户列表分页响应。"""

    items: List[UserListItem]
    total: int
    page: int
    page_size: int


class UserStatusUpdate(BaseModel):
    """用户状态更新请求。"""

    is_active: bool = Field(..., description="是否启用")
