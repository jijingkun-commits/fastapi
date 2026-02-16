"""SQL 权限重写器（中文注释）。

基于用户权限上下文重写 SQL：
1. 表级检查：拒绝访问未授权的表
2. 行级过滤：自动注入 WHERE 条件（RLS）
3. 列级脱敏：替换敏感列为脱敏表达式

参考 Vanna 的 transform_args 模式实现。
"""
import re
import logging
from typing import Tuple, Optional, List, Dict

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.ai.utils.permission_context import UserPermissionContext
from app.services.permission_service import get_permission_service

logger = logging.getLogger(__name__)


def _escape_sql_value(value: str) -> str:
    """转义 SQL 值，防止注入。
    
    Args:
        value: 原始值
        
    Returns:
        转义后的值
    """
    if value is None:
        return ""
    # 转义单引号和反斜杠
    return value.replace("\\", "\\\\").replace("'", "''")


def rewrite_sql_with_permissions(
    sql: str,
    user_context: UserPermissionContext
) -> Tuple[str, bool, Optional[str]]:
    """根据用户权限重写 SQL。
    
    执行流程：
    1. 检查表级权限（拒绝未授权表）
    2. 注入行级过滤条件（WHERE）
    3. 替换敏感列为脱敏表达式
    
    Args:
        sql: 原始 SQL 语句
        user_context: 用户权限上下文
        
    Returns:
        (rewritten_sql, is_allowed, error_message) 元组
        - rewritten_sql: 重写后的 SQL（如果允许）
        - is_allowed: 是否允许执行
        - error_message: 错误描述（如果不允许）
    """
    if not sql or not sql.strip():
        return (sql, False, "SQL 语句为空")
    
    sql = sql.strip()

    service = get_permission_service()
    context_allowed, context_error = service.validate_query_context(user_context)
    if not context_allowed:
        logger.warning(
            "SQL 权限上下文拒绝: user_id=%s, data_role=%s, reason=%s",
            user_context.user_id,
            user_context.data_role,
            context_error,
        )
        return (sql, False, context_error)

    try:
        # 1. 提取并检查表级权限
        tables = _extract_tables_with_schema(sql)
        
        allowed, error = _check_table_permissions(tables, user_context)
        if not allowed:
            return (sql, False, error)
        
        # 2. 注入行级过滤条件
        rewritten_sql = _inject_row_filters(sql, tables, user_context)
        
        # 3. 处理列级脱敏
        rewritten_sql = _apply_column_masking(rewritten_sql, tables, user_context)
        
        logger.info(f"SQL 权限重写完成: 表={len(tables)}, 原始长度={len(sql)}, 重写后={len(rewritten_sql)}")
        
        return (rewritten_sql, True, None)
        
    except ParseError as e:
        logger.warning(f"SQL 解析失败，跳过权限重写: {e}")
        # 解析失败时，仍然检查基本的表权限
        return _fallback_permission_check(sql, user_context)
    except Exception as e:
        logger.error(f"SQL 权限重写异常: {e}", exc_info=True)
        return (sql, False, f"权限检查失败: {str(e)}")


def _extract_tables_with_schema(sql: str) -> List[Tuple[str, str]]:
    """提取 SQL 中的表名（含 Schema）。
    
    Args:
        sql: SQL 语句
        
    Returns:
        [(schema, table), ...] 列表
    """
    tables = []
    
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
        
        for table in parsed.find_all(exp.Table):
            schema = table.db or "public"
            table_name = table.name
            if table_name:
                tables.append((schema.lower(), table_name.lower()))
                
    except ParseError:
        tables = _extract_tables_regex(sql)
    
    return list(set(tables))


def _extract_tables_regex(sql: str) -> List[Tuple[str, str]]:
    """正则提取表名（降级方案）。"""
    tables = []
    
    # 匹配 schema.table 或 table
    pattern = r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)'
    
    for match in re.finditer(pattern, sql, re.IGNORECASE):
        full_name = match.group(1)
        if "." in full_name:
            schema, table = full_name.split(".", 1)
        else:
            schema, table = "public", full_name
        tables.append((schema.lower(), table.lower()))
    
    return tables


def _check_table_permissions(
    tables: List[Tuple[str, str]], 
    user_context: UserPermissionContext
) -> Tuple[bool, Optional[str]]:
    """检查所有表的访问权限。
    
    Args:
        tables: [(schema, table), ...] 列表
        user_context: 用户权限上下文
        
    Returns:
        (allowed, error_message)
    """
    service = get_permission_service()
    
    for schema, table in tables:
        allowed, error = service.check_table_access(user_context, schema, table)
        if not allowed:
            logger.warning(f"表访问被拒绝: user_id={user_context.user_id}, "
                         f"data_role={user_context.data_role}, table={schema}.{table}")
            return (False, error)
    
    return (True, None)


def _inject_row_filters(
    sql: str, 
    tables: List[Tuple[str, str]], 
    user_context: UserPermissionContext
) -> str:
    """注入行级过滤条件（RLS）。
    
    Args:
        sql: 原始 SQL
        tables: 表列表
        user_context: 用户权限上下文
        
    Returns:
        注入过滤条件后的 SQL
    """
    service = get_permission_service()
    
    # 收集所有过滤条件
    all_filters: List[str] = []
    
    for schema, table in tables:
        filters = service.get_row_filters_for_table(user_context, schema, table)
        
        for column, operator, value in filters:
            # 转义值，防止 SQL 注入
            escaped_value = _escape_sql_value(value)
            
            # 构建过滤条件
            if operator.upper() == "IN":
                # IN 操作符：值应该是逗号分隔的列表
                values = [f"'{_escape_sql_value(v.strip())}'" for v in value.split(",")]
                condition = f"{table}.{column} IN ({', '.join(values)})"
            elif operator.upper() == "LIKE":
                condition = f"{table}.{column} LIKE '{escaped_value}'"
            else:
                # 默认 = 操作符
                condition = f"{table}.{column} = '{escaped_value}'"
            
            all_filters.append(condition)

    deduped_filters = list(dict.fromkeys(all_filters))

    if not deduped_filters:
        return sql
    
    # 注入 WHERE 条件
    filter_clause = " AND ".join(deduped_filters)
    
    # 使用 sqlglot 注入（更安全）
    try:
        return _inject_where_clause_sqlglot(sql, filter_clause)
    except Exception as e:
        logger.warning(f"sqlglot 注入失败，使用正则注入: {e}")
        return _inject_where_clause_regex(sql, filter_clause)


def _inject_where_clause_sqlglot(sql: str, filter_clause: str) -> str:
    """使用 sqlglot 注入 WHERE 条件。"""
    parsed = sqlglot.parse_one(sql, dialect="postgres")
    
    # 查找现有的 WHERE 子句
    where = parsed.find(exp.Where)
    
    if where:
        # 已有 WHERE，添加 AND 条件
        new_condition = sqlglot.parse_one(filter_clause)
        where.this = exp.And(this=where.this, expression=new_condition)
    else:
        # 没有 WHERE，添加新的
        # 找到 FROM 子句后插入
        new_where = exp.Where(this=sqlglot.parse_one(filter_clause))
        
        # 简化处理：直接在 SQL 文本中插入
        # sqlglot 的 AST 操作较复杂，这里使用文本方式
        return _inject_where_clause_regex(sql, filter_clause)
    
    return parsed.sql(dialect="postgres")


def _inject_where_clause_regex(sql: str, filter_clause: str) -> str:
    """使用正则注入 WHERE 条件（降级方案）。"""
    sql_upper = sql.upper()
    
    # 检查是否已有 WHERE
    where_match = re.search(r'\bWHERE\b', sql_upper)
    
    if where_match:
        # 在 WHERE 后插入条件
        where_pos = where_match.end()
        return f"{sql[:where_pos]} ({filter_clause}) AND {sql[where_pos:]}"
    else:
        # 查找插入位置（在 GROUP BY / ORDER BY / LIMIT 之前）
        insert_patterns = [
            r'\bGROUP\s+BY\b',
            r'\bORDER\s+BY\b',
            r'\bLIMIT\b',
            r'\bHAVING\b',
            r';?\s*$'
        ]
        
        for pattern in insert_patterns:
            match = re.search(pattern, sql_upper)
            if match:
                insert_pos = match.start()
                return f"{sql[:insert_pos]} WHERE {filter_clause} {sql[insert_pos:]}"
        
        # 默认追加到末尾
        sql = sql.rstrip().rstrip(";")
        return f"{sql} WHERE {filter_clause}"


def _apply_column_masking(
    sql: str, 
    tables: List[Tuple[str, str]], 
    user_context: UserPermissionContext
) -> str:
    """应用列级脱敏。
    
    Args:
        sql: SQL 语句
        tables: 表列表
        user_context: 用户权限上下文
        
    Returns:
        脱敏处理后的 SQL
    """
    service = get_permission_service()
    
    # 收集所有需要脱敏的列
    columns_to_mask: Dict[str, str] = {}  # {column_name: mask_type}
    
    for schema, table in tables:
        masked = service.get_masked_columns_for_table(user_context, schema, table)
        columns_to_mask.update(masked)
    
    if not columns_to_mask:
        return sql
    
    # 替换 SELECT 中的敏感列
    for column, mask_type in columns_to_mask.items():
        mask_expr = _get_mask_expression(column, mask_type)
        
        # 替换列引用（简化实现，支持基本场景）
        # 匹配 column 或 table.column
        patterns = [
            (rf'\b{column}\b(?!\s*=)', mask_expr),  # 避免替换 WHERE 中的 column = 'xxx'
            (rf'(\w+\.){column}\b(?!\s*=)', rf'\1{mask_expr}'),
        ]
        
        for pattern, replacement in patterns:
            # 只替换 SELECT 部分
            select_end = sql.upper().find("FROM")
            if select_end > 0:
                select_part = sql[:select_end]
                rest_part = sql[select_end:]
                
                # 在 SELECT 部分进行替换
                new_select = re.sub(pattern, replacement, select_part, flags=re.IGNORECASE)
                sql = new_select + rest_part
    
    return sql


def _get_mask_expression(column: str, mask_type: str) -> str:
    """生成脱敏表达式。
    
    Args:
        column: 列名
        mask_type: 脱敏类型 (hide / partial / hash)
        
    Returns:
        SQL 脱敏表达式
    """
    if mask_type == "hide":
        return "'***'"
    elif mask_type == "partial":
        # 部分脱敏：显示前3位和后4位，中间用 **** 替代
        return f"CONCAT(LEFT({column}, 3), '****', RIGHT({column}, 4))"
    elif mask_type == "hash":
        # 哈希脱敏：返回 MD5 前8位
        return f"LEFT(MD5({column}::text), 8)"
    else:
        # 默认隐藏
        return "'***'"


def _fallback_permission_check(
    sql: str, 
    user_context: UserPermissionContext
) -> Tuple[str, bool, Optional[str]]:
    """降级权限检查（SQL 解析失败时）。
    
    使用简单正则提取表名进行检查。
    """
    tables = _extract_tables_regex(sql)
    
    allowed, error = _check_table_permissions(tables, user_context)
    if not allowed:
        return (sql, False, error)
    
    # 解析失败时不进行重写，但仍允许执行
    logger.warning("SQL 解析失败，跳过行级/列级权限处理")
    return (sql, True, None)


# ==================== 便捷函数 ====================

def check_and_rewrite_sql(
    sql: str, 
    user_id: int
) -> Tuple[str, bool, Optional[str]]:
    """便捷函数：检查并重写 SQL。
    
    自动获取用户权限上下文并进行权限重写。
    
    Args:
        sql: 原始 SQL
        user_id: 用户 ID
        
    Returns:
        (rewritten_sql, is_allowed, error_message)
    """
    from app.services.permission_service import get_user_permission_context
    
    user_context = get_user_permission_context(user_id)
    return rewrite_sql_with_permissions(sql, user_context)


__all__ = [
    "rewrite_sql_with_permissions",
    "check_and_rewrite_sql",
]
