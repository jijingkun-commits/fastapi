"""表结构同步脚本：从 Analytics DB 同步表元数据到 App DB（中文注释）。

功能：
1. 读取 Analytics DB 的 information_schema（支持多 Schema）
2. 生成表/字段描述的 embedding
3. 写入 t_meta_tables / t_meta_columns（包含 schema_name）
4. 可选：将 DDL 训练到 Vanna 向量库

使用方法：
    python scripts/schema_sync.py [--force] [--schemas fdmdata,sdmdata]
"""
import logging
import argparse
from typing import List, Dict, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

from app.core.config import DATABASE_URL, ANALYTICS_DATABASE_URL, ANALYTICS_SCHEMAS
from app.db.session import get_db_context
from app.models.data_agent_metadata import MetaTable, MetaColumn, MetaRelation
from app.ai.utils.embedding_util import get_embedding

logger = logging.getLogger(__name__)


def get_analytics_tables(analytics_url: str, schemas: Optional[List[str]] = None) -> List[Dict]:
    """从 Analytics DB 获取指定 Schema 的所有表信息。
    
    Args:
        analytics_url: 数据库连接 URL
        schemas: 要同步的 Schema 列表（默认使用 ANALYTICS_SCHEMAS 配置）
        
    Returns:
        表信息列表，每个表包含 schema、name、columns
    """
    if schemas is None:
        schemas = ANALYTICS_SCHEMAS
    
    engine = create_engine(analytics_url)
    inspector = inspect(engine)
    
    tables = []
    
    for schema in schemas:
        logger.info(f"扫描 Schema: {schema}")
        
        try:
            table_names = inspector.get_table_names(schema=schema)
        except Exception as e:
            logger.warning(f"无法读取 Schema {schema}: {e}")
            continue
        
        for table_name in table_names:
            # 跳过系统表
            if table_name.startswith("pg_") or table_name.startswith("sql_"):
                continue
                
            columns = []
            try:
                pk_columns = inspector.get_pk_constraint(table_name, schema=schema).get('constrained_columns', [])
                fk_map = {}
                for fk in inspector.get_foreign_keys(table_name, schema=schema):
                    for col in fk.get('constrained_columns', []):
                        fk_map[col] = {
                            "referred_table": fk.get('referred_table'),
                            "referred_schema": fk.get('referred_schema', schema),
                            "referred_columns": fk.get('referred_columns', [])
                        }
                
                for col in inspector.get_columns(table_name, schema=schema):
                    col_info = {
                        "name": col['name'],
                        "type": str(col['type']),
                        "nullable": col.get('nullable', True),
                        "default": str(col.get('default', '')),
                        "is_primary_key": col['name'] in pk_columns,
                        "is_foreign_key": col['name'] in fk_map,
                    }
                    if col['name'] in fk_map:
                        # 外键使用完整的 schema.table 格式
                        fk_info = fk_map[col['name']]
                        fk_table = fk_info['referred_table']
                        fk_schema = fk_info.get('referred_schema', schema)
                        col_info["foreign_table"] = f"{fk_schema}.{fk_table}" if fk_schema else fk_table
                        col_info["foreign_column"] = fk_info['referred_columns'][0] if fk_info['referred_columns'] else None
                    columns.append(col_info)
                
                tables.append({
                    "schema": schema,
                    "name": table_name,
                    "columns": columns
                })
                
            except Exception as e:
                logger.warning(f"读取表 {schema}.{table_name} 失败: {e}")
                continue
    
    engine.dispose()
    logger.info(f"共发现 {len(tables)} 个表")
    return tables


def generate_table_description(schema: str, table_name: str, columns: List[Dict]) -> str:
    """生成表的自然语言描述（用于 embedding）。
    
    Args:
        schema: Schema 名称
        table_name: 表名
        columns: 列信息列表
        
    Returns:
        表的自然语言描述
    """
    col_descs = []
    for col in columns:
        col_desc = f"{col['name']} ({col['type']})"
        if col.get('is_primary_key'):
            col_desc += " [主键]"
        if col.get('is_foreign_key'):
            col_desc += f" [外键 -> {col.get('foreign_table', '?')}]"
        col_descs.append(col_desc)
    
    full_name = f"{schema}.{table_name}"
    return f"表 {full_name}，包含字段：{', '.join(col_descs)}"


def generate_ddl(schema: str, table_name: str, columns: List[Dict]) -> str:
    """生成 CREATE TABLE DDL 语句。
    
    Args:
        schema: Schema 名称
        table_name: 表名
        columns: 列信息列表
        
    Returns:
        CREATE TABLE DDL 语句
    """
    col_defs = []
    for col in columns:
        nullable = "" if col.get('nullable') else " NOT NULL"
        pk = " PRIMARY KEY" if col.get('is_primary_key') else ""
        col_defs.append(f"    {col['name']} {col['type']}{nullable}{pk}")
    
    full_name = f"{schema}.{table_name}"
    return f"CREATE TABLE {full_name} (\n" + ",\n".join(col_defs) + "\n);"


def sync_tables_to_metadata(tables: List[Dict], force: bool = False) -> int:
    """同步表信息到 t_meta_tables 和 t_meta_columns。
    
    Args:
        tables: 表信息列表（包含 schema、name、columns）
        force: 是否强制更新（即使已存在）
        
    Returns:
        同步的表数量
    """
    synced_count = 0
    
    with get_db_context() as db:
        for table_info in tables:
            schema = table_info.get("schema", "public")
            table_name = table_info["name"]
            columns = table_info["columns"]
            full_name = f"{schema}.{table_name}"
            
            # 查找现有记录（按 schema + table_name 查询）
            existing = db.query(MetaTable).filter(
                MetaTable.schema_name == schema,
                MetaTable.table_name == table_name
            ).first()
            
            if existing and not force:
                logger.info(f"跳过已存在的表: {full_name}")
                continue
            
            # 生成描述和 embedding
            description = generate_table_description(schema, table_name, columns)
            embedding = get_embedding(description)
            
            if existing:
                # 更新
                existing.description = description
                existing.embedding = embedding
                meta_table = existing
                logger.info(f"更新表元数据: {full_name}")
            else:
                # 新建
                meta_table = MetaTable(
                    schema_name=schema,
                    table_name=table_name,
                    display_name=table_name,
                    description=description,
                    embedding=embedding
                )
                db.add(meta_table)
                db.flush()  # 获取 ID
                logger.info(f"创建表元数据: {full_name}")
            
            # 同步字段
            for col in columns:
                col_desc = f"{full_name}.{col['name']}: {col['type']}"
                col_embedding = get_embedding(col_desc)
                
                existing_col = db.query(MetaColumn).filter(
                    MetaColumn.table_id == meta_table.id,
                    MetaColumn.column_name == col['name']
                ).first()
                
                if existing_col:
                    existing_col.data_type = col['type']
                    existing_col.is_primary_key = col.get('is_primary_key', False)
                    existing_col.is_foreign_key = col.get('is_foreign_key', False)
                    existing_col.foreign_table = col.get('foreign_table')
                    existing_col.foreign_column = col.get('foreign_column')
                    existing_col.embedding = col_embedding
                else:
                    db.add(MetaColumn(
                        table_id=meta_table.id,
                        column_name=col['name'],
                        display_name=col['name'],
                        data_type=col['type'],
                        is_primary_key=col.get('is_primary_key', False),
                        is_foreign_key=col.get('is_foreign_key', False),
                        foreign_table=col.get('foreign_table'),
                        foreign_column=col.get('foreign_column'),
                        embedding=col_embedding
                    ))
            
            synced_count += 1
        
        db.commit()
    
    return synced_count


def sync_relations(tables: List[Dict]) -> int:
    """同步表关系到 t_meta_relations。"""
    relations_count = 0
    
    with get_db_context() as db:
        for table_info in tables:
            schema = table_info.get("schema", "public")
            table_name = table_info["name"]
            full_from_table = f"{schema}.{table_name}"
            
            for col in table_info["columns"]:
                if col.get('is_foreign_key') and col.get('foreign_table'):
                    foreign_table = col['foreign_table']
                    
                    # 检查是否已存在
                    existing = db.query(MetaRelation).filter(
                        MetaRelation.from_table == full_from_table,
                        MetaRelation.from_column == col['name'],
                        MetaRelation.to_table == foreign_table
                    ).first()
                    
                    if not existing:
                        db.add(MetaRelation(
                            from_table=full_from_table,
                            from_column=col['name'],
                            to_table=foreign_table,
                            to_column=col.get('foreign_column', 'id'),
                            relation_type="foreign_key"
                        ))
                        relations_count += 1
        
        db.commit()
    
    return relations_count


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="同步 Analytics DB 表结构到元数据表")
    parser.add_argument("--force", action="store_true", help="强制更新已存在的记录")
    parser.add_argument("--schemas", type=str, help="要同步的 Schema 列表（逗号分隔），默认使用配置")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    # 解析 Schema 参数
    schemas = None
    if args.schemas:
        schemas = [s.strip() for s in args.schemas.split(",") if s.strip()]
    
    logger.info("开始同步表结构...")
    logger.info(f"Analytics DB: {ANALYTICS_DATABASE_URL[:50]}...")
    logger.info(f"目标 Schema: {schemas or ANALYTICS_SCHEMAS}")
    
    # 获取表信息
    tables = get_analytics_tables(ANALYTICS_DATABASE_URL, schemas=schemas)
    logger.info(f"发现 {len(tables)} 个表")
    
    if not tables:
        logger.warning("未发现任何表，请检查 Schema 配置是否正确")
        return
    
    # 同步到元数据表
    synced = sync_tables_to_metadata(tables, force=args.force)
    logger.info(f"同步了 {synced} 个表的元数据")
    
    # 同步关系
    relations = sync_relations(tables)
    logger.info(f"同步了 {relations} 个表关系")
    
    logger.info("同步完成！")


if __name__ == "__main__":
    main()
