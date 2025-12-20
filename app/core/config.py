"""配置管理：集中管理环境变量与应用设置（中文注释）。"""
import os
from datetime import timedelta

from dotenv import load_dotenv

# 加载 .env 文件中的环境变量（若存在）
load_dotenv()


# 数据库连接串（示例：mysql+pymysql://user:pass@host:port/schema）
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:13006/chat_db",
)

# JWT 配置
JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
INIT_DB_ON_STARTUP: bool = os.getenv("INIT_DB_ON_STARTUP", "false").lower() in {"1","true","yes"}


def access_token_expires() -> timedelta:
    """返回访问令牌的过期时间间隔。"""
    return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
