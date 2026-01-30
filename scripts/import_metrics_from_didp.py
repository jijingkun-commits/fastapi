"""
指标数据导入脚本

从 DIDP 导出的指标文件 (dmp_show_ind_info_*.txt) 解析并导入到 t_metric_definition 表。

Usage:
    python scripts/import_metrics_from_didp.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.session import engine


# 源文件路径
SOURCE_FILE = project_root / "docs/内部参考/数据资料/dmp_show_ind_info_20260123.txt"

# 字段分隔符 (ASCII 27, ESC)
DELIMITER = "\x1b"

# 源文件字段映射 (按顺序)
# 0: IND_E_NAME (指标编码)
# 1: IND_NAME (指标名称)
# 2: FIRST_THEME (一级主题)
# 3: SECOND_THEME (二级主题)
# 4: FREQUEN (频率)
# 5: UNIT (单位)
# 6: IND_DESC (指标描述)
# 7: MIX_CAL_RULE (混合计算规则)
# 8: BUSINESS_CLIB (业务口径)
# 9: PREDIT_DATA_TIME (预计数据时间)
# 10: TIME_POINT (时间点类型)
# 11: CURR (币种)
# 12: IND_TYPE (指标类型)
# 13: IND_CALIBER (指标口径)
# ...后续字段省略

from typing import Optional


def parse_line(line: str) -> Optional[dict]:
    """解析单行数据，返回指标字典"""
    parts = line.strip().split(DELIMITER)
    if len(parts) < 7:
        return None
    
    metric_id = parts[0].strip()
    if not metric_id:
        return None
    
    return {
        "metric_id": metric_id,
        "metric_name": parts[1].strip() if len(parts) > 1 else "",
        "category": parts[2].strip() if len(parts) > 2 else None,  # FIRST_THEME -> category
        "description": parts[6].strip() if len(parts) > 6 else "",  # IND_DESC -> description
        "unit": parts[5].strip() if len(parts) > 5 else None,
        "frequency": parts[4].strip() if len(parts) > 4 else None,
        "aliases": None,  # 暂时不设置别名
        "sql_template": None,  # 需后续手动补充
    }


def import_metrics():
    """导入指标到数据库"""
    if not SOURCE_FILE.exists():
        print(f"错误：源文件不存在 - {SOURCE_FILE}")
        return
    
    print(f"读取源文件: {SOURCE_FILE}")
    
    metrics = []
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            metric = parse_line(line)
            if metric:
                metrics.append(metric)
            else:
                print(f"跳过第 {line_no} 行: 解析失败")
    
    print(f"解析成功: {len(metrics)} 条指标")
    
    if not metrics:
        print("无有效数据，退出")
        return
    
    # 插入数据库
    with engine.connect() as conn:
        # 清空旧数据
        conn.execute(text("TRUNCATE TABLE t_metric_definition"))
        print("已清空旧数据")
        
        # 批量插入
        insert_sql = text("""
            INSERT INTO t_metric_definition 
            (metric_id, metric_name, description, category, unit, frequency, aliases, sql_template)
            VALUES 
            (:metric_id, :metric_name, :description, :category, :unit, :frequency, :aliases, :sql_template)
        """)
        
        batch_size = 500
        for i in range(0, len(metrics), batch_size):
            batch = metrics[i:i+batch_size]
            conn.execute(insert_sql, batch)
            print(f"已插入 {min(i+batch_size, len(metrics))}/{len(metrics)}")
        
        conn.commit()
        print("导入完成！")
        
        # 统计
        result = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition"))
        count = result.scalar()
        print(f"数据库中共有 {count} 条指标")


if __name__ == "__main__":
    import_metrics()
