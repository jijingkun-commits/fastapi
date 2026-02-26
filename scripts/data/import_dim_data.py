"""
分析库维度数据导入脚本。

读取文本文件并导入到 FDM/SDM 层维度表中。
自动处理主键冲突（去重）。
"""
import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import ANALYTICS_DATABASE_URL

# Configuration
FILES_CONFIG = [
    {
        "file_path": "docs/内部参考/数据资料/DMP_F_MID_ORG_TREE_20250630.txt",
        "table": "fdmdata.f_mid_org_tree",
        "columns": ["level7_cd", "level7_val", "org_no", "org_val", "org_lv"],
        "delimiter": chr(27),
        "pk": "org_no"
    },
    {
        "file_path": "docs/内部参考/数据资料/ods_g_c_dim_date_20250630.txt",
        "table": "sdmdata.s_ods_g_c_dim_date",
        "delimiter": chr(27),
        "pk": "date_id"
    }
]

def import_file(conn, config):
    file_path = config["file_path"]
    table_name = config["table"]
    delimiter = config["delimiter"]
    pk = config.get("pk")
    
    if not os.path.exists(file_path):
        print(f"[错误] 文件未找到: {file_path}")
        return

    print(f"[导入中] 导入 {file_path} 到 {table_name}...")
    
    # 1. Truncate Table
    print(f"   清空表 {table_name}...")
    conn.execute(text(f"TRUNCATE TABLE {table_name}"))
    
    # 2. Read and Insert
    batch_size = 1000
    batch = []
    
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split(delimiter)
            batch.append(tuple(parts))
            count += 1
            
            if len(batch) >= batch_size:
                _insert_batch(conn, table_name, batch, config.get("columns"), pk)
                batch = []
                print(f"   已导入 {count} 行...", end='\r')
                
        if batch:
            _insert_batch(conn, table_name, batch, config.get("columns"), pk)
            
    print(f"\n[完成] 成功导入 {count} 行到 {table_name}")

def _insert_batch(conn, table_name, batch, defined_columns, pk=None):
    if not batch:
        return
        
    sample_row = batch[0]
    num_columns = len(sample_row)
    
    if defined_columns:
        cols_part = "(" + ", ".join(defined_columns) + ")"
    else:
        cols_part = ""
    
    vals_ph = ", ".join([f":v{i}" for i in range(num_columns)])
    
    conflict_clause = ""
    if pk:
        conflict_clause = f"ON CONFLICT ({pk}) DO NOTHING"
        
    stmt = text(f"INSERT INTO {table_name} {cols_part} VALUES ({vals_ph}) {conflict_clause}")
    
    # Convert batch (list of tuples) to list of dicts
    params_list = []
    for row in batch:
        row_dict = {f"v{i}": (None if val == '' else val) for i, val in enumerate(row)}
        params_list.append(row_dict)
        
    conn.execute(stmt, params_list)


def main():
    engine = create_engine(str(ANALYTICS_DATABASE_URL))
    
    with engine.begin() as conn:
        for config in FILES_CONFIG:
            try:
                import_file(conn, config)
            except Exception as e:
                print(f"\n[失败] 导入 {config['table']} 出错: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    main()
