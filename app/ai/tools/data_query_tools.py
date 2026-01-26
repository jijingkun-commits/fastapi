"""问数工具：基于 Vanna 的语义查询工具（中文注释）。

提供自然语言到 SQL 的转换和执行功能。
"""
import logging
from typing import Optional, Dict, Any, List
import json

from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig

from app.ai.semantic import get_vanna
from app.ai.workflow.data_intent_helpers import (
    match_metric,
    parse_time_range,
    extract_dimensions,
    check_sql_safety,
    add_limit_if_missing
)
from app.db.session import get_analytics_db_context

logger = logging.getLogger(__name__)


@tool
def semantic_query(
    question: str,
    config: Optional[RunnableConfig] = None
) -> str:
    """基于自然语言的数据查询工具。
    
    使用 Vanna RAG 将自然语言问题转换为 SQL 并执行。
    支持预定义指标匹配和自由查询。
    
    Args:
        question: 自然语言查询问题，如"本月销售额是多少"
        
    Returns:
        查询结果的自然语言描述和数据
    """
    logger.info(f"语义查询: {question}")
    
    try:
        vanna = get_vanna()
        
        # 尝试匹配预定义指标
        metric_name = match_metric(question)
        if metric_name:
            logger.info(f"匹配到预定义指标: {metric_name}")
        
        # 解析时间范围
        time_type, time_text = parse_time_range(question)
        if time_type:
            logger.info(f"识别到时间范围: {time_type} ({time_text})")
        
        # 提取维度
        dimensions = extract_dimensions(question)
        if dimensions:
            logger.info(f"识别到维度: {dimensions}")
        
        # 生成 SQL
        sql = vanna.generate_sql(question)
        
        if not sql:
            return "无法理解您的查询需求，请尝试更具体的描述。"
        
        # 安全检查
        is_safe, error_msg = check_sql_safety(sql)
        if not is_safe:
            logger.warning(f"SQL 安全检查失败: {error_msg}")
            return f"查询被拒绝：{error_msg}"
        
        # 自动添加 LIMIT
        sql = add_limit_if_missing(sql)
        
        logger.info(f"生成 SQL: {sql[:100]}...")
        
        # 执行 SQL
        df = vanna.run_sql(sql)
        
        # 格式化结果
        if df is None or df.empty:
            return f"查询完成，没有找到符合条件的数据。\n\n执行的 SQL：\n```sql\n{sql}\n```"
        
        # 转换为可读格式
        row_count = len(df)
        if row_count == 1 and len(df.columns) <= 3:
            # 单行少列结果，直接展示值
            values = ", ".join([f"{col}: {df.iloc[0][col]}" for col in df.columns])
            result_text = f"查询结果：{values}"
        else:
            # 多行结果，展示表格
            result_text = f"查询返回 {row_count} 条记录：\n\n"
            result_text += df.head(10).to_markdown(index=False)
            if row_count > 10:
                result_text += f"\n\n... 共 {row_count} 条记录"
        
        result_text += f"\n\n执行的 SQL：\n```sql\n{sql}\n```"
        
        return result_text
        
    except Exception as e:
        logger.exception(f"语义查询失败: {e}")
        return f"查询执行失败: {str(e)}"


@tool
def execute_sql(
    sql: str,
    config: Optional[RunnableConfig] = None
) -> str:
    """执行 SQL 查询（仅限 SELECT 语句）。
    
    在 Analytics DB 上执行只读 SQL 查询。
    
    Args:
        sql: SQL 查询语句（必须是 SELECT）
        
    Returns:
        查询结果
    """
    logger.info(f"执行 SQL: {sql[:100]}...")
    
    # 安全检查
    is_safe, error_msg = check_sql_safety(sql)
    if not is_safe:
        return f"SQL 被拒绝：{error_msg}"
    
    # 添加 LIMIT
    sql = add_limit_if_missing(sql)
    
    try:
        vanna = get_vanna()
        df = vanna.run_sql(sql)
        
        if df is None or df.empty:
            return "查询完成，没有返回数据。"
        
        row_count = len(df)
        result = df.head(20).to_markdown(index=False)
        
        if row_count > 20:
            result += f"\n\n... 共 {row_count} 条记录（仅显示前 20 条）"
        
        return result
        
    except Exception as e:
        logger.exception(f"SQL 执行失败: {e}")
        return f"执行失败: {str(e)}"


# 导出工具列表
DATA_QUERY_TOOLS = [semantic_query, execute_sql]
