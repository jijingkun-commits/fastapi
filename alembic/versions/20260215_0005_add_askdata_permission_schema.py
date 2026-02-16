"""补齐问数权限表与用户权限字段。

Revision ID: 20260215_0005
Revises: 20260213_0004
Create Date: 2026-02-15
"""

from __future__ import annotations

from typing import Iterable

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260215_0005"
down_revision = "20260213_0004"
branch_labels = None
depends_on = None


def _get_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_unique(table_name: str, columns: Iterable[str]) -> bool:
    inspector = sa.inspect(op.get_bind())
    expected = list(columns)
    for unique in inspector.get_unique_constraints(table_name):
        unique_columns = unique.get("column_names") or []
        if unique_columns == expected:
            return True
    return False


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def _ensure_user_permission_columns() -> None:
    """确保 t_user 包含问数权限字段。"""

    columns = _get_columns("t_user")
    if not columns:
        return

    if "role" not in columns:
        op.add_column(
            "t_user",
            sa.Column(
                "role",
                sa.String(length=50),
                nullable=True,
                server_default=sa.text("'user'"),
                comment="用户角色: admin/analyst/user",
            ),
        )

    if "org_code" not in columns:
        op.add_column(
            "t_user",
            sa.Column("org_code", sa.String(length=100), nullable=True, comment="机构代码"),
        )

    if "org_name" not in columns:
        op.add_column(
            "t_user",
            sa.Column("org_name", sa.String(length=200), nullable=True, comment="机构名称"),
        )

    if "dept_code" not in columns:
        op.add_column(
            "t_user",
            sa.Column("dept_code", sa.String(length=100), nullable=True, comment="部门代码"),
        )

    if "dept_name" not in columns:
        op.add_column(
            "t_user",
            sa.Column("dept_name", sa.String(length=200), nullable=True, comment="部门名称"),
        )

    op.execute("ALTER TABLE t_user ALTER COLUMN role SET DEFAULT 'user'")
    op.execute("UPDATE t_user SET role = 'user' WHERE role IS NULL")


def _ensure_permission_table_structures() -> None:
    """创建问数权限三张配置表，并补齐约束与索引。"""

    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    if "t_data_permission_table" not in existing_tables:
        op.create_table(
            "t_data_permission_table",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("role", sa.String(length=50), nullable=False, comment="用户角色"),
            sa.Column("schema_name", sa.String(length=100), nullable=False, comment="Schema 名称"),
            sa.Column("table_name", sa.String(length=100), nullable=False, comment="表名，支持 * 通配符"),
            sa.Column(
                "allow_access",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
                comment="是否允许访问",
            ),
            sa.Column("description", sa.Text(), nullable=True, comment="描述"),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="更新时间"),
            sa.UniqueConstraint("role", "schema_name", "table_name", name="uq_perm_table_role_schema_table"),
            comment="表级权限配置：控制角色能访问哪些表",
        )

    table_columns = _get_columns("t_data_permission_table")
    if "description" not in table_columns:
        op.add_column("t_data_permission_table", sa.Column("description", sa.Text(), nullable=True, comment="描述"))
    if "created_at" not in table_columns:
        op.add_column(
            "t_data_permission_table",
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="创建时间"),
        )
    if "updated_at" not in table_columns:
        op.add_column(
            "t_data_permission_table",
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="更新时间"),
        )

    if not _has_unique("t_data_permission_table", ("role", "schema_name", "table_name")):
        op.create_unique_constraint(
            "uq_perm_table_role_schema_table",
            "t_data_permission_table",
            ["role", "schema_name", "table_name"],
        )
    if not _has_index("t_data_permission_table", "idx_perm_table_role"):
        op.create_index("idx_perm_table_role", "t_data_permission_table", ["role"], unique=False)

    if "t_data_permission_row" not in existing_tables:
        op.create_table(
            "t_data_permission_row",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("role", sa.String(length=50), nullable=True, comment="用户角色，NULL 表示所有角色"),
            sa.Column("schema_name", sa.String(length=100), nullable=False, comment="Schema 名称"),
            sa.Column("table_name", sa.String(length=100), nullable=False, comment="表名，支持 * 通配符"),
            sa.Column("filter_column", sa.String(length=100), nullable=False, comment="过滤字段名"),
            sa.Column(
                "filter_source",
                sa.String(length=50),
                nullable=False,
                comment="值来源: user.org_code / user.dept_code / fixed",
            ),
            sa.Column("filter_value", sa.String(length=200), nullable=True, comment="固定过滤值（source=fixed 时使用）"),
            sa.Column(
                "filter_operator",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'='"),
                comment="比较运算符",
            ),
            sa.Column("description", sa.Text(), nullable=True, comment="描述"),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="更新时间"),
            sa.UniqueConstraint(
                "role",
                "schema_name",
                "table_name",
                "filter_column",
                name="uq_perm_row_role_schema_table_column",
            ),
            comment="行级权限规则：控制用户能看到哪些行（RLS）",
        )

    row_columns = _get_columns("t_data_permission_row")
    if "filter_operator" not in row_columns:
        op.add_column(
            "t_data_permission_row",
            sa.Column(
                "filter_operator",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'='"),
                comment="比较运算符",
            ),
        )
    if "description" not in row_columns:
        op.add_column("t_data_permission_row", sa.Column("description", sa.Text(), nullable=True, comment="描述"))
    if "created_at" not in row_columns:
        op.add_column(
            "t_data_permission_row",
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="创建时间"),
        )
    if "updated_at" not in row_columns:
        op.add_column(
            "t_data_permission_row",
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="更新时间"),
        )

    if not _has_unique("t_data_permission_row", ("role", "schema_name", "table_name", "filter_column")):
        op.create_unique_constraint(
            "uq_perm_row_role_schema_table_column",
            "t_data_permission_row",
            ["role", "schema_name", "table_name", "filter_column"],
        )
    if not _has_index("t_data_permission_row", "idx_perm_row_role"):
        op.create_index("idx_perm_row_role", "t_data_permission_row", ["role"], unique=False)

    if "t_data_permission_column" not in existing_tables:
        op.create_table(
            "t_data_permission_column",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("role", sa.String(length=50), nullable=False, comment="用户角色"),
            sa.Column("schema_name", sa.String(length=100), nullable=False, comment="Schema 名称"),
            sa.Column("table_name", sa.String(length=100), nullable=False, comment="表名"),
            sa.Column("column_name", sa.String(length=100), nullable=False, comment="字段名"),
            sa.Column("mask_type", sa.String(length=50), nullable=False, comment="脱敏类型: hide/partial/hash"),
            sa.Column("mask_pattern", sa.String(length=200), nullable=True, comment="脱敏显示模式"),
            sa.Column("description", sa.Text(), nullable=True, comment="描述"),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="更新时间"),
            sa.UniqueConstraint(
                "role",
                "schema_name",
                "table_name",
                "column_name",
                name="uq_perm_column_role_schema_table_column",
            ),
            comment="列级权限配置：敏感字段脱敏规则",
        )

    column_columns = _get_columns("t_data_permission_column")
    if "description" not in column_columns:
        op.add_column("t_data_permission_column", sa.Column("description", sa.Text(), nullable=True, comment="描述"))
    if "created_at" not in column_columns:
        op.add_column(
            "t_data_permission_column",
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="创建时间"),
        )
    if "updated_at" not in column_columns:
        op.add_column(
            "t_data_permission_column",
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()"), comment="更新时间"),
        )

    if not _has_unique("t_data_permission_column", ("role", "schema_name", "table_name", "column_name")):
        op.create_unique_constraint(
            "uq_perm_column_role_schema_table_column",
            "t_data_permission_column",
            ["role", "schema_name", "table_name", "column_name"],
        )
    if not _has_index("t_data_permission_column", "idx_perm_column_role"):
        op.create_index("idx_perm_column_role", "t_data_permission_column", ["role"], unique=False)


def _seed_default_permissions() -> None:
    """初始化默认问数权限规则（幂等）。"""

    statements = [
        """
        INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
        SELECT 'admin', 'fdmdata', '*', true, '管理员可访问 fdmdata 全部表'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_table
            WHERE role = 'admin' AND schema_name = 'fdmdata' AND table_name = '*'
        )
        """,
        """
        INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
        SELECT 'admin', 'sdmdata', '*', true, '管理员可访问 sdmdata 全部表'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_table
            WHERE role = 'admin' AND schema_name = 'sdmdata' AND table_name = '*'
        )
        """,
        """
        INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
        SELECT 'analyst', 'fdmdata', '*', true, '分析师可访问 fdmdata 全部表'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_table
            WHERE role = 'analyst' AND schema_name = 'fdmdata' AND table_name = '*'
        )
        """,
        """
        INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
        SELECT 'analyst', 'sdmdata', '*', true, '分析师可访问 sdmdata 全部表'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_table
            WHERE role = 'analyst' AND schema_name = 'sdmdata' AND table_name = '*'
        )
        """,
        """
        INSERT INTO t_data_permission_row (
            role,
            schema_name,
            table_name,
            filter_column,
            filter_source,
            filter_operator,
            description
        )
        SELECT 'analyst', 'fdmdata', '*', 'org_code', 'user.org_code', '=', '分析师只能查看本机构数据'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_row
            WHERE role = 'analyst'
              AND schema_name = 'fdmdata'
              AND table_name = '*'
              AND filter_column = 'org_code'
        )
        """,
        """
        INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
        SELECT 'user', 'fdmdata', 'f_mid_deposit_%', true, '普通用户仅可访问存款相关表'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_table
            WHERE role = 'user' AND schema_name = 'fdmdata' AND table_name = 'f_mid_deposit_%'
        )
        """,
        """
        INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
        SELECT 'user', 'sdmdata', '*', true, '普通用户可访问维度表'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_table
            WHERE role = 'user' AND schema_name = 'sdmdata' AND table_name = '*'
        )
        """,
        """
        INSERT INTO t_data_permission_row (
            role,
            schema_name,
            table_name,
            filter_column,
            filter_source,
            filter_operator,
            description
        )
        SELECT 'user', 'fdmdata', '*', 'org_code', 'user.org_code', '=', '普通用户只能查看本机构数据'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_row
            WHERE role = 'user'
              AND schema_name = 'fdmdata'
              AND table_name = '*'
              AND filter_column = 'org_code'
        )
        """,
        """
        INSERT INTO t_data_permission_column (
            role,
            schema_name,
            table_name,
            column_name,
            mask_type,
            mask_pattern,
            description
        )
        SELECT 'analyst', 'fdmdata', '*', 'mobile', 'partial', '***####****', '手机号部分脱敏'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_column
            WHERE role = 'analyst'
              AND schema_name = 'fdmdata'
              AND table_name = '*'
              AND column_name = 'mobile'
        )
        """,
        """
        INSERT INTO t_data_permission_column (
            role,
            schema_name,
            table_name,
            column_name,
            mask_type,
            description
        )
        SELECT 'user', 'fdmdata', '*', 'id_card', 'hide', '身份证号完全隐藏'
        WHERE NOT EXISTS (
            SELECT 1 FROM t_data_permission_column
            WHERE role = 'user'
              AND schema_name = 'fdmdata'
              AND table_name = '*'
              AND column_name = 'id_card'
        )
        """,
    ]

    for statement in statements:
        op.execute(sa.text(statement))


def upgrade() -> None:
    """升级：补齐问数权限相关结构。"""

    _ensure_user_permission_columns()
    _ensure_permission_table_structures()
    _seed_default_permissions()


def downgrade() -> None:
    """降级：删除问数权限配置表（保留 t_user 字段，避免破坏历史数据）。"""

    op.execute("DROP TABLE IF EXISTS t_data_permission_column")
    op.execute("DROP TABLE IF EXISTS t_data_permission_row")
    op.execute("DROP TABLE IF EXISTS t_data_permission_table")

