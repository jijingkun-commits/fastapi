-- 033: memory-admin 配置补齐（web/audit 开关 + 分页配置）
-- 背景: 管理后台入口、审计开关与分页上限需要可配置并支持灰度回滚
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
    ('feature.enable_document_memory_admin_api', 'false', 'boolean', 'feature', '文档记忆后台运维 API 开关', false, false),
    ('feature.enable_document_memory_admin_web', 'false', 'boolean', 'feature', '文档记忆后台管理页面开关', false, false),
    ('feature.enable_document_memory_admin_audit', 'false', 'boolean', 'feature', '文档记忆后台管理审计开关', false, false),
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
