-- 待办事项表升级脚本
-- 新增字段以支持完整的待办管理功能

-- 1. 新增字段到 t_todo 表
DO $$
BEGIN
    -- 时间管理字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='start_time') THEN
        ALTER TABLE t_todo ADD COLUMN start_time TIMESTAMP(6);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='actual_completion_time') THEN
        ALTER TABLE t_todo ADD COLUMN actual_completion_time TIMESTAMP(6);
    END IF;
    
    -- 状态管理字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='status') THEN
        ALTER TABLE t_todo ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'todo';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='progress') THEN
        ALTER TABLE t_todo ADD COLUMN progress INT4 DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='progress_notes') THEN
        ALTER TABLE t_todo ADD COLUMN progress_notes TEXT;
    END IF;
    
    -- 分类字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='category') THEN
        ALTER TABLE t_todo ADD COLUMN category VARCHAR(50);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='tags') THEN
        ALTER TABLE t_todo ADD COLUMN tags JSONB;
    END IF;
    
    -- 提醒配置字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='reminder_enabled') THEN
        ALTER TABLE t_todo ADD COLUMN reminder_enabled BOOL DEFAULT false;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='reminder_type') THEN
        ALTER TABLE t_todo ADD COLUMN reminder_type VARCHAR(20);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='reminder_advance_minutes') THEN
        ALTER TABLE t_todo ADD COLUMN reminder_advance_minutes INT4;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='reminder_times') THEN
        ALTER TABLE t_todo ADD COLUMN reminder_times JSONB;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='last_reminded_at') THEN
        ALTER TABLE t_todo ADD COLUMN last_reminded_at TIMESTAMP(6);
    END IF;
    
    -- 元数据字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='metadata') THEN
        ALTER TABLE t_todo ADD COLUMN metadata JSONB;
    END IF;
END $$;

-- 2. 添加注释
COMMENT ON COLUMN t_todo.start_time IS '开始时间';
COMMENT ON COLUMN t_todo.actual_completion_time IS '实际完成时间';
COMMENT ON COLUMN t_todo.status IS '状态：todo/in_progress/done/cancelled';
COMMENT ON COLUMN t_todo.progress IS '进度百分比 (0-100)';
COMMENT ON COLUMN t_todo.progress_notes IS '具体进展说明';
COMMENT ON COLUMN t_todo.category IS '分类标签';
COMMENT ON COLUMN t_todo.tags IS '标签数组';
COMMENT ON COLUMN t_todo.reminder_enabled IS '是否启用提醒';
COMMENT ON COLUMN t_todo.reminder_type IS '提醒方式：email/notification/both';
COMMENT ON COLUMN t_todo.reminder_advance_minutes IS '提前多少分钟提醒';
COMMENT ON COLUMN t_todo.reminder_times IS '多次提醒时间点';
COMMENT ON COLUMN t_todo.last_reminded_at IS '最后提醒时间';
COMMENT ON COLUMN t_todo.metadata IS '扩展元数据';

-- 3. 创建新增索引
CREATE INDEX IF NOT EXISTS idx_todo_status ON t_todo(status);
CREATE INDEX IF NOT EXISTS idx_todo_due_date ON t_todo(due_date);
CREATE INDEX IF NOT EXISTS idx_todo_reminder ON t_todo(reminder_enabled, reminder_advance_minutes) WHERE reminder_enabled = true;
CREATE INDEX IF NOT EXISTS idx_todo_user_status_due ON t_todo(user_id, status, due_date);

-- 4. 数据迁移：补齐空 status，统一以状态字段表达完成态
UPDATE t_todo 
SET status = CASE 
    WHEN COALESCE(progress, 0) >= 100 OR actual_completion_time IS NOT NULL THEN 'done' 
    ELSE 'todo' 
END
WHERE status IS NULL OR status = '';

-- 5. 创建待办操作日志表
CREATE TABLE IF NOT EXISTS t_todo_history (
    id BIGSERIAL PRIMARY KEY,
    todo_id BIGINT NOT NULL,
    user_id INT4 NOT NULL,
    action VARCHAR(20) NOT NULL,                -- create/update/delete/complete/cancel
    changed_fields JSONB,                       -- 记录变更的字段
    old_values JSONB,                           -- 变更前的值
    new_values JSONB,                           -- 变更后的值
    confirmed_by_user BOOL DEFAULT false,       -- 是否经过用户确认
    operation_time TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

COMMENT ON TABLE t_todo_history IS '待办操作历史记录表';
COMMENT ON COLUMN t_todo_history.action IS '操作类型：create/update/delete/complete/cancel';
COMMENT ON COLUMN t_todo_history.confirmed_by_user IS '是否经过用户确认';

CREATE INDEX IF NOT EXISTS idx_todo_history_todo_id ON t_todo_history(todo_id);
CREATE INDEX IF NOT EXISTS idx_todo_history_user_id ON t_todo_history(user_id);

-- 6. 创建提醒队列表
CREATE TABLE IF NOT EXISTS t_todo_reminder_queue (
    id BIGSERIAL PRIMARY KEY,
    todo_id BIGINT NOT NULL,
    user_id INT4 NOT NULL,
    reminder_time TIMESTAMP(6) NOT NULL,        -- 计划提醒时间
    reminder_type VARCHAR(20),                  -- email/notification/both
    status VARCHAR(20) DEFAULT 'pending',       -- pending/sent/failed
    sent_at TIMESTAMP(6),                       -- 实际发送时间
    error_message TEXT,                         -- 失败原因
    retry_count INT4 DEFAULT 0,                 -- 重试次数
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE t_todo_reminder_queue IS '待办提醒任务队列';
COMMENT ON COLUMN t_todo_reminder_queue.status IS '提醒状态：pending/sent/failed';

CREATE INDEX IF NOT EXISTS idx_reminder_queue_time ON t_todo_reminder_queue(reminder_time, status);
CREATE INDEX IF NOT EXISTS idx_reminder_queue_user ON t_todo_reminder_queue(user_id, status);

-- 7. 输出执行结果
DO $$
DECLARE
    todo_count INT;
    history_count INT;
    queue_count INT;
BEGIN
    SELECT COUNT(*) INTO todo_count FROM t_todo;
    SELECT COUNT(*) INTO history_count FROM t_todo_history;
    SELECT COUNT(*) INTO queue_count FROM t_todo_reminder_queue;
    
    RAISE NOTICE '✅ 待办表升级完成';
    RAISE NOTICE '   - t_todo: % 条记录', todo_count;
    RAISE NOTICE '   - t_todo_history: % 条记录', history_count;
    RAISE NOTICE '   - t_todo_reminder_queue: % 条记录', queue_count;
END $$;
