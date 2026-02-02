"""
从 DIDP META_DATA JSON 文件生成 PostgreSQL DDL。

Usage:
    python install/data_import/generate_ddl.py
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
META_DATA_DIR = PROJECT_ROOT / "data/DIDP_PROJECT_WORKSPACE/META_DATA"

# 类型映射: Greenplum/Oracle -> PostgreSQL
TYPE_MAPPING = {
    "CHARACTER VARYING": "VARCHAR",
    "VARCHAR": "VARCHAR",
    "NUMERIC": "NUMERIC",
    "DATE": "DATE",
    "TIMESTAMP": "TIMESTAMP",
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "SMALLINT": "SMALLINT",
    "DOUBLE PRECISION": "DOUBLE PRECISION",
    "REAL": "REAL",
    "TEXT": "TEXT",
    "CLOB": "TEXT",
    "BOOLEAN": "BOOLEAN",
}


def map_column_type(col: Dict) -> str:
    """将源类型映射为 PostgreSQL 类型。"""
    col_type = col.get("col_type", "VARCHAR").upper()
    pg_type = TYPE_MAPPING.get(col_type, "VARCHAR")
    
    col_length = col.get("col_length", "0")
    col_scale = col.get("col_scale", "0")
    
    # 处理长度和精度
    if pg_type == "VARCHAR":
        if col_length and col_length != "0":
            return f"VARCHAR({col_length})"
        return "VARCHAR(255)"
    elif pg_type == "NUMERIC":
        if col_length and col_length != "0":
            if col_scale and col_scale != "0":
                return f"NUMERIC({col_length},{col_scale})"
            return f"NUMERIC({col_length})"
        return "NUMERIC"
    
    return pg_type


def generate_ddl(table_name: str, schema: str, columns: List[Dict]) -> str:
    """生成 CREATE TABLE DDL。"""
    lines = [f"-- {table_name}"]
    lines.append(f"CREATE TABLE IF NOT EXISTS {schema}.{table_name} (")
    
    col_defs = []
    for col in columns:
        col_name = col.get("column_name", "").lower()
        col_type = map_column_type(col)
        col_desc = col.get("column_desc", "")
        
        col_def = f"    {col_name} {col_type}"
        col_defs.append(col_def)
    
    lines.append(",\n".join(col_defs))
    lines.append(");")
    
    # 添加注释
    lines.append("")
    for col in columns:
        col_name = col.get("column_name", "").lower()
        col_desc = col.get("column_desc", "")
        if col_desc:
            escaped_desc = col_desc.replace("'", "''")
            lines.append(f"COMMENT ON COLUMN {schema}.{table_name}.{col_name} IS '{escaped_desc}';")
    
    lines.append("")
    return "\n".join(lines)


def find_meta_file(table_name: str) -> Path:
    """查找表的元数据文件。"""
    # 搜索模式
    patterns = [
        f"**/*.{table_name}.json",
        f"**/SCH_FDM_IND_*/*{table_name}.json",
        f"**/SDMDATA/*{table_name}.json",
    ]
    
    for pattern in patterns:
        files = list(META_DATA_DIR.glob(pattern))
        # 过滤掉 properties.json 文件
        files = [f for f in files if not f.name.endswith('.properties.json')]
        if files:
            return files[0]
    
    return None


def main():
    # 需要生成 DDL 的表（按优先级排序）
    tables = [
        ("fdmdata", "f_mid_index_result"),
        ("fdmdata", "f_mid_index_result_derive"),
        ("fdmdata", "f_mid_index_result_dim"),
        ("fdmdata", "f_mid_org_tree_k"),
        ("fdmdata", "f_mid_loan_k_tb"),
        ("sdmdata", "s_mms_dmp_pub_cust_tag_all"),
        ("fdmdata", "f_mid_dep_k_tb"),
        ("sdmdata", "s_ods_g_b_cif_basic_info"),
        ("sdmdata", "s_ods_g_b_dep_acct_info"),
    ]
    
    output_lines = [
        "-- 03_create_business_tables.sql",
        "-- 业务表建表语句（按覆盖度优先级排序）",
        "-- 自动生成，请勿手动修改",
        "",
    ]
    
    for schema, table_name in tables:
        print(f"处理 {schema}.{table_name}...")
        
        meta_file = find_meta_file(table_name.upper())
        if not meta_file:
            print(f"  警告: 未找到 {table_name} 的元数据文件")
            continue
        
        print(f"  使用: {meta_file}")
        
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                columns = json.load(f)
        except Exception as e:
            print(f"  错误: {e}")
            continue
        
        ddl = generate_ddl(table_name, schema, columns)
        output_lines.append(ddl)
        print(f"  生成了 {len(columns)} 个字段的 DDL")
    
    # 写入输出文件
    output_path = PROJECT_ROOT / "install/data_import/03_create_business_tables.sql"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    
    print(f"\n已生成: {output_path}")


if __name__ == "__main__":
    main()
