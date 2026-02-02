-- 复合索引优化脚本
-- 为常用查询添加复合索引，提升查询性能
-- 日期：2026-01-30

-- 1. 聊天消息表复合索引
-- 用于 get_threads_by_user 等按用户+时间排序的查询
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_message_user_time 
ON t_chat_message(user_id, create_time DESC);

-- 用于按 thread_id 查询消息
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_message_thread_time 
ON t_chat_message(thread_id, create_time ASC);

-- 2. 待办表复合索引
-- 用于按用户查询未完成待办
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_todo_user_status 
ON t_todo(user_id, status) WHERE is_deleted = false;

-- 用于按用户+截止日期排序
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_todo_user_due 
ON t_todo(user_id, due_date) WHERE is_deleted = false AND is_completed = false;

-- 3. 幂等性记录表索引
-- 用于快速查找幂等键
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_idempotency_key_lookup 
ON t_idempotency_key(idempotency_key, user_id);

-- 4. 验证索引创建
DO $$
BEGIN
    RAISE NOTICE '✅ 复合索引创建完成';
    RAISE NOTICE '   - idx_chat_message_user_time';
    RAISE NOTICE '   - idx_chat_message_thread_time';
    RAISE NOTICE '   - idx_todo_user_status';
    RAISE NOTICE '   - idx_todo_user_due';
    RAISE NOTICE '   - idx_idempotency_key_lookup';
END $$;
