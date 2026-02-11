"""Alembic 环境配置。

支持从 .env 读取 DATABASE_URL，自动发现所有模型。
"""
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 将项目根目录加入 sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
import os
load_dotenv()

# 导入 Base 和所有模型
from app.db.base import Base
from app.models.user import User
from app.models.todo import Todo, TodoHistory, TodoReminderQueue
from app.models.chat_message import ChatMessage
from app.models.chat_asset import ChatAsset
from app.models.data_agent_metadata import MetaTable, MetaColumn, MetaRelation
from app.models.result_enrichment_rule import ResultEnrichmentRule, ResultEnrichmentRuleAudit
from app.models.token_blacklist import TokenBlacklist

# Alembic 配置
config = context.config

# 设置数据库 URL
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
else:
    raise ValueError("DATABASE_URL 环境变量未设置")

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 模型元数据（用于自动生成迁移）
target_metadata = Base.metadata

# 忽略不在模型中的表（LangGraph checkpoints、LLM 配置等）
EXCLUDE_TABLES = {
    "checkpoints", "checkpoint_writes", "checkpoint_blobs", "checkpoint_migrations",
    "t_llm_model", "t_llm_provider", "t_system_config", "t_chat_feedback",
    "t_metrics", "f_mid_dep_tb", "f_mid_loan_tb", "t_dmp_ind_info",
    "schema_migrations", "t_agent_skills", "t_data_query_log",
    "alembic_version",
}

def include_object(object, name, type_, reflected, compare_to):
    """过滤要迁移的对象。"""
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """离线模式运行迁移（生成 SQL 脚本）。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移（直接连接数据库）。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=False,  # 忽略类型细微差异（JSONB vs JSON）
            compare_server_default=False,  # 忽略默认值差异
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
