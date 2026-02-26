
import json
import os
import sys
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import ANALYTICS_DATABASE_URL

# Table Definitions based on DIDP JSONs
# Simplified for PostgreSQL

DDL_STATEMENTS = [
    # 1. ORG TREE
    """
    CREATE TABLE IF NOT EXISTS fdmdata.f_mid_org_tree (
        level7_cd VARCHAR(100),
        level7_val VARCHAR(100),
        org_no VARCHAR(100),
        org_val VARCHAR(100),
        org_lv VARCHAR(100),
        -- Adding commonly used fields seen in queries if not in JSON, 
        -- but based on JSON these are the main ones.
        -- Some queries use 'org_no_map', assuming it maps here or logic handles it.
        PRIMARY KEY (org_no)
    );
    """,
    
    # 2. DATE DIMENSION
    """
    CREATE TABLE IF NOT EXISTS sdmdata.s_ods_g_c_dim_date (
        date_id DATE PRIMARY KEY,
        ld_dt DATE,
        lte_dt DATE,
        lme_dt DATE,
        lqe_dt DATE,
        lye_dt DATE,
        lyse_dt DATE,
        lt_dt DATE,
        lm_dt DATE,
        lq_dt DATE,
        ly_dt DATE,
        lys_dt DATE,
        wd_id NUMERIC,
        wd_cn_nm VARCHAR(100),
        t_id NUMERIC,
        t_chn_nm VARCHAR(100),
        ts_dt DATE,
        te_dt DATE,
        te_ind VARCHAR(20),
        t_days NUMERIC,
        t_t_days NUMERIC,
        m_id NUMERIC,
        m_cn_nm VARCHAR(100),
        ms_dt DATE,
        me_dt DATE,
        me_ind VARCHAR(20),
        m_days NUMERIC,
        m_t_days NUMERIC,
        q_id NUMERIC,
        q_cn_nm VARCHAR(100),
        qs_dt DATE,
        qe_dt DATE,
        qe_ind VARCHAR(20),
        q_days NUMERIC,
        q_t_days NUMERIC,
        hy_id NUMERIC,
        hy_cn_nm VARCHAR(100),
        hys_dt DATE,
        hye_dt DATE,
        hy_ind VARCHAR(20),
        hy_days NUMERIC,
        hy_t_days NUMERIC,
        y_id NUMERIC,
        y_cn_nm VARCHAR(100),
        ys_dt DATE,
        ye_dt DATE,
        ye_ind VARCHAR(20),
        y_days NUMERIC,
        y_t_days NUMERIC,
        work_day_ind VARCHAR(20),
        jxb_fr_id VARCHAR(5),
        ztetl_dt VARCHAR(10)
    );
    """
]

def main():
    print(f"Connecting to Analytics DB: {ANALYTICS_DATABASE_URL}")
    engine = create_engine(str(ANALYTICS_DATABASE_URL))
    
    with engine.begin() as conn:
        # Ensure schemas exist
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS fdmdata;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS sdmdata;"))
        
        for ddl in DDL_STATEMENTS:
            print(f"Executing DDL...")
            conn.execute(text(ddl))
            
    print("Successfully created dimension tables: f_mid_org_tree, s_ods_g_c_dim_date")

if __name__ == "__main__":
    main()
