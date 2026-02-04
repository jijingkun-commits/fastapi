"""导入新数据文件到 data_db 数据库。

数据文件来源: data/数据文件20260202/
分隔符: ESC (0x1b)
编码: UTF-8
"""
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
from psycopg import sql

# 数据库连接配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "dbname": "data_db"
}

# 数据文件目录
DATA_DIR = Path(__file__).resolve().parents[1] / "data/数据文件20260202"

# 表配置：文件名 -> (schema.table, 字段列表)
# 字段顺序必须与现有表结构一致
TABLE_CONFIGS = {
    "dmp_f_mid_index_resultT_20250630.txt": {
        "table": "fdmdata.f_mid_index_result",
        "columns": [
            "data_dt", "org_no", "org_no_map", "ccy", "index_code", 
            "index_name", "index_value", "month_to_date", "quarter_to_date", 
            "year_to_date", "ztetl_dt"
        ]
    },
    "dmp_f_mid_index_result_derive_20250630.txt": {
        "table": "fdmdata.f_mid_index_result_derive",
        "columns": [
            "data_dt", "org_no", "org_no_map", "ccy", "index_code",
            "index_name", "index_value", "month_to_date", "quarter_to_date",
            "year_to_date", "ztetl_dt"
        ]
    },
    "dmp_f_mid_index_result_dim_20250630.txt": {
        "table": "fdmdata.f_mid_index_result_dim",
        "columns": [
            "data_dt", "org_no", "org_no_map", "ccy", "index_code",
            "index_name", "index_value", "month_to_date", "quarter_to_date",
            "year_to_date", "bus_dim_1", "bus_dim_2", "bus_dim_3", "bus_dim_4",
            "bus_dim_5", "bus_dim_6", "bus_dim_7", "bus_dim_8", "bus_dim_9",
            "bus_dim_10", "bus_dim_11", "bus_dim_12", "bus_dim_13", "bus_dim_14",
            "bus_dim_15", "bus_dim_exp", "group_sign", "ztetl_dt"
        ]
    },
    "dmp_f_mid_loan_k_tb_20250630.txt": {
        "table": "fdmdata.f_mid_loan_k_tb",
        "columns": [
            "data_dt", "duebill_no", "biz_contr_no", "dept_cd", "dept_val",
            "ccy_cd", "ecif_cust_no", "prod_no", "duebill_sts_cd", 
            "norm_actl_y_intr", "crdt_biz_cate_cd", "rsdu_matr_days", 
            "crdt_obj_class_cd", "mod_belong", "obs_biz_ind", "norm_prin_subj_no",
            "five_class_cd", "prin_ovrd_days", "int_ovrd_days", "new_productmark",
            "norm_prin_bal", "norm_prin_y_accum", "prin_bal", "y_prin_wgt_accum",
            "loan_bal_y_avg", "y_tot_owe_int", "int_amt2", "margin_bal",
            "ibs_owe_int_amt", "obs_owe_int_amt", "titc_cust_id", "indu_type_cd",
            "holding_type_cd", "ent_scal_cd", "level4_cd", "level3_cd", 
            "level2_cd", "level1_cd", "st_own_ent_ind", "tech_corp_ind",
            "ext_dt", "ext_matr_dt", "prim_guar_mode_cd", "loan_invest_indu_cd",
            "all_crdt_tot_amt", "y_prin_bal_accum", "cust_mgr_no",
            "int_amt2_m_accum", "int_amt2_q_accum", "int_amt2_y_accum", "legal_org_cd"
        ]
    },
    "dmp_f_mid_org_tree_k_20250630.txt": {
        "table": "fdmdata.f_mid_org_tree_k",
        "columns": ["dept_cd", "dept_name", "org_no", "org_val", "org_lv"]
    },
}


def ensure_schema_exists(conn):
    """确保 fdmdata schema 存在。"""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS fdmdata")
    conn.commit()
    print("✅ Schema fdmdata 已确认存在")


def create_table_if_not_exists(conn, table_name: str, columns: list):
    """如果表不存在，创建表（简化版，全部使用 TEXT 类型）。"""
    schema, tbl = table_name.split(".")
    
    with conn.cursor() as cur:
        # 检查表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            )
        """, (schema, tbl))
        exists = cur.fetchone()[0]
        
        if not exists:
            cols_def = ", ".join([f'"{c}" TEXT' for c in columns])
            create_sql = f'CREATE TABLE {table_name} ({cols_def})'
            cur.execute(create_sql)
            conn.commit()
            print(f"✅ 创建表 {table_name}")
        else:
            print(f"ℹ️  表 {table_name} 已存在")


def import_file(conn, filename: str, config: dict, truncate: bool = True):
    """导入单个数据文件。"""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        print(f"⚠️  文件不存在: {filepath}")
        return False
    
    table = config["table"]
    columns = config["columns"]
    
    # 创建表（如果不存在）
    create_table_if_not_exists(conn, table, columns)
    
    # 构建 COPY 语句
    cols_str = ", ".join([f'"{c}"' for c in columns])
    copy_sql = f"""
        COPY {table} ({cols_str})
        FROM STDIN
        WITH (FORMAT text, DELIMITER E'\\x1b', ENCODING 'UTF8', NULL '')
    """
    
    file_size = filepath.stat().st_size / (1024 * 1024)  # MB
    print(f"\n📁 导入 {filename} ({file_size:.1f} MB) -> {table}")
    
    with conn.cursor() as cur:
        if truncate:
            print(f"   清空表 {table}...")
            cur.execute(f"TRUNCATE TABLE {table}")
        
        print(f"   开始 COPY 导入...")
        with open(filepath, 'r', encoding='utf-8') as f:
            with cur.copy(copy_sql) as copy:
                while chunk := f.read(1024 * 1024):  # 1MB chunks
                    copy.write(chunk)
        
        # 获取导入行数
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"   ✅ 导入完成: {count:,} 行")
    
    conn.commit()
    return True


def main():
    """主函数：导入所有数据文件。"""
    print("=" * 60)
    print("数据导入工具 - data/数据文件20260202")
    print("=" * 60)
    
    # 连接数据库
    try:
        conn = psycopg.connect(**DB_CONFIG)
        print(f"✅ 已连接数据库: {DB_CONFIG['dbname']}")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n请确保 data_db 数据库已创建:")
        print("  docker exec fastapi-postgres psql -U postgres -c 'CREATE DATABASE data_db;'")
        return
    
    try:
        # 确保 schema 存在
        ensure_schema_exists(conn)
        
        # 导入各表
        success_count = 0
        for filename, config in TABLE_CONFIGS.items():
            if import_file(conn, filename, config):
                success_count += 1
        
        print("\n" + "=" * 60)
        print(f"导入完成: {success_count}/{len(TABLE_CONFIGS)} 个文件")
        print("=" * 60)
        
        # 显示各表数据量
        print("\n📊 当前数据量统计:")
        with conn.cursor() as cur:
            for config in TABLE_CONFIGS.values():
                table = config["table"]
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"   {table}: {count:,} 行")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
