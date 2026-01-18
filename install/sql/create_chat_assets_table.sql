-- ============================================
-- 对话资产表迁移脚本 (PostgreSQL)
-- 用途：存储 MinIO 中资产的元数据，支持动态 URL 替换
-- ============================================

-- 创建资产类型枚举（如果不存在）
DO $$ BEGIN
    CREATE TYPE asset_type AS ENUM ('chart', 'image', 'export', 'attachment');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 创建对话资产表
CREATE TABLE IF NOT EXISTS t_chat_assets (
    id BIGSERIAL PRIMARY KEY,
    
    -- 关联字段
    qa_record_id BIGINT NOT NULL,                      -- 关联问答记录ID
    chat_id VARCHAR(64) NOT NULL,                       -- 对话ID（冗余，方便查询）
    user_id BIGINT,                                     -- 用户ID（冗余，方便查询）
    
    -- 资产信息
    asset_type asset_type DEFAULT 'image',              -- 资产类型
    object_key VARCHAR(255) NOT NULL,                   -- MinIO 存储路径
    original_url TEXT,                                  -- 原始 URL（外部来源时）
    file_name VARCHAR(255),                             -- 文件名
    file_size BIGINT,                                   -- 文件大小（bytes）
    content_type VARCHAR(100),                          -- MIME 类型
    
    -- 时间信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,     -- 创建时间
    expires_at TIMESTAMP                                -- 预签名URL过期时间（可选）
);

-- 添加注释
COMMENT ON TABLE t_chat_assets IS '对话资产表';
COMMENT ON COLUMN t_chat_assets.qa_record_id IS '关联问答记录ID';
COMMENT ON COLUMN t_chat_assets.chat_id IS '对话ID（冗余，方便查询）';
COMMENT ON COLUMN t_chat_assets.user_id IS '用户ID（冗余，方便查询）';
COMMENT ON COLUMN t_chat_assets.asset_type IS '资产类型: chart/image/export/attachment';
COMMENT ON COLUMN t_chat_assets.object_key IS 'MinIO 存储路径';
COMMENT ON COLUMN t_chat_assets.original_url IS '原始 URL（外部来源时）';
COMMENT ON COLUMN t_chat_assets.file_name IS '文件名';
COMMENT ON COLUMN t_chat_assets.file_size IS '文件大小（bytes）';
COMMENT ON COLUMN t_chat_assets.content_type IS 'MIME 类型';
COMMENT ON COLUMN t_chat_assets.created_at IS '创建时间';
COMMENT ON COLUMN t_chat_assets.expires_at IS '预签名URL过期时间';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_chat_assets_qa_record_id ON t_chat_assets(qa_record_id);
CREATE INDEX IF NOT EXISTS idx_chat_assets_chat_id ON t_chat_assets(chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_assets_user_id ON t_chat_assets(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_assets_user_chat ON t_chat_assets(user_id, chat_id);

-- 输出成功信息
SELECT 'Migration completed: t_chat_assets table created successfully' AS status;
