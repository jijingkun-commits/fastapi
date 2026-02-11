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


def _sync_sample_values(chat_engine) -> int:
    """从分析库采样列值，填充 t_meta_columns.sample_values。
    
    策略：
    1. 查找 sample_values 为空的列
    2. 对每个列，从分析库查询 DISTINCT 值（取前 5 个）
    3. 优先采样枚举型/代码型列（行数适中、唯一值少的列）
    4. 跳过主键、大文本等不适合采样的列
    
    注意：需要分析库连接（ANALYTICS_DATABASE_URL）
    """
    from app.core.config import ANALYTICS_DATABASE_URL
    
    if not ANALYTICS_DATABASE_URL:
        logger.warning("[sample_values] 未配置 ANALYTICS_DATABASE_URL，跳过采样")
        return 0
    
    analytics_engine = create_engine(ANALYTICS_DATABASE_URL)
    
    with chat_engine.connect() as conn:
        # 查找缺少 sample_values 的列（排除主键和大文本类型）
        rows = conn.execute(text("""
            SELECT c.id, t.schema_name, t.table_name, c.column_name, c.data_type,
                   c.is_primary_key
            FROM t_meta_columns c
            JOIN t_meta_tables t ON c.table_id = t.id
            WHERE (c.sample_values IS NULL OR c.sample_values = '')
              AND c.is_primary_key = false
              AND LOWER(COALESCE(c.data_type, '')) NOT IN ('text', 'bytea', 'json', 'jsonb')
            ORDER BY t.schema_name, t.table_name, c.column_name
        """)).fetchall()
        
        if not rows:
            logger.info("[sample_values] 所有列已有样本值")
            return 0
        
        logger.info(f"[sample_values] 需要采样: {len(rows)} 列")
    
    updated = 0
    errors = 0
    
    for row in rows:
        schema = row.schema_name or "public"
        table = row.table_name
        column = row.column_name
        full_table = f"{schema}.{table}"
        
        try:
            # 从分析库采样 DISTINCT 值（取前 5 个非空值）
            sample_sql = text(f"""
                SELECT DISTINCT "{column}"::text AS val
                FROM {full_table}
                WHERE "{column}" IS NOT NULL
                LIMIT 5
            """)
            
            with analytics_engine.connect() as a_conn:
                samples = a_conn.execute(sample_sql).fetchall()
            
            if not samples:
                continue
            
            # 格式化样本值（截断过长的值）
            values = []
            for s in samples:
                val = str(s.val).strip()
                if len(val) > 50:
                    val = val[:50] + "..."
                values.append(val)
            
            sample_str = ", ".join(values)
            
            # 写回 chat_db
            with chat_engine.connect() as conn:
                conn.execute(text(
                    "UPDATE t_meta_columns SET sample_values = :vals WHERE id = :id"
                ), {"vals": sample_str, "id": row.id})
                conn.commit()
            
            updated += 1
            if updated % 50 == 0:
                logger.info(f"  [sample_values] 进度: {updated}/{len(rows)}")
                
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.debug(f"  采样失败 ({full_table}.{column}): {e}")
    
    logger.info(
        f"[sample_values] 采样完成: 成功 {updated}/{len(rows)}, 失败 {errors}"
    )
    return updated


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


def sync_sample_values():
    """单独运行 sample_values 采样（python -m app.ai.semantic.schema_sync --samples）。"""
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
    
    logger.info("===== sample_values 采样开始 =====")
    count = _sync_sample_values(engine)
    logger.info(f"===== 采样完成: {count} 列 =====")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="语义向量同步 / 样本值采样")
    parser.add_argument("--samples", action="store_true", help="仅运行 sample_values 采样")
    parser.add_argument("--all", action="store_true", help="运行向量同步 + 样本值采样")
    args = parser.parse_args()
    
    if args.samples:
        sync_sample_values()
    elif args.all:
        sync_schema_vectors()
        sync_sample_values()
    else:
        sync_schema_vectors()
