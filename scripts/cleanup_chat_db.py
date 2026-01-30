import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

def cleanup():
    # Force use of DATABASE_URL (chat_db) regardless of what ANALYTICS_DB points to now
    # We want to clean the *old* location
    
    # NOTE: app.core.config might have already loaded .env. 
    # But since we just edited .env.dev, and the python process for this script will start fresh,
    # it *should* see the new env... wait.
    # If we rely on config.py, it reads .env. 
    # DATABASE_URL is chat_db. 
    # So we can safely use DATABASE_URL from config.
    
    print(f"Cleaning up old schema in: {DATABASE_URL}")
    if "chat_db" not in DATABASE_URL:
        print("WARNING: DATABASE_URL does not seem to be chat_db. Aborting safety check.")
        sys.exit(1)
        
    engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        try:
            conn.execute(text("DROP SCHEMA IF EXISTS fdmdata CASCADE"))
            print("Dropped schema fdmdata and all its objects from chat_db.")
        except Exception as e:
            print(f"Error dropping schema: {e}")

if __name__ == "__main__":
    cleanup()
