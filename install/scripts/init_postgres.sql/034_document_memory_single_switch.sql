-- 034: 文档记忆单开关收敛
-- 背景: 用户个性化永久记忆切换到纯文档 + 单开关模式
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
    ('feature.enable_document_memory', 'false', 'boolean', 'feature', '用户个性化永久记忆总开关（纯文档）', false, false)
ON CONFLICT (config_key) DO UPDATE
SET
    config_value = EXCLUDED.config_value,
    value_type = EXCLUDED.value_type,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    is_secret = EXCLUDED.is_secret,
    is_readonly = EXCLUDED.is_readonly;

DELETE FROM t_system_config
WHERE config_key IN (
    'feature.enable_user_preference_memory',
    'feature.enable_document_memory_recall',
    'feature.enable_document_memory_flush',
    'feature.enable_document_memory_hybrid_search',
    'feature.enable_document_memory_embedding_worker',
    'feature.enable_document_memory_admin_api',
    'feature.enable_document_memory_admin_web',
    'feature.enable_document_memory_admin_audit'
);
