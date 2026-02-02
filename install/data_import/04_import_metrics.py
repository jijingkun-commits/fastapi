"""
指标元数据导入脚本

从 DIDP 导出的指标文件导入到 t_metric_definition 表。

Usage:
    python install/data_import/04_import_metrics.py [--file PATH]

Options:
    --file PATH    指定数据文件路径（默认: data/dmp_show_ind_info_*.txt）
"""

import argparse
import glob
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from app.db.session import engine

# 字段分隔符 (ASCII 27, ESC)
DELIMITER = "\x1b"


def find_source_file() -> Optional[Path]:
    """查找指标数据文件。"""
    pattern = str(PROJECT_ROOT / "data/dmp_show_ind_info_*.txt")
    files = glob.glob(pattern)
    if files:
        # 返回最新的文件
        return Path(sorted(files)[-1])
    return None


def parse_line(line: str) -> Optional[dict]:
    """解析单行数据，返回指标字典。"""
    parts = line.strip().split(DELIMITER)
    if len(parts) < 7:
        return None
    
    metric_id = parts[0].strip()
    if not metric_id:
        return None
    
    return {
        "metric_id": metric_id,
        "metric_name": parts[1].strip() if len(parts) > 1 else "",
        "category": parts[2].strip() if len(parts) > 2 else None,
        "description": parts[6].strip() if len(parts) > 6 else "",
        "unit": parts[5].strip() if len(parts) > 5 else None,
        "frequency": parts[4].strip() if len(parts) > 4 else None,
        "aliases": None,
        "sql_template": None,
    }


def import_metrics(source_file: Path):
    """导入指标到数据库。"""
    if not source_file.exists():
        print(f"错误：源文件不存在 - {source_file}")
        sys.exit(1)
    
    print(f"读取源文件: {source_file}")
    
    metrics = []
    skipped = 0
    with open(source_file, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            metric = parse_line(line)
            if metric:
                metrics.append(metric)
            else:
                skipped += 1
    
    print(f"解析成功: {len(metrics)} 条指标")
    if skipped > 0:
        print(f"跳过: {skipped} 行（格式不正确）")
    
    if not metrics:
        print("无有效数据，退出")
        sys.exit(1)
    
    # 使用 UPSERT 导入，保留已有的 sql_template
    with engine.connect() as conn:
        insert_sql = text("""
            INSERT INTO t_metric_definition 
            (metric_id, metric_name, description, category, unit, frequency, aliases, sql_template)
            VALUES 
            (:metric_id, :metric_name, :description, :category, :unit, :frequency, :aliases, :sql_template)
            ON CONFLICT (metric_id) DO UPDATE SET
                metric_name = EXCLUDED.metric_name,
                description = EXCLUDED.description,
                category = COALESCE(EXCLUDED.category, t_metric_definition.category),
                unit = COALESCE(EXCLUDED.unit, t_metric_definition.unit),
                frequency = EXCLUDED.frequency,
                updated_at = NOW()
        """)
        
        batch_size = 500
        for i in range(0, len(metrics), batch_size):
            batch = metrics[i:i+batch_size]
            conn.execute(insert_sql, batch)
            print(f"进度: {min(i+batch_size, len(metrics))}/{len(metrics)}")
        
        conn.commit()
        
        # 统计
        result = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition"))
        count = result.scalar()
        print(f"\n导入完成！数据库中共有 {count} 条指标")


def main():
    parser = argparse.ArgumentParser(description="导入指标元数据")
    parser.add_argument("--file", type=str, help="指定数据文件路径")
    args = parser.parse_args()
    
    if args.file:
        source_file = Path(args.file)
    else:
        source_file = find_source_file()
        if not source_file:
            print("错误：未找到指标数据文件 (data/dmp_show_ind_info_*.txt)")
            print("请使用 --file 参数指定文件路径")
            sys.exit(1)
    
    import_metrics(source_file)


if __name__ == "__main__":
    main()
