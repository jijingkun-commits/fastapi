"""
指标 SQL 模板提取脚本

从 DIDP 工程导出的 SQL 文件中提取指标计算逻辑，更新到 t_metric_definition 表。

Usage:
    python scripts/extract_metric_sql.py [--dry-run]
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.session import engine


# SQL 文件目录
DIDP_BASE = project_root / "docs/内部参考/数据资料/DIDP_PROJECT_WORKSPACE/KJ2023_11/1.0"

# 需要扫描的目录前缀 (FDM层包含计算逻辑)
FDM_PREFIXES = ["SCH_FDM_IND_"]

# 文件名正则：提取指标代码
METRIC_CODE_PATTERN = re.compile(r"_([AYZ]\d{6})\.sql$", re.IGNORECASE)


def find_sql_files() -> List[Tuple[str, Path]]:
    """扫描所有指标 SQL 文件，返回 (metric_id, file_path) 列表"""
    results = []
    
    for item in DIDP_BASE.iterdir():
        if not item.is_dir():
            continue
        
        # 只处理 FDM 层目录
        if not any(item.name.startswith(prefix) for prefix in FDM_PREFIXES):
            continue
        
        # 遍历子目录
        for subdir in item.iterdir():
            if not subdir.is_dir():
                continue
            
            # 查找 F_MID_INDEX_RESULT 相关目录
            if "F_MID_INDEX_RESULT" not in subdir.name:
                continue
            
            for sql_file in subdir.glob("*.sql"):
                match = METRIC_CODE_PATTERN.search(sql_file.name)
                if match:
                    metric_id = match.group(1).upper()
                    results.append((metric_id, sql_file))
    
    return results


def extract_select_query(sql_content: str) -> Optional[str]:
    """从完整 SQL 中提取 SELECT 查询部分"""
    # 移除 DELETE 语句和注释
    lines = []
    in_comment = False
    
    for line in sql_content.split("\n"):
        stripped = line.strip()
        
        # 跳过块注释
        if "/*" in stripped:
            in_comment = True
        if "*/" in stripped:
            in_comment = False
            continue
        if in_comment:
            continue
        
        # 跳过 DELETE 语句
        if stripped.upper().startswith("DELETE"):
            continue
        
        # 跳过单行注释
        if stripped.startswith("--"):
            continue
        
        lines.append(line)
    
    cleaned = "\n".join(lines).strip()
    
    # 查找 SELECT 语句
    # 先找 INSERT INTO ... SELECT
    insert_match = re.search(
        r"INSERT\s+INTO\s+\S+\s*\([^)]+\)\s*(SELECT.+)",
        cleaned,
        re.IGNORECASE | re.DOTALL
    )
    
    if insert_match:
        select_part = insert_match.group(1).strip()
        # 移除末尾分号
        if select_part.endswith(";"):
            select_part = select_part[:-1].strip()
        return select_part
    
    # 直接查找 SELECT
    select_match = re.search(r"(SELECT.+)", cleaned, re.IGNORECASE | re.DOTALL)
    if select_match:
        select_part = select_match.group(1).strip()
        if select_part.endswith(";"):
            select_part = select_part[:-1].strip()
        return select_part
    
    return None


def adapt_sql_for_postgres(sql: str) -> str:
    """将提取的 SQL 适配为 PostgreSQL 风格"""
    adapted = sql
    
    # 替换日期占位符
    adapted = adapted.replace("'[DATE]'", ":data_dt")
    adapted = adapted.replace("[DATE]", ":data_dt")
    
    # 统一 schema 为小写
    adapted = re.sub(r"\bFDMDATA\.", "fdmdata.", adapted, flags=re.IGNORECASE)
    adapted = re.sub(r"\bSDMDATA\.", "sdmdata.", adapted, flags=re.IGNORECASE)
    adapted = re.sub(r"\bADMDATA\.", "admdata.", adapted, flags=re.IGNORECASE)
    
    return adapted


def get_existing_metrics() -> Dict[str, int]:
    """获取数据库中已有的指标及其 ID"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT metric_id FROM t_metric_definition"))
        return {row[0]: 1 for row in result}


def update_sql_template(metric_id: str, sql_template: str, dry_run: bool = False):
    """更新指标的 SQL 模板"""
    if dry_run:
        print(f"[DRY-RUN] 更新 {metric_id}: {sql_template[:80]}...")
        return
    
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE t_metric_definition SET sql_template = :sql WHERE metric_id = :id"),
            {"sql": sql_template, "id": metric_id}
        )
        conn.commit()


def main():
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("=== DRY RUN 模式 (不写入数据库) ===\n")
    
    print(f"扫描目录: {DIDP_BASE}\n")
    
    # 获取已有指标
    existing_metrics = get_existing_metrics()
    print(f"数据库已有指标: {len(existing_metrics)} 条\n")
    
    # 扫描 SQL 文件
    sql_files = find_sql_files()
    print(f"找到 SQL 文件: {len(sql_files)} 个\n")
    
    # 统计
    matched = 0
    updated = 0
    skipped = 0
    errors = []
    
    for metric_id, file_path in sql_files:
        # 检查指标是否存在
        if metric_id not in existing_metrics:
            skipped += 1
            continue
        
        matched += 1
        
        try:
            # 读取并解析 SQL
            content = file_path.read_text(encoding="utf-8")
            select_sql = extract_select_query(content)
            
            if not select_sql:
                errors.append((metric_id, "无法提取 SELECT 语句"))
                continue
            
            # 适配 PostgreSQL
            adapted_sql = adapt_sql_for_postgres(select_sql)
            
            # 更新数据库
            update_sql_template(metric_id, adapted_sql, dry_run)
            updated += 1
            
        except Exception as e:
            errors.append((metric_id, str(e)))
    
    # 输出统计
    print("\n" + "=" * 50)
    print("提取完成！")
    print(f"  - 匹配指标: {matched}")
    print(f"  - 更新成功: {updated}")
    print(f"  - 跳过(无对应指标): {skipped}")
    print(f"  - 错误: {len(errors)}")
    
    if errors:
        print("\n错误详情:")
        for metric_id, error in errors[:10]:
            print(f"  {metric_id}: {error}")
        if len(errors) > 10:
            print(f"  ... 还有 {len(errors) - 10} 个错误")


if __name__ == "__main__":
    main()
