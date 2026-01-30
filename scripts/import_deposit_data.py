import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import ANALYTICS_DATABASE_URL

def import_data():
    print(f"Starting import to {ANALYTICS_DATABASE_URL}...")
    
    # Check file existence
    data_file = Path(__file__).resolve().parents[1] / "docs/内部参考/数据资料/DMP_F_MID_DEP_TB_20250630.txt"
    if not data_file.exists():
        print(f"File not found: {data_file}")
        return

    # Create Engine
    engine = create_engine(ANALYTICS_DATABASE_URL)
    
    # We need a raw connection for COPY
    # SQLAlchemy connection.connection returns the DBAPI connection (psycopg connection)
    with engine.connect() as conn:
        with conn.connection.cursor() as cur:
            print("Truncating target table fdmdata.f_mid_dep_tb...")
            cur.execute("TRUNCATE TABLE fdmdata.f_mid_dep_tb")
            conn.commit() # Ensure truncate is committed if using transaction

            print("Beginning COPY import...")
            start_time = time.time()
            
            # Using COPY FROM STDIN with the specific delimiter
            # text format is default. NULL string handling might be needed if \N is used.
            # If the file is strictly \x1b delimited text
            
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
            # Note: NULL '' assumes empty strings between delimiters are NULLs. 
            # If the file uses \N for nulls, remove NULL ''.
            
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    # psycopg3 copy syntax
                    # If this is psycopg 3:
                    if hasattr(cur, 'copy'):
                        with cur.copy(copy_sql) as copy:
                            while data := f.read(1024 * 1024): # 1MB chunks
                                copy.write(data)
                    else:
                        # Fallback for psycopg2 or older generic DBAPI
                        cur.copy_expert(copy_sql, f)
                        
                # Commit the transaction on the raw connection just to be sure
                conn.connection.commit()
                elapsed = time.time() - start_time
                print(f"Import completed successfully in {elapsed:.2f} seconds.")
                
            except Exception as e:
                print(f"Import failed: {e}")
                conn.rollback() # SQLAlchemy rollback
                
    # Verify persistence with a fresh connection
    print("Verifying persistence with fresh connection...")
    with engine.connect() as conn:
        cnt = conn.execute(text("SELECT count(*) FROM fdmdata.f_mid_dep_tb")).scalar()
        print(f"PERSISTENT Total rows in fdmdata.f_mid_dep_tb: {cnt}")

if __name__ == "__main__":
    import_data()
