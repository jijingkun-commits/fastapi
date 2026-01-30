import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加父目录到路径以导入应用模块
sys.path.append(str(Path(__file__).resolve().parents[3]))

from app.core.config import DATABASE_URL
from app.ai.utils.embedding_util import get_embedding
from app.services.llm_config_service import LLMConfigService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_schema_vectors():
    """
    同步 schema 向量数据 (针对 t_metric_definition 表)：
    1. 扫描 t_metric_definition 表中缺少 embedding 的记录。
    2. 使用 metric_name + description 生成 embedding。
    3. 更新数据库。
    """
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # 1. 初始化 LLM 配置服务
    try:
        LLMConfigService.load_from_db(session)
    except Exception as e:
        logger.error(f"加载 LLM 配置失败: {e}")
        return
    finally:
        session.close()
    
    logger.info("开始 Metric 语义向量同步任务...")
    
    # 2. 检查总数和缺失数
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition")).scalar()
        missing = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition WHERE embedding IS NULL")).scalar()
        logger.info(f"指标总数: {total}, 缺失向量数: {missing}")
        
        if missing == 0:
            logger.info("所有指标已向量化，无需更新。")
            return

        # 3. 批量处理更新
        batch_size = 50 
        processed = 0
        
        while processed < missing:
            # 获取一批待处理数据
            rows = conn.execute(text("""
                SELECT metric_id, metric_name, description 
                FROM t_metric_definition 
                WHERE embedding IS NULL 
                LIMIT :limit
            """), {"limit": batch_size}).fetchall()
            
            if not rows:
                break
                
            logger.info(f"正在处理批次: {len(rows)} 条记录...")
            
            updates: List[Dict[str, Any]] = []
            
            for row in rows:
                # 构建语义搜索文本
                # 格式: "指标名称: 描述"
                text_content = f"指标名称: {row.metric_name}\n定义: {row.description}"
                
                # 生成 Embedding
                try:
                    emb = get_embedding(text_content)
                    if emb:
                        # 准备批量更新数据
                        updates.append({
                            "id": row.metric_id,
                            "emb": str(emb) # pgvector 兼容字符串格式
                        })
                except Exception as e:
                    logger.error(f"生成 Embedding 失败 (id={row.metric_id}): {e}")
            
            # 批量写入数据库
            if updates:
                try:
                    conn.execute(text("""
                        UPDATE t_metric_definition 
                        SET embedding = :emb 
                        WHERE metric_id = :id
                    """), updates)
                    conn.commit()
                    logger.info(f"批次更新成功: {len(updates)} 条")
                except Exception as e:
                    logger.error(f"数据库批量更新失败: {e}")
                    conn.rollback()
            
            processed += len(rows)
            logger.info(f"总体进度: {min(processed, missing)}/{missing}")

    logger.info("Metric 向量同步完成。")

if __name__ == "__main__":
    sync_schema_vectors()
