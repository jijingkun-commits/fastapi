import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import ANALYTICS_DATABASE_URL

def verify():
    print(f"Connecting to: {ANALYTICS_DATABASE_URL}")
    engine = create_engine(ANALYTICS_DATABASE_URL)
    
    with engine.connect() as conn:
        # Check Schema
        schemas = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'fdmdata'")).fetchall()
        print(f"Schema 'fdmdata' exists: {bool(schemas)}")
        
        # Check Table
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'fdmdata' AND table_name = 'f_mid_dep_tb'")).fetchall()
        print(f"Table 'fdmdata.f_mid_dep_tb' exists: {bool(tables)}")
        
        # Count
        try:
            count = conn.execute(text("SELECT count(*) FROM fdmdata.f_mid_dep_tb")).scalar()
            print(f"Row count: {count}")
        except Exception as e:
            print(f"Count failed: {e}")
            
        # Sample
        if count and count > 0:
            print("Sample data (top 3):")
            rows = conn.execute(text("SELECT * FROM fdmdata.f_mid_dep_tb LIMIT 3")).fetchall()
            for row in rows:
                print(row)

if __name__ == "__main__":
    verify()
