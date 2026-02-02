#!/usr/bin/env python3
"""
导入表和字段元数据到 t_meta_tables 和 t_meta_columns

功能：
1. 从 DIDP META_DATA JSON 文件提取表结构和字段描述
2. 导入到 t_meta_tables 和 t_meta_columns 表
3. 可选：生成 embedding 以支持向量检索

用法：
    python 07_import_table_metadata.py [--generate-embeddings]
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL, ANALYTICS_DATABASE_URL

# DIDP 元数据目录
META_DATA_DIR = project_root / "data" / "DIDP_PROJECT_WORKSPACE" / "META_DATA"

# 表名到 schema 的映射规则
def get_schema_for_table(table_name: str) -> str:
    """根据表名前缀判断 schema"""
    name_lower = table_name.lower()
    if name_lower.startswith("f_"):
        return "fdmdata"
    elif name_lower.startswith("s_"):
        return "sdmdata"
    elif name_lower.startswith("a_"):
        return "admdata"
    else:
        return "public"


def get_table_category(table_name: str) -> str:
    """根据表名判断业务分类"""
    name_lower = table_name.lower()
    
    if "index_result" in name_lower or "ind_" in name_lower:
        return "指标"
    elif "loan" in name_lower or "ln_" in name_lower or "credit" in name_lower:
        return "贷款"
    elif "dep_" in name_lower or "deposit" in name_lower:
        return "存款"
    elif "cif_" in name_lower or "cust" in name_lower:
        return "客户"
    elif "org_" in name_lower:
        return "机构"
    elif "rrs_" in name_lower or "1104" in name_lower:
        return "监管报表"
    elif "pam_" in name_lower:
        return "绩效"
    else:
        return "其他"


def find_all_meta_files() -> list:
    """查找所有元数据 JSON 文件"""
    if not META_DATA_DIR.exists():
        print(f"[错误] 元数据目录不存在: {META_DATA_DIR}")
        return []
    
    meta_files = []
    for f in META_DATA_DIR.glob("**/*.json"):
        # 排除 properties 文件
        if f.name.endswith('.properties.json'):
            continue
        meta_files.append(f)
    
    return meta_files


def extract_table_name_from_path(file_path: Path) -> str:
    """从文件路径提取表名"""
    # 文件名格式是 SCHEMA.TABLE_NAME.json（如 SCH_FDM_IND_CW_XX.F_MID_INDEX_RESULT.json）
    stem = file_path.stem
    # 取最后一个点后面的部分作为表名
    if "." in stem:
        return stem.split(".")[-1].lower()
    return stem.lower()


def import_metadata(generate_embeddings: bool = False):
    """导入元数据到数据库"""
    
    chat_engine = create_engine(str(DATABASE_URL))
    data_engine = create_engine(str(ANALYTICS_DATABASE_URL))
    
    # 获取数据库中实际存在的表
    with data_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('fdmdata', 'sdmdata', 'admdata', 'public')
        """))
        existing_tables = {f"{row[0]}.{row[1]}".lower() for row in result}
    
    print(f"数据库中存在 {len(existing_tables)} 张表")
    
    # 查找元数据文件
    meta_files = find_all_meta_files()
    print(f"找到 {len(meta_files)} 个元数据文件")
    
    imported_tables = 0
    imported_columns = 0
    
    with chat_engine.begin() as conn:
        for meta_file in meta_files:
            table_name = extract_table_name_from_path(meta_file)
            schema_name = get_schema_for_table(table_name)
            full_name = f"{schema_name}.{table_name}"
            
            # 只导入数据库中存在的表
            if full_name not in existing_tables:
                continue
            
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    columns = json.load(f)
            except Exception as e:
                print(f"  [跳过] {table_name}: 读取失败 - {e}")
                continue
            
            if not columns:
                continue
            
            # 构建表描述
            col_names = [c.get("column_name", "").lower() for c in columns[:10]]
            table_desc = f"表 {full_name}，包含字段：{', '.join(col_names)}"
            if len(columns) > 10:
                table_desc += f" 等共 {len(columns)} 个字段"
            
            category = get_table_category(table_name)
            
            # UPSERT 表元数据
            table_sql = text("""
                INSERT INTO t_meta_tables (schema_name, table_name, display_name, description, category)
                VALUES (:schema_name, :table_name, :display_name, :description, :category)
                ON CONFLICT ON CONSTRAINT uq_schema_table DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    updated_at = NOW()
                RETURNING id
            """)
            
            result = conn.execute(table_sql, {
                "schema_name": schema_name,
                "table_name": table_name,
                "display_name": table_name,
                "description": table_desc,
                "category": category,
            })
            table_id = result.fetchone()[0]
            imported_tables += 1
            
            # 导入字段元数据
            for col in columns:
                col_name = col.get("column_name", "").lower()
                col_desc = col.get("column_desc", "")
                col_type = col.get("col_type", "VARCHAR")
                is_pk = col.get("pk_flag", "0") == "1"
                
                # 截断过长的值
                display_name = (col_desc if col_desc else col_name)[:100]
                
                col_sql = text("""
                    INSERT INTO t_meta_columns (table_id, column_name, display_name, data_type, description, is_primary_key)
                    VALUES (:table_id, :column_name, :display_name, :data_type, :description, :is_primary_key)
                    ON CONFLICT (table_id, column_name) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        data_type = EXCLUDED.data_type,
                        description = EXCLUDED.description,
                        is_primary_key = EXCLUDED.is_primary_key
                """)
                
                conn.execute(col_sql, {
                    "table_id": table_id,
                    "column_name": col_name,
                    "display_name": display_name,
                    "data_type": col_type,
                    "description": col_desc,
                    "is_primary_key": is_pk,
                })
                imported_columns += 1
    
    print(f"\n导入完成:")
    print(f"  - 表: {imported_tables} 张")
    print(f"  - 字段: {imported_columns} 个")
    
    # 生成 embedding
    if generate_embeddings:
        print("\n生成 embedding...")
        generate_table_embeddings(chat_engine)


def generate_table_embeddings(engine):
    """为表元数据生成 embedding"""
    try:
        from app.ai.utils.embedding_util import get_embedding
        
        with engine.begin() as conn:
            # 获取没有 embedding 的表
            tables = conn.execute(text("""
                SELECT id, schema_name, table_name, description 
                FROM t_meta_tables 
                WHERE embedding IS NULL
            """)).fetchall()
            
            print(f"需要生成 embedding 的表: {len(tables)} 张")
            
            success_count = 0
            for table in tables:
                table_id, schema_name, table_name, description = table
                
                # 生成描述文本
                text_for_embedding = f"{schema_name}.{table_name}: {description or table_name}"
                
                try:
                    embedding = get_embedding(text_for_embedding)
                    
                    if embedding:
                        # 转换为字符串格式
                        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                        
                        # 使用 CAST 语法避免 :: 被 SQLAlchemy 误解析
                        conn.execute(text("""
                            UPDATE t_meta_tables 
                            SET embedding = CAST(:embedding AS vector)
                            WHERE id = :id
                        """), {"embedding": embedding_str, "id": table_id})
                        
                        success_count += 1
                        if success_count % 10 == 0:
                            print(f"  已处理 {success_count} 张表...")
                    else:
                        print(f"  [跳过] {schema_name}.{table_name}: 未能生成 embedding")
                except Exception as e:
                    print(f"  [失败] {schema_name}.{table_name}: {e}")
            
            print(f"embedding 生成完成，成功: {success_count} 张")
            
    except ImportError as e:
        print(f"[警告] 无法导入 embedding 模块: {e}")
        print("请手动运行 embedding 生成或确保 API key 配置正确")


def main():
    parser = argparse.ArgumentParser(description="导入表元数据")
    parser.add_argument("--generate-embeddings", action="store_true", 
                        help="生成 embedding 向量（需要配置 API key）")
    args = parser.parse_args()
    
    print("=" * 60)
    print("表元数据导入")
    print("=" * 60)
    
    import_metadata(generate_embeddings=args.generate_embeddings)


if __name__ == "__main__":
    main()
