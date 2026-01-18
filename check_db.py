import sys
import os
# Add current directory to path
sys.path.insert(0, os.getcwd())

from app.core.config import DATABASE_URL
from sqlalchemy import create_engine, inspect

print(f"Checking DB: {DATABASE_URL}")
try:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables found: {tables}")
    required = ['t_user', 't_chat_message']
    missing = [t for t in required if t not in tables]
    if missing:
        print(f"ERROR: Missing tables: {missing}")
        sys.exit(1)
    print("SUCCESS: Database check passed.")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
