"""用户相关的Pydantic模型（中文注释）。"""
from typing import Optional
from pydantic import BaseModel


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
    """用户对外展示模型。"""
    id: int
    userName: Optional[str] = None
    mobile: Optional[str] = None

    class Config:
        from_attributes = True
