"""SQL 解析工具（中文注释）。

使用 sqlglot 提供统一的 SQL 解析功能：
- 表名提取
- SQL 语法验证
- SQL 规范化

统一替代分散在各处的正则解析逻辑。
"""
import logging
from typing import List, Set, Optional, Tuple
import re

logger = logging.getLogger(__name__)

# 尝试导入 sqlglot，如果不可用则降级到正则
try:
    import sqlglot
    from sqlglot import exp
    from sqlglot.errors import ParseError
    SQLGLOT_AVAILABLE = True
except ImportError:
    logger.warning("sqlglot 未安装，将使用正则表达式作为降级方案")
    SQLGLOT_AVAILABLE = False


def extract_tables_from_sql(sql: str, dialect: str = "postgres") -> Set[str]:
    """从 SQL 语句中提取所有引用的表名。
    
    使用 sqlglot 进行 AST 解析，比正则更准确可靠。
    
    Args:
        sql: SQL 语句
        dialect: SQL 方言，默认 postgres
        
    Returns:
        表名集合（小写，包含 schema 前缀如果有的话）
        
    Examples:
        >>> extract_tables_from_sql("SELECT * FROM users JOIN orders ON ...")
        {'users', 'orders'}
        >>> extract_tables_from_sql("SELECT * FROM public.users")
        {'public.users'}
    """
    if not sql or not sql.strip():
        return set()
    
    if SQLGLOT_AVAILABLE:
        return _extract_tables_sqlglot(sql, dialect)
    else:
        return _extract_tables_regex(sql)


def _extract_tables_sqlglot(sql: str, dialect: str = "postgres") -> Set[str]:
    """使用 sqlglot 提取表名。"""
    tables = set()
    
    try:
        # 解析 SQL
        parsed = sqlglot.parse(sql, dialect=dialect)
        
        for statement in parsed:
            if statement is None:
                continue
            
            # 遍历所有 Table 节点
            for table in statement.find_all(exp.Table):
                table_name = table.name
                
                # 处理 schema 前缀
                if table.db:
                    table_name = f"{table.db}.{table_name}"
                elif table.catalog:
                    table_name = f"{table.catalog}.{table_name}"
                
                if table_name:
                    tables.add(table_name.lower())
        
        logger.debug(f"sqlglot 解析提取到表: {tables}")
        return tables
        
    except ParseError as e:
        logger.warning(f"sqlglot 解析失败，降级到正则: {e}")
        return _extract_tables_regex(sql)
    except Exception as e:
        logger.exception(f"表名提取异常: {e}")
        return _extract_tables_regex(sql)


def _extract_tables_regex(sql: str) -> Set[str]:
    """降级方案：使用正则提取表名。
    
    注意：正则方案可能不够准确，可能被特殊构造的 SQL 绕过。
    """
    tables = set()
    
    # 匹配 FROM/JOIN/INTO/UPDATE 后的表名
    # 支持 schema.table 格式
    patterns = [
        r'(?:FROM|JOIN)\s+(?:LATERAL\s+)?([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
        r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
        r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, sql, re.IGNORECASE)
        for match in matches:
            # 过滤 SQL 关键词（可能被误匹配）
            if match.upper() not in {'SELECT', 'WHERE', 'AND', 'OR', 'ON', 'AS', 'SET', 'VALUES'}:
                tables.add(match.lower())
    
    logger.debug(f"正则解析提取到表: {tables}")
    return tables


def validate_sql_syntax(sql: str, dialect: str = "postgres") -> Tuple[bool, Optional[str]]:
    """验证 SQL 语法是否正确。
    
    Args:
        sql: SQL 语句
        dialect: SQL 方言
        
    Returns:
        (is_valid, error_message) 元组
    """
    if not sql or not sql.strip():
        return (False, "SQL 语句为空")
    
    if not SQLGLOT_AVAILABLE:
        # 如果 sqlglot 不可用，跳过语法验证
        return (True, None)
    
    try:
        parsed = sqlglot.parse(sql, dialect=dialect)
        
        # 检查是否解析成功
        if not parsed or all(p is None for p in parsed):
            return (False, "无法解析 SQL 语句")
        
        return (True, None)
        
    except ParseError as e:
        return (False, f"SQL 语法错误: {str(e)}")
    except Exception as e:
        logger.exception(f"SQL 验证异常: {e}")
        return (False, f"SQL 验证失败: {str(e)}")


def normalize_sql(sql: str, dialect: str = "postgres") -> str:
    """规范化 SQL 语句（格式化）。
    
    Args:
        sql: SQL 语句
        dialect: SQL 方言
        
    Returns:
        格式化后的 SQL
    """
    if not sql or not sql.strip():
        return sql
    
    if not SQLGLOT_AVAILABLE:
        # 简单清理空白
        return " ".join(sql.split())
    
    try:
        # 使用 sqlglot 格式化
        return sqlglot.transpile(sql, read=dialect, write=dialect, pretty=True)[0]
    except Exception as e:
        logger.warning(f"SQL 格式化失败: {e}")
        # 降级到简单清理
        return " ".join(sql.split())


def is_select_only(sql: str) -> bool:
    """检查 SQL 是否只包含 SELECT 语句（只读）。
    
    Args:
        sql: SQL 语句
        
    Returns:
        是否为只读查询
    """
    if not sql or not sql.strip():
        return False
    
    sql_upper = sql.strip().upper()
    
    # 快速检查：必须以 SELECT 或 WITH 开头
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False
    
    # 检查是否包含修改语句关键词
    dangerous_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", 
        "ALTER", "CREATE", "GRANT", "REVOKE", "EXECUTE"
    ]
    
    for keyword in dangerous_keywords:
        # 使用词边界匹配
        if re.search(rf'\b{keyword}\b', sql_upper):
            return False
    
    return True


def get_query_type(sql: str) -> str:
    """获取 SQL 语句类型。
    
    Args:
        sql: SQL 语句
        
    Returns:
        语句类型: 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DDL', 'UNKNOWN'
    """
    if not sql or not sql.strip():
        return "UNKNOWN"
    
    sql_upper = sql.strip().upper()
    
    if sql_upper.startswith("SELECT") or sql_upper.startswith("WITH"):
        return "SELECT"
    elif sql_upper.startswith("INSERT"):
        return "INSERT"
    elif sql_upper.startswith("UPDATE"):
        return "UPDATE"
    elif sql_upper.startswith("DELETE"):
        return "DELETE"
    elif any(sql_upper.startswith(kw) for kw in ["CREATE", "ALTER", "DROP", "TRUNCATE"]):
        return "DDL"
    else:
        return "UNKNOWN"


# 导出
__all__ = [
    "extract_tables_from_sql",
    "validate_sql_syntax",
    "normalize_sql",
    "is_select_only",
    "get_query_type",
    "SQLGLOT_AVAILABLE",
]
