-- 021. 添加 Kimi K2 系列模型 (通过千问供应商)
-- Migration number: 021
-- Description: 添加 kimi-k2-thinking 和 kimi-k2.5 模型 (通过阿里云 DashScope 接入)

-- 1. 添加 kimi-k2-thinking 模型
-- Kimi K2 Thinking 是月之暗面 (Moonshot AI) 推出的深度推理模型，仅支持思考模式，
-- 通过 reasoning_content 字段展示思考过程。基于 MoE 架构，约 1T 总参数，32B 激活参数。
-- 具有卓越的编码和工具调用能力，适用于逻辑分析、规划或深度理解场景。
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
    'kimi-k2-thinking',
    'Kimi K2 Thinking',
    'reasoning',
    true,    -- 仅支持深度思考模式（始终开启）
    true,    -- 支持 Function Calling 和结构化输出
    true,    -- 支持流式输出
    16384,   -- 最大输出 16K token
    262144,  -- 256K 上下文窗口
    1.0,     -- DashScope 默认温度 1.0
    32768,   -- 最大思维链长度 32K
    'Kimi K2 Thinking（月之暗面）：深度推理模型，基于 MoE 架构（约 1T 总参数 / 32B 激活参数），仅支持思考模式。在编码、数学推理、逻辑分析和工具调用方面表现卓越，适合需要深度理解和多步骤规划的复杂任务。通过阿里云 DashScope 接入。',
    5,       -- 排序
    false,
    true,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM t_llm_provider p
WHERE p.code = 'qwen'
AND NOT EXISTS (
    SELECT 1 FROM t_llm_model WHERE model_code = 'kimi-k2-thinking'
);

-- 2. 添加 kimi-k2.5 模型
-- Kimi K2.5 是月之暗面迄今最全能的旗舰模型，在 Agent、代码生成、视觉理解等任务上
-- 取得开源 SOTA 表现。同时支持图像/视频/文本输入、思考与非思考模式切换。
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
    'kimi-k2.5',
    'Kimi K2.5',
    'chat',
    true,    -- 支持思考模式（可通过 enable_thinking 开关切换）
    true,    -- 支持 Function Calling
    true,    -- 支持流式输出
    32768,   -- 最大输出 32K token
    262144,  -- 256K 上下文窗口
    0.6,     -- DashScope 非思考模式默认温度 0.6
    32768,   -- 最大思维链长度 32K
    'Kimi K2.5（月之暗面）：迄今最全能的旗舰模型，在 Agent、代码生成、视觉理解及通用智能任务上取得开源 SOTA 表现。支持图像/视频/文本多模态输入，可切换思考与非思考模式。适合需要综合能力的复杂场景。通过阿里云 DashScope 接入。',
    6,       -- 排序
    false,
    true,
    '{}'::jsonb,
    NOW(),
    NOW()
FROM t_llm_provider p
WHERE p.code = 'qwen'
AND NOT EXISTS (
    SELECT 1 FROM t_llm_model WHERE model_code = 'kimi-k2.5'
);
