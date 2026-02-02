-- ============================================================
-- 业务表 DDL（按覆盖度优先级排序）
-- 共 65 张表
-- 生成时间: 2026-01-30
-- ============================================================

-- f_mid_index_result
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_index_result (
    data_dt VARCHAR(20),
    org_no VARCHAR(20),
    org_no_map VARCHAR(50),
    ccy VARCHAR(10),
    index_code VARCHAR(20),
    index_name VARCHAR(100),
    index_value NUMERIC(38,8),
    month_to_date NUMERIC(38,8),
    quarter_to_date NUMERIC(38,8),
    year_to_date NUMERIC(38,8),
    bus_dim_1 VARCHAR(50),
    bus_dim_2 VARCHAR(50),
    bus_dim_3 VARCHAR(50),
    bus_dim_4 VARCHAR(50),
    bus_dim_5 VARCHAR(50),
    bus_dim_6 VARCHAR(50),
    bus_dim_7 VARCHAR(50),
    bus_dim_8 VARCHAR(50),
    bus_dim_9 VARCHAR(50),
    bus_dim_10 VARCHAR(50),
    bus_dim_11 VARCHAR(50),
    bus_dim_12 VARCHAR(50),
    bus_dim_13 VARCHAR(50),
    bus_dim_14 VARCHAR(50),
    bus_dim_15 VARCHAR(50),
    bus_dim_exp VARCHAR(200),
    group_sign VARCHAR(10),
    ztetl_dt VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_index_result.data_dt IS '业务日期';
COMMENT ON COLUMN fdmdata.f_mid_index_result.org_no IS '机构';
COMMENT ON COLUMN fdmdata.f_mid_index_result.org_no_map IS '机构名称';
COMMENT ON COLUMN fdmdata.f_mid_index_result.ccy IS '币种';
COMMENT ON COLUMN fdmdata.f_mid_index_result.index_code IS '指标编码';
COMMENT ON COLUMN fdmdata.f_mid_index_result.index_name IS '指标名称';
COMMENT ON COLUMN fdmdata.f_mid_index_result.index_value IS '指标值';
COMMENT ON COLUMN fdmdata.f_mid_index_result.month_to_date IS '月累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result.quarter_to_date IS '季累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result.year_to_date IS '年累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_1 IS '业务维度1';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_2 IS '业务维度2';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_3 IS '业务维度3';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_4 IS '业务维度4';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_5 IS '业务维度5';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_6 IS '业务维度6';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_7 IS '业务维度7';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_8 IS '业务维度8';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_9 IS '业务维度9';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_10 IS '业务维度10';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_11 IS '业务维度11';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_12 IS '业务维度12';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_13 IS '业务维度13';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_14 IS '业务维度14';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_15 IS '业务维度15';
COMMENT ON COLUMN fdmdata.f_mid_index_result.bus_dim_exp IS '业务维度组合说明';
COMMENT ON COLUMN fdmdata.f_mid_index_result.group_sign IS '汇总标志(0是1否)';
COMMENT ON COLUMN fdmdata.f_mid_index_result.ztetl_dt IS '中台ETL日期';

-- f_mid_index_result_derive
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_index_result_derive (
    data_dt VARCHAR(20),
    org_no VARCHAR(20),
    org_no_map VARCHAR(50),
    ccy VARCHAR(10),
    index_code VARCHAR(20),
    index_name VARCHAR(100),
    index_value NUMERIC(38,8),
    month_to_date NUMERIC(38,8),
    quarter_to_date NUMERIC(38,8),
    year_to_date NUMERIC(38,8),
    ztetl_dt VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.data_dt IS '业务日期';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.org_no IS '机构';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.org_no_map IS '机构名称';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.ccy IS '币种';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.index_code IS '指标编码';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.index_name IS '指标名称';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.index_value IS '指标值';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.month_to_date IS '月累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.quarter_to_date IS '季累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.year_to_date IS '年累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_derive.ztetl_dt IS '中台ETL日期';

-- f_mid_index_result_dim
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_index_result_dim (
    data_dt VARCHAR(20),
    org_no VARCHAR(20),
    org_no_map VARCHAR(50),
    ccy VARCHAR(10),
    index_code VARCHAR(20),
    index_name VARCHAR(100),
    index_value NUMERIC(38,8),
    month_to_date NUMERIC(38,8),
    quarter_to_date NUMERIC(38,8),
    year_to_date NUMERIC(38,8),
    bus_dim_1 VARCHAR(50),
    bus_dim_2 VARCHAR(50),
    bus_dim_3 VARCHAR(50),
    bus_dim_4 VARCHAR(50),
    bus_dim_5 VARCHAR(50),
    bus_dim_6 VARCHAR(50),
    bus_dim_7 VARCHAR(50),
    bus_dim_8 VARCHAR(50),
    bus_dim_9 VARCHAR(50),
    bus_dim_10 VARCHAR(50),
    bus_dim_11 VARCHAR(50),
    bus_dim_12 VARCHAR(50),
    bus_dim_13 VARCHAR(50),
    bus_dim_14 VARCHAR(50),
    bus_dim_15 VARCHAR(50),
    bus_dim_exp VARCHAR(200),
    group_sign VARCHAR(10),
    ztetl_dt VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.data_dt IS '业务日期';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.org_no IS '机构';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.org_no_map IS '机构名称';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.ccy IS '币种';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.index_code IS '指标编码';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.index_name IS '指标名称';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.index_value IS '指标值';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.month_to_date IS '月累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.quarter_to_date IS '季累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.year_to_date IS '年累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_1 IS '业务维度1';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_2 IS '业务维度2';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_3 IS '业务维度3';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_4 IS '业务维度4';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_5 IS '业务维度5';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_6 IS '业务维度6';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_7 IS '业务维度7';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_8 IS '业务维度8';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_9 IS '业务维度9';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_10 IS '业务维度10';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_11 IS '业务维度11';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_12 IS '业务维度12';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_13 IS '业务维度13';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_14 IS '业务维度14';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_15 IS '业务维度15';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.bus_dim_exp IS '业务维度组合说明';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.group_sign IS '汇总标志(0是1否)';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim.ztetl_dt IS '中台ETL日期';

-- f_mid_org_tree_k
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_org_tree_k (
    dept_cd VARCHAR(100),
    dept_name VARCHAR(100),
    org_no VARCHAR(100),
    org_val VARCHAR(100),
    org_lv VARCHAR(100)
);
COMMENT ON COLUMN fdmdata.f_mid_org_tree_k.dept_cd IS '部门机构代码';
COMMENT ON COLUMN fdmdata.f_mid_org_tree_k.dept_name IS '部门机构名称';
COMMENT ON COLUMN fdmdata.f_mid_org_tree_k.org_no IS '各级机构代码';
COMMENT ON COLUMN fdmdata.f_mid_org_tree_k.org_val IS '机构层级';

-- f_mid_loan_k_tb
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_loan_k_tb (
    data_dt DATE,
    duebill_no VARCHAR(100),
    biz_contr_no VARCHAR(100),
    dept_cd VARCHAR(20),
    dept_val VARCHAR(100),
    ccy_cd VARCHAR(40),
    ecif_cust_no VARCHAR(100),
    prod_no VARCHAR(100),
    duebill_sts_cd VARCHAR(40),
    norm_actl_y_intr NUMERIC(18,10),
    crdt_biz_cate_cd VARCHAR(40),
    rsdu_matr_days INTEGER,
    crdt_obj_class_cd VARCHAR(40),
    mod_belong VARCHAR(8),
    obs_biz_ind VARCHAR(20),
    norm_prin_subj_no VARCHAR(100),
    five_class_cd VARCHAR(40),
    prin_ovrd_days INTEGER,
    int_ovrd_days INTEGER,
    new_productmark VARCHAR(40),
    norm_prin_bal NUMERIC(40,8),
    norm_prin_y_accum NUMERIC(40,8),
    prin_bal NUMERIC(40,8),
    y_prin_wgt_accum NUMERIC(40,8),
    loan_bal_y_avg NUMERIC(40,8),
    y_tot_owe_int NUMERIC(40,8),
    int_amt2 NUMERIC(40,8),
    margin_bal NUMERIC(40,8),
    ibs_owe_int_amt NUMERIC(40,8),
    obs_owe_int_amt NUMERIC(40,8),
    titc_cust_id VARCHAR(40),
    indu_type_cd VARCHAR(40),
    holding_type_cd VARCHAR(40),
    ent_scal_cd VARCHAR(40),
    level4_cd VARCHAR(40),
    level3_cd VARCHAR(40),
    level2_cd VARCHAR(40),
    level1_cd VARCHAR(40),
    st_own_ent_ind VARCHAR(40),
    tech_corp_ind VARCHAR(40),
    ext_dt DATE,
    ext_matr_dt DATE,
    prim_guar_mode_cd VARCHAR(40),
    loan_invest_indu_cd VARCHAR(40),
    all_crdt_tot_amt NUMERIC(40,8),
    y_prin_bal_accum NUMERIC(40,8),
    cust_mgr_no VARCHAR(100),
    int_amt2_m_accum NUMERIC(40,8),
    int_amt2_q_accum NUMERIC(40,8),
    int_amt2_y_accum NUMERIC(40,8),
    legal_org_cd VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.data_dt IS '业务日期';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.duebill_no IS '借据编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.biz_contr_no IS '业务合同编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.dept_cd IS '客户经理所在部门编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.dept_val IS '客户经理所在部门名称';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.ccy_cd IS '币种';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.prod_no IS '产品编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.duebill_sts_cd IS '借据状态代码';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.norm_actl_y_intr IS '正常执行年利率';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.crdt_biz_cate_cd IS '信贷业务种类代码';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.rsdu_matr_days IS '剩余期限天数';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.crdt_obj_class_cd IS '信贷对象分类代码';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.mod_belong IS '模型归属 01-零售 02-普惠';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.obs_biz_ind IS '表外业务标志';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.norm_prin_subj_no IS '正常本金科目编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.five_class_cd IS '五级分类';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.prin_ovrd_days IS '本金逾期天数';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.int_ovrd_days IS '利息逾期天数';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.new_productmark IS '产品标识';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.norm_prin_bal IS '正常本金余额';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.norm_prin_y_accum IS '正常本金余额年积数';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.prin_bal IS '借款本金余额';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.y_prin_wgt_accum IS '本金余额年加权积数';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.loan_bal_y_avg IS '本金余额年日均';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.y_tot_owe_int IS '本年累计产生欠息';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.int_amt2 IS '当日利息收入-税后';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.margin_bal IS '保证金余额';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.ibs_owe_int_amt IS '表内欠息';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.obs_owe_int_amt IS '表外欠息';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.titc_cust_id IS '两增两控客户标志';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.indu_type_cd IS '行业类型';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.holding_type_cd IS '控股类型';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.ent_scal_cd IS '企业规模';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.level4_cd IS '产品细类';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.level3_cd IS '产品中类';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.level2_cd IS '产品粗类';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.level1_cd IS '产品大类';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.st_own_ent_ind IS '国资企业标志';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.tech_corp_ind IS '科技企业标志';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.ext_dt IS '展期起始日期';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.ext_matr_dt IS '展期到期日期';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.prim_guar_mode_cd IS '担保方式';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.loan_invest_indu_cd IS '贷款投向行业';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.all_crdt_tot_amt IS '客户授信总额';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.y_prin_bal_accum IS '本金余额年积数';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.cust_mgr_no IS '客户经理编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.int_amt2_m_accum IS '利息收入-本月累计税后';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.int_amt2_q_accum IS '利息收入-本季累计税后';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.int_amt2_y_accum IS '利息收入-本年累计税后';
COMMENT ON COLUMN fdmdata.f_mid_loan_k_tb.legal_org_cd IS '法人机构编码';

-- s_mms_dmp_pub_cust_tag_all
CREATE TABLE IF NOT EXISTS sdmdata.s_mms_dmp_pub_cust_tag_all (
    data_dt DATE,
    cust_id VARCHAR(32),
    tag_id VARCHAR(100),
    tag_val VARCHAR(1000),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_mms_dmp_pub_cust_tag_all.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_mms_dmp_pub_cust_tag_all.cust_id IS '客户号';
COMMENT ON COLUMN sdmdata.s_mms_dmp_pub_cust_tag_all.tag_id IS '标签编号';
COMMENT ON COLUMN sdmdata.s_mms_dmp_pub_cust_tag_all.tag_val IS '标签值';

-- f_mid_dep_k_tb
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_dep_k_tb (
    data_dt DATE,
    dep_acct_no VARCHAR(100),
    prin_subj_no VARCHAR(100),
    ecif_cust_no VARCHAR(100),
    prod_no VARCHAR(20),
    dept_cd VARCHAR(40),
    dept_val VARCHAR(100),
    cust_acct_no VARCHAR(100),
    cust_acct_name VARCHAR(100),
    prod_sign_intr NUMERIC(18,10),
    actl_y_intr NUMERIC(18,10),
    fix_cur_ind VARCHAR(20),
    open_dt DATE,
    dep_clct_no VARCHAR(40),
    cust_type_cd VARCHAR(40),
    acct_bal NUMERIC(40,8),
    ccy_cd VARCHAR(20),
    std_y_avg_bal NUMERIC(40,8),
    acct_y_accum NUMERIC(40,8),
    titc_cust_id VARCHAR(40),
    level1_cd VARCHAR(40),
    level2_cd VARCHAR(40),
    level3_cd VARCHAR(40),
    level4_cd VARCHAR(40),
    acct_y_wgt_accum NUMERIC(40,8),
    d_payb_int_m_accum NUMERIC(40,8),
    d_payb_int_q_accum NUMERIC(40,8),
    d_payb_int_y_accum NUMERIC(40,8),
    d_payb_int_d_accum NUMERIC(40,8),
    legal_org_cd VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.data_dt IS '业务日期';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.dep_acct_no IS '存款账户号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.prin_subj_no IS '会计科目号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.prod_no IS '产品编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.dept_cd IS '客户经理所在部门编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.dept_val IS '客户经理所在部门名称';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.cust_acct_no IS '客户账号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.cust_acct_name IS '账户名称';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.prod_sign_intr IS '签约利率';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.actl_y_intr IS '实际执行利率';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.fix_cur_ind IS '定活标志';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.open_dt IS '开户日期';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.dep_clct_no IS '员工号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.cust_type_cd IS '客户类型代码';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.acct_bal IS '账户余额';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.ccy_cd IS '币种';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.std_y_avg_bal IS '标准年日均';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.acct_y_accum IS '余额年积数';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.titc_cust_id IS '是否两增两控企业';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.level1_cd IS '产品大类编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.level2_cd IS '产品中类编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.level3_cd IS '产品粗类编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.level4_cd IS '产品细类编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.acct_y_wgt_accum IS '余额加权年积数';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.d_payb_int_m_accum IS '当日应付利息-本月累计';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.d_payb_int_q_accum IS '当日应付利息-本季累计';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.d_payb_int_y_accum IS '当日应付利息-本年累计';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.d_payb_int_d_accum IS '当日应付利息-当日';
COMMENT ON COLUMN fdmdata.f_mid_dep_k_tb.legal_org_cd IS '法人机构编码';

-- s_ods_g_b_cif_basic_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_cif_basic_info (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    ecif_cust_no VARCHAR(100),
    cust_name VARCHAR(1000),
    cust_en_name VARCHAR(1000),
    cust_type_cd VARCHAR(40),
    open_cert_type_cd VARCHAR(40),
    open_cert_no VARCHAR(100),
    corp_char_cd VARCHAR(40),
    indu_type_cd VARCHAR(40),
    cust_lvl_cd VARCHAR(40),
    crdt_lvl_cd VARCHAR(40),
    cust_cmpl_ind VARCHAR(20),
    cust_risk_capc_lvl_cd VARCHAR(40),
    cust_pd NUMERIC(18,10),
    cust_sts_cd VARCHAR(40),
    oversea_cust_ind VARCHAR(20),
    potn_cust_ind VARCHAR(20),
    rsdt_char_cd VARCHAR(40),
    supv_rsdt_ind VARCHAR(20),
    tax_rsdt_char_cd VARCHAR(40),
    tax_rsdt_nation_cd VARCHAR(40),
    taxpayer_ident_no VARCHAR(100),
    no_taxpayer_ident_no_rsn_cd VARCHAR(40),
    get_decl_doc_ind VARCHAR(20),
    bank_rel VARCHAR(400),
    bank_coop_rel_cd VARCHAR(40),
    bank_rel_pty_type_cd VARCHAR(40),
    bank_shareholder_ind VARCHAR(20),
    hold_bank_share_amt NUMERIC(38,8),
    hold_bank_share_pct NUMERIC(18,10),
    agent_open_cust_ind VARCHAR(20),
    first_crdt_dt DATE,
    buy_loan_ind VARCHAR(20),
    loan_card_ind VARCHAR(20),
    titc_cust_id VARCHAR(20),
    titc_cust_limt_amt NUMERIC(38,8),
    cust_risk_expo_ind VARCHAR(20),
    cust_risk_expo_amt NUMERIC(38,8),
    loan_card_no VARCHAR(100),
    open_dt DATE,
    open_org_cd VARCHAR(20),
    open_tlr_no VARCHAR(20),
    open_chnl_type_cd VARCHAR(40),
    close_dt DATE,
    net_verf_rslt_cd VARCHAR(40),
    org_cd VARCHAR(100),
    cust_mgr_no VARCHAR(100),
    ecif_cre_dttm VARCHAR(255),
    ecif_upd_dttm VARCHAR(255),
    cre_src_sys_cd VARCHAR(40),
    src_sys_cre_dttm VARCHAR(255),
    last_upd_dttm VARCHAR(255),
    last_upd_org_cd VARCHAR(20),
    last_upd_tlr_no VARCHAR(20),
    last_upd_sys_cd VARCHAR(40),
    etl_dt DATE,
    bel_org VARCHAR(40),
    cust_asset_lvl VARCHAR(2),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    cust_valid_state VARCHAR(10),
    indi_busi_flg VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_en_name IS '客户英文名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_type_cd IS '客户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.open_cert_type_cd IS '开户证件类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.open_cert_no IS '开户证件号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.corp_char_cd IS '单位性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.indu_type_cd IS '行业类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_lvl_cd IS '客户级别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.crdt_lvl_cd IS '信用等级代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_cmpl_ind IS '客户合规标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_risk_capc_lvl_cd IS '客户风险承受能力等级代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_pd IS '客户违约概率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_sts_cd IS '客户状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.oversea_cust_ind IS '境外客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.potn_cust_ind IS '潜在客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.rsdt_char_cd IS '居民性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.supv_rsdt_ind IS '居民标志（监管）';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.tax_rsdt_char_cd IS '税收居民性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.tax_rsdt_nation_cd IS '税收居民国家地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.taxpayer_ident_no IS '纳税人识别号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.no_taxpayer_ident_no_rsn_cd IS '未提供纳税人识别号原因代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.get_decl_doc_ind IS '取得声明文件标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.bank_rel IS '与本行关联关系';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.bank_coop_rel_cd IS '与本行合作关系代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.bank_rel_pty_type_cd IS '本行关联方类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.bank_shareholder_ind IS '本行股东标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.hold_bank_share_amt IS '持本行股份金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.hold_bank_share_pct IS '持本行股份比例';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.agent_open_cust_ind IS '代理开立客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.first_crdt_dt IS '首次建立信贷关系日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.buy_loan_ind IS '有贷户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.loan_card_ind IS '有无贷款卡标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.titc_cust_id IS '两增两控客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.titc_cust_limt_amt IS '两增两控客户额度金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_risk_expo_ind IS '客户风险暴露标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_risk_expo_amt IS '客户风险暴露金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.loan_card_no IS '贷款卡编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.open_dt IS '开户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.open_org_cd IS '开户机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.open_tlr_no IS '开户柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.open_chnl_type_cd IS '开户渠道类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.close_dt IS '销户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.net_verf_rslt_cd IS '联网核查结果代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.org_cd IS '归属机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_mgr_no IS '客户经理编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.ecif_cre_dttm IS 'ECIF创建时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.ecif_upd_dttm IS 'ECIF更新时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cre_src_sys_cd IS '创建源系统代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.src_sys_cre_dttm IS '源系统创建时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.last_upd_dttm IS '最近更新时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.last_upd_org_cd IS '最近更新机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.last_upd_tlr_no IS '最近更新柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.last_upd_sys_cd IS '最近更新系统代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.bel_org IS '管户机构';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_asset_lvl IS '客户层级';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.cust_valid_state IS '客户有效状态标识';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_basic_info.indi_busi_flg IS '个体工商户标志';

-- s_ods_g_b_dep_acct_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_dep_acct_info (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    dep_acct_no VARCHAR(100),
    cust_acct_no VARCHAR(100),
    org_no VARCHAR(20),
    ccy_cd VARCHAR(40),
    ccy_ident_cd VARCHAR(40),
    prod_no VARCHAR(100),
    prod_pd_no VARCHAR(100),
    agt_no VARCHAR(100),
    cust_acct_type_cd VARCHAR(40),
    cust_type_cd VARCHAR(40),
    ecif_cust_no VARCHAR(100),
    cust_acct_name VARCHAR(1000),
    prin_subj_no VARCHAR(40),
    payb_int_subj_no VARCHAR(40),
    int_tax_subj_no VARCHAR(100),
    wait_draw_int_subj_no VARCHAR(100),
    int_adv_subj_no VARCHAR(100),
    fix_cur_ind VARCHAR(20),
    dep_type_cd VARCHAR(40),
    acct_char_cd VARCHAR(40),
    acct_class_cd VARCHAR(40),
    corp_cur_dep_acct_attr_cd VARCHAR(40),
    interbank_dep_acct_type_cd VARCHAR(40),
    spcl_dep_type_cd VARCHAR(40),
    ife_acct_cate_cd VARCHAR(40),
    rsrv_acct_type_cd VARCHAR(40),
    fin_dep_acct_type_cd VARCHAR(40),
    cstn_acct_type_cd VARCHAR(40),
    safe_acct_char_cd VARCHAR(40),
    fta_acct_type_cd VARCHAR(40),
    fin_supv_type_cd VARCHAR(40),
    medium_type_cd VARCHAR(40),
    verf_acct_ind VARCHAR(20),
    margin_acct_ind VARCHAR(20),
    margin_purp_cd VARCHAR(40),
    chq_acct_ind VARCHAR(20),
    stl_acct_ind VARCHAR(20),
    allow_unexp_draw_ind VARCHAR(20),
    rept_mode_cd VARCHAR(40),
    rept_term VARCHAR(40),
    guar_fin_biz_ind VARCHAR(20),
    agt_dep_ind VARCHAR(20),
    supv_acct_ind VARCHAR(20),
    open_dt DATE,
    open_tm VARCHAR(20),
    open_org_cd VARCHAR(20),
    open_tlr_no VARCHAR(20),
    open_acct_chnl VARCHAR(100),
    open_acct_loc_region_cd VARCHAR(40),
    open_acct_ip_addr VARCHAR(100),
    open_acct_mac_addr VARCHAR(100),
    open_acct_cert_type_cd VARCHAR(40),
    open_acct_cert_no VARCHAR(100),
    safe_auth_doc_no VARCHAR(100),
    open_acct_agentee_name VARCHAR(1000),
    open_acct_agentee_cert_type_cd VARCHAR(40),
    open_acct_agentee_cert_no VARCHAR(100),
    open_acct_agentee_cert_start_dt DATE,
    open_acct_agentee_cert_end_dt DATE,
    open_acct_agentee_nation_cd VARCHAR(40),
    open_acct_agentee_tel VARCHAR(100),
    dep_term_type_cd VARCHAR(40),
    actl_term NUMERIC(10),
    dep_term_desc TEXT,
    matr_dt DATE,
    rsdu_matr_days NUMERIC(10),
    last_acct_dt DATE,
    open_acct_y_intr NUMERIC(18,10),
    intr_no VARCHAR(100),
    intr_adj_type_cd VARCHAR(40),
    intr_float_type_cd VARCHAR(40),
    intr_float_val NUMERIC(38,8),
    intr_float_pct NUMERIC(18,10),
    base_y_intr NUMERIC(18,10),
    actl_y_intr NUMERIC(18,10),
    unexp_draw_y_intr NUMERIC(18,10),
    int_ind VARCHAR(20),
    int_mode_cd VARCHAR(40),
    start_int_dt DATE,
    int_pay_mode_cd VARCHAR(40),
    int_stl_freq_cd VARCHAR(40),
    last_int_stl_dt DATE,
    next_int_stl_dt DATE,
    agt_intr_type_cd VARCHAR(40),
    agt_base_y_intr NUMERIC(18,10),
    agt_y_intr NUMERIC(18,10),
    agt_dep_eff_dt DATE,
    agt_dep_matr_dt DATE,
    dep_acct_sts_cd VARCHAR(40),
    wait_cnv_long_sus_dt DATE,
    cnv_long_sus_dt DATE,
    cnv_biz_incm_dt DATE,
    acct_free_draw_ind VARCHAR(20),
    acct_loss_ind VARCHAR(20),
    acct_frz_ind VARCHAR(20),
    acct_pay_type_cd VARCHAR(40),
    pldg_ind VARCHAR(20),
    close_dt DATE,
    close_tm VARCHAR(20),
    close_serl_no VARCHAR(100),
    close_org_cd VARCHAR(100),
    close_tlr_no VARCHAR(100),
    dep_clct_org_no VARCHAR(100),
    dep_clct_no VARCHAR(40),
    cust_mgr_no VARCHAR(100),
    data_del_ind VARCHAR(20),
    src_sys_cd VARCHAR(100),
    etl_dt DATE,
    prod_sign_intr NUMERIC(18,10),
    rrying_agt_amt NUMERIC(38,8),
    prod_sign_dt DATE,
    prod_matr_dt DATE,
    face_check_ind VARCHAR(10),
    prod_type VARCHAR(10),
    prod_data VARCHAR(20),
    xjx_y_intr NUMERIC(18,10),
    tempdep_yxrq DATE,
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.dep_acct_no IS '存款账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.cust_acct_no IS '客户账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.org_no IS '内部机构号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.ccy_ident_cd IS '钞汇类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.prod_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.prod_pd_no IS '产品期次编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.agt_no IS '协议编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.cust_acct_type_cd IS '客户账号类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.cust_type_cd IS '客户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.cust_acct_name IS '客户账户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.prin_subj_no IS '本金科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.payb_int_subj_no IS '应付利息科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.int_tax_subj_no IS '利息税科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.wait_draw_int_subj_no IS '待支取利息科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.int_adv_subj_no IS '利息前置科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.fix_cur_ind IS '定期活期标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.dep_type_cd IS '存款种类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.acct_char_cd IS '账户性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.acct_class_cd IS '账户分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.corp_cur_dep_acct_attr_cd IS '对公活期户属性代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.interbank_dep_acct_type_cd IS '同业存放账户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.spcl_dep_type_cd IS '专项存款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.ife_acct_cate_cd IS '互联网金融企业账户类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.rsrv_acct_type_cd IS '备付金账户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.fin_dep_acct_type_cd IS '财政存款账户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.cstn_acct_type_cd IS '托管账户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.safe_acct_char_cd IS '外管账户性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.fta_acct_type_cd IS '自贸区账户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.fin_supv_type_cd IS '资金监管类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.medium_type_cd IS '介质类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.verf_acct_ind IS '验资户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.margin_acct_ind IS '保证金账户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.margin_purp_cd IS '保证金用途代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.chq_acct_ind IS '支票户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.stl_acct_ind IS '结算账户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.allow_unexp_draw_ind IS '允许提前支取标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.rept_mode_cd IS '转存方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.rept_term IS '转存期限';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.guar_fin_biz_ind IS '担保融资业务标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.agt_dep_ind IS '协定存款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.supv_acct_ind IS '监管账户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_dt IS '开户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_tm IS '开户时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_org_cd IS '开户机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_tlr_no IS '开户柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_chnl IS '开户渠道';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_loc_region_cd IS '开户地地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_ip_addr IS '开户IP地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_mac_addr IS '开户MAC地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_cert_type_cd IS '开户证明文件类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_cert_no IS '开户证明文件编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.safe_auth_doc_no IS '外管局批件编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_agentee_name IS '开户代理人名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_agentee_cert_type_cd IS '开户代理人证件类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_agentee_cert_no IS '开户代理人证件号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_agentee_cert_start_dt IS '开户代理人证件有效期起始日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_agentee_cert_end_dt IS '开户代理人证件有效期结束日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_agentee_nation_cd IS '开户代理人国籍代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_agentee_tel IS '开户代理人电话';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.dep_term_type_cd IS '存款期限类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.actl_term IS '实际期限';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.dep_term_desc IS '存款期限描述';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.matr_dt IS '到期日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.rsdu_matr_days IS '剩余期限天数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.last_acct_dt IS '上次动户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.open_acct_y_intr IS '开户年利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.intr_no IS '利率编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.intr_adj_type_cd IS '利率靠档方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.intr_float_type_cd IS '利率浮动类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.intr_float_val IS '利率浮动值';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.intr_float_pct IS '利率浮动比例';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.base_y_intr IS '基准年利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.actl_y_intr IS '实际执行年利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.unexp_draw_y_intr IS '提前支取年利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.int_ind IS '计息标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.int_mode_cd IS '计息方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.start_int_dt IS '起息日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.int_pay_mode_cd IS '利息支付方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.int_stl_freq_cd IS '结息频率代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.last_int_stl_dt IS '上次结息日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.next_int_stl_dt IS '下次结息日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.agt_intr_type_cd IS '协定利率类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.agt_base_y_intr IS '协定基准年利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.agt_y_intr IS '协定年利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.agt_dep_eff_dt IS '协定存款生效日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.agt_dep_matr_dt IS '协定存款到期日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.dep_acct_sts_cd IS '存款账户状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.wait_cnv_long_sus_dt IS '待转久悬户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.cnv_long_sus_dt IS '转久悬户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.cnv_biz_incm_dt IS '转营业外收入日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.acct_free_draw_ind IS '账户通兑标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.acct_loss_ind IS '账户挂失标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.acct_frz_ind IS '账户冻结标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.acct_pay_type_cd IS '账户收付类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.pldg_ind IS '质押标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.close_dt IS '销户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.close_tm IS '销户时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.close_serl_no IS '销户流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.close_org_cd IS '销户机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.close_tlr_no IS '销户柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.dep_clct_org_no IS '揽存人员机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.dep_clct_no IS '揽存人员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.cust_mgr_no IS '客户经理编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.data_del_ind IS '数据删除标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.prod_sign_intr IS '签约利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.rrying_agt_amt IS '日日盈存款协定金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.prod_sign_dt IS '日日盈产品签约日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.prod_matr_dt IS '日日盈产品到期日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.face_check_ind IS '当面核实标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.prod_type IS '产品标识';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.prod_data IS '违约时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_info.xjx_y_intr IS '薪嘉薪21日实际利率';

-- f_mid_sxqj_a010_h
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_sxqj_a010_h (
    rel_col VARCHAR(50),
    dim_val VARCHAR(50),
    sum_flag VARCHAR(50),
    ztetl_dt DATE,
    legal_org_cd VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_sxqj_a010_h.rel_col IS '关联字段(客户号)';
COMMENT ON COLUMN fdmdata.f_mid_sxqj_a010_h.dim_val IS '维度值';
COMMENT ON COLUMN fdmdata.f_mid_sxqj_a010_h.sum_flag IS '汇总标志';
COMMENT ON COLUMN fdmdata.f_mid_sxqj_a010_h.ztetl_dt IS '中台跑批日期';
COMMENT ON COLUMN fdmdata.f_mid_sxqj_a010_h.legal_org_cd IS '法人机构编码';

-- s_ods_g_b_cif_corp_extend_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_cif_corp_extend_info (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    ecif_cust_no VARCHAR(100),
    oper_place_area NUMERIC(38,8),
    oper_place_prop_cd VARCHAR(40),
    bas_dep_acct_aprv_no VARCHAR(40),
    bas_dep_acct_bank_name VARCHAR(1000),
    bas_dep_acct_bank_no VARCHAR(100),
    bas_dep_acct_no VARCHAR(100),
    bas_dep_acct_open_dt DATE,
    corp_depr_cate_cd VARCHAR(40),
    ipo_co_ind VARCHAR(20),
    stockexch_cd VARCHAR(40),
    stock_cate_cd VARCHAR(40),
    stock_cd VARCHAR(40),
    grp_cust_ind VARCHAR(20),
    single_legal_cust_ind VARCHAR(20),
    grp_no VARCHAR(40),
    grp_par_corp_ind VARCHAR(20),
    fmly_ent_ind VARCHAR(20),
    tech_corp_ind VARCHAR(20),
    tech_corp_type_cd VARCHAR(20),
    tech_corp_type_name VARCHAR(1000),
    sse_star_ind VARCHAR(20),
    ent_growth_stg_cd VARCHAR(40),
    high_new_tech_ent_ind VARCHAR(20),
    guar_co_ind VARCHAR(20),
    spcl_econ_zone_ent_ind VARCHAR(20),
    region_impt_ent_ind VARCHAR(20),
    fin_class_ent_ind VARCHAR(20),
    st_own_ent_ind VARCHAR(20),
    sasac_ent_ind VARCHAR(20),
    nation_macro_ctrl_indu_ind VARCHAR(20),
    city_cnty_type_cd VARCHAR(40),
    agri_rel_ind VARCHAR(20),
    high_enrg_consm_ent_ind VARCHAR(20),
    over_cap_ent_ind VARCHAR(20),
    elim_cap_list_ent_ind VARCHAR(20),
    env_prot_ent_ind VARCHAR(20),
    high_polt_ent_ind VARCHAR(20),
    bank_trade_fin_cust_cd VARCHAR(20),
    spcl_biz_ind VARCHAR(20),
    steel_trade_ent_ind VARCHAR(20),
    major_ent_ind VARCHAR(20),
    indu_restru_type_cd VARCHAR(40),
    strtg_emrg_indu_ind VARCHAR(20),
    indu_tx_upgrd_ind VARCHAR(20),
    lead_ent_ind VARCHAR(20),
    prmt_ie_ind VARCHAR(20),
    ent_shut_ind VARCHAR(20),
    integ_plat_ent_ind VARCHAR(20),
    indu_park_ind VARCHAR(20),
    lgfp_sbrd_ent_cd VARCHAR(20),
    lgfp_sbrd_cd VARCHAR(40),
    lgfp_law_char_cd VARCHAR(40),
    govt_fin_loan_type_cd VARCHAR(40),
    small_sum_loan_co_ind VARCHAR(20),
    list_impt_sup_indu_ind VARCHAR(20),
    uscc_ent_int VARCHAR(20),
    land_consldtn_org_ind VARCHAR(20),
    tax_exmt_type_cd VARCHAR(40),
    tax_org_type_cd VARCHAR(40),
    small_ent_ind VARCHAR(20),
    ent_qal_lvl_cd VARCHAR(40),
    rmt_cust_ind VARCHAR(20),
    fgn_ex_prmt_no VARCHAR(100),
    bank_cust_class_cd VARCHAR(40),
    taxpayer_qal_type_cd VARCHAR(40),
    need_vat_spcl_invc_ind VARCHAR(20),
    taxpayer_full_name VARCHAR(400),
    nation_tax_reg_cert_no VARCHAR(40),
    taxpayer_addr VARCHAR(400),
    taxpayer_tel VARCHAR(100),
    taxpayer_bank_name VARCHAR(400),
    taxpayer_acct_no VARCHAR(100),
    oversea_subj_type_cd VARCHAR(40),
    rel_with_bank_ibs_cd VARCHAR(40),
    adm_penalty_list_ind VARCHAR(20),
    civil_judge_list_ind VARCHAR(20),
    enforce_list_ind VARCHAR(20),
    tax_owed_list_ind VARCHAR(20),
    ecif_cre_dttm VARCHAR(255),
    ecif_upd_dttm VARCHAR(255),
    cre_src_sys_cd VARCHAR(40),
    src_sys_cre_dttm VARCHAR(255),
    last_upd_dttm VARCHAR(255),
    last_upd_org_cd VARCHAR(20),
    last_upd_tlr_no VARCHAR(20),
    last_upd_sys_cd VARCHAR(40),
    etl_dt DATE,
    sse_star_type VARCHAR(10),
    tax_addr_en VARCHAR(300),
    tax_addr_ch VARCHAR(300),
    tax_addr_type VARCHAR(20),
    tax_city VARCHAR(300),
    tax_area_ch VARCHAR(20),
    tax_addr_nation VARCHAR(20),
    inno_busi_ind VARCHAR(20),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    assetstype VARCHAR(20),
    sse_star_ind_c VARCHAR(10),
    sse_star_type_c VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.oper_place_area IS '经营场地面积';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.oper_place_prop_cd IS '经营场地所有权代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.bas_dep_acct_aprv_no IS '基本账户核准号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.bas_dep_acct_bank_name IS '基本账户开户行名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.bas_dep_acct_bank_no IS '基本账户开户行号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.bas_dep_acct_no IS '基本账户账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.bas_dep_acct_open_dt IS '基本账户开户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.corp_depr_cate_cd IS '对公存款人类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.ipo_co_ind IS '上市公司标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.stockexch_cd IS '上市交易所代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.stock_cate_cd IS '股票类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.stock_cd IS '上市公司代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.grp_cust_ind IS '集团客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.single_legal_cust_ind IS '单一法人客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.grp_no IS '所属集团编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.grp_par_corp_ind IS '集团母公司标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.fmly_ent_ind IS '是否家族企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tech_corp_ind IS '科技企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tech_corp_type_cd IS '科技企业类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tech_corp_type_name IS '科技企业类型名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.sse_star_ind IS '科创企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.ent_growth_stg_cd IS '企业成长阶段代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.high_new_tech_ent_ind IS '是否高新技术企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.guar_co_ind IS '是否担保公司标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.spcl_econ_zone_ent_ind IS '是否特殊经济区内企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.region_impt_ent_ind IS '是否地区重点企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.fin_class_ent_ind IS '是否融资类企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.st_own_ent_ind IS '国资企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.sasac_ent_ind IS '是否国资委所属企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.nation_macro_ctrl_indu_ind IS '是否国家宏观调控限控行业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.city_cnty_type_cd IS '城乡类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.agri_rel_ind IS '是否涉农标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.high_enrg_consm_ent_ind IS '是否高能耗企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.over_cap_ent_ind IS '是否产能过剩企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.elim_cap_list_ent_ind IS '是否属于淘汰产能目录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.env_prot_ent_ind IS '是否环保企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.high_polt_ent_ind IS '是否高污染企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.bank_trade_fin_cust_cd IS '是否本行贸易融资客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.spcl_biz_ind IS '是否特种经营标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.steel_trade_ent_ind IS '是否钢贸企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.major_ent_ind IS '是否优势企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.indu_restru_type_cd IS '产业结构调整类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.strtg_emrg_indu_ind IS '战略新兴产业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.indu_tx_upgrd_ind IS '工业转型升级标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.lead_ent_ind IS '是否龙头企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.prmt_ie_ind IS '进出口权标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.ent_shut_ind IS '企业关停标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.integ_plat_ent_ind IS '是否综合平台企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.indu_park_ind IS '是否为工业园区、经济开发区等行政管理区标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.lgfp_sbrd_ent_cd IS '是否政府投融资平台企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.lgfp_sbrd_cd IS '地方政府融资平台隶属关系代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.lgfp_law_char_cd IS '地方政府融资平台法律性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.govt_fin_loan_type_cd IS '政府融资贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.small_sum_loan_co_ind IS '是否小额贷款公司标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.list_impt_sup_indu_ind IS '是否列入重点扶持产业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.uscc_ent_int IS '是否一照一码企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.land_consldtn_org_ind IS '是否土地整治机构标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_exmt_type_cd IS '纳税豁免类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_org_type_cd IS '纳税机构类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.small_ent_ind IS '小企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.ent_qal_lvl_cd IS '企业资质等级代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.rmt_cust_ind IS '是否异地客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.fgn_ex_prmt_no IS '外汇许可证号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.bank_cust_class_cd IS '本行客户分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.taxpayer_qal_type_cd IS '纳税人资质类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.need_vat_spcl_invc_ind IS '是否需要开具增值税专用发票标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.taxpayer_full_name IS '纳税人全称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.nation_tax_reg_cert_no IS '纳税人登记证号国税';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.taxpayer_addr IS '纳税人地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.taxpayer_tel IS '纳税人电话';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.taxpayer_bank_name IS '纳税人行名';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.taxpayer_acct_no IS '纳税人账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.oversea_subj_type_cd IS '境外主体类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.rel_with_bank_ibs_cd IS '与我行关系类型代码(国结)';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.adm_penalty_list_ind IS '行政处罚记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.civil_judge_list_ind IS '民事判决记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.enforce_list_ind IS '强制执行记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_owed_list_ind IS '欠税记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.ecif_cre_dttm IS 'ECIF创建时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.ecif_upd_dttm IS 'ECIF更新时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.cre_src_sys_cd IS '创建源系统代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.src_sys_cre_dttm IS '源系统创建时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.last_upd_dttm IS '最近更新时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.last_upd_org_cd IS '最近更新机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.last_upd_tlr_no IS '最近更新柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.last_upd_sys_cd IS '最近更新系统代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.sse_star_type IS '科创企业类型';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_addr_en IS '税收居民-英文详细地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_addr_ch IS '税收居民-中文详细地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_addr_type IS '税收居民-地址类型';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_city IS '税收居民-英文所在城市';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_area_ch IS '税收居民-中文-行政区划';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.tax_addr_nation IS '税收居民-国家代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.inno_busi_ind IS '创新业务标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.assetstype IS '国资分类';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.sse_star_ind_c IS '是否C类科创企业';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_extend_info.sse_star_type_c IS 'C类科创类型';

-- s_ods_g_b_ln_duebill
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_ln_duebill (
    tx_dt DATE,
    legal_org_cd VARCHAR(20),
    duebill_no VARCHAR(100),
    tx_serl_no VARCHAR(100),
    sub_tx_serl_no VARCHAR(100),
    serl_no INTEGER,
    duebill_name VARCHAR(1000),
    ecif_cust_no VARCHAR(40),
    subj_no VARCHAR(20),
    subj_name VARCHAR(1000),
    org_no VARCHAR(20),
    tx_ccy_cd VARCHAR(40),
    tx_type_cd VARCHAR(40),
    tx_mode_cd VARCHAR(40),
    dc_cd VARCHAR(40),
    cash_xfer_ind VARCHAR(20),
    tx_chnl_cd VARCHAR(40),
    tx_cd VARCHAR(40),
    tx_desc TEXT,
    cur_term INTEGER,
    tx_prin_amt NUMERIC(40,8),
    tx_prin_exch_usd_amt NUMERIC(40,8),
    tx_prin_exch_rmb_amt NUMERIC(40,8),
    tx_int_amt NUMERIC(40,8),
    tx_int_exch_usd_amt NUMERIC(40,8),
    tx_int_exch_rmb_amt NUMERIC(40,8),
    duebill_bal NUMERIC(40,8),
    cntpty_acct_no VARCHAR(100),
    cntpty_acct_name VARCHAR(1000),
    cntpty_fin_org_cd VARCHAR(40),
    cntpty_fin_org_name VARCHAR(1000),
    tx_agentee_cert_type_cd VARCHAR(40),
    tx_agentee_cert_no VARCHAR(100),
    tx_agentee_name VARCHAR(400),
    tx_abstract_cd VARCHAR(40),
    tx_abstract_desc TEXT,
    tx_tm VARCHAR(20),
    tx_org_cd VARCHAR(100),
    tx_tlr_no VARCHAR(20),
    auth_tlr_no VARCHAR(100),
    tx_sts_cd VARCHAR(40),
    src_sys_cd VARCHAR(20),
    etl_dt DATE,
    dttm NUMERIC,
    prod_no VARCHAR(20),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_dt IS '交易日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.duebill_no IS '借据编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_serl_no IS '交易流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.sub_tx_serl_no IS '子交易流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.serl_no IS '笔次序号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.duebill_name IS '借据名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.subj_no IS '明细科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.subj_name IS '明细科目名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.org_no IS '内部机构号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_ccy_cd IS '交易货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_type_cd IS '交易类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_mode_cd IS '交易方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.dc_cd IS '借贷方向代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.cash_xfer_ind IS '现转标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_chnl_cd IS '交易渠道代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_cd IS '交易代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_desc IS '交易代码描述';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.cur_term IS '当前期数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_prin_amt IS '交易本金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_prin_exch_usd_amt IS '交易本金金额折美元';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_prin_exch_rmb_amt IS '交易本金金额折人民币';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_int_amt IS '交易利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_int_exch_usd_amt IS '交易利息金额折美元';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_int_exch_rmb_amt IS '交易利息金额折人民币';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.duebill_bal IS '借据余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.cntpty_acct_no IS '对方账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.cntpty_acct_name IS '对方账户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.cntpty_fin_org_cd IS '对方金融机构代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.cntpty_fin_org_name IS '对方金融机构名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_agentee_cert_type_cd IS '交易代理人证件类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_agentee_cert_no IS '交易代理人证件号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_agentee_name IS '交易代理人姓名';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_abstract_cd IS '交易摘要代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_abstract_desc IS '交易摘要描述';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_tm IS '交易时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_org_cd IS '交易机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_tlr_no IS '交易柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.auth_tlr_no IS '授权柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.tx_sts_cd IS '交易状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.dttm IS '时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill.prod_no IS '产品编号';

-- s_ods_g_b_cif_corp_basic_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_cif_corp_basic_info (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    ecif_cust_no VARCHAR(100),
    cust_name VARCHAR(1000),
    cust_abrv_name VARCHAR(400),
    cbrc_small_ent_ind VARCHAR(20),
    bank_small_ent_ind VARCHAR(20),
    tax_reg_cert_no VARCHAR(100),
    tax_reg_cert_eff_dt DATE,
    tax_reg_cert_expr_dt DATE,
    tax_reg_cert_auth_org VARCHAR(200),
    prmt_oba_no VARCHAR(40),
    ent_middle_sign_no VARCHAR(40),
    ent_crdt_cd VARCHAR(40),
    ent_crdt_expr_dt DATE,
    found_dt DATE,
    indu_class_cd VARCHAR(40),
    sbrd_cd VARCHAR(40),
    holding_type_cd VARCHAR(40),
    inest_prin_part_cd VARCHAR(40),
    reg_type_cd VARCHAR(40),
    reg_dt DATE,
    reg_nation_cd VARCHAR(40),
    pbc_reg_region_cd VARCHAR(40),
    reg_adm_div_cd VARCHAR(40),
    reg_cap_ccy_cd VARCHAR(40),
    reg_cap_amt NUMERIC(38,8),
    paid_cap_ccy_cd VARCHAR(40),
    paid_cap_amt NUMERIC(38,8),
    annl_incm_amt NUMERIC(38,8),
    annl_sale_amt NUMERIC(38,8),
    tot_asset_amt NUMERIC(38,8),
    net_asset_amt NUMERIC(38,8),
    liab_tot_amt NUMERIC(38,8),
    org_type_cd VARCHAR(40),
    org_sub_type_cd VARCHAR(40),
    spcl_econ_zone_ent_type_cd VARCHAR(40),
    ent_econ_type_cd VARCHAR(40),
    nation_econ_dept_cd VARCHAR(40),
    ent_env_prot_lvl_cd VARCHAR(40),
    fin_org_type_cd VARCHAR(40),
    swift_no VARCHAR(20),
    spv_nation_cd VARCHAR(40),
    biz_term VARCHAR(40),
    biz_sts_cd VARCHAR(40),
    ent_scal_cd VARCHAR(40),
    biz_scope TEXT,
    major_biz_scope TEXT,
    cust_side_biz TEXT,
    emp_nums INTEGER,
    legal_bank_cust_no VARCHAR(40),
    legal_bank_name VARCHAR(1000),
    legal_bank_fin_org_cd VARCHAR(40),
    compt_org_name VARCHAR(400),
    compt_org_legal_name VARCHAR(1000),
    compt_org_legal_cert_type_cd VARCHAR(40),
    compt_org_legal_cert_no VARCHAR(100),
    interbank_org_no VARCHAR(40),
    interbank_url VARCHAR(100),
    interbank_cust_ind VARCHAR(20),
    biz_place_cd VARCHAR(40),
    rsdt_ctry_cd VARCHAR(40),
    fgn_invest_ctry_cd VARCHAR(40),
    safe_no VARCHAR(20),
    fx_decl_mode_cd VARCHAR(40),
    fx_decl_contact VARCHAR(100),
    fx_decl_contact_tel VARCHAR(100),
    is_org_type_cd VARCHAR(40),
    custom_reg_no VARCHAR(100),
    lei_cd VARCHAR(100),
    trade_ent_class_cd VARCHAR(40),
    ptnr_type_cd VARCHAR(40),
    ecif_cre_dttm VARCHAR(255),
    ecif_upd_dttm VARCHAR(255),
    cre_src_sys_cd VARCHAR(40),
    src_sys_cre_dttm VARCHAR(255),
    last_upd_dttm VARCHAR(255),
    last_upd_org_cd VARCHAR(20),
    last_upd_tlr_no VARCHAR(20),
    last_upd_sys_cd VARCHAR(40),
    etl_dt DATE,
    st_own_ent_belong VARCHAR(200),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.cust_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.cust_abrv_name IS '客户简称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.cbrc_small_ent_ind IS '银标小企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.bank_small_ent_ind IS '我行小企业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.tax_reg_cert_no IS '税务登记证号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.tax_reg_cert_eff_dt IS '税务登记证生效日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.tax_reg_cert_expr_dt IS '税务登记证失效日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.tax_reg_cert_auth_org IS '税务登记证签发机关';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.prmt_oba_no IS '开户许可证编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ent_middle_sign_no IS '企业中征码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ent_crdt_cd IS '机构信用代码证';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ent_crdt_expr_dt IS '机构信用代码证失效日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.found_dt IS '成立日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.indu_class_cd IS '产业分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.sbrd_cd IS '隶属关系代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.holding_type_cd IS '控股类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.inest_prin_part_cd IS '投资主体代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.reg_type_cd IS '登记注册类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.reg_dt IS '注册日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.reg_nation_cd IS '注册地国别或地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.pbc_reg_region_cd IS '人民银行注册地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.reg_adm_div_cd IS '注册地行政区划代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.reg_cap_ccy_cd IS '注册资本货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.reg_cap_amt IS '注册资本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.paid_cap_ccy_cd IS '实收资本货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.paid_cap_amt IS '实收资本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.annl_incm_amt IS '年收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.annl_sale_amt IS '年销售金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.tot_asset_amt IS '总资产金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.net_asset_amt IS '净资产金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.liab_tot_amt IS '负债总额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.org_type_cd IS '组织机构类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.org_sub_type_cd IS '组织机构子类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.spcl_econ_zone_ent_type_cd IS '特殊经济区企业类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ent_econ_type_cd IS '企业经济类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.nation_econ_dept_cd IS '国民经济部门代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ent_env_prot_lvl_cd IS '企业环保级别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.fin_org_type_cd IS '金融机构类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.swift_no IS 'SWIFT号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.spv_nation_cd IS 'SPV或壳机构所属国家地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.biz_term IS '经营期限';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.biz_sts_cd IS '经营状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ent_scal_cd IS '企业规模代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.biz_scope IS '经营范围';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.major_biz_scope IS '主营业务范围';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.cust_side_biz IS '客户兼营业务';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.emp_nums IS '员工人数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.legal_bank_cust_no IS '法人行客户号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.legal_bank_name IS '法人行名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.legal_bank_fin_org_cd IS '法人行金融机构代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.compt_org_name IS '主管单位';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.compt_org_legal_name IS '主管单位法人名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.compt_org_legal_cert_type_cd IS '主管单位法人证件类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.compt_org_legal_cert_no IS '主管单位法人证件号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.interbank_org_no IS '同业机构行号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.interbank_url IS '同业机构网址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.interbank_cust_ind IS '同业客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.biz_place_cd IS '营业场所代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.rsdt_ctry_cd IS '常驻国家代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.fgn_invest_ctry_cd IS '外方投资者国别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.safe_no IS '所属外管局编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.fx_decl_mode_cd IS '外汇申报方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.fx_decl_contact IS '外汇申报联系人';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.fx_decl_contact_tel IS '外汇申报联系人电话';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.is_org_type_cd IS '国际结算机构类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.custom_reg_no IS '海关注册号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.lei_cd IS '全球法人机构识别编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.trade_ent_class_cd IS '贸易企业分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ptnr_type_cd IS '合作方类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ecif_cre_dttm IS 'ECIF创建时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.ecif_upd_dttm IS 'ECIF更新时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.cre_src_sys_cd IS '创建源系统代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.src_sys_cre_dttm IS '源系统创建时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.last_upd_dttm IS '最近更新时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.last_upd_org_cd IS '最近更新机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.last_upd_tlr_no IS '最近更新柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.last_upd_sys_cd IS '最近更新系统代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_corp_basic_info.st_own_ent_belong IS '国资企业隶属关系企业隶属';

-- s_rrs_rd_1104_cz_m
CREATE TABLE IF NOT EXISTS sdmdata.s_rrs_rd_1104_cz_m (
    report_id VARCHAR(50),
    ddate VARCHAR(10),
    bankid VARCHAR(20),
    rid VARCHAR(20),
    a VARCHAR(50),
    b VARCHAR(50),
    c VARCHAR(50),
    d VARCHAR(50),
    e VARCHAR(50),
    f VARCHAR(50),
    g VARCHAR(50),
    h VARCHAR(50),
    i VARCHAR(50),
    j VARCHAR(50),
    k VARCHAR(50),
    l VARCHAR(50),
    m VARCHAR(50),
    n VARCHAR(50),
    o VARCHAR(50),
    p VARCHAR(50),
    q VARCHAR(50),
    r VARCHAR(50),
    s VARCHAR(50),
    t VARCHAR(50),
    u VARCHAR(50),
    v VARCHAR(50),
    w VARCHAR(50),
    x VARCHAR(50),
    y VARCHAR(50),
    z VARCHAR(50),
    a1 VARCHAR(50),
    a2 VARCHAR(50),
    a3 VARCHAR(50),
    a4 VARCHAR(50),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.report_id IS '表名';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.ddate IS '日期';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.bankid IS '行号';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.rid IS '机构号';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.a IS '列号A';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.b IS '列号B';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.c IS '列号C';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.d IS '列号D';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.e IS '列号E';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.f IS '列号F';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.g IS '列号G';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.h IS '列号H';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.i IS '列号I';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.j IS '列号J';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.k IS '列号K';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.l IS '列号L';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.m IS '列号M';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.n IS '列号N';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.o IS '列号O';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.p IS '列号P';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.q IS '列号Q';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.r IS '列号R';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.s IS '列号S';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.t IS '列号T';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.u IS '列号U';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.v IS '列号V';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.w IS '列号W';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.x IS '列号X';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.y IS '列号Y';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.z IS '列号Z';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.a1 IS '列号A1';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.a2 IS '列号A2';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.a3 IS '列号A3';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_m.a4 IS '列号A4';

-- s_ods_g_c_code_dict_h
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_c_code_dict_h (
    legal_org_cd VARCHAR(20),
    code_cd VARCHAR(40),
    code_val VARCHAR(200),
    start_dt DATE,
    code_val_name VARCHAR(400),
    code_val_desc TEXT,
    code_lvl INTEGER,
    up_code_val VARCHAR(200),
    sort_id INTEGER,
    class_cd VARCHAR(40),
    ref_cd VARCHAR(40),
    end_dt DATE,
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.code_cd IS '代码编号';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.code_val IS '代码值';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.start_dt IS '开始日期';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.code_val_name IS '代码值名称';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.code_val_desc IS '代码值描述';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.code_lvl IS '代码级别';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.up_code_val IS '上级代码值';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.sort_id IS '排序编号';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.class_cd IS '分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.ref_cd IS '参照代码';
COMMENT ON COLUMN sdmdata.s_ods_g_c_code_dict_h.end_dt IS '结束日期';

-- f_mid_mms_sxyxh
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_mms_sxyxh (
    legal_org_cd VARCHAR(20),
    cust_id VARCHAR(40),
    org_code VARCHAR(32),
    ztetl_dt VARCHAR(32)
);
COMMENT ON COLUMN fdmdata.f_mid_mms_sxyxh.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN fdmdata.f_mid_mms_sxyxh.cust_id IS '客户号';
COMMENT ON COLUMN fdmdata.f_mid_mms_sxyxh.org_code IS '二级机构编码';
COMMENT ON COLUMN fdmdata.f_mid_mms_sxyxh.ztetl_dt IS '中台日期';

-- s_rrs_rd_1104_cz_q
CREATE TABLE IF NOT EXISTS sdmdata.s_rrs_rd_1104_cz_q (
    report_id VARCHAR(50),
    ddate VARCHAR(10),
    bankid VARCHAR(20),
    rid VARCHAR(20),
    a VARCHAR(50),
    b VARCHAR(50),
    c VARCHAR(50),
    d VARCHAR(50),
    e VARCHAR(50),
    f VARCHAR(50),
    g VARCHAR(50),
    h VARCHAR(50),
    i VARCHAR(50),
    j VARCHAR(50),
    k VARCHAR(50),
    l VARCHAR(50),
    m VARCHAR(50),
    n VARCHAR(50),
    o VARCHAR(50),
    p VARCHAR(50),
    q VARCHAR(50),
    r VARCHAR(50),
    s VARCHAR(50),
    t VARCHAR(50),
    u VARCHAR(50),
    v VARCHAR(50),
    w VARCHAR(50),
    x VARCHAR(50),
    y VARCHAR(50),
    z VARCHAR(50),
    a1 VARCHAR(50),
    a2 VARCHAR(50),
    a3 VARCHAR(50),
    a4 VARCHAR(50),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.report_id IS '表名';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.ddate IS '日期';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.bankid IS '行号';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.rid IS '机构号';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.a IS '列号A';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.b IS '列号B';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.c IS '列号C';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.d IS '列号D';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.e IS '列号E';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.f IS '列号F';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.g IS '列号G';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.h IS '列号H';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.i IS '列号I';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.j IS '列号J';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.k IS '列号K';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.l IS '列号L';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.m IS '列号M';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.n IS '列号N';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.o IS '列号O';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.p IS '列号P';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.q IS '列号Q';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.r IS '列号R';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.s IS '列号S';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.t IS '列号T';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.u IS '列号U';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.v IS '列号V';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.w IS '列号W';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.x IS '列号X';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.y IS '列号Y';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.z IS '列号Z';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.a1 IS '列号A1';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.a2 IS '列号A2';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.a3 IS '列号A3';
COMMENT ON COLUMN sdmdata.s_rrs_rd_1104_cz_q.a4 IS '列号A4';

-- s_ods_g_b_ln_duebill_amt
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_ln_duebill_amt (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    duebill_no VARCHAR(100),
    ccy_cd VARCHAR(40),
    orig_ccy_ind VARCHAR(20),
    prin_amt NUMERIC(38,8),
    prin_bal NUMERIC(38,8),
    prin_ld_bal NUMERIC(38,8),
    prin_lme_bal NUMERIC(38,8),
    prin_lqe_bal NUMERIC(38,8),
    prin_lye_bal NUMERIC(38,8),
    prin_lysme_bal NUMERIC(38,8),
    m_prin_bal_accum NUMERIC(38,8),
    q_prin_bal_accum NUMERIC(38,8),
    y_prin_bal_accum NUMERIC(38,8),
    norm_prin_y_accum NUMERIC(38,8),
    m_prin_wgt_accum NUMERIC(38,8),
    q_prin_wgt_accum NUMERIC(38,8),
    y_prin_wgt_accum NUMERIC(38,8),
    y_norm_prin_wgt_accum NUMERIC(38,8),
    std_m_avg_prin_bal NUMERIC(38,8),
    std_q_avg_prin_bal NUMERIC(38,8),
    std_y_avg_prin_bal NUMERIC(38,8),
    actl_m_avg_prin_bal NUMERIC(38,8),
    actl_q_avg_prin_bal NUMERIC(38,8),
    actl_y_avg_prin_bal NUMERIC(38,8),
    norm_prin_bal NUMERIC(38,8),
    ovrd_prin_bal NUMERIC(38,8),
    idle_prin_bal NUMERIC(38,8),
    bad_prin_bal NUMERIC(38,8),
    ibs_owe_int_amt NUMERIC(38,8),
    obs_owe_int_amt NUMERIC(38,8),
    rai_amt NUMERIC(38,8),
    cai_amt NUMERIC(38,8),
    adi_amt NUMERIC(38,8),
    rdi_amt NUMERIC(38,8),
    dci_amt NUMERIC(38,8),
    roi_amt NUMERIC(38,8),
    coi_amt NUMERIC(38,8),
    rapi_amt NUMERIC(38,8),
    capi_amt NUMERIC(38,8),
    rpi_amt NUMERIC(38,8),
    margin_amt NUMERIC(38,8),
    margin_bal NUMERIC(38,8),
    adv_amt NUMERIC(38,8),
    adv_bal NUMERIC(38,8),
    ovrd_amt NUMERIC(38,8),
    cpi_amt NUMERIC(38,8),
    aci_amt NUMERIC(38,8),
    rci_amt NUMERIC(38,8),
    wai_amt NUMERIC(38,8),
    int_adj_amt NUMERIC(38,8),
    recvb_mulct_amt NUMERIC(38,8),
    recvb_fee_amt NUMERIC(38,8),
    int_incm_amt NUMERIC(38,8),
    fee_incm_amt NUMERIC(38,8),
    mulct_incm_amt NUMERIC(38,8),
    rrabsci_amt NUMERIC(38,8),
    rabsroi_amt NUMERIC(38,8),
    rabsrpi_amt NUMERIC(38,8),
    ali_amt NUMERIC(38,8),
    eve_acru_int_amt NUMERIC(38,8),
    y_tot_owe_int NUMERIC(38,8),
    depr_prin_amt NUMERIC(38,8),
    depr_rsrv_amt NUMERIC(38,8),
    deval_loss_amt NUMERIC(38,8),
    restru_b_loan_amt NUMERIC(38,8),
    chrgoff_prin_amt NUMERIC(38,8),
    chrgoff_int_amt NUMERIC(38,8),
    crp_amt NUMERIC(38,8),
    cri_amt NUMERIC(38,8),
    loan_incm_amt NUMERIC(38,8),
    src_sys_cd VARCHAR(100),
    etl_dt DATE,
    pi_norm_prin_bal NUMERIC(38,8),
    pi_norm_y_avg_prin_bal NUMERIC(38,8),
    pi_norm_prin_y_bal_accum NUMERIC(38,8),
    pi_norm_prin_y_wgt_accum NUMERIC(38,8),
    ovrd_less90_prin_bal NUMERIC(38,8),
    ovrd_less90_prin_y_avg_bal NUMERIC(38,8),
    ovrd_less90_prin_y_accum NUMERIC(38,8),
    ovrd_less90_prin_y_wgt_accum NUMERIC(38,8),
    ovrd_more90_prin_bal NUMERIC(38,8),
    ovrd_more90_prin_y_avg_bal NUMERIC(38,8),
    ovrd_more90_prin_y_accum NUMERIC(38,8),
    prin_wgt_bal NUMERIC(38,8),
    int_amt1 NUMERIC(38,8),
    int_amt2 NUMERIC(38,8),
    int_tax NUMERIC(38,8),
    actl_int_amt NUMERIC(38,8),
    actl_pi_amt NUMERIC(38,8),
    crp_amt_d NUMERIC(38,8),
    cri_amt_d NUMERIC(38,8),
    ret_rapi_amt_d NUMERIC(38,8),
    ret_capi_amt_d NUMERIC(38,8),
    ret_rpi_amt_d NUMERIC(38,8),
    ret_cpi_amt_d NUMERIC(38,8),
    ret_rai_amt_d NUMERIC(38,8),
    ret_cai_amt_d NUMERIC(38,8),
    ret_ra_owe_int_d NUMERIC(38,8),
    ret_ca_owe_int_d NUMERIC(38,8),
    lzlk_y_accum NUMERIC(38,8),
    lzlk_y_avg_prin_bal NUMERIC(38,8),
    int_pref_amt NUMERIC(20,7),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    int_amt2_m_accum NUMERIC(40,8),
    int_amt2_q_accum NUMERIC(40,8),
    int_amt2_y_accum NUMERIC(40,8)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.duebill_no IS '借据编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.orig_ccy_ind IS '原币标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.prin_amt IS '借款本金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.prin_bal IS '借款本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.prin_ld_bal IS '本金上日余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.prin_lme_bal IS '本金上月末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.prin_lqe_bal IS '本金上季末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.prin_lye_bal IS '本金上年末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.prin_lysme_bal IS '本金上年同期月末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.m_prin_bal_accum IS '本金余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.q_prin_bal_accum IS '本金余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.y_prin_bal_accum IS '本金余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.norm_prin_y_accum IS '正常本金余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.m_prin_wgt_accum IS '本金余额月加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.q_prin_wgt_accum IS '本金余额季加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.y_prin_wgt_accum IS '本金余额年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.y_norm_prin_wgt_accum IS '正常本金余额年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.std_m_avg_prin_bal IS '标准月日均本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.std_q_avg_prin_bal IS '标准季日均本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.std_y_avg_prin_bal IS '标准年日均本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.actl_m_avg_prin_bal IS '实际月日均本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.actl_q_avg_prin_bal IS '实际季日均本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.actl_y_avg_prin_bal IS '实际年日均本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.norm_prin_bal IS '正常本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_prin_bal IS '逾期本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.idle_prin_bal IS '呆滞本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.bad_prin_bal IS '呆账本金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ibs_owe_int_amt IS '表内欠息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.obs_owe_int_amt IS '表外欠息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.rai_amt IS '应收应计利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.cai_amt IS '催收应计利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.adi_amt IS '应计贴息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.rdi_amt IS '应收贴息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.dci_amt IS '贴息复利金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.roi_amt IS '应收欠息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.coi_amt IS '催收欠息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.rapi_amt IS '应收应计罚息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.capi_amt IS '催收应计罚息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.rpi_amt IS '应收罚息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.margin_amt IS '保证金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.margin_bal IS '保证金余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.adv_amt IS '垫款金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.adv_bal IS '垫款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_amt IS '银监逾期金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.cpi_amt IS '催收罚息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.aci_amt IS '应计复息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.rci_amt IS '应收复息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.wai_amt IS '待摊利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_adj_amt IS '利息调整金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.recvb_mulct_amt IS '应收罚金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.recvb_fee_amt IS '应收费用金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_incm_amt IS '利息收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.fee_incm_amt IS '费用收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.mulct_incm_amt IS '罚金收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.rrabsci_amt IS '应收赎回证券化贷款复息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.rabsroi_amt IS '赎回证券化贷款应收欠息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.rabsrpi_amt IS '赎回证券化贷款应收罚息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ali_amt IS '已计提贷款利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.eve_acru_int_amt IS '每日计提利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.y_tot_owe_int IS '本年累计产生欠息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.depr_prin_amt IS '减值本金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.depr_rsrv_amt IS '减值准备金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.deval_loss_amt IS '减值损失金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.restru_b_loan_amt IS '重组前贷款金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.chrgoff_prin_amt IS '已核销本金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.chrgoff_int_amt IS '已核销利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.crp_amt IS '核销收回本金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.cri_amt IS '核销收回利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.loan_incm_amt IS '贷款损益金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.pi_norm_prin_bal IS '本息未逾期贷款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.pi_norm_y_avg_prin_bal IS '本息未逾期贷款年日均';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.pi_norm_prin_y_bal_accum IS '本息未逾期贷款余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.pi_norm_prin_y_wgt_accum IS '本息未逾期贷款余额年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_less90_prin_bal IS '逾期90天内贷款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_less90_prin_y_avg_bal IS '逾期90天内贷款年日均';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_less90_prin_y_accum IS '逾期90天内贷款年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_less90_prin_y_wgt_accum IS '逾期90天内贷款年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_more90_prin_bal IS '逾期超90天贷款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_more90_prin_y_avg_bal IS '逾期超90天贷款年日均';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ovrd_more90_prin_y_accum IS '逾期超90天贷款年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.prin_wgt_bal IS '借款本金加权利息余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_amt1 IS '当日应计利息税前';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_amt2 IS '当日利息收入税后';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_tax IS '当日利息收入税金';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.actl_int_amt IS '当日实收利息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.actl_pi_amt IS '当日实收罚息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.crp_amt_d IS '当日核销收回本金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.cri_amt_d IS '当日核销收回利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ret_rapi_amt_d IS '归还应收应计罚息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ret_capi_amt_d IS '归还催收应计罚息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ret_rpi_amt_d IS '归还应收罚息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ret_cpi_amt_d IS '归还催收罚息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ret_rai_amt_d IS '归还应收应计利息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ret_cai_amt_d IS '归还催收应计利息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ret_ra_owe_int_d IS '归还应收欠息利息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.ret_ca_owe_int_d IS '归还催收欠息利息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.lzlk_y_accum IS '两增两控年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.lzlk_y_avg_prin_bal IS '两增两控日均';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_pref_amt IS '利息优惠金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_amt2_m_accum IS '利息收入-本月累计税后';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_amt2_q_accum IS '利息收入-本季累计税后';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_duebill_amt.int_amt2_y_accum IS '利息收入-本年累计税后';

-- s_ods_g_b_gl_subj_bal
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_gl_subj_bal (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    subj_no VARCHAR(20),
    org_cd VARCHAR(20),
    ccy_cd VARCHAR(40),
    ye_stl_xfer_ind VARCHAR(20),
    bal_dc_cd VARCHAR(40),
    obs_subj_ind VARCHAR(20),
    prev_dr_bal NUMERIC(38,8),
    prev_cr_bal NUMERIC(38,8),
    cash_dr_cnt NUMERIC(10),
    cash_cr_cnt NUMERIC(10),
    dr_cnt NUMERIC(10),
    cr_cnt NUMERIC(10),
    dr_amt NUMERIC(38,8),
    cr_amt NUMERIC(38,8),
    m_dr_amt NUMERIC(38,8),
    m_cr_amt NUMERIC(38,8),
    q_dr_amt NUMERIC(38,8),
    q_cr_amt NUMERIC(38,8),
    y_dr_amt NUMERIC(38,8),
    y_cr_amt NUMERIC(38,8),
    dr_bal NUMERIC(38,8),
    cr_bal NUMERIC(38,8),
    m_dr_bal_accum NUMERIC(38,8),
    m_cr_bal_accum NUMERIC(38,8),
    q_dr_bal_accum NUMERIC(38,8),
    q_cr_bal_accum NUMERIC(38,8),
    y_dr_bal_accum NUMERIC(38,8),
    y_cr_bal_accum NUMERIC(38,8),
    m_dr_avg_bal NUMERIC(38,8),
    m_cr_avg_bal NUMERIC(38,8),
    q_dr_avg_bal NUMERIC(38,8),
    q_cr_avg_bal NUMERIC(38,8),
    y_dr_avg_bal NUMERIC(38,8),
    y_cr_avg_bal NUMERIC(38,8),
    src_sys_cd VARCHAR(100),
    etl_dt DATE,
    jxb_fr_id VARCHAR(3),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.subj_no IS '会计科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.ye_stl_xfer_ind IS '年终结转标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.bal_dc_cd IS '余额借贷方向代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.obs_subj_ind IS '表外科目标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.prev_dr_bal IS '期初借方余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.prev_cr_bal IS '期初贷方余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.cash_dr_cnt IS '本期现金借方笔数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.cash_cr_cnt IS '本期现金贷方笔数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.dr_cnt IS '本期借方笔数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.cr_cnt IS '本期贷方笔数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.dr_amt IS '本期借方发生额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.cr_amt IS '本期贷方发生额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.m_dr_amt IS '本月借方发生额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.m_cr_amt IS '本月贷方发生额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.q_dr_amt IS '本季借方发生额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.q_cr_amt IS '本季贷方发生额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.y_dr_amt IS '本年借方发生额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.y_cr_amt IS '本年贷方发生额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.dr_bal IS '期末借方余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.cr_bal IS '期末贷方余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.m_dr_bal_accum IS '期末借方余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.m_cr_bal_accum IS '期末贷方余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.q_dr_bal_accum IS '期末借方余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.q_cr_bal_accum IS '期末贷方余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.y_dr_bal_accum IS '期末借方余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.y_cr_bal_accum IS '期末贷方余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.m_dr_avg_bal IS '期末借方月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.m_cr_avg_bal IS '期末贷方月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.q_dr_avg_bal IS '期末借方季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.q_cr_avg_bal IS '期末贷方季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.y_dr_avg_bal IS '期末借方年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.y_cr_avg_bal IS '期末贷方年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_gl_subj_bal.etl_dt IS 'ETL日期';

-- s_ods_g_s_cif_asset_liab_sum
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_s_cif_asset_liab_sum (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    ecif_cust_no VARCHAR(100),
    ccy_cd VARCHAR(40),
    cust_name VARCHAR(1000),
    cust_type_cd VARCHAR(40),
    cust_crdt_stat_class_cd VARCHAR(40),
    ent_scal_cd VARCHAR(40),
    cust_spon_org_cd VARCHAR(40),
    crdt_reg_org_cd VARCHAR(40),
    dep_frst_acct_org_cd VARCHAR(40),
    max_dep_yavg_org_cd VARCHAR(40),
    cur_dep_frst_acct_org_cd VARCHAR(40),
    fix_dep_frst_acct_org_cd VARCHAR(40),
    ln_crdt_tot_amt NUMERIC(38,8),
    ln_crdt_expo_tot_amt NUMERIC(38,8),
    ln_putout_tot_amt NUMERIC(38,8),
    tot_asset_bal NUMERIC(38,8),
    tot_asset_m_avg_bal NUMERIC(38,8),
    tot_asset_q_avg_bal NUMERIC(38,8),
    tot_asset_y_avg_bal NUMERIC(38,8),
    tot_liab_bal NUMERIC(38,8),
    tot_liab_m_avg_bal NUMERIC(38,8),
    tot_liab_q_avg_bal NUMERIC(38,8),
    tot_liab_y_avg_bal NUMERIC(38,8),
    dep_bal NUMERIC(38,8),
    dep_m_avg_bal NUMERIC(38,8),
    dep_q_avg_bal NUMERIC(38,8),
    dep_y_avg_bal NUMERIC(38,8),
    cur_dep_bal NUMERIC(38,8),
    cur_dep_m_avg_bal NUMERIC(38,8),
    cur_dep_q_avg_bal NUMERIC(38,8),
    cur_dep_y_avg_bal NUMERIC(38,8),
    ld_fix_dep_bal NUMERIC(38,8),
    fix_dep_bal NUMERIC(38,8),
    fix_dep_m_avg_bal NUMERIC(38,8),
    fix_dep_q_avg_bal NUMERIC(38,8),
    fix_dep_y_avg_bal NUMERIC(38,8),
    ld_fin_prod_bal NUMERIC(38,8),
    fin_prod_bal NUMERIC(38,8),
    fin_prod_m_avg_bal NUMERIC(38,8),
    fin_prod_q_avg_bal NUMERIC(38,8),
    fin_prod_y_avg_bal NUMERIC(38,8),
    insur_prod_bal NUMERIC(38,8),
    insur_prod_m_avg_bal NUMERIC(38,8),
    insur_prod_q_avg_bal NUMERIC(38,8),
    insur_prod_y_avg_bal NUMERIC(38,8),
    ld_fund_prod_bal NUMERIC(38,8),
    fund_prod_bal NUMERIC(38,8),
    fund_prod_m_avg_bal NUMERIC(38,8),
    fund_prod_q_avg_bal NUMERIC(38,8),
    fund_prod_y_avg_bal NUMERIC(38,8),
    ld_im_prod_bal NUMERIC(38,8),
    im_prod_bal NUMERIC(38,8),
    im_prod_m_avg_bal NUMERIC(38,8),
    im_prod_q_avg_bal NUMERIC(38,8),
    im_prod_y_avg_bal NUMERIC(38,8),
    all_loan_bal NUMERIC(38,8),
    all_loan_m_avg_bal NUMERIC(38,8),
    all_loan_q_avg_bal NUMERIC(38,8),
    all_loan_y_avg_bal NUMERIC(38,8),
    loan_bal NUMERIC(38,8),
    loan_m_avg_bal NUMERIC(38,8),
    loan_q_avg_bal NUMERIC(38,8),
    loan_y_avg_bal NUMERIC(38,8),
    indv_consm_ln_bal NUMERIC(38,8),
    acpt_tot_amt NUMERIC(38,8),
    fin_lg_tot_amt NUMERIC(38,8),
    non_fin_lg_tot_amt NUMERIC(38,8),
    lc_tot_amt NUMERIC(38,8),
    etl_dt DATE,
    all_crdt_tot_amt NUMERIC(38,8),
    ln_unif_tot_amt NUMERIC(38,8),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cust_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cust_type_cd IS '客户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cust_crdt_stat_class_cd IS '客户信贷统计分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ent_scal_cd IS '企业规模代码';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cust_spon_org_cd IS '客户主办机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.crdt_reg_org_cd IS '信贷客户登记机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.dep_frst_acct_org_cd IS '存款最早有效核算机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.max_dep_yavg_org_cd IS '最高存款年日均所属机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cur_dep_frst_acct_org_cd IS '活期存款最早有效核算机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fix_dep_frst_acct_org_cd IS '定期存款最早有效核算机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ln_crdt_tot_amt IS '信贷授信总额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ln_crdt_expo_tot_amt IS '信贷授信敞口总额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ln_putout_tot_amt IS '信贷发放总额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.tot_asset_bal IS '总资产余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.tot_asset_m_avg_bal IS '总资产月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.tot_asset_q_avg_bal IS '总资产季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.tot_asset_y_avg_bal IS '总资产年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.tot_liab_bal IS '总负债余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.tot_liab_m_avg_bal IS '总负债月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.tot_liab_q_avg_bal IS '总负债季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.tot_liab_y_avg_bal IS '总负债年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.dep_bal IS '存款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.dep_m_avg_bal IS '存款月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.dep_q_avg_bal IS '存款季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.dep_y_avg_bal IS '存款年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cur_dep_bal IS '活期存款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cur_dep_m_avg_bal IS '活期存款月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cur_dep_q_avg_bal IS '活期存款季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.cur_dep_y_avg_bal IS '活期存款年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ld_fix_dep_bal IS '上日定期存款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fix_dep_bal IS '定期存款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fix_dep_m_avg_bal IS '定期存款月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fix_dep_q_avg_bal IS '定期存款季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fix_dep_y_avg_bal IS '定期存款年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ld_fin_prod_bal IS '上日理财产品余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fin_prod_bal IS '理财产品余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fin_prod_m_avg_bal IS '理财产品月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fin_prod_q_avg_bal IS '理财产品季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fin_prod_y_avg_bal IS '理财产品年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.insur_prod_bal IS '保险产品余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.insur_prod_m_avg_bal IS '保险产品月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.insur_prod_q_avg_bal IS '保险产品季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.insur_prod_y_avg_bal IS '保险产品年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ld_fund_prod_bal IS '上日基金产品余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fund_prod_bal IS '基金产品余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fund_prod_m_avg_bal IS '基金产品月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fund_prod_q_avg_bal IS '基金产品季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.fund_prod_y_avg_bal IS '基金产品年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.ld_im_prod_bal IS '上日资管产品余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.im_prod_bal IS '资管产品余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.im_prod_m_avg_bal IS '资管产品月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.im_prod_q_avg_bal IS '资管产品季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.im_prod_y_avg_bal IS '资管产品年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.all_loan_bal IS '所有贷款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.all_loan_m_avg_bal IS '所有贷款月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.all_loan_q_avg_bal IS '所有贷款季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.all_loan_y_avg_bal IS '所有贷款年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.loan_bal IS '各项贷款余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.loan_m_avg_bal IS '各项贷款月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.loan_q_avg_bal IS '各项贷款季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_s_cif_asset_liab_sum.loan_y_avg_bal IS '各项贷款年日均余额';

-- s_ods_g_c_prd_rel_hie
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_c_prd_rel_hie (
    level1_cd VARCHAR(10),
    level1_val VARCHAR(100),
    level2_cd VARCHAR(10),
    level2_val VARCHAR(100),
    level3_cd VARCHAR(10),
    level3_val VARCHAR(100),
    level4_cd VARCHAR(10),
    level4_val VARCHAR(100),
    level5_cd VARCHAR(10),
    level5_val VARCHAR(100),
    is_sp_prd VARCHAR(10),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level1_cd IS '一级节点编码';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level1_val IS '一级节点码值';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level2_cd IS '二级节点编码';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level2_val IS '二级节点码值';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level3_cd IS '三级节点编码';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level3_val IS '三级节点码值';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level4_cd IS '四级节点编码';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level4_val IS '四级节点码值';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level5_cd IS '五集结点编码';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.level5_val IS '五级节点码值';
COMMENT ON COLUMN sdmdata.s_ods_g_c_prd_rel_hie.is_sp_prd IS '是否特色产品';

-- s_ods_m_pam_d_dep
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_m_pam_d_dep (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    dep_acct_cd VARCHAR(40),
    cust_acct_no VARCHAR(100),
    cust_acct_type_cd VARCHAR(40),
    sub_acct_sn VARCHAR(20),
    cust_mgr_no VARCHAR(100),
    cust_mgr_bel_dept_cd VARCHAR(40),
    cust_mgr_bel_org_cd VARCHAR(40),
    subj_no VARCHAR(100),
    prod_no VARCHAR(100),
    acct_name VARCHAR(1000),
    cust_mgr_name VARCHAR(1000),
    org_cd VARCHAR(20),
    ccy_cd VARCHAR(40),
    ecif_cust_no VARCHAR(40),
    cust_name VARCHAR(1000),
    cust_type_cd VARCHAR(40),
    fix_cur_ind VARCHAR(20),
    dep_type_cd VARCHAR(40),
    open_org_cd VARCHAR(20),
    open_org_name VARCHAR(1000),
    open_dt DATE,
    start_int_dt DATE,
    div_pct NUMERIC(40,8),
    b_div_bal NUMERIC(40,8),
    dep_bal NUMERIC(40,8),
    int_bal NUMERIC(40,8),
    payb_int_amt NUMERIC(40,8),
    ftp_profit NUMERIC(40,8),
    ftp_m_accum NUMERIC(40,8),
    ftp_y_accum NUMERIC(40,8),
    actl_y_intr NUMERIC(18,10),
    m_prin_bal_accum NUMERIC(40,8),
    prin_m_avg NUMERIC(40,8),
    q_prin_bal_accum NUMERIC(40,8),
    prin_q_avg NUMERIC(40,8),
    y_prin_bal_accum NUMERIC(40,8),
    prin_y_avg NUMERIC(40,8),
    int_bal_m_accum NUMERIC(40,8),
    int_bal_m_avg NUMERIC(40,8),
    int_bal_q_accum NUMERIC(40,8),
    int_bal_q_avg NUMERIC(40,8),
    int_bal_y_accum NUMERIC(40,8),
    int_bal_y_avg NUMERIC(40,8),
    ori_dept_flag VARCHAR(5),
    ori_cust_mgr VARCHAR(100),
    yj_int_amt NUMERIC(40,8),
    inc_flag VARCHAR(20),
    agt_dep_ind VARCHAR(20),
    prod_sign_intr NUMERIC(18,10),
    jxb_fr_id VARCHAR(4),
    ztetl_dt VARCHAR(10),
    d_payb_int_amt NUMERIC(40,8),
    d_payb_int_m_accum NUMERIC(40,8),
    d_payb_int_q_accum NUMERIC(40,8)
);
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.dep_acct_cd IS '存款账户编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.cust_acct_no IS '客户账号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.cust_acct_type_cd IS '客户账号类型代码';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.sub_acct_sn IS '子账号序号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.cust_mgr_no IS '客户经理编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.cust_mgr_bel_dept_cd IS '客户经理所属部门编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.cust_mgr_bel_org_cd IS '客户经理所属机构编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.subj_no IS '科目编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.prod_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.acct_name IS '账户名称';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.cust_mgr_name IS '客户经理名称';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.cust_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.cust_type_cd IS '客户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.fix_cur_ind IS '定期活期标志';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.dep_type_cd IS '存款种类代码';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.open_org_cd IS '开户机构编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.open_org_name IS '开户机构名称';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.open_dt IS '开户日期';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.start_int_dt IS '起息日期';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.div_pct IS '分成比例';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.b_div_bal IS '分成前余额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.dep_bal IS '存款余额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.int_bal IS '利息余额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.payb_int_amt IS '应付利息金额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.ftp_profit IS 'ftp创利金额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.ftp_m_accum IS 'ftp创利金额月积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.ftp_y_accum IS 'ftp创利金额年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.actl_y_intr IS '执行年利率';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.m_prin_bal_accum IS '本金余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.prin_m_avg IS '本金余额月日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.q_prin_bal_accum IS '本金余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.prin_q_avg IS '本金余额季日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.y_prin_bal_accum IS '本金余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.prin_y_avg IS '本金余额年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.int_bal_m_accum IS '利息余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.int_bal_m_avg IS '利息余额月日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.int_bal_q_accum IS '利息余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.int_bal_q_avg IS '利息余额季日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.int_bal_y_accum IS '利息余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.int_bal_y_avg IS '利息余额年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.ori_dept_flag IS '原部门标志';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.ori_cust_mgr IS '原客户经理编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.yj_int_amt IS '本年累计应计利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.inc_flag IS '增量标记';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.agt_dep_ind IS '协定存款标志';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.prod_sign_intr IS '特殊产品签约利率';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.d_payb_int_amt IS '当日应付利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.d_payb_int_m_accum IS '当日应付利息-本月累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_dep.d_payb_int_q_accum IS '当日应付利息-本季累计';

-- s_ods_m_pam_d_crdt
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_m_pam_d_crdt (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    duebill_no VARCHAR(100),
    cust_mgr_no VARCHAR(100),
    cust_mgr_name VARCHAR(1000),
    cust_mgr_bel_dept_cd VARCHAR(40),
    cust_mgr_bel_org_cd VARCHAR(40),
    subj_no VARCHAR(100),
    prod_no VARCHAR(100),
    ccy_cd VARCHAR(40),
    contr_no VARCHAR(100),
    guar_mode_cd VARCHAR(40),
    ent_scal_cd VARCHAR(40),
    tech_corp_ind VARCHAR(20),
    crdt_obj_class_cd VARCHAR(40),
    crdt_attr_class_cd VARCHAR(40),
    crdt_biz_cate_cd VARCHAR(40),
    obs_biz_ind VARCHAR(20),
    ecif_cust_no VARCHAR(40),
    cust_name VARCHAR(1000),
    titc_cust_id VARCHAR(20),
    open_org_cd VARCHAR(20),
    org_cd VARCHAR(20),
    b_div_bal NUMERIC(40,8),
    div_pct NUMERIC(40,8),
    actl_y_intr NUMERIC(18,10),
    actl_m_intr NUMERIC(18,10),
    chrgoff_amt NUMERIC(40,8),
    loan_bal NUMERIC(40,8),
    loan_bal_m_accum NUMERIC(40,8),
    loan_bal_q_accum NUMERIC(40,8),
    loan_bal_y_accum NUMERIC(40,8),
    loan_bal_m_avg NUMERIC(40,8),
    loan_bal_q_avg NUMERIC(40,8),
    loan_bal_y_avg NUMERIC(40,8),
    ovrd_prin_bal NUMERIC(40,8),
    norm_prin_bal NUMERIC(40,8),
    norm_prin_m_accum NUMERIC(40,8),
    norm_prin_q_accum NUMERIC(40,8),
    norm_prin_y_accum NUMERIC(40,8),
    norm_prin_m_avg NUMERIC(40,8),
    norm_prin_q_avg NUMERIC(40,8),
    norm_prin_y_avg NUMERIC(40,8),
    norm_prin_wgt_bal NUMERIC(40,8),
    norm_prin_m_wgt_accum NUMERIC(40,8),
    norm_prin_q_wgt_accum NUMERIC(40,8),
    norm_prin_y_wgt_accum NUMERIC(40,8),
    norm_prin_m_wgt_avg NUMERIC(40,8),
    norm_prin_q_wgt_avg NUMERIC(40,8),
    norm_prin_y_wgt_avg NUMERIC(40,8),
    five1_prin_bal NUMERIC(40,8),
    five1_prin_m_accum NUMERIC(40,8),
    five1_prin_q_accum NUMERIC(40,8),
    five1_prin_y_accum NUMERIC(40,8),
    five1_prin_m_avg NUMERIC(40,8),
    five1_prin_q_avg NUMERIC(40,8),
    five1_prin_y_avg NUMERIC(40,8),
    five2_prin_bal NUMERIC(40,8),
    five2_prin_m_accum NUMERIC(40,8),
    five2_prin_q_accum NUMERIC(40,8),
    five2_prin_y_accum NUMERIC(40,8),
    five2_prin_m_avg NUMERIC(40,8),
    five2_prin_q_avg NUMERIC(40,8),
    five2_prin_y_avg NUMERIC(40,8),
    five3_prin_bal NUMERIC(40,8),
    five3_prin_m_accum NUMERIC(40,8),
    five3_prin_q_accum NUMERIC(40,8),
    five3_prin_y_accum NUMERIC(40,8),
    five3_prin_m_avg NUMERIC(40,8),
    five3_prin_q_avg NUMERIC(40,8),
    five3_prin_y_avg NUMERIC(40,8),
    five4_prin_bal NUMERIC(40,8),
    five4_prin_m_accum NUMERIC(40,8),
    five4_prin_q_accum NUMERIC(40,8),
    five4_prin_y_accum NUMERIC(40,8),
    five4_prin_m_avg NUMERIC(40,8),
    five4_prin_q_avg NUMERIC(40,8),
    five4_prin_y_avg NUMERIC(40,8),
    five5_prin_bal NUMERIC(40,8),
    five5_prin_m_accum NUMERIC(40,8),
    five5_prin_q_accum NUMERIC(40,8),
    five5_prin_y_accum NUMERIC(40,8),
    five5_prin_m_avg NUMERIC(40,8),
    five5_prin_q_avg NUMERIC(40,8),
    five5_prin_y_avg NUMERIC(40,8),
    five_npl_bal NUMERIC(40,8),
    five_npl_bal_m_accum NUMERIC(40,8),
    five_npl_bal_q_accum NUMERIC(40,8),
    five_npl_bal_y_accum NUMERIC(40,8),
    five_npl_bal_m_avg NUMERIC(40,8),
    five_npl_bal_q_avg NUMERIC(40,8),
    five_npl_bal_y_avg NUMERIC(40,8),
    ori_dept_flag VARCHAR(5),
    ori_cust_mgr VARCHAR(100),
    pi_norm_prin_bal NUMERIC(40,8),
    pi_norm_prin_y_accum NUMERIC(40,8),
    pi_norm_prin_y_avg_bal NUMERIC(40,8),
    pi_norm_prin_y_wgt_accum NUMERIC(40,8),
    ovrd_less90_prin_bal NUMERIC(40,8),
    ovrd_less90_prin_y_avg_bal NUMERIC(40,8),
    ovrd_less90_prin_y_accum NUMERIC(40,8),
    ovrd_less90_prin_y_wgt_accum NUMERIC(40,8),
    ovrd_more90_prin_bal NUMERIC(40,8),
    ovrd_more90_prin_y_avg_bal NUMERIC(40,8),
    ovrd_more90_prin_y_accum NUMERIC(40,8),
    loan_bal_y_wgt_accum NUMERIC(40,8),
    int_amt1 NUMERIC(40,8),
    int_amt2 NUMERIC(40,8),
    actl_pi_amt NUMERIC(40,8),
    pi_norm_int1_amt NUMERIC(40,8),
    pi_norm_int2_amt NUMERIC(40,8),
    ovrd_less90_int1_amt NUMERIC(40,8),
    ovrd_less90_int2_amt NUMERIC(40,8),
    actl_int_amt NUMERIC(40,8),
    pi_norm_actl_int NUMERIC(40,8),
    ovrd_less90_actl_int NUMERIC(40,8),
    ibs_owe_int_amt NUMERIC(40,8),
    obs_owe_int_amt NUMERIC(40,8),
    inc_flag VARCHAR(20),
    crp_amt_d NUMERIC(40,8),
    cri_amt_d NUMERIC(40,8),
    ret_rapi_amt_d NUMERIC(40,8),
    ret_capi_amt_d NUMERIC(40,8),
    ret_rpi_amt_d NUMERIC(40,8),
    ret_cpi_amt_d NUMERIC(40,8),
    ret_rai_amt_d NUMERIC(40,8),
    ret_cai_amt_d NUMERIC(40,8),
    ret_ra_owe_int_d NUMERIC(40,8),
    ret_ca_owe_int_d NUMERIC(40,8),
    yj_ovrd_amt NUMERIC(40,8),
    indu_type_cd VARCHAR(40),
    st_own_ent_ind VARCHAR(20),
    holding_type_cd VARCHAR(40),
    sse_star_ind VARCHAR(20),
    mod_belong VARCHAR(8),
    jxb_fr_id VARCHAR(4),
    ztetl_dt VARCHAR(10),
    int_amt2_d NUMERIC(40,8),
    int_amt2_m_accum NUMERIC(40,8),
    int_amt2_q_accum NUMERIC(40,8)
);
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.data_dt IS '数据日期                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.legal_org_cd IS '法人机构编码              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.duebill_no IS '借据编号                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.cust_mgr_no IS '客户经理编号              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.cust_mgr_name IS '客户经理名称              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.cust_mgr_bel_dept_cd IS '客户经理所属部门编号      ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.cust_mgr_bel_org_cd IS '客户经理所属机构编号      ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.subj_no IS '科目编号                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.prod_no IS '产品编号                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ccy_cd IS '货币代码                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.contr_no IS '合同编号                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.guar_mode_cd IS '担保方式代码              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ent_scal_cd IS '企业规模代码              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.tech_corp_ind IS '科技企业标志              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.crdt_obj_class_cd IS '信贷对象分类代码          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.crdt_attr_class_cd IS '信贷经营属性分类代码      ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.crdt_biz_cate_cd IS '信贷业务种类代码          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ecif_cust_no IS '客户统一编号              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.cust_name IS '客户名称                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.titc_cust_id IS '两增两控客户标志          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.open_org_cd IS '开户机构编号              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.org_cd IS '内部机构编号              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.b_div_bal IS '分成前余额                ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.div_pct IS '分成比例                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.actl_y_intr IS '执行年利率                ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.actl_m_intr IS '执行月利率                ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.chrgoff_amt IS '核销金额                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.loan_bal IS '贷款余额                  ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.loan_bal_m_accum IS '贷款余额月积数            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.loan_bal_q_accum IS '贷款余额季积数            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.loan_bal_y_accum IS '贷款余额年积数            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.loan_bal_m_avg IS '贷款余额月日均            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.loan_bal_q_avg IS '贷款余额季日均            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.loan_bal_y_avg IS '贷款余额年日均            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_prin_bal IS '逾期本金余额              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_bal IS '正常本金余额              ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_m_accum IS '正常本金余额月积数        ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_q_accum IS '正常本金余额季积数        ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_y_accum IS '正常本金余额年积数        ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_m_avg IS '正常本金余额月日均        ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_q_avg IS '正常本金余额季日均        ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_y_avg IS '正常本金余额年日均        ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_wgt_bal IS '正常本金加权利息余额      ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_m_wgt_accum IS '正常本金加权利息余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_q_wgt_accum IS '正常本金加权利息余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_y_wgt_accum IS '正常本金加权利息余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_m_wgt_avg IS '正常本金加权利息余额月日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_q_wgt_avg IS '正常本金加权利息余额季日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.norm_prin_y_wgt_avg IS '正常本金加权利息余额年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five1_prin_bal IS '五级正常本金余额          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five1_prin_m_accum IS '五级正常本金余额月积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five1_prin_q_accum IS '五级正常本金余额季积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five1_prin_y_accum IS '五级正常本金余额年积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five1_prin_m_avg IS '五级正常本金余额月日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five1_prin_q_avg IS '五级正常本金余额季日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five1_prin_y_avg IS '五级正常本金余额年日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five2_prin_bal IS '五级关注本金余额          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five2_prin_m_accum IS '五级关注本金余额月积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five2_prin_q_accum IS '五级关注本金余额季积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five2_prin_y_accum IS '五级关注本金余额年积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five2_prin_m_avg IS '五级关注本金余额月日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five2_prin_q_avg IS '五级关注本金余额季日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five2_prin_y_avg IS '五级关注本金余额年日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five3_prin_bal IS '五级次级本金余额          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five3_prin_m_accum IS '五级次级本金余额月积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five3_prin_q_accum IS '五级次级本金余额季积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five3_prin_y_accum IS '五级次级本金余额年积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five3_prin_m_avg IS '五级次级本金余额月日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five3_prin_q_avg IS '五级次级本金余额季日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five3_prin_y_avg IS '五级次级本金余额年日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five4_prin_bal IS '五级可疑本金余额          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five4_prin_m_accum IS '五级可疑本金余额月积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five4_prin_q_accum IS '五级可疑本金余额季积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five4_prin_y_accum IS '五级可疑本金余额年积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five4_prin_m_avg IS '五级可疑本金余额月日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five4_prin_q_avg IS '五级可疑本金余额季日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five4_prin_y_avg IS '五级可疑本金余额年日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five5_prin_bal IS '五级损失本金余额          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five5_prin_m_accum IS '五级损失本金余额月积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five5_prin_q_accum IS '五级损失本金余额季积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five5_prin_y_accum IS '五级损失本金余额年积数    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five5_prin_m_avg IS '五级损失本金余额月日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five5_prin_q_avg IS '五级损失本金余额季日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five5_prin_y_avg IS '五级损失本金余额年日均    ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five_npl_bal IS '五级不良余额      ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five_npl_bal_m_accum IS '五级不良余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five_npl_bal_q_accum IS '五级不良余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five_npl_bal_y_accum IS '五级不良余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five_npl_bal_m_avg IS '五级不良余额月日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five_npl_bal_q_avg IS '五级不良余额季日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.five_npl_bal_y_avg IS '五级不良余额年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ori_dept_flag IS '原部门标志';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ori_cust_mgr IS '原客户经理编号';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.pi_norm_prin_bal IS '本息未逾期贷款余额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.pi_norm_prin_y_accum IS '本息未逾期贷款年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.pi_norm_prin_y_avg_bal IS '本息未逾期贷款年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.pi_norm_prin_y_wgt_accum IS '本息未逾期贷款年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_less90_prin_bal IS '逾期90天内贷款余额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_less90_prin_y_avg_bal IS '逾期90天内贷款年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_less90_prin_y_accum IS '逾期90天内贷款年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_less90_prin_y_wgt_accum IS '逾期90天内贷款年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_more90_prin_bal IS '逾期超90天贷款余额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_more90_prin_y_avg_bal IS '逾期超90天贷款年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_more90_prin_y_accum IS '逾期超90天贷款年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.loan_bal_y_wgt_accum IS '贷款余额年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.int_amt1 IS '贷款利息收入-本年累计税前';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.int_amt2 IS '贷款利息收入-本年累计税后';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.actl_pi_amt IS '实收罚息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.pi_norm_int1_amt IS '本息未逾期税前应计利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.pi_norm_int2_amt IS '本息未逾期税后应计利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_less90_int1_amt IS '逾期90天内税前应计利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_less90_int2_amt IS '逾期90天内税后应计利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.actl_int_amt IS '实收利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.pi_norm_actl_int IS '本息未逾期实收利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ovrd_less90_actl_int IS '逾期90天内实收利息';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ibs_owe_int_amt IS '表内欠息金额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.obs_owe_int_amt IS '表外欠息金额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.inc_flag IS '存量标记';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.crp_amt_d IS '核销收回本金当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.cri_amt_d IS '核销收回利息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ret_rapi_amt_d IS '归还应收应计罚息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ret_capi_amt_d IS '归还催收应计罚息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ret_rpi_amt_d IS '归还应收罚息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ret_cpi_amt_d IS '归还催收罚息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ret_rai_amt_d IS '归还应收应计利息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ret_cai_amt_d IS '归还催收应计利息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ret_ra_owe_int_d IS '归还应收欠息利息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.ret_ca_owe_int_d IS '归还催收欠息利息当年累计';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.yj_ovrd_amt IS '银监逾期金额';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.indu_type_cd IS '行业类型代码';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.st_own_ent_ind IS '国资企业标志';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.holding_type_cd IS '控股类型代码';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.sse_star_ind IS '科创企业标志';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.mod_belong IS '模型归属 01-零售 02-普惠';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.int_amt2_d IS '贷款利息收入-每日税后';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.int_amt2_m_accum IS '贷款利息收入-本月累计税后';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_d_crdt.int_amt2_q_accum IS '贷款利息收入-本季累计税后';

-- f_mid_index_result_dim_derive
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_index_result_dim_derive (
    data_dt VARCHAR(20),
    org_no VARCHAR(20),
    org_no_map VARCHAR(50),
    ccy VARCHAR(10),
    index_code VARCHAR(20),
    index_name VARCHAR(100),
    index_value NUMERIC(38,8),
    month_to_date NUMERIC(38,8),
    quarter_to_date NUMERIC(38,8),
    year_to_date NUMERIC(38,8),
    bus_dim_1 VARCHAR(50),
    bus_dim_2 VARCHAR(50),
    bus_dim_3 VARCHAR(50),
    bus_dim_4 VARCHAR(50),
    bus_dim_5 VARCHAR(50),
    bus_dim_6 VARCHAR(50),
    bus_dim_7 VARCHAR(50),
    bus_dim_8 VARCHAR(50),
    bus_dim_9 VARCHAR(50),
    bus_dim_10 VARCHAR(50),
    bus_dim_11 VARCHAR(50),
    bus_dim_12 VARCHAR(50),
    bus_dim_13 VARCHAR(50),
    bus_dim_14 VARCHAR(50),
    bus_dim_15 VARCHAR(50),
    bus_dim_exp VARCHAR(200),
    group_sign VARCHAR(10),
    ztetl_dt VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.data_dt IS '业务日期';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.org_no IS '机构';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.org_no_map IS '机构名称';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.ccy IS '币种';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.index_code IS '指标编码';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.index_name IS '指标名称';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.index_value IS '指标值';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.month_to_date IS '月累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.quarter_to_date IS '季累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.year_to_date IS '年累计';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_1 IS '业务维度1';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_2 IS '业务维度2';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_3 IS '业务维度3';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_4 IS '业务维度4';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_5 IS '业务维度5';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_6 IS '业务维度6';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_7 IS '业务维度7';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_8 IS '业务维度8';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_9 IS '业务维度9';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_10 IS '业务维度10';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_11 IS '业务维度11';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_12 IS '业务维度12';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_13 IS '业务维度13';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_14 IS '业务维度14';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_15 IS '业务维度15';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.bus_dim_exp IS '业务维度组合说明';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.group_sign IS '汇总标志(0是1否)';
COMMENT ON COLUMN fdmdata.f_mid_index_result_dim_derive.ztetl_dt IS '中台ETL日期';

-- s_sps_upss_corebkserial
CREATE TABLE IF NOT EXISTS sdmdata.s_sps_upss_corebkserial (
    appid VARCHAR(4),
    pltdate VARCHAR(8),
    pltnum VARCHAR(8),
    businum VARCHAR(36),
    sttlmbkid VARCHAR(14),
    srflg VARCHAR(1),
    sendbkid VARCHAR(14),
    wkdt VARCHAR(8),
    payseqno VARCHAR(8),
    txtpcd VARCHAR(5),
    txctgypurpcd VARCHAR(5),
    busitbtp VARCHAR(4),
    finlattr VARCHAR(5),
    transcode VARCHAR(10),
    provno VARCHAR(4),
    transdep VARCHAR(16),
    operator VARCHAR(8),
    payerbkid VARCHAR(14),
    payeraccno VARCHAR(32),
    payername VARCHAR(120),
    rcverbkid VARCHAR(14),
    rcveraccno VARCHAR(32),
    rcvername VARCHAR(120),
    amt NUMERIC(18,2),
    feeamt NUMERIC(18,2),
    postfeeamt NUMERIC(18,2),
    corebksts VARCHAR(2),
    corebkrspcd VARCHAR(8),
    corebkrspmsg VARCHAR(120),
    corebkdt VARCHAR(8),
    corebknum VARCHAR(16),
    corebkvchno VARCHAR(12),
    chkcorebksts VARCHAR(2),
    bkchkflg VARCHAR(1),
    oripltdate VARCHAR(8),
    oripltnum VARCHAR(8),
    oritrstatus VARCHAR(3),
    sysdt VARCHAR(8),
    systm VARCHAR(6),
    subaccno VARCHAR(20),
    accttp VARCHAR(4),
    mkinfo1 VARCHAR(20),
    mkinfo2 VARCHAR(60),
    mkinfo3 VARCHAR(120),
    mkinfo4 VARCHAR(20),
    mkinfo5 VARCHAR(60),
    mkinfo6 VARCHAR(120),
    mkinfo7 VARCHAR(60),
    mkinfo8 VARCHAR(60),
    mkinfo9 VARCHAR(4),
    mkinfo10 VARCHAR(10),
    createts VARCHAR(255),
    updatets VARCHAR(255),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.appid IS 'hvps大额，beps小额';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.pltdate IS '与人行工作日期保持一致';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.pltnum IS '平台流水号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.businum IS '业务受理编号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.sttlmbkid IS '清算行行号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.srflg IS '0-往账 1-来账';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.sendbkid IS '发起行行号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.wkdt IS '委托日期';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.payseqno IS '大额为报文标识号；小额普通业务是明细标识号后8位';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.txtpcd IS '业务类型编码，见取值范围';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.txctgypurpcd IS '业务种类编码，见取值范围';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.busitbtp IS '业务表类型，10分';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.finlattr IS '第1位表示记账性质:
a-正交易
b-实时冲正交易
c-抹账/取消交易
d-超时交易冲正(用于实时借记来账记账超时场景)
第2~3位表示交易步点
第4位记账类型
第5位借贷标志 D-借(汇出),C-贷(汇入)
';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.transcode IS '交易代码';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.provno IS '省市代码';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.transdep IS '交易机构';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.operator IS '操作员';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.payerbkid IS '付款人开户行行号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.payeraccno IS '付款人账号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.payername IS ' 对应人行同名';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.rcverbkid IS '收款人开户行行号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.rcveraccno IS '收款人账号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.rcvername IS '收款人名称 对应人行同名';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.amt IS '金额';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.feeamt IS '手续费';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.postfeeamt IS '邮电费';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.corebksts IS '第1位0表示成功；1表示失败；2表示反向；3表示超时；9表示正在处理中；第2位充许扩充
00-成功,
10-失败,
20-冲正,
21-撤销,
30-超时,
99-正在处理中
原正交易流水若被冲正或撤销时需更改原正交易流水主机状态为冲正或撤销。';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.corebkrspcd IS '主机响应码';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.corebkrspmsg IS '主机响应信息';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.corebkdt IS '主机日期';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.corebknum IS '主机流水号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.corebkvchno IS '主机传票号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.chkcorebksts IS '对账后根据主机流水产生的主机状态';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.bkchkflg IS '0-未对账,1-对平,2-主机多,3-平台多;5-金额不符';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.oripltdate IS '冗余';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.oripltnum IS '冗余';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.oritrstatus IS '原交易状态----反向交易时必须要填';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.sysdt IS '数据录入时的机器日期';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.systm IS '机器时间';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.subaccno IS '子账户序号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.accttp IS '账户类型';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo1 IS '交易代码';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo2 IS '全局流水号';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo3 IS '记账摘要码';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo4 IS '备用字段4';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo5 IS '备用字段5';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo6 IS '备用字段6';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo7 IS '备用字段7';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo8 IS '备用字段8';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo9 IS '备用字段9';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.mkinfo10 IS '备用字段10';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.createts IS 'sysdate';
COMMENT ON COLUMN sdmdata.s_sps_upss_corebkserial.updatets IS 'sysdate';

-- s_plm_credit_online_jf
CREATE TABLE IF NOT EXISTS sdmdata.s_plm_credit_online_jf (
    bankid NUMERIC(19),
    cifid VARCHAR(128),
    cliname VARCHAR(256),
    certtype VARCHAR(8),
    certno VARCHAR(128),
    pre_quota NUMERIC(16,2),
    real_quota NUMERIC(16,2),
    rate_val NUMERIC(11,6),
    loan_term NUMERIC(6),
    prdt_no VARCHAR(16),
    repay_type VARCHAR(32),
    status VARCHAR(32),
    limit_period NUMERIC(6),
    is_entrust VARCHAR(8),
    is_cic VARCHAR(8),
    is_prepayment VARCHAR(8),
    phone VARCHAR(32),
    effective_date_f VARCHAR(10),
    effective_date_n VARCHAR(10),
    freeze_date_n VARCHAR(10),
    expiry_date_n VARCHAR(10),
    refuse_date_n VARCHAR(10),
    applyno VARCHAR(128),
    modno VARCHAR(128),
    bdate VARCHAR(32),
    recommend_operid VARCHAR(32),
    recommend_date VARCHAR(32),
    orgnature VARCHAR(8),
    channelno VARCHAR(32),
    operid VARCHAR(12),
    operbrno VARCHAR(12),
    operdate VARCHAR(12),
    salary_flg VARCHAR(2),
    credit_agreement_no VARCHAR(32),
    reltype VARCHAR(128),
    industry VARCHAR(32),
    oper_type VARCHAR(32),
    sub_no VARCHAR(64),
    sub_applyno VARCHAR(64),
    purpose VARCHAR(32),
    manage_operid_lvl VARCHAR(8),
    is_transfer VARCHAR(10),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    xb_rate NUMERIC(9,6),
    depaccna VARCHAR(128),
    depacc_no VARCHAR(128),
    reppriacna VARCHAR(128),
    reppriac_no VARCHAR(128),
    freeze_quota VARCHAR(32),
    is_force_risk VARCHAR(8),
    is_stock_credit VARCHAR(8)
);
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.bankid IS '银行实体号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.cifid IS '员工客户号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.cliname IS '员工姓名';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.certtype IS '证件类型';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.certno IS '证件号码';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.pre_quota IS '预先贷款额度';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.real_quota IS '贷款额度';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.rate_val IS '贷款利率';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.loan_term IS '贷款期限';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.prdt_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.repay_type IS '还款方式';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.status IS '状态10待生效20生效30冻结40失效50拒绝';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.limit_period IS '额度期限';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.is_entrust IS '是否受托支付 0否 1是';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.is_cic IS '是否循环 0否 1是';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.is_prepayment IS '是否可提前还款 0否 1是';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.phone IS '手机号码';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.effective_date_f IS '首次授信日期';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.effective_date_n IS '授信生效日期';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.freeze_date_n IS '最新冻结日期';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.expiry_date_n IS '授信终止日期';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.refuse_date_n IS '最新拒绝日期';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.applyno IS '申请流水号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.modno IS '模型编号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.bdate IS '预授信日期';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.recommend_operid IS '推荐客户经理';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.recommend_date IS '推荐日期';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.orgnature IS '客户类别 10-个体工商户(无字号) 20-小微业主 99-其他';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.channelno IS '渠道号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.operid IS '申请人';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.operbrno IS '请机构';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.operdate IS '申请日期';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.salary_flg IS '产品类型 01-经营性 02-非经营性';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.credit_agreement_no IS '额度协议号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.reltype IS '担保方式 30-保证  50-信用';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.industry IS '贷款投向';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.oper_type IS '付息方式5-月6-季7-半年';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.sub_no IS '子额度流水号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.sub_applyno IS '子额度申请号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.purpose IS '贷款用途';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.manage_operid_lvl IS '客户经理等级';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.is_transfer IS '是否移交业务';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.xb_rate IS '信保保费费率';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.depaccna IS '放款行';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.depacc_no IS '放款账号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.reppriacna IS '还款行';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.reppriac_no IS '还款账号';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.freeze_quota IS '冻结金额';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.is_force_risk IS '风控准入能否强制通过';
COMMENT ON COLUMN sdmdata.s_plm_credit_online_jf.is_stock_credit IS '是否存量额度(二十万合同改造202409)';

-- s_ods_g_b_dep_acct_amt
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_dep_acct_amt (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    dep_acct_no VARCHAR(100),
    ccy_cd VARCHAR(40),
    ccy_ident_cd VARCHAR(40),
    orig_ccy_ind VARCHAR(20),
    prin_subj_no VARCHAR(40),
    open_dt DATE,
    open_acct_amt NUMERIC(38,8),
    agt_limt_amt NUMERIC(38,8),
    frz_amt NUMERIC(38,8),
    ctrl_amt NUMERIC(38,8),
    cnv_long_sus_amt NUMERIC(38,8),
    close_int_amt NUMERIC(38,8),
    acct_bal NUMERIC(38,8),
    acct_ld_bal NUMERIC(38,8),
    acct_lme_bal NUMERIC(38,8),
    acct_lqe_bal NUMERIC(38,8),
    acct_lye_bal NUMERIC(38,8),
    acct_lysme_bal NUMERIC(38,8),
    acct_m_accum NUMERIC(38,8),
    acct_q_accum NUMERIC(38,8),
    acct_y_accum NUMERIC(38,8),
    acct_m_wgt_accum NUMERIC(38,8),
    acct_q_wgt_accum NUMERIC(38,8),
    acct_y_wgt_accum NUMERIC(38,8),
    std_m_avg_bal NUMERIC(38,8),
    std_q_avg_bal NUMERIC(38,8),
    std_y_avg_bal NUMERIC(38,8),
    actl_m_avg_bal NUMERIC(38,8),
    actl_q_avg_bal NUMERIC(38,8),
    actl_y_avg_bal NUMERIC(38,8),
    eve_paid_int_amt NUMERIC(38,8),
    d_payb_int_amt NUMERIC(38,8),
    payb_int_amt NUMERIC(38,8),
    paid_int_amt NUMERIC(38,8),
    int_tax_amt NUMERIC(38,8),
    wait_draw_int_amt NUMERIC(38,8),
    int_adv_amt NUMERIC(38,8),
    src_sys_cd VARCHAR(100),
    etl_dt DATE,
    zyew_amt NUMERIC(17,2),
    y_payb_int_amt NUMERIC(38,8),
    acct_lye_avg NUMERIC(38,8),
    y_paid_int_amt NUMERIC(38,8),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    d_payb_int_m_accum NUMERIC(40,8),
    d_payb_int_q_accum NUMERIC(40,8),
    d_payb_int_y_accum NUMERIC(40,8)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.dep_acct_no IS '存款账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.ccy_ident_cd IS '钞汇类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.orig_ccy_ind IS '原币标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.prin_subj_no IS '本金科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.open_dt IS '开户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.open_acct_amt IS '开户金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.agt_limt_amt IS '协定额度金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.frz_amt IS '冻结金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.ctrl_amt IS '控制金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.cnv_long_sus_amt IS '已转久悬金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.close_int_amt IS '销户利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_bal IS '账户余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_ld_bal IS '账户上日余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_lme_bal IS '账户上月末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_lqe_bal IS '账户上季末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_lye_bal IS '账户上年末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_lysme_bal IS '账户上年同期月末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_m_accum IS '账户余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_q_accum IS '账户余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_y_accum IS '账户余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_m_wgt_accum IS '账户余额月加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_q_wgt_accum IS '账户余额季加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.acct_y_wgt_accum IS '账户余额年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.std_m_avg_bal IS '标准月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.std_q_avg_bal IS '标准季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.std_y_avg_bal IS '标准年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.actl_m_avg_bal IS '实际月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.actl_q_avg_bal IS '实际季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.actl_y_avg_bal IS '实际年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.eve_paid_int_amt IS '每日已付利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.d_payb_int_amt IS '当日应付利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.payb_int_amt IS '应付利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.paid_int_amt IS '已付利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.int_tax_amt IS '利息税金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.wait_draw_int_amt IS '待支取利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.int_adv_amt IS '利息前置金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.y_paid_int_amt IS '本年已付利息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.d_payb_int_m_accum IS '当日应付利息-本月累计';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.d_payb_int_q_accum IS '当日应付利息-本季累计';
COMMENT ON COLUMN sdmdata.s_ods_g_b_dep_acct_amt.d_payb_int_y_accum IS '当日应付利息-本年累计';

-- s_ibk_device_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ibk_device_info (
    device_id VARCHAR(32),
    term_id VARCHAR(32),
    dept_id VARCHAR(32),
    type_id VARCHAR(32),
    brand_id VARCHAR(32),
    model_id VARCHAR(32),
    term_seq VARCHAR(40),
    counter_code VARCHAR(40),
    term_ip VARCHAR(40),
    status VARCHAR(10),
    term_name VARCHAR(100),
    term_addr VARCHAR(200),
    post VARCHAR(100),
    install_date VARCHAR(32),
    active_date VARCHAR(32),
    service_type VARCHAR(20),
    install_type VARCHAR(20),
    layout_type VARCHAR(20),
    man_id VARCHAR(32),
    serviceman_id VARCHAR(32),
    company_id VARCHAR(32),
    company_name VARCHAR(200),
    service_begindate VARCHAR(32),
    service_enddate VARCHAR(32),
    service_years VARCHAR(10),
    is_cctv VARCHAR(10),
    is_ups VARCHAR(10),
    is_international VARCHAR(10),
    business_begintime VARCHAR(20),
    business_endtime VARCHAR(20),
    is_vip VARCHAR(10),
    area_id VARCHAR(32),
    area_addr VARCHAR(32),
    function_type VARCHAR(32),
    longitude VARCHAR(32),
    latitude VARCHAR(32),
    auditing VARCHAR(10),
    current_ip VARCHAR(32),
    version_atmc VARCHAR(100),
    version_sp VARCHAR(100),
    version_agent VARCHAR(100),
    version_mb VARCHAR(100),
    flag_xfs VARCHAR(10),
    flag_ej VARCHAR(10),
    flag_fsn VARCHAR(10),
    ej_files VARCHAR(200),
    fsn_path VARCHAR(200),
    task_para VARCHAR(100),
    version_ad VARCHAR(100),
    modify_userid VARCHAR(200),
    modify_date VARCHAR(6),
    add_userid VARCHAR(200),
    add_date VARCHAR(6),
    asset_no VARCHAR(40),
    cash_box_num VARCHAR(40),
    service_sms_type VARCHAR(2),
    ej_open_date VARCHAR(32),
    acquire_code VARCHAR(32),
    inst_code VARCHAR(32),
    master_key VARCHAR(32),
    pin_key VARCHAR(32),
    mac_key VARCHAR(32),
    term_mac VARCHAR(32),
    virtual_teller_id VARCHAR(32),
    dept_code VARCHAR(32),
    dep_vir_teller VARCHAR(32),
    cwd_vir_teller VARCHAR(32),
    merchid VARCHAR(32),
    legal_person_number VARCHAR(50),
    revert_dept_id VARCHAR(32),
    jxb_fr_id VARCHAR(3),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ibk_device_info.device_id IS '主键ID';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.term_id IS '终端编号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.dept_id IS '机构编号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.type_id IS '设备类型';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.brand_id IS '设备品牌';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.model_id IS '设备型号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.term_seq IS '设备序列号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.counter_code IS '柜员号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.term_ip IS '终端IP';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.status IS '管理状态';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.term_name IS '终端名称';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.term_addr IS '安装地址';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.post IS '地址邮编';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.install_date IS '安装日期';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.active_date IS '开通时间';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.service_type IS '布放模式';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.install_type IS '安装方式';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.layout_type IS '设立形式';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.man_id IS '管机员id';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.serviceman_id IS '维护人员id';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.company_id IS '服务商id';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.company_name IS '服务商名称';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.service_begindate IS '维护开始日期';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.service_enddate IS '维护到期日期';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.service_years IS '维护年限';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.is_cctv IS '是否视频监控';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.is_ups IS '是否安装UPS';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.is_international IS '是否受理国际卡';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.business_begintime IS '营业开始时间';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.business_endtime IS '营业结束时间';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.is_vip IS '是否是VIP机器';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.area_id IS '所属区域';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.area_addr IS '设备投放地域';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.function_type IS '设备功能区域';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.longitude IS 'ATM经度';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.latitude IS 'ATM纬度';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.auditing IS 'agent状态';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.current_ip IS '当前Ip';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.version_atmc IS 'ATMC/RCC版本号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.version_sp IS 'SP/DSP版本号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.version_agent IS 'Agent版本号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.version_mb IS '主板/介质版本号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.flag_xfs IS 'XFS报文开启状态';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.flag_ej IS 'EJ上传开启状态:0.不上传，1.上传失败暂停服务，2.上传';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.flag_fsn IS 'FSN上传开启状态:0.关闭，1.开启';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.ej_files IS '电子流水的文件样式';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.fsn_path IS '冠字号的文件样式';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.task_para IS 'task para in XML format';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.version_ad IS 'AD版本号/n';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.modify_userid IS '修改人';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.modify_date IS '修改时间';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.add_userid IS '添加人';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.add_date IS '添加时间';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.asset_no IS '资产编号/r';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.cash_box_num IS '缺钞阀值(张数),取款箱/循环箱总张数低于该阀值则告警';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.service_sms_type IS '维护短信模式 0：默认 1：市区 2：郊区';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.ej_open_date IS 'EJ开启时间 格式yyyy-MM-dd';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.acquire_code IS '受理机构号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.inst_code IS '发送机构号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.master_key IS '主密钥';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.pin_key IS 'PIN密钥';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.mac_key IS 'MAC密钥';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.term_mac IS '设备MAC';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.virtual_teller_id IS '尾箱号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.dept_code IS '终端编号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.dep_vir_teller IS '存款虚拟柜员号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.cwd_vir_teller IS '取款虚拟柜员号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.merchid IS '商户id';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.legal_person_number IS '法人编号';
COMMENT ON COLUMN sdmdata.s_ibk_device_info.revert_dept_id IS '设备归属机构编号';

-- s_ibk_igaps_business_log
CREATE TABLE IF NOT EXISTS sdmdata.s_ibk_igaps_business_log (
    bussiness_sn VARCHAR(128),
    term_code VARCHAR(50),
    dept_id VARCHAR(50),
    customer_name VARCHAR(50),
    id_card VARCHAR(50),
    counter_code VARCHAR(100),
    gaps_date DATE,
    gaps_time VARCHAR(255),
    business_type VARCHAR(50),
    resp_code VARCHAR(50),
    resp_msg VARCHAR(400),
    image_index_no VARCHAR(50),
    remark VARCHAR(100),
    backup_field0 VARCHAR(50),
    backup_field1 VARCHAR(50),
    backup_field2 VARCHAR(50),
    backup_field3 VARCHAR(50),
    backup_field4 VARCHAR(50),
    business_params VARCHAR(200),
    image_supplementary_scanning VARCHAR(1),
    update_time DATE,
    customer_no VARCHAR(50),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.bussiness_sn IS '业务交易流水、该字段唯一G开头的流水号';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.term_code IS '终端号';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.dept_id IS '机构号';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.customer_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.id_card IS '身份证';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.counter_code IS '柜员号';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.gaps_date IS '交易日期，年月日';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.gaps_time IS '交易时间，年月日时分秒';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.business_type IS '业务类型';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.resp_code IS '成功或失败的响应码';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.resp_msg IS '成功或失败的响应信息';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.image_index_no IS '影像索引号';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.remark IS '备注';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.backup_field0 IS '备用字段0';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.backup_field1 IS '备用字段1';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.backup_field2 IS '备用字段2';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.backup_field3 IS '备用字段3';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.backup_field4 IS '备用字段4';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.business_params IS '业务参数(交易参数)';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.image_supplementary_scanning IS '是否影像补扫（0表示未补扫，1是已补扫）';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.update_time IS '更新时间';
COMMENT ON COLUMN sdmdata.s_ibk_igaps_business_log.customer_no IS '客户号';

-- s_hrp_emp_employee_all_h
CREATE TABLE IF NOT EXISTS sdmdata.s_hrp_emp_employee_all_h (
    legal_org_cd VARCHAR(20),
    emp_no VARCHAR(40),
    emp_name VARCHAR(100),
    org_cd VARCHAR(20),
    dept_no VARCHAR(40),
    post_no VARCHAR(40),
    cert_type VARCHAR(20),
    id_no VARCHAR(40),
    sex_cd VARCHAR(40),
    edu_deg_cd VARCHAR(40),
    contact_tel_no VARCHAR(100),
    duty_lvl_cd VARCHAR(40),
    post_months INTEGER,
    emp_cate_cd VARCHAR(40),
    emp_sts_cd VARCHAR(40),
    canv_cd VARCHAR(40),
    rela_cd VARCHAR(40),
    marriag VARCHAR(40),
    childstatus VARCHAR(40),
    childs INTEGER,
    compyears INTEGER,
    workyears INTEGER,
    titlelevel VARCHAR(40),
    bank_no VARCHAR(20),
    jobtype INTEGER,
    sc_cd VARCHAR(50),
    danwei_no VARCHAR(20),
    bumen_no VARCHAR(20),
    zuimoji_no VARCHAR(20),
    suoshuyewu_team_no VARCHAR(20),
    job_dt DATE,
    renyuanpaixu_no VARCHAR(50),
    guoji VARCHAR(50),
    yuangong_ph VARCHAR(100),
    list_lungang_dt DATE,
    list_qiangxiu_dt DATE,
    ruzhi_dt VARCHAR(20),
    xulie VARCHAR(200),
    zixulie VARCHAR(200),
    ruzhilujing_laiyuan VARCHAR(200),
    yonggongzhuangtai VARCHAR(200),
    ruzhi_dt_hangling NUMERIC(2),
    lizhi_dt_zengjianyuan VARCHAR(200),
    job_dt_gongling NUMERIC(2),
    nianling NUMERIC(3),
    xueli VARCHAR(200),
    jxb_fr_id VARCHAR(5),
    start_dt DATE,
    end_dt DATE,
    regulatory_approval_dt VARCHAR(300),
    employment_dt VARCHAR(300),
    part_full_time VARCHAR(200),
    email VARCHAR(200),
    pay_grade_1 VARCHAR(8),
    pay_grade_2 VARCHAR(8),
    certificate VARCHAR(800)
);
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.emp_no IS '员工编号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.emp_name IS '员工姓名';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.dept_no IS '所属部门编码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.post_no IS '岗位编号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.cert_type IS '证件类型';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.id_no IS '身份证号码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.sex_cd IS '性别代码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.edu_deg_cd IS '学历代码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.contact_tel_no IS '联系电话号码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.duty_lvl_cd IS '职务级别代码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.post_months IS '岗位月数';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.emp_cate_cd IS '员工类别代码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.emp_sts_cd IS '员工状态代码';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.canv_cd IS '揽储机构';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.rela_cd IS '是否关联方';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.marriag IS '婚姻状况';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.childstatus IS '生育状况';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.childs IS '子女情况(个数)';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.compyears IS '行龄';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.workyears IS '工龄';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.titlelevel IS '职称';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.bank_no IS '员工卡号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.jobtype IS '岗位类别';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.sc_cd IS '所属经营机构';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.danwei_no IS '单位编号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.bumen_no IS '部门编号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.zuimoji_no IS '最末级编号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.suoshuyewu_team_no IS '所属业务团队编号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.job_dt IS '任现岗位时间';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.renyuanpaixu_no IS '人员排序号';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.guoji IS '国籍';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.yuangong_ph IS '员工照片';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.list_lungang_dt IS '最后一次轮岗时间';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.list_qiangxiu_dt IS '最后一次强休时间';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.ruzhi_dt IS '入职时间';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.xulie IS '序列';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.zixulie IS '子序列';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.ruzhilujing_laiyuan IS '入职路径（招聘来源）';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.yonggongzhuangtai IS '用工状态（人员状态）';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.ruzhi_dt_hangling IS '入职时间（行龄）';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.lizhi_dt_zengjianyuan IS '离职时间（增减员时间）';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.job_dt_gongling IS '工作年限（工龄）';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.nianling IS '年龄';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.xueli IS '学历';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.regulatory_approval_dt IS '监管批复时间';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.employment_dt IS '任职时间';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.part_full_time IS '学历性质';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.email IS '邮箱';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.pay_grade_1 IS '薪级';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.pay_grade_2 IS '薪档';
COMMENT ON COLUMN sdmdata.s_hrp_emp_employee_all_h.certificate IS '证书';

-- f_mid_khfl_a017_h
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_khfl_a017_h (
    rel_col VARCHAR(50),
    dim_val VARCHAR(50),
    sum_flag VARCHAR(50),
    ztetl_dt DATE,
    legal_org_cd VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_khfl_a017_h.rel_col IS '关联字段(客户号)';
COMMENT ON COLUMN fdmdata.f_mid_khfl_a017_h.dim_val IS '维度值';
COMMENT ON COLUMN fdmdata.f_mid_khfl_a017_h.sum_flag IS '汇总标志';
COMMENT ON COLUMN fdmdata.f_mid_khfl_a017_h.ztetl_dt IS '中台跑批日期';
COMMENT ON COLUMN fdmdata.f_mid_khfl_a017_h.legal_org_cd IS '法人机构编码';

-- s_ods_g_b_crd_debit_card
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_crd_debit_card (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    card_no VARCHAR(100),
    prim_card_no VARCHAR(100),
    org_cd VARCHAR(20),
    ecif_cust_no VARCHAR(40),
    prod_no VARCHAR(20),
    card_assc_cd VARCHAR(40),
    card_kind_char_cd VARCHAR(40),
    card_kind_class_cd VARCHAR(40),
    card_kind_lvl_cd VARCHAR(40),
    hold_passbk_ind VARCHAR(20),
    card_medium_type_cd VARCHAR(40),
    issue_card_obj_cd VARCHAR(40),
    card_ccy_type_cd VARCHAR(40),
    card_ident_type_cd VARCHAR(40),
    card_lvl_cd VARCHAR(40),
    issue_chnl_cd VARCHAR(40),
    joint_card_ind VARCHAR(20),
    emp_card_ind VARCHAR(20),
    intl_card_ind VARCHAR(20),
    aio_card_ind VARCHAR(20),
    ssc_ind VARCHAR(20),
    msc_ind VARCHAR(20),
    sal_card_ind VARCHAR(20),
    ctzn_card_ind VARCHAR(20),
    free_fee_type_cd VARCHAR(40),
    fin_ic_std_type_cd VARCHAR(40),
    fin_ic_use_mode_cd VARCHAR(40),
    apply_dt DATE,
    apply_org_no VARCHAR(100),
    apply_loc_adm_div_cd VARCHAR(40),
    issue_card_dt DATE,
    issue_card_org_no VARCHAR(100),
    issue_card_tlr_no VARCHAR(100),
    issue_card_mode_cd VARCHAR(40),
    issue_card_contact_name VARCHAR(400),
    eff_dt DATE,
    cancel_card_dt DATE,
    cancel_card_org_no VARCHAR(100),
    cancel_card_tlr_no VARCHAR(100),
    card_sts_cd VARCHAR(40),
    acct_bal NUMERIC(38,8),
    acct_ld_bal NUMERIC(38,8),
    acct_lme_bal NUMERIC(38,8),
    acct_lqe_bal NUMERIC(38,8),
    acct_lye_bal NUMERIC(38,8),
    acct_lysme_bal NUMERIC(38,8),
    acct_m_accum NUMERIC(38,8),
    acct_q_accum NUMERIC(38,8),
    acct_y_accum NUMERIC(38,8),
    acct_m_wgt_accum NUMERIC(38,8),
    acct_q_wgt_accum NUMERIC(38,8),
    acct_y_wgt_accum NUMERIC(38,8),
    std_m_avg_bal NUMERIC(38,8),
    std_q_avg_bal NUMERIC(38,8),
    std_y_avg_bal NUMERIC(38,8),
    actl_m_avg_bal NUMERIC(38,8),
    actl_q_avg_bal NUMERIC(38,8),
    actl_y_avg_bal NUMERIC(38,8),
    src_sys_cd VARCHAR(20),
    etl_dt DATE,
    card_biz_type_cd VARCHAR(40),
    batch_not_act_months INTEGER,
    payer_acct_name VARCHAR(4000),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_no IS '卡号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.prim_card_no IS '主卡卡号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.prod_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_assc_cd IS '发卡组织代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_kind_char_cd IS '卡种性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_kind_class_cd IS '卡种类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_kind_lvl_cd IS '卡种等级代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.hold_passbk_ind IS '有折标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_medium_type_cd IS '卡介质类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.issue_card_obj_cd IS '发卡对象代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_ccy_type_cd IS '卡币种类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_ident_type_cd IS '卡面标识类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_lvl_cd IS '卡级别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.issue_chnl_cd IS '发卡渠道代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.joint_card_ind IS '联名卡标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.emp_card_ind IS '员工卡标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.intl_card_ind IS '国际卡标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.aio_card_ind IS '一卡通标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.ssc_ind IS '社会保障卡标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.msc_ind IS '军人保障卡标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.sal_card_ind IS '工资卡标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.ctzn_card_ind IS '市民卡标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.free_fee_type_cd IS '免缴费用类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.fin_ic_std_type_cd IS '金融IC卡标准类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.fin_ic_use_mode_cd IS '金融IC卡使用方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.apply_dt IS '申请日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.apply_org_no IS '申请机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.apply_loc_adm_div_cd IS '卡申请地行政区划代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.issue_card_dt IS '发卡日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.issue_card_org_no IS '发卡机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.issue_card_tlr_no IS '发卡柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.issue_card_mode_cd IS '发卡方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.issue_card_contact_name IS '发卡联系人名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.eff_dt IS '有效日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.cancel_card_dt IS '销卡日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.cancel_card_org_no IS '销卡机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.cancel_card_tlr_no IS '销卡柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_sts_cd IS '卡片状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_bal IS '账户余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_ld_bal IS '账户上日余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_lme_bal IS '账户上月末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_lqe_bal IS '账户上季末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_lye_bal IS '账户上年末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_lysme_bal IS '账户上年同期月末余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_m_accum IS '账户余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_q_accum IS '账户余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_y_accum IS '账户余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_m_wgt_accum IS '账户余额月加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_q_wgt_accum IS '账户余额季加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.acct_y_wgt_accum IS '账户余额年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.std_m_avg_bal IS '标准月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.std_q_avg_bal IS '标准季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.std_y_avg_bal IS '标准年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.actl_m_avg_bal IS '实际月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.actl_q_avg_bal IS '实际季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.actl_y_avg_bal IS '实际年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.card_biz_type_cd IS '卡业务类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.batch_not_act_months IS '批量未激活月数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_crd_debit_card.payer_acct_name IS '代发单位名称';

-- s_cyq_cbps_maintransdtl
CREATE TABLE IF NOT EXISTS sdmdata.s_cyq_cbps_maintransdtl (
    workdate VARCHAR(8),
    agentserialno VARCHAR(33),
    sysid VARCHAR(6),
    worktime VARCHAR(6),
    agentflag VARCHAR(8),
    acchost VARCHAR(1),
    priority VARCHAR(4),
    bustype VARCHAR(6),
    bussubtype VARCHAR(12),
    transcode VARCHAR(20),
    mbflag VARCHAR(1),
    dcflag VARCHAR(1),
    channelcode VARCHAR(4),
    channeldate VARCHAR(8),
    channeltime VARCHAR(9),
    channelseq VARCHAR(30),
    accbrno VARCHAR(12),
    brno VARCHAR(12),
    tellerno VARCHAR(12),
    chktellerno VARCHAR(12),
    authtellerno VARCHAR(12),
    sendtellerno VARCHAR(12),
    terminalno VARCHAR(30),
    transflag VARCHAR(1),
    accclass VARCHAR(4),
    crflag VARCHAR(1),
    clearaccseq VARCHAR(20),
    currency VARCHAR(3),
    amount VARCHAR(18),
    realamount VARCHAR(18),
    feeflag VARCHAR(3),
    feecode VARCHAR(8),
    feeamount VARCHAR(18),
    cbpsfeeamount VARCHAR(18),
    postscript VARCHAR(270),
    ptcid VARCHAR(64),
    entrustdate VARCHAR(8),
    busseqno VARCHAR(8),
    msgid VARCHAR(16),
    sendbank VARCHAR(14),
    sendbankname VARCHAR(280),
    sendsettlebank VARCHAR(14),
    payeropnbank VARCHAR(14),
    payeropnname VARCHAR(280),
    payerbank VARCHAR(14),
    payersettlebank VARCHAR(14),
    payeracc VARCHAR(32),
    payername VARCHAR(180),
    payeraddr VARCHAR(240),
    recvbank VARCHAR(14),
    recvbankname VARCHAR(280),
    recvsettlebank VARCHAR(14),
    payeeopnbank VARCHAR(14),
    payeeopnname VARCHAR(280),
    payeebank VARCHAR(14),
    payeesettlebank VARCHAR(14),
    payeeacc VARCHAR(32),
    payeename VARCHAR(180),
    payeeaddr VARCHAR(240),
    idtype VARCHAR(3),
    idno VARCHAR(30),
    rspstatus VARCHAR(10),
    rspcode VARCHAR(10),
    rspmsg VARCHAR(1000),
    tradestep VARCHAR(2),
    tradestatus VARCHAR(2),
    status VARCHAR(2),
    preworkdate VARCHAR(8),
    preagentserialno VARCHAR(33),
    printcnt VARCHAR(2),
    authtp VARCHAR(4),
    cleardate VARCHAR(8),
    msgtype VARCHAR(20),
    sendtime VARCHAR(14),
    remark VARCHAR(270),
    realtype VARCHAR(4),
    realacc VARCHAR(32),
    realname VARCHAR(120),
    chkflag VARCHAR(1),
    note1 VARCHAR(30),
    note2 VARCHAR(180),
    note3 VARCHAR(50),
    note4 VARCHAR(100),
    note5 VARCHAR(300),
    globalseqno VARCHAR(32),
    payertype VARCHAR(4),
    payeetype VARCHAR(4),
    agentmodel VARCHAR(2),
    agentname VARCHAR(200),
    agentidentype VARCHAR(6),
    agentidentnumber VARCHAR(60),
    agentaddress VARCHAR(60),
    agentphone VARCHAR(30),
    payeridentno VARCHAR(60),
    payerphone VARCHAR(30),
    payeridentype VARCHAR(6),
    payeeidentype VARCHAR(6),
    payeeidentno VARCHAR(60),
    payeephone VARCHAR(30),
    prooftype VARCHAR(4),
    prooflotnum VARCHAR(35),
    proofordernum VARCHAR(35),
    proofdate VARCHAR(10),
    recefee VARCHAR(18),
    actualfee VARCHAR(18),
    clearflag VARCHAR(1),
    notifyflag VARCHAR(2),
    consignacc VARCHAR(32),
    frzno VARCHAR(32),
    acgsrlno VARCHAR(32),
    etl_dt DATE
);
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.workdate IS '平台受理日期';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.agentserialno IS '平台业务流水号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.sysid IS '系统标识(CBPS-城银清算)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.worktime IS '交易时间';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.agentflag IS '业务标识(01-汇兑,02-通存通兑,03-实时借贷记,04-即时转账)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.acchost IS '账户所属系统(0-传统核心,,1-现金管理,2-银数,3-通联,4-电子账户)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.priority IS '业务优先级(NORM-普通,URGT-加急,HIGH-特急)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.bustype IS '业务类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.bussubtype IS '业务种类';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.transcode IS '交易代码';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.mbflag IS '来往账标志(0-往,1-来)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.dcflag IS '借贷方标识(D-借,C-贷)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.channelcode IS '发起渠道';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.channeldate IS '发起渠道日期';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.channeltime IS '发起渠道时间';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.channelseq IS '发起渠道流水号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.accbrno IS '账户所属网点';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.brno IS '操作网点';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.tellerno IS '操作柜员';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.chktellerno IS '复核柜员';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.authtellerno IS '授权柜员';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.sendtellerno IS '发送柜员';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.terminalno IS '操作终端号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.transflag IS '现转标志(1-转账,2-待销账)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.accclass IS '账号类别(0-对公,1-卡,2-活期一本通,9-内部户)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.crflag IS '钞汇标志(0-钞户,1-汇户)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.clearaccseq IS '账号序号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.currency IS '交易币种(行内)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.amount IS '交易金额';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.realamount IS '实际交易金额';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.feeflag IS '手续费收取标志(0-现金,1-转账,2-不收费,3-集中收取)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.feecode IS '费用代码（手续费）';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.feeamount IS '手续费金额';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.cbpsfeeamount IS '跨行手续费金额';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.postscript IS '业务附言';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.ptcid IS '协议号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.entrustdate IS '委托日期';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.busseqno IS '支付交易序号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.msgid IS '报文标识号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.sendbank IS '发起行行号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.sendbankname IS '发起行行名';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.sendsettlebank IS '发起清算行号行号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeropnbank IS '付款人开户行';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeropnname IS '付款人开户行行名';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payerbank IS '付款行行号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payersettlebank IS '付款清算行行号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeracc IS '付款人账号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payername IS '付款人名称';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeraddr IS '付款人地址';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.recvbank IS '接收行行号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.recvbankname IS '接收行行名';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.recvsettlebank IS '接收清算行行号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeeopnbank IS '收款人开户行';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeeopnname IS '收款人开户行行名';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeebank IS '收款行行号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeesettlebank IS '收款清算行行号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeeacc IS '收款账号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeename IS '收款人名称';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeeaddr IS '收款人地址';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.idtype IS '证件类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.idno IS '证件号码';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.rspstatus IS '第三方业务处理状态';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.rspcode IS '第三方处理码';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.rspmsg IS '第三方处理信息';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.tradestep IS '交易步数';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.tradestatus IS '处理状态(00-待处理,10-待复核,11-待授权,12-待发送,13-待回执,20-发送中,21-已发送,30-回执中,31-已回执,40-已宕账,41-已入账,42-已退回,43-已退汇,44-已重发,45-已完成,46-已冲正)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.status IS '业务状态(10-受理,20-在途,30-确认,00-成功,99-失败)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.preworkdate IS '原业务平台受理日期';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.preagentserialno IS '原业务平台业务流水号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.printcnt IS '打印次数';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.authtp IS '认证方式';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.cleardate IS '清算日期';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.msgtype IS '报文类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.sendtime IS '报文发送时间';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.remark IS '备注';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.realtype IS '实际账户类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.realacc IS '实际账号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.realname IS '实际账号户名';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.chkflag IS '对账标志(9-初始,0-不符,1-相符)';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.note1 IS '备用1';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.note2 IS '备用2';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.note3 IS '备用3';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.note4 IS '备用4';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.note5 IS '备用5';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.globalseqno IS '全局流水号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payertype IS '付款账户类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeetype IS '收款账户类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.agentmodel IS '代理人模式';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.agentname IS '代理人名称';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.agentidentype IS '代理人证件类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.agentidentnumber IS '代理人证件号码';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.agentaddress IS '代理人地址';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.agentphone IS '代理人电话';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeridentno IS '付款人证件号码';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payerphone IS '付款人电话';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeridentype IS '付款人证件类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeeidentype IS '收款人证件类型';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeeidentno IS '收款人证件号码';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.payeephone IS '收款人电话';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.prooftype IS '凭证种类';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.prooflotnum IS '凭证批号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.proofordernum IS '凭证序号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.proofdate IS '凭证日期';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.recefee IS '应收手续费';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.actualfee IS '实收手续费';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.clearflag IS '清算标志1-已清算0-未清算';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.notifyflag IS '通知渠道标识0-未通知1-已通知';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.consignacc IS '代销账户';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.frzno IS '冻结编号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.acgsrlno IS '渠道记账流水号';
COMMENT ON COLUMN sdmdata.s_cyq_cbps_maintransdtl.etl_dt IS '数据日期';

-- s_ibp_ibps_pay_trans_reg
CREATE TABLE IF NOT EXISTS sdmdata.s_ibp_ibps_pay_trans_reg (
    wkdt VARCHAR(12),
    businum VARCHAR(64),
    userid VARCHAR(60),
    payfg VARCHAR(4),
    srflag VARCHAR(1),
    orgsnder VARCHAR(35),
    orgrcver VARCHAR(35),
    msgtp VARCHAR(35),
    msgid VARCHAR(64),
    credttm VARCHAR(20),
    payseqno VARCHAR(36),
    endtoendid VARCHAR(64),
    txtpcd VARCHAR(10),
    txctgypurpcd VARCHAR(10),
    channelid VARCHAR(16),
    channelseq VARCHAR(64),
    transcode VARCHAR(12),
    provno VARCHAR(4),
    orgno VARCHAR(20),
    inputoper VARCHAR(16),
    checkoper VARCHAR(16),
    auther VARCHAR(16),
    paysttlbkid VARCHAR(35),
    rcvsttlbkid VARCHAR(35),
    payerbkid VARCHAR(35),
    payerbknm VARCHAR(140),
    payeraccttp VARCHAR(4),
    payeracctno VARCHAR(35),
    payername VARCHAR(200),
    payercitycd VARCHAR(6),
    rcverbkid VARCHAR(35),
    rcverbknm VARCHAR(140),
    rcveraccttp VARCHAR(4),
    rcveracctno VARCHAR(35),
    rcvername VARCHAR(120),
    rcvercitycd VARCHAR(6),
    rlrcverbkid VARCHAR(35),
    rcversttlmaccttp VARCHAR(4),
    rcversttlmacct VARCHAR(35),
    rcversttlmacctnm VARCHAR(120),
    authtp VARCHAR(64),
    authmsg VARCHAR(200),
    url VARCHAR(2048),
    authstnid VARCHAR(60),
    mrchntcd VARCHAR(35),
    mrchntnm VARCHAR(80),
    ctctdtlsnm VARCHAR(140),
    ccy VARCHAR(3),
    amt NUMERIC(18,2),
    thirdfeeamt NUMERIC(18,2),
    feeflagtransfer VARCHAR(3),
    feetflagcollect VARCHAR(3),
    feeamt NUMERIC(18,2),
    postfeeamt NUMERIC(18,2),
    unfee NUMERIC(18,2),
    feepayacctno VARCHAR(35),
    feebkid VARCHAR(14),
    ps VARCHAR(512),
    pltdate VARCHAR(8),
    pltnum VARCHAR(16),
    corebkdt VARCHAR(8),
    corebknum VARCHAR(64),
    accorgno VARCHAR(35),
    oribusinum VARCHAR(64),
    orimsgid VARCHAR(64),
    oriorgsnder VARCHAR(35),
    ansflag VARCHAR(1),
    ansmsgtp VARCHAR(35),
    ansmsgid VARCHAR(35),
    anscredttm VARCHAR(20),
    txrespsts VARCHAR(4),
    txresprjctcd VARCHAR(20),
    txresprjctinf VARCHAR(315),
    txnetgdt VARCHAR(12),
    txnetgtm VARCHAR(20),
    txnetgrnd VARCHAR(20),
    sttlmdt VARCHAR(12),
    txprccd VARCHAR(20),
    txrjctcd VARCHAR(20),
    txrjctinf VARCHAR(315),
    rjttxptyid VARCHAR(35),
    chksts VARCHAR(1),
    printnum VARCHAR(8),
    agentbkflg VARCHAR(1),
    sysdt VARCHAR(8),
    systm VARCHAR(6),
    respcode VARCHAR(20),
    respmsg VARCHAR(512),
    trstatus VARCHAR(3),
    steptrack VARCHAR(256),
    corebksts VARCHAR(4),
    txsts VARCHAR(4),
    refundamt NUMERIC(18,2),
    refundsts VARCHAR(1),
    cmkinfo VARCHAR(64),
    cmkinfo1 VARCHAR(64),
    cmkinfo2 VARCHAR(64),
    cmkinfo3 VARCHAR(16),
    cmkinfo4 VARCHAR(20),
    cmkinfo5 VARCHAR(20),
    cmkinfo6 VARCHAR(32),
    cmkinfo7 VARCHAR(256),
    hmkinfo VARCHAR(64),
    hmkinfo1 VARCHAR(16),
    hmkinfo2 VARCHAR(64),
    hmkinfo3 VARCHAR(128),
    hmkinfo4 VARCHAR(128),
    hmkinfo5 VARCHAR(128),
    hmkinfo6 VARCHAR(32),
    hmkinfo7 VARCHAR(256),
    etl_dt DATE,
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.wkdt IS '委托日期';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.businum IS '业务受理编号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.userid IS '本行客户号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.payfg IS '收付款标志（RF00-收款，RF01--付款，RF02--第三方）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.srflag IS '往来标识（0-往帐，1-来账）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.orgsnder IS '发起清算行';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.orgrcver IS '接收清算行';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.msgtp IS '报文类型';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.msgid IS '报文标识号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.credttm IS '报文发送时间';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.payseqno IS '支付交易序号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.endtoendid IS '端到端标识号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txtpcd IS '业务类型编码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txctgypurpcd IS '业务种类编码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.channelid IS '渠道标识';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.channelseq IS '渠道流水号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.transcode IS '交易代码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.provno IS '省市代码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.orgno IS '交易机构号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.inputoper IS '录入柜员';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.checkoper IS '复核柜员';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.auther IS '授权柜员';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.paysttlbkid IS '付款清算行';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcvsttlbkid IS '收款清算行';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.payerbkid IS '付款人开户行行号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.payerbknm IS '付款人开户行行名';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.payeraccttp IS '付款人账号类型（AT00-单位银行结算账户，AT01-个人借记卡（存折）账户，AT02-个人贷记卡账户）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.payeracctno IS '付款人账号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.payername IS '付款人账号名称';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.payercitycd IS '付款人城市代码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcverbkid IS '收款人开户行行号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcverbknm IS '收款人开户行行名';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcveraccttp IS '收款人账户类型（AT00-单位银行结算账户，AT01-个人借记卡（存折）账户，AT02-个人贷记卡账户）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcveracctno IS '收款人账号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcvername IS '收款人名称';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcvercitycd IS '收款人城市代码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rlrcverbkid IS '收款人实际开户行行号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcversttlmaccttp IS '收款人实际账号类型（AT00-单位银行结算账户，AT01-个人借记卡（存折）账户，AT02-个人贷记卡账户）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcversttlmacct IS '收款人实际账号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rcversttlmacctnm IS '收款人实际账号名称';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.authtp IS '认证方式（AC00-协议方式，AC01-线认证方式，AC02-动态密码方式）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.authmsg IS '认证信息';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.url IS '身份校验URL信息';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.authstnid IS '预授权号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.mrchntcd IS '商户编号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.mrchntnm IS '商户名称';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.ctctdtlsnm IS '订单详情';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.ccy IS '货币码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.amt IS '金额';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.thirdfeeamt IS '第三方手续费';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.feeflagtransfer IS '手续费收取方式（0-转帐，1-现金）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.feetflagcollect IS '手续费关联标识（0-关联，1-不关联）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.feeamt IS '手续费';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.postfeeamt IS '邮电费';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.unfee IS '优惠手续费';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.feepayacctno IS '手续费付款账号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.feebkid IS '手续费收取行号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.ps IS '附言';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.pltdate IS '平台日期';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.pltnum IS '平台流水号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.corebkdt IS '主机账务日期';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.corebknum IS '主机流水号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.accorgno IS '账户开户机构号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.oribusinum IS '原业务受理编号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.orimsgid IS '原报文标识号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.oriorgsnder IS '原发起清算行';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.ansflag IS '回执往来标志（0-往帐，1-来账）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.ansmsgtp IS '回执报文类型';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.ansmsgid IS '回执报文标识号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.anscredttm IS '回执时间';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txrespsts IS '业务回执状态（PR00-已转发，PR09-已拒绝，PR01-待认证）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txresprjctcd IS '业务回执拒绝码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txresprjctinf IS '业务回执拒绝信息';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txnetgdt IS '轧差日期';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txnetgtm IS '轧差时间';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txnetgrnd IS '轧差场次';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.sttlmdt IS '清算日期';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txprccd IS '业务处理码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txrjctcd IS '拒绝码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txrjctinf IS '业务拒绝信息';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.rjttxptyid IS '拒绝业务参与机构行号';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.chksts IS '对账处理标志（0-未对账，1-对平，2-需补账，3-需核销，4-需抹账，9-对账中）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.printnum IS '打印次数';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.agentbkflg IS '代理行标识';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.sysdt IS '机器日期';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.systm IS '机器时间';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.respcode IS '交易响应码';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.respmsg IS '交易响应信息';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.trstatus IS '交易状态';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.steptrack IS '步点轨迹';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.corebksts IS '主机状态（0-初始，1-成功，2-失败，3-结果未知，9-正在处理）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.txsts IS '业务状态（PR01-待认证，PR02-已付款，PR03-已轧差，PR04-已清算，PR08-已撤销，PR09-已拒绝，PR10-已确认）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.refundamt IS '已退金额（0-未退款，1-已退款，9-退款中）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.refundsts IS '退款状态（0-未退款，1-已退款，9-退款中）';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.cmkinfo IS '渠道接入预留标志集合位';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.cmkinfo1 IS '渠道预留1';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.cmkinfo2 IS '渠道预留2';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.cmkinfo3 IS '渠道预留3';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.cmkinfo4 IS '渠道预留4';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.cmkinfo5 IS '渠道预留5';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.cmkinfo6 IS '渠道预留6';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.cmkinfo7 IS '渠道预留字段集合';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.hmkinfo IS '更新预留标志集合位';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.hmkinfo1 IS '更新预留1';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.hmkinfo2 IS '更新预留2';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.hmkinfo3 IS '更新预留3';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.hmkinfo4 IS '更新预留4';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.hmkinfo5 IS '更新预留5';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.hmkinfo6 IS '更新预留6';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.hmkinfo7 IS '更新预留字段集合';
COMMENT ON COLUMN sdmdata.s_ibp_ibps_pay_trans_reg.etl_dt IS '数据日期';

-- s_ods_g_b_fin_invest_acct
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_fin_invest_acct (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    invest_fin_acct_no VARCHAR(100),
    prod_no VARCHAR(100),
    prod_name VARCHAR(1000),
    fin_acct_no VARCHAR(100),
    org_cd VARCHAR(20),
    ecif_cust_no VARCHAR(40),
    cust_name VARCHAR(1000),
    acct_cate_cd VARCHAR(40),
    cust_cate_cd VARCHAR(40),
    prod_type_cd VARCHAR(40),
    ccy_cd VARCHAR(40),
    ta_cd VARCHAR(40),
    ta_name VARCHAR(1000),
    cust_cap_acct_no VARCHAR(100),
    cust_cap_acct_sno VARCHAR(100),
    bank_acct_no VARCHAR(100),
    subj_no VARCHAR(100),
    contr_no VARCHAR(100),
    buy_cost_amt NUMERIC(40,8),
    hold_tot_shares NUMERIC(40,8),
    frz_tot_shares NUMERIC(40,8),
    cur_incm_amt NUMERIC(40,8),
    tot_incm_amt NUMERIC(40,8),
    unit_net_val_amt NUMERIC(18,10),
    acct_bal NUMERIC(40,8),
    acct_exch_usd_bal NUMERIC(40,8),
    acct_exch_rmb_bal NUMERIC(40,8),
    acct_m_accum NUMERIC(40,8),
    acct_q_accum NUMERIC(40,8),
    acct_y_accum NUMERIC(40,8),
    std_m_avg_bal NUMERIC(40,8),
    std_q_avg_bal NUMERIC(40,8),
    std_y_avg_bal NUMERIC(40,8),
    open_dt DATE,
    cur_pd_start_dt DATE,
    cur_pd_end_dt DATE,
    last_chg_dt DATE,
    cust_mgr_no VARCHAR(100),
    src_sys_cd VARCHAR(20),
    etl_dt DATE,
    status VARCHAR(2),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.invest_fin_acct_no IS '投资理财账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.prod_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.prod_name IS '产品名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.fin_acct_no IS '理财账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.cust_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.acct_cate_cd IS '账户类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.cust_cate_cd IS '客户类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.prod_type_cd IS '产品类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.ta_cd IS 'TA代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.ta_name IS 'TA名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.cust_cap_acct_no IS '客户资金账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.cust_cap_acct_sno IS '客户资金账户子序号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.bank_acct_no IS '银行入账账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.subj_no IS '内部科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.contr_no IS '合约编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.buy_cost_amt IS '买入成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.hold_tot_shares IS '持有份额总数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.frz_tot_shares IS '已冻结份额总数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.cur_incm_amt IS '本期收益金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.tot_incm_amt IS '累计收益金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.unit_net_val_amt IS '单位净值金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.acct_bal IS '账户余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.acct_exch_usd_bal IS '账户余额折美元';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.acct_exch_rmb_bal IS '账户余额折人民币';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.acct_m_accum IS '账户余额月积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.acct_q_accum IS '账户余额季积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.acct_y_accum IS '账户余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.std_m_avg_bal IS '标准月日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.std_q_avg_bal IS '标准季日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.std_y_avg_bal IS '标准年日均余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.open_dt IS '开户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.cur_pd_start_dt IS '本期起始日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.cur_pd_end_dt IS '本期到期日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.last_chg_dt IS '最后变动日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.cust_mgr_no IS '客户经理编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_fin_invest_acct.status IS '签约状态';

-- f_mid_payr_summary
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_payr_summary (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    sign_agt_no VARCHAR(200),
    cust_acct_no VARCHAR(100),
    ecif_cust_no VARCHAR(100),
    cust_name VARCHAR(400),
    sign_org VARCHAR(100),
    bndfje_wh NUMERIC(20,4),
    bndfje_th NUMERIC(20,4),
    payr_sum NUMERIC(20,4),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.data_dt IS '数据日期';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.sign_agt_no IS '签约协议号';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.cust_acct_no IS '客户账号';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.ecif_cust_no IS '代发单位客户编号';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.cust_name IS '代发单位客户名称';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.sign_org IS '签约机构';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.bndfje_wh IS '本年代发金额-我行';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.bndfje_th IS '本年代发金额-他行';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.payr_sum IS '本年代发次数';
COMMENT ON COLUMN fdmdata.f_mid_payr_summary.ztetl_dt IS '中台跑批时间';

-- s_ods_g_b_cif_merchant_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_cif_merchant_info (
    data_dt DATE,
    legal_org_cd VARCHAR(10),
    org_no VARCHAR(10),
    merchant_id NUMERIC(16),
    seller_name VARCHAR(120),
    seller_abbr VARCHAR(100),
    merchant_type_cd VARCHAR(10),
    seller_main_type VARCHAR(6),
    network_access_seller_type VARCHAR(2),
    ecif_cust_no VARCHAR(20),
    terminal_no VARCHAR(100),
    mcc VARCHAR(4),
    mcc_name VARCHAR(200),
    settle_type VARCHAR(1),
    settle_account_name VARCHAR(200),
    sellte_bank_name VARCHAR(200),
    settle_account_no VARCHAR(200),
    settle_account_mobile VARCHAR(200),
    create_time VARCHAR(10),
    modify_time VARCHAR(10),
    audit_state_time VARCHAR(10),
    merchant_state VARCHAR(10),
    audit_state VARCHAR(10),
    legal_name VARCHAR(20),
    legal_certificate_start VARCHAR(50),
    legal_certificate_end VARCHAR(50),
    legal_certificate_type VARCHAR(3),
    legal_certificate_no VARCHAR(50),
    org_num VARCHAR(200),
    business_license VARCHAR(200),
    business_license_end VARCHAR(50),
    business_license_start VARCHAR(50),
    enterprise_address VARCHAR(200),
    enterprise_district VARCHAR(50),
    seller_business_scope TEXT,
    merchant_web VARCHAR(100),
    enterprise_phone VARCHAR(20),
    register_address VARCHAR(200),
    register_area_cd VARCHAR(10),
    register_city_cd VARCHAR(10),
    register_district_cd VARCHAR(10),
    urban_type_cd VARCHAR(3),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.legal_org_cd IS '法人机构代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.org_no IS '内部机构号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.merchant_id IS '商户编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.seller_name IS '商户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.seller_abbr IS '商户简称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.merchant_type_cd IS '商户进件类型（1：POS 2：条码支付 3：线上收单，多种类型以;拼接）';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.seller_main_type IS '商户主体类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.network_access_seller_type IS '入网商户类型代码 10:网络特约商户 ，20：实体特约商户，30：实体兼实体特约商户';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.ecif_cust_no IS '客户号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.terminal_no IS '终端号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.mcc IS '商户mcc码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.mcc_name IS '商户mcc名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.settle_type IS '结算账户类型代码 1：对公，2：个人';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.settle_account_name IS '结算账户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.sellte_bank_name IS '结算银行名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.settle_account_no IS '结算账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.settle_account_mobile IS '结算账户预留电话号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.create_time IS '创建时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.modify_time IS '修改时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.audit_state_time IS '审核时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.merchant_state IS '商户状态 0:正常; 1:冻结(暂停收银)；2:清退(已删除)；3:注销(上报)；4:移入/移除黑名单(已删除)；5:暂停结算';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.audit_state IS '审核状态 10:待确认（保留）, 20:待审核, 30:待复核, 50:待抽查,  100:开户成功, -10:待修改（保留）, -20:审核拒绝, -30:复核拒绝, -50:抽查拒绝, -100:资料作废';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.legal_name IS '企业法人名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.legal_certificate_start IS '法人代表证件有效开始日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.legal_certificate_end IS '法人身份证有效期截止日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.legal_certificate_type IS '企业法人证件类型  1居民身份证，2军人或武警身份证件，21：中国人民武装警察身份证件，3外国公民护照，4其他类个人身份有效证件,5港澳台居民来往内地通行证 ，51：台湾居民来往大陆通行证';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.legal_certificate_no IS '企业法人代表身份证件号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.org_num IS '组织机构代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.business_license IS '营业执照号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.business_license_end IS '营业执照有效期截止日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.business_license_start IS '营业执照有效期起始日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.enterprise_address IS '企业经营地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.enterprise_district IS '营业地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.seller_business_scope IS '经营范围';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.merchant_web IS '商户官网地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.enterprise_phone IS '企业联系电话';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.register_address IS '企业注册地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.register_area_cd IS '注册省份代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.register_city_cd IS '注册城市代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.register_district_cd IS '注册地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_merchant_info.urban_type_cd IS '城乡代码类型';

-- s_cbs_kcab_xjmxtb
CREATE TABLE IF NOT EXISTS sdmdata.s_cbs_kcab_xjmxtb (
    farendma VARCHAR(4),
    jiaoyirq VARCHAR(8),
    zhujriqi VARCHAR(8),
    jiaoyisj NUMERIC(16),
    qtjiaoym VARCHAR(20),
    jiaoyima VARCHAR(20),
    jiaoyigy VARCHAR(8),
    shoqguiy VARCHAR(8),
    qudaoooo VARCHAR(7),
    guiylius VARCHAR(32),
    zhanghao VARCHAR(48),
    xjinzhlb VARCHAR(4),
    huobdaih VARCHAR(4),
    weixdhao VARCHAR(8),
    weixleib VARCHAR(2),
    xjinsfbz VARCHAR(1),
    jiaoyije NUMERIC(21,2),
    zhanghye NUMERIC(21,2),
    xjinfsbz VARCHAR(1),
    yngyjigo VARCHAR(12),
    zhngjigo VARCHAR(12),
    zhyyjigo VARCHAR(12),
    zhkjjigo VARCHAR(12),
    ruznzhbz VARCHAR(1),
    zhmxxhao NUMERIC(16),
    duifjgdh VARCHAR(12),
    duifguiy VARCHAR(8),
    duifgywx VARCHAR(8),
    duifwxlb VARCHAR(2),
    kehuzhao VARCHAR(48),
    moduleee VARCHAR(2),
    chanphao VARCHAR(10),
    yewuzlbh VARCHAR(500),
    xiaozxuh VARCHAR(48),
    pingzhma VARCHAR(32),
    paijiaaa NUMERIC(20,7),
    xjinxmdm VARCHAR(12),
    zhaiyodm VARCHAR(10),
    zhaiyoms VARCHAR(300),
    beizhuxx VARCHAR(300),
    yuangyls VARCHAR(32),
    yuanjyrq VARCHAR(8),
    chzbizhi VARCHAR(1),
    bchongbz VARCHAR(1),
    dayinbzz VARCHAR(1),
    dayincis NUMERIC(16),
    fenhbios VARCHAR(4),
    weihguiy VARCHAR(8),
    weihjigo VARCHAR(12),
    weihriqi VARCHAR(8),
    weihshij VARCHAR(9),
    shijchuo NUMERIC(16),
    jiluztai VARCHAR(1),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.farendma IS '法人代码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.jiaoyirq IS '交易日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhujriqi IS '主机日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.jiaoyisj IS '交易时间';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.qtjiaoym IS '前台交易码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.jiaoyima IS '交易码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.jiaoyigy IS '交易柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.shoqguiy IS '授权柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.qudaoooo IS '渠道';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.guiylius IS '柜员流水';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhanghao IS '账号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.xjinzhlb IS '现金账户类别';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.huobdaih IS '货币代号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.weixdhao IS '尾箱号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.weixleib IS '尾箱类别';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.xjinsfbz IS '现金收付标志(0-领用,1-上缴)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.jiaoyije IS '交易金额';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhanghye IS '账户余额';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.xjinfsbz IS '现金发生标志';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.yngyjigo IS '营业机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhngjigo IS '账务机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhyyjigo IS '账户营业机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhkjjigo IS '账户会计机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.ruznzhbz IS '入总账标志(1-是,0-否)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhmxxhao IS '账户明细序号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.duifjgdh IS '对方机构代号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.duifguiy IS '对方柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.duifgywx IS '对方柜员尾箱';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.duifwxlb IS '对方尾箱类别';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.kehuzhao IS '客户账号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.moduleee IS '模块';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.chanphao IS '产品号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.yewuzlbh IS '业务种类编号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.xiaozxuh IS '待销账序号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.pingzhma IS '凭证号码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.paijiaaa IS '牌价';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.xjinxmdm IS '现金项目代码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhaiyodm IS '摘要代码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.zhaiyoms IS '摘要描述';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.beizhuxx IS '备注信息';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.yuangyls IS '原柜员流水号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.yuanjyrq IS '原交易日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.chzbizhi IS '冲正标志(0-无关,1-当日冲正,2-隔日冲正)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.bchongbz IS '被冲正标志(0-无关,1-被冲正,2-冲正,3-被隔日冲正)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.dayinbzz IS '打印标志(0-未打印,1-已打印)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.dayincis IS '打印次数';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.fenhbios IS '分行标识';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.weihguiy IS '维护柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.weihjigo IS '维护机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.weihriqi IS '维护日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.weihshij IS '维护时间';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.shijchuo IS '时间戳';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjmxtb.jiluztai IS '记录状态(0-正常,1-删除)';

-- s_ods_g_b_cap_invest_acct
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_cap_invest_acct (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    invest_acct_no VARCHAR(250),
    init_invest_acct_no VARCHAR(100),
    org_cd VARCHAR(30),
    belong_dept_no VARCHAR(100),
    prod_no VARCHAR(100),
    ccy_cd VARCHAR(40),
    asset_biz_no VARCHAR(100),
    asset_biz_name VARCHAR(1000),
    cap_biz_type_cd VARCHAR(40),
    asset_liab_type_cd VARCHAR(40),
    fin_asset_3class_cd VARCHAR(40),
    fin_asset_4class_cd VARCHAR(40),
    tx_acct_type_cd VARCHAR(40),
    repo_tx_dir_cd VARCHAR(40),
    otc_tx_ind VARCHAR(20),
    mtch_tx_ind VARCHAR(20),
    acru_type_cd VARCHAR(40),
    intr_contr_no VARCHAR(100),
    biz_contr_no VARCHAR(100),
    open_dt DATE,
    posn_dt DATE,
    start_int_dt DATE,
    matr_dt DATE,
    rsdu_matr_days INTEGER,
    reprice_dt DATE,
    clr_dt DATE,
    close_dt DATE,
    prod_intr NUMERIC(18,10),
    actl_intr NUMERIC(18,10),
    repo_intr NUMERIC(18,10),
    face_val_amt NUMERIC(38,8),
    cost_subj_no VARCHAR(100),
    cost_amt NUMERIC(38,8),
    cost_m_accum NUMERIC(38,8),
    cost_q_accum NUMERIC(38,8),
    cost_y_accum NUMERIC(38,8),
    cost_m_wgt_accum NUMERIC(38,8),
    cost_q_wgt_accum NUMERIC(38,8),
    cost_y_wgt_accum NUMERIC(38,8),
    std_m_avg_cost_amt NUMERIC(38,8),
    std_q_avg_cost_amt NUMERIC(38,8),
    std_y_avg_cost_amt NUMERIC(38,8),
    actl_m_avg_cost_amt NUMERIC(38,8),
    actl_q_avg_cost_amt NUMERIC(38,8),
    actl_y_avg_cost_amt NUMERIC(38,8),
    recvb_int_subj_no VARCHAR(40),
    recvb_int_amt NUMERIC(38,8),
    acru_int_subj_no VARCHAR(100),
    acru_int_amt NUMERIC(38,8),
    eve_acru_int_amt NUMERIC(38,8),
    payb_int_subj_no VARCHAR(40),
    payb_int_amt NUMERIC(38,8),
    int_incm_subj_no VARCHAR(100),
    int_incm_amt NUMERIC(38,8),
    int_exp_subj_no VARCHAR(100),
    int_exp_amt NUMERIC(38,8),
    int_adj_subj_no VARCHAR(40),
    int_adj_amt NUMERIC(38,8),
    invest_incm_subj_no VARCHAR(100),
    invest_incm_amt NUMERIC(38,8),
    fair_val_adj_subj_no VARCHAR(100),
    fair_val_adj_amt NUMERIC(38,8),
    fair_val_adj_incm_subj_no VARCHAR(100),
    fair_val_adj_incm_amt NUMERIC(38,8),
    depr_rsrv_subj_no VARCHAR(40),
    depr_rsrv_amt NUMERIC(38,8),
    deval_loss_subj_no VARCHAR(40),
    deval_loss_amt NUMERIC(38,8),
    cntpty_cust_no VARCHAR(100),
    cntpty_name VARCHAR(1000),
    cntpty_acct_type_cd VARCHAR(40),
    cntpty_cate_cd VARCHAR(40),
    cntpty_char_cd VARCHAR(40),
    cntpty_nation_cd VARCHAR(40),
    cntpty_indu_cd VARCHAR(40),
    cntpty_corp_crdt_rating_cd VARCHAR(40),
    cntpty_corp_crdt_rating_org_name VARCHAR(1000),
    cntpty_open_cap_acct_no VARCHAR(100),
    cntpty_open_bank_name VARCHAR(1000),
    cntpty_open_bank_no VARCHAR(100),
    cntpty_cstn_acct_no VARCHAR(100),
    bank_stl_acct_no VARCHAR(100),
    bank_stl_org_pay_no VARCHAR(100),
    cntpty_stl_acct_no VARCHAR(100),
    cntpty_stl_org_pay_no VARCHAR(100),
    open_tlr_no VARCHAR(20),
    tx_tlr_no VARCHAR(20),
    check_tlr_no VARCHAR(20),
    acct_sts_cd VARCHAR(40),
    src_sys_cd VARCHAR(20),
    etl_dt DATE,
    cb_amt NUMERIC(38,8),
    int_pay_mode_cd VARCHAR(40),
    int_stl_freq_cd VARCHAR(40),
    cust_acct_no VARCHAR(100),
    sub_acct_seq VARCHAR(10),
    dom_for_ind VARCHAR(10),
    tx_org_name VARCHAR(32),
    cntpty_high_cust_no VARCHAR(100),
    cntpty_high_cust_name VARCHAR(200),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.invest_acct_no IS '投资账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.init_invest_acct_no IS '原投资账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.belong_dept_no IS '归属部门编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.prod_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.asset_biz_no IS '资产业务代号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.asset_biz_name IS '资产业务名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cap_biz_type_cd IS '资金业务类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.asset_liab_type_cd IS '资产负债类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.fin_asset_3class_cd IS '金融资产计量分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.fin_asset_4class_cd IS '金融资产四分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.tx_acct_type_cd IS '交易账户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.repo_tx_dir_cd IS '回购交易方向代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.otc_tx_ind IS '场外交易标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.mtch_tx_ind IS '撮合交易标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.acru_type_cd IS '计提类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.intr_contr_no IS '内部合同编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.biz_contr_no IS '业务合同编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.open_dt IS '开户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.posn_dt IS '持仓日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.start_int_dt IS '起息日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.matr_dt IS '到期日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.rsdu_matr_days IS '剩余期限天数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.reprice_dt IS '重定价日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.clr_dt IS '清算日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.close_dt IS '销户日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.prod_intr IS '产品利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.actl_intr IS '执行利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.repo_intr IS '回购利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.face_val_amt IS '面值金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cost_subj_no IS '成本科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cost_amt IS '成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cost_m_accum IS '成本金额月积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cost_q_accum IS '成本金额季积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cost_y_accum IS '成本金额年积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cost_m_wgt_accum IS '成本金额月加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cost_q_wgt_accum IS '成本金额季加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cost_y_wgt_accum IS '成本金额年加权积数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.std_m_avg_cost_amt IS '标准月日均成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.std_q_avg_cost_amt IS '标准季日均成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.std_y_avg_cost_amt IS '标准年日均成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.actl_m_avg_cost_amt IS '实际月日均成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.actl_q_avg_cost_amt IS '实际季日均成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.actl_y_avg_cost_amt IS '实际年日均成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.recvb_int_subj_no IS '应收利息科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.recvb_int_amt IS '应收利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.acru_int_subj_no IS '应计利息科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.acru_int_amt IS '应计利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.eve_acru_int_amt IS '每日计提利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.payb_int_subj_no IS '应付利息科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.payb_int_amt IS '应付利息金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.int_incm_subj_no IS '利息收入科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.int_incm_amt IS '利息收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.int_exp_subj_no IS '利息支出科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.int_exp_amt IS '利息支出金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.int_adj_subj_no IS '利息调整科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.int_adj_amt IS '利息调整金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.invest_incm_subj_no IS '投资损益科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.invest_incm_amt IS '投资损益金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.fair_val_adj_subj_no IS '公允价值变动科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.fair_val_adj_amt IS '公允价值变动金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.fair_val_adj_incm_subj_no IS '公允价值变动损益科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.fair_val_adj_incm_amt IS '公充价值变动损益金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.depr_rsrv_subj_no IS '减值准备科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.depr_rsrv_amt IS '减值准备金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.deval_loss_subj_no IS '减值损失科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.deval_loss_amt IS '减值损失金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_cust_no IS '交易对手客户编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_name IS '交易对手名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_acct_type_cd IS '交易对手会计类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_cate_cd IS '交易对手类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_char_cd IS '交易对手属性代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_nation_cd IS '交易对手国家代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_indu_cd IS '交易对手行业代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_corp_crdt_rating_cd IS '交易对手主体信用评级代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_corp_crdt_rating_org_name IS '交易对手主体信用评级机构名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_open_cap_acct_no IS '交易对手开户行资金账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_open_bank_name IS '交易对手开户行名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_open_bank_no IS '交易对手开户行行号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_cstn_acct_no IS '交易对手托管账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.bank_stl_acct_no IS '本行清算账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.bank_stl_org_pay_no IS '本行清算机构支付行号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_stl_acct_no IS '对方清算账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_stl_org_pay_no IS '对方清算机构支付行号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.open_tlr_no IS '开户柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.tx_tlr_no IS '交易柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.check_tlr_no IS '复核柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.acct_sts_cd IS '账户状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cb_amt IS '成本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.int_pay_mode_cd IS '利息支付方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.int_stl_freq_cd IS '结息频率代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cust_acct_no IS '客户账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.sub_acct_seq IS '子账号序列';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.dom_for_ind IS '境内外标志 (01-境内,02-境外)';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.tx_org_name IS '交易台名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_high_cust_no IS '交易对手上级主体客户号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cap_invest_acct.cntpty_high_cust_name IS '交易对手上级主体名称';

-- s_rrs_rd_g01
CREATE TABLE IF NOT EXISTS sdmdata.s_rrs_rd_g01 (
    ddate VARCHAR(10),
    bankid VARCHAR(20),
    rid VARCHAR(20),
    a NUMERIC(40,10),
    b NUMERIC(40,10),
    c NUMERIC(40,10),
    jxb_fr_id VARCHAR(3),
    ztetl_dt VARCHAR(10)
);

-- s_cbs_kcab_xjcrtb
CREATE TABLE IF NOT EXISTS sdmdata.s_cbs_kcab_xjcrtb (
    farendma VARCHAR(4),
    diocriqi DATE,
    diocjyls VARCHAR(40),
    xuhaoooo NUMERIC(21),
    yuanjyrq DATE,
    yuyuejgo VARCHAR(300),
    crkuczbz VARCHAR(300),
    yyjhleix VARCHAR(300),
    guiyzlei VARCHAR(300),
    yngyjigo VARCHAR(20),
    zhngjigo VARCHAR(300),
    huobdaih VARCHAR(4),
    xjinqnzh VARCHAR(300),
    weixdhao VARCHAR(40),
    weixleib VARCHAR(300),
    xjinsfbz VARCHAR(300),
    xjinfsbz VARCHAR(300),
    jiaoyije NUMERIC(21,2),
    zhanghao VARCHAR(48),
    duifjgdh VARCHAR(20),
    duifjgmc VARCHAR(300),
    xjinyybh VARCHAR(300),
    pingzhzl VARCHAR(300),
    pngzphao VARCHAR(40),
    pingzhma VARCHAR(300),
    peicguiy VARCHAR(300),
    peicjine NUMERIC(21,2),
    qtjiaoym VARCHAR(300),
    jiaoyima VARCHAR(20),
    jiaoyirq DATE,
    jiaoyisj NUMERIC(21),
    jiaoyigy VARCHAR(20),
    jiaoyijg VARCHAR(20),
    shoqguiy VARCHAR(300),
    guiylius VARCHAR(40),
    qudaoooo VARCHAR(20),
    scjyriqi DATE,
    xjincrzt VARCHAR(300),
    beizhuxx VARCHAR(4000),
    fenhbios VARCHAR(10),
    weihguiy VARCHAR(20),
    weihjigo VARCHAR(20),
    weihriqi DATE,
    weihshij VARCHAR(20),
    shijchuo NUMERIC(21),
    jiluztai VARCHAR(1),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.farendma IS '法人代码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.diocriqi IS '调出日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.diocjyls IS '调出柜员流水';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.xuhaoooo IS '序号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.yuanjyrq IS '原交易日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.yuyuejgo IS '预约机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.crkuczbz IS '出入库操作标志';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.yyjhleix IS '预约计划类型';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.guiyzlei IS '柜员种类';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.yngyjigo IS '营业机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.zhngjigo IS '账务机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.huobdaih IS '货币代号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.xjinqnzh IS '券种';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.weixdhao IS '尾箱号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.weixleib IS '尾箱类别';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.xjinsfbz IS '现金收付标志';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.xjinfsbz IS '现金发生标志';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.jiaoyije IS '交易金额';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.zhanghao IS '账号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.duifjgdh IS '对方机构代号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.duifjgmc IS '对方金融机构名称';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.xjinyybh IS '现金申请编号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.pingzhzl IS '凭证种类';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.pngzphao IS '凭证批号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.pingzhma IS '凭证号码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.peicguiy IS '配钞柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.peicjine IS '配钞金额';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.qtjiaoym IS '前台交易码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.jiaoyima IS '交易码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.jiaoyirq IS '交易日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.jiaoyisj IS '交易时间';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.jiaoyigy IS '交易柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.jiaoyijg IS '交易机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.shoqguiy IS '授权柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.guiylius IS '柜员流水';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.qudaoooo IS '渠道';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.scjyriqi IS '上次交易日';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.xjincrzt IS '现金出入状态';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.beizhuxx IS '备注信息';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.fenhbios IS '分行标识';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.weihguiy IS '维护柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.weihjigo IS '维护机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.weihriqi IS '维护日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.weihshij IS '维护时间';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.shijchuo IS '时间戳';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjcrtb.jiluztai IS '记录状态';

-- s_ods_g_b_cif_indiv_extend_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_cif_indiv_extend_info (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    ecif_cust_no VARCHAR(100),
    relg_cd VARCHAR(40),
    hlth_sts_cd VARCHAR(40),
    rsdt_situ_cd VARCHAR(40),
    city_rsdt_start_dt DATE,
    rsdt_years INTEGER,
    fmly_pop INTEGER,
    prim_incm_src VARCHAR(40),
    incm_ccy_cd VARCHAR(40),
    pers_mm_incm_amt NUMERIC(40,8),
    pers_annl_incm_amt NUMERIC(40,8),
    fmly_mm_incm_amt NUMERIC(40,8),
    fmly_annl_incm_amt NUMERIC(40,8),
    bank_emp_ind VARCHAR(20),
    bank_emp_no VARCHAR(100),
    farmers_ind VARCHAR(20),
    aml_rating_cd VARCHAR(40),
    soc_sec_situ VARCHAR(100),
    hobby_desc VARCHAR(400),
    vip_cust_ind VARCHAR(20),
    tax_rsdt_fmly_name VARCHAR(400),
    tax_rsdt_name VARCHAR(400),
    tax_rsdt_birth_dt DATE,
    tax_rsdt_living_cn_addr VARCHAR(400),
    tax_rsdt_living_en_addr VARCHAR(400),
    tax_rsdt_birth_nation_cd VARCHAR(40),
    tax_rsdt_birth_nation_name VARCHAR(400),
    pars_situ TEXT,
    pers_fin_asset_amt NUMERIC(40,8),
    fmly_fin_asset_amt NUMERIC(40,8),
    prim_relv_bank TEXT,
    prod_invest_exp TEXT,
    cur_hold_fin_prod_type TEXT,
    cur_hold_fin_prod_org TEXT,
    invest_term_pref VARCHAR(100),
    invest_risk_pref VARCHAR(100),
    veh_info VARCHAR(100),
    hold_house_nums INTEGER,
    house_info VARCHAR(100),
    use_alipay_or_wechat_ind VARCHAR(20),
    info_get_mode_cd VARCHAR(40),
    othr_econ_src TEXT,
    ident_cerf_mode_cd VARCHAR(40),
    ident_cerf_rslt_cd VARCHAR(40),
    unable_verf_rsn_cd VARCHAR(40),
    disp_mode_cd VARCHAR(40),
    get_cert_doc_ind VARCHAR(20),
    compt_org TEXT,
    bank_duty_cd VARCHAR(40),
    hold_card_situ_cd VARCHAR(40),
    fgn_passport_rsdt_ind VARCHAR(20),
    crdt_farmers_ind VARCHAR(20),
    adm_award_list_ind VARCHAR(20),
    adm_penalty_list_ind VARCHAR(20),
    arrs_post_pay_biz_list_ind VARCHAR(20),
    civil_judge_list_ind VARCHAR(20),
    enforce_list_ind VARCHAR(20),
    min_living_allow_list_ind VARCHAR(20),
    tax_owed_list_ind VARCHAR(20),
    recv_list_ind VARCHAR(20),
    cust_crdt_stat_class_cd VARCHAR(40),
    gop_sts_cd VARCHAR(40),
    ecif_cre_dttm VARCHAR(255),
    ecif_upd_dttm VARCHAR(255),
    cre_src_sys_cd VARCHAR(40),
    src_sys_cre_dttm VARCHAR(255),
    last_upd_dttm VARCHAR(255),
    last_upd_org_cd VARCHAR(20),
    last_upd_tlr_no VARCHAR(20),
    last_upd_sys_cd VARCHAR(40),
    etl_dt DATE,
    tax_addr_type VARCHAR(20),
    tax_city VARCHAR(300),
    tax_area_ch VARCHAR(20),
    tax_addr_nation VARCHAR(20),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.relg_cd IS '宗教信仰代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.hlth_sts_cd IS '健康状况代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.rsdt_situ_cd IS '居住状况代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.city_rsdt_start_dt IS '本城市居住起始日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.rsdt_years IS '居住年限';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.fmly_pop IS '家庭人口';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.prim_incm_src IS '主要收入来源代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.incm_ccy_cd IS '收入货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.pers_mm_incm_amt IS '个人月收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.pers_annl_incm_amt IS '个人年收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.fmly_mm_incm_amt IS '家庭月收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.fmly_annl_incm_amt IS '家庭年收入金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.bank_emp_ind IS '本行员工标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.bank_emp_no IS '本行员工号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.farmers_ind IS '是否农户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.aml_rating_cd IS '反洗钱评级代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.soc_sec_situ IS '社会保障情况';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.hobby_desc IS '兴趣爱好';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.vip_cust_ind IS '是否VIP客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_rsdt_fmly_name IS '税收居民-姓(英文或拼音)';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_rsdt_name IS '税收居民-名(英文或拼音)';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_rsdt_birth_dt IS '税收居民-出生日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_rsdt_living_cn_addr IS '税收居民-现居地址(中文)';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_rsdt_living_en_addr IS '税收居民-现居地址(英文)';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_rsdt_birth_nation_cd IS '税收居民-出生国家地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_rsdt_birth_nation_name IS '税收居民-出生国家地区名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.pars_situ IS '父母状况';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.pers_fin_asset_amt IS '个人金融资产金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.fmly_fin_asset_amt IS '家庭金融资产金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.prim_relv_bank IS '主要往来银行';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.prod_invest_exp IS '产品投资经历';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.cur_hold_fin_prod_type IS '当前持有金融产品类型';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.cur_hold_fin_prod_org IS '当前持有金融产品机构';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.invest_term_pref IS '投资期限偏好';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.invest_risk_pref IS '投资风险偏好';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.veh_info IS '车辆信息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.hold_house_nums IS '持有住房套数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.house_info IS '房屋信息';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.use_alipay_or_wechat_ind IS '使用支付宝或微信支付标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.info_get_mode_cd IS '信息获取方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.othr_econ_src IS '其它经济来源';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.ident_cerf_mode_cd IS '身份核验方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.ident_cerf_rslt_cd IS '身份核实结果代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.unable_verf_rsn_cd IS '无法核实原因代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.disp_mode_cd IS '处置方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.get_cert_doc_ind IS '是否取得证明文件标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.compt_org IS '主管机构';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.bank_duty_cd IS '本行职务代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.hold_card_situ_cd IS '持卡情况代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.fgn_passport_rsdt_ind IS '是否拥有外国护照或居住权标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.crdt_farmers_ind IS '是否为信用户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.adm_award_list_ind IS '行政奖励记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.adm_penalty_list_ind IS '行政处罚记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.arrs_post_pay_biz_list_ind IS '后付费业务欠费记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.civil_judge_list_ind IS '民事判决记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.enforce_list_ind IS '强制执行记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.min_living_allow_list_ind IS '低保救助记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_owed_list_ind IS '欠税记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.recv_list_ind IS '被追偿记录标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.cust_crdt_stat_class_cd IS '客户信贷统计分类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.gop_sts_cd IS '脱贫状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.ecif_cre_dttm IS 'ECIF创建时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.ecif_upd_dttm IS 'ECIF更新时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.cre_src_sys_cd IS '创建源系统代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.src_sys_cre_dttm IS '源系统创建时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.last_upd_dttm IS '最近更新时间戳';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.last_upd_org_cd IS '最近更新机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.last_upd_tlr_no IS '最近更新柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.last_upd_sys_cd IS '最近更新系统代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_addr_type IS '税收居民-地址类型';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_city IS '税收居民-英文所在城市';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_area_ch IS '税收居民-中文-行政区划';
COMMENT ON COLUMN sdmdata.s_ods_g_b_cif_indiv_extend_info.tax_addr_nation IS '税收居民-国家代码';

-- s_nnt_efs_sys_loginfo2
CREATE TABLE IF NOT EXISTS sdmdata.s_nnt_efs_sys_loginfo2 (
    trxdate VARCHAR(8),
    trxserno VARCHAR(32),
    trxtime VARCHAR(9),
    zoneno VARCHAR(8),
    brno VARCHAR(16),
    tlrno VARCHAR(16),
    trxno VARCHAR(16),
    custserno VARCHAR(16),
    imgserno VARCHAR(128),
    tskserno VARCHAR(32),
    vouchtype VARCHAR(4),
    vouchno VARCHAR(32),
    caccno VARCHAR(32),
    ccurr VARCHAR(3),
    camt VARCHAR(24),
    daccno VARCHAR(32),
    dcurr VARCHAR(3),
    damt VARCHAR(24),
    trxnote VARCHAR(2048),
    retstatus VARCHAR(1),
    retcode VARCHAR(16),
    retmsg VARCHAR(512),
    revretstatus VARCHAR(1),
    revtrxserno VARCHAR(32),
    note1 VARCHAR(10),
    note2 VARCHAR(20),
    note3 VARCHAR(30),
    note4 VARCHAR(40),
    note5 VARCHAR(50),
    note6 VARCHAR(60),
    ip VARCHAR(128),
    endtime VARCHAR(9),
    uuid VARCHAR(64),
    etl_dt DATE,
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.trxdate IS '交易日期';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.trxserno IS '前端交易流水号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.trxtime IS '交易时间(HHMMSSNNN)';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.zoneno IS '地区代码';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.brno IS '机构号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.tlrno IS '柜员代码';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.trxno IS '交易代码';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.custserno IS '客户流水号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.imgserno IS '影像索引号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.tskserno IS '任务流水号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.vouchtype IS '凭证类型';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.vouchno IS '凭证号码';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.caccno IS '贷方账卡号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.ccurr IS '贷方币种';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.camt IS '贷方金额';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.daccno IS '借方账卡号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.dcurr IS '借方币种';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.damt IS '借方金额';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.trxnote IS '交易备注';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.retstatus IS '处理状态 0-失败、2-异常、1-成功';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.retcode IS '返回代码';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.retmsg IS '返回信息';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.revretstatus IS '冲正处理标志 1.是 0.否 2.异常';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.revtrxserno IS '冲正流水号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.note1 IS '备注1';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.note2 IS '备注2';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.note3 IS '备注3';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.note4 IS '备注4';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.note5 IS '备注5';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.note6 IS '备注6';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.ip IS '服务端IP';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.endtime IS '交易结束时间(HHMMSSNNN)';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.uuid IS '交易唯一标识，相当于全局流水号';
COMMENT ON COLUMN sdmdata.s_nnt_efs_sys_loginfo2.etl_dt IS 'ETL日期';

-- s_ods_g_b_tx_fin_evt
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_tx_fin_evt (
    tx_dt DATE,
    legal_org_cd VARCHAR(20),
    tx_serl_no VARCHAR(100),
    prod_evt_sn INTEGER,
    extr_serl_no VARCHAR(100),
    glbl_serl_no VARCHAR(100),
    msg_serl_no VARCHAR(100),
    tx_org_cd VARCHAR(100),
    tx_org_adm_div_cd VARCHAR(40),
    acct_org_no VARCHAR(100),
    cust_acc_ind VARCHAR(20),
    tx_tm VARCHAR(20),
    init_acct_dt DATE,
    init_tx_serl_no VARCHAR(100),
    extr_dt DATE,
    oc_acct_type_cd VARCHAR(40),
    biz_type_cd VARCHAR(40),
    prod_no VARCHAR(100),
    prod_name VARCHAR(1000),
    tx_cd VARCHAR(40),
    tx_name VARCHAR(400),
    extr_tx_cd VARCHAR(100),
    extr_tx_name VARCHAR(400),
    acct_no VARCHAR(100),
    cust_acct_no VARCHAR(100),
    acct_sn INTEGER,
    acct_type_cd VARCHAR(40),
    subj_no VARCHAR(100),
    dc_cd VARCHAR(40),
    dccy_ind VARCHAR(20),
    ccy_cd VARCHAR(40),
    ccy_ident_cd VARCHAR(40),
    acct_amt NUMERIC(40,8),
    cust_acct_bal NUMERIC(40,8),
    acct_exch_usd_amt NUMERIC(40,8),
    acct_exch_rmb_amt NUMERIC(40,8),
    exch_mode_cd VARCHAR(40),
    relv_acc_ind VARCHAR(20),
    incm_pay_type_cd VARCHAR(40),
    abstract_cd VARCHAR(40),
    abstract_desc TEXT,
    cash_xfer_type_cd VARCHAR(40),
    rev_wipe_cd VARCHAR(20),
    batch_ind VARCHAR(20),
    obs_biz_ind VARCHAR(20),
    inter_bank_ind VARCHAR(20),
    vchr_type_cd VARCHAR(40),
    vchr_no VARCHAR(100),
    tx_chnl_cd VARCHAR(40),
    pay_org_id VARCHAR(100),
    pay_org_name VARCHAR(600),
    pay_tx_type_cd VARCHAR(40),
    pay_biz_kind_cd VARCHAR(40),
    clr_ident_cd VARCHAR(40),
    clr_mtch_no_type_cd VARCHAR(40),
    clr_mtch_no VARCHAR(200),
    tx_trml_type_cd VARCHAR(40),
    tx_trml_no VARCHAR(100),
    tx_ip_addr VARCHAR(100),
    dev_mac_addr VARCHAR(100),
    cash_item_cd VARCHAR(40),
    fx_pay_tx_cd VARCHAR(40),
    tx_place_nation_cd VARCHAR(40),
    tx_place_adm_div_cd VARCHAR(40),
    xborder_tx_ind VARCHAR(20),
    tx_to_nation_cd VARCHAR(40),
    tx_to_adm_div_cd VARCHAR(40),
    fin_org_tx_rel_cd VARCHAR(40),
    ecif_cust_no VARCHAR(100),
    cust_type_cd VARCHAR(40),
    cust_name VARCHAR(1000),
    cert_type_cd VARCHAR(40),
    cert_no VARCHAR(100),
    card_type_cd VARCHAR(40),
    tx_init_sys_no VARCHAR(40),
    init_org_no VARCHAR(200),
    cntpty_acct_no VARCHAR(100),
    cntpty_acct_type_cd VARCHAR(40),
    cntpty_name VARCHAR(1000),
    cntpty_cust_type_cd VARCHAR(40),
    cntpty_ecif_cust_no VARCHAR(100),
    cntpty_bank_cust_ind VARCHAR(20),
    cntpty_cert_type_cd VARCHAR(40),
    cntpty_cert_no VARCHAR(100),
    cntpty_fin_org_cd VARCHAR(100),
    cntpty_fin_org_name VARCHAR(400),
    cntpty_fin_org_type_cd VARCHAR(40),
    cntpty_clr_bank_no VARCHAR(200),
    cntpty_clr_bank_name VARCHAR(1000),
    cntpty_fin_org_nation_cd VARCHAR(40),
    cntpty_card_type_cd VARCHAR(40),
    cntpty_osa_acct_ind VARCHAR(20),
    cntpty_subj_no VARCHAR(100),
    agent_cust_no VARCHAR(100),
    agent_cust_name VARCHAR(400),
    agent_cert_type_cd VARCHAR(40),
    agent_cert_no VARCHAR(100),
    agent_nation_cd VARCHAR(40),
    tx_info_desc TEXT,
    tx_tlr_no VARCHAR(20),
    check_tlr_no VARCHAR(20),
    auth_tlr_no VARCHAR(100),
    merch_no VARCHAR(100),
    merch_name VARCHAR(400),
    merch_type_cd VARCHAR(40),
    meas_obj_cd VARCHAR(20),
    meas_obj_user_name VARCHAR(400),
    data_del_ind VARCHAR(20),
    src_sys_cd VARCHAR(100),
    etl_dt DATE,
    rec_org_id VARCHAR(40),
    trans_code VARCHAR(100),
    remittype VARCHAR(1),
    fxq_tx_chnl_cd VARCHAR(40),
    cntpty_src_cd VARCHAR(10),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_dt IS '交易日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_serl_no IS '交易流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.prod_evt_sn IS '产品事件序号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.extr_serl_no IS '外部流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.glbl_serl_no IS '全局流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.msg_serl_no IS '报文流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_org_cd IS '交易机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_org_adm_div_cd IS '交易机构行政区划代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.acct_org_no IS '核算机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cust_acc_ind IS '客户账标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_tm IS '交易时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.init_acct_dt IS '原记账日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.init_tx_serl_no IS '原交易流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.extr_dt IS '外部日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.oc_acct_type_cd IS '开销户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.biz_type_cd IS '业务类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.prod_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.prod_name IS '产品名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_cd IS '交易代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_name IS '交易名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.extr_tx_cd IS '外部交易代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.extr_tx_name IS '外部交易名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.acct_no IS '记账账户';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cust_acct_no IS '客户账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.acct_sn IS '账户序号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.acct_type_cd IS '账户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.subj_no IS '科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.dc_cd IS '借贷方向代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.dccy_ind IS '本币标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.ccy_ident_cd IS '钞汇类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.acct_amt IS '记账金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cust_acct_bal IS '客户账户余额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.acct_exch_usd_amt IS '记账金额折美元';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.acct_exch_rmb_amt IS '记账金额折人民币';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.exch_mode_cd IS '折算方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.relv_acc_ind IS '来往账标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.incm_pay_type_cd IS '收付类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.abstract_cd IS '摘要代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.abstract_desc IS '摘要描述';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cash_xfer_type_cd IS '现转类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.rev_wipe_cd IS '冲抹账类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.batch_ind IS '批量标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.obs_biz_ind IS '表外业务标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.inter_bank_ind IS '跨行标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.vchr_type_cd IS '凭证种类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.vchr_no IS '凭证号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_chnl_cd IS '交易渠道代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.pay_org_id IS '支付机构标识';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.pay_org_name IS '支付机构名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.pay_tx_type_cd IS '支付交易类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.pay_biz_kind_cd IS '支付业务种类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.clr_ident_cd IS '清算系统标识代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.clr_mtch_no_type_cd IS '清算匹配号类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.clr_mtch_no IS '清算匹配号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_trml_type_cd IS '交易终端类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_trml_no IS '交易终端编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_ip_addr IS '交易IP地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.dev_mac_addr IS '设备MAC地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cash_item_cd IS '现金项目代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.fx_pay_tx_cd IS '涉外收支交易代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_place_nation_cd IS '交易发生地国别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_place_adm_div_cd IS '交易发生地行政区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.xborder_tx_ind IS '跨境交易标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_to_nation_cd IS '交易去向国别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_to_adm_div_cd IS '交易去向行政区划代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.fin_org_tx_rel_cd IS '金融机构和交易关系代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cust_type_cd IS '客户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cust_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cert_type_cd IS '证件类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cert_no IS '证件号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.card_type_cd IS '银行卡类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_init_sys_no IS '交易发起系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.init_org_no IS '发起行机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_acct_no IS '交易对手账号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_acct_type_cd IS '交易对手账户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_name IS '交易对手名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_cust_type_cd IS '交易对手客户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_ecif_cust_no IS '交易对手客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_bank_cust_ind IS '交易对手本行客户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_cert_type_cd IS '交易对手证件类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_cert_no IS '交易对手证件号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_fin_org_cd IS '交易对手金融机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_fin_org_name IS '交易对手金融机构名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_fin_org_type_cd IS '交易对手金融机构类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_clr_bank_no IS '交易对手清算行号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_clr_bank_name IS '交易对手清算行名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_fin_org_nation_cd IS '交易对手金融机构国家代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_card_type_cd IS '交易对手卡片类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_osa_acct_ind IS '交易对手离岸账户标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_subj_no IS '交易对手科目编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.agent_cust_no IS '代办人客户编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.agent_cust_name IS '代办人客户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.agent_cert_type_cd IS '代办人证件类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.agent_cert_no IS '代办人证件号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.agent_nation_cd IS '代办人国籍代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_info_desc IS '交易信息说明';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.tx_tlr_no IS '交易柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.check_tlr_no IS '复核柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.auth_tlr_no IS '授权柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.merch_no IS '商户编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.merch_name IS '商户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.merch_type_cd IS '商户类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.meas_obj_cd IS '计量对象编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.meas_obj_user_name IS '计量对象用户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.data_del_ind IS '数据删除标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.rec_org_id IS '接收机构标识码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.trans_code IS '交易平台代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.remittype IS '汇款方式';
COMMENT ON COLUMN sdmdata.s_ods_g_b_tx_fin_evt.cntpty_src_cd IS '交易对手数据来源标识';

-- f_mid_fns_subject
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_fns_subject (
    orgname VARCHAR(200),
    deptname VARCHAR(300),
    creationtime VARCHAR(19),
    year VARCHAR(4),
    explanation VARCHAR(300),
    subject VARCHAR(40),
    currtype VARCHAR(40),
    amount NUMERIC(28,8),
    direction VARCHAR(1),
    localdebitamount NUMERIC(28,8),
    localcreditamount NUMERIC(28,8),
    if_tech_exp VARCHAR(10),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.orgname IS '机构名称';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.deptname IS '部门名称';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.creationtime IS '创建时间';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.year IS '年份';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.explanation IS '摘要';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.subject IS '科目号';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.currtype IS '币种';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.amount IS '金额';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.direction IS '借贷方向';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.localdebitamount IS '借方金额';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.localcreditamount IS '贷方金额';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.if_tech_exp IS '是否科技投入（0是1否）';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.jxb_fr_id IS '法人机构';
COMMENT ON COLUMN fdmdata.f_mid_fns_subject.ztetl_dt IS '中台跑批时间';

-- s_rrs_rd_cw_r1104_g04
CREATE TABLE IF NOT EXISTS sdmdata.s_rrs_rd_cw_r1104_g04 (
    ddate VARCHAR(10),
    bankid VARCHAR(20),
    rid VARCHAR(20),
    a VARCHAR(50),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);

-- s_ods_m_pam_u_aum_zyf
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_m_pam_u_aum_zyf (
    data_dt DATE,
    ecif_cust_no VARCHAR(100),
    prod_no VARCHAR(50),
    acct_bal NUMERIC(38,8),
    mark_bal NUMERIC(38,8),
    cust_mgr_no VARCHAR(100),
    cust_mgr_bel_dept_cd VARCHAR(20),
    aum_flag VARCHAR(5),
    recmd_no VARCHAR(100),
    recmd_dept_cd VARCHAR(100),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_aum_zyf.recmd_no IS '考核员工号(优先取推荐人，再取客户经理)';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_aum_zyf.recmd_dept_cd IS '考核部门编号(对应考核员工推荐人优先)';

-- s_ods_g_b_ln_contr_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_ln_contr_info (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    biz_contr_no VARCHAR(100),
    apply_no VARCHAR(100),
    prim_contr_no VARCHAR(100),
    ecif_cust_no VARCHAR(100),
    cust_name VARCHAR(1000),
    org_cd VARCHAR(20),
    prod_no VARCHAR(100),
    contr_type_cd VARCHAR(40),
    loan_char_cd VARCHAR(40),
    loan_biz_cate_cd VARCHAR(40),
    ccy_cd VARCHAR(40),
    contr_amt NUMERIC(38,8),
    contr_exch_usd_amt NUMERIC(38,8),
    contr_exch_rmb_amt NUMERIC(38,8),
    expo_amt NUMERIC(38,8),
    margin_pct NUMERIC(18,10),
    margin_amt NUMERIC(38,8),
    contr_sign_dt DATE,
    contr_eff_dt DATE,
    contr_matr_dt DATE,
    contr_end_dt DATE,
    grace_pd_days NUMERIC(10),
    base_intr_type_cd VARCHAR(40),
    base_y_intr NUMERIC(18,10),
    intr_float_mode_cd VARCHAR(40),
    intr_float_val NUMERIC(38,8),
    actl_y_intr NUMERIC(18,10),
    intr_reprice_mode_cd VARCHAR(40),
    intr_reprice_y_freq NUMERIC(10),
    prim_guar_mode_cd VARCHAR(40),
    guar_mode_cd VARCHAR(40),
    trdpty_cate_cd VARCHAR(40),
    loan_term VARCHAR(100),
    putout_mode_cd VARCHAR(40),
    repay_mode_cd VARCHAR(40),
    repay_prin_freq_cd VARCHAR(40),
    repay_int_freq_cd VARCHAR(40),
    repay_day NUMERIC(10),
    int_stl_freq_cd VARCHAR(40),
    loan_cap_src_cd VARCHAR(40),
    loan_purp_cd VARCHAR(40),
    loan_purp_desc TEXT,
    loan_invest_indu_cd VARCHAR(40),
    al_smelt_seg_cd VARCHAR(40),
    loan_invest_region_cd VARCHAR(40),
    ctry_rstr_indu_ind VARCHAR(20),
    entrust_loan_ind VARCHAR(20),
    entrust_loan_type_cd VARCHAR(40),
    syndic_loan_ind VARCHAR(20),
    proj_loan_ind VARCHAR(20),
    sub_loan_ind VARCHAR(20),
    hcd_ind VARCHAR(20),
    strtg_emrg_indu_type_cd VARCHAR(40),
    cultr_indu_ind VARCHAR(20),
    fin_sup_type_cd VARCHAR(40),
    fmly_farm_loan_ind VARCHAR(20),
    agri_mjr_prfs_loan_ind VARCHAR(20),
    cntr_farmers_loan_ind VARCHAR(20),
    agri_lead_ent_loan_ind VARCHAR(20),
    fpc_loan_ind VARCHAR(20),
    rceo_loan_ind VARCHAR(20),
    strt_guar_loan_type_cd VARCHAR(40),
    strt_guar_loan_ind VARCHAR(20),
    disa_strt_guar_loan_ind VARCHAR(20),
    edu_loan_type_cd VARCHAR(40),
    oldg_biz_ind VARCHAR(20),
    bank_tax_coop_loan_ind VARCHAR(20),
    agri_rel_loan_ind VARCHAR(20),
    agri_rel_loan_type_cd VARCHAR(40),
    sup_agri_loan_ind VARCHAR(20),
    sup_agri_loan_type_cd VARCHAR(40),
    estate_loan_type_cd VARCHAR(40),
    green_loan_actl_invest_cd VARCHAR(100),
    disc_int_loan_ind VARCHAR(20),
    ahp_loan_ind VARCHAR(20),
    ahp_loan_type_cd VARCHAR(40),
    fin_tpa_loan_ind VARCHAR(20),
    fin_tpa_loan_type_cd VARCHAR(40),
    tpa_cust_char_cd VARCHAR(40),
    tpa_prom_nums NUMERIC(10),
    prom_povt_pop_ind VARCHAR(20),
    refin_loan_ind VARCHAR(20),
    buy_out_bill_trade_fin_ind VARCHAR(20),
    cmps_consm_loan_ind VARCHAR(20),
    bank_frst_loan_ind VARCHAR(20),
    phma_loan_ind VARCHAR(20),
    buy_house_tot_amt NUMERIC(38,8),
    frst_pay_amt NUMERIC(38,8),
    frst_pay_pct NUMERIC(18,10),
    buy_hse_area NUMERIC(38,8),
    hold_hse_nums NUMERIC(10),
    m_prop_mgmt_fee_amt NUMERIC(38,8),
    loan_fin_use_loc_cd VARCHAR(40),
    fin_plat_loan_type_cd VARCHAR(40),
    fin_plat_actl_invest_cd VARCHAR(40),
    fin_plat_repay_src_cd VARCHAR(40),
    fin_plat_guar_mode_cd VARCHAR(40),
    fin_plat_npl_div_mode_cd VARCHAR(40),
    invest_loan_type_cd VARCHAR(40),
    invest_loan_invested_mode_cd VARCHAR(40),
    crdt_emp_no VARCHAR(100),
    revol_loan_ind VARCHAR(20),
    rmt_biz_ind VARCHAR(20),
    oper_no VARCHAR(100),
    reg_no VARCHAR(100),
    reg_org_no VARCHAR(100),
    reg_dt DATE,
    upd_dt DATE,
    contr_sts_cd VARCHAR(40),
    src_sys_cd VARCHAR(100),
    etl_dt DATE,
    drtimes NUMERIC(10),
    product_mark VARCHAR(100),
    aprv_no VARCHAR(100),
    marginoriginalsum NUMERIC(24,6),
    marginoriginalratio NUMERIC(10,6),
    marginlatestratio NUMERIC(10,6),
    marginbalance NUMERIC(24,6),
    online_loan_cd VARCHAR(10),
    kbdchanneltype VARCHAR(20),
    occ_cdzy_amt NUMERIC(38,8),
    cancel_ind VARCHAR(100),
    repay_souce_cd VARCHAR(100),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    isoperating VARCHAR(10),
    agri_rel_loan_ind_pboc VARCHAR(20),
    green_loan_invest_cbrc VARCHAR(20)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.biz_contr_no IS '业务合同编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.apply_no IS '申请编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.prim_contr_no IS '主合同编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.cust_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.prod_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_type_cd IS '合同类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_char_cd IS '贷款性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_biz_cate_cd IS '信贷业务类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_amt IS '合同金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_exch_usd_amt IS '合同金额折美元';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_exch_rmb_amt IS '合同金额折人民币';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.expo_amt IS '敞口金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.margin_pct IS '保证金比例';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.margin_amt IS '保证金金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_sign_dt IS '合同签订日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_eff_dt IS '合同生效日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_matr_dt IS '合同到期日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_end_dt IS '合同终止日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.grace_pd_days IS '宽限期天数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.base_intr_type_cd IS '基准利率类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.base_y_intr IS '基准年利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.intr_float_mode_cd IS '利率浮动方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.intr_float_val IS '利率浮动值';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.actl_y_intr IS '执行年利率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.intr_reprice_mode_cd IS '利率重定价方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.intr_reprice_y_freq IS '利率重定价年频率';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.prim_guar_mode_cd IS '主要担保方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.guar_mode_cd IS '担保方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.trdpty_cate_cd IS '第三方类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_term IS '贷款期限';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.putout_mode_cd IS '放款方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.repay_mode_cd IS '还款方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.repay_prin_freq_cd IS '还本周期代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.repay_int_freq_cd IS '还息周期代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.repay_day IS '还款日';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.int_stl_freq_cd IS '结息周期代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_cap_src_cd IS '贷款资金来源代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_purp_cd IS '贷款用途代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_purp_desc IS '贷款用途描述';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_invest_indu_cd IS '贷款投向行业代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.al_smelt_seg_cd IS '铝冶炼细分代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_invest_region_cd IS '贷款投向地区代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.ctry_rstr_indu_ind IS '国家限制行业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.entrust_loan_ind IS '委托贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.entrust_loan_type_cd IS '委托贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.syndic_loan_ind IS '银团贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.proj_loan_ind IS '项目贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.sub_loan_ind IS '转贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.hcd_ind IS '禾创贷标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.strtg_emrg_indu_type_cd IS '战略新兴产业类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.cultr_indu_ind IS '文化产业标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fin_sup_type_cd IS '财政扶持方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fmly_farm_loan_ind IS '家庭农场贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.agri_mjr_prfs_loan_ind IS '农业专业大户贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.cntr_farmers_loan_ind IS '承包方农户贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.agri_lead_ent_loan_ind IS '农业产业化龙头企业贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fpc_loan_ind IS '农民专业合作社贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.rceo_loan_ind IS '农村集体经济组织贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.strt_guar_loan_type_cd IS '创业担保贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.strt_guar_loan_ind IS '创业担保贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.disa_strt_guar_loan_ind IS '残疾人创业担保贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.edu_loan_type_cd IS '助学贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.oldg_biz_ind IS '内保外贷业务标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.bank_tax_coop_loan_ind IS '银税合作贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.agri_rel_loan_ind IS '涉农贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.agri_rel_loan_type_cd IS '涉农贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.sup_agri_loan_ind IS '支农贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.sup_agri_loan_type_cd IS '支农贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.estate_loan_type_cd IS '房地产贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.green_loan_actl_invest_cd IS '绿色贷款实际投向代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.disc_int_loan_ind IS '贴息贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.ahp_loan_ind IS '保障性安居工程贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.ahp_loan_type_cd IS '保障性安居工程贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fin_tpa_loan_ind IS '金融精准扶贫贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fin_tpa_loan_type_cd IS '金融精准扶贫贷款类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.tpa_cust_char_cd IS '精准扶贫客户性质代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.tpa_prom_nums IS '精准扶贫贷款带动人数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.prom_povt_pop_ind IS '带动贫困人口贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.refin_loan_ind IS '无还本续贷标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.buy_out_bill_trade_fin_ind IS '买断票据类贸易融资标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.cmps_consm_loan_ind IS '校园消费贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.bank_frst_loan_ind IS '本行首次贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.phma_loan_ind IS '个人住房抵押追加贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.buy_house_tot_amt IS '购入房产总价款金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.frst_pay_amt IS '首付款金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.frst_pay_pct IS '首付款比例';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.buy_hse_area IS '购买住房面积';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.hold_hse_nums IS '已有住房套数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.m_prop_mgmt_fee_amt IS '月物业费金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.loan_fin_use_loc_cd IS '贷款资金使用地代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fin_plat_loan_type_cd IS '融资平台贷款种类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fin_plat_actl_invest_cd IS '融资平台实际投向代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fin_plat_repay_src_cd IS '融资平台偿债来源代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fin_plat_guar_mode_cd IS '融资平台担保方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.fin_plat_npl_div_mode_cd IS '融资平台不良贷款分担方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.invest_loan_type_cd IS '投贷联动类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.invest_loan_invested_mode_cd IS '投贷联动被投资方式代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.crdt_emp_no IS '信贷员工编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.revol_loan_ind IS '循环贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.rmt_biz_ind IS '异地业务标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.oper_no IS '经办人编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.reg_no IS '登记人编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.reg_org_no IS '登记机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.reg_dt IS '登记日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.upd_dt IS '更新日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.contr_sts_cd IS '合同状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.drtimes IS '债务重组次数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.product_mark IS '产品标识';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.aprv_no IS '审批流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.online_loan_cd IS '互联网贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.kbdchanneltype IS '科保贷渠道类型';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.occ_cdzy_amt IS '存单质押金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.agri_rel_loan_ind_pboc IS '涉农贷款标志_人行口径';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_contr_info.green_loan_invest_cbrc IS '银监绿色贷款投放代码';

-- s_ods_m_rpt_acc_exch_bus_count
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_m_rpt_acc_exch_bus_count (
    etl_dt DATE,
    org_cd VARCHAR(30),
    oper_tlr_no VARCHAR(100),
    oper_tlr_name VARCHAR(1000),
    transdate DATE,
    ebk_open_account INTEGER,
    ebk_message_change INTEGER,
    ebk_trsfloor INTEGER,
    ebk_down INTEGER,
    cls_coll INTEGER,
    ebs_acct INTEGER,
    ebs_prsnttn INTEGER,
    fds_volume_up INTEGER,
    fds_redem INTEGER,
    fms_volume_up INTEGER,
    bis_pay_issue INTEGER,
    bis_ins_pre INTEGER,
    ibs_count INTEGER,
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    bis_non_realtm INTEGER,
    ebk_p_pwd_reset INTEGER,
    ebk_p_cert_manag INTEGER,
    ebk_c_op_pwd_reset INTEGER,
    ebk_c_op_del INTEGER,
    ebk_c_op_add INTEGER,
    ebk_c_op_upd INTEGER,
    ebk_c_role_upd INTEGER,
    ebk_c_sign_mod INTEGER,
    ebk_c_sign_close INTEGER,
    ebk_c_limit_set INTEGER,
    ebk_c_cert_manag INTEGER,
    ebk_user_device_unbind INTEGER,
    ebk_loc_rule_set INTEGER,
    evs_loan_seal INTEGER
);
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.etl_dt IS '数据日期 ';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.org_cd IS '机构号';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.oper_tlr_no IS '柜员号';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.oper_tlr_name IS '柜员名称';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.transdate IS '交易日期';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_open_account IS '网银系统（企业开户）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_message_change IS '网银系统（信息变更）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_trsfloor IS '网银系统（白名单录入）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_down IS '网银系统（落地）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.cls_coll IS '公贷系统（抵质押出入库）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebs_acct IS '票据系统（记账）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebs_prsnttn IS '票据系统（托收）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.fds_volume_up IS '代销基金管理系统（购买）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.fds_redem IS '代销基金管理系统（赎回）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.fms_volume_up IS '理财销售系统（购买）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.bis_pay_issue IS '银保通系统（缴费出单）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.bis_ins_pre IS '银保通系统（保费试算）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ibs_count IS '国际结算系统';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.bis_non_realtm IS '银保通系统（非实时单）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_p_pwd_reset IS '网银系统（个人密码重置）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_p_cert_manag IS '网银系统（个人证书管理）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_op_pwd_reset IS '网银系统（企业操作员密码重置）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_op_del IS '网银系统（企业操作员删除）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_op_add IS '网银系统（企业操作员新增）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_op_upd IS '网银系统（企业操作员修改）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_role_upd IS '网银系统（企业角色修改）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_sign_mod IS '网银系统（企业签约变更）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_sign_close IS '网银系统（企业签约注销）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_limit_set IS '网银系统（企业限额设置）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_c_cert_manag IS '网银系统（企业证书管理）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_user_device_unbind IS '网银系统（用户绑定设备解绑）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.ebk_loc_rule_set IS '网银系统（落地规则维护）';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_acc_exch_bus_count.evs_loan_seal IS '信贷验印';

-- s_arm_merchant_info1
CREATE TABLE IF NOT EXISTS sdmdata.s_arm_merchant_info1 (
    id VARCHAR(19),
    merchant_no VARCHAR(100),
    jxb_merchant_no VARCHAR(100),
    apply_type VARCHAR(10),
    merchant_type VARCHAR(10),
    parent_merchant VARCHAR(200),
    owner_organization VARCHAR(100),
    belong_org_uuid VARCHAR(50),
    image_url VARCHAR(200),
    identity_type VARCHAR(100),
    identity_no VARCHAR(100),
    identity_start_date VARCHAR(30),
    identity_end_date VARCHAR(30),
    registered_capital VARCHAR(50),
    industry_category VARCHAR(300),
    merchant_name VARCHAR(100),
    merchant_abbreviation VARCHAR(100),
    legal_identity_address VARCHAR(255),
    legal_identity_image VARCHAR(200),
    legal_inentity_reverse_image VARCHAR(200),
    legal_name VARCHAR(128),
    legal_identity_type VARCHAR(20),
    legal_identify_no VARCHAR(100),
    legal_phone VARCHAR(50),
    legal_identity_start_date VARCHAR(20),
    legal_identity_end_date VARCHAR(20),
    contact_identify_image VARCHAR(100),
    contact_identify_reverse_image VARCHAR(100),
    contact_name VARCHAR(20),
    contact_identity_type VARCHAR(20),
    contact_identify_no VARCHAR(100),
    contact_identity_start_date VARCHAR(30),
    contact_identity_end_date VARCHAR(30),
    contact_phone VARCHAR(50),
    card_image_url VARCHAR(100),
    card_no VARCHAR(100),
    bank_deposit VARCHAR(50),
    bank_no VARCHAR(100),
    bank_type VARCHAR(20),
    deposit_provice VARCHAR(20),
    deposit_city VARCHAR(20),
    deposit_branch_bank VARCHAR(100),
    network_number VARCHAR(100),
    deposit_person VARCHAR(120),
    deposit_person_identity_type VARCHAR(20),
    deposit_person_identity_no VARCHAR(20),
    deposit_person_phone VARCHAR(20),
    pay_type VARCHAR(100),
    bill_rate VARCHAR(10),
    main_type VARCHAR(30),
    trade_type VARCHAR(2),
    pay_way VARCHAR(2),
    merchant_property VARCHAR(2),
    commercial_land VARCHAR(2),
    business_lot VARCHAR(120),
    business_area VARCHAR(120),
    business_acreage VARCHAR(20),
    business_time VARCHAR(20),
    employees VARCHAR(10),
    business_range_main VARCHAR(100),
    business_range_side VARCHAR(100),
    affiliated_group VARCHAR(100),
    affiliated_group_count VARCHAR(10),
    affiliated_group_area VARCHAR(100),
    lastyear_business_volume VARCHAR(50),
    month_average_volume VARCHAR(50),
    average_trade VARCHAR(50),
    skill VARCHAR(2),
    mail VARCHAR(50),
    service_phone VARCHAR(40),
    terminal_number VARCHAR(20),
    store_photo VARCHAR(100),
    cashier_photo VARCHAR(100),
    head_photo VARCHAR(100),
    protocol_photo VARCHAR(300),
    business_site VARCHAR(100),
    signed_photo VARCHAR(100),
    upay_return_status VARCHAR(20),
    risk_status VARCHAR(20),
    gmt_create VARCHAR(40),
    gmt_modify VARCHAR(40),
    created_by VARCHAR(20),
    updated_by VARCHAR(20),
    reg_addr VARCHAR(255),
    province VARCHAR(255),
    city VARCHAR(255),
    county VARCHAR(255),
    mcc_code VARCHAR(255),
    buss_addr VARCHAR(255),
    temporary_storage VARCHAR(2),
    openid VARCHAR(100),
    long_and_lat VARCHAR(255),
    company_type VARCHAR(2),
    pay_desc VARCHAR(100),
    other_photo VARCHAR(300),
    merchant_status VARCHAR(20),
    manage_scope VARCHAR(1000),
    manage_address VARCHAR(200),
    pre_min_limit VARCHAR(19),
    pre_max_limit VARCHAR(19),
    min_limit VARCHAR(50),
    max_limit VARCHAR(50),
    reserved_seal_card_name VARCHAR(100),
    reserved_seal_card_account VARCHAR(100),
    account_opening_permit_name VARCHAR(100),
    account_opening_permit_number VARCHAR(100),
    reserved_seal_card_image VARCHAR(100),
    account_opening_permit_image VARCHAR(100),
    zfb_rate VARCHAR(50),
    union_rate VARCHAR(50),
    settlement_type VARCHAR(10),
    contract_temp_location_path VARCHAR(80),
    contract_final_location_path VARCHAR(80),
    business_name VARCHAR(50),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.id IS '主键';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.merchant_no IS '银联商户号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.jxb_merchant_no IS '银行内部商户号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.apply_type IS '进件类型 0 POS 1条码';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.merchant_type IS '商户类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.parent_merchant IS '连锁商户母商户名称';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.owner_organization IS '归属机构名称';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.belong_org_uuid IS '所属机构uuid';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.image_url IS '企业证件照片地址';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.identity_type IS '企业证件类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.identity_no IS '企业证件号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.identity_start_date IS '证件开始日';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.identity_end_date IS '证件到期日';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.registered_capital IS '注册资金';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.industry_category IS '行业类别';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.merchant_name IS '商户名称';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.merchant_abbreviation IS '商户简称';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_identity_address IS '法人身份证地址';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_identity_image IS '法人证件照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_inentity_reverse_image IS '法人证件反面照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_name IS '法人/负责人姓名';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_identity_type IS '法人/负责人证件类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_identify_no IS '法人/负责人证件号码';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_phone IS '法人/负责人手机';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_identity_start_date IS '法人/负责人证件开始日';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.legal_identity_end_date IS '法人/负责人证件到期日';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contact_identify_image IS '联系人证件照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contact_identify_reverse_image IS '联系人证件反面照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contact_name IS '联系人姓名';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contact_identity_type IS '联系人证件类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contact_identify_no IS '联系人证件号码';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contact_identity_start_date IS '联系人证件开始日';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contact_identity_end_date IS '联系人证件到期日';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contact_phone IS '联系人手机';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.card_image_url IS '银行卡/存折/开户许可证照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.card_no IS '银行卡号/存折号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.bank_deposit IS '开户行';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.bank_no IS '账号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.bank_type IS '账户类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.deposit_provice IS '开户省份';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.deposit_city IS '开户地市';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.deposit_branch_bank IS '开户支行';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.network_number IS '网点号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.deposit_person IS '开户人姓名';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.deposit_person_identity_type IS '开户证件类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.deposit_person_identity_no IS '开户证件编号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.deposit_person_phone IS '开户手机号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.pay_type IS '支付类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.bill_rate IS '结算费率';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.main_type IS '主体类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.trade_type IS '商户交易类型';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.pay_way IS '付款方式';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.merchant_property IS '商户性质';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.commercial_land IS '营业用地性质';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.business_lot IS '经营地段';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.business_area IS '经营区域';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.business_acreage IS '营业用地面积';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.business_time IS '营业时间';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.employees IS '员工人数';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.business_range_main IS '营业范围主业';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.business_range_side IS '营业范围副业';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.affiliated_group IS '分支机构';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.affiliated_group_count IS '分支机构数量';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.affiliated_group_area IS '分支机构范围';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.lastyear_business_volume IS '前一年营业额';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.month_average_volume IS '预计月平均银行卡营业额';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.average_trade IS '预计每张签购单平均交易额';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.skill IS '收银员卡片手里业务知识和操作技能';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.mail IS '邮箱';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.service_phone IS '客服电话';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.terminal_number IS '终端台数';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.store_photo IS '店内照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.cashier_photo IS '收银台照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.head_photo IS '商家门头照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.protocol_photo IS '协议照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.business_site IS '固定经营场所证明';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.signed_photo IS '电子协议签名照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.upay_return_status IS '银联返回状态';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.risk_status IS '风控状态';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.gmt_create IS '创建时间';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.gmt_modify IS '修改时间';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.created_by IS '创建人';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.updated_by IS '修改人';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.reg_addr IS '注册地址';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.province IS '省份';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.city IS '城市';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.county IS '区（县）';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.mcc_code IS 'MCC码';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.buss_addr IS '定位地址';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.temporary_storage IS '是否暂存 1为暂存默认为空';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.openid IS '微信openid 查询暂存数据使用';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.long_and_lat IS '经纬度';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.company_type IS '企业类别';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.pre_min_limit IS '单笔最小限额';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.pre_max_limit IS '单笔最大限额';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.min_limit IS '最小限额pos';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.max_limit IS '最大限额pos';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.reserved_seal_card_name IS '预留印鉴卡户名';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.reserved_seal_card_account IS '预留印鉴卡账号';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.account_opening_permit_name IS '开户许可证-账户名称';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.account_opening_permit_number IS '开户许可证账户号码';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.reserved_seal_card_image IS '预留印鉴卡照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.account_opening_permit_image IS '开户许可证照片';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.zfb_rate IS '支付宝费率';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.union_rate IS '银联费率';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.settlement_type IS '3=个人结算卡，6=开户许可证，5=预留印鉴卡';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contract_temp_location_path IS '电子协议生成存放本地路径';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.contract_final_location_path IS '签章完成电子协议存放路径';
COMMENT ON COLUMN sdmdata.s_arm_merchant_info1.business_name IS '入网业务员';

-- s_ods_m_pam_u_cust_aum
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_m_pam_u_cust_aum (
    data_dt DATE,
    ecif_cust_no VARCHAR(40),
    dep_bal NUMERIC(40,8),
    fin_bal NUMERIC(40,8),
    fund_bal NUMERIC(40,8),
    assert_bal NUMERIC(40,8),
    insur_bal NUMERIC(40,8),
    aum_bal NUMERIC(40,8),
    aum_y_accum NUMERIC(40,8),
    aum_m_accum NUMERIC(40,8),
    aum_y_avg NUMERIC(40,8),
    aum_m_avg NUMERIC(40,8),
    fin_proxy_bal NUMERIC(40,8),
    fin_manager_bal NUMERIC(40,8),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.data_dt IS '数据日期            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.ecif_cust_no IS '客户编号            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.dep_bal IS '储蓄余额            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.fin_bal IS '理财余额            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.fund_bal IS '基金余额            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.assert_bal IS '资管余额            ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.insur_bal IS '保险余额           ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.aum_bal IS 'AUM余额          ';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.aum_y_accum IS 'AUM年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.aum_m_accum IS 'AUM月积数';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.aum_y_avg IS 'AUM年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.aum_m_avg IS 'AUM月日均';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.fin_proxy_bal IS '理财余额(代销)';
COMMENT ON COLUMN sdmdata.s_ods_m_pam_u_cust_aum.fin_manager_bal IS '理财余额(自营)';

-- s_rrs_rd_g01_1_a
CREATE TABLE IF NOT EXISTS sdmdata.s_rrs_rd_g01_1_a (
    ddate VARCHAR(10),
    bankid VARCHAR(20),
    rid VARCHAR(20),
    a NUMERIC(40,10),
    b NUMERIC(40,10),
    c NUMERIC(40,10),
    jxb_fr_id VARCHAR(3),
    ztetl_dt VARCHAR(10)
);

-- s_crw_wm_red_warning_signal_tb
CREATE TABLE IF NOT EXISTS sdmdata.s_crw_wm_red_warning_signal_tb (
    warning_obj_code VARCHAR(100),
    warning_obj_name VARCHAR(300),
    card_type VARCHAR(10),
    card_no VARCHAR(100),
    warning_obj_type VARCHAR(10),
    signal_code VARCHAR(50),
    model_code VARCHAR(60),
    signal_name VARCHAR(300),
    signal_status VARCHAR(10),
    warning_level VARCHAR(10),
    betrue VARCHAR(10),
    warning_grade NUMERIC(32),
    update_date VARCHAR(255),
    remark1 VARCHAR(10),
    remark2 VARCHAR(255),
    warning_date VARCHAR(255),
    be_read VARCHAR(10),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    signal_desc TEXT,
    crpt_no VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.warning_obj_code IS '预警对象编号';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.warning_obj_name IS '预警对象名称';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.card_type IS '证件类型';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.card_no IS '证件编号';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.warning_obj_type IS '预警对象类型（1 - 个人、2 - 企业、3 - 同业、4 - 集团）';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.signal_code IS '预警信号编号';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.model_code IS '模型编号';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.signal_name IS '信号名称';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.signal_status IS '预警信号状态(1 - 处置中、2 - 已处置、3 - 系统自动解除、4 - 解除中、5 - 人工已解除、6 - 贷前信号、7 - 贷中信号、8 - 待处置)';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.warning_level IS '预警等级(1-红、2-黄、3-蓝、4-提示)';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.betrue IS '是否属实';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.warning_grade IS '模型分值';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.update_date IS '信号状态更新时间';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.remark1 IS '是否影响还款意愿或能力(1是0否)';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.remark2 IS '流程解除时间';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.warning_date IS '预警日期';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.be_read IS '是否阅读(1是0否)';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.signal_desc IS '信号描述';
COMMENT ON COLUMN sdmdata.s_crw_wm_red_warning_signal_tb.crpt_no IS '法人机构号';

-- s_ods_f_cms_zq_investment
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_f_cms_zq_investment (
    etl_dt DATE,
    bondna VARCHAR(1024),
    bondcd VARCHAR(64),
    bdparm VARCHAR(1024),
    agname VARCHAR(1024),
    astype VARCHAR(1024),
    bondol NUMERIC,
    bdratg VARCHAR(32),
    bondir NUMERIC,
    ysyjtg VARCHAR(32),
    yslxam NUMERIC,
    yjlxam NUMERIC,
    inadam NUMERIC,
    pchgam NUMERIC,
    ogyear NUMERIC,
    rmyear NUMERIC,
    opendt VARCHAR(8),
    eddate VARCHAR(8),
    lsfxdt VARCHAR(8),
    pyperd VARCHAR(64),
    zqdate VARCHAR(16),
    lxdate VARCHAR(16),
    days NUMERIC,
    eddate1 NUMERIC,
    bondam NUMERIC,
    netprice NUMERIC,
    dirtyprice NUMERIC,
    produtyna VARCHAR(128),
    inveid VARCHAR(32),
    lastdt VARCHAR(8),
    teamna VARCHAR(32),
    brchof VARCHAR(32),
    issubr VARCHAR(60),
    frozam NUMERIC(17,2),
    repttp VARCHAR(32),
    teamid VARCHAR(32),
    agnumb VARCHAR(32),
    pfloss VARCHAR(255),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.etl_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.bondna IS '代码简称';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.bondcd IS '代码编号';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.bdparm IS '资产分类';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.agname IS '发行人名称';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.astype IS '科目';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.bondol IS '成本(余额)';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.bdratg IS '风险权重';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.bondir IS '年利率%';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.ysyjtg IS '应收应计类型';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.yslxam IS '应收利息金额';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.yjlxam IS '应计利息金额';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.inadam IS '利息调整';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.pchgam IS '公允价值变动';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.ogyear IS '原始期限';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.rmyear IS '剩余期限';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.opendt IS '起息日/购买日';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.eddate IS '到期日';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.lsfxdt IS '下一付息日';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.pyperd IS '兑付(付息周期)';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.zqdate IS '到期日划分';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.lxdate IS '利息到期日划分';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.days IS '付息天数(天)';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.eddate1 IS '到期天数(天)';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.bondam IS '持仓面值';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.netprice IS '市场净价';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.dirtyprice IS '市场全价';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.produtyna IS '线下资产类别';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.inveid IS '资管账户';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.lastdt IS '最近一期的开放日';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.teamna IS '交易台';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.brchof IS '归属机构';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.issubr IS '发行人ID';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.frozam IS '已质押';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.repttp IS '资产分类id';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.teamid IS '浜ゆ槗鍙癐D';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.agnumb IS '褰掑睘鏈烘瀯ID';
COMMENT ON COLUMN sdmdata.s_ods_f_cms_zq_investment.pfloss IS '减值准备(估值)';

-- f_mid_dkcp_a008_h
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_dkcp_a008_h (
    level5_cd VARCHAR(50),
    prod_no VARCHAR(50),
    prod_val VARCHAR(50),
    prod_level VARCHAR(50),
    ztetl_dt DATE
);
COMMENT ON COLUMN fdmdata.f_mid_dkcp_a008_h.level5_cd IS '五级产品编号';
COMMENT ON COLUMN fdmdata.f_mid_dkcp_a008_h.prod_no IS '各级产品编号';
COMMENT ON COLUMN fdmdata.f_mid_dkcp_a008_h.prod_val IS '产品名称';
COMMENT ON COLUMN fdmdata.f_mid_dkcp_a008_h.prod_level IS '产品代码级别';
COMMENT ON COLUMN fdmdata.f_mid_dkcp_a008_h.ztetl_dt IS '中台跑批日期';

-- s_ods_g_b_org_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_org_info (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    org_cd VARCHAR(20),
    org_name VARCHAR(1000),
    org_abrv_name VARCHAR(400),
    cbrc_org_no VARCHAR(40),
    fin_biz_lic_cd VARCHAR(40),
    pboc_org_cd VARCHAR(40),
    pboc_pay_bank_no VARCHAR(40),
    uscc_cd VARCHAR(40),
    biz_lic_no VARCHAR(40),
    org_cert_cd VARCHAR(40),
    lei_cd VARCHAR(100),
    fin_org_id VARCHAR(40),
    fin_org_cd VARCHAR(40),
    org_cate_cd VARCHAR(40),
    org_lvl_cd VARCHAR(40),
    legal_no VARCHAR(100),
    town_bank_ind VARCHAR(20),
    fta_ind VARCHAR(20),
    cmny_sub_branch_ind VARCHAR(20),
    sm_ent_mnpl_branch_ind VARCHAR(20),
    tech_fin_mnpl_org_ind VARCHAR(20),
    tech_sub_branch_type_cd VARCHAR(40),
    employed_nums VARCHAR(38),
    branch_org_cd VARCHAR(40),
    biz_sts_cd VARCHAR(40),
    found_dt DATE,
    org_start_work_tm VARCHAR(40),
    org_stop_work_tm VARCHAR(40),
    org_fin_biz_lic_addr VARCHAR(400),
    org_reg_post_cd VARCHAR(40),
    org_reg_adm_div_cd VARCHAR(40),
    org_reg_region_cd VARCHAR(40),
    org_offc_addr VARCHAR(400),
    org_offc_adm_div_cd VARCHAR(40),
    org_contact_tel VARCHAR(100),
    lead_name VARCHAR(100),
    lead_duty_name VARCHAR(1000),
    lead_contact_tel VARCHAR(100),
    org_reg_cap_amt VARCHAR(38),
    data_del_ind VARCHAR(20),
    src_sys_cd VARCHAR(20),
    etl_dt DATE,
    emp_no VARCHAR(40),
    lead_post_name VARCHAR(50),
    org_reg_addr VARCHAR(500),
    org_cntycd VARCHAR(20),
    ztetl_dt VARCHAR(20)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_name IS '机构名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_abrv_name IS '机构简称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.cbrc_org_no IS '所属监管机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.fin_biz_lic_cd IS '金融许可证编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.pboc_org_cd IS '人行机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.pboc_pay_bank_no IS '人行支付行号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.uscc_cd IS '统一社会信用代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.biz_lic_no IS '营业执照号码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_cert_cd IS '组织机构代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.lei_cd IS '全球法人机构识别编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.fin_org_id IS '金融机构标识码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.fin_org_cd IS '金融机构代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_cate_cd IS '机构类别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_lvl_cd IS '机构级别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.legal_no IS '法人编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.town_bank_ind IS '村镇银行标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.fta_ind IS '自贸区标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.cmny_sub_branch_ind IS '社区支行标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.sm_ent_mnpl_branch_ind IS '小微企业专营支行标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.tech_fin_mnpl_org_ind IS '科技金融专营机构标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.tech_sub_branch_type_cd IS '科技支行类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.employed_nums IS '从业人数';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.branch_org_cd IS '网点内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.biz_sts_cd IS '营业状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.found_dt IS '成立日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_start_work_tm IS '机构工作开始时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_stop_work_tm IS '机构工作终止时间';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_fin_biz_lic_addr IS '机构金融许可证地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_reg_post_cd IS '机构注册地址邮政编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_reg_adm_div_cd IS '机构注册地行政区划代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_reg_region_cd IS '机构注册地区域代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_offc_addr IS '机构办公地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_offc_adm_div_cd IS '机构办公地址行政区划代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_contact_tel IS '机构联系电话';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.lead_name IS '负责人姓名';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.lead_duty_name IS '负责人职务名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.lead_contact_tel IS '负责人联系电话';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_reg_cap_amt IS '机构注册资本金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.data_del_ind IS '数据删除标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.emp_no IS '负责人工号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.lead_post_name IS '负责人岗位名称（职务）';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_reg_addr IS '注册地址';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_info.org_cntycd IS '所属区划代码--区县编码（6位-民政版）';

-- s_ods_g_b_org_tlr_info
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_org_tlr_info (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    tlr_no VARCHAR(40),
    tlr_name VARCHAR(1000),
    org_cd VARCHAR(20),
    emp_no VARCHAR(40),
    post_no VARCHAR(400),
    dev_cd VARCHAR(40),
    tlr_type_cd VARCHAR(40),
    vt_tlr_ind VARCHAR(20),
    cust_mgr_ind VARCHAR(20),
    crdt_admin_ind VARCHAR(20),
    emp_eff_ind VARCHAR(20),
    auth_scope TEXT,
    tlr_user_lvl_cd VARCHAR(40),
    tlr_perm_lvl_cd VARCHAR(40),
    post_dt DATE,
    tlr_sts_cd VARCHAR(40),
    src_sys_cd VARCHAR(20),
    etl_dt DATE,
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    ibk_auth_scope VARCHAR(100)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.tlr_no IS '柜员编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.tlr_name IS '柜员名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.emp_no IS '员工编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.post_no IS '岗位编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.dev_cd IS '设备编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.tlr_type_cd IS '柜员类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.vt_tlr_ind IS '虚拟柜员标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.cust_mgr_ind IS '客户经理标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.crdt_admin_ind IS '信贷管理员标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.emp_eff_ind IS '员工有效标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.auth_scope IS '授权范围';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.tlr_user_lvl_cd IS '柜员用户级别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.tlr_perm_lvl_cd IS '柜员权限级别代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.post_dt IS '上岗日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.tlr_sts_cd IS '柜员状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_org_tlr_info.ibk_auth_scope IS '超柜角色';

-- s_ods_f_plm_ac_businesscont_h
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_f_plm_ac_businesscont_h (
    bankid NUMERIC(19),
    applyno VARCHAR(32),
    contno VARCHAR(32),
    vercontno VARCHAR(64),
    cifid VARCHAR(32),
    cliname VARCHAR(64),
    certtype VARCHAR(8),
    certno VARCHAR(18),
    prdt_no VARCHAR(16),
    occurtype VARCHAR(12),
    occurdate VARCHAR(8),
    bustype VARCHAR(10),
    is_cic VARCHAR(8),
    curr VARCHAR(8),
    bus_sum NUMERIC(16,2),
    used_sum NUMERIC(16,2),
    unused_sum NUMERIC(16,2),
    repay_sum NUMERIC(16,2),
    bus_bal NUMERIC(16,2),
    norm_bal NUMERIC(16,2),
    over_bal NUMERIC(16,2),
    flow_bal NUMERIC(16,2),
    sla_bal NUMERIC(16,2),
    bad_bal NUMERIC(16,2),
    in_debt_int NUMERIC(16,2),
    out_debt_int NUMERIC(16,2),
    cmpd_debt_int NUMERIC(16,2),
    tot_paid_int NUMERIC(16,2),
    cancel_sum NUMERIC(16,2),
    term_type VARCHAR(8),
    term NUMERIC(16),
    signdate VARCHAR(8),
    begindate VARCHAR(8),
    enddate VARCHAR(8),
    finishdate VARCHAR(8),
    brate_type VARCHAR(8),
    irate NUMERIC(9,6),
    brate NUMERIC(9,6),
    float_mod VARCHAR(8),
    float_type VARCHAR(8),
    rate_float NUMERIC(9),
    arate NUMERIC(9,6),
    over_duefloat NUMERIC(9,6),
    over_duerate NUMERIC(9,6),
    fine_float NUMERIC(9,6),
    fine_rate NUMERIC(9,6),
    occ_float NUMERIC(9,6),
    occ_rate NUMERIC(9,6),
    cmpd_float NUMERIC(9,6),
    cmpd_rate NUMERIC(9,6),
    con_float NUMERIC(9,6),
    con_rate NUMERIC(9,6),
    ibtype VARCHAR(8),
    repay_type VARCHAR(8),
    repayday VARCHAR(8),
    repay_limit NUMERIC(16),
    pay_type VARCHAR(8),
    paydescribe VARCHAR(512),
    guar_type VARCHAR(8),
    oth_guar_type VARCHAR(12),
    industrytype VARCHAR(12),
    purpose VARCHAR(512),
    purpose_detail VARCHAR(4000),
    clsfour VARCHAR(8),
    clsfive VARCHAR(8),
    rpt_five VARCHAR(8),
    survey_operid VARCHAR(5),
    check_operid VARCHAR(5),
    manage_operid VARCHAR(6),
    manage_instcode VARCHAR(5),
    bal_operid VARCHAR(5),
    operid VARCHAR(6),
    instcode VARCHAR(5),
    con_sts VARCHAR(8),
    account_type VARCHAR(8),
    loan_type VARCHAR(8),
    agre_highsum NUMERIC(16,2),
    agre_lowguarrate NUMERIC(9,6),
    agre_singlerate NUMERIC(9,6),
    agre_is_instead VARCHAR(8),
    agre_instead_beg VARCHAR(8),
    agre_instead_end VARCHAR(8),
    agre_is_autopay VARCHAR(8),
    relacno VARCHAR(32),
    depaccna VARCHAR(64),
    reppriacna VARCHAR(64),
    depacc_no VARCHAR(32),
    reppriac_no VARCHAR(32),
    bal_instcode VARCHAR(5),
    bus_prdt_type VARCHAR(8),
    nlmy VARCHAR(30),
    nhdk VARCHAR(30),
    zhdk VARCHAR(30),
    fptx VARCHAR(30),
    is_farm VARCHAR(8),
    mtel VARCHAR(32),
    istel VARCHAR(2),
    depopnbrna VARCHAR(60),
    repopnbrna VARCHAR(60),
    limitflag VARCHAR(2),
    brf VARCHAR(500),
    is_comp VARCHAR(8),
    comp_time VARCHAR(8),
    comp_brf VARCHAR(512),
    credit_no VARCHAR(32),
    sub_no VARCHAR(32),
    initial_credit_no VARCHAR(32),
    sign_applyno VARCHAR(32),
    spec_flg VARCHAR(2),
    arate_n NUMERIC(9,6),
    repaytype_no VARCHAR(8),
    is_lowrisk VARCHAR(2),
    is_temp VARCHAR(2),
    trust_cifid VARCHAR(32),
    trust_cliname VARCHAR(64),
    trust_certtype VARCHAR(8),
    trust_certno VARCHAR(32),
    trust_rate NUMERIC(9,6),
    trust_sum NUMERIC(16,2),
    trust_account VARCHAR(60),
    chrg_frqcy VARCHAR(2),
    loop VARCHAR(2),
    deposit_no VARCHAR(32),
    funds_src VARCHAR(5),
    in_over_int NUMERIC(16,2),
    out_over_int NUMERIC(16,2),
    un_over_int NUMERIC(16,2),
    un_out_over_int NUMERIC(16,2),
    un_cmpd_int NUMERIC(16,2),
    un_debt_int NUMERIC(16,2),
    loopterm VARCHAR(6),
    un_out_nor_int NUMERIC(16,2),
    lo_intst NUMERIC(16,2),
    is_stamp VARCHAR(8),
    float_direct VARCHAR(2),
    rate_type VARCHAR(8),
    strate_ris_industry VARCHAR(2),
    is_online VARCHAR(6),
    is_rebuild_loan VARCHAR(2),
    first_rebuild_loan VARCHAR(2),
    fin_difficulty VARCHAR(2),
    agri_related_ind VARCHAR(30),
    is_green_loan VARCHAR(4),
    green_loan_invest VARCHAR(128),
    green_loan_invest_yj VARCHAR(128),
    rate_chg_period VARCHAR(8),
    decoreindustry VARCHAR(5),
    digitalefficiency VARCHAR(5),
    isventureguarantee VARCHAR(2),
    ispensionindustry VARCHAR(2),
    pensionindustryflag VARCHAR(4),
    high_manufacturing VARCHAR(20),
    high_service VARCHAR(20),
    intellectualproperty VARCHAR(8),
    rebuild_type VARCHAR(8)
);
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.bankid IS '银行实体号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.applyno IS '申请编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.contno IS '借款合同流水号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.vercontno IS '信贷合同编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.cifid IS '客户流水号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.cliname IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.certtype IS '客户证件类型';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.certno IS '客户证件号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.prdt_no IS '业务品种';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.occurtype IS '贷款形式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.occurdate IS '发生日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.bustype IS '业务类型：10单报单批；15单报单批-协议；20额度项下；40最高额授信；45授信-协议';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_cic IS '循环贷款标志';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.curr IS '协议币种';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.bus_sum IS '合同金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.used_sum IS '已提取金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.unused_sum IS '可提取金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.repay_sum IS '合同收回贷款金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.bus_bal IS '表内余额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.norm_bal IS '正常余额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.over_bal IS '逾期余额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.flow_bal IS '逾期90天以上余额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.sla_bal IS '呆滞余额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.bad_bal IS '呆帐余额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.in_debt_int IS '表内欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.out_debt_int IS '表外欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.cmpd_debt_int IS '复利';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.tot_paid_int IS '累计实收利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.cancel_sum IS '核销金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.term_type IS '期限月';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.term IS '期限日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.signdate IS '协议签订日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.begindate IS '协议开始日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.enddate IS '协议到期日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.finishdate IS '协议终止日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.brate_type IS '基准利率类型:1LPR利率2人行基准';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.irate IS '人行基准利率%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.brate IS '产品利率‰(默认人行基准)';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.float_mod IS '利率浮动方式1次月首日2次季首日4次年首日5次年首笔';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.float_type IS '利率浮动方式:1固定利率2浮动利率';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.rate_float IS '利率浮动值';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.arate IS '执行月利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.over_duefloat IS '逾期利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.over_duerate IS '逾期贷款利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.fine_float IS '挪用利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.fine_rate IS '挪用贷款利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.occ_float IS '挤占利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.occ_rate IS '挤占利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.cmpd_float IS '复利利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.cmpd_rate IS '复利利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.con_float IS '约定利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.con_rate IS '约定利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.ibtype IS '计息方式：S周期性(schedule)、D按日匡算(day)';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.repay_type IS '还款方式：S周期性还款(schedule)、D非周期性还款(day)';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.repayday IS '指定还款日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.repay_limit IS '还款宽限期天';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.pay_type IS '放款方式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.paydescribe IS '支付说明';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.guar_type IS '主要担保方式：10抵押、20质押、30保证、40保证金、50信用';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.oth_guar_type IS '附加担保方式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.industrytype IS '贷款投向';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.purpose IS '贷款用途';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.purpose_detail IS '贷款用途描述';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.clsfour IS '贷款四级分类';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.clsfive IS '贷款五级分类10正常20关注30次级40可疑50损失';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.rpt_five IS '报表五级分类';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.survey_operid IS '调查客户经理';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.check_operid IS '辅调客户经理';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.manage_operid IS '客户经理编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.manage_instcode IS '业务所属机构';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.bal_operid IS '余额所属客户经理';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.operid IS '操作员';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.instcode IS '操作机构';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.con_sts IS '合同状态：10待生效20有效、30结清、99无效、90循环贷止付';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.account_type IS '记账类型：1放款、2记账撤销';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.loan_type IS '贷款类别：1个贷、2微贷';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.agre_highsum IS '协议-单笔最高授信额度';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.agre_lowguarrate IS '协议-最低保证金比例';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.agre_singlerate IS '协议-单笔最低保证金比例';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.agre_is_instead IS '协议-是否代偿';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.agre_instead_beg IS '协议-代偿起始日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.agre_instead_end IS '协议-代偿终止日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.agre_is_autopay IS '协议-代偿是否自动扣款';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.relacno IS '协议合同号-合作协议或无实体额度度编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.depaccna IS '账户名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.reppriacna IS '账户名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.depacc_no IS '贷款入账账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.reppriac_no IS '还款账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.bal_instcode IS '余额所属机构';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.bus_prdt_type IS '贷款种类';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.nlmy IS '农林牧渔分类';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.nhdk IS '农户、农村企业、城市企业分类';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.zhdk IS '农村及城市企业贷款类型';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.fptx IS '扶贫贴息贷款分类';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_farm IS '是否涉农：1是；0否';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.mtel IS '借款人电话号码';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.istel IS '是否发送短信';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.depopnbrna IS '放款账户开户机构名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.repopnbrna IS '还款账户开户机构名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.limitflag IS '宽限期启用标志0未启用1启用';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.brf IS '备注';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_comp IS '决议条件是否落实';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.comp_time IS '决议条件落实时间';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.comp_brf IS '决议条件落实内容';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.credit_no IS '授信协议编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.sub_no IS '授信子额度编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.initial_credit_no IS '初始授信协议编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.sign_applyno IS '签约申请流水号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.spec_flg IS '特殊额度标志0否1是-额度项下业务使用';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.arate_n IS '贷款合同利率';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.repaytype_no IS '还款方式编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_lowrisk IS '是否低风险业务';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_temp IS '暂存标识0暂存1保存';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.trust_cifid IS '委托人客户号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.trust_cliname IS '委托人名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.trust_certtype IS '委托人证件类型';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.trust_certno IS '委托人证件号码';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.trust_rate IS '手续费比例';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.trust_sum IS '手续费金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.trust_account IS '委托人存款账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.chrg_frqcy IS '委托贷款收费频率';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.loop IS '委托贷款收费频率循环量';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.deposit_no IS '保证金账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.funds_src IS '出账利率方式11实时利率20合同利率';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.in_over_int IS '逾期欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.out_over_int IS '表外逾期欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.un_over_int IS '待结逾期利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.un_out_over_int IS '待结表外逾期利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.un_cmpd_int IS '待结复息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.un_debt_int IS '待结正常利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.loopterm IS '循环期限';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.un_out_nor_int IS '待结表外正常利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.lo_intst IS '欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_stamp IS '印花税是否代扣';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.float_direct IS 'LPR加减点';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.rate_type IS '出账利率方式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.strate_ris_industry IS '战略新兴产业';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_online IS '线上线下签订方式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_rebuild_loan IS '是否重组贷款';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.first_rebuild_loan IS '是否首笔重组贷款';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.fin_difficulty IS '是否财政困难';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.agri_related_ind IS '涉农附报指标';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.is_green_loan IS '是否绿色贷款';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.green_loan_invest IS '绿色贷款投向';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.green_loan_invest_yj IS '银监绿色贷款投向';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.rate_chg_period IS '利率调整周期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.decoreindustry IS '数字经济核心产业';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.digitalefficiency IS '数字化效率提升产业';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.isventureguarantee IS '是否创业担保';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.ispensionindustry IS '是否养老产业';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.pensionindustryflag IS '养老产业标识';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.high_manufacturing IS '高技术制造业';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.high_service IS '高技术服务业';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.intellectualproperty IS '知识文化产业';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businesscont_h.rebuild_type IS '重组类型（1、首次重组，2、重组到期后期授信，3、再次重组）';

-- s_ods_f_plm_ac_businessvch_h
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_f_plm_ac_businessvch_h (
    bankid NUMERIC(19),
    applyno VARCHAR(32),
    contno VARCHAR(32),
    vchno VARCHAR(32),
    cifid VARCHAR(32),
    cliname VARCHAR(64),
    certtype VARCHAR(8),
    certno VARCHAR(18),
    prdt_no VARCHAR(16),
    core_prdt_no VARCHAR(16),
    occurtype VARCHAR(12),
    occurdate VARCHAR(8),
    ext_num NUMERIC(16),
    curr VARCHAR(8),
    bus_sum NUMERIC(16,2),
    bus_bal NUMERIC(16,2),
    norm_bal NUMERIC(16,2),
    over_bal NUMERIC(16,2),
    flow_bal NUMERIC(16,2),
    sla_bal NUMERIC(16,2),
    bad_bal NUMERIC(16,2),
    in_debt_int NUMERIC(16,2),
    out_debt_int NUMERIC(16,2),
    cmpd_debt_int NUMERIC(16,2),
    tot_paid_int NUMERIC(16,2),
    paid_int NUMERIC(16,2),
    paid_fine NUMERIC(16,2),
    cancel_sum NUMERIC(16,2),
    term_type VARCHAR(8),
    term NUMERIC(16),
    begindate VARCHAR(8),
    enddate VARCHAR(8),
    bintdate VARCHAR(8),
    finishdate VARCHAR(8),
    brate_type VARCHAR(8),
    irate NUMERIC(9,6),
    brate NUMERIC(9,6),
    float_mod VARCHAR(8),
    float_type VARCHAR(8),
    rate_float NUMERIC(9),
    arate NUMERIC(9,6),
    over_duefloat NUMERIC(9,6),
    over_duerate NUMERIC(9,6),
    fine_float NUMERIC(9,6),
    fine_rate NUMERIC(9,6),
    occ_float NUMERIC(9,6),
    occ_rate NUMERIC(9,6),
    cmpd_float NUMERIC(9,6),
    cmpd_rate NUMERIC(9,6),
    con_float NUMERIC(9,6),
    con_rate NUMERIC(9,6),
    extenddate VARCHAR(8),
    extrate NUMERIC(9,6),
    ibtype VARCHAR(8),
    repay_type VARCHAR(8),
    repayday VARCHAR(12),
    repay_limit NUMERIC(16),
    pay_type VARCHAR(8),
    paydescribe VARCHAR(512),
    guar_type VARCHAR(8),
    oth_guar_type VARCHAR(12),
    industrytype VARCHAR(12),
    purpose VARCHAR(512),
    purpose_detail VARCHAR(256),
    clsfour VARCHAR(8),
    clsfive VARCHAR(8),
    rpt_five VARCHAR(8),
    cls_detail VARCHAR(128),
    loanac_no VARCHAR(32),
    loanac_id NUMERIC(19),
    loanac_seqn NUMERIC(19),
    is_otherloan VARCHAR(8),
    depacc_no VARCHAR(32),
    depacc_seq NUMERIC(16),
    is_autoreppri VARCHAR(8),
    is_otherreppri VARCHAR(8),
    reppriac_no VARCHAR(32),
    reppriac_seq NUMERIC(16),
    secreppriac_no VARCHAR(32),
    is_autorepint VARCHAR(8),
    is_otherrepint VARCHAR(8),
    repintac_no VARCHAR(32),
    repintac_seq NUMERIC(16),
    secrepintac_no VARCHAR(32),
    secrepintac_seq NUMERIC(16),
    first_due_date VARCHAR(12),
    lst_repay_date VARCHAR(8),
    first_lo_date VARCHAR(8),
    lo_date VARCHAR(8),
    overdue_day NUMERIC(16),
    overdue_period VARCHAR(8),
    is_preserve VARCHAR(8),
    is_insolvent VARCHAR(8),
    survey_operid VARCHAR(5),
    check_operid VARCHAR(5),
    manage_operid VARCHAR(6),
    manage_instcode VARCHAR(5),
    bal_operid VARCHAR(6),
    operid VARCHAR(6),
    instcode VARCHAR(5),
    vch_sts VARCHAR(8),
    account_type VARCHAR(8),
    loan_type VARCHAR(8),
    paid_cmpd NUMERIC(16,2),
    depaccna VARCHAR(64),
    reppriacna VARCHAR(64),
    extcontno VARCHAR(32),
    reppriaccardno VARCHAR(32),
    secreppriac_seq NUMERIC(16),
    bal_instcode VARCHAR(5),
    brf VARCHAR(512),
    repay_fee_sum NUMERIC(16,2),
    lo_reason VARCHAR(512),
    early_pay_sum NUMERIC(16,2),
    un_over_int NUMERIC(16,2),
    un_cmpd_int NUMERIC(16,2),
    repaytype_no VARCHAR(8),
    advanced_expired_flg VARCHAR(1),
    arate_n NUMERIC(9,6),
    amt_lo_date VARCHAR(8),
    amt_over_days NUMERIC(9),
    settle_intst_thisyear NUMERIC(16,2),
    lo_intst_thisyear NUMERIC(16,2),
    curr_prov_intst NUMERIC(16,2),
    income_intst_total NUMERIC(16,2),
    income_intst_thisyear NUMERIC(16,2),
    verify_date VARCHAR(8),
    final_operid VARCHAR(5),
    deposit_sub_no VARCHAR(32),
    funds_src VARCHAR(5),
    in_over_int NUMERIC(16,2),
    out_over_int NUMERIC(16,2),
    un_out_over_int NUMERIC(16,2),
    un_debt_int NUMERIC(16,2),
    is_aging VARCHAR(2),
    core_paystyle VARCHAR(2),
    lo_intst NUMERIC(16,2),
    un_out_nor_int NUMERIC(16,2),
    float_direct VARCHAR(2),
    rate_type VARCHAR(8),
    is_online VARCHAR(6),
    watch_days VARCHAR(2),
    watch_begindate VARCHAR(8),
    watch_enddate VARCHAR(8),
    rate_chg_period VARCHAR(8),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.bankid IS '法人机构号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.applyno IS '申请编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.contno IS '信贷合同编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.vchno IS '借款借据编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.cifid IS '客户编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.cliname IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.certtype IS '客户证件类型';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.certno IS '客户证件号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.prdt_no IS '业务品种';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.core_prdt_no IS '账务业务品种';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.occurtype IS '发生类型：1新增、2续贷、3并行';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.occurdate IS '发生日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.ext_num IS '展期次数';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.curr IS '借据币种';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.bus_sum IS '借款金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.bus_bal IS '借款余额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.norm_bal IS '正常本金';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.over_bal IS '逾期余额（昨日）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.flow_bal IS '逾期90天以上余额（昨日）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.sla_bal IS '呆滞余额（昨日）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.bad_bal IS '呆帐余额（昨日）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.in_debt_int IS '表内欠息（昨日）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.out_debt_int IS '表外欠息（昨日）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.cmpd_debt_int IS '复利（昨日）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.tot_paid_int IS '累计实收利息（嘉兴未使用）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.paid_int IS '实收利息（嘉兴未使用）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.paid_fine IS '实收罚息（嘉兴未使用）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.cancel_sum IS '核销金额（嘉兴未使用）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.term_type IS '期限类型：M月、D日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.term IS '贷款期数';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.begindate IS '协议开始日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.enddate IS '协议到期日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.bintdate IS '贷款实际发放日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.finishdate IS '结清日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.brate_type IS '基准利率类型:1LPR利率2人行基准';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.irate IS '行内基准利率%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.brate IS '基准利率%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.float_mod IS '利率浮动类型:数据字典220005';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.float_type IS '利率浮动方式:1固定利率2浮动利率';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.rate_float IS '利率浮动值';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.arate IS '执行月利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.over_duefloat IS '逾期利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.over_duerate IS '逾期贷款利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.fine_float IS '挪用利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.fine_rate IS '挪用贷款利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.occ_float IS '挤占利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.occ_rate IS '挤占利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.cmpd_float IS '复利利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.cmpd_rate IS '复利利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.con_float IS '约定利率浮动%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.con_rate IS '约定利率‰';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.extenddate IS '展期到期日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.extrate IS '展期年利率%';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.ibtype IS '计息方式：1不计息、2按日计息、3按周计息、4按旬计息、5按月计息、6按季计息、7按年计息、8利随本清、9按揭';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.repay_type IS '还款方式：1按月等额本息、2按月等额本金、3按月付息按季还本、4前三月还息以后等额本息、5按月付息每半年还';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.repayday IS '指定还款日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.repay_limit IS '还款宽限期天';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.pay_type IS '放款方式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.paydescribe IS '支付说明';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.guar_type IS '主要担保方式：10抵押、20质押、30保证、40保证金、50信用';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.oth_guar_type IS '次要担保方式：10抵押、20质押、30保证、40保证金';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.industrytype IS '贷款投向行业类型';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.purpose IS '贷款用途';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.purpose_detail IS '贷款用途描述';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.clsfour IS '贷款四级分类';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.clsfive IS '贷款五级分类';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.rpt_five IS '报表五级分类0102正常、0103正常-、0201关注+、0202关注、0203关注-、0301次级+、0302次级、0303次级-、040';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.cls_detail IS '分类认定说明';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.loanac_no IS '贷款账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.loanac_id IS '贷款账号标识';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.loanac_seqn IS '贷款账号序号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_otherloan IS '是否第三方放款:0否1是';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.depacc_no IS '存款账户（放款）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.depacc_seq IS '存款账户序号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_autoreppri IS '自动还本标志:0否1是';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_otherreppri IS '是否第三方还本:0否1是';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.reppriac_no IS '还款账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.reppriac_seq IS '还款账号序号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.secreppriac_no IS '第二还款帐号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_autorepint IS '自动还息标志:0否1是';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_otherrepint IS '是否第三方还息:0否1是';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.repintac_no IS '还息账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.repintac_seq IS '还息账号序号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.secrepintac_no IS '第二还息账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.secrepintac_seq IS '第二还息账号序号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.first_due_date IS '首次还息日期（嘉兴未使用）';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.lst_repay_date IS '最后一次还款日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.first_lo_date IS '逾期日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.lo_date IS '当前逾期起始日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.overdue_day IS '最长逾期天数';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.overdue_period IS '当前逾期期次';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_preserve IS '是否转保全0否，1是';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_insolvent IS '是否以资抵债:0否，1是';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.survey_operid IS '调查客户经理';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.check_operid IS '辅调客户经理';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.manage_operid IS '信贷员工编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.manage_instcode IS '管理机构编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.bal_operid IS '余额所属客户经理';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.operid IS '操作员';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.instcode IS '登记机构编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.vch_sts IS '借据状态：10有效（已出账）、15审批通过(待记账)、20无效（撤销）、30结清、60核销';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.account_type IS '记账类型：0未发送、1放款、2记账撤销';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.loan_type IS '贷款类别：1小贷、2微贷';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.paid_cmpd IS '实收复利';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.depaccna IS '账户名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.reppriacna IS '账户名称';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.extcontno IS '展期协议编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.reppriaccardno IS '还款卡号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.secreppriac_seq IS '第二还款账号序号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.bal_instcode IS '余额所属机构';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.brf IS '备注';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.repay_fee_sum IS '提前还款违约金金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.lo_reason IS '欠款原因';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.early_pay_sum IS '提前还款金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.un_over_int IS '未结逾期利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.un_cmpd_int IS '未结复利';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.repaytype_no IS '还款方式编号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.advanced_expired_flg IS '提前到期：0，否；1，是';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.arate_n IS '执行利率';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.amt_lo_date IS '本金逾期起始日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.amt_over_days IS '本金逾期天数';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.settle_intst_thisyear IS '当年结息金额';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.lo_intst_thisyear IS '本年欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.curr_prov_intst IS '当前计提利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.income_intst_total IS '累计利息收入';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.income_intst_thisyear IS '本年利息收入';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.verify_date IS '核销日期';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.final_operid IS '终批人';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.deposit_sub_no IS '保证金子账号';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.funds_src IS '出账利率方式11实时利率20合同利率';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.in_over_int IS '逾期欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.out_over_int IS '表外逾期欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.un_out_over_int IS '待结表外逾期利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.un_debt_int IS '待结正常利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_aging IS '是否分期还本';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.core_paystyle IS '核心受托支付方式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.lo_intst IS '欠息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.un_out_nor_int IS '待结表外正常利息';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.float_direct IS 'LPR加减点';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.rate_type IS '出账利率方式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.is_online IS '线上线下签订方式';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.watch_days IS '观察期天数';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.watch_begindate IS '观察期起始日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.watch_enddate IS '观察期到期日';
COMMENT ON COLUMN sdmdata.s_ods_f_plm_ac_businessvch_h.rate_chg_period IS '利率调整周期';

-- s_ods_g_c_org_tree_h
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_c_org_tree_h (
    level1_cd VARCHAR(20),
    level1_val VARCHAR(100),
    level2_cd VARCHAR(20),
    level2_val VARCHAR(100),
    level3_cd VARCHAR(20),
    level3_val VARCHAR(100),
    level4_cd VARCHAR(20),
    level4_val VARCHAR(100),
    level5_cd VARCHAR(20),
    level5_val VARCHAR(100),
    level6_cd VARCHAR(20),
    level6_val VARCHAR(100),
    level7_cd VARCHAR(20),
    level7_val VARCHAR(100),
    level8_cd VARCHAR(20),
    level8_val VARCHAR(100),
    busi_flag VARCHAR(5),
    short_name VARCHAR(100),
    lv4_ind VARCHAR(2),
    start_dt DATE,
    end_dt DATE
);

-- s_ods_g_b_ln_credit_agt
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_b_ln_credit_agt (
    data_dt DATE,
    legal_org_cd VARCHAR(20),
    crdt_agt_no VARCHAR(100),
    par_crdt_agt_no VARCHAR(100),
    crdt_agt_text_no VARCHAR(100),
    apply_no VARCHAR(100),
    apply_type VARCHAR(100),
    crdt_agt_name VARCHAR(1000),
    ecif_cust_no VARCHAR(100),
    cust_name VARCHAR(1000),
    org_cd VARCHAR(20),
    prod_no VARCHAR(100),
    crdt_obj_type_cd VARCHAR(40),
    crdt_agt_type_cd VARCHAR(40),
    batch_sub_cate_cd VARCHAR(40),
    ccy_cd VARCHAR(40),
    matr_limt_amt NUMERIC(40,8),
    matr_expo_amt NUMERIC(40,8),
    limt_amt NUMERIC(40,8),
    limt_exch_usd_amt NUMERIC(40,8),
    limt_exch_rmb_amt NUMERIC(40,8),
    expo_amt NUMERIC(40,8),
    expo_exch_usd_amt NUMERIC(40,8),
    expo_exch_rmb_amt NUMERIC(40,8),
    aval_amt NUMERIC(40,8),
    aval_exch_usd_amt NUMERIC(40,8),
    aval_exch_rmb_amt NUMERIC(40,8),
    trdpty_limt_amt NUMERIC(40,8),
    sgl_cust_limt NUMERIC(40,8),
    apply_dt DATE,
    eff_dt DATE,
    crdt_sts_cd VARCHAR(40),
    frst_crdt_dt DATE,
    crdt_start_dt DATE,
    crdt_matr_dt DATE,
    actl_matr_dt DATE,
    decis_opinion TEXT,
    fnl_aprv_no VARCHAR(100),
    rel_pty_crdt_ind VARCHAR(20),
    revol_limt_ind VARCHAR(20),
    tmp_limt_ind VARCHAR(20),
    prob_crdt_ind VARCHAR(20),
    crdt_emp_no VARCHAR(100),
    src_sys_cd VARCHAR(100),
    etl_dt DATE,
    occur_type VARCHAR(10),
    aprv_no VARCHAR(100),
    aprv_dt DATE,
    unif_limt_amt NUMERIC(40,8),
    unif_expo_amt NUMERIC(40,8),
    unif_aval_amt NUMERIC(40,8),
    risk_ctr_aprv_ind VARCHAR(20),
    risk_ctr_aprv_userid VARCHAR(32),
    risk_ctr_aprv_usernm VARCHAR(80),
    aprv_reg_dt DATE,
    mrtg_limt_amt NUMERIC(40,8),
    pldg_limt_amt NUMERIC(40,8),
    margin_limt_amt NUMERIC(40,8),
    credit_limt_amt NUMERIC(40,8),
    biz_prod_no VARCHAR(100),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    expo_crdt_ind VARCHAR(20),
    unif_using_amt NUMERIC(40,8)
);
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.data_dt IS '数据日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.legal_org_cd IS '法人机构编码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_agt_no IS '授信协议编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.par_crdt_agt_no IS '父授信协议编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_agt_text_no IS '授信协议文本编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.apply_no IS '申请编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.apply_type IS '申请类型';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_agt_name IS '授信协议名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.cust_name IS '客户名称';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.org_cd IS '内部机构编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.prod_no IS '产品编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_obj_type_cd IS '授信主体种类代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_agt_type_cd IS '授信协议类型代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.batch_sub_cate_cd IS '批量额度子协议种类';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.ccy_cd IS '货币代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.matr_limt_amt IS '到期额度金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.matr_expo_amt IS '到期敞口金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.limt_amt IS '额度金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.limt_exch_usd_amt IS '额度金额折美元';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.limt_exch_rmb_amt IS '额度金额折人民币';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.expo_amt IS '敞口金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.expo_exch_usd_amt IS '敞口金额折美元';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.expo_exch_rmb_amt IS '敞口金额折人民币';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.aval_amt IS '可用金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.aval_exch_usd_amt IS '可用金额折美元';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.aval_exch_rmb_amt IS '可用金额折人民币';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.trdpty_limt_amt IS '第三方额度金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.sgl_cust_limt IS '单户限额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.apply_dt IS '申请日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.eff_dt IS '生效日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_sts_cd IS '授信状态代码';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.frst_crdt_dt IS '首次授信日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_start_dt IS '授信开始日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_matr_dt IS '授信到期日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.actl_matr_dt IS '实际到期日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.decis_opinion IS '决策单意见';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.fnl_aprv_no IS '最终审批人编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.rel_pty_crdt_ind IS '关联方授信标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.revol_limt_ind IS '循环额度标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.tmp_limt_ind IS '临时额度标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.prob_crdt_ind IS '是否重组授信';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.crdt_emp_no IS '授信员工编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.src_sys_cd IS '来源系统编号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.etl_dt IS 'ETL日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.occur_type IS '发生类型';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.aprv_no IS '审批流水号';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.aprv_dt IS '审批日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.unif_limt_amt IS '授信额度';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.unif_expo_amt IS '敞口金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.unif_aval_amt IS '可用金额';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.risk_ctr_aprv_ind IS '经审批风控中心审批标志';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.risk_ctr_aprv_userid IS '终审人编号-经审批风控中心审批';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.risk_ctr_aprv_usernm IS '终审人名称-经审批风控中心审批';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.aprv_reg_dt IS '批复登记日期';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.mrtg_limt_amt IS '抵押额度';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.pldg_limt_amt IS '质押额度';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.margin_limt_amt IS '保证额度';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.credit_limt_amt IS '信用额度';
COMMENT ON COLUMN sdmdata.s_ods_g_b_ln_credit_agt.biz_prod_no IS '业务产品编号';

-- f_mid_ctcxcp_a036_h
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_ctcxcp_a036_h (
    level5_cd VARCHAR(50),
    prod_no VARCHAR(50),
    prod_val VARCHAR(50),
    prod_level VARCHAR(50),
    ztetl_dt DATE
);
COMMENT ON COLUMN fdmdata.f_mid_ctcxcp_a036_h.level5_cd IS '五级产品编号';
COMMENT ON COLUMN fdmdata.f_mid_ctcxcp_a036_h.prod_no IS '各级产品编号';
COMMENT ON COLUMN fdmdata.f_mid_ctcxcp_a036_h.prod_val IS '产品名称';
COMMENT ON COLUMN fdmdata.f_mid_ctcxcp_a036_h.prod_level IS '产品代码级别';
COMMENT ON COLUMN fdmdata.f_mid_ctcxcp_a036_h.ztetl_dt IS '中台跑批日期';

-- f_mid_ckcp_a038_h
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_ckcp_a038_h (
    level5_cd VARCHAR(50),
    prod_no VARCHAR(50),
    prod_val VARCHAR(50),
    prod_level VARCHAR(50),
    ztetl_dt DATE
);
COMMENT ON COLUMN fdmdata.f_mid_ckcp_a038_h.level5_cd IS '五级产品编号';
COMMENT ON COLUMN fdmdata.f_mid_ckcp_a038_h.prod_no IS '各级产品编号';
COMMENT ON COLUMN fdmdata.f_mid_ckcp_a038_h.prod_val IS '产品名称';
COMMENT ON COLUMN fdmdata.f_mid_ckcp_a038_h.prod_level IS '产品代码级别';
COMMENT ON COLUMN fdmdata.f_mid_ckcp_a038_h.ztetl_dt IS '中台跑批日期';

-- s_ods_m_rpt_genpro_t
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_m_rpt_genpro_t (
    etl_dt DATE,
    org_cd VARCHAR(20),
    ccy_cd VARCHAR(40),
    xh VARCHAR(200),
    pd VARCHAR(10),
    xname NUMERIC(65),
    amt NUMERIC(40,8),
    remark1 VARCHAR(1000),
    fb_bal VARCHAR(40),
    y_fb_bal_accum VARCHAR(40),
    y_avg_fb_bal VARCHAR(40),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.etl_dt IS '数据时间';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.org_cd IS '机构编号';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.ccy_cd IS '币种';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.xh IS '编号';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.pd IS '频度';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.xname IS '编号名称';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.amt IS '余额';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.remark1 IS '科目的代号';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.fb_bal IS '法备余额';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.y_fb_bal_accum IS '法备余额年积数';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.y_avg_fb_bal IS '法备余额年日均';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.jxb_fr_id IS '法人机构';
COMMENT ON COLUMN sdmdata.s_ods_m_rpt_genpro_t.ztetl_dt IS '中台跑批时间';

-- s_cbs_kcab_xjsqtb
CREATE TABLE IF NOT EXISTS sdmdata.s_cbs_kcab_xjsqtb (
    farendma VARCHAR(4),
    xjinyybh VARCHAR(30),
    xjinsfbz VARCHAR(1),
    xjinfsbz VARCHAR(1),
    yngyjigo VARCHAR(12),
    guiyzlei VARCHAR(1),
    zhngjigo VARCHAR(12),
    huobdaih VARCHAR(4),
    yyjhleix VARCHAR(1),
    canbleix VARCHAR(2),
    xjinqnzh VARCHAR(1),
    zongjine NUMERIC(21,2),
    diocriqi VARCHAR(8),
    cunftyzh VARCHAR(48),
    duifjgdh VARCHAR(12),
    shifoubz VARCHAR(1),
    pingzhzl VARCHAR(5),
    pngzphao VARCHAR(10),
    pingzhma VARCHAR(32),
    zhaiyodm VARCHAR(10),
    zhaiyoms VARCHAR(300),
    beizhuxx VARCHAR(300),
    xjinsqzt VARCHAR(1),
    jiaoyirq VARCHAR(8),
    jiaoyisj NUMERIC(16),
    jiaoyigy VARCHAR(8),
    jiaoyijg VARCHAR(12),
    shoqguiy VARCHAR(8),
    guiylius VARCHAR(32),
    qudaoooo VARCHAR(7),
    shijjyje NUMERIC(21,2),
    shuoming VARCHAR(300),
    scjyriqi VARCHAR(8),
    fenhbios VARCHAR(4),
    weihguiy VARCHAR(8),
    weihjigo VARCHAR(12),
    weihriqi VARCHAR(8),
    weihshij VARCHAR(9),
    shijchuo NUMERIC(16),
    jiluztai VARCHAR(1),
    jxb_fr_id VARCHAR(5),
    ztetl_dt VARCHAR(10),
    ysmkunsh VARCHAR(6)
);
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.farendma IS '法人代码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.xjinyybh IS '现金申请编号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.xjinsfbz IS '现金收付标志(0-领用,1-上缴)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.xjinfsbz IS '现金发生标志';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.yngyjigo IS '营业机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.guiyzlei IS '柜员种类(0-柜面柜员,1-自助设备)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.zhngjigo IS '账务机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.huobdaih IS '货币代号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.yyjhleix IS '预约计划类型(0-日常,1-临时,2-集中)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.canbleix IS '残损币情况(1-全兑,2-半兑)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.xjinqnzh IS '券种(1-流通券,2-破损券,3-假币,4-反宣币)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.zongjine IS '总金额';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.diocriqi IS '调出日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.cunftyzh IS '对方同业账号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.duifjgdh IS '对方机构代号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.shifoubz IS '是否控制明细(1-是,0-否)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.pingzhzl IS '凭证种类';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.pngzphao IS '凭证批号';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.pingzhma IS '凭证号码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.zhaiyodm IS '摘要代码';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.zhaiyoms IS '摘要描述';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.beizhuxx IS '备注信息';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.xjinsqzt IS '现金申请状态(0-待审批,1-已撤销,2-已拒绝,3-已出库,4-已配钞,5-已入库,6-已审批,7-已作废)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.jiaoyirq IS '交易日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.jiaoyisj IS '交易时间';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.jiaoyigy IS '交易柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.jiaoyijg IS '交易机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.shoqguiy IS '授权柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.guiylius IS '柜员流水';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.qudaoooo IS '渠道';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.shijjyje IS '实际交易金额';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.shuoming IS '说明';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.scjyriqi IS '上次交易日';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.fenhbios IS '分行标识';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.weihguiy IS '维护柜员';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.weihjigo IS '维护机构';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.weihriqi IS '维护日期';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.weihshij IS '维护时间';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.shijchuo IS '时间戳';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.jiluztai IS '记录状态(0-正常,1-删除)';
COMMENT ON COLUMN sdmdata.s_cbs_kcab_xjsqtb.ysmkunsh IS '已扫描捆数';

-- ============================================================
-- 补充的表（2026-01-31 追加）
-- ============================================================

-- f_mid_dep_tb
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_dep_tb (
    data_dt DATE,
    dep_acct_no VARCHAR(100),
    prin_subj_no VARCHAR(100),
    ecif_cust_no VARCHAR(100),
    prod_no VARCHAR(20),
    org_no VARCHAR(40),
    level7_val VARCHAR(100),
    cust_acct_no VARCHAR(100),
    cust_acct_name VARCHAR(100),
    prod_sign_intr NUMERIC(18,10),
    actl_y_intr NUMERIC(18,10),
    fix_cur_ind VARCHAR(20),
    open_dt DATE,
    dep_clct_no VARCHAR(40),
    cust_type_cd VARCHAR(40),
    acct_bal NUMERIC(40,8),
    ccy_cd VARCHAR(20),
    std_y_avg_bal NUMERIC(40,8),
    acct_y_accum NUMERIC(40,8),
    titc_cust_id VARCHAR(40),
    level1_cd VARCHAR(40),
    level2_cd VARCHAR(40),
    level3_cd VARCHAR(40),
    level4_cd VARCHAR(40),
    acct_y_wgt_accum NUMERIC(40,8),
    d_payb_int_m_accum NUMERIC(40,8),
    d_payb_int_q_accum NUMERIC(40,8),
    d_payb_int_y_accum NUMERIC(40,8),
    d_payb_int_d_accum NUMERIC(40,8),
    legal_org_cd VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_dep_tb.data_dt IS '业务日期';
COMMENT ON COLUMN fdmdata.f_mid_dep_tb.dep_acct_no IS '存款账户号';
COMMENT ON COLUMN fdmdata.f_mid_dep_tb.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_tb.prod_no IS '产品编号';
COMMENT ON COLUMN fdmdata.f_mid_dep_tb.org_no IS '开户机构';
COMMENT ON COLUMN fdmdata.f_mid_dep_tb.level7_val IS '机构名称';
COMMENT ON COLUMN fdmdata.f_mid_dep_tb.acct_bal IS '账户余额';
COMMENT ON COLUMN fdmdata.f_mid_dep_tb.ccy_cd IS '币种';

-- f_mid_loan_tb
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_loan_tb (
    data_dt DATE,
    duebill_no VARCHAR(100),
    biz_contr_no VARCHAR(100),
    org_cd VARCHAR(20),
    level7_val VARCHAR(100),
    ccy_cd VARCHAR(40),
    ecif_cust_no VARCHAR(100),
    prod_no VARCHAR(100),
    duebill_sts_cd VARCHAR(40),
    norm_actl_y_intr NUMERIC(18,10),
    crdt_biz_cate_cd VARCHAR(40),
    rsdu_matr_days INTEGER,
    crdt_obj_class_cd VARCHAR(40),
    mod_belong VARCHAR(8),
    obs_biz_ind VARCHAR(20),
    norm_prin_subj_no VARCHAR(100),
    five_class_cd VARCHAR(40),
    prin_ovrd_days INTEGER,
    int_ovrd_days INTEGER,
    new_productmark VARCHAR(40),
    norm_prin_bal NUMERIC(40,8),
    norm_prin_y_accum NUMERIC(40,8),
    prin_bal NUMERIC(40,8),
    y_prin_wgt_accum NUMERIC(40,8),
    y_tot_owe_int NUMERIC(40,8),
    int_amt2 NUMERIC(40,8),
    margin_bal NUMERIC(40,8),
    ibs_owe_int_amt NUMERIC(40,8),
    obs_owe_int_amt NUMERIC(40,8),
    titc_cust_id VARCHAR(40),
    indu_type_cd VARCHAR(40),
    holding_type_cd VARCHAR(40),
    ent_scal_cd VARCHAR(40),
    level4_cd VARCHAR(40),
    level3_cd VARCHAR(40),
    level2_cd VARCHAR(40),
    level1_cd VARCHAR(40),
    st_own_ent_ind VARCHAR(40),
    tech_corp_ind VARCHAR(40),
    ext_dt DATE,
    ext_matr_dt DATE,
    prim_guar_mode_cd VARCHAR(40),
    loan_invest_indu_cd VARCHAR(40),
    all_crdt_tot_amt NUMERIC(40,8),
    y_prin_bal_accum NUMERIC(40,8),
    cust_mgr_no VARCHAR(100),
    int_amt2_m_accum NUMERIC(40,8),
    int_amt2_q_accum NUMERIC(40,8),
    int_amt2_y_accum NUMERIC(40,8),
    legal_org_cd VARCHAR(20)
);
COMMENT ON COLUMN fdmdata.f_mid_loan_tb.data_dt IS '业务日期';
COMMENT ON COLUMN fdmdata.f_mid_loan_tb.duebill_no IS '借据编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_tb.ecif_cust_no IS '客户统一编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_tb.prod_no IS '产品编号';
COMMENT ON COLUMN fdmdata.f_mid_loan_tb.prin_bal IS '借款本金余额';
COMMENT ON COLUMN fdmdata.f_mid_loan_tb.five_class_cd IS '五级分类';

-- f_mid_org_tree
CREATE TABLE IF NOT EXISTS fdmdata.f_mid_org_tree (
    level7_cd VARCHAR(100),
    level7_val VARCHAR(100),
    org_no VARCHAR(100),
    org_val VARCHAR(100),
    org_lv VARCHAR(100)
);
COMMENT ON COLUMN fdmdata.f_mid_org_tree.level7_cd IS '7级机构代码';
COMMENT ON COLUMN fdmdata.f_mid_org_tree.level7_val IS '7级机构名称';
COMMENT ON COLUMN fdmdata.f_mid_org_tree.org_no IS '各级机构代码';

-- s_ods_g_c_dim_date
CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_c_dim_date (
    date_id DATE,
    ld_dt DATE,
    lme_dt DATE,
    lqe_dt DATE,
    lye_dt DATE,
    m_id NUMERIC(10),
    m_cn_nm VARCHAR(100),
    ms_dt DATE,
    me_dt DATE,
    me_ind VARCHAR(20),
    q_id NUMERIC(10),
    q_cn_nm VARCHAR(100),
    qs_dt DATE,
    qe_dt DATE,
    y_id NUMERIC(10),
    y_cn_nm VARCHAR(100),
    ys_dt DATE,
    ye_dt DATE,
    work_day_ind VARCHAR(20),
    ztetl_dt VARCHAR(10)
);
COMMENT ON COLUMN sdmdata.s_ods_g_c_dim_date.date_id IS '当前日期';
COMMENT ON COLUMN sdmdata.s_ods_g_c_dim_date.lme_dt IS '上月月末日期';
COMMENT ON COLUMN sdmdata.s_ods_g_c_dim_date.m_cn_nm IS '月中文名称';
COMMENT ON COLUMN sdmdata.s_ods_g_c_dim_date.work_day_ind IS '工作日标志';
