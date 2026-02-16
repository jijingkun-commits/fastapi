"""问数权限控制模型（中文注释）。

包含三层权限控制：
- 表级权限：控制角色能访问哪些表
- 行级权限（RLS）：控制用户能看到哪些行
- 列级权限：敏感字段脱敏规则
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DataPermissionTable(Base):
    """表级权限配置。
    
    控制不同角色能访问哪些 Schema 和表。
    table_name 支持通配符 * 表示全部表。
    """
    __tablename__ = "t_data_permission_table"

    __table_args__ = (
        UniqueConstraint("role", "schema_name", "table_name", name="uq_perm_table_role_schema_table"),
        Index("idx_perm_table_role", "role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户角色")
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Schema 名称")
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="表名，支持 * 通配符")
    allow_access: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否允许访问")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, comment="更新时间")


class DataPermissionRow(Base):
    """行级权限规则（RLS）。
    
    控制用户只能看到符合条件的行，如机构隔离。
    filter_source 指定过滤值来源：
    - user.org_code：使用用户的机构代码
    - user.dept_code：使用用户的部门代码
    - fixed：使用固定值
    """
    __tablename__ = "t_data_permission_row"

    __table_args__ = (
        UniqueConstraint("role", "schema_name", "table_name", "filter_column", name="uq_perm_row_role_schema_table_column"),
        Index("idx_perm_row_role", "role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[Optional[str]] = mapped_column(String(50), comment="用户角色，NULL 表示所有角色")
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Schema 名称")
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="表名，支持 * 通配符")
    filter_column: Mapped[str] = mapped_column(String(100), nullable=False, comment="过滤字段名")
    filter_source: Mapped[str] = mapped_column(String(50), nullable=False, comment="值来源: user.org_code / user.dept_code / fixed")
    filter_value: Mapped[Optional[str]] = mapped_column(String(200), comment="固定过滤值（source=fixed 时使用）")
    filter_operator: Mapped[str] = mapped_column(String(20), default="=", comment="比较运算符")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, comment="更新时间")


class DataPermissionColumn(Base):
    """列级权限配置（字段脱敏）。
    
    控制敏感字段的显示方式。
    mask_type 脱敏类型：
    - hide：完全隐藏，返回 ***
    - partial：部分脱敏，如 138****1234
    - hash：哈希处理，返回 MD5 前8位
    """
    __tablename__ = "t_data_permission_column"

    __table_args__ = (
        UniqueConstraint("role", "schema_name", "table_name", "column_name", name="uq_perm_column_role_schema_table_column"),
        Index("idx_perm_column_role", "role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户角色")
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Schema 名称")
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="表名")
    column_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="字段名")
    mask_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="脱敏类型: hide/partial/hash")
    mask_pattern: Mapped[Optional[str]] = mapped_column(String(200), comment="脱敏显示模式")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="描述")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, comment="更新时间")
