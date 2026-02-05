import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL, ZHIPU_API_KEY, QWEN_API_KEY

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
        
        # 2. Insert Qwen Provider (阿里通义 - 主要对话模型)
        print("Checking/Inserting Qwen Provider...")
        qwen_api_key = QWEN_API_KEY or "check-env-vars"
        
        rows = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'qwen'")).fetchall()
        if not rows:
            conn.execute(text("""
                INSERT INTO t_llm_provider (name, code, api_key, base_url, sort_order, is_active, extra_config)
                VALUES ('阿里通义', 'qwen', :api_key, 'https://dashscope.aliyuncs.com/compatible-mode/v1', 1, TRUE, '{}')
            """), {"api_key": qwen_api_key})
            qwen_provider_id = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'qwen'")).scalar()
            print(f"Created Qwen Provider ID: {qwen_provider_id}")
        else:
            qwen_provider_id = rows[0][0]
            print(f"Found Qwen Provider ID: {qwen_provider_id}")
        
        # 3. Insert DeepSeek-V3.1 Model (铺底对话模型)
        print("Checking/Inserting DeepSeek-V3.1 Model (default chat model)...")
        rows = conn.execute(text("SELECT id FROM t_llm_model WHERE model_code = 'deepseek-v3.1' AND provider_id = :pid"), {"pid": qwen_provider_id}).fetchall()
        if not rows:
            # 清除现有 chat 类型的默认标记，避免多默认冲突
            conn.execute(text("UPDATE t_llm_model SET is_default = FALSE WHERE model_type = 'chat' AND is_default = TRUE"))
            conn.execute(text("""
                INSERT INTO t_llm_model (
                    provider_id, model_code, model_name, model_type,
                    supports_thinking, supports_tool_call, supports_streaming,
                    max_output_tokens, context_window, default_temperature, thinking_budget,
                    description, sort_order, is_default, is_active
                ) VALUES (
                    :pid, 'deepseek-v3.1', 'DeepSeek-V3.1', 'chat',
                    TRUE, TRUE, TRUE,
                    65536, 131072, 0.7, 32768,
                    'DeepSeek V3.1 685B 满血版（通过阿里云 DashScope 接入）', 1, TRUE, TRUE
                )
            """), {"pid": qwen_provider_id})
            print("Inserted deepseek-v3.1 model as default chat model.")
        else:
            print("DeepSeek-V3.1 model already exists.")
        
        # 4. Insert Zhipu Provider (智谱 - Embedding 模型)
        print("Checking/Inserting Zhipu Provider...")
        zhipu_api_key = ZHIPU_API_KEY or "check-env-vars"
        
        rows = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'zhipu'")).fetchall()
        if not rows:
            conn.execute(text("""
                INSERT INTO t_llm_provider (name, code, api_key, base_url, sort_order, is_active)
                VALUES ('智谱 AI', 'zhipu', :api_key, 'https://open.bigmodel.cn/api/paas/v4', 20, TRUE)
            """), {"api_key": zhipu_api_key})
            zhipu_provider_id = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'zhipu'")).scalar()
            print(f"Created Zhipu Provider ID: {zhipu_provider_id}")
        else:
            zhipu_provider_id = rows[0][0]
            print(f"Found Zhipu Provider ID: {zhipu_provider_id}")

        # 5. Insert Embedding Model
        print("Checking/Inserting Embedding Model...")
        rows = conn.execute(text("SELECT id FROM t_llm_model WHERE model_code = 'embedding-3'")).fetchall()
        if not rows:
            # 清除现有 embedding 类型的默认标记
            conn.execute(text("UPDATE t_llm_model SET is_default = FALSE WHERE model_type = 'embedding' AND is_default = TRUE"))
            conn.execute(text("""
                INSERT INTO t_llm_model (
                    provider_id, model_code, model_name, model_type, 
                    context_window, max_output_tokens, is_default, is_active
                ) VALUES (
                    :pid, 'embedding-3', '智谱 Embedding-3', 'embedding',
                    8192, 2048, TRUE, TRUE
                )
            """), {"pid": zhipu_provider_id})
            print("Inserted embedding-3 model.")
        else:
            print("Embedding model already exists.")

if __name__ == "__main__":
    init_llm_config()
