-- ============================================================
-- 问数助手专用只读用户创建脚本
-- ============================================================
-- 
-- 用途：创建一个只读数据库用户，专用于问数助手的数据查询
-- 安全性：只授予业务 Schema 的 SELECT 权限，禁止访问系统表和敏感数据
--
-- 使用方法：
--   1. 以超级用户身份连接数据库
--   2. 修改下方的密码（change_me_in_production）
--   3. 根据实际情况修改 Schema 列表
--   4. 执行此脚本
--
-- 注意事项：
--   - 生产环境必须使用强密码
--   - 确保 ANALYTICS_DATABASE_URL 使用此用户连接
-- ============================================================

-- 1. 创建只读用户（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'askdata_reader') THEN
        CREATE USER askdata_reader WITH PASSWORD 'change_me_in_production';
        RAISE NOTICE '用户 askdata_reader 已创建';
    ELSE
        RAISE NOTICE '用户 askdata_reader 已存在，跳过创建';
    END IF;
END
$$;

-- 2. 授予数据库连接权限
-- 注意：需要替换 YOUR_DATABASE 为实际数据库名，或在 psql 中使用 \gexec
-- GRANT CONNECT ON DATABASE YOUR_DATABASE TO askdata_reader;
-- 或者使用动态 SQL（在 psql 中执行）:
DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO askdata_reader', current_database());
END
$$;

-- 3. 授予业务 Schema 的使用权限
-- 根据实际情况修改 Schema 列表
GRANT USAGE ON SCHEMA public TO askdata_reader;
-- GRANT USAGE ON SCHEMA fdmdata TO askdata_reader;  -- 如果存在
-- GRANT USAGE ON SCHEMA sdmdata TO askdata_reader;  -- 如果存在

-- 4. 授予业务表的 SELECT 权限
GRANT SELECT ON ALL TABLES IN SCHEMA public TO askdata_reader;
-- GRANT SELECT ON ALL TABLES IN SCHEMA fdmdata TO askdata_reader;
-- GRANT SELECT ON ALL TABLES IN SCHEMA sdmdata TO askdata_reader;

-- 5. 对未来新建的表也自动授权
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO askdata_reader;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA fdmdata GRANT SELECT ON TABLES TO askdata_reader;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA sdmdata GRANT SELECT ON TABLES TO askdata_reader;

-- 6. 撤销敏感表的权限（双重保障）
-- 即使在 public schema 中，也禁止访问这些表
DO $$
DECLARE
    sensitive_tables TEXT[] := ARRAY[
        't_user',
        't_chat_message',
        't_chat_feedback',
        't_chat_asset',
        't_todo',
        't_todo_history',
        't_todo_reminder_queue',
        't_llm_model',
        't_llm_provider',
        't_agent_skills',
        't_system_config',
        't_metric_definitions',
        't_data_query_log'
    ];
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY sensitive_tables
    LOOP
        BEGIN
            EXECUTE format('REVOKE SELECT ON TABLE %I FROM askdata_reader', tbl);
            RAISE NOTICE '已撤销对表 % 的访问权限', tbl;
        EXCEPTION WHEN undefined_table THEN
            -- 表不存在，忽略
            NULL;
        END;
    END LOOP;
END
$$;

-- 7. 撤销系统 Schema 的权限
-- PostgreSQL 默认允许访问 pg_catalog，需要明确撤销
REVOKE ALL ON SCHEMA pg_catalog FROM askdata_reader;
REVOKE ALL ON SCHEMA information_schema FROM askdata_reader;

-- 8. 验证权限配置
DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE '问数专用用户 askdata_reader 配置完成';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '请在 .env 中配置：';
    RAISE NOTICE 'ANALYTICS_DATABASE_URL=postgresql+psycopg://askdata_reader:YOUR_PASSWORD@host:5432/database';
    RAISE NOTICE '';
    RAISE NOTICE '测试连接：';
    RAISE NOTICE 'psql -U askdata_reader -d database -c "SELECT COUNT(*) FROM pg_tables"';
    RAISE NOTICE '（应该报错，因为无权访问 pg_catalog）';
END
$$;
