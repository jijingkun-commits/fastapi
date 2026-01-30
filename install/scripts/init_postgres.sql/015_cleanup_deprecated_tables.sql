-- 015_cleanup_deprecated_tables.sql
-- 清理问数场景废弃表，统一使用 t_metric_definition

-- ============================================================
-- 1. 删除废弃的 t_metrics 表
-- ============================================================
DROP TABLE IF EXISTS t_metrics CASCADE;

-- ============================================================
-- 2. 删除废弃的 t_dmp_ind_info 表（如果存在）
-- ============================================================
DROP TABLE IF EXISTS t_dmp_ind_info CASCADE;

-- ============================================================
-- 3. 说明
-- ============================================================
-- 问数场景指标表统一为 t_metric_definition
-- 
-- 废弃原因：
-- - t_metrics: 结构设计不合理，缺少 sql_template
-- - t_dmp_ind_info: DIDP 原始格式，字段过多，不适合项目使用
--
-- 使用方式：
-- - 所有指标定义存储在 t_metric_definition
-- - 使用 scripts/init_metric_definition.py 初始化
-- - 使用 scripts/import_metrics_from_didp.py 导入 DIDP 指标
