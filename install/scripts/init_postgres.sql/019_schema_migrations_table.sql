-- 迁移版本控制表
-- 记录已执行的迁移脚本，防止重复执行
-- 日期：2026-01-30

-- 1. 创建迁移记录表
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL UNIQUE,      -- 迁移版本号（如 "018"）
    script_name VARCHAR(255) NOT NULL,         -- 脚本文件名
    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INT,                     -- 执行耗时（毫秒）
    checksum VARCHAR(64),                      -- 脚本内容校验和（可选）
    applied_by VARCHAR(100),                   -- 执行者（可选）
    notes TEXT                                 -- 备注
);

COMMENT ON TABLE schema_migrations IS '数据库迁移版本记录表';
COMMENT ON COLUMN schema_migrations.version IS '迁移版本号，如 001, 002';
COMMENT ON COLUMN schema_migrations.script_name IS '执行的脚本文件名';
COMMENT ON COLUMN schema_migrations.checksum IS '脚本内容的 SHA256 校验和';

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
ON schema_migrations(version);

-- 3. 插入已知的历史迁移记录（补录）
-- 这些脚本已经执行过，需要记录以防止重复执行
INSERT INTO schema_migrations (version, script_name, notes) VALUES
    ('001', 'init_postgres.sql', '初始化表结构'),
    ('003', '003_llm_config.sql', 'LLM 配置表'),
    ('004', '004_create_todo_table.sql', '待办表'),
    ('006', '006_add_vision_models.sql', '视觉模型'),
    ('007', '007_upgrade_todo_tables.sql', '待办表升级'),
    ('008', '008_add_logical_delete.sql', '逻辑删除'),
    ('009', '009_phase4_advanced_features.sql', '高级功能'),
    ('010', '010_optimization_phase1.sql', '优化阶段1'),
    ('011', '011_add_qwen_flash_model.sql', 'Qwen Flash 模型'),
    ('012', '012_add_glm_45v_model.sql', 'GLM 4.5V 模型'),
    ('013', '013_add_deepseek_v3_via_qwen.sql', 'DeepSeek V3'),
    ('014', '014_add_data_permissions.sql', '数据权限'),
    ('015', '015_cleanup_deprecated_tables.sql', '清理废弃表'),
    ('016', '016_expand_metrics.sql', '扩展指标'),
    ('017', '017_add_idempotency_key.sql', '幂等性键'),
    ('018', '018_add_composite_indexes.sql', '复合索引'),
    ('019', '019_schema_migrations_table.sql', '迁移版本控制表')
ON CONFLICT (version) DO NOTHING;

-- 4. 验证
DO $$
DECLARE
    cnt INT;
BEGIN
    SELECT COUNT(*) INTO cnt FROM schema_migrations;
    RAISE NOTICE '✅ 迁移版本控制表创建完成，已记录 % 个版本', cnt;
END $$;
