import sys
import os
import re
from collections import Counter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import DATABASE_URL, ANALYTICS_DATABASE_URL

def get_existing_tables(engine):
    """Fetch all existing table names (schema.table) from the analytics database."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        """))
        # Normalize to lowercase: 'schema.table'
        return {f"{row[0]}.{row[1]}".lower() for row in result}

def extract_tables_from_sql(sql_template):
    """Extract table references from SQL template."""
    if not sql_template:
        return set()
    
    # Improved regex to capture FROM/JOIN schema.table
    # Look for: FROM/JOIN [optional whitespace] [schema.table]
    pattern = r'(?:FROM|JOIN)\s+([a-z0-9_]+\.[a-z0-9_]+)'
    
    matches = re.findall(pattern, sql_template.lower(), re.IGNORECASE)
    
    # Filter for known schemas to avoid false positives (e.g., aliases)
    valid_schemas = {'fdmdata', 'sdmdata', 'admdata', 'odsfile'}
    
    tables = set()
    for m in matches:
        parts = m.split('.')
        if len(parts) == 2 and parts[0] in valid_schemas:
            tables.add(m)
            
    return tables

def main():
    print(f"Connecting to Chat DB: {DATABASE_URL}")
    print(f"Connecting to Data DB: {ANALYTICS_DATABASE_URL}")
    
    chat_engine = create_engine(str(DATABASE_URL))
    data_engine = create_engine(str(ANALYTICS_DATABASE_URL))

    existing_tables = get_existing_tables(data_engine)
    print(f"Found {len(existing_tables)} existing tables in Data DB.")
    # print(existing_tables)

    with chat_engine.connect() as conn:
        metrics = conn.execute(text("""
            SELECT metric_id, metric_name, sql_template 
            FROM t_metric_definition 
            WHERE sql_template IS NOT NULL
        """)).fetchall()

    total_with_sql = len(metrics)
    ready_count = 0
    blocked_metrics = [] # List of (metric_name, missing_tables_set)
    missing_table_impact = Counter()

    print(f"Analyzing {total_with_sql} metrics with SQL templates...")

    for m in metrics:
        metric_id = m[0]
        metric_name = m[1]
        sql = m[2]
        
        required_tables = extract_tables_from_sql(sql)
        missing_tables = {t for t in required_tables if t not in existing_tables}
        
        # Heuristic fix: 'fdmdata.f_mid_index_result' is often used for derive metrics
        # We might not need this table if we implement derived logic via code, 
        # but for now let's treat it as a missing physical table.
        
        if not missing_tables:
            ready_count += 1
        else:
            blocked_metrics.append((metric_name, missing_tables))
            for t in missing_tables:
                missing_table_impact[t] += 1

    availability_rate = (ready_count / total_with_sql) * 100 if total_with_sql > 0 else 0
    
    print("\n" + "="*50)
    print("📊 METRIC AVAILABILITY REPORT")
    print("="*50)
    print(f"Total Metrics with SQL: {total_with_sql}")
    print(f"Ready to Query:         {ready_count} ({availability_rate:.1f}%)")
    print(f"Blocked by Missing Tbl: {total_with_sql - ready_count}")
    
    print("\n" + "="*50)
    print("🚀 TOP 15 MISSING TABLES BY IMPACT")
    print("(Creating these tables unlocks the most metrics)")
    print("="*50)
    
    print(f"{'Table Name':<40} | {'Blocked Metrics':<15} | {'Cumulative %':<10}")
    print("-" * 70)
    
    sorted_missing = missing_table_impact.most_common(15)
    
    cumulative_unblocked = 0
    # Note: Cumulative sum here is a simplification, as metrics might miss multiple tables.
    # But it gives a good rough estimate of value.
    
    for table, count in sorted_missing:
        print(f"{table:<40} | {count:<15} |")

    print("\n" + "="*50)
    print("💡 RECOMMENDATION")
    print("="*50)
    
    if sorted_missing:
        top_table = sorted_missing[0][0]
        print(f"Prioritize importing: {top_table}")
        if "org_tree" in top_table:
            print("This is the Organization Dimension table, used for almost all aggregations.")
        if "dim_date" in top_table:
            print("This is the Date Dimension table, used for time-based analysis.")

if __name__ == "__main__":
    main()
