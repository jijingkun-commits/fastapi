"""数据查询错误处理模块（中文注释）。

提供友好的错误提示和智能建议：
1. 错误分类（可恢复/不可恢复）
2. 用户友好的错误消息
3. 智能建议（下一步操作）

使用方式：
    from app.ai.utils.error_handler import format_error_message, get_error_suggestions
    
    msg, suggestions = format_error_message(error_str, context)
    print(msg)  # "无法找到表 'orders'..."
    print(suggestions)  # ["请检查表名是否正确", "可用的表：..."]
"""
import logging
import re
from typing import List, Tuple, Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """错误分类。"""
    TABLE_NOT_FOUND = "table_not_found"
    COLUMN_NOT_FOUND = "column_not_found"
    SYNTAX_ERROR = "syntax_error"
    TYPE_MISMATCH = "type_mismatch"
    PERMISSION_DENIED = "permission_denied"
    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"
    RESULT_TOO_LARGE = "result_too_large"
    UNSAFE_QUERY = "unsafe_query"
    UNKNOWN = "unknown"


# 错误模式匹配规则
ERROR_PATTERNS = {
    ErrorCategory.TABLE_NOT_FOUND: [
        (r'relation "([^"]+)" does not exist', "表 '{0}' 不存在"),
        (r'table "([^"]+)" does not exist', "表 '{0}' 不存在"),
        (r"relation '([^']+)' does not exist", "表 '{0}' 不存在"),
        (r'unknown table[:\s]*([^\s,]+)', "表 '{0}' 未找到"),
    ],
    ErrorCategory.COLUMN_NOT_FOUND: [
        (r'column "([^"]+)" does not exist', "列 '{0}' 不存在"),
        (r'column "([^"]+)" of relation "([^"]+)" does not exist', "表 '{1}' 中没有列 '{0}'"),
        (r'unknown column[:\s]*([^\s,]+)', "列 '{0}' 未找到"),
    ],
    ErrorCategory.SYNTAX_ERROR: [
        (r'syntax error at or near "([^"]+)"', "SQL 语法错误（在 '{0}' 附近）"),
        (r'syntax error', "SQL 语法错误"),
        (r'unterminated quoted string', "字符串引号未闭合"),
        (r'missing (FROM|WHERE|SELECT)', "缺少 {0} 子句"),
    ],
    ErrorCategory.TYPE_MISMATCH: [
        (r'cannot cast type ([^\s]+) to ([^\s]+)', "类型转换错误：无法将 {0} 转换为 {1}"),
        (r'invalid input syntax for type ([^\s:]+)', "数据格式错误：不是有效的 {0} 类型"),
        (r'operator does not exist: ([^\s]+) ([^\s]+) ([^\s]+)', "类型不匹配：{0} 和 {2} 不能进行 {1} 运算"),
    ],
    ErrorCategory.PERMISSION_DENIED: [
        (r'permission denied for (table|schema|relation) ([^\s]+)', "权限不足：无法访问 {0} '{1}'"),
        (r'access denied', "访问被拒绝"),
    ],
    ErrorCategory.CONNECTION_ERROR: [
        (r'connection refused', "数据库连接被拒绝"),
        (r'could not connect', "无法连接数据库"),
        (r'connection reset', "数据库连接已断开"),
    ],
    ErrorCategory.TIMEOUT: [
        (r'statement timeout', "查询超时"),
        (r'query timeout', "查询超时"),
        (r'canceling statement due to statement timeout', "查询执行时间过长，已被取消"),
    ],
    ErrorCategory.RESULT_TOO_LARGE: [
        (r'out of memory', "结果数据量过大"),
        (r'result set too large', "返回结果过多"),
    ],
}


# 错误类别对应的用户友好消息模板
USER_FRIENDLY_MESSAGES = {
    ErrorCategory.TABLE_NOT_FOUND: "🔍 **找不到数据表**\n\n{detail}\n\n可能的原因：\n- 表名拼写错误\n- 表不存在或已被删除\n- 缺少 schema 前缀",
    ErrorCategory.COLUMN_NOT_FOUND: "🔍 **找不到数据列**\n\n{detail}\n\n可能的原因：\n- 列名拼写错误\n- 该列已被移除或重命名",
    ErrorCategory.SYNTAX_ERROR: "⚠️ **SQL 语法错误**\n\n{detail}\n\n系统将尝试自动修正...",
    ErrorCategory.TYPE_MISMATCH: "⚠️ **数据类型不匹配**\n\n{detail}\n\n请检查筛选条件中的值是否与列类型一致。",
    ErrorCategory.PERMISSION_DENIED: "🔒 **权限不足**\n\n{detail}\n\n请联系管理员获取访问权限。",
    ErrorCategory.CONNECTION_ERROR: "🔌 **数据库连接问题**\n\n{detail}\n\n请稍后重试，如问题持续请联系技术支持。",
    ErrorCategory.TIMEOUT: "⏱️ **查询超时**\n\n{detail}\n\n建议：\n- 添加更多筛选条件\n- 缩小查询时间范围\n- 减少返回的数据量",
    ErrorCategory.RESULT_TOO_LARGE: "📊 **数据量过大**\n\n{detail}\n\n建议添加筛选条件或使用聚合查询。",
    ErrorCategory.UNSAFE_QUERY: "🛡️ **查询被安全策略拦截**\n\n{detail}",
    ErrorCategory.UNKNOWN: "❌ **查询执行失败**\n\n{detail}",
}


# 错误类别对应的建议
ERROR_SUGGESTIONS = {
    ErrorCategory.TABLE_NOT_FOUND: [
        "检查表名是否正确",
        "尝试添加 schema 前缀（如 fdmdata.表名）",
        "查看可用的数据表列表",
    ],
    ErrorCategory.COLUMN_NOT_FOUND: [
        "检查列名拼写是否正确",
        "确认该列是否存在于目标表中",
        "查看表的完整列信息",
    ],
    ErrorCategory.SYNTAX_ERROR: [
        "系统正在自动尝试修正 SQL",
        "如多次失败，请尝试简化查询条件",
    ],
    ErrorCategory.TYPE_MISMATCH: [
        "检查筛选条件中的值类型",
        "日期字段请使用 'YYYY-MM-DD' 格式",
        "数值字段不要加引号",
    ],
    ErrorCategory.PERMISSION_DENIED: [
        "联系数据管理员申请权限",
        "尝试查询其他已授权的数据表",
    ],
    ErrorCategory.CONNECTION_ERROR: [
        "请稍后重试",
        "如问题持续，请联系技术支持",
    ],
    ErrorCategory.TIMEOUT: [
        "添加时间范围筛选（如最近7天）",
        "减少返回的列数量",
        "使用 GROUP BY 进行聚合",
    ],
    ErrorCategory.RESULT_TOO_LARGE: [
        "添加 LIMIT 限制返回行数",
        "增加筛选条件缩小范围",
        "考虑使用聚合统计",
    ],
    ErrorCategory.UNSAFE_QUERY: [
        "只支持 SELECT 查询",
        "不能访问系统表或敏感数据",
    ],
    ErrorCategory.UNKNOWN: [
        "请尝试重新描述您的问题",
        "如问题持续，请联系技术支持",
    ],
}


def classify_error(error_str: str) -> Tuple[ErrorCategory, str, List[str]]:
    """分类错误并提取详细信息。
    
    Args:
        error_str: 原始错误字符串
        
    Returns:
        (错误类别, 格式化的详细信息, 匹配到的值列表)
    """
    error_lower = error_str.lower()
    
    for category, patterns in ERROR_PATTERNS.items():
        for pattern, template in patterns:
            match = re.search(pattern, error_str, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    detail = template.format(*groups) if groups else template
                except (IndexError, KeyError):
                    detail = template
                return category, detail, list(groups)
    
    # 未匹配到具体模式，尝试通用分类
    if "permission" in error_lower or "denied" in error_lower:
        return ErrorCategory.PERMISSION_DENIED, error_str, []
    if "timeout" in error_lower:
        return ErrorCategory.TIMEOUT, error_str, []
    if "connection" in error_lower:
        return ErrorCategory.CONNECTION_ERROR, error_str, []
    
    return ErrorCategory.UNKNOWN, error_str, []


def format_error_message(
    error_str: str,
    context: Optional[Dict] = None,
    include_raw: bool = False
) -> str:
    """格式化用户友好的错误消息。
    
    Args:
        error_str: 原始错误字符串
        context: 上下文信息（如可用表列表）
        include_raw: 是否包含原始错误信息
        
    Returns:
        用户友好的错误消息
    """
    category, detail, matched_values = classify_error(error_str)
    
    # 获取模板
    template = USER_FRIENDLY_MESSAGES.get(category, USER_FRIENDLY_MESSAGES[ErrorCategory.UNKNOWN])
    message = template.format(detail=detail)
    
    # 添加上下文信息
    if context:
        if category == ErrorCategory.TABLE_NOT_FOUND and context.get("available_tables"):
            tables = context["available_tables"][:5]
            message += f"\n\n可用的数据表：\n- " + "\n- ".join(tables)
            if len(context["available_tables"]) > 5:
                message += f"\n- ...（共 {len(context['available_tables'])} 张表）"
        
        if category == ErrorCategory.COLUMN_NOT_FOUND and context.get("available_columns"):
            cols = context["available_columns"][:10]
            message += f"\n\n该表的可用列：\n- " + "\n- ".join(cols)
    
    # 添加原始错误（调试用）
    if include_raw:
        message += f"\n\n<details>\n<summary>技术详情</summary>\n\n```\n{error_str}\n```\n</details>"
    
    return message


def get_error_suggestions(error_str: str, iterations: int = 1) -> List[str]:
    """获取错误处理建议。
    
    Args:
        error_str: 错误字符串
        iterations: 当前重试次数
        
    Returns:
        建议列表
    """
    category, _, _ = classify_error(error_str)
    
    suggestions = ERROR_SUGGESTIONS.get(category, ERROR_SUGGESTIONS[ErrorCategory.UNKNOWN]).copy()
    
    # 根据重试次数调整建议
    if iterations >= 2:
        suggestions.insert(0, "已多次尝试自动修正")
        suggestions.append("建议尝试换一种方式描述问题")
    
    if iterations >= 3:
        suggestions.insert(0, "⚠️ 已达最大重试次数")
    
    return suggestions


def is_recoverable(error_str: str) -> bool:
    """判断错误是否可以通过重试恢复。
    
    Args:
        error_str: 错误字符串
        
    Returns:
        是否可恢复
    """
    category, _, _ = classify_error(error_str)
    
    # 可恢复的错误类别
    recoverable = {
        ErrorCategory.TABLE_NOT_FOUND,
        ErrorCategory.COLUMN_NOT_FOUND,
        ErrorCategory.SYNTAX_ERROR,
        ErrorCategory.TYPE_MISMATCH,
    }
    
    # 不可恢复的错误类别
    unrecoverable = {
        ErrorCategory.PERMISSION_DENIED,
        ErrorCategory.CONNECTION_ERROR,
    }
    
    if category in recoverable:
        return True
    if category in unrecoverable:
        return False
    
    # 其他情况保守处理
    return False


def format_retry_message(iterations: int, max_iterations: int = 3) -> str:
    """格式化重试状态消息。
    
    Args:
        iterations: 当前迭代次数
        max_iterations: 最大迭代次数
        
    Returns:
        状态消息
    """
    if iterations < max_iterations:
        return f"🔄 正在重新生成 SQL（第 {iterations + 1}/{max_iterations} 次尝试）..."
    else:
        return f"⚠️ 已尝试 {iterations} 次，仍无法生成正确的 SQL"


def build_final_error_message(
    error_str: str,
    iterations: int,
    sql: str = None,
    context: Optional[Dict] = None
) -> str:
    """构建最终的错误消息（用于达到最大重试次数或不可恢复错误）。
    
    Args:
        error_str: 错误字符串
        iterations: 尝试次数
        sql: 最后尝试的 SQL
        context: 上下文信息
        
    Returns:
        完整的错误消息
    """
    # 格式化主消息
    message = format_error_message(error_str, context)
    
    # 添加尝试次数信息
    if iterations > 1:
        message += f"\n\n---\n📊 **尝试统计**: 共尝试 {iterations} 次自动修正"
    
    # 添加建议
    suggestions = get_error_suggestions(error_str, iterations)
    if suggestions:
        message += "\n\n💡 **建议**:\n"
        for i, sug in enumerate(suggestions, 1):
            message += f"{i}. {sug}\n"
    
    return message
