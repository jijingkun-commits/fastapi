-- 增量脚本 027：为 head_president 补齐表级权限并修正行级过滤源
-- 背景：head_president 从未配置过表级权限，且行级规则使用 user.dept_code，
--       导致无 dept_code 的总行行长用户无法通过 validate_query_context 校验。
-- 修复：补齐表级权限，行级规则改用 user.org_code（总行行长按机构口径过滤）。

BEGIN;

-- 1) 表级权限：允许 head_president 访问 fdmdata 和 sdmdata 全部表
INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
VALUES ('head_president', 'fdmdata', '*', true, '总行行长可访问 fdmdata 全部表')
ON CONFLICT (role, schema_name, table_name) DO NOTHING;

INSERT INTO t_data_permission_table (role, schema_name, table_name, allow_access, description)
VALUES ('head_president', 'sdmdata', '*', true, '总行行长可访问 sdmdata 全部表')
ON CONFLICT (role, schema_name, table_name) DO NOTHING;

-- 2) 修正 schema 通配行级规则：head_president 改用 org_code 口径
UPDATE t_data_permission_row
SET
    filter_column = 'org_code',
    filter_source = 'user.org_code',
    description = '机构范围（总行行长按机构口径过滤）',
    updated_at = NOW()
WHERE role = 'head_president'
  AND schema_name = 'fdmdata'
  AND table_name = '*';

-- 若 schema 通配规则不存在（026 的 UPDATE 未命中），则插入
INSERT INTO t_data_permission_row (role, schema_name, table_name, filter_column, filter_source, filter_operator, description)
VALUES ('head_president', 'fdmdata', '*', 'org_code', 'user.org_code', '=', '机构范围（总行行长按机构口径过滤）')
ON CONFLICT (role, schema_name, table_name, filter_column) DO NOTHING;

-- 3) 修正精确表行级规则：head_president 改用 user.org_code 来源
UPDATE t_data_permission_row
SET
    filter_source = 'user.org_code',
    description = '机构范围（精确规则，总行行长按机构口径）',
    updated_at = NOW()
WHERE role = 'head_president'
  AND schema_name = 'fdmdata'
  AND table_name IN ('f_mid_dep_tb', 'f_mid_index_result', 'f_mid_index_result_derive',
                     'f_mid_index_result_dim', 'f_mid_index_result_dim_derive',
                     'f_mid_org_tree', 'f_mid_mms_sxyxh');

-- 4) 存量 admin 用户数据修补
UPDATE t_user
SET data_role = 'head_president',
    org_code = '0000',
    org_name = '总行'
WHERE username = 'admin'
  AND (data_role IS NULL OR data_role = 'staff');

COMMIT;
