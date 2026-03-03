-- 031: 文档记忆混合检索（FTS + 向量）补充迁移
-- 背景: 在两表方案上补齐向量状态治理与混合检索配置
-- 影响: chat_db.t_user_memory_chunk / chat_db.t_system_config
-- 执行: ./deploy.sh dev migrate 或 ./deploy.sh prod migrate

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE t_user_memory_chunk
    ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(16) NOT NULL DEFAULT 'pending';

ALTER TABLE t_user_memory_chunk
    ADD COLUMN IF NOT EXISTS embedding_retry_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE t_user_memory_chunk
    ADD COLUMN IF NOT EXISTS embedding_error TEXT;

ALTER TABLE t_user_memory_chunk
    ADD COLUMN IF NOT EXISTS embedding_updated_time TIMESTAMP;

DROP INDEX IF EXISTS idx_user_memory_chunk_embedding_ivfflat;

-- 兼容历史维度：文档记忆默认向量维度统一为 2048
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 't_user_memory_chunk'
          AND column_name = 'embedding'
          AND udt_name = 'vector'
    ) THEN
        UPDATE t_user_memory_chunk
        SET embedding = NULL
        WHERE embedding IS NOT NULL;

        ALTER TABLE t_user_memory_chunk
            ALTER COLUMN embedding TYPE vector(2048);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_memory_chunk_embedding_status
    ON t_user_memory_chunk(user_id, embedding_status, update_time);

-- 说明: 当前 embedding 为 2048 维，pgvector 的 ivfflat/hnsw 均受 2000 维上限约束，
-- 因此此处不创建 ANN 向量索引，混合检索走 user_id 过滤后的精确向量计算。

INSERT INTO t_system_config (
    config_key,
    config_value,
    value_type,
    category,
    description,
    is_secret,
    is_readonly
)
VALUES
    ('memory.document.hybrid.min_score', '0.05', 'number', 'memory', '文档记忆混合召回最低分', false, false),
    ('memory.document.embedding.batch_size', '32', 'number', 'memory', '文档记忆向量补偿批大小', false, false),
    ('memory.document.embedding.max_retry', '3', 'number', 'memory', '文档记忆向量自动重试上限', false, false)
ON CONFLICT (config_key) DO UPDATE
SET
    config_value = EXCLUDED.config_value,
    value_type = EXCLUDED.value_type,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    is_secret = EXCLUDED.is_secret,
    is_readonly = EXCLUDED.is_readonly;
