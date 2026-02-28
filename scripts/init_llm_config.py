import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.ai.scene_registry import (
    ROUTE_GROUP_DEFAULT_CHAT,
    ROUTE_GROUP_EMBEDDING,
    ROUTE_GROUP_LIGHTWEIGHT,
    ROUTE_GROUP_SQL_GENERATION,
    ROUTE_GROUP_VISION,
    SCENE_DEFINITIONS,
)
from app.core.config import DATABASE_URL, ZHIPU_API_KEY, QWEN_API_KEY


def _resolve_model_id(conn, model_code: str):
    return conn.execute(
        text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_code = :model_code
              AND is_active = TRUE
            LIMIT 1
            """
        ),
        {"model_code": model_code},
    ).scalar()


def _resolve_default_chat_model_id(conn):
    model_id = conn.execute(
        text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_type = 'chat'
              AND is_default = TRUE
              AND is_active = TRUE
            ORDER BY id ASC
            LIMIT 1
            """
        )
    ).scalar()
    if model_id:
        return model_id

    return conn.execute(
        text(
            """
            SELECT id
            FROM t_llm_model
            WHERE is_active = TRUE
            ORDER BY sort_order ASC, id ASC
            LIMIT 1
            """
        )
    ).scalar()


def _resolve_default_model_id_by_type(conn, model_type: str):
    model_id = conn.execute(
        text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_type = :model_type
              AND is_default = TRUE
              AND is_active = TRUE
            ORDER BY id ASC
            LIMIT 1
            """
        ),
        {"model_type": model_type},
    ).scalar()
    if model_id:
        return model_id

    return conn.execute(
        text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_type = :model_type
              AND is_active = TRUE
            ORDER BY sort_order ASC, id ASC
            LIMIT 1
            """
        ),
        {"model_type": model_type},
    ).scalar()


def _init_scene_configs(conn):
    scene_ddl = """
    CREATE TABLE IF NOT EXISTS t_llm_scene (
        id SERIAL PRIMARY KEY,
        scene_key VARCHAR(255) NOT NULL UNIQUE,
        scene_name VARCHAR(120) NOT NULL,
        scene_type VARCHAR(32) NOT NULL DEFAULT 'text',
        default_model_id INTEGER NOT NULL REFERENCES t_llm_model(id) ON DELETE RESTRICT,
        description TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        create_time TIMESTAMP DEFAULT NOW(),
        update_time TIMESTAMP DEFAULT NOW(),
        CONSTRAINT ck_t_llm_scene_scene_key_format CHECK (position('.' in scene_key) > 0),
        CONSTRAINT ck_t_llm_scene_scene_type CHECK (
            scene_type in ('text','image','video','audio','embedding','vision','rerank','asr','tts')
        )
    );
    """
    conn.execute(text(scene_ddl))

    default_chat_model_id = _resolve_default_chat_model_id(conn)
    if not default_chat_model_id:
        raise RuntimeError("未找到可用模型，无法初始化 t_llm_scene")

    # 单一来源模式下，scene 绑定即路由配置；初始化阶段采用稳定兜底模型。
    lightweight_model_id = (
        _resolve_model_id(conn, "qwen3.5-flash")
        or _resolve_model_id(conn, "qwen-flash")
        or default_chat_model_id
    )
    sql_generation_model_id = (
        _resolve_model_id(conn, "qwen-plus")
        or default_chat_model_id
    )
    embedding_model_id = _resolve_default_model_id_by_type(conn, "embedding")
    if not embedding_model_id:
        raise RuntimeError("未找到可用 embedding 模型，无法初始化 embedding 场景")
    vision_model_id = (
        _resolve_default_model_id_by_type(conn, "vision")
        or _resolve_default_model_id_by_type(conn, "chat")
        or _resolve_default_model_id_by_type(conn, "reasoning")
        or default_chat_model_id
    )

    model_id_by_group = {
        ROUTE_GROUP_DEFAULT_CHAT: default_chat_model_id,
        ROUTE_GROUP_LIGHTWEIGHT: lightweight_model_id,
        ROUTE_GROUP_SQL_GENERATION: sql_generation_model_id,
        ROUTE_GROUP_EMBEDDING: embedding_model_id,
        ROUTE_GROUP_VISION: vision_model_id,
    }

    upsert_sql = text(
        """
        INSERT INTO t_llm_scene (
            scene_key,
            scene_name,
            scene_type,
            default_model_id,
            description,
            is_active
        ) VALUES (
            :scene_key,
            :scene_name,
            :scene_type,
            :default_model_id,
            :description,
            TRUE
        )
        ON CONFLICT (scene_key)
        DO UPDATE SET
            scene_name = EXCLUDED.scene_name,
            scene_type = EXCLUDED.scene_type,
            default_model_id = EXCLUDED.default_model_id,
            description = EXCLUDED.description,
            is_active = TRUE,
            update_time = NOW()
        """
    )

    for scene in SCENE_DEFINITIONS:
        conn.execute(
            upsert_sql,
            {
                "scene_key": scene.scene_key,
                "scene_name": scene.scene_name,
                "scene_type": scene.scene_type,
                "default_model_id": model_id_by_group[scene.route_group],
                "description": scene.description,
            },
        )


def init_llm_config():
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)

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

        print("Checking/Inserting Qwen Provider...")
        qwen_api_key = QWEN_API_KEY or "check-env-vars"
        rows = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'qwen'"))
        qwen_provider_id = rows.scalar()
        if not qwen_provider_id:
            conn.execute(
                text(
                    """
                    INSERT INTO t_llm_provider (name, code, api_key, base_url, sort_order, is_active, extra_config)
                    VALUES ('阿里通义', 'qwen', :api_key, 'https://dashscope.aliyuncs.com/compatible-mode/v1', 1, TRUE, '{}')
                    """
                ),
                {"api_key": qwen_api_key},
            )
            qwen_provider_id = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'qwen'"))
            qwen_provider_id = qwen_provider_id.scalar()
            print(f"Created Qwen Provider ID: {qwen_provider_id}")
        else:
            print(f"Found Qwen Provider ID: {qwen_provider_id}")

        print("Checking/Inserting DeepSeek-V3.1 Model (default chat model)...")
        rows = conn.execute(
            text("SELECT id FROM t_llm_model WHERE model_code = 'deepseek-v3.1' AND provider_id = :pid"),
            {"pid": qwen_provider_id},
        )
        if not rows.scalar():
            conn.execute(text("UPDATE t_llm_model SET is_default = FALSE WHERE model_type = 'chat' AND is_default = TRUE"))
            conn.execute(
                text(
                    """
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
                    """
                ),
                {"pid": qwen_provider_id},
            )
            print("Inserted deepseek-v3.1 model as default chat model.")
        else:
            print("DeepSeek-V3.1 model already exists.")

        print("Checking/Inserting Zhipu Provider...")
        zhipu_api_key = ZHIPU_API_KEY or "check-env-vars"
        rows = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'zhipu'"))
        zhipu_provider_id = rows.scalar()
        if not zhipu_provider_id:
            conn.execute(
                text(
                    """
                    INSERT INTO t_llm_provider (name, code, api_key, base_url, sort_order, is_active)
                    VALUES ('智谱 AI', 'zhipu', :api_key, 'https://open.bigmodel.cn/api/paas/v4', 20, TRUE)
                    """
                ),
                {"api_key": zhipu_api_key},
            )
            zhipu_provider_id = conn.execute(text("SELECT id FROM t_llm_provider WHERE code = 'zhipu'"))
            zhipu_provider_id = zhipu_provider_id.scalar()
            print(f"Created Zhipu Provider ID: {zhipu_provider_id}")
        else:
            print(f"Found Zhipu Provider ID: {zhipu_provider_id}")

        print("Checking/Inserting Embedding Model...")
        rows = conn.execute(text("SELECT id FROM t_llm_model WHERE model_code = 'embedding-3'"))
        if not rows.scalar():
            conn.execute(text("UPDATE t_llm_model SET is_default = FALSE WHERE model_type = 'embedding' AND is_default = TRUE"))
            conn.execute(
                text(
                    """
                    INSERT INTO t_llm_model (
                        provider_id, model_code, model_name, model_type,
                        context_window, max_output_tokens, is_default, is_active
                    ) VALUES (
                        :pid, 'embedding-3', '智谱 Embedding-3', 'embedding',
                        8192, 2048, TRUE, TRUE
                    )
                    """
                ),
                {"pid": zhipu_provider_id},
            )
            print("Inserted embedding-3 model.")
        else:
            print("Embedding model already exists.")

        _init_scene_configs(conn)
        print(f"t_llm_scene initialized with {len(SCENE_DEFINITIONS)} scene entries.")


if __name__ == "__main__":
    init_llm_config()
