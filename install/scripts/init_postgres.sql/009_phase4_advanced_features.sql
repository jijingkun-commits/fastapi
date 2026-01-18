-- Phase 4 数据库扩展：重复任务和子任务支持
-- 为 t_todo 表添加高级功能字段

-- 1. 重复任务字段
DO $$
BEGIN
    -- 是否为重复任务
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='is_recurring') THEN
        ALTER TABLE t_todo ADD COLUMN is_recurring BOOL DEFAULT false;
    END IF;
    
    -- 重复模式 (daily, weekly, monthly, custom)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='recurrence_pattern') THEN
        ALTER TABLE t_todo ADD COLUMN recurrence_pattern VARCHAR(50);
    END IF;
    
    -- 重复间隔（每N天/周/月）
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='recurrence_interval') THEN
        ALTER TABLE t_todo ADD COLUMN recurrence_interval INT DEFAULT 1;
    END IF;
    
    -- 重复的星期几 (JSONB数组，如 [1,3,5] 表示周一三五)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='recurrence_days') THEN
        ALTER TABLE t_todo ADD COLUMN recurrence_days JSONB;
    END IF;
    
    -- 重复结束日期
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='recurrence_end_date') THEN
        ALTER TABLE t_todo ADD COLUMN recurrence_end_date TIMESTAMP;
    END IF;
    
    -- 关联的重复任务模板ID
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='parent_recurring_id') THEN
        ALTER TABLE t_todo ADD COLUMN parent_recurring_id INT;
    END IF;
END $$;

-- 2. 子任务字段
DO $$
BEGIN
    -- 父任务ID
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='parent_id') THEN
        ALTER TABLE t_todo ADD COLUMN parent_id INT;
    END IF;
    
    -- 任务排序
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='task_order') THEN
        ALTER TABLE t_todo ADD COLUMN task_order INT DEFAULT 0;
    END IF;
    
    -- 层级深度
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='depth_level') THEN
        ALTER TABLE t_todo ADD COLUMN depth_level INT DEFAULT 0;
    END IF;
END $$;

-- 3. 添加注释
COMMENT ON COLUMN t_todo.is_recurring IS '是否为重复任务';
COMMENT ON COLUMN t_todo.recurrence_pattern IS '重复模式：daily/weekly/monthly/custom';
COMMENT ON COLUMN t_todo.recurrence_interval IS '重复间隔（每N天/周/月）';
COMMENT ON COLUMN t_todo.recurrence_days IS '重复的星期几（JSONB数组）';
COMMENT ON COLUMN t_todo.recurrence_end_date IS '重复结束日期';
COMMENT ON COLUMN t_todo.parent_recurring_id IS '关联的重复任务模板ID';
COMMENT ON COLUMN t_todo.parent_id IS '父任务ID（用于子任务）';
COMMENT ON COLUMN t_todo.task_order IS '任务排序';
COMMENT ON COLUMN t_todo.depth_level IS '层级深度';

-- 4. 创建索引
CREATE INDEX IF NOT EXISTS idx_todo_parent ON t_todo(parent_id);
CREATE INDEX IF NOT EXISTS idx_todo_recurring ON t_todo(parent_recurring_id);
CREATE INDEX IF NOT EXISTS idx_todo_is_recurring ON t_todo(is_recurring) WHERE is_recurring = true;

-- 5. 创建外键（可选，确保数据完整性）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_todo_parent'
    ) THEN
        ALTER TABLE t_todo 
        ADD CONSTRAINT fk_todo_parent 
        FOREIGN KEY (parent_id) REFERENCES t_todo(id) ON DELETE CASCADE;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_todo_recurring'
    ) THEN
        ALTER TABLE t_todo 
        ADD CONSTRAINT fk_todo_recurring 
        FOREIGN KEY (parent_recurring_id) REFERENCES t_todo(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 6. 输出结果
DO $$
BEGIN
    RAISE NOTICE '✅ Phase 4 数据库扩展完成';
    RAISE NOTICE '   - 已添加重复任务字段（6个）';
    RAISE NOTICE '   - 已添加子任务字段（3个）';
    RAISE NOTICE '   - 已创建相关索引';
    RAISE NOTICE '   - 已设置外键约束';
END $$;
