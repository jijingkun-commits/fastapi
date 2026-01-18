-- PostgreSQL 初始化脚本（中文注释）
-- 用于 Docker 容器首次启动时自动执行

-- 用户表
CREATE TABLE IF NOT EXISTS t_user (
    id SERIAL PRIMARY KEY,
    "userName" VARCHAR(200),
    password VARCHAR(300),
    mobile VARCHAR(100),
    "createTime" TIMESTAMP,
    "updateTime" TIMESTAMP
);

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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_chat_message_user_id ON t_chat_message(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_thread_id ON t_chat_message(thread_id);

-- 注意：LangGraph Checkpoint 表由 AsyncPostgresSaver.setup() 自动创建
-- 包括 checkpoints 和 writes 两张表
