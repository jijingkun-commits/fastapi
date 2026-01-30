import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

def migrate_vector_dim():
    engine = create_engine(DATABASE_URL)
    
    with engine.begin() as conn:
        print("Migrating vector dimensions from 1536 to 2048...")
        
        # 1. Drop Index using the old operator class/dim
        conn.execute(text("DROP INDEX IF EXISTS idx_metric_embedding;"))
        
        # 2. Alter Column
        # Note: altering vector dimension requires using `::vector(2048)` for conversion if data exists
        # But since data is all NULL (or failed insert), simple alter might work if column is empty.
        # If not, we might need to drop and add. 
        # Since we just created it and failed to populate, it's virtually empty of vectors.
        # Or safely: DROP COLUMN then ADD COLUMN.
        
        conn.execute(text("ALTER TABLE t_dmp_ind_info DROP COLUMN IF EXISTS embedding;"))
        conn.execute(text("ALTER TABLE t_dmp_ind_info ADD COLUMN embedding vector(2048);"))
        
        # 3. Skip Index Creation
        # ivfflat has a limit of 2000 dimensions. Zhipu uses 2048.
        # Since we have < 3000 rows, sequential scan is very fast and acceptable.
        print("Skipping index creation due to dimension limit (>2000). Sequential scan will be used.")
        
        print("Migration completed.")

if __name__ == "__main__":
    migrate_vector_dim()
