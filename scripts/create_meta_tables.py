import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import engine
from app.db.base import Base
# Import new models to register them
from app.models.data_agent_metadata import MetaTable, MetaColumn, MetaRelation, DataQueryLog, Metric

def create_meta_tables():
    print("Creating vector extension...")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("✅ Extension 'vector' created (if not exists).")
    except Exception as e:
        print(f"⚠️  Warning creating extension: {e}")

    print("Creating data agent metadata tables...")
    try:
        # This will only create tables that do not exist
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_meta_tables()
