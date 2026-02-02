-- 01_create_fdmdata_schema.sql
-- 创建 fdmdata schema（基础数据模型层）

CREATE SCHEMA IF NOT EXISTS fdmdata;

COMMENT ON SCHEMA fdmdata IS 'Foundation Data Model - 基础数据模型层，存储加工后的业务明细数据';
