"""Schema 路由器：根据问题自动选择查询的 Schema（中文注释）。

提供多数据源场景下的 Schema 路由功能：
- 关键词匹配：根据问题中的业务关键词选择 Schema
- 表名前缀：根据表名前缀识别所属 Schema
- 显式指定：支持用户通过 @schema 语法显式指定
- 默认回退：无法识别时使用默认 Schema
"""
import re
import logging
from typing import Optional, Tuple, List

from app.core.config import (
    ANALYTICS_SCHEMAS,
    ANALYTICS_DEFAULT_SCHEMA,
    SCHEMA_ALIASES,
)

logger = logging.getLogger(__name__)


# ==================== 表名前缀规则 ====================

# 表名前缀 -> Schema 映射
TABLE_PREFIX_RULES = {
    "f_mid_": "fdmdata",      # 金融中间表
    "f_ods_": "fdmdata",      # 金融 ODS 表
    "f_dwd_": "fdmdata",      # 金融明细表
    "f_dws_": "fdmdata",      # 金融汇总表
    "s_ods_": "sdmdata",      # 维度 ODS 表
    "s_dim_": "sdmdata",      # 维度表
    "dim_": "sdmdata",        # 维度表（简写）
}


# ==================== 主要函数 ====================

def route_schema(question: str, sql: Optional[str] = None) -> str:
    """根据问题和 SQL 自动路由到合适的 Schema。
    
    路由优先级：
    1. 显式指定（@fdmdata、@sdmdata 等）
    2. SQL 中的表名前缀
    3. 问题中的业务关键词
    4. 默认 Schema
    
    Args:
        question: 用户问题
        sql: 生成的 SQL（可选）
        
    Returns:
        目标 Schema 名称
    """
    # 1. 检查显式指定
    explicit_schema = extract_explicit_schema(question)
    if explicit_schema:
        logger.info(f"Schema 路由: 显式指定 -> {explicit_schema}")
        return explicit_schema
    
    # 2. 检查 SQL 中的表名前缀
    if sql:
        schema_from_sql = detect_schema_from_sql(sql)
        if schema_from_sql:
            logger.info(f"Schema 路由: SQL 表名前缀 -> {schema_from_sql}")
            return schema_from_sql
    
    # 3. 检查问题中的业务关键词
    schema_from_keywords = match_schema_by_keywords(question)
    if schema_from_keywords:
        logger.info(f"Schema 路由: 关键词匹配 -> {schema_from_keywords}")
        return schema_from_keywords
    
    # 4. 默认 Schema
    logger.info(f"Schema 路由: 使用默认 -> {ANALYTICS_DEFAULT_SCHEMA}")
    return ANALYTICS_DEFAULT_SCHEMA


def extract_explicit_schema(question: str) -> Optional[str]:
    """从问题中提取显式指定的 Schema。
    
    支持格式：
    - @fdmdata 存款余额是多少
    - 查询 @sdmdata 的日期数据
    
    Args:
        question: 用户问题
        
    Returns:
        显式指定的 Schema（如果有）
    """
    # 匹配 @schema 格式
    pattern = r'@(\w+)'
    match = re.search(pattern, question)
    
    if match:
        schema = match.group(1).lower()
        # 验证是否在白名单中
        allowed = [s.lower() for s in ANALYTICS_SCHEMAS]
        if schema in allowed:
            return schema
        else:
            logger.warning(f"显式指定的 Schema '{schema}' 不在白名单中")
    
    return None


def remove_explicit_schema(question: str) -> str:
    """从问题中移除显式指定的 Schema 标记。
    
    Args:
        question: 原始问题
        
    Returns:
        移除 @schema 后的问题
    """
    return re.sub(r'@\w+\s*', '', question).strip()


def detect_schema_from_sql(sql: str) -> Optional[str]:
    """从 SQL 中检测表名前缀，推断 Schema。
    
    Args:
        sql: SQL 语句
        
    Returns:
        推断的 Schema（如果能识别）
    """
    sql_lower = sql.lower()
    
    for prefix, schema in TABLE_PREFIX_RULES.items():
        if prefix in sql_lower:
            return schema
    
    return None


def match_schema_by_keywords(question: str) -> Optional[str]:
    """根据问题中的业务关键词匹配 Schema。
    
    使用配置的 SCHEMA_ALIASES 进行匹配。
    
    Args:
        question: 用户问题
        
    Returns:
        匹配的 Schema（如果有）
    """
    question_lower = question.lower()
    
    for alias, schema in SCHEMA_ALIASES.items():
        if alias.lower() in question_lower:
            return schema
    
    return None


def detect_schema_from_table_name(table_name: str) -> Optional[str]:
    """根据表名检测所属 Schema。
    
    Args:
        table_name: 表名（可能包含 schema 前缀）
        
    Returns:
        推断的 Schema
    """
    # 如果已经包含 schema 前缀（如 fdmdata.f_mid_dep_tb）
    if '.' in table_name:
        schema = table_name.split('.')[0].lower()
        allowed = [s.lower() for s in ANALYTICS_SCHEMAS]
        if schema in allowed:
            return schema
    
    # 根据表名前缀判断
    table_lower = table_name.lower()
    for prefix, schema in TABLE_PREFIX_RULES.items():
        if table_lower.startswith(prefix):
            return schema
    
    return None


def get_full_table_name(table_name: str, schema: Optional[str] = None) -> str:
    """获取完整的表名（包含 Schema 前缀）。
    
    Args:
        table_name: 表名
        schema: Schema（如果不提供则自动检测）
        
    Returns:
        完整表名（schema.table_name 格式）
    """
    # 如果已经有 schema 前缀
    if '.' in table_name:
        return table_name
    
    # 尝试自动检测
    if not schema:
        schema = detect_schema_from_table_name(table_name)
    
    # 使用默认 schema
    if not schema:
        schema = ANALYTICS_DEFAULT_SCHEMA
    
    return f"{schema}.{table_name}"


def get_routing_context(question: str) -> dict:
    """获取路由上下文信息（用于调试）。
    
    Args:
        question: 用户问题
        
    Returns:
        包含路由信息的字典
    """
    return {
        "question": question,
        "explicit_schema": extract_explicit_schema(question),
        "keyword_match": match_schema_by_keywords(question),
        "default_schema": ANALYTICS_DEFAULT_SCHEMA,
        "allowed_schemas": ANALYTICS_SCHEMAS,
        "schema_aliases": SCHEMA_ALIASES,
    }


# ==================== 导出 ====================

__all__ = [
    "route_schema",
    "extract_explicit_schema",
    "remove_explicit_schema",
    "detect_schema_from_sql",
    "match_schema_by_keywords",
    "detect_schema_from_table_name",
    "get_full_table_name",
    "get_routing_context",
    "TABLE_PREFIX_RULES",
]
