-- Phase 1: 数据库优化
-- 添加时区支持、约束和ENUM类型

-- 1. 创建ENUM类型
DO $$
BEGIN
    -- 创建todo_status枚举
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'todo_status') THEN
        CREATE TYPE todo_status AS ENUM ('todo', 'in_progress', 'done', 'on_hold', 'cancelled');
        RAISE NOTICE '✅ 已创建 todo_status 枚举类型';
    END IF;
    
    -- 创建recurrence_pattern枚举
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recurrence_pattern') THEN
        CREATE TYPE recurrence_pattern AS ENUM ('daily', 'weekly', 'monthly', 'custom');
        RAISE NOTICE '✅ 已创建 recurrence_pattern 枚举类型';
    END IF;
END $$;

-- 2. 添加约束
DO $$
BEGIN
    -- progress范围约束
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_progress') THEN
        ALTER TABLE t_todo ADD CONSTRAINT check_progress 
            CHECK (progress >= 0 AND progress <= 100);
        RAISE NOTICE '✅ 已添加 progress 约束 (0-100)';
    END IF;
    
    -- priority范围约束
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_priority') THEN
        ALTER TABLE t_todo ADD CONSTRAINT check_priority 
            CHECK (priority IN (1, 2, 3));
        RAISE NOTICE '✅ 已添加 priority 约束 (1,2,3)';
    END IF;
    
    -- 重复任务逻辑约束
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'check_recurring_logic') THEN
        ALTER TABLE t_todo ADD CONSTRAINT check_recurring_logic
            CHECK (
                (is_recurring = false) OR 
                (is_recurring = true AND recurrence_pattern IS NOT NULL)
            );
        RAISE NOTICE '✅ 已添加重复任务逻辑约束';
    END IF;
END $$;

-- 3. 时区优化
DO $$
BEGIN
    -- 修改时间字段为带时区类型
    -- 注意：这会保留现有数据
    ALTER TABLE t_todo 
        ALTER COLUMN create_time TYPE TIMESTAMPTZ USING create_time AT TIME ZONE 'UTC',
        ALTER COLUMN update_time TYPE TIMESTAMPTZ USING update_time AT TIME ZONE 'UTC';
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='due_date') THEN
        ALTER TABLE t_todo 
            ALTER COLUMN due_date TYPE TIMESTAMPTZ USING due_date AT TIME ZONE 'UTC';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='start_time') THEN
        ALTER TABLE t_todo 
            ALTER COLUMN start_time TYPE TIMESTAMPTZ USING start_time AT TIME ZONE 'UTC';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='actual_completion_time') THEN
        ALTER TABLE t_todo 
            ALTER COLUMN actual_completion_time TYPE TIMESTAMPTZ USING actual_completion_time AT TIME ZONE 'UTC';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='recurrence_end_date') THEN
        ALTER TABLE t_todo 
            ALTER COLUMN recurrence_end_date TYPE TIMESTAMPTZ USING recurrence_end_date AT TIME ZONE 'UTC';
    END IF;
    
    RAISE NOTICE '✅ 已将所有时间字段转换为 TIMESTAMPTZ';
END $$;

-- 4. 优化索引
DO $$
BEGIN
    -- 创建复合索引（常用查询组合）
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_todo_user_status') THEN
        CREATE INDEX idx_todo_user_status ON t_todo(user_id, status) WHERE is_deleted = false;
        RAISE NOTICE '✅ 已创建复合索引 idx_todo_user_status';
    END IF;
    
    -- 截止日期索引（排序常用）
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_todo_due_date') THEN
        CREATE INDEX idx_todo_due_date ON t_todo(due_date) WHERE is_deleted = false AND status != 'done';
        RAISE NOTICE '✅ 已创建 idx_todo_due_date 部分索引';
    END IF;
    
    -- 重复任务查询索引
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_todo_recurring_query') THEN
        CREATE INDEX idx_todo_recurring_query ON t_todo(parent_recurring_id, due_date) 
            WHERE parent_recurring_id IS NOT NULL;
        RAISE NOTICE '✅ 已创建 idx_todo_recurring_query 索引';
    END IF;
END $$;

-- 5. 输出总结
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ Phase 1 数据库优化完成';
    RAISE NOTICE '========================================';
    RAISE NOTICE '  - 新增 2 个ENUM类型';
    RAISE NOTICE '  - 新增 3 个约束';
    RAISE NOTICE '  - 时间字段全部支持时区';
    RAISE NOTICE '  - 新增 3 个优化索引';
    RAISE NOTICE '';
END $$;
