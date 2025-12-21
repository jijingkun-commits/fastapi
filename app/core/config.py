"""配置管理：集中管理环境变量与应用设置（中文注释）。"""
import os
from datetime import timedelta

from dotenv import load_dotenv

# 加载 .env 文件中的环境变量（若存在）
load_dotenv()

# 运行环境（dev/test/prod）
ENV: str = os.getenv("ENV", "dev").lower()


# 数据库连接串（示例：mysql+pymysql://user:pass@host:port/schema）
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:13006/chat_db",
)

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
