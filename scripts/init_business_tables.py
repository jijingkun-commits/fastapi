import sys
from pathlib import Path
import re

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import ANALYTICS_DATABASE_URL

def clean_ddl(ddl_content: str) -> str:
    """
    Clean Greenplum/DW specific DDL for standard PostgreSQL compatibility.
    Targeting the specific structure of the provided DDL file.
    Structure: CREATE TABLE ... ( ... columns ... ) WITH (appendonly=true...) DISTRIBUTED BY ... PARTITION BY ... ;
    We want to keep: CREATE TABLE ... ( ... columns ... );
    """
    # Robust Regex to remove Greenplum specific tail
    # Pattern: Match closing paren of columns, then whitespace, then WITH (appendonly=true, then anything until semicolon.
    # We replace it with `);`
    
    # Using specific anchor text from the file for safety
    pattern = r'\)\s+WITH\s*\(appendonly=true.*?;'
    
    cleaned = re.sub(pattern, ');', ddl_content, flags=re.DOTALL | re.IGNORECASE)
    
    return cleaned

def init_tables():
    print(f"Connecting to Analytics DB: {ANALYTICS_DATABASE_URL}")
    # Use autocommit to avoid "InFailedSqlTransaction" if one statement fails
    engine = create_engine(ANALYTICS_DATABASE_URL, isolation_level="AUTOCOMMIT")
    
    # Read the DDL file
    ddl_path = Path(__file__).resolve().parents[1] / "docs/内部参考/数据资料/存款和贷款表结构.txt"
    try:
        with open(ddl_path, "r", encoding="utf-8") as f:
            raw_ddl = f.read()
    except UnicodeDecodeError:
        with open(ddl_path, "r", encoding="gb18030") as f:
            raw_ddl = f.read()

    cleaned_ddl = clean_ddl(raw_ddl)
    
    with engine.connect() as conn:
        # Create Schema
        try:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS fdmdata;"))
            print("Schema 'fdmdata' ensured.")
        except Exception as e:
            print(f"Error creating schema: {e}")
        
        # Execute statements
        statements = [stmt.strip() for stmt in cleaned_ddl.split(';') if stmt.strip()]
        
        for stmt in statements:
            try:
                # Skip partial empty or comment-only parts
                if not stmt: continue
                conn.execute(text(stmt))
                print(f"Executed statement: {stmt[:50]}...")
            except Exception as e:
                print(f"Error executing statement: {stmt[:100]}...\nError: {e}")

if __name__ == "__main__":
    init_tables()
