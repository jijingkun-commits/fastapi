-- 增量脚本 028：限制 staff 角色访问贷款明细表
-- 背景：staff 当前通过 fdmdata.* 通配规则可访问贷款明细表，不符合业务口径。
-- 策略：对目标贷款表增加精确 deny 规则，优先级高于 schema 通配 allow。

BEGIN;

INSERT INTO t_data_permission_table (
    role,
    schema_name,
    table_name,
    allow_access,
    description
)
VALUES (
    'staff',
    'fdmdata',
    'f_mid_loan_k_tb',
    false,
    'staff 禁止访问贷款明细表（客户维度）'
)
ON CONFLICT (role, schema_name, table_name)
DO UPDATE SET
    allow_access = EXCLUDED.allow_access,
    description = EXCLUDED.description,
    updated_at = NOW();

INSERT INTO t_data_permission_table (
    role,
    schema_name,
    table_name,
    allow_access,
    description
)
VALUES (
    'staff',
    'fdmdata',
    'f_mid_loan_tb',
    false,
    'staff 禁止访问贷款明细表（机构维度）'
)
ON CONFLICT (role, schema_name, table_name)
DO UPDATE SET
    allow_access = EXCLUDED.allow_access,
    description = EXCLUDED.description,
    updated_at = NOW();

COMMIT;
