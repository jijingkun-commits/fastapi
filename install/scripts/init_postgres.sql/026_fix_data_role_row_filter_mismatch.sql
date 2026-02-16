-- 增量脚本 026：修复 data_role 行级规则与 fdmdata 表字段不匹配
-- 背景：schema.* 使用 dept_cd 规则时，部分核心表仅包含 org_no/org_code，导致 SQL 注入不存在列报错

BEGIN;

-- 1) 保持 schema.* 通配规则为部门口径（与既有策略保持一致）
UPDATE t_data_permission_row
SET
    filter_column = 'dept_cd',
    filter_source = 'user.dept_code',
    filter_operator = '=',
    description = '部门范围（schema 通配规则）'
WHERE role IN ('head_president', 'department_gm', 'department_vgm', 'staff')
  AND schema_name = 'fdmdata'
  AND table_name = '*';

-- 2) 为不含 dept_cd 的核心表补充精确规则（org_no / org_code）
WITH role_scope(role_name) AS (
    VALUES
        ('head_president'),
        ('department_gm'),
        ('department_vgm'),
        ('staff')
),
table_scope(table_name, filter_column) AS (
    VALUES
        ('f_mid_dep_tb', 'org_no'),
        ('f_mid_index_result', 'org_no'),
        ('f_mid_index_result_derive', 'org_no'),
        ('f_mid_index_result_dim', 'org_no'),
        ('f_mid_index_result_dim_derive', 'org_no'),
        ('f_mid_org_tree', 'org_no'),
        ('f_mid_mms_sxyxh', 'org_code')
)
INSERT INTO t_data_permission_row (
    role,
    schema_name,
    table_name,
    filter_column,
    filter_source,
    filter_operator,
    description
)
SELECT
    r.role_name,
    'fdmdata',
    t.table_name,
    t.filter_column,
    'user.dept_code',
    '=',
    '机构范围（精确规则，覆盖 schema 通配）'
FROM role_scope r
CROSS JOIN table_scope t
ON CONFLICT (role, schema_name, table_name, filter_column)
DO UPDATE SET
    filter_source = EXCLUDED.filter_source,
    filter_operator = EXCLUDED.filter_operator,
    description = EXCLUDED.description,
    updated_at = NOW();

COMMIT;

