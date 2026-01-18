-- 011. 添加 Qwen Flash 模型
-- Migration number: 011
-- Description: 添加通义千问 qwen-flash 模型

-- 添加 qwen-flash 模型
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
    extra_config
) 
SELECT 
    1,  -- qwen provider
    'qwen-flash',
    'Qwen Flash',
    'chat',
    true,   -- 支持深度思考模式（可切换）
    true,   -- 支持 function calling
    true,   -- 支持流式输出
    8192,   -- 最大输出 token
    1000000, -- 1M 上下文窗口
    0.7,
    4096,
    'Qwen3 系列 Flash 模型，支持思考模式和非思考模式的有效融合，可在对话中切换模式。复杂推理类任务性能优秀，支持 1M 上下文长度，价格实惠。',
    2,      -- 排序（在 qwen-plus 后面）
    false,
    true,
    '{}'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM t_llm_model WHERE model_code = 'qwen-flash'
);
