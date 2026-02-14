"""SQL 安全检查工具（中文注释）。

提供统一的 SQL 安全检查功能：
- 危险操作检测（DROP, DELETE, UPDATE 等）
- 敏感表访问检测
- Schema 白名单检测
- 多语句检测
- 自动添加 LIMIT

统一替代分散在 data_query_tools.py, data_graph.py, data_intent_helpers.py 中的重复实现。
"""
import re
import logging
from typing import Tuple, Optional, Set, List

from app.ai.utils.sql_parser import extract_tables_from_sql, is_select_only, get_query_type
from app.core.config import ANALYTICS_SCHEMAS

logger = logging.getLogger(__name__)


# ==================== 配置常量 ====================

# 危险 SQL 关键词（禁止执行）
DANGEROUS_KEYWORDS: Set[str] = {
    "DROP", "DELETE", "UPDATE", "TRUNCATE", "ALTER", 
    "INSERT", "CREATE", "GRANT", "REVOKE", "EXECUTE",
    "CALL",  # 存储过程调用
}

# 敏感表黑名单（默认值，运行时从数据库读取）
DEFAULT_SENSITIVE_TABLES: Set[str] = {
    # 用户/认证相关
    "t_user", "users", "t_users",
    "password", "passwords",
    "secret", "secrets",
    "token", "tokens",
    "api_key", "api_keys",
    "credential", "credentials",
    "auth", "authentication",
    # 系统配置相关
    "t_llm_model", "t_llm_models",
    "t_system_config",
    "t_agent_skills",
    "t_metric_definitions",
    # 聊天/待办相关（系统数据）
    "t_chat_message", "t_chat_asset", "t_chat_assets", "t_chat_feedback",
    "t_todo", "t_todo_history", "t_todo_reminder_queue",
    # LangGraph 检查点
    "checkpoints", "checkpoint_blobs", "checkpoint_writes",
}

# 系统 Schema 黑名单（默认值，运行时从数据库读取）
DEFAULT_SYSTEM_SCHEMAS: Set[str] = {
    "pg_catalog",
    "information_schema",
    "pg_toast",
    "pg_temp",
}

# 允许访问的 information_schema 只读视图（用于元数据查询）
# 这些视图只包含表结构信息，不含敏感数据
ALLOWED_METADATA_VIEWS: Set[str] = {
    "information_schema.tables",
    "information_schema.columns",
    "information_schema.schemata",
    "information_schema.table_constraints",
    "information_schema.key_column_usage",
    "information_schema.views",
}


def get_sensitive_tables() -> Set[str]:
    """获取敏感表黑名单（从数据库配置读取）。"""
    try:
        from app.ai.semantic.data_access_control import get_table_blacklist
        db_blacklist = get_table_blacklist()
        # 合并默认值和数据库配置
        return DEFAULT_SENSITIVE_TABLES | db_blacklist
    except Exception as e:
        logger.warning(f"获取敏感表配置失败，使用默认值: {e}")
        return DEFAULT_SENSITIVE_TABLES


def get_system_schemas() -> Set[str]:
    """获取系统 Schema 黑名单（从数据库配置读取）。"""
    try:
        from app.ai.semantic.data_access_control import get_system_schema_blacklist
        db_blacklist = get_system_schema_blacklist()
        # 合并默认值和数据库配置
        return DEFAULT_SYSTEM_SCHEMAS | db_blacklist
    except Exception as e:
        logger.warning(f"获取系统 Schema 配置失败，使用默认值: {e}")
        return DEFAULT_SYSTEM_SCHEMAS


def get_analytics_schema_allowlist() -> Set[str]:
    """获取分析 Schema 白名单（环境变量与数据库配置取交集）。"""

    env_allowlist = {s.lower() for s in ANALYTICS_SCHEMAS}

    try:
        from app.ai.semantic.data_access_control import get_analytics_schema_allowlist as _load_allowlist

        db_allowlist = {s.lower() for s in _load_allowlist()}
        if not db_allowlist:
            return env_allowlist
        if not env_allowlist:
            return db_allowlist
        return env_allowlist & db_allowlist
    except Exception as e:
        logger.warning(f"获取分析 Schema 白名单失败，使用环境变量配置: {e}")
        return env_allowlist

# 默认查询结果限制
DEFAULT_LIMIT = 1000


# ==================== 主要函数 ====================

def check_sql_safety(sql: str, check_schema: bool = True) -> Tuple[bool, Optional[str]]:
    """检查 SQL 语句的安全性（综合检查）。
    
    检查项：
    1. 是否为只读查询（SELECT/WITH）
    2. 是否包含危险操作关键词
    3. 是否访问敏感表
    4. 是否访问允许的 Schema（可选）
    5. 是否包含多条语句
    
    Args:
        sql: SQL 语句
        check_schema: 是否检查 Schema 白名单（默认 True）
        
    Returns:
        (is_safe, error_message) 元组
        - is_safe: 是否安全
        - error_message: 错误描述（如果不安全）
    """
    if not sql or not sql.strip():
        return (False, "SQL 语句为空")
    
    sql = sql.strip()
    
    # 检查是否为只读查询
    if not is_select_only(sql):
        query_type = get_query_type(sql)
        return (False, f"只允许 SELECT 查询，检测到 {query_type} 语句")
    
    # 检查危险关键词
    is_safe, error = check_dangerous_keywords(sql)
    if not is_safe:
        return (False, error)
    
    # 检查敏感表
    is_safe, error = check_sensitive_tables(sql)
    if not is_safe:
        return (False, error)
    
    # 检查 Schema 白名单
    if check_schema:
        is_safe, error = check_schema_whitelist(sql)
        if not is_safe:
            return (False, error)
    
    # 检查多语句
    is_safe, error = check_multiple_statements(sql)
    if not is_safe:
        return (False, error)
    
    return (True, None)


def check_dangerous_keywords(sql: str) -> Tuple[bool, Optional[str]]:
    """检查 SQL 是否包含危险操作关键词。
    
    使用词边界匹配，避免误判（如 "UPDATE_TIME" 不应被判定为 UPDATE）。
    
    Args:
        sql: SQL 语句
        
    Returns:
        (is_safe, error_message) 元组
    """
    sql_upper = sql.upper()
    
    for keyword in DANGEROUS_KEYWORDS:
        # 使用词边界匹配
        if re.search(rf'\b{keyword}\b', sql_upper):
            logger.warning(f"SQL 安全检查: 检测到危险关键词 {keyword}")
            return (False, f"检测到危险操作: {keyword}")
    
    return (True, None)


def check_sensitive_tables(sql: str) -> Tuple[bool, Optional[str]]:
    """检查 SQL 是否访问敏感表。
    
    使用 sqlglot 解析器提取表名，比简单正则更准确。
    敏感表列表从数据库配置动态读取。
    
    Args:
        sql: SQL 语句
        
    Returns:
        (is_safe, error_message) 元组
    """
    # 使用统一的表名提取工具
    tables = extract_tables_from_sql(sql)
    
    # 从数据库获取最新的敏感表配置
    sensitive_tables = get_sensitive_tables()
    sensitive_lower = {t.lower() for t in sensitive_tables}
    
    for table in tables:
        # 提取纯表名（去除 schema 前缀）
        table_name = table.split('.')[-1].lower()
        
        if table_name in sensitive_lower:
            logger.warning(f"SQL 安全检查: 检测到敏感表访问 {table}")
            return (False, f"检测到敏感表访问: {table}")
    
    return (True, None)


def check_schema_whitelist(sql: str) -> Tuple[bool, Optional[str]]:
    """检查 SQL 访问的 Schema 是否在白名单中。
    
    仅允许访问分析 Schema 白名单（环境变量与数据库配置交集）。
    系统 Schema 黑名单从数据库配置动态读取。
    特例：允许访问 ALLOWED_METADATA_VIEWS 中的元数据视图。
    
    Args:
        sql: SQL 语句
        
    Returns:
        (is_safe, error_message) 元组
    """
    # 使用统一的表名提取工具
    tables = extract_tables_from_sql(sql)
    
    # 标准化允许的 Schema（小写）
    allowed_schemas = get_analytics_schema_allowlist()
    # 从数据库获取最新的系统 Schema 黑名单
    system_schemas = get_system_schemas()
    system_schemas_lower = {s.lower() for s in system_schemas}
    # 允许的元数据视图（小写）
    allowed_metadata_views = {v.lower() for v in ALLOWED_METADATA_VIEWS}
    
    for table in tables:
        # 检查是否包含 schema 前缀
        if '.' in table:
            full_table = table.lower()
            parts = table.split('.')
            schema = parts[0].lower()
            
            # 优先检查是否为允许的元数据视图
            if full_table in allowed_metadata_views:
                logger.debug(f"SQL 安全检查: 允许访问元数据视图 {table}")
                continue
            
            # 检查系统 Schema 黑名单
            if schema in system_schemas_lower:
                logger.warning(f"SQL 安全检查: 检测到系统 Schema 访问 {schema}")
                return (False, f"禁止访问系统 Schema: {schema}")
            
            # 检查 Schema 白名单
            if schema not in allowed_schemas:
                logger.warning(f"SQL 安全检查: Schema {schema} 不在白名单中")
                return (False, f"Schema '{schema}' 不在允许访问的范围内。允许的 Schema: {', '.join(allowed_schemas)}")
    
    return (True, None)


def check_multiple_statements(sql: str) -> Tuple[bool, Optional[str]]:
    """检查 SQL 是否包含多条语句。
    
    通过分号分隔检测，防止 SQL 注入攻击。
    处理顺序：移除字符串字面量 -> 移除 SQL 注释 -> 按分号分割。
    
    Args:
        sql: SQL 语句
        
    Returns:
        (is_safe, error_message) 元组
    """
    # 移除字符串字面量中的分号（简化处理）
    sql_cleaned = re.sub(r"'[^']*'", "''", sql)  # 替换单引号字符串
    sql_cleaned = re.sub(r'"[^"]*"', '""', sql_cleaned)  # 替换双引号字符串
    
    # 移除 SQL 注释，避免 "; -- comment" 被误判为多条语句
    sql_cleaned = re.sub(r'--[^\n]*', '', sql_cleaned)  # 行注释
    sql_cleaned = re.sub(r'/\*.*?\*/', '', sql_cleaned, flags=re.DOTALL)  # 块注释
    
    # 检查分号
    statements = [s.strip() for s in sql_cleaned.split(';') if s.strip()]
    
    if len(statements) > 1:
        logger.warning(f"SQL 安全检查: 检测到多条语句 ({len(statements)} 条)")
        return (False, "不允许执行多条 SQL 语句")
    
    return (True, None)


def add_limit_if_missing(sql: str, limit: int = DEFAULT_LIMIT) -> str:
    """如果 SQL 缺少 LIMIT 子句，自动添加。
    
    防止返回过大的结果集导致性能问题。
    
    Args:
        sql: SQL 语句
        limit: 默认限制行数
        
    Returns:
        添加 LIMIT 后的 SQL
    """
    if not sql or not sql.strip():
        return sql
    
    sql_upper = sql.upper()
    
    # 检查是否已有 LIMIT
    if "LIMIT" not in sql_upper:
        sql = re.sub(r';\s*--[^\n]*$', '', sql).rstrip()
        sql = sql.rstrip(';').rstrip()
        return f"{sql} LIMIT {limit}"
    
    return sql


def sanitize_sql(sql: str, auto_limit: bool = True, limit: int = DEFAULT_LIMIT) -> Tuple[str, bool, Optional[str]]:
    """综合处理 SQL 语句：安全检查 + 自动添加 LIMIT。
    
    Args:
        sql: 原始 SQL 语句
        auto_limit: 是否自动添加 LIMIT
        limit: 默认限制行数
        
    Returns:
        (processed_sql, is_safe, error_message) 元组
        - processed_sql: 处理后的 SQL（如果安全）
        - is_safe: 是否安全
        - error_message: 错误描述（如果不安全）
    """
    # 安全检查
    is_safe, error = check_sql_safety(sql)
    
    if not is_safe:
        return (sql, False, error)
    
    # 自动添加 LIMIT
    if auto_limit:
        sql = add_limit_if_missing(sql, limit)
    
    return (sql, True, None)


# ==================== 导出 ====================

__all__ = [
    "check_sql_safety",
    "check_dangerous_keywords",
    "check_sensitive_tables",
    "check_schema_whitelist",
    "check_multiple_statements",
    "add_limit_if_missing",
    "sanitize_sql",
    "get_sensitive_tables",
    "get_system_schemas",
    "get_analytics_schema_allowlist",
    "DANGEROUS_KEYWORDS",
    "DEFAULT_SENSITIVE_TABLES",
    "DEFAULT_SYSTEM_SCHEMAS",
    "ALLOWED_METADATA_VIEWS",
    "DEFAULT_LIMIT",
]
