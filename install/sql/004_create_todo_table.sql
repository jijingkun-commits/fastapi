-- ==============================================
-- 待办事项表 t_todo
-- 用于存储用户的待办任务
-- ==============================================

CREATE TABLE IF NOT EXISTS t_todo (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,                           -- 用户ID
    title VARCHAR(255) NOT NULL,                        -- 待办标题
    description TEXT,                                   -- 详细描述
    is_completed BOOLEAN DEFAULT FALSE,                 -- 是否已完成
    priority INTEGER DEFAULT 2,                         -- 优先级 1=低 2=中 3=高
    due_date TIMESTAMP,                                 -- 截止日期
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,    -- 创建时间
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- 更新时间
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_todo_user_id ON t_todo(user_id);
CREATE INDEX IF NOT EXISTS idx_todo_user_completed ON t_todo(user_id, is_completed);

COMMENT ON TABLE t_todo IS '待办事项表';
COMMENT ON COLUMN t_todo.user_id IS '用户ID';
COMMENT ON COLUMN t_todo.title IS '待办标题';
COMMENT ON COLUMN t_todo.description IS '详细描述';
COMMENT ON COLUMN t_todo.is_completed IS '是否已完成';
COMMENT ON COLUMN t_todo.priority IS '优先级 1=低 2=中 3=高';
COMMENT ON COLUMN t_todo.due_date IS '截止日期';
