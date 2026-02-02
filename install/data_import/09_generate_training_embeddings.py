#!/usr/bin/env python3
"""
为 t_data_query_log 表生成 question_embedding

场景：
1. 批量导入历史训练数据后，需要补充 embedding
2. 早期记录缺少 embedding 需要补充

注意：正常使用问数功能时，embedding 会在记录时自动生成（见 data_access_control.py）

用法：
    python 09_generate_training_embeddings.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL


def generate_training_embeddings():
    """为训练数据生成 embedding"""
    
    try:
        from app.ai.utils.embedding_util import get_embedding
    except ImportError as e:
        print(f"[错误] 无法导入 embedding 模块: {e}")
        return
    
    engine = create_engine(str(DATABASE_URL))
    
    # 获取需要生成 embedding 的记录
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM t_data_query_log")).scalar()
        pending = conn.execute(text("SELECT COUNT(*) FROM t_data_query_log WHERE question_embedding IS NULL")).scalar()
        
        print(f"t_data_query_log 总记录: {total}")
        print(f"需要生成 embedding: {pending}")
        
        if pending == 0:
            print("所有记录已有 embedding，无需处理")
            return
    
    # 处理缺少 embedding 的记录
    success = 0
    failed = 0
    
    with engine.begin() as conn:
        records = conn.execute(text("""
            SELECT id, question 
            FROM t_data_query_log 
            WHERE question_embedding IS NULL
        """)).fetchall()
        
        for record in records:
            record_id = record.id
            question = record.question
            
            try:
                embedding = get_embedding(question)
                
                if embedding:
                    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                    
                    conn.execute(text("""
                        UPDATE t_data_query_log 
                        SET question_embedding = CAST(:embedding AS vector)
                        WHERE id = :id
                    """), {"embedding": embedding_str, "id": record_id})
                    
                    success += 1
                else:
                    failed += 1
                    
            except Exception as e:
                print(f"  [失败] ID={record_id}: {e}")
                failed += 1
            
            if (success + failed) % 50 == 0:
                print(f"  已处理 {success + failed} 条...")
    
    print(f"\n完成！")
    print(f"  成功: {success}")
    print(f"  失败: {failed}")


def main():
    print("=" * 60)
    print("训练数据 Embedding 生成")
    print("=" * 60)
    
    generate_training_embeddings()


if __name__ == "__main__":
    main()
