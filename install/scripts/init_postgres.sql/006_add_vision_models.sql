-- 添加智谱 Vision 模型配置
-- model_type = 'vision' 表示这是一个视觉理解模型

-- 首先确保智谱提供商存在
INSERT INTO t_llm_provider (code, name, base_url, api_key, is_active, sort_order, create_time, update_time)
SELECT 'zhipu', '智谱 AI', 'https://open.bigmodel.cn/api/paas/v4', '', true, 20, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM t_llm_provider WHERE code = 'zhipu');

-- 更新智谱提供商的 API Key（如果已存在）
-- 注意：需要手动替换 YOUR_ZHIPU_API_KEY
-- UPDATE t_llm_provider SET api_key = 'YOUR_ZHIPU_API_KEY' WHERE code = 'zhipu';

-- 插入 Vision 模型
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
    'glm-4v-flash',
    'GLM-4V Flash',
    'vision',
    false,
    false,
    true,
    1024,
    8000,
    0.7,
    '智谱 GLM-4V Flash 视觉理解模型，支持图片分析',
    1,
    true,  -- 设为 vision 类型的默认模型
    true,
    NOW(),
    NOW()
FROM t_llm_provider p
WHERE p.code = 'zhipu'
AND NOT EXISTS (
    SELECT 1 FROM t_llm_model WHERE model_code = 'glm-4v-flash'
);

-- 也可以添加其他 Vision 模型，如：
-- glm-4v-plus (更强大但更贵)
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
    'glm-4v-plus',
    'GLM-4V Plus',
    'vision',
    false,
    false,
    true,
    4096,
    16000,
    0.7,
    '智谱 GLM-4V Plus 高级视觉理解模型',
    2,
    false,
    true,
    NOW(),
    NOW()
FROM t_llm_provider p
WHERE p.code = 'zhipu'
AND NOT EXISTS (
    SELECT 1 FROM t_llm_model WHERE model_code = 'glm-4v-plus'
);
