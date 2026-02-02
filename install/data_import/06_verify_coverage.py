"""
指标覆盖率验证脚本

检查指标 SQL 依赖的表是否存在，计算覆盖率。

Usage:
    python install/data_import/06_verify_coverage.py
"""

import re
import sys
from collections import Counter
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL, ANALYTICS_DATABASE_URL


def get_existing_tables(engine):
    """获取数据库中已存在的表。"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        """))
        return {f"{row[0]}.{row[1]}".lower() for row in result}


def extract_tables_from_sql(sql_template):
    """从 SQL 模板中提取表引用。"""
    if not sql_template:
        return set()
    
    pattern = r'(?:FROM|JOIN)\s+([a-z0-9_]+\.[a-z0-9_]+)'
    matches = re.findall(pattern, sql_template.lower(), re.IGNORECASE)
    
    # 只保留已知 schema 的表
    valid_schemas = {'fdmdata', 'sdmdata', 'admdata', 'odsfile'}
    
    tables = set()
    for m in matches:
        parts = m.split('.')
        if len(parts) == 2 and parts[0] in valid_schemas:
            tables.add(m)
    
    return tables


def main():
    print("=" * 60)
    print("指标覆盖率验证报告")
    print("=" * 60)
    
    chat_engine = create_engine(str(DATABASE_URL))
    data_engine = create_engine(str(ANALYTICS_DATABASE_URL))
    
    # 获取已存在的表
    existing_tables = get_existing_tables(data_engine)
    print(f"\n数据库中现有 {len(existing_tables)} 张表")
    
    # 获取所有有 SQL 模板的指标
    with chat_engine.connect() as conn:
        metrics = conn.execute(text("""
            SELECT metric_id, metric_name, sql_template 
            FROM t_metric_definition 
            WHERE sql_template IS NOT NULL
        """)).fetchall()
    
    total_with_sql = len(metrics)
    print(f"有 SQL 模板的指标: {total_with_sql} 个")
    
    if total_with_sql == 0:
        print("\n没有指标有 SQL 模板，请先运行:")
        print("  python install/data_import/04_import_metrics.py")
        print("  python install/data_import/05_link_metric_sql.py")
        return
    
    # 分析每个指标
    ready_count = 0
    blocked_metrics = []
    missing_table_impact = Counter()
    
    for m in metrics:
        metric_id, metric_name, sql = m
        required_tables = extract_tables_from_sql(sql)
        missing_tables = {t for t in required_tables if t not in existing_tables}
        
        if not missing_tables:
            ready_count += 1
        else:
            blocked_metrics.append((metric_name, missing_tables))
            for t in missing_tables:
                missing_table_impact[t] += 1
    
    coverage_rate = (ready_count / total_with_sql) * 100 if total_with_sql > 0 else 0
    
    # 输出报告
    print("\n" + "-" * 60)
    print("覆盖率统计")
    print("-" * 60)
    print(f"  可查询指标: {ready_count} 个 ({coverage_rate:.1f}%)")
    print(f"  被阻塞指标: {total_with_sql - ready_count} 个")
    
    if missing_table_impact:
        print("\n" + "-" * 60)
        print("TOP 15 缺失表（按影响指标数量排序）")
        print("-" * 60)
        print(f"{'表名':<45} | {'阻塞指标数':<10}")
        print("-" * 60)
        
        for table, count in missing_table_impact.most_common(15):
            print(f"{table:<45} | {count:<10}")
    
    print("\n" + "=" * 60)
    
    if coverage_rate < 50:
        print("建议: 覆盖率较低，请创建缺失的业务表")
        print("执行: psql -d data_db -f install/data_import/03_create_business_tables.sql")
    else:
        print("状态: 覆盖率良好")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
