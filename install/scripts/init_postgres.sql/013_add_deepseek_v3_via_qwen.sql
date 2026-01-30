-- 013. Add DeepSeek-V3.2 model via Qwen provider
-- Migration number: 013
-- Description: 添加 DeepSeek-V3.2 模型 (通过千问供应商) 并设为默认

-- 1. 重置所有现有模型的默认状态
UPDATE t_llm_model SET is_default = false WHERE is_default = true;

-- 2. 删除旧的 deepseek-v3 模型（如果存在）
DELETE FROM t_llm_model WHERE model_code = 'deepseek-v3';

-- 3. 添加 deepseek-v3.2 模型
INSERT INTO t_llm_model (
    provider_id, 
    model_code, 
    model_name, 
    model_type,
    supports_thinking, 
    supports_tool_call, 
    supports_streaming,
    max_output_tokens,
    context_window,
    default_temperature,
    thinking_budget,
    description,
    sort_order,
    is_default,
    is_active,
    extra_config,
    create_time,
    update_time
) 
SELECT 
    p.id,
    'deepseek-v3.2',
    'DeepSeek-V3.2',
    'chat',
    false,   -- V3.2 是标准对话模型，暂不启用 thinking
    true,    -- 支持 function calling
    true,    -- 支持流式输出
    8192,    -- 最大输出 token (根据 DashScope 文档)
    65536,   -- 64k context (DashScope 限制)
    0.7,
    0,       -- 不需要 thinking budget
    'DeepSeek-V3.2 模型（通过阿里云 DashScope 接入）。最新版本，性能更强，支持工具调用。',
    1,       -- 排序第一，设为默认
    true,    -- 设为默认
    true,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM t_llm_provider p
WHERE p.code = 'qwen'  -- 确保使用 qwen provider
AND NOT EXISTS (
    SELECT 1 FROM t_llm_model WHERE model_code = 'deepseek-v3.2'
);

-- 如果模型已存在 (例如重复运行)，则强制更新它为默认
UPDATE t_llm_model 
SET is_default = true, sort_order = 1 
WHERE model_code = 'deepseek-v3.2';
