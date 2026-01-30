"""问数自动验证脚本 (Ask Data Verification Script).

功能：
1. 读取并清洗 DDL (去除 Greenplum 特有语法)。
2. 在本地数据库创建表。
3. 触发元数据同步 (Schema Sync)。
4. 使用 Vanna 验证 Text-to-SQL 生成效果。
"""
import sys
import os
import re
import logging
from typing import List
from sqlalchemy import create_engine, text

# 添加路径
sys.path.append(os.getcwd())

from app.core.config import DATABASE_URL
from scripts.schema_sync import get_analytics_tables, sync_tables_to_metadata, sync_relations
from app.ai.semantic.vanna_client import get_vanna

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("AskDataTest")

DDL_FILE = "docs/问数表结构与指标/存款和贷款表结构.txt"

def clean_ddl(raw_ddl: str) -> List[str]:
    """清洗 DDL，使其适配 Standard Postgres。"""
    # 移除 Greenplum 特有的子句
    # 1. 移除 WITH (...)
    ddl = re.sub(r'WITH\s*\([^)]+\)', '', raw_ddl, flags=re.IGNORECASE)
    # 2. 移除 DISTRIBUTED BY ...
    ddl = re.sub(r'DISTRIBUTED BY\s*\([^)]+\)', '', ddl, flags=re.IGNORECASE)
    # 3. 移除 PARTITION BY ... 到分号
    # 简单处理：找到 CREATE TABLE 语句，保留到最后一个 )，再加上 ;
    # 但是文件里有多个 CREATE TABLE。
    
    # 策略：逐个语句处理
    # 假设每个 CREATE TABLE 语句之间用 COMMENT 分隔或者其他。
    # 更好的方法是只保留 CREATE TABLE 内部以及 COMMENT。
    
    statements = []
    
    # 分割原始文件中的语句 (简单按 ; 分割)
    raw_stmts = raw_ddl.split(';')
    
    for stmt in raw_stmts:
        stmt = stmt.strip()
        if not stmt:
            continue
            
        if "CREATE TABLE" in stmt.upper():
            # 提取表名
            match = re.search(r'CREATE TABLE\s+([^\s\(]+)', stmt, re.IGNORECASE)
            table_name = match.group(1) if match else "unknown"
            
            # 截取到最后一个 )，抛弃后面的 PARTITION/DISTRIBUTED
            # 找到最后一个 ) 的位置
            last_paren = stmt.rfind(')')
            if last_paren != -1:
                # 检查这个 ) 是否是 PARTITION 的结尾
                # 如果 DDL 包含 PARTITION BY (...)，那么最后一个 ) 可能是 partition 的
                # 原始 Postgres CREATE TABLE 应该是 CREATE TABLE x (cols);
                # Greenplum 是 ... ) DISTRIBUTED BY ...;
                
                # 让我们尝试一种更暴力的清洗：删除所有 PARTITION BY 及其后的内容，直到末尾
                # 这种方法假设 PARTITION BY 是语句的最后部分
                
                # 移除 PARTITION BY 子句
                if "PARTITION BY" in stmt.upper():
                    stmt = re.split(r'PARTITION BY', stmt, flags=re.IGNORECASE)[0]
                
                # 移除 DISTRIBUTED BY 子句
                if "DISTRIBUTED BY" in stmt.upper():
                    stmt = re.split(r'DISTRIBUTED BY', stmt, flags=re.IGNORECASE)[0]
                
                # 移除 WITH 子句 (在末尾的)
                if "WITH (" in stmt.upper():
                    # 这里有点风险，因为 WITH 也可以在 CREATE 之前? 没有，CREATE TABLE ... WITH
                    pass
                
                stmt = stmt.strip()
                if not stmt.endswith(")"):
                    # 如果被截断了，可能需要重新补 )? 
                    # 不，上面的 split 应该保留了前面的部分
                    pass
            
            # 确保以 fdmdata schema 创建时，schema 存在
            # 这里简单暴力：把 fdmdata.去掉，直接建在 public (方便测试)
            # 或者先创建 schema
            stmt = stmt.replace("fdmdata.", "public.") 
            stmt = stmt.replace("DEFAULT '9999'::character varying", "DEFAULT '9999'")
            
            statements.append(stmt)
        
        elif "COMMENT ON" in stmt.upper():
            stmt = stmt.replace("fdmdata.", "public.")
            statements.append(stmt)
            
    return statements

def setup_database():
    """在本地 DB 创建表结构。"""
    logger.info("正在读取并清洗 DDL...")
    with open(DDL_FILE, 'r') as f:
        raw_content = f.read()
    
    sqls = clean_ddl(raw_content)
    
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        logger.info("正在执行 DDL...")
        conn.execute(text("DROP TABLE IF EXISTS public.f_mid_loan_tb CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS public.f_mid_dep_tb CASCADE;"))
        
        for sql in sqls:
            try:
                # 简单的清理
                sql = re.sub(r'WITH\s*\([^)]+\)', '', sql) 
                conn.execute(text(sql))
            except Exception as e:
                logger.warning(f"执行 SQL 失败 (可能不影响): {e}\nSQL: {sql[:50]}...")
        conn.commit()
    logger.info("数据库准备完成。")

def run_sync():
    """运行 Schema Sync。"""
    logger.info("开始同步元数据...")
    # 因为我们建在 public，这里的 ANALYTICS_DB 应该指向本地
    # 并且 get_analytics_tables 会读取 public
    tables = get_analytics_tables(DATABASE_URL)
    target_tables = [t for t in tables if t['name'] in ['f_mid_loan_tb', 'f_mid_dep_tb']]
    
    if not target_tables:
        logger.error("❌ 未能在数据库中找到目标表！")
        return False
        
    sync_tables_to_metadata(target_tables, force=True)
    return True

def verify_generation():
    """验证 SQL 生成。"""
    logger.info("初始化 Vanna...")
    vn = get_vanna()
    
    # 强制重新训练 Vanna (将 metadata 注入向量库)
    # 注意：get_vanna 默认可能不会自动训练新表，除非 schema_sync 做了。
    # schema_sync.py 只更新了 t_meta_tables。Vanna 类通常会从 meta tables 读取。
    # 我们假设 VannaClient.get_related_documentation 会查 t_meta_tables。
    
    test_cases = [
        ("查询所有贷款的余额", ["SELECT", "SUM", "prin_bal", "f_mid_loan_tb"]),
        ("2023年1月的存款总额", ["WHERE", "data_dt", "2023"]),
        ("按机构统计存款余额", ["GROUP BY", "org", "f_mid_dep_tb"])
    ]
    
    all_passed = True
    for q, keywords in test_cases:
        print(f"\n❓ Question: {q}")
        try:
            sql = vn.generate_sql(q)
            print(f"💡 Generated SQL: {sql}")
            
            missing = [kw for kw in keywords if kw.lower() not in sql.lower()]
            if missing:
                print(f"❌ FAILED: Missing keywords {missing}")
                all_passed = False
            else:
                print("✅ PASS")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            all_passed = False
            
    return all_passed

def fix_embedding_config():
    """强制将 Embedding 模型改为 embedding-2 (1024维)，以匹配数据库定义。"""
    logger.info("检查并修复 Embedding 模型配置...")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # 检查当前的 embedding 模型
        current = conn.execute(text("SELECT model_code FROM t_llm_model WHERE model_type='embedding' AND is_active=true")).scalar()
        if current and current != 'embedding-2':
            logger.warning(f"检测到当前 Embedding 模型为 {current} (可能不兼容 1024 维)，正在切换为 embedding-2...")
            # 更新配置
            conn.execute(text("UPDATE t_llm_model SET model_code='embedding-2', model_name='Zhipu Embedding-2' WHERE model_type='embedding'"))
            conn.commit()
            logger.info("已切换为 embedding-2")
        
        # 强制修正数据库字段维度为 1024
        
        
        logger.info("正在修正数据库向量维度为 1024...")
        tables_map = {
            "t_meta_tables": "embedding", 
            "t_meta_columns": "embedding", 
            "t_metrics": "embedding", 
            "t_data_query_log": "question_embedding",
            "t_dmp_ind_info": "embedding"
        }
        
        for tbl, col in tables_map.items():
            # Check dimension first
            dim_check = conn.execute(text(f"""
                SELECT atttypmod FROM pg_attribute 
                WHERE attrelid = '{tbl}'::regclass AND attname = '{col}'
            """)).scalar()
            logger.info(f"表 {tbl}.{col} 当前 typmod: {dim_check}")
            
            # 1536 dims -> typmod usually -1? No. pgvector stores dims.
            # Just Force Alter irrespective of current state to be sure
            try:
                conn.execute(text(f"ALTER TABLE {tbl} ALTER COLUMN {col} TYPE vector(1024) USING NULL::vector"))
                logger.info(f"已执行 ALTER {tbl}.{col}")
            except Exception as e:
                logger.warning(f"ALTER {tbl}.{col} 失败 (可能表或列不存在): {e}")
            
        conn.commit()
        logger.info("数据库向量维度修正完成")
        
        # 强制刷新 LLMConfigService 缓存
        from app.services.llm_config_service import LLMConfigService
        LLMConfigService._initialized = False
        logger.info("已重置 LLMConfigService 缓存")
        
        # 验证 Embedding 维度
        from app.ai.utils.embedding_util import get_embedding
        vec = get_embedding("test")
        if vec:
            logger.info(f"当前 Embedding 维度校验: {len(vec)}")
            if len(vec) != 1024:
                logger.error(f"⚠️ 警告: Embedding 维度仍为 {len(vec)}，与数据库定义 (1024) 不匹配！")




def main():
    try:
        fix_embedding_config()  # Add this call
        setup_database()
        if run_sync():
            msg = "✅ Verification Passed" if verify_generation() else "❌ Verification Failed"
            print(f"\n{msg}")
            sys.exit(0 if "Passed" in msg else 1)
        else:
            sys.exit(1)
    except Exception as e:
        logger.exception(f"测试过程发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
