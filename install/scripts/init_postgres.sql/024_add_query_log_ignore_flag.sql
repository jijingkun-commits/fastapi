-- 024: 为 t_data_query_log 新增 is_ignored 软隐藏字段
-- 背景: SQL 修正台新增“忽略日志”功能，默认查询需过滤已忽略记录
-- 影响: chat_db.t_data_query_log
-- 执行: docker exec -i fastapi-postgres psql -U postgres -d chat_db -f 024_add_query_log_ignore_flag.sql

ALTER TABLE t_data_query_log
  ADD COLUMN IF NOT EXISTS is_ignored BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN t_data_query_log.is_ignored IS '是否已忽略（软隐藏）';

-- 可选：清理默认值（应用层已维护默认语义）
ALTER TABLE t_data_query_log
  ALTER COLUMN is_ignored DROP DEFAULT;
