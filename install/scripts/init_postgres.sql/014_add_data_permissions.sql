-- 014_add_data_permissions.sql
-- 问数权限控制表结构
-- 支持表级、行级（RLS）、列级权限控制

-- ============================================================
-- 1. 扩展用户表：添加角色、机构、部门字段
-- ============================================================
ALTER TABLE t_user ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';
ALTER TABLE t_user ADD COLUMN IF NOT EXISTS org_code VARCHAR(100);
ALTER TABLE t_user ADD COLUMN IF NOT EXISTS org_name VARCHAR(200);
ALTER TABLE t_user ADD COLUMN IF NOT EXISTS dept_code VARCHAR(100);
ALTER TABLE t_user ADD COLUMN IF NOT EXISTS dept_name VARCHAR(200);

COMMENT ON COLUMN t_user.role IS '用户角色: admin/analyst/user';
COMMENT ON COLUMN t_user.org_code IS '机构代码';
COMMENT ON COLUMN t_user.org_name IS '机构名称';
COMMENT ON COLUMN t_user.dept_code IS '部门代码';
COMMENT ON COLUMN t_user.dept_name IS '部门名称';

-- ============================================================
-- 2. 表级权限配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS t_data_permission_table (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    schema_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,      -- 支持通配符 * 
    allow_access BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(role, schema_name, table_name)
);

COMMENT ON TABLE t_data_permission_table IS '表级权限配置：控制角色能访问哪些表';
COMMENT ON COLUMN t_data_permission_table.role IS '用户角色';
COMMENT ON COLUMN t_data_permission_table.schema_name IS 'Schema 名称';
COMMENT ON COLUMN t_data_permission_table.table_name IS '表名，支持 * 通配符';
COMMENT ON COLUMN t_data_permission_table.allow_access IS '是否允许访问';

-- ============================================================
-- 3. 行级权限规则表（RLS）
-- ============================================================
CREATE TABLE IF NOT EXISTS t_data_permission_row (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50),                       -- NULL 表示对所有角色生效
    schema_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,       -- 支持通配符 *
    filter_column VARCHAR(100) NOT NULL,    -- 过滤字段，如 org_code
    filter_source VARCHAR(50) NOT NULL,     -- 值来源: user.org_code / user.dept_code / fixed
    filter_value VARCHAR(200),              -- 固定值（filter_source=fixed 时使用）
    filter_operator VARCHAR(20) DEFAULT '=', -- 比较运算符: = / IN / LIKE
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(role, schema_name, table_name, filter_column)
);

COMMENT ON TABLE t_data_permission_row IS '行级权限规则：控制用户能看到哪些行（RLS）';
COMMENT ON COLUMN t_data_permission_row.role IS '用户角色，NULL 表示所有角色';
COMMENT ON COLUMN t_data_permission_row.filter_column IS '用于过滤的字段名';
COMMENT ON COLUMN t_data_permission_row.filter_source IS '过滤值来源: user.org_code / user.dept_code / fixed';
COMMENT ON COLUMN t_data_permission_row.filter_value IS '固定过滤值（source=fixed 时使用）';
COMMENT ON COLUMN t_data_permission_row.filter_operator IS '比较运算符';

-- ============================================================
-- 4. 列级权限配置表（字段脱敏）
-- ============================================================
CREATE TABLE IF NOT EXISTS t_data_permission_column (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    schema_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    mask_type VARCHAR(50) NOT NULL,         -- 脱敏类型: hide / partial / hash
    mask_pattern VARCHAR(200),              -- 脱敏模式（如 partial 时的显示格式）
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(role, schema_name, table_name, column_name)
);

COMMENT ON TABLE t_data_permission_column IS '列级权限配置：敏感字段脱敏规则';
COMMENT ON COLUMN t_data_permission_column.mask_type IS '脱敏类型: hide=隐藏 / partial=部分显示 / hash=哈希';
COMMENT ON COLUMN t_data_permission_column.mask_pattern IS '脱敏显示模式，如手机号 138****1234';

-- ============================================================
-- 5. 插入默认配置
-- ============================================================

-- admin 角色：全部权限
INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
VALUES ('admin', 'fdmdata', '*', true, '管理员可访问 fdmdata 全部表')
ON CONFLICT (role, schema_name, table_name) DO NOTHING;

INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
VALUES ('admin', 'sdmdata', '*', true, '管理员可访问 sdmdata 全部表')
ON CONFLICT (role, schema_name, table_name) DO NOTHING;

-- analyst 角色：可访问全部业务表，但需要机构过滤
INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
VALUES ('analyst', 'fdmdata', '*', true, '分析师可访问 fdmdata 全部表')
ON CONFLICT (role, schema_name, table_name) DO NOTHING;

INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
VALUES ('analyst', 'sdmdata', '*', true, '分析师可访问 sdmdata 全部表')
ON CONFLICT (role, schema_name, table_name) DO NOTHING;

-- analyst 角色的行级过滤（机构隔离）
INSERT INTO t_data_permission_row (role, schema_name, table_name, filter_column, filter_source, description)
VALUES ('analyst', 'fdmdata', '*', 'org_code', 'user.org_code', '分析师只能查看本机构数据')
ON CONFLICT (role, schema_name, table_name, filter_column) DO NOTHING;

-- user 角色：仅可访问部分表
INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
VALUES ('user', 'fdmdata', 'f_mid_deposit_%', true, '普通用户仅可访问存款相关表')
ON CONFLICT (role, schema_name, table_name) DO NOTHING;

INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
VALUES ('user', 'sdmdata', '*', true, '普通用户可访问维度表')
ON CONFLICT (role, schema_name, table_name) DO NOTHING;

-- user 角色的行级过滤
INSERT INTO t_data_permission_row (role, schema_name, table_name, filter_column, filter_source, description)
VALUES ('user', 'fdmdata', '*', 'org_code', 'user.org_code', '普通用户只能查看本机构数据')
ON CONFLICT (role, schema_name, table_name, filter_column) DO NOTHING;

-- 列级脱敏示例（analyst 角色手机号部分脱敏）
INSERT INTO t_data_permission_column (role, schema_name, table_name, column_name, mask_type, mask_pattern, description)
VALUES ('analyst', 'fdmdata', '*', 'mobile', 'partial', '***####****', '手机号部分脱敏')
ON CONFLICT (role, schema_name, table_name, column_name) DO NOTHING;

INSERT INTO t_data_permission_column (role, schema_name, table_name, column_name, mask_type, description)
VALUES ('user', 'fdmdata', '*', 'id_card', 'hide', '身份证号完全隐藏')
ON CONFLICT (role, schema_name, table_name, column_name) DO NOTHING;

-- ============================================================
-- 6. 创建索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_perm_table_role ON t_data_permission_table(role);
CREATE INDEX IF NOT EXISTS idx_perm_row_role ON t_data_permission_row(role);
CREATE INDEX IF NOT EXISTS idx_perm_column_role ON t_data_permission_column(role);
