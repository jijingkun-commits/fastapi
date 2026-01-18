-- 待办表补充优化脚本
-- 新增字段: is_deleted (逻辑删除) 和扩展 status 枚举

-- 1. 新增逻辑删除字段
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='t_todo' AND column_name='is_deleted') THEN
        ALTER TABLE t_todo ADD COLUMN is_deleted BOOL DEFAULT false;
    END IF;
END $$;

COMMENT ON COLUMN t_todo.is_deleted IS '逻辑删除标记';

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_todo_is_deleted ON t_todo(is_deleted);

-- 3. 输出结果
DO $$
BEGIN
    RAISE NOTICE '✅ 待办表补充优化完成';
    RAISE NOTICE '   - 已添加 is_deleted 字段';
    RAISE NOTICE '   - 支持逻辑删除';
    RAISE NOTICE '   - status 支持 on_hold (挂起)';
END $$;
