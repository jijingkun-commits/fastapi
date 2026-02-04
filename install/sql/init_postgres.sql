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

-- ============================================================
-- 注意：以下表由其他脚本创建
-- ============================================================
-- LangGraph Checkpoint 表：由 AsyncPostgresSaver.setup() 自动创建
-- LLM 配置表：由 install/sql/003_llm_config.sql 创建
-- 技能表：由 scripts/init_skill_config.py 创建
-- 指标表：由 install/data_import/ 脚本创建
