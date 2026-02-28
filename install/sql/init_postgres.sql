-- PostgreSQL 初始化脚本（全量建表）
-- 用途：新环境首次部署时执行
-- 更新日期：2026-02-02
-- 注意：投产后的增量变更请使用 install/scripts/init_postgres.sql/ 或 Alembic

-- ============================================================
-- 用户管理
-- ============================================================

-- 用户表
CREATE TABLE IF NOT EXISTS t_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(200),
    password VARCHAR(300),
    mobile VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',
    org_code VARCHAR(100),
    org_name VARCHAR(200),
    dept_code VARCHAR(100),
    dept_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    create_time TIMESTAMP,
    update_time TIMESTAMP
);

COMMENT ON TABLE t_user IS '用户表';
COMMENT ON COLUMN t_user.username IS '用户名称';
COMMENT ON COLUMN t_user.password IS '密码';
COMMENT ON COLUMN t_user.mobile IS '手机号';
COMMENT ON COLUMN t_user.role IS '用户角色: admin/analyst/user';
COMMENT ON COLUMN t_user.org_code IS '机构代码';
COMMENT ON COLUMN t_user.org_name IS '机构名称';
COMMENT ON COLUMN t_user.dept_code IS '部门代码';
COMMENT ON COLUMN t_user.dept_name IS '部门名称';
COMMENT ON COLUMN t_user.is_active IS '是否启用';

-- Token 黑名单表（登出用）
CREATE TABLE IF NOT EXISTS t_token_blacklist (
    id SERIAL PRIMARY KEY,
    token_jti VARCHAR(64) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES t_user(id),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_t_token_blacklist_token_jti ON t_token_blacklist(token_jti);

COMMENT ON TABLE t_token_blacklist IS 'Token黑名单表';
COMMENT ON COLUMN t_token_blacklist.token_jti IS 'JWT ID，唯一标识';
COMMENT ON COLUMN t_token_blacklist.user_id IS '关联用户ID';
COMMENT ON COLUMN t_token_blacklist.expires_at IS 'Token原过期时间';
COMMENT ON COLUMN t_token_blacklist.created_at IS '加入黑名单时间';

-- ============================================================
-- 聊天系统
-- ============================================================

-- 对话消息表
CREATE TABLE IF NOT EXISTS t_chat_message (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER,
    thread_id VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'ai',
    content_type VARCHAR(50) NOT NULL DEFAULT 'markdown',
    content TEXT,
    metadata JSONB,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS ix_t_chat_message_user_id ON t_chat_message(user_id);
CREATE INDEX IF NOT EXISTS ix_t_chat_message_thread_id ON t_chat_message(thread_id);

COMMENT ON TABLE t_chat_message IS '对话消息表';
COMMENT ON COLUMN t_chat_message.user_id IS '用户ID';
COMMENT ON COLUMN t_chat_message.thread_id IS '对话线程ID';
COMMENT ON COLUMN t_chat_message.role IS '消息角色: ai/human/system';
COMMENT ON COLUMN t_chat_message.content_type IS '内容类型: markdown/chart/table';
COMMENT ON COLUMN t_chat_message.content IS '消息内容';
COMMENT ON COLUMN t_chat_message.metadata IS '元数据JSON';
COMMENT ON COLUMN t_chat_message.title IS '对话标题';

-- 用户偏好记忆表（跨会话）
CREATE TABLE IF NOT EXISTS t_user_memory (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    scope VARCHAR(32) NOT NULL DEFAULT 'global',
    memory_key VARCHAR(128) NOT NULL,
    memory_value TEXT NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 1.000,
    source_thread_id VARCHAR(100),
    source_message_id BIGINT,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_memory_user_scope ON t_user_memory(user_id, scope);
CREATE INDEX IF NOT EXISTS idx_user_memory_user_update ON t_user_memory(user_id, update_time);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_memory_active_unique
    ON t_user_memory(user_id, scope, memory_key)
    WHERE status = 'active';

COMMENT ON TABLE t_user_memory IS '用户跨会话偏好记忆表';
COMMENT ON COLUMN t_user_memory.scope IS '作用域，默认 global';
COMMENT ON COLUMN t_user_memory.memory_key IS '偏好键，例如 response.language';
COMMENT ON COLUMN t_user_memory.memory_value IS '偏好值';
COMMENT ON COLUMN t_user_memory.confidence IS '偏好置信度';

-- 文档化永久记忆主表（两表方案）
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

COMMENT ON TABLE t_user_memory_document IS '文档化永久记忆主表';
COMMENT ON COLUMN t_user_memory_document.doc_kind IS '文档类型: long_term/daily/session';
COMMENT ON COLUMN t_user_memory_document.doc_key IS '文档键，如 MEMORY 或 YYYY-MM-DD';
COMMENT ON COLUMN t_user_memory_document.content_md IS '文档正文';
COMMENT ON COLUMN t_user_memory_document.content_hash IS '文档内容哈希';

-- 文档化永久记忆分块检索表
-- 依赖 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

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

COMMENT ON TABLE t_user_memory_chunk IS '文档化永久记忆分块检索表';
COMMENT ON COLUMN t_user_memory_chunk.chunk_tsv IS '全文检索向量';
COMMENT ON COLUMN t_user_memory_chunk.embedding IS '向量嵌入（2048维）';
COMMENT ON COLUMN t_user_memory_chunk.embedding_status IS '向量状态: pending/ready/failed';

-- 对话资产表（图片、图表等）
CREATE TYPE asset_type AS ENUM ('chart', 'image', 'export', 'attachment');

CREATE TABLE IF NOT EXISTS t_chat_assets (
    id BIGSERIAL PRIMARY KEY,
    qa_record_id BIGINT NOT NULL,
    chat_id VARCHAR(64) NOT NULL,
    user_id BIGINT,
    asset_type asset_type NOT NULL DEFAULT 'image',
    object_key VARCHAR(255) NOT NULL,
    original_url TEXT,
    file_name VARCHAR(255),
    file_size BIGINT,
    content_type VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_t_chat_assets_user_id ON t_chat_assets(user_id);
CREATE INDEX IF NOT EXISTS ix_t_chat_assets_chat_id ON t_chat_assets(chat_id);
CREATE INDEX IF NOT EXISTS ix_t_chat_assets_qa_record_id ON t_chat_assets(qa_record_id);
CREATE INDEX IF NOT EXISTS idx_user_chat ON t_chat_assets(user_id, chat_id);

COMMENT ON TABLE t_chat_assets IS '对话资产表';

-- 幂等键表
CREATE TABLE IF NOT EXISTS t_idempotency_key (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR(64) NOT NULL,
    user_id INTEGER,
    endpoint VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    thread_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_t_idempotency_key_key ON t_idempotency_key(key);

COMMENT ON TABLE t_idempotency_key IS '幂等键记录表';
COMMENT ON COLUMN t_idempotency_key.key IS '幂等键';
COMMENT ON COLUMN t_idempotency_key.status IS '状态: pending/completed/failed';
COMMENT ON COLUMN t_idempotency_key.thread_id IS '关联的对话线程ID';

-- ============================================================
-- 待办系统
-- ============================================================

-- 待办任务表
CREATE TABLE IF NOT EXISTS t_todo (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP,
    due_date TIMESTAMP,
    actual_completion_time TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,
    progress_notes TEXT,
    priority INTEGER NOT NULL DEFAULT 2,
    category VARCHAR(50),
    tags JSONB,
    reminder_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    reminder_type VARCHAR(20),
    reminder_advance_minutes INTEGER,
    reminder_times JSONB,
    last_reminded_at TIMESTAMP,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    is_recurring BOOLEAN NOT NULL DEFAULT FALSE,
    recurrence_pattern VARCHAR(50),
    recurrence_interval INTEGER NOT NULL DEFAULT 1,
    recurrence_days JSONB,
    recurrence_end_date TIMESTAMP,
    parent_recurring_id INTEGER,
    parent_id INTEGER,
    task_order INTEGER NOT NULL DEFAULT 0,
    depth_level INTEGER NOT NULL DEFAULT 0,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra_data JSONB
);

CREATE INDEX IF NOT EXISTS ix_t_todo_user_id ON t_todo(user_id);
CREATE INDEX IF NOT EXISTS idx_todo_status ON t_todo(status);
CREATE INDEX IF NOT EXISTS idx_todo_due_date ON t_todo(due_date);
CREATE INDEX IF NOT EXISTS idx_todo_is_deleted ON t_todo(is_deleted);

COMMENT ON TABLE t_todo IS '待办任务表';
COMMENT ON COLUMN t_todo.status IS '状态: pending/in_progress/completed/cancelled';
COMMENT ON COLUMN t_todo.priority IS '优先级: 1=低, 2=中, 3=高';
COMMENT ON COLUMN t_todo.progress IS '进度百分比: 0-100';

-- 待办历史表
CREATE TABLE IF NOT EXISTS t_todo_history (
    id SERIAL PRIMARY KEY,
    todo_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,
    changed_fields JSONB,
    old_values JSONB,
    new_values JSONB,
    confirmed_by_user BOOLEAN NOT NULL DEFAULT FALSE,
    operation_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extra_data JSONB
);

CREATE INDEX IF NOT EXISTS ix_t_todo_history_todo_id ON t_todo_history(todo_id);
CREATE INDEX IF NOT EXISTS ix_t_todo_history_user_id ON t_todo_history(user_id);

COMMENT ON TABLE t_todo_history IS '待办操作历史表';
COMMENT ON COLUMN t_todo_history.action IS '操作类型: create/update/delete/complete';

-- 提醒队列表
CREATE TABLE IF NOT EXISTS t_todo_reminder_queue (
    id SERIAL PRIMARY KEY,
    todo_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reminder_time TIMESTAMP NOT NULL,
    reminder_type VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    sent_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE t_todo_reminder_queue IS '待办提醒队列表';
COMMENT ON COLUMN t_todo_reminder_queue.status IS '状态: pending/sent/failed';

-- ============================================================
-- 问数元数据
-- ============================================================

-- 启用 vector 扩展（如果未启用）
CREATE EXTENSION IF NOT EXISTS vector;

-- 表元数据
CREATE TABLE IF NOT EXISTS t_meta_tables (
    id SERIAL PRIMARY KEY,
    schema_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    category VARCHAR(50),
    embedding VECTOR(2048),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_schema_table UNIQUE (schema_name, table_name)
);

COMMENT ON TABLE t_meta_tables IS '表元数据';

-- 列元数据
CREATE TABLE IF NOT EXISTS t_meta_columns (
    id SERIAL PRIMARY KEY,
    table_id INTEGER NOT NULL REFERENCES t_meta_tables(id) ON DELETE CASCADE,
    column_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    data_type VARCHAR(50),
    description TEXT,
    is_primary_key BOOLEAN,
    is_foreign_key BOOLEAN,
    foreign_table VARCHAR(100),
    foreign_column VARCHAR(100),
    sample_values TEXT,
    embedding VECTOR(2048),
    CONSTRAINT uq_table_column UNIQUE (table_id, column_name)
);

COMMENT ON TABLE t_meta_columns IS '列元数据';

-- 表关系元数据
CREATE TABLE IF NOT EXISTS t_meta_relations (
    id SERIAL PRIMARY KEY,
    from_table VARCHAR(100) NOT NULL,
    from_column VARCHAR(100) NOT NULL,
    to_table VARCHAR(100) NOT NULL,
    to_column VARCHAR(100) NOT NULL,
    relation_type VARCHAR(20),
    join_hint TEXT
);

COMMENT ON TABLE t_meta_relations IS '表关系元数据';

-- 指标定义表
CREATE TABLE IF NOT EXISTS t_metric_definition (
    metric_id VARCHAR(50) PRIMARY KEY,
    metric_name VARCHAR(200) NOT NULL,
    aliases TEXT,
    description TEXT NOT NULL,
    category VARCHAR(100),
    sub_category VARCHAR(100),
    unit VARCHAR(50),
    frequency VARCHAR(20),
    sql_template TEXT,
    embedding VECTOR(2048),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metric_def_name ON t_metric_definition(metric_name);
CREATE INDEX IF NOT EXISTS idx_metric_def_category ON t_metric_definition(category);

COMMENT ON TABLE t_metric_definition IS '指标定义表';
COMMENT ON COLUMN t_metric_definition.metric_id IS '指标唯一编码';
COMMENT ON COLUMN t_metric_definition.metric_name IS '指标名称';
COMMENT ON COLUMN t_metric_definition.aliases IS '别名/同义词（逗号分隔）';
COMMENT ON COLUMN t_metric_definition.description IS '自然语言口径描述（向量化核心字段）';
COMMENT ON COLUMN t_metric_definition.sql_template IS '完整SQL模板';
COMMENT ON COLUMN t_metric_definition.embedding IS '语义向量（智谱 embedding-3，2048维）';

-- 问数查询日志表
CREATE TABLE IF NOT EXISTS t_data_query_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    thread_id VARCHAR(100),
    question TEXT NOT NULL,
    generated_sql TEXT,
    sql_source VARCHAR(20),
    execution_result JSONB,
    is_correct BOOLEAN,
    corrected_sql TEXT,
    trained BOOLEAN DEFAULT FALSE,
    is_ignored BOOLEAN NOT NULL DEFAULT FALSE,
    question_embedding VECTOR(2048),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_log_user_id ON t_data_query_log(user_id);
CREATE INDEX IF NOT EXISTS idx_query_log_thread_id ON t_data_query_log(thread_id);

COMMENT ON TABLE t_data_query_log IS '问数查询日志表';
COMMENT ON COLUMN t_data_query_log.user_id IS '用户ID';
COMMENT ON COLUMN t_data_query_log.thread_id IS '会话ID';
COMMENT ON COLUMN t_data_query_log.question IS '用户原始问题';
COMMENT ON COLUMN t_data_query_log.generated_sql IS '生成的SQL';
COMMENT ON COLUMN t_data_query_log.sql_source IS '来源: metric/vanna/template';
COMMENT ON COLUMN t_data_query_log.is_correct IS '是否正确（用户反馈）';
COMMENT ON COLUMN t_data_query_log.corrected_sql IS '人工修正后的SQL';
COMMENT ON COLUMN t_data_query_log.trained IS '是否已训练进向量库';
COMMENT ON COLUMN t_data_query_log.is_ignored IS '是否已忽略（软隐藏）';
COMMENT ON COLUMN t_data_query_log.question_embedding IS '问题向量（智谱 embedding-3，2048维）';

-- ============================================================
-- AI 技能与反馈
-- ============================================================

-- AI 技能表
CREATE TABLE IF NOT EXISTS t_agent_skills (
    id SERIAL PRIMARY KEY,
    skill_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    file_hash VARCHAR(64),
    embedding VECTOR(2048),
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    auto_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 100,
    scope VARCHAR(32) NOT NULL DEFAULT 'global',
    trigger_phrases JSONB NOT NULL DEFAULT '[]'::jsonb,
    conflicts_with JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_skills_skill_id ON t_agent_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_agent_skills_embedding_ivfflat ON t_agent_skills USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_agent_skills_fts ON t_agent_skills USING gin (to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, '') || ' ' || coalesce(content, '')));
CREATE INDEX IF NOT EXISTS idx_agent_skills_trigger_phrases_gin ON t_agent_skills USING gin (trigger_phrases jsonb_path_ops);

COMMENT ON TABLE t_agent_skills IS 'AI技能表';
COMMENT ON COLUMN t_agent_skills.skill_id IS '技能唯一标识';
COMMENT ON COLUMN t_agent_skills.name IS '技能名称';
COMMENT ON COLUMN t_agent_skills.description IS '技能描述（用于向量匹配）';
COMMENT ON COLUMN t_agent_skills.content IS 'SKILL.md完整内容';
COMMENT ON COLUMN t_agent_skills.file_hash IS '文件MD5（增量同步用）';
COMMENT ON COLUMN t_agent_skills.embedding IS '语义向量（2048维）';
COMMENT ON COLUMN t_agent_skills.is_enabled IS '是否启用';
COMMENT ON COLUMN t_agent_skills.auto_enabled IS '是否允许自动触发';
COMMENT ON COLUMN t_agent_skills.priority IS '冲突裁决优先级（越小越优先）';
COMMENT ON COLUMN t_agent_skills.scope IS '技能作用域：global/data/todo/admin';
COMMENT ON COLUMN t_agent_skills.trigger_phrases IS '触发短语列表';
COMMENT ON COLUMN t_agent_skills.conflicts_with IS '冲突技能ID列表';

-- 对话反馈表
CREATE TABLE IF NOT EXISTS t_chat_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    message_id BIGINT NOT NULL,
    score INTEGER NOT NULL CHECK (score IN (-1, 0, 1)),
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_feedback_user_message UNIQUE (user_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_message_id ON t_chat_feedback(message_id);

COMMENT ON TABLE t_chat_feedback IS '对话反馈表';
COMMENT ON COLUMN t_chat_feedback.score IS '评分: -1=差评, 0=中立, 1=好评';
COMMENT ON COLUMN t_chat_feedback.reason IS '反馈原因';

-- ============================================================
-- LLM 配置
-- ============================================================

-- 模型提供商表
CREATE TABLE IF NOT EXISTS t_llm_provider (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    base_url VARCHAR(500),
    api_key VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    extra_config JSONB,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE t_llm_provider IS 'LLM提供商表';
COMMENT ON COLUMN t_llm_provider.code IS '提供商代码: qwen/deepseek/openai';
COMMENT ON COLUMN t_llm_provider.name IS '显示名称';
COMMENT ON COLUMN t_llm_provider.base_url IS 'API基础地址';
COMMENT ON COLUMN t_llm_provider.api_key IS 'API Key';

-- 模型表
CREATE TABLE IF NOT EXISTS t_llm_model (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER NOT NULL REFERENCES t_llm_provider(id) ON DELETE CASCADE,
    model_code VARCHAR(100) NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    model_type VARCHAR(50) DEFAULT 'chat',
    supports_thinking BOOLEAN DEFAULT false,
    supports_tool_call BOOLEAN DEFAULT true,
    supports_streaming BOOLEAN DEFAULT true,
    max_output_tokens INTEGER DEFAULT 4096,
    context_window INTEGER DEFAULT 32000,
    default_temperature FLOAT DEFAULT 0.7,
    thinking_budget INTEGER DEFAULT 4096,
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    rpm_limit INTEGER,
    tpm_limit INTEGER,
    extra_config JSONB,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider_id, model_code)
);

CREATE INDEX IF NOT EXISTS idx_llm_model_provider ON t_llm_model(provider_id);
CREATE INDEX IF NOT EXISTS idx_llm_model_active ON t_llm_model(is_active) WHERE is_active = true;

COMMENT ON TABLE t_llm_model IS 'LLM模型表';
COMMENT ON COLUMN t_llm_model.model_code IS '模型代码: qwen-plus/deepseek-reasoner';
COMMENT ON COLUMN t_llm_model.model_type IS '类型: chat/reasoning/embedding';
COMMENT ON COLUMN t_llm_model.supports_thinking IS '支持深度思考';
COMMENT ON COLUMN t_llm_model.supports_tool_call IS '支持工具调用';

-- 系统配置表
CREATE TABLE IF NOT EXISTS t_system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    value_type VARCHAR(20) DEFAULT 'string',
    category VARCHAR(50),
    description TEXT,
    is_secret BOOLEAN DEFAULT false,
    is_readonly BOOLEAN DEFAULT false,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_config_category ON t_system_config(category);

COMMENT ON TABLE t_system_config IS '系统配置表';
COMMENT ON COLUMN t_system_config.config_key IS '配置键: ai.message_max_tokens';
COMMENT ON COLUMN t_system_config.value_type IS '类型: string/number/boolean/json';
COMMENT ON COLUMN t_system_config.is_secret IS '是否敏感（UI掩码显示）';

-- 默认系统配置（关键特性开关）
INSERT INTO t_system_config (config_key, config_value, value_type, category, description, is_secret, is_readonly)
VALUES
    ('feature.proxy_experiment_enabled', 'false', 'boolean', 'feature', '中转供应商实验总开关（建议仅开发/测试开启）', false, false),
    ('feature.proxy_experiment_providers', 'openai_proxy_trial', 'string', 'feature', '中转实验 provider 白名单（逗号分隔）', false, false),
    ('feature.enable_user_preference_memory', 'true', 'boolean', 'feature', '跨会话用户偏好记忆总开关', false, false),
    ('memory.user_preference_bootstrap_template', '{"assistant.persona":"小嘉"}', 'json', 'memory', '新用户偏好记忆初始化模板（JSON）', false, false),
    ('feature.enable_document_memory', 'false', 'boolean', 'feature', '文档化永久记忆总开关（两表）', false, false),
    ('feature.enable_document_memory_recall', 'false', 'boolean', 'feature', '文档化记忆召回开关', false, false),
    ('feature.enable_document_memory_flush', 'false', 'boolean', 'feature', '文档化记忆写入开关', false, false),
    ('feature.enable_document_memory_hybrid_search', 'false', 'boolean', 'feature', '文档记忆混合检索开关（FTS+向量）', false, false),
    ('feature.enable_document_memory_embedding_worker', 'false', 'boolean', 'feature', '文档记忆向量异步补偿开关', false, false),
    ('feature.enable_document_memory_admin_api', 'false', 'boolean', 'feature', '文档记忆后台运维 API 开关', false, false),
    ('memory.document.max_results', '6', 'number', 'memory', '文档记忆检索结果上限', false, false),
    ('memory.document.max_injected_chars', '1200', 'number', 'memory', '文档记忆注入预算（字符）', false, false),
    ('memory.document.hybrid.vector_weight', '0.7', 'number', 'memory', '文档记忆向量权重', false, false),
    ('memory.document.hybrid.text_weight', '0.3', 'number', 'memory', '文档记忆文本权重', false, false),
    ('memory.document.hybrid.min_score', '0.05', 'number', 'memory', '文档记忆混合召回最低分', false, false),
    ('memory.document.embedding.batch_size', '32', 'number', 'memory', '文档记忆向量补偿批大小', false, false),
    ('memory.document.embedding.max_retry', '3', 'number', 'memory', '文档记忆向量自动重试上限', false, false)
ON CONFLICT (config_key) DO NOTHING;

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
   NEW.update_time = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_llm_provider_modtime ON t_llm_provider;
CREATE TRIGGER update_llm_provider_modtime BEFORE UPDATE ON t_llm_provider FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

DROP TRIGGER IF EXISTS update_llm_model_modtime ON t_llm_model;
CREATE TRIGGER update_llm_model_modtime BEFORE UPDATE ON t_llm_model FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

DROP TRIGGER IF EXISTS update_system_config_modtime ON t_system_config;
CREATE TRIGGER update_system_config_modtime BEFORE UPDATE ON t_system_config FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

-- ============================================================
-- 注意：以下表由其他方式创建
-- ============================================================
-- LangGraph Checkpoint 表：由 AsyncPostgresSaver.setup() 自动创建
-- 业务数据表（fdmdata/sdmdata）：由 install/data_import/ 脚本创建
