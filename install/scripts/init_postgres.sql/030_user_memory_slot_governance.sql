-- 030_user_memory_slot_governance: 槽位治理字段与开关
-- 背景: 支持 slot_key 归一化、同槽位覆盖归档、乱序保护
-- 影响: chat_db.t_user_memory_document / chat_db.t_system_config

ALTER TABLE t_user_memory_document
    ADD COLUMN IF NOT EXISTS slot_key VARCHAR(128);

ALTER TABLE t_user_memory_document
    ADD COLUMN IF NOT EXISTS operation VARCHAR(32) NOT NULL DEFAULT 'upsert';

ALTER TABLE t_user_memory_document
    ADD COLUMN IF NOT EXISTS last_event_time TIMESTAMP;

UPDATE t_user_memory_document
SET
    slot_key = COALESCE(NULLIF(slot_key, ''), doc_key),
    operation = COALESCE(NULLIF(operation, ''), 'upsert')
WHERE slot_key IS NULL
   OR slot_key = ''
   OR operation IS NULL
   OR operation = '';

CREATE INDEX IF NOT EXISTS idx_user_memory_document_user_slot
    ON t_user_memory_document(user_id, slot_key, status);

CREATE INDEX IF NOT EXISTS idx_user_memory_document_slot_event
    ON t_user_memory_document(user_id, slot_key, last_event_time);

INSERT INTO t_system_config (config_key, config_value, value_type, category, description, is_secret, is_readonly)
VALUES
    ('memory.slot_governance_enabled', 'true', 'boolean', 'memory', '用户记忆槽位治理开关（同槽位覆盖归档）', false, false)
ON CONFLICT (config_key) DO UPDATE
SET
    config_value = EXCLUDED.config_value,
    value_type = EXCLUDED.value_type,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    is_secret = EXCLUDED.is_secret,
    is_readonly = EXCLUDED.is_readonly;
