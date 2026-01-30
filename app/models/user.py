"""用户模型，对应表 t_user（中文注释）。

数据库字段已统一为小写格式（username, create_time, update_time）。
支持问数权限控制的角色、机构、部门字段。
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "t_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(
        String(200), comment="用户名称"
    )
    password: Mapped[Optional[str]] = mapped_column(String(300), comment="密码")
    mobile: Mapped[Optional[str]] = mapped_column(String(100), comment="手机号")
    
    # 问数权限控制字段
    role: Mapped[Optional[str]] = mapped_column(
        String(50), default="user", comment="用户角色: admin/analyst/user"
    )
    org_code: Mapped[Optional[str]] = mapped_column(
        String(100), comment="机构代码"
    )
    org_name: Mapped[Optional[str]] = mapped_column(
        String(200), comment="机构名称"
    )
    dept_code: Mapped[Optional[str]] = mapped_column(
        String(100), comment="部门代码"
    )
    dept_name: Mapped[Optional[str]] = mapped_column(
        String(200), comment="部门名称"
    )
    
    create_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="创建时间"
    )
    update_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="修改时间"
    )
