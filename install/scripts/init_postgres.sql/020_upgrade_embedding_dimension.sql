-- 020: 升级 embedding 列维度从 vector(1024) 到 vector(2048)
-- 背景: embedding 模型从 embedding-2 (1024维) 升级到 embedding-3 (2048维)
-- 影响: t_meta_tables, t_meta_columns, t_metrics 三张表
-- 注意: 升级后需重新运行 python -m app.ai.semantic.schema_sync 生成新向量

-- 清空旧的不兼容向量
UPDATE t_meta_tables SET embedding = NULL WHERE embedding IS NOT NULL;
UPDATE t_meta_columns SET embedding = NULL WHERE embedding IS NOT NULL;
UPDATE t_metrics SET embedding = NULL WHERE embedding IS NOT NULL;

-- 修改列定义为 vector(2048)
ALTER TABLE t_meta_tables ALTER COLUMN embedding TYPE vector(2048);
ALTER TABLE t_meta_columns ALTER COLUMN embedding TYPE vector(2048);
ALTER TABLE t_metrics ALTER COLUMN embedding TYPE vector(2048);
