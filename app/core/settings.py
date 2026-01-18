from typing import Optional, Literal
from pydantic import Field, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    应用配置校验模型
    
    用于在启动时校验关键环境变量是否正确配置。
    """
    
    # 核心配置
    ENV: str = Field(default="dev", description="运行环境")
    DATABASE_URL: str = Field(..., description="数据库连接串")
    
    # JWT
    JWT_SECRET: str = Field(..., min_length=8, description="JWT 密钥")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=120, gt=0)
    
    # MinIO
    MINIO_ENDPOINT: str = Field(default="localhost:19000")
    MINIO_ACCESS_KEY: str = Field(...)
    MINIO_SECRET_KEY: str = Field(...)
    MINIO_BUCKET_ASSETS: str = Field(default="chat-assets")
    
    # AI 提供商
    MODEL_PROVIDER: Literal["qwen", "deepseek"] = Field(default="qwen")
    
    # 智谱 (Vision)
    ZHIPU_API_KEY: Optional[str] = Field(None, description="智谱 API Key (若使用相关功能则必填)")
    
    # RAGFlow
    RAGFLOW_BASE_URL: str = "http://localhost:9380"
    RAGFLOW_API_KEY: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore" # 忽略未定义的变量
    )

# 实例化即进行校验
# settings = Settings()
