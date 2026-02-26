"""指标模板迁移脚本：新增 query_template 列并批量填充。

用法: python -m scripts.migrate_query_template

背景: t_metric_definition 中 1524 条 sql_template 存储的是 ETL 批处理脚本，
不可直接用于 RAG 和 SQL 生成。本脚本新增 query_template 列，
存放可直接执行的 SELECT 查询模板。
"""
import sys
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_migration():
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        # 1. 新增列（如果不存在）
        logger.info("=== 步骤 1: 新增列 ===")
        conn.execute(text("""
            ALTER TABLE t_metric_definition
              ADD COLUMN IF NOT EXISTS query_template TEXT
        """))
        conn.execute(text("""
            ALTER TABLE t_metric_definition
              ADD COLUMN IF NOT EXISTS template_source VARCHAR(20) DEFAULT 'none'
        """))
        logger.info("列已创建: query_template, template_source")

        # 2. 迁移现有 SELECT 模板
        logger.info("=== 步骤 2: 迁移 SELECT 模板 ===")
        r = conn.execute(text("""
            UPDATE t_metric_definition
            SET query_template = sql_template,
                template_source = 'manual'
            WHERE sql_template IS NOT NULL
              AND sql_template ~* '^\\s*SELECT'
              AND query_template IS NULL
        """))
        logger.info(f"SELECT 模板迁移: {r.rowcount} 条")

        # 3. 结果表查询 - f_mid_index_result (排除 _dim 和 _derive)
        logger.info("=== 步骤 3: 生成 f_mid_index_result 查询模板 ===")
        r = conn.execute(text("""
            UPDATE t_metric_definition
            SET query_template = 
                'SELECT data_dt, org_no, org_no_map AS 机构名称, ccy AS 币种, '
                || 'index_name AS 指标名称, index_value AS 指标值, '
                || 'year_to_date AS 年累计 '
                || 'FROM fdmdata.f_mid_index_result '
                || 'WHERE index_code = ''' || metric_id || ''' AND data_dt = ''${data_dt}'' '
                || 'ORDER BY org_no',
                template_source = 'result_lookup'
            WHERE sql_template IS NOT NULL
              AND UPPER(sql_template) LIKE '%INSERT INTO%F_MID_INDEX_RESULT%'
              AND UPPER(sql_template) NOT LIKE '%F_MID_INDEX_RESULT_DIM%'
              AND UPPER(sql_template) NOT LIKE '%F_MID_INDEX_RESULT_DERIVE%'
              AND query_template IS NULL
        """))
        logger.info(f"f_mid_index_result 查询模板: {r.rowcount} 条")

        # 4. 结果表查询 - f_mid_index_result_dim
        logger.info("=== 步骤 4: 生成 f_mid_index_result_dim 查询模板 ===")
        r = conn.execute(text("""
            UPDATE t_metric_definition
            SET query_template = 
                'SELECT data_dt, org_no, org_no_map AS 机构名称, ccy AS 币种, '
                || 'index_name AS 指标名称, index_value AS 指标值, '
                || 'year_to_date AS 年累计, dim_name AS 维度名称, dim_value AS 维度值 '
                || 'FROM fdmdata.f_mid_index_result_dim '
                || 'WHERE index_code = ''' || metric_id || ''' AND data_dt = ''${data_dt}'' '
                || 'ORDER BY org_no',
                template_source = 'result_lookup'
            WHERE sql_template IS NOT NULL
              AND UPPER(sql_template) LIKE '%INSERT INTO%F_MID_INDEX_RESULT_DIM%'
              AND query_template IS NULL
        """))
        logger.info(f"f_mid_index_result_dim 查询模板: {r.rowcount} 条")

        # 5. 结果表查询 - f_mid_index_result_derive
        logger.info("=== 步骤 5: 生成 f_mid_index_result_derive 查询模板 ===")
        r = conn.execute(text("""
            UPDATE t_metric_definition
            SET query_template = 
                'SELECT data_dt, org_no, org_no_map AS 机构名称, ccy AS 币种, '
                || 'index_name AS 指标名称, index_value AS 指标值, '
                || 'year_to_date AS 年累计 '
                || 'FROM fdmdata.f_mid_index_result_derive '
                || 'WHERE index_code = ''' || metric_id || ''' AND data_dt = ''${data_dt}'' '
                || 'ORDER BY org_no',
                template_source = 'result_lookup'
            WHERE sql_template IS NOT NULL
              AND UPPER(sql_template) LIKE '%INSERT INTO%F_MID_INDEX_RESULT_DERIVE%'
              AND query_template IS NULL
        """))
        logger.info(f"f_mid_index_result_derive 查询模板: {r.rowcount} 条")

    # 6. 验证结果
    logger.info("=== 步骤 6: 验证迁移结果 ===")
    with engine.connect() as conn:
        stats = conn.execute(text("""
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE template_source = 'manual') AS manual_count,
                COUNT(*) FILTER (WHERE template_source = 'result_lookup') AS result_lookup_count,
                COUNT(*) FILTER (WHERE template_source = 'ai_extract') AS ai_extract_count,
                COUNT(*) FILTER (WHERE template_source = 'none' OR template_source IS NULL) AS none_count,
                COUNT(*) FILTER (WHERE query_template IS NOT NULL) AS query_ready
            FROM t_metric_definition
        """)).fetchone()

        logger.info(f"总数: {stats.total}")
        logger.info(f"手动 SELECT: {stats.manual_count}")
        logger.info(f"结果表查询: {stats.result_lookup_count}")
        logger.info(f"AI 提取: {stats.ai_extract_count}")
        logger.info(f"未处理: {stats.none_count}")
        logger.info(f"query_template 覆盖率: {stats.query_ready}/{stats.total} = "
                     f"{stats.query_ready * 100.0 / max(stats.total, 1):.1f}%")


if __name__ == "__main__":
    run_migration()
