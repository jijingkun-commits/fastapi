"""
从 DIDP SQL 文件中提取指标 SQL 模板并更新到数据库。

Usage:
    python scripts/extract_metric_sql.py
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from app.db.session import engine

# DIDP 工作空间路径
DIDP_WORKSPACE = Path(__file__).resolve().parents[1] / "data/DIDP_PROJECT_WORKSPACE"

# 匹配指标 ID 的正则 (如 A000023, AK002439, Y000034)
METRIC_ID_PATTERN = re.compile(r"^[A-Z]+\d+$")


def extract_sql_from_file(file_path: Path) -> Optional[Tuple[str, str]]:
    """从 SQL 文件中提取指标 ID 和 SELECT 语句。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="gb18030") as f:
            content = f.read()
    
    # 从文件名提取指标 ID
    filename = file_path.stem
    parts = filename.split("_")
    metric_id = parts[-1] if parts else None
    
    if not metric_id or not METRIC_ID_PATTERN.match(metric_id):
        return None
    
    # 提取 SELECT 语句 (从 SELECT 到 INSERT 结束的 ;)
    # 简化处理：提取整个 SQL 内容
    
    # 替换日期占位符
    sql_template = content.replace("[DATE]", "${data_dt}")
    
    return metric_id, sql_template


def find_sql_files():
    """查找所有指标 SQL 文件 (FDM 层的 INDEX_RESULT 相关)。"""
    sql_files = []
    
    for pattern in [
        "**/*F_MID_INDEX_RESULT/*.sql",
        "**/*F_MID_INDEX_RESULT_DIM/*.sql",
        "**/*F_MID_INDEX_RESULT_DERIVE/*.sql",
    ]:
        sql_files.extend(DIDP_WORKSPACE.glob(pattern))
    
    return sql_files


def main():
    print(f"扫描目录: {DIDP_WORKSPACE}")
    
    sql_files = find_sql_files()
    print(f"找到 {len(sql_files)} 个 SQL 文件")
    
    # 提取指标 SQL
    metric_sqls = {}
    for file_path in sql_files:
        result = extract_sql_from_file(file_path)
        if result:
            metric_id, sql = result
            # 如果有多个 SQL 文件，保留第一个（通常是基础版本）
            if metric_id not in metric_sqls:
                metric_sqls[metric_id] = sql
    
    print(f"提取到 {len(metric_sqls)} 个指标 SQL")
    
    # 更新数据库
    update_sql = text("""
        UPDATE t_metric_definition 
        SET sql_template = :sql_template,
            updated_at = NOW()
        WHERE metric_id = :metric_id
          AND sql_template IS NULL
    """)
    
    updated = 0
    with engine.begin() as conn:
        for metric_id, sql_template in metric_sqls.items():
            result = conn.execute(update_sql, {
                "metric_id": metric_id,
                "sql_template": sql_template
            })
            if result.rowcount > 0:
                updated += 1
    
    print(f"更新了 {updated} 个指标的 SQL 模板")
    
    # 统计
    with engine.connect() as conn:
        stats = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(sql_template) as with_sql
            FROM t_metric_definition
        """)).fetchone()
        print(f"\n数据库统计:")
        print(f"  总指标数: {stats[0]}")
        print(f"  有 SQL 模板: {stats[1]}")
        print(f"  无 SQL 模板: {stats[0] - stats[1]}")


if __name__ == "__main__":
    main()
