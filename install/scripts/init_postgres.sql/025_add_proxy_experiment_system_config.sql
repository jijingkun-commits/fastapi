-- 025: 补齐中转实验统一配置（t_system_config）
-- 背景: 中转实验开关收敛为后台两参数控制（总开关 + provider 白名单）
-- 影响: chat_db.t_system_config
-- 执行: ./deploy.sh dev migrate 或 ./deploy.sh prod migrate

INSERT INTO t_system_config (config_key, config_value, value_type, category, description, is_secret, is_readonly)
VALUES
    ('feature.proxy_experiment_enabled', 'false', 'boolean', 'feature', '中转供应商实验总开关（建议仅开发/测试开启）', false, false),
    ('feature.proxy_experiment_providers', 'openai_proxy_trial', 'string', 'feature', '中转实验 provider 白名单（逗号分隔）', false, false)
ON CONFLICT (config_key) DO NOTHING;
