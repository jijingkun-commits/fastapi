-- 016_expand_metrics.sql
-- 扩展指标定义，基于现有业务表 f_mid_dep_tb / f_mid_loan_tb

-- ============================================================
-- 存款类指标扩展
-- ============================================================

-- 活期存款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('DEP_003', '活期存款余额', '活期余额,活期存款', '统计期末全行活期类存款的账面余额合计。',
    'SELECT SUM(acct_bal) as 活期存款余额 FROM fdmdata.f_mid_dep_tb WHERE fix_cur_ind = ''0'' AND data_dt = ''${data_dt}''',
    '存款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 存款户数
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('DEP_004', '存款户数', '存款账户数,储蓄户数', '统计期末存款账户总数（按账号去重）。',
    'SELECT COUNT(DISTINCT dep_acct_no) as 存款户数 FROM fdmdata.f_mid_dep_tb WHERE data_dt = ''${data_dt}''',
    '存款', '户', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 日均存款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('DEP_005', '日均存款余额', '日均存款,平均存款', '统计期末全行存款的日均余额（使用 std_y_avg_bal 字段）。',
    'SELECT SUM(std_y_avg_bal) as 日均存款余额 FROM fdmdata.f_mid_dep_tb WHERE data_dt = ''${data_dt}''',
    '存款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 分机构存款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('DEP_006', '分机构存款余额', '各机构存款,分行存款', '按机构统计存款余额分布。',
    'SELECT org_no as 机构代码, level7_val as 机构名称, SUM(acct_bal) as 存款余额 FROM fdmdata.f_mid_dep_tb WHERE data_dt = ''${data_dt}'' GROUP BY org_no, level7_val ORDER BY 存款余额 DESC',
    '存款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 对公存款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('DEP_007', '对公存款余额', '公司存款,企业存款', '统计期末对公客户存款余额（cust_type_cd 为对公类型）。',
    'SELECT SUM(acct_bal) as 对公存款余额 FROM fdmdata.f_mid_dep_tb WHERE cust_type_cd = ''2'' AND data_dt = ''${data_dt}''',
    '存款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 个人存款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('DEP_008', '个人存款余额', '零售存款,私人存款', '统计期末个人客户存款余额（cust_type_cd 为个人类型）。',
    'SELECT SUM(acct_bal) as 个人存款余额 FROM fdmdata.f_mid_dep_tb WHERE cust_type_cd = ''1'' AND data_dt = ''${data_dt}''',
    '存款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- ============================================================
-- 贷款类指标扩展
-- ============================================================

-- 正常贷款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('LOAN_003', '正常贷款余额', '正常类贷款,一类贷款', '统计期末五级分类为正常的贷款本金余额。',
    'SELECT SUM(prin_bal) as 正常贷款余额 FROM fdmdata.f_mid_loan_tb WHERE five_class_cd = ''1'' AND data_dt = ''${data_dt}''',
    '贷款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 关注类贷款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('LOAN_004', '关注类贷款余额', '关注贷款,二类贷款', '统计期末五级分类为关注的贷款本金余额。',
    'SELECT SUM(prin_bal) as 关注类贷款余额 FROM fdmdata.f_mid_loan_tb WHERE five_class_cd = ''2'' AND data_dt = ''${data_dt}''',
    '贷款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 逾期贷款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('LOAN_005', '逾期贷款余额', '逾期贷款,过期贷款', '统计期末本金逾期天数大于0的贷款余额。',
    'SELECT SUM(prin_bal) as 逾期贷款余额 FROM fdmdata.f_mid_loan_tb WHERE prin_ovrd_days > 0 AND data_dt = ''${data_dt}''',
    '贷款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 贷款户数
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('LOAN_006', '贷款户数', '贷款账户数,信贷户数', '统计期末贷款账户总数（按借据号去重）。',
    'SELECT COUNT(DISTINCT duebill_no) as 贷款户数 FROM fdmdata.f_mid_loan_tb WHERE data_dt = ''${data_dt}''',
    '贷款', '户', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 分机构贷款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('LOAN_007', '分机构贷款余额', '各机构贷款,分行贷款', '按机构统计贷款余额分布。',
    'SELECT org_cd as 机构代码, level7_val as 机构名称, SUM(prin_bal) as 贷款余额 FROM fdmdata.f_mid_loan_tb WHERE data_dt = ''${data_dt}'' GROUP BY org_cd, level7_val ORDER BY 贷款余额 DESC',
    '贷款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 分行业贷款余额
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('LOAN_008', '分行业贷款余额', '行业贷款,行业分布', '按行业统计贷款余额分布。',
    'SELECT indu_type_cd as 行业代码, SUM(prin_bal) as 贷款余额 FROM fdmdata.f_mid_loan_tb WHERE data_dt = ''${data_dt}'' AND indu_type_cd IS NOT NULL GROUP BY indu_type_cd ORDER BY 贷款余额 DESC',
    '贷款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 不良贷款率
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('LOAN_009', '不良贷款率', '不良率,NPL比率', '不良贷款余额占贷款总额的比例。',
    'SELECT ROUND(SUM(CASE WHEN five_class_cd IN (''3'', ''4'', ''5'') THEN prin_bal ELSE 0 END) * 100.0 / NULLIF(SUM(prin_bal), 0), 2) as 不良贷款率 FROM fdmdata.f_mid_loan_tb WHERE data_dt = ''${data_dt}''',
    '贷款', '%', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- 利息收入
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('LOAN_010', '利息收入', '贷款利息,利息', '统计期末应收利息总额。',
    'SELECT SUM(int_amt2) as 利息收入 FROM fdmdata.f_mid_loan_tb WHERE data_dt = ''${data_dt}''',
    '贷款', '元', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();

-- ============================================================
-- 综合类指标
-- ============================================================

-- 存贷比
INSERT INTO t_metric_definition (metric_id, metric_name, aliases, description, sql_template, category, unit, is_active)
VALUES ('COMP_001', '存贷比', '贷存比', '贷款余额与存款余额的比例。',
    'SELECT ROUND((SELECT SUM(prin_bal) FROM fdmdata.f_mid_loan_tb WHERE data_dt = ''${data_dt}'') * 100.0 / NULLIF((SELECT SUM(acct_bal) FROM fdmdata.f_mid_dep_tb WHERE data_dt = ''${data_dt}''), 0), 2) as 存贷比',
    '综合', '%', true)
ON CONFLICT (metric_id) DO UPDATE SET 
    metric_name = EXCLUDED.metric_name,
    sql_template = EXCLUDED.sql_template,
    updated_at = NOW();
