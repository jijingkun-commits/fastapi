-- 032: 记忆管理动作审计表
-- 背景: 记录管理接口关键动作与执行结果，满足审计追踪要求
-- 影响: chat_db.t_user_memory_admin_audit
-- 执行: ./deploy.sh dev migrate 或 ./deploy.sh prod migrate

CREATE TABLE IF NOT EXISTS t_user_memory_admin_audit (
    id BIGSERIAL PRIMARY KEY,
    operator_user_id INTEGER NOT NULL,
    target_user_id INTEGER,
    memory_id BIGINT,
    action VARCHAR(64) NOT NULL,
    action_payload JSONB,
    result_status VARCHAR(16) NOT NULL,
    error_message TEXT,
    create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memory_admin_audit_operator_time
    ON t_user_memory_admin_audit(operator_user_id, create_time);
CREATE INDEX IF NOT EXISTS idx_memory_admin_audit_target_time
    ON t_user_memory_admin_audit(target_user_id, create_time);
CREATE INDEX IF NOT EXISTS idx_memory_admin_audit_memory_time
    ON t_user_memory_admin_audit(memory_id, create_time);

COMMENT ON TABLE t_user_memory_admin_audit IS '记忆管理动作审计表';
COMMENT ON COLUMN t_user_memory_admin_audit.operator_user_id IS '操作人用户ID';
COMMENT ON COLUMN t_user_memory_admin_audit.target_user_id IS '目标用户ID';
COMMENT ON COLUMN t_user_memory_admin_audit.memory_id IS '记忆文档ID';
COMMENT ON COLUMN t_user_memory_admin_audit.action IS '管理动作';
COMMENT ON COLUMN t_user_memory_admin_audit.action_payload IS '动作上下文';
COMMENT ON COLUMN t_user_memory_admin_audit.result_status IS '执行结果';
COMMENT ON COLUMN t_user_memory_admin_audit.error_message IS '失败原因';
