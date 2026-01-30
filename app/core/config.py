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



# 数据库连接串（示例：mysql+pymysql://user:pass@host:port/schema）
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

# 意图分类器模型配置（使用轻量级快速模型）
INTENT_CLASSIFIER_MODEL = os.getenv("INTENT_CLASSIFIER_MODEL", "glm-4.5-air")

# 智谱 API Key (用于 Embedding 向量化)
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")


# 搜索
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# 技能检索
SKILL_SIMILARITY_THRESHOLD: float = float(os.getenv("SKILL_SIMILARITY_THRESHOLD", "0.5"))

# 静态资源
PUBLIC_DIR = os.getenv("PUBLIC_DIR", "public")
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", "http://localhost:8000/public")

# 功能开关
SQL_REQUIRE_APPROVAL = os.getenv("SQL_REQUIRE_APPROVAL", "true").lower() == "true"
ENABLE_THINKING = os.getenv("ENABLE_THINKING", "false").lower() == "true"
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "1024"))

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
    "postgres://postgres:postgres@localhost:5432/checkpoints"
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

