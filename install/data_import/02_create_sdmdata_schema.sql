-- 02_create_sdmdata_schema.sql
-- 创建 sdmdata schema（标准数据模型层）

CREATE SCHEMA IF NOT EXISTS sdmdata;

COMMENT ON SCHEMA sdmdata IS 'Standard Data Model - 标准数据模型层，存储 ODS 层源系统数据';
