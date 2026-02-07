-- 022: 指标定义表新增 query_template 和 template_source 列
-- 背景: sql_template 中 1524 条存储的是 ETL 批处理脚本（DELETE+INSERT），不可直接用于 RAG 和 SQL 生成
-- 方案: 新增 query_template 列存储可直接执行的 SELECT 查询，保留原始 sql_template 不修改
-- 日期: 2026-02-07
-- 关联: ADR-011 指标模板架构决策

-- 1. 新增列
ALTER TABLE t_metric_definition
  ADD COLUMN IF NOT EXISTS query_template TEXT;

ALTER TABLE t_metric_definition
  ADD COLUMN IF NOT EXISTS template_source VARCHAR(20) DEFAULT 'none';

COMMENT ON COLUMN t_metric_definition.query_template IS '可直接执行的 SELECT 查询模板（从 sql_template 提取或手工编写）';
COMMENT ON COLUMN t_metric_definition.template_source IS '模板来源: manual(手动) | ai_extract(AI提取) | result_lookup(结果表查询) | none(未处理)';

-- 2. 迁移现有 SELECT 模板（19 条）
UPDATE t_metric_definition
SET query_template = sql_template,
    template_source = 'manual'
WHERE sql_template IS NOT NULL
  AND sql_template ~* '^\s*SELECT'
  AND query_template IS NULL;

-- 3. 为写入 f_mid_index_result 的指标生成结果表查询模板（约 901 条）
UPDATE t_metric_definition
SET query_template = format(
    'SELECT data_dt, org_no, org_no_map AS 机构名称, ccy AS 币种, '
    || 'index_name AS 指标名称, index_value AS 指标值, '
    || 'year_to_date AS 年累计 '
    || 'FROM fdmdata.f_mid_index_result '
    || 'WHERE index_code = ''%s'' AND data_dt = ''${data_dt}'' '
    || 'ORDER BY org_no',
    metric_id
),
    template_source = 'result_lookup'
WHERE sql_template IS NOT NULL
  AND sql_template ILIKE '%INSERT INTO%F_MID_INDEX_RESULT%'
  AND sql_template NOT ILIKE '%F_MID_INDEX_RESULT_DIM%'
  AND sql_template NOT ILIKE '%F_MID_INDEX_RESULT_DERIVE%'
  AND query_template IS NULL;

-- 4. 为写入 f_mid_index_result_dim 的指标生成结果表查询模板（约 301 条）
UPDATE t_metric_definition
SET query_template = format(
    'SELECT data_dt, org_no, org_no_map AS 机构名称, ccy AS 币种, '
    || 'index_name AS 指标名称, index_value AS 指标值, '
    || 'year_to_date AS 年累计, dim_name AS 维度名称, dim_value AS 维度值 '
    || 'FROM fdmdata.f_mid_index_result_dim '
    || 'WHERE index_code = ''%s'' AND data_dt = ''${data_dt}'' '
    || 'ORDER BY org_no',
    metric_id
),
    template_source = 'result_lookup'
WHERE sql_template IS NOT NULL
  AND sql_template ILIKE '%INSERT INTO%F_MID_INDEX_RESULT_DIM%'
  AND query_template IS NULL;

-- 5. 为写入 f_mid_index_result_derive 的指标生成结果表查询模板（约 288 条）
UPDATE t_metric_definition
SET query_template = format(
    'SELECT data_dt, org_no, org_no_map AS 机构名称, ccy AS 币种, '
    || 'index_name AS 指标名称, index_value AS 指标值, '
    || 'year_to_date AS 年累计 '
    || 'FROM fdmdata.f_mid_index_result_derive '
    || 'WHERE index_code = ''%s'' AND data_dt = ''${data_dt}'' '
    || 'ORDER BY org_no',
    metric_id
),
    template_source = 'result_lookup'
WHERE sql_template IS NOT NULL
  AND sql_template ILIKE '%INSERT INTO%F_MID_INDEX_RESULT_DERIVE%'
  AND query_template IS NULL;

-- 6. 验证迁移结果
DO $$
DECLARE
    v_total INT;
    v_manual INT;
    v_result_lookup INT;
    v_none INT;
BEGIN
    SELECT COUNT(*) INTO v_total FROM t_metric_definition;
    SELECT COUNT(*) INTO v_manual FROM t_metric_definition WHERE template_source = 'manual';
    SELECT COUNT(*) INTO v_result_lookup FROM t_metric_definition WHERE template_source = 'result_lookup';
    SELECT COUNT(*) INTO v_none FROM t_metric_definition WHERE template_source = 'none' OR template_source IS NULL;
    
    RAISE NOTICE '=== 指标模板迁移结果 ===';
    RAISE NOTICE '总数: %', v_total;
    RAISE NOTICE '手动 SELECT: %', v_manual;
    RAISE NOTICE '结果表查询: %', v_result_lookup;
    RAISE NOTICE '未处理: %', v_none;
    RAISE NOTICE 'query_template 覆盖率: %', 
        ROUND((v_manual + v_result_lookup)::NUMERIC / NULLIF(v_total, 0) * 100, 1) || '%';
END $$;
