"""数据导入脚本：导入存款数据到分析库。

事务策略：TRUNCATE + COPY 在同一事务中执行，失败时整体回滚。
"""
import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import ANALYTICS_DATABASE_URL


def import_data():
    """导入存款数据。
    
    使用单一事务包装 TRUNCATE + COPY，确保原子性：
    - 成功：TRUNCATE + COPY 一起提交
    - 失败：整体回滚，原数据保持不变
    """
    print(f"Starting import to {ANALYTICS_DATABASE_URL}...")
    
    # Check file existence
    data_file = Path(__file__).resolve().parents[1] / "docs/内部参考/数据资料/DMP_F_MID_DEP_TB_20250630.txt"
    if not data_file.exists():
        print(f"File not found: {data_file}")
        return

    # Create Engine
    engine = create_engine(ANALYTICS_DATABASE_URL)
    
    copy_sql = """
    COPY fdmdata.f_mid_dep_tb 
    FROM STDIN 
    WITH (
        FORMAT text, 
        DELIMITER E'\x1b', 
        ENCODING 'UTF8',
        NULL ''
    )
    """
    
    # 使用单一事务：TRUNCATE + COPY 一起提交或回滚
    with engine.connect() as conn:
        try:
            with conn.connection.cursor() as cur:
                print("Truncating target table fdmdata.f_mid_dep_tb...")
                cur.execute("TRUNCATE TABLE fdmdata.f_mid_dep_tb")
                # 注意：此处不提交，与 COPY 在同一事务中

                print("Beginning COPY import...")
                start_time = time.time()
                
                with open(data_file, 'r', encoding='utf-8') as f:
                    if hasattr(cur, 'copy'):
                        # psycopg3 syntax
                        with cur.copy(copy_sql) as copy:
                            while data := f.read(1024 * 1024):  # 1MB chunks
                                copy.write(data)
                    else:
                        # psycopg2 fallback
                        cur.copy_expert(copy_sql, f)
                
                # 统一提交：TRUNCATE + COPY 作为整体
                conn.connection.commit()
                elapsed = time.time() - start_time
                print(f"✅ Import completed successfully in {elapsed:.2f} seconds.")
                
        except Exception as e:
            # 整体回滚：TRUNCATE + COPY 都撤销
            conn.connection.rollback()
            print(f"❌ Import failed (rolled back): {e}")
            raise
                
    # Verify persistence with a fresh connection
    _verify_import(engine)


def _verify_import(engine):
    """验证导入结果。"""
    print("Verifying persistence with fresh connection...")
    with engine.connect() as conn:
        cnt = conn.execute(text("SELECT count(*) FROM fdmdata.f_mid_dep_tb")).scalar()
        print(f"PERSISTENT Total rows in fdmdata.f_mid_dep_tb: {cnt}")

if __name__ == "__main__":
    import_data()
