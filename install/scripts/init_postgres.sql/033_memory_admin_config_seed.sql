-- 033: memory-admin 配置补齐（分页配置）
-- 背景: 单开关模式下仅保留分页与预算参数
-- 影响: chat_db.t_system_config
-- 执行: ./deploy.sh dev migrate 或 ./deploy.sh prod migrate

INSERT INTO t_system_config (
    config_key,
    config_value,
    value_type,
    category,
    description,
    is_secret,
    is_readonly
)
VALUES
    ('memory.document.admin.default_page_size', '20', 'number', 'memory', '文档记忆后台管理默认分页大小', false, false),
    ('memory.document.admin.max_page_size', '100', 'number', 'memory', '文档记忆后台管理最大分页大小', false, false)
ON CONFLICT (config_key) DO UPDATE
SET
    config_value = EXCLUDED.config_value,
    value_type = EXCLUDED.value_type,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    is_secret = EXCLUDED.is_secret,
    is_readonly = EXCLUDED.is_readonly;
