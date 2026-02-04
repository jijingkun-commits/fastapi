"""初始化系统配置数据（中文注释）。

此脚本用于将预定义的系统配置写入数据库。
用法：
    python install/scripts/init_system_config.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.repositories import config_repo


# 预定义配置项
# 格式：(key, value, value_type, category, description)
CONFIGS = [
    # AI 配置
    ("ai.message_max_tokens", "80000", "number", "ai", "消息上下文最大 token 数"),
    ("ai.enable_thinking", "false", "boolean", "ai", "是否启用深度思考模式"),
    ("ai.thinking_budget", "4096", "number", "ai", "深度思考 token 预算"),
    ("ai.reasoning_effort", "medium", "string", "ai", "思考强度: low/medium/high"),
    ("ai.streaming", "true", "boolean", "ai", "是否启用流式输出"),
    ("ai.request_timeout", "120", "number", "ai", "请求超时时间（秒）"),
    ("ai.max_retries", "2", "number", "ai", "最大重试次数"),
    ("ai.sql_require_approval", "true", "boolean", "ai", "SQL 查询是否需要人工审核"),
    
    # MCP 配置
    ("mcp.chart_server_url", "http://localhost:1122/sse", "string", "mcp", "MCP 图表服务器 URL"),
    ("mcp.chart_enabled", "true", "boolean", "mcp", "是否启用 MCP 图表工具"),
    
    # RAGFlow 配置
    ("ragflow.api_url", "http://localhost:80/api/v1", "string", "ragflow", "RAGFlow API 地址"),
    ("ragflow.base_url", "http://localhost:9380", "string", "ragflow", "RAGFlow 基础 URL"),
    ("ragflow.similarity_threshold", "0.2", "number", "ragflow", "检索相似度阈值（0-1）"),
    ("ragflow.top_k", "5", "number", "ragflow", "检索返回的最大文档数"),
    ("ragflow.vector_weight", "0.6", "number", "ragflow", "向量检索权重（0-1）"),
    ("ragflow.dataset_ids", "", "string", "ragflow", "知识库 ID 列表（逗号分隔）"),
    
    # AI 模型参数
    ("ai.model_temperature", "0.7", "number", "ai", "模型温度参数（0-2）"),
    
    # 问数助手配置
    ("askdata.schema_whitelist", "fdmdata,sdmdata,public", "string", "askdata", "允许查询的 Schema 白名单（逗号分隔）"),
    ("askdata.schema_blacklist", "pg_catalog,information_schema", "string", "askdata", "禁止查询的系统 Schema（逗号分隔）"),
    ("askdata.table_blacklist", "t_user,t_chat_message,t_chat_feedback,t_chat_asset,t_todo,t_llm_model,t_agent_skills,t_system_config,t_metric_definitions", "string", "askdata", "禁止查询的敏感表（逗号分隔）"),
    ("askdata.require_approval", "true", "boolean", "askdata", "SQL 执行是否需要人工确认"),
]


def init_system_config(db: Session):
    print("开始初始化系统配置...")
    
    for key, value, value_type, category, description in CONFIGS:
        config_repo.upsert_config(
            db=db,
            key=key,
            value=value,
            value_type=value_type,
            category=category,
            description=description
        )
        print(f"配置项: {key} = {value}")
    
    db.commit()
    print(f"系统配置初始化完成，共 {len(CONFIGS)} 项")


if __name__ == "__main__":
    with SessionLocal() as db:
        init_system_config(db)
