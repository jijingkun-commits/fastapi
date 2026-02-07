"""语义向量同步工具。

同步以下表的 embedding 向量：
1. t_meta_tables: 表元数据（用于 DDL 检索）
2. t_metric_definition: 指标定义（用于指标匹配）

重要：embedding 维度由 EMBEDDING_DIMENSION 配置决定（当前 2048 维，对应 embedding-3 模型）。
如果更换 embedding 模型，需要：
1. ALTER TABLE 修改 embedding 列维度
2. 清空旧向量（UPDATE ... SET embedding = NULL）
3. 重新运行本脚本（python -m app.ai.semantic.schema_sync）
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[3]))

from app.core.config import DATABASE_URL
from app.ai.utils.embedding_util import get_embedding
from app.services.llm_config_service import LLMConfigService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _sync_table_vectors(engine) -> int:
    """同步 t_meta_tables 的 embedding 向量。"""
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM t_meta_tables")).scalar()
        missing = conn.execute(text("SELECT COUNT(*) FROM t_meta_tables WHERE embedding IS NULL")).scalar()
        logger.info(f"[t_meta_tables] 总数: {total}, 缺失向量: {missing}")
        
        if missing == 0:
            logger.info("[t_meta_tables] 所有记录已向量化。")
            return 0
        
        rows = conn.execute(text("""
            SELECT id, table_name, display_name, description 
            FROM t_meta_tables WHERE embedding IS NULL
        """)).fetchall()
        
        updated = 0
        for row in rows:
            text_content = f"{row.display_name or row.table_name}: {row.description or ''}"
            try:
                emb = get_embedding(text_content)
                if emb:
                    conn.execute(text(
                        "UPDATE t_meta_tables SET embedding = :emb WHERE id = :id"
                    ), {"emb": str(emb), "id": row.id})
                    updated += 1
                    if updated % 10 == 0:
                        conn.commit()
                        logger.info(f"  [t_meta_tables] 进度: {updated}/{missing}")
            except Exception as e:
                logger.error(f"  生成向量失败 (id={row.id}, {row.table_name}): {e}")
        
        conn.commit()
        logger.info(f"[t_meta_tables] 向量同步完成: {updated}/{missing}")
        return updated


def _sync_metric_vectors(engine) -> int:
    """同步 t_metric_definition 的 embedding 向量。"""
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition")).scalar()
        missing = conn.execute(text("SELECT COUNT(*) FROM t_metric_definition WHERE embedding IS NULL")).scalar()
        logger.info(f"[t_metric_definition] 总数: {total}, 缺失向量: {missing}")
        
        if missing == 0:
            logger.info("[t_metric_definition] 所有记录已向量化。")
            return 0

        batch_size = 50
        processed = 0
        total_updated = 0
        
        while processed < missing:
            rows = conn.execute(text("""
                SELECT metric_id, metric_name, description 
                FROM t_metric_definition 
                WHERE embedding IS NULL 
                LIMIT :limit
            """), {"limit": batch_size}).fetchall()
            
            if not rows:
                break
            
            updates: List[Dict[str, Any]] = []
            
            for row in rows:
                text_content = f"指标名称: {row.metric_name}\n定义: {row.description}"
                try:
                    emb = get_embedding(text_content)
                    if emb:
                        updates.append({"id": row.metric_id, "emb": str(emb)})
                except Exception as e:
                    logger.error(f"  生成向量失败 (metric_id={row.metric_id}): {e}")
            
            if updates:
                try:
                    conn.execute(text(
                        "UPDATE t_metric_definition SET embedding = :emb WHERE metric_id = :id"
                    ), updates)
                    conn.commit()
                    total_updated += len(updates)
                except Exception as e:
                    logger.error(f"  批量更新失败: {e}")
                    conn.rollback()
            
            processed += len(rows)
            logger.info(f"  [t_metric_definition] 进度: {min(processed, missing)}/{missing}")

        logger.info(f"[t_metric_definition] 向量同步完成: {total_updated}/{missing}")
        return total_updated


def sync_schema_vectors():
    """同步所有语义向量（t_meta_tables + t_metric_definition）。"""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        LLMConfigService.load_from_db(session)
    except Exception as e:
        logger.error(f"加载 LLM 配置失败: {e}")
        return
    finally:
        session.close()
    
    logger.info("===== 语义向量同步开始 =====")
    
    table_count = _sync_table_vectors(engine)
    metric_count = _sync_metric_vectors(engine)
    
    logger.info(f"===== 同步完成: 表元数据 {table_count} 条, 指标定义 {metric_count} 条 =====")


if __name__ == "__main__":
    sync_schema_vectors()
