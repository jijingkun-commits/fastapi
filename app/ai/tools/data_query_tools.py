"""问数工具：两层漏斗查询策略（中文注释）。

实现逻辑：
1. 第一层：匹配预定义指标 → 使用 sql_template
2. 第二层：无匹配 → AI 自由生成 SQL

包含表可用性检查和缺表友好提示。
"""
import logging
from typing import Optional
from datetime import date

from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig

from app.services.metric_service import get_metric_service
from app.ai.utils.sql_safety import check_sql_safety, add_limit_if_missing


logger = logging.getLogger(__name__)


@tool
def semantic_query(
    question: str,
    config: Optional[RunnableConfig] = None
) -> str:
    """基于自然语言的数据查询工具。
    
    两层漏斗策略：
    1. 优先匹配预定义指标，使用 sql_template
    2. 无匹配时，使用 AI 生成 SQL
    
    Args:
        question: 自然语言查询问题，如"本月存款余额是多少"
        
    Returns:
        查询结果的自然语言描述和数据
    """
    logger.info(f"语义查询: {question}")
    
    metric_service = get_metric_service()
    
    # ========== 第一层：指标匹配 ==========
    metric = metric_service.match_metric(question)
    
    if metric and metric.sql_template:
        logger.info(f"匹配到指标: {metric.metric_name} ({metric.metric_id})")
        
        # 检查表可用性
        all_available, missing = metric_service.check_tables_availability(metric.sql_template)
        
        if not all_available:
            missing_str = ", ".join(missing)
            logger.warning(f"指标 {metric.metric_id} 缺少表: {missing_str}")
            return (
                f"⚠️ 指标「{metric.metric_name}」暂不可用\n\n"
                f"**原因**：缺少以下数据表：\n"
                f"- {chr(10).join('`' + t + '`' for t in missing)}\n\n"
                f"请联系数据管理员导入相关数据表后重试。"
            )
        
        # 准备 SQL（替换参数）
        today = date.today().isoformat()
        sql = metric_service.prepare_sql(
            metric.sql_template, 
            {"data_dt": today, "date": today}
        )
        
        # 安全检查
        is_safe, error_msg = check_sql_safety(sql)
        if not is_safe:
            logger.warning(f"SQL 安全检查失败: {error_msg}")
            return f"查询被拒绝：{error_msg}"
        
        # 添加 LIMIT
        sql = add_limit_if_missing(sql)
        
        # 执行 SQL
        return _execute_and_format(sql, metric.metric_name, metric.unit)
    
    # ========== 第二层：AI 自由生成 ==========
    logger.info("未匹配到指标，使用 AI 生成 SQL")
    
    try:
        from app.ai.semantic import get_vanna
        vanna = get_vanna()
        
        # 生成 SQL
        sql = vanna.generate_sql(question)
        
        if not sql:
            return "无法理解您的查询需求，请尝试更具体的描述。"
        
        # 检查表可用性
        all_available, missing = metric_service.check_tables_availability(sql)
        
        if not all_available:
            missing_str = ", ".join(missing)
            logger.warning(f"AI 生成的 SQL 缺少表: {missing_str}")
            return (
                f"⚠️ 无法执行此查询\n\n"
                f"**原因**：需要的数据表不存在：\n"
                f"- {chr(10).join('`' + t + '`' for t in missing)}\n\n"
                f"当前系统仅支持查询存款和贷款相关数据。"
            )
        
        # 安全检查
        is_safe, error_msg = check_sql_safety(sql)
        if not is_safe:
            logger.warning(f"SQL 安全检查失败: {error_msg}")
            return f"查询被拒绝：{error_msg}"
        
        # 添加 LIMIT
        sql = add_limit_if_missing(sql)
        
        logger.info(f"AI 生成 SQL: {sql[:100]}...")
        
        # 执行 SQL
        return _execute_and_format(sql)
        
    except Exception as e:
        logger.exception(f"AI 生成 SQL 失败: {e}")
        return f"查询执行失败: {str(e)}"


def _execute_and_format(sql: str, metric_name: Optional[str] = None, unit: Optional[str] = None) -> str:
    """执行 SQL 并格式化结果。
    
    Args:
        sql: SQL 语句
        metric_name: 指标名称（用于结果描述）
        unit: 单位
        
    Returns:
        格式化的结果字符串
    """
    try:
        from app.ai.semantic import get_vanna
        vanna = get_vanna()
        
        df = vanna.run_sql(sql)
        
        if df is None or df.empty:
            return f"查询完成，没有找到符合条件的数据。\n\n执行的 SQL：\n```sql\n{sql}\n```"
        
        row_count = len(df)
        
        # 单值结果
        if row_count == 1 and len(df.columns) <= 3:
            values = ", ".join([f"{col}: {df.iloc[0][col]}" for col in df.columns])
            if metric_name:
                result_text = f"**{metric_name}**：{values}"
            else:
                result_text = f"查询结果：{values}"
            if unit:
                result_text += f" ({unit})"
        else:
            # 多行结果
            if metric_name:
                result_text = f"**{metric_name}** 查询返回 {row_count} 条记录：\n\n"
            else:
                result_text = f"查询返回 {row_count} 条记录：\n\n"
            result_text += df.head(10).to_markdown(index=False)
            if row_count > 10:
                result_text += f"\n\n... 共 {row_count} 条记录"
        
        result_text += f"\n\n执行的 SQL：\n```sql\n{sql}\n```"
        
        return result_text
        
    except Exception as e:
        logger.exception(f"SQL 执行失败: {e}")
        return f"执行失败: {str(e)}\n\n执行的 SQL：\n```sql\n{sql}\n```"


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
    
    metric_service = get_metric_service()
    
    # 表可用性检查
    all_available, missing = metric_service.check_tables_availability(sql)
    if not all_available:
        return f"SQL 执行失败：缺少数据表 {', '.join(missing)}"
    
    # 安全检查
    is_safe, error_msg = check_sql_safety(sql)
    if not is_safe:
        return f"SQL 被拒绝：{error_msg}"
    
    # 添加 LIMIT
    sql = add_limit_if_missing(sql)
    
    try:
        from app.ai.semantic import get_vanna
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
