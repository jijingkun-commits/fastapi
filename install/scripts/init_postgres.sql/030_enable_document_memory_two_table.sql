-- 030: 文档化永久记忆（两表）DDL + 配置初始化
-- 背景: 引入非 KV 的自由知识沉淀记忆，主存储为 document + chunk
-- 影响: chat_db.t_user_memory_document / chat_db.t_user_memory_chunk / chat_db.t_system_config
-- 执行: ./deploy.sh dev migrate 或 ./deploy.sh prod migrate

-- 依赖扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 文档化永久记忆主表
CREATE TABLE IF NOT EXISTS t_user_memory_document (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    doc_kind VARCHAR(32) NOT NULL DEFAULT 'daily',
    doc_key VARCHAR(128) NOT NULL,
    title VARCHAR(255),
    content_md TEXT NOT NULL,
    summary_md TEXT,
    source VARCHAR(32) NOT NULL DEFAULT 'memory',
    scope VARCHAR(32) NOT NULL DEFAULT 'private',
    scope_ref VARCHAR(128),
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    revision INTEGER NOT NULL DEFAULT 1,
    content_hash VARCHAR(64) NOT NULL,
    source_thread_id VARCHAR(100),
    source_message_id BIGINT,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_memory_document_user_update
    ON t_user_memory_document(user_id, update_time);
CREATE INDEX IF NOT EXISTS idx_user_memory_document_user_scope
    ON t_user_memory_document(user_id, source, scope, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_memory_document_active_unique
    ON t_user_memory_document(user_id, doc_kind, doc_key)
    WHERE status = 'active';

-- 文档化永久记忆分块检索表
CREATE TABLE IF NOT EXISTS t_user_memory_chunk (
    id BIGSERIAL PRIMARY KEY,
    doc_id BIGINT NOT NULL REFERENCES t_user_memory_document(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    chunk_no INTEGER NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_hash VARCHAR(64) NOT NULL,
    chunk_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', coalesce(chunk_text, ''))) STORED,
    embedding VECTOR(2048),
    embedding_model VARCHAR(128),
    embedding_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    embedding_retry_count INTEGER NOT NULL DEFAULT 0,
    embedding_error TEXT,
    embedding_updated_time TIMESTAMP,
    source VARCHAR(32) NOT NULL DEFAULT 'memory',
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_memory_chunk_user_doc_no
    ON t_user_memory_chunk(user_id, doc_id, chunk_no);
CREATE INDEX IF NOT EXISTS idx_user_memory_chunk_doc
    ON t_user_memory_chunk(doc_id);
CREATE INDEX IF NOT EXISTS idx_user_memory_chunk_embedding_status
    ON t_user_memory_chunk(user_id, embedding_status, update_time);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_memory_chunk_unique_hash
    ON t_user_memory_chunk(user_id, doc_id, chunk_hash);
CREATE INDEX IF NOT EXISTS idx_user_memory_chunk_tsv
    ON t_user_memory_chunk USING gin(chunk_tsv);
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
    ('feature.enable_document_memory', 'false', 'boolean', 'feature', '用户个性化永久记忆总开关（纯文档）', false, false),
    ('memory.document.max_results', '6', 'number', 'memory', '文档记忆检索结果上限', false, false),
    ('memory.document.max_injected_chars', '1200', 'number', 'memory', '文档记忆注入预算（字符）', false, false),
    ('memory.document.hybrid.vector_weight', '0.7', 'number', 'memory', '文档记忆向量权重', false, false),
    ('memory.document.hybrid.text_weight', '0.3', 'number', 'memory', '文档记忆文本权重', false, false),
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
