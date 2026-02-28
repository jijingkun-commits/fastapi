"""配置管理：集中管理环境变量与应用设置（中文注释）。"""
# Force reload for env update
import os

# Fix for MCP 502 Error: Bypass system proxy for local addresses
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

from datetime import timedelta

from dotenv import load_dotenv
from pathlib import Path

_ENV = os.getenv("ENV", "dev").lower()
# parents[2] = 项目根目录 (config.py -> core -> app -> fastapi)
_BASE = Path(__file__).resolve().parents[2]
dotenv_path = _BASE / f".env.{_ENV}"
load_dotenv(dotenv_path, override=True)

ENV: str = _ENV
PROJECT_ROOT: Path = _BASE



# 数据库连接串（示例：postgresql+psycopg://user:pass@host:port/schema）
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/chat_db",
)

# 问数 Agent 专用分析库（只读连接）
ANALYTICS_DATABASE_URL: str = os.getenv(
    "ANALYTICS_DATABASE_URL",
    DATABASE_URL, # 默认回退到主库，但在生产环境应隔离
)

# 问数允许的 Schema 白名单（逗号分隔）
_analytics_schemas_str = os.getenv("ANALYTICS_SCHEMAS", "fdmdata,sdmdata,public")
ANALYTICS_SCHEMAS: list = [s.strip().lower() for s in _analytics_schemas_str.split(",") if s.strip()]

# 默认 Schema（无法识别时使用）
ANALYTICS_DEFAULT_SCHEMA: str = os.getenv("ANALYTICS_DEFAULT_SCHEMA", "fdmdata")

# Schema 别名映射（用户友好名称 -> 实际 schema）
# 格式：alias1:schema1,alias2:schema2
_schema_aliases_str = os.getenv("SCHEMA_ALIASES", "存款:fdmdata,贷款:fdmdata,维度:sdmdata,日期:sdmdata")
SCHEMA_ALIASES: dict = {}
for pair in _schema_aliases_str.split(","):
    if ":" in pair:
        alias, schema = pair.split(":", 1)
        SCHEMA_ALIASES[alias.strip()] = schema.strip().lower()

# Embedding 向量维度（必须与数据库 Vector 列定义一致）
# 智谱 embedding-3: 2048 维, embedding-2: 1024 维
# 重要：数据库中 Vector 列均定义为 2048 维，必须使用 embedding-3 模型
EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "2048"))

# 数据库连接池参数
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_ECHO: bool = os.getenv("DB_ECHO", "false" if ENV == "prod" else "true").lower() in {"1","true","yes"}

# JWT 配置
JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
INIT_DB_ON_STARTUP: bool = os.getenv("INIT_DB_ON_STARTUP", "false").lower() in {"1","true","yes"}

# 日志相关配置
# 默认等级：非 prod 用 DEBUG，prod 用 INFO，可被 LOG_LEVEL 覆盖
_DEFAULT_LOG_LEVEL = "INFO" if ENV == "prod" else "DEBUG"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", _DEFAULT_LOG_LEVEL).upper()
LOG_FILE: str = os.getenv("LOG_FILE", "logs/assistant.log")
LOG_ROTATE_WHEN: str = os.getenv("LOG_ROTATE_WHEN", "midnight")
LOG_ROTATE_INTERVAL: int = int(os.getenv("LOG_ROTATE_INTERVAL", "1"))
LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
LOG_COLORIZE: bool = os.getenv("LOG_COLORIZE", "true").lower() in {"1","true","yes"}

# CORS 允许的来源（逗号分隔）。非 prod 默认全放开，prod 需显式设置。
_DEFAULT_CORS_ORIGINS = "*" if ENV != "prod" else ""
CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", _DEFAULT_CORS_ORIGINS)



def access_token_expires() -> timedelta:
    """返回访问令牌的过期时间间隔。"""
    return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)


# ==========================================
# AI & MCP 相关配置 (补充 app/ai/config.py 依赖)
# ==========================================

# AI 模型配置
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "qwen")
MODEL_TYPE = os.getenv("MODEL_TYPE", "chat")
MODEL_NAME = os.getenv("MODEL_NAME", "glm-4.5-air")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.7"))
MESSAGE_MAX_TOKENS = int(os.getenv("MESSAGE_MAX_TOKENS", "4096"))

# Agent Specific Models
MODEL_CORE_NAME = os.getenv("MODEL_CORE_NAME", MODEL_NAME)
MODEL_REVIEW_NAME = os.getenv("MODEL_REVIEW_NAME", MODEL_NAME)
MODEL_DEBUG_NAME = os.getenv("MODEL_DEBUG_NAME", MODEL_NAME)

# AI 参数
STREAMING = os.getenv("STREAMING", "true").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "medium")

# 意图分类器模型配置（使用轻量级快速模型，推荐非推理模型如 qwen-plus）
# 注意：运行时优先从 t_system_config 读取，此处为回退默认值
INTENT_CLASSIFIER_MODEL = os.getenv("INTENT_CLASSIFIER_MODEL", "qwen-plus")

# 智谱 API Key (用于 Embedding 向量化)
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")

# 阿里云 DashScope API Key (用于 Qwen/DeepSeek 模型)
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")


# 搜索
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# 技能检索
SKILL_SIMILARITY_THRESHOLD: float = float(os.getenv("SKILL_SIMILARITY_THRESHOLD", "0.55"))

# 静态资源
PUBLIC_DIR = os.getenv("PUBLIC_DIR", "public")
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000/public")

# 功能开关
SQL_REQUIRE_APPROVAL = os.getenv("SQL_REQUIRE_APPROVAL", "true").lower() == "true"
ENABLE_THINKING = os.getenv("ENABLE_THINKING", "false").lower() == "true"
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "1024"))

# 跨会话用户偏好记忆开关
ENABLE_USER_PREFERENCE_MEMORY = os.getenv("ENABLE_USER_PREFERENCE_MEMORY", "false").lower() == "true"
USER_PREFERENCE_MEMORY_MAX_ITEMS = int(os.getenv("USER_PREFERENCE_MEMORY_MAX_ITEMS", "8"))

# 文档化永久记忆开关（两表方案）
ENABLE_DOCUMENT_MEMORY = os.getenv("ENABLE_DOCUMENT_MEMORY", "false").lower() == "true"
ENABLE_DOCUMENT_MEMORY_RECALL = os.getenv("ENABLE_DOCUMENT_MEMORY_RECALL", "false").lower() == "true"
ENABLE_DOCUMENT_MEMORY_FLUSH = os.getenv("ENABLE_DOCUMENT_MEMORY_FLUSH", "false").lower() == "true"
ENABLE_DOCUMENT_MEMORY_HYBRID_SEARCH = (
    os.getenv("ENABLE_DOCUMENT_MEMORY_HYBRID_SEARCH", "false").lower() == "true"
)
ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER = (
    os.getenv("ENABLE_DOCUMENT_MEMORY_EMBEDDING_WORKER", "false").lower() == "true"
)
ENABLE_DOCUMENT_MEMORY_ADMIN_API = (
    os.getenv("ENABLE_DOCUMENT_MEMORY_ADMIN_API", "false").lower() == "true"
)
DOCUMENT_MEMORY_MAX_RESULTS = int(os.getenv("DOCUMENT_MEMORY_MAX_RESULTS", "6"))
DOCUMENT_MEMORY_MAX_INJECTED_CHARS = int(os.getenv("DOCUMENT_MEMORY_MAX_INJECTED_CHARS", "1200"))
DOCUMENT_MEMORY_VECTOR_WEIGHT = float(os.getenv("DOCUMENT_MEMORY_VECTOR_WEIGHT", "0.7"))
DOCUMENT_MEMORY_TEXT_WEIGHT = float(os.getenv("DOCUMENT_MEMORY_TEXT_WEIGHT", "0.3"))
DOCUMENT_MEMORY_HYBRID_MIN_SCORE = float(os.getenv("DOCUMENT_MEMORY_HYBRID_MIN_SCORE", "0.05"))
DOCUMENT_MEMORY_EMBEDDING_BATCH_SIZE = int(
    os.getenv("DOCUMENT_MEMORY_EMBEDDING_BATCH_SIZE", "32")
)
DOCUMENT_MEMORY_EMBEDDING_MAX_RETRY = int(
    os.getenv("DOCUMENT_MEMORY_EMBEDDING_MAX_RETRY", "3")
)

# 结果增强规则开关与缓存 TTL
ENABLE_RESULT_ENRICHMENT = os.getenv("ENABLE_RESULT_ENRICHMENT", "true").lower() == "true"
RESULT_ENRICHMENT_RULE_TTL_SECONDS = int(os.getenv("RESULT_ENRICHMENT_RULE_TTL_SECONDS", "120"))

# 中转供应商实验适配环境变量兜底（优先读取 t_system_config 中的 feature.* 开关）
# 仅当数据库未配置对应键时才使用以下环境变量
ENABLE_PROXY_EXPERIMENT = os.getenv("ENABLE_PROXY_EXPERIMENT", "false").lower() == "true"
_proxy_provider_codes = os.getenv("PROXY_EXPERIMENT_PROVIDERS", "openai_proxy_trial")
PROXY_EXPERIMENT_PROVIDERS = {
    code.strip() for code in _proxy_provider_codes.split(",") if code.strip()
}

# internal 消息内容清洗开关（用于兼容 Responses 风格 content block）
# 默认值：非 prod 为 true，prod 为 false（可通过环境变量覆盖）
ENABLE_INTERNAL_CONTENT_SANITIZE = os.getenv(
    "ENABLE_INTERNAL_CONTENT_SANITIZE",
    "true" if ENV != "prod" else "false",
).lower() == "true"

# 规则体系与命令注册中心灰度开关（C-5）
ENABLE_RULESET_V2 = os.getenv("ENABLE_RULESET_V2", "false").lower() == "true"
ENABLE_PROMPT_REGISTRY_V2 = os.getenv("ENABLE_PROMPT_REGISTRY_V2", "false").lower() == "true"
RULESET_V2_ROLLOUT_PERCENTAGE = int(os.getenv("RULESET_V2_ROLLOUT_PERCENTAGE", "0"))
PROMPT_REGISTRY_V2_ROLLOUT_PERCENTAGE = int(
    os.getenv("PROMPT_REGISTRY_V2_ROLLOUT_PERCENTAGE", "0")
)

# LLM Judge 输出评估（用于问数助手 SQL 质量评估）
ENABLE_LLM_JUDGE = os.getenv("ENABLE_LLM_JUDGE", "false").lower() == "true"
# 注意：运行时优先从 t_system_config 读取，此处为回退默认值
LLM_JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", "qwen-plus")

# SQL 生成 / 内部分析模型配置（标准模型，非推理模型）
# 注意：运行时优先从 t_system_config 读取，此处为回退默认值
SQL_GENERATION_MODEL = os.getenv("SQL_GENERATION_MODEL", "qwen-plus")


# ==========================================
# 模型路由配置键（t_system_config 中的 key）
# ==========================================
MODEL_ROUTING_DEFAULT_CHAT = "model_routing.default_chat"          # 默认对话模型：未显式传 model_id 时使用
MODEL_ROUTING_INTENT_CLASSIFIER = "model_routing.lightweight"      # 轻量任务：意图分类
MODEL_ROUTING_LLM_JUDGE = "model_routing.lightweight"              # 轻量任务：评估/参数提取（与意图分类共享同一配置）
MODEL_ROUTING_SQL_GENERATION = "model_routing.sql_generation"      # SQL 生成 / 内部分析
MODEL_ROUTING_EMBEDDING = "embedding"                              # Embedding 向量化路由
MODEL_ROUTING_VISION = "vision"                                    # Vision 多模态路由（优先于 type=vision 默认模型）

# 模型调用场景（供 get_scene_llm 使用）
MODEL_SCENE_DEFAULT_CHAT = "default_chat"
MODEL_SCENE_LIGHTWEIGHT = "lightweight"
MODEL_SCENE_SQL_GENERATION = "sql_generation"


def get_scene_routing(scene: str) -> tuple[str, str]:
    """获取模型调用场景对应的路由键与环境变量回退值。"""
    scene_map = {
        MODEL_SCENE_DEFAULT_CHAT: (MODEL_ROUTING_DEFAULT_CHAT, ""),
        MODEL_SCENE_LIGHTWEIGHT: (MODEL_ROUTING_INTENT_CLASSIFIER, INTENT_CLASSIFIER_MODEL),
        MODEL_SCENE_SQL_GENERATION: (MODEL_ROUTING_SQL_GENERATION, SQL_GENERATION_MODEL),
    }
    if scene not in scene_map:
        raise ValueError(f"不支持的模型调用场景: {scene}")
    return scene_map[scene]


def get_routing_model(config_key: str, env_fallback: str) -> str:
    """获取模型路由配置（优先 t_system_config，回退环境变量）。

    Args:
        config_key: t_system_config 中的配置键
        env_fallback: 环境变量回退值

    Returns:
        模型代码
    """
    from app.services.config_resolver import ConfigResolver

    value = ConfigResolver.get_string(config_key, env_fallback)
    return value if value else env_fallback

# MCP Chart
MCP_CHART_SERVER_URL = os.getenv("MCP_CHART_SERVER_URL", "http://127.0.0.1:1122/sse")
MCP_CHART_ENABLED = os.getenv("MCP_CHART_ENABLED", "true").lower() == "true"


# MinIO (与 settings.py 保持同步，供 ai/config.py 使用)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:19000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET_ASSETS = os.getenv("MINIO_BUCKET_ASSETS", "chat-assets")


# ==========================================
# 数据库 & Checkpointer 额外配置
# ==========================================

# LangGraph Postgres Checkpointer 连接串
# 注意: langgraph 使用 psycopg 3，需要标准 postgres:// 格式
PG_CHECKPOINTER_URI: str = os.getenv(
    "PG_CHECKPOINTER_URI", 
    "postgres://postgres:postgres@localhost:5432/chat_db"
)


# ==========================================
# RAGFlow 知识库配置
# ==========================================

RAGFLOW_BASE_URL: str = os.getenv("RAGFLOW_BASE_URL", "http://localhost:9380")
RAGFLOW_API_URL: str = os.getenv("RAGFLOW_API_URL", "http://localhost:9380/api/v1")
RAGFLOW_API_KEY: str = os.getenv("RAGFLOW_API_KEY", "")

# 知识库 ID（逗号分隔支持多个）
_dataset_ids_str = os.getenv("RAGFLOW_DATASET_IDS", "")
RAGFLOW_DATASET_IDS: list = [x.strip() for x in _dataset_ids_str.split(",") if x.strip()]
RAGFLOW_DATASET_ID: str = RAGFLOW_DATASET_IDS[0] if RAGFLOW_DATASET_IDS else ""

# 检索参数
RAGFLOW_SIMILARITY_THRESHOLD: float = float(os.getenv("RAGFLOW_SIMILARITY_THRESHOLD", "0.2"))
RAGFLOW_TOP_K: int = int(os.getenv("RAGFLOW_TOP_K", "5"))
RAGFLOW_VECTOR_WEIGHT: float = float(os.getenv("RAGFLOW_VECTOR_WEIGHT", "0.6"))
