import sys
from pathlib import Path
import os

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

def init_db():
    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    # 1. Create Table DDL
    ddl = """
    CREATE TABLE IF NOT EXISTS t_dmp_ind_info (
        metric_code VARCHAR(50) PRIMARY KEY,
        metric_name VARCHAR(100) NOT NULL,
        category VARCHAR(50),
        sub_category VARCHAR(50),
        frequency VARCHAR(20),
        unit VARCHAR(20),
        description TEXT,
        formula TEXT,
        text_formula TEXT,
        reporting_tag VARCHAR(100),
        result_time_hint VARCHAR(100),
        value_type VARCHAR(50),
        currency_scope VARCHAR(50),
        metric_type VARCHAR(50),
        tags VARCHAR(200),
        accumulation VARCHAR(50),
        scope VARCHAR(50),
        department VARCHAR(50),
        business_labels VARCHAR(200),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """
    
    # 2. Vector Extension
    vector_ddl = """
    CREATE EXTENSION IF NOT EXISTS vector;
    ALTER TABLE t_dmp_ind_info ADD COLUMN IF NOT EXISTS embedding vector(1536);
    CREATE INDEX IF NOT EXISTS idx_metric_embedding ON t_dmp_ind_info USING ivfflat (embedding vector_cosine_ops);
    """

    with engine.begin() as conn:
        print("Executing DDL...")
        conn.execute(text(ddl))
        conn.execute(text(vector_ddl))
        print("Table t_dmp_ind_info created/verified.")

    # 3. Import Data
    file_path = Path("/Users/jijingkun/bojxAI/fastapi/docs/内部参考/数据资料/dmp_show_ind_info_20260123.txt")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    print(f"Reading file: {file_path}")
    count = 0
    
    # Use raw SQL for best control over types
    insert_sql = text("""
    INSERT INTO t_dmp_ind_info (
        metric_code, metric_name, category, sub_category, frequency, unit, description, 
        formula, text_formula, reporting_tag, result_time_hint, value_type, currency_scope, 
        metric_type, tags, accumulation, scope, department, business_labels
    ) VALUES (
        :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10, :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19
    ) ON CONFLICT (metric_code) DO UPDATE SET
        metric_name = EXCLUDED.metric_name,
        description = EXCLUDED.description,
        updated_at = NOW();
    """)

    with engine.begin() as conn:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Split by Escape character \x1b
                parts = line.split('\x1b')
                
                # Pad with None if parts are fewer than expected (19 columns)
                # Based on analysis, we expect about 19 cols.
                # If parts > 19, truncate? Or maybe the last col is extra?
                # Let's trust the first 19.
                
                data = {f'p{i+1}': parts[i] if i < len(parts) else None for i in range(19)}
                
                conn.execute(insert_sql, data)
                count += 1
                if count % 100 == 0:
                    print(f"Imported {count} rows...")

    print(f"Import completed. Total rows: {count}")

if __name__ == "__main__":
    init_db()
