-- 029: 用户偏好记忆总开关 + 新用户初始化模板
-- 背景: 统一为单开关 feature.enable_user_preference_memory，并支持新用户默认 AI 人设模板
-- 影响: chat_db.t_system_config
-- 执行: ./deploy.sh dev migrate 或 ./deploy.sh prod migrate

INSERT INTO t_system_config (config_key, config_value, value_type, category, description, is_secret, is_readonly)
VALUES
    ('feature.enable_user_preference_memory', 'true', 'boolean', 'feature', '跨会话用户偏好记忆总开关', false, false)
ON CONFLICT (config_key) DO UPDATE
SET
    config_value = EXCLUDED.config_value,
    value_type = EXCLUDED.value_type,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    is_secret = EXCLUDED.is_secret,
    is_readonly = EXCLUDED.is_readonly;

INSERT INTO t_system_config (config_key, config_value, value_type, category, description, is_secret, is_readonly)
VALUES
    ('memory.user_preference_bootstrap_template', '{"assistant.persona":"小嘉"}', 'json', 'memory', '新用户偏好记忆初始化模板（JSON）', false, false)
ON CONFLICT (config_key) DO NOTHING;
