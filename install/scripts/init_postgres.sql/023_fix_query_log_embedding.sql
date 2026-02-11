-- 023: 修复 t_data_query_log 表的 embedding 维度
-- 背景: 020 升级脚本遗漏了 t_data_query_log 表
-- 影响: t_data_query_log.question_embedding
-- 数据库: chat_db (不是 data_db)
-- 执行: docker exec -i fastapi-postgres psql -U postgres -d chat_db -f 023_fix_query_log_embedding.sql

-- 清空旧的不兼容向量
UPDATE t_data_query_log SET question_embedding = NULL WHERE question_embedding IS NOT NULL;

-- 修改列定义为 vector(2048)
ALTER TABLE t_data_query_log ALTER COLUMN question_embedding TYPE vector(2048);
