"""指标定义表初始化脚本。

创建 t_metric_definition 表，包含：
- 业务语义层：用于语义匹配
- 物理实现层：用于 SQL 生成
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

DDL = """
-- 删除旧表（如存在）
DROP TABLE IF EXISTS t_metric_definition CASCADE;

-- 创建新的指标定义表
CREATE TABLE t_metric_definition (
    -- 主键
    metric_id VARCHAR(50) PRIMARY KEY,
    
    -- ========== 业务语义层（用于语义匹配）==========
    metric_name VARCHAR(200) NOT NULL,              -- 指标名称
    aliases TEXT,                                   -- 别名/同义词（逗号分隔）
    description TEXT NOT NULL,                      -- 自然语言口径描述（向量化核心）
    category VARCHAR(100),                          -- 指标分类
    sub_category VARCHAR(100),                      -- 指标子分类
    unit VARCHAR(50),                               -- 单位
    frequency VARCHAR(20),                          -- 统计频率（日/月/季/年）
    
    -- ========== 物理层 (SQL Template Only) ==========
    -- 核心策略：不再依赖细粒度字段，完全由 SQL 模板定义计算逻辑
    sql_template TEXT,                              -- 完整 SQL 模板（必需，包含 WHERE/GROUP BY/JOIN）
    
    -- 约束：sql_template 不能为空（因为我们移除了物理字段，它是唯一的 SQL 来源）
    -- (注意：在 INSERT 时应用层需保证 sql_template 有值)
    
    -- ========== 辅助信息 ==========
    embedding VECTOR(1024),                         -- 语义向量（1024维，适配 ZhipuAI/OpenAI）
    is_active BOOLEAN DEFAULT TRUE,                 -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_metric_def_name ON t_metric_definition(metric_name);
CREATE INDEX idx_metric_def_category ON t_metric_definition(category);

-- 表注释
COMMENT ON TABLE t_metric_definition IS '指标定义表：业务语义 + SQL 模板';
COMMENT ON COLUMN t_metric_definition.metric_id IS '指标唯一编码';
COMMENT ON COLUMN t_metric_definition.metric_name IS '指标名称（用户会问的）';
COMMENT ON COLUMN t_metric_definition.aliases IS '别名/同义词，逗号分隔';
COMMENT ON COLUMN t_metric_definition.description IS '自然语言口径描述（向量化核心字段）';
COMMENT ON COLUMN t_metric_definition.sql_template IS '完整 SQL 模板（必需）';
COMMENT ON COLUMN t_metric_definition.embedding IS '语义向量（1024维）';
"""

SAMPLE_DATA = """
-- 插入示例数据
INSERT INTO t_metric_definition 
    (metric_id, metric_name, aliases, description, sql_template)
VALUES
    ('DEP_001', '存款余额', '存款总额,储蓄余额,吸收存款', 
     '统计期末全行各类存款的账面余额合计，包括活期存款和定期存款。', 
     'SELECT SUM(acct_bal) FROM fdmdata.f_mid_dep_tb WHERE ccy_cd = ''CNY'' AND data_dt = ''${data_dt}'''),
     
    ('DEP_002', '定期存款余额', '定存余额,定期储蓄', 
     '统计期末全行定期类存款的账面余额合计。', 
     'SELECT SUM(acct_bal) FROM fdmdata.f_mid_dep_tb WHERE fix_cur_ind = ''1'' AND data_dt = ''${data_dt}'''),
     
    ('LOAN_001', '贷款余额', '贷款总额,放款余额,信贷余额', 
     '统计期末全行各类贷款的本金余额合计。', 
     'SELECT SUM(prin_bal) FROM fdmdata.f_mid_loan_tb WHERE ccy_cd = ''CNY'' AND data_dt = ''${data_dt}'''),
     
    ('LOAN_002', '不良贷款余额', '不良贷款,问题贷款', 
     '统计期末五级分类为次级、可疑、损失的贷款本金余额合计。', 
     'SELECT SUM(prin_bal) FROM fdmdata.f_mid_loan_tb WHERE five_class_cd IN (''3'', ''4'', ''5'') AND data_dt = ''${data_dt}''');
"""

def init_metric_definition():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    
    with engine.connect() as conn:
        print("Creating t_metric_definition table...")
        # Execute entire DDL as one block
        conn.exec_driver_sql(DDL)
        
        print("Inserting sample data...")
        conn.exec_driver_sql(SAMPLE_DATA)
                    
        # Verify
        cnt = conn.execute(text("SELECT count(*) FROM t_metric_definition")).scalar()
        print(f"Done. Total metrics: {cnt}")

if __name__ == "__main__":
    init_metric_definition()
