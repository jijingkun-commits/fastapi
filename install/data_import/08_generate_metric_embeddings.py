#!/usr/bin/env python3
"""
为 t_metric_definition 表生成 embedding 向量

功能：
1. 扫描 t_metric_definition 中 embedding 为空的记录
2. 使用指标名称和描述生成文本
3. 调用 embedding API 生成向量
4. 更新到数据库

用法：
    python 08_generate_metric_embeddings.py [--batch-size 100] [--limit 1000]
"""

import sys
import argparse
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL


def generate_metric_embeddings(batch_size: int = 100, limit: int = None):
    """为指标生成 embedding"""
    
    try:
        from app.ai.utils.embedding_util import get_embedding
    except ImportError as e:
        print(f"[错误] 无法导入 embedding 模块: {e}")
        print("请确保 API key 配置正确")
        return
    
    engine = create_engine(str(DATABASE_URL))
    
    # 获取需要生成 embedding 的指标
    with engine.connect() as conn:
        count_sql = text("SELECT COUNT(*) FROM t_metric_definition WHERE embedding IS NULL")
        total_pending = conn.execute(count_sql).scalar()
        
        print(f"需要生成 embedding 的指标: {total_pending} 条")
        
        if total_pending == 0:
            print("所有指标已有 embedding，无需处理")
            return
    
    # 分批处理
    processed = 0
    success = 0
    failed = 0
    
    while True:
        with engine.begin() as conn:
            # 获取一批待处理的指标
            fetch_sql = text("""
                SELECT metric_id, metric_name, description, aliases
                FROM t_metric_definition 
                WHERE embedding IS NULL
                LIMIT :batch_size
            """)
            
            metrics = conn.execute(fetch_sql, {"batch_size": batch_size}).fetchall()
            
            if not metrics:
                break
            
            for metric in metrics:
                metric_code = metric.metric_id or ""
                metric_name = metric.metric_name or ""
                description = metric.description or ""
                aliases = metric.aliases or ""
                
                # 构建文本用于 embedding
                text_parts = []
                if metric_name:
                    text_parts.append(f"指标名称: {metric_name}")
                if description:
                    text_parts.append(f"定义: {description}")
                if aliases:
                    text_parts.append(f"别名: {aliases}")
                if metric_code:
                    text_parts.append(f"代码: {metric_code}")
                
                text_content = "\n".join(text_parts) if text_parts else metric_name
                
                try:
                    embedding = get_embedding(text_content)
                    
                    if embedding:
                        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                        
                        update_sql = text("""
                            UPDATE t_metric_definition 
                            SET embedding = CAST(:embedding AS vector)
                            WHERE metric_id = :metric_id
                        """)
                        
                        conn.execute(update_sql, {"embedding": embedding_str, "metric_id": metric_code})
                        success += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    print(f"  [失败] {metric_name}: {e}")
                    failed += 1
                
                processed += 1
                
                # 进度报告
                if processed % 100 == 0:
                    print(f"  已处理 {processed} 条，成功 {success}，失败 {failed}")
                
                # 检查限制
                if limit and processed >= limit:
                    break
            
            # 避免 API 限流
            time.sleep(0.1)
        
        if limit and processed >= limit:
            break
    
    print(f"\n完成！")
    print(f"  总处理: {processed} 条")
    print(f"  成功: {success} 条")
    print(f"  失败: {failed} 条")
    
    # 验证结果
    with engine.connect() as conn:
        has_emb = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition WHERE embedding IS NOT NULL")).scalar()
        total = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition")).scalar()
        print(f"\n当前状态: {has_emb}/{total} 条指标有 embedding ({has_emb/total*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="为指标生成 embedding")
    parser.add_argument("--batch-size", type=int, default=100, help="每批处理数量")
    parser.add_argument("--limit", type=int, default=None, help="最大处理数量（用于测试）")
    args = parser.parse_args()
    
    print("=" * 60)
    print("指标 Embedding 生成")
    print("=" * 60)
    
    generate_metric_embeddings(batch_size=args.batch_size, limit=args.limit)


if __name__ == "__main__":
    main()
