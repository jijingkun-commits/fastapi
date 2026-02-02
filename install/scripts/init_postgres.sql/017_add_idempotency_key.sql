-- 017_add_idempotency_key.sql
-- 幂等键记录表，用于防重复提交

CREATE TABLE IF NOT EXISTS t_idempotency_key (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR(64) NOT NULL,
    user_id INTEGER,
    endpoint VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'started',
    thread_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (key, endpoint, user_id)
);

COMMENT ON TABLE t_idempotency_key IS '幂等键记录表';
COMMENT ON COLUMN t_idempotency_key.key IS '幂等键';
COMMENT ON COLUMN t_idempotency_key.endpoint IS '端点标识';
COMMENT ON COLUMN t_idempotency_key.status IS '状态: started/completed/failed';
COMMENT ON COLUMN t_idempotency_key.thread_id IS '对话线程ID';
