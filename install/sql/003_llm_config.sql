-- 3. LLM Configuration Tables
-- Migration number: 003
-- Description: Create tables for LLM providers, models, and system configuration.

-- 1. 模型提供商表
CREATE TABLE IF NOT EXISTS t_llm_provider (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,           -- 提供商代码: qwen, deepseek, openai
    name VARCHAR(100) NOT NULL,                 -- 显示名称: 阿里通义, DeepSeek
    base_url VARCHAR(500),                      -- API 基础地址
    api_key VARCHAR(500),                       -- API Key (明文存储)
    is_active BOOLEAN DEFAULT true,             -- 是否启用
    sort_order INTEGER DEFAULT 0,               -- 排序
    extra_config JSONB,                         -- 额外配置 (timeout, retries 等)
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 模型表
CREATE TABLE IF NOT EXISTS t_llm_model (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER NOT NULL REFERENCES t_llm_provider(id) ON DELETE CASCADE,
    model_code VARCHAR(100) NOT NULL,           -- 模型代码: qwen-plus, deepseek-reasoner
    model_name VARCHAR(200) NOT NULL,           -- 显示名称
    model_type VARCHAR(50) DEFAULT 'chat',      -- 类型: chat, reasoning, embedding
    
    -- 能力标记
    supports_thinking BOOLEAN DEFAULT false,    -- 支持深度思考
    supports_tool_call BOOLEAN DEFAULT true,    -- 支持工具调用
    supports_streaming BOOLEAN DEFAULT true,    -- 支持流式输出
    max_output_tokens INTEGER DEFAULT 4096,     -- 最大输出 token
    context_window INTEGER DEFAULT 32000,       -- 上下文窗口大小
    
    -- 默认参数
    default_temperature FLOAT DEFAULT 0.7,
    thinking_budget INTEGER DEFAULT 4096,       -- 思考 token 预算
    
    -- 显示配置
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_default BOOLEAN DEFAULT false,           -- 是否为默认模型
    is_active BOOLEAN DEFAULT true,             -- 是否启用
    
    -- 速率限制
    rpm_limit INTEGER,                          -- 每分钟请求数限制
    tpm_limit INTEGER,                          -- 每分钟 token 限制
    
    extra_config JSONB,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(provider_id, model_code)
);

-- 3. 系统配置表（通用键值对）
CREATE TABLE IF NOT EXISTS t_system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,    -- 配置键: ai.message_max_tokens
    config_value TEXT NOT NULL,                 -- 配置值 (JSON 或字符串)
    value_type VARCHAR(20) DEFAULT 'string',    -- 类型: string, number, boolean, json
    category VARCHAR(50),                       -- 分类: ai, minio, mcp
    description TEXT,                           -- 配置说明
    is_secret BOOLEAN DEFAULT false,            -- 是否敏感 (UI 隐藏/掩码显示)
    is_readonly BOOLEAN DEFAULT false,          -- 是否只读
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_llm_model_provider ON t_llm_model(provider_id);
CREATE INDEX IF NOT EXISTS idx_llm_model_active ON t_llm_model(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_system_config_category ON t_system_config(category);

-- Triggers for update_time
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
