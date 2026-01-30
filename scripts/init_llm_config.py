import sys
from pathlib import Path
import os
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL, ZHIPU_API_KEY

def init_llm_config():
    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    # 1. Create Tables DDL
    provider_ddl = """
    CREATE TABLE IF NOT EXISTS t_llm_provider (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        code VARCHAR(50) NOT NULL UNIQUE,
        api_key VARCHAR(500),
        base_url VARCHAR(500),
        sort_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        extra_config JSONB,
        create_time TIMESTAMP DEFAULT NOW(),
        update_time TIMESTAMP DEFAULT NOW()
    );
    """
    
    model_ddl = """
    CREATE TABLE IF NOT EXISTS t_llm_model (
        id SERIAL PRIMARY KEY,
        provider_id INTEGER NOT NULL REFERENCES t_llm_provider(id) ON DELETE CASCADE,
        model_code VARCHAR(100) NOT NULL,
        model_name VARCHAR(200) NOT NULL,
        model_type VARCHAR(50) DEFAULT 'chat',
        supports_thinking BOOLEAN DEFAULT FALSE,
        supports_tool_call BOOLEAN DEFAULT TRUE,
        supports_streaming BOOLEAN DEFAULT TRUE,
        max_output_tokens INTEGER DEFAULT 4096,
        context_window INTEGER DEFAULT 32000,
        default_temperature FLOAT DEFAULT 0.7,
        thinking_budget INTEGER DEFAULT 4096,
        description TEXT,
        sort_order INTEGER DEFAULT 0,
        is_default BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        rpm_limit INTEGER,
        tpm_limit INTEGER,
        extra_config JSONB,
        create_time TIMESTAMP DEFAULT NOW(),
        update_time TIMESTAMP DEFAULT NOW()
    );
    """

    with engine.begin() as conn:
        print("Executing DDL...")
        conn.execute(text(provider_ddl))
        conn.execute(text(model_ddl))
        print("Tables t_llm_provider/t_llm_model created/verified.")
        
        # 2. Insert Default Provider (Zhipu)
        print("Checking/Inserting Zhipu Provider...")
        api_key = ZHIPU_API_KEY or "check-env-vars"
        
        # Check Zhipu provider
        rows = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'zhipu'")).fetchall()
        if not rows:
            conn.execute(text("""
                INSERT INTO t_llm_provider (name, code, api_key, base_url, is_active)
                VALUES ('Zhipu AI', 'zhipu', :api_key, 'https://open.bigmodel.cn/api/paas/v4/', TRUE)
            """), {"api_key": api_key})
            provider_id = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'zhipu'")).scalar()
            print(f"Created Zhipu Provider ID: {provider_id}")
        else:
            provider_id = rows[0][0]
            print(f"Found Zhipu Provider ID: {provider_id}")

        # 3. Insert Embedding Model
        print("Checking/Inserting Embedding Model...")
        rows = conn.execute(text("SELECT id FROM t_llm_model WHERE model_code = 'embedding-3'")).fetchall()
        if not rows:
            conn.execute(text("""
                INSERT INTO t_llm_model (
                    provider_id, model_code, model_name, model_type, 
                    context_window, max_output_tokens, is_active
                ) VALUES (
                    :pid, 'embedding-3', 'Zhipu Embedding-3', 'embedding',
                    8192, 1024, TRUE
                )
            """), {"pid": provider_id})
            print("Inserted embedding-3 model.")
        else:
            print("Embedding model already exists.")

if __name__ == "__main__":
    init_llm_config()
