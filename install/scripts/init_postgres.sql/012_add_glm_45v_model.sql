-- 添加智谱 GLM-4.5V 推理模型
-- 重要说明：
-- 1. glm-4.5v 不支持标准的 Function Calling / Tool Calls，仅适合纯对话场景
-- 2. 智谱推理模型不需要 enable_thinking 参数（这是 Qwen 特有的）

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
    description,
    sort_order,
    is_default,
    is_active,
    create_time,
    update_time
)
SELECT 
    p.id,
    'glm-4.5v',
    'GLM-4.5V (推理)',
    'chat',
    false,  -- 智谱不支持 enable_thinking 参数
    false,  -- glm-4.5v 不支持标准 Tool Calls
    true,
    4096,
    128000,
    0.7,
    '智谱 GLM-4.5V 深度推理模型（不支持工具调用，仅适合纯对话场景）',
    3,
    false,
    true,
    NOW(),
    NOW()
FROM t_llm_provider p
WHERE p.code = 'zhipu'
AND NOT EXISTS (
    SELECT 1 FROM t_llm_model WHERE model_code = 'glm-4.5v'
);
