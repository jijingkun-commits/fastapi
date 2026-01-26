"""LangGraph 问数 Agent（中文注释）。

基于 Vanna RAG 的数据查询 Agent，支持：
- 指标查询（预定义指标模板）
- 自由查询（Vanna SQL 生成）
- 数据可视化
- SQL 安全校验
"""
import logging
import json
from typing import Dict, List, Optional, Literal

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.config import get_stream_writer

from app.ai.llm_util import get_llm
from app.ai.state import DataAgentState
from app.ai.semantic import get_vanna
from app.ai.prompts.data_prompts import (
    DATA_INTENT_ANALYSIS_PROMPT,
    SQL_GENERATION_PROMPT,
    RESULT_INTERPRETATION_PROMPT,
    SQL_SAFETY_CHECK_PROMPT
)
from app.ai.events import emit_token, emit_status, emit_error, emit_result
from app.ai.utils.state_helpers import get_user_id

logger = logging.getLogger(__name__)


# ==================== 系统提示词 ====================

AVAILABLE_METRICS = """
- total_gmv: 成交总额 (GMV)，同义词：销售额、收入
- order_count: 订单数量，同义词：成单量、订单总数
- avg_order_value: 客单价 (AOV)，同义词：平均订单金额
- new_user_count: 新增用户数，同义词：注册用户
"""


# ==================== 节点函数 ====================

def analyze_data_intent(state: DataAgentState) -> Dict:
    """分析用户数据查询意图。
    
    职责：
    1. 识别意图类型（metric_query, free_query, visualization, clarification）
    2. 提取时间范围、筛选条件、聚合维度
    3. 匹配预定义指标（如有）
    """
    logger.info("=== analyze_data_intent 节点 ===")
    
    messages = state.get("messages", [])
    if not messages:
        return {"clarification_needed": "请输入您的数据查询问题"}
    
    # 获取最后一条用户消息
    last_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break
    
    if not last_message:
        return {"clarification_needed": "请输入您的数据查询问题"}
    
    # 调用 LLM 分析意图
    llm = get_llm()
    prompt = DATA_INTENT_ANALYSIS_PROMPT.format(
        question=last_message,
        available_metrics=AVAILABLE_METRICS
    )
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # 解析 JSON 响应
        # 尝试提取 JSON
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            analysis = json.loads(content[json_start:json_end])
        else:
            analysis = {"intent": "free_query"}
        
        logger.info(f"意图分析结果: {analysis}")
        
        updates = {
            "data_intent": analysis.get("intent", "free_query"),
            "matched_metric": analysis.get("metric_name"),
            "time_range": analysis.get("time_range"),
            "filters": analysis.get("filters", []),
            "dimensions": analysis.get("dimensions", []),
            "viz_type": analysis.get("chart_type"),
            "clarification_needed": analysis.get("clarification_needed"),
            "query_context": {
                "original_question": last_message,
                "analysis": analysis
            }
        }
        
        return updates
        
    except Exception as e:
        logger.exception(f"意图分析失败: {e}")
        return {
            "data_intent": "free_query",
            "query_context": {"original_question": last_message}
        }


def metric_resolve(state: DataAgentState) -> Dict:
    """解析预定义指标，生成模板 SQL。
    
    职责：
    1. 从 semantic_model.yaml 或 t_metrics 表加载指标定义
    2. 根据时间范围和维度生成 SQL
    """
    logger.info("=== metric_resolve 节点 ===")
    
    matched_metric = state.get("matched_metric")
    time_range = state.get("time_range")
    dimensions = state.get("dimensions", [])
    
    if not matched_metric:
        return {"sql_source": "vanna"}  # 回退到 Vanna
    
    # 简化版：根据指标名生成 SQL 模板
    # 生产环境应从数据库或 YAML 加载配置
    sql_templates = {
        "total_gmv": """
            SELECT {dimensions} SUM(amount) AS total_gmv
            FROM t_orders
            WHERE status IN ('paid', 'shipped', 'completed')
            {time_filter}
            {group_by}
        """,
        "order_count": """
            SELECT {dimensions} COUNT(*) AS order_count
            FROM t_orders
            WHERE status != 'cancelled'
            {time_filter}
            {group_by}
        """,
        "avg_order_value": """
            SELECT {dimensions}
                   SUM(amount) / NULLIF(COUNT(*), 0) AS avg_order_value
            FROM t_orders
            WHERE status IN ('paid', 'shipped', 'completed')
            {time_filter}
            {group_by}
        """
    }
    
    template = sql_templates.get(matched_metric)
    if not template:
        return {"sql_source": "vanna"}
    
    # 构建 SQL
    dim_select = ", ".join(dimensions) + ", " if dimensions else ""
    group_by = f"GROUP BY {', '.join(dimensions)}" if dimensions else ""
    time_filter = _build_time_filter(time_range)
    
    sql = template.format(
        dimensions=dim_select,
        time_filter=time_filter,
        group_by=group_by
    ).strip()
    
    # 清理多余空白
    sql = " ".join(sql.split())
    
    logger.info(f"生成指标 SQL: {sql[:100]}...")
    
    return {
        "generated_sql": sql,
        "sql_source": "metric",
        "pending_sql": sql  # 待审核
    }


def schema_retrieve(state: DataAgentState) -> Dict:
    """检索相关表结构（Vanna RAG）。
    
    职责：
    1. 使用 Vanna 检索相关 DDL
    2. 检索相关指标文档
    3. 检索类似历史问题
    """
    logger.info("=== schema_retrieve 节点 ===")
    
    query_context = state.get("query_context", {})
    question = query_context.get("original_question", "")
    
    if not question:
        return {}
    
    try:
        vanna = get_vanna()
        
        # 检索相关 DDL
        ddl_list = vanna.get_related_ddl(question)
        
        # 检索相关文档/指标
        docs = vanna.get_related_documentation(question)
        
        # 检索历史问答
        similar_qs = vanna.get_related_question_sql(question)
        
        retrieved_schema = []
        for ddl in ddl_list:
            retrieved_schema.append({"type": "ddl", "content": ddl})
        for doc in docs:
            retrieved_schema.append({"type": "documentation", "content": doc})
        for sq in similar_qs:
            retrieved_schema.append({"type": "similar_query", "content": sq})
        
        logger.info(f"检索到 {len(retrieved_schema)} 条相关信息")
        
        return {"retrieved_schema": retrieved_schema}
        
    except Exception as e:
        logger.exception(f"Schema 检索失败: {e}")
        return {"retrieved_schema": []}


def sql_generate(state: DataAgentState) -> Dict:
    """使用 Vanna 生成 SQL。
    
    职责：
    1. 构建包含检索结果的 prompt
    2. 调用 LLM 生成 SQL
    3. 进行基础安全检查
    """
    logger.info("=== sql_generate 节点 ===")
    
    # 如果已有生成的 SQL（来自 metric_resolve），跳过
    if state.get("generated_sql"):
        return {}
    
    query_context = state.get("query_context", {})
    question = query_context.get("original_question", "")
    retrieved_schema = state.get("retrieved_schema", [])
    
    # 构建上下文
    ddl_context = "\n".join([s["content"] for s in retrieved_schema if s["type"] == "ddl"])
    doc_context = "\n".join([s["content"] for s in retrieved_schema if s["type"] == "documentation"])
    similar_context = "\n".join([
        f"Q: {s['content'].get('question', '')}\nSQL: {s['content'].get('sql', '')}"
        for s in retrieved_schema if s["type"] == "similar_query"
    ])
    
    try:
        vanna = get_vanna()
        
        # 使用 Vanna 生成 SQL
        sql = vanna.generate_sql(question)
        
        if sql:
            logger.info(f"Vanna 生成 SQL: {sql[:100]}...")
            return {
                "generated_sql": sql,
                "sql_source": "vanna",
                "pending_sql": sql
            }
        else:
            return {"clarification_needed": "无法理解您的查询需求，请重新描述"}
            
    except Exception as e:
        logger.exception(f"SQL 生成失败: {e}")
        return {"clarification_needed": f"SQL 生成失败: {str(e)}"}


def sql_safety_check(state: DataAgentState) -> Dict:
    """SQL 安全检查。
    
    检查：
    1. 是否包含危险操作（DROP, DELETE, UPDATE, TRUNCATE）
    2. 是否访问敏感表
    3. 是否有无限制查询
    """
    logger.info("=== sql_safety_check 节点 ===")
    
    sql = state.get("pending_sql") or state.get("generated_sql")
    if not sql:
        return {}
    
    sql_upper = sql.upper()
    
    # 简单检查危险操作
    dangerous_keywords = ["DROP", "DELETE", "UPDATE", "TRUNCATE", "ALTER", "INSERT"]
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            logger.warning(f"检测到危险关键词: {keyword}")
            return {
                "clarification_needed": f"检测到危险操作 ({keyword})，问数功能仅支持查询操作",
                "pending_sql": None
            }
    
    # 检查敏感表
    sensitive_tables = ["t_user", "password", "secret", "token"]
    for table in sensitive_tables:
        if table.upper() in sql_upper:
            logger.warning(f"检测到敏感表访问: {table}")
            return {
                "clarification_needed": f"检测到敏感表访问 ({table})，请联系管理员",
                "pending_sql": None
            }
    
    # 检查是否有 LIMIT（防止超大结果集）
    if "LIMIT" not in sql_upper:
        sql = sql.rstrip(";") + " LIMIT 1000;"
        logger.info("自动添加 LIMIT 1000")
        return {"generated_sql": sql, "pending_sql": sql}
    
    return {"sql_approved": True}


def sql_execute(state: DataAgentState) -> Dict:
    """执行 SQL 并返回结果。
    
    职责：
    1. 在 Analytics DB 执行 SQL
    2. 将结果转换为可序列化格式
    3. 生成结果解释
    """
    logger.info("=== sql_execute 节点 ===")
    
    writer = get_stream_writer()
    
    sql = state.get("generated_sql")
    if not sql:
        emit_error(writer, "没有可执行的 SQL", node="sql_execute")
        return {"messages": [AIMessage(content="❌ 没有可执行的 SQL")]}
    
    try:
        vanna = get_vanna()
        
        # 执行 SQL
        emit_status(writer, "正在执行查询...", node="sql_execute")
        df = vanna.run_sql(sql)
        
        # 转换为可序列化格式
        result_data = df.to_dict(orient="records")
        columns = list(df.columns)
        
        logger.info(f"查询返回 {len(result_data)} 行数据")
        
        # 生成结果解释
        query_context = state.get("query_context", {})
        question = query_context.get("original_question", "")
        
        interpretation = _interpret_result(question, sql, result_data)
        
        # 构建响应消息
        response_msg = AIMessage(
            content=interpretation,
            additional_kwargs={
                "data_type": "sql_result",
                "data": {
                    "sql": sql,
                    "columns": columns,
                    "rows": result_data[:100],  # 限制返回行数
                    "total_rows": len(result_data),
                    "sql_source": state.get("sql_source", "unknown")
                }
            }
        )
        
        emit_result(
            writer,
            data_type="sql_result",
            data={"rows": result_data[:20], "columns": columns},
            message=interpretation,
            node="sql_execute"
        )
        
        return {
            "messages": [response_msg],
            "sql_result": result_data
        }
        
    except Exception as e:
        logger.exception(f"SQL 执行失败: {e}")
        error_msg = f"❌ 查询执行失败: {str(e)}"
        emit_error(writer, error_msg, node="sql_execute")
        return {"messages": [AIMessage(content=error_msg)]}


def clarify_node(state: DataAgentState) -> Dict:
    """澄清节点：向用户询问更多信息。"""
    logger.info("=== clarify_node 节点 ===")
    
    clarification = state.get("clarification_needed", "请提供更多信息")
    
    return {
        "messages": [AIMessage(content=f"🤔 {clarification}")]
    }


# ==================== 辅助函数 ====================

def _build_time_filter(time_range: Optional[str]) -> str:
    """根据时间范围描述生成 SQL WHERE 子句。"""
    if not time_range:
        return ""
    
    time_range_lower = time_range.lower()
    
    # 简单匹配
    if "本月" in time_range or "这个月" in time_range:
        return "AND created_at >= DATE_TRUNC('month', CURRENT_DATE)"
    elif "上月" in time_range or "上个月" in time_range:
        return "AND created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND created_at < DATE_TRUNC('month', CURRENT_DATE)"
    elif "今天" in time_range:
        return "AND DATE(created_at) = CURRENT_DATE"
    elif "昨天" in time_range:
        return "AND DATE(created_at) = CURRENT_DATE - 1"
    elif "过去7天" in time_range or "最近7天" in time_range:
        return "AND created_at >= CURRENT_DATE - INTERVAL '7 days'"
    elif "过去30天" in time_range or "最近30天" in time_range:
        return "AND created_at >= CURRENT_DATE - INTERVAL '30 days'"
    else:
        return ""


def _interpret_result(question: str, sql: str, result: List[Dict]) -> str:
    """生成查询结果的自然语言解释。"""
    if not result:
        return "查询完成，没有找到符合条件的数据。"
    
    # 简单解释
    row_count = len(result)
    if row_count == 1:
        # 单值结果，直接展示
        row = result[0]
        values = ", ".join([f"{k}: {v}" for k, v in row.items()])
        return f"查询结果：{values}"
    else:
        return f"查询完成，共返回 {row_count} 条记录。"


# ==================== 路由函数 ====================

def route_data_intent(state: DataAgentState) -> Literal["clarify", "metric", "schema", "execute", "end"]:
    """根据意图路由到不同节点。"""
    
    # 需要澄清
    if state.get("clarification_needed"):
        return "clarify"
    
    # 意图分类
    intent = state.get("data_intent")
    
    if intent == "clarification":
        return "clarify"
    elif intent == "metric_query" and state.get("matched_metric"):
        return "metric"
    elif intent in ["free_query", "visualization"]:
        return "schema"
    else:
        return "schema"  # 默认走 Vanna


def route_after_metric(state: DataAgentState) -> Literal["safety", "schema"]:
    """指标解析后路由。"""
    if state.get("generated_sql"):
        return "safety"
    else:
        return "schema"  # 回退到 Vanna


def route_after_safety(state: DataAgentState) -> Literal["execute", "clarify"]:
    """安全检查后路由。"""
    if state.get("clarification_needed"):
        return "clarify"
    return "execute"


# ==================== 图构建 ====================

def create_data_graph(checkpointer=None):
    """创建问数 Agent LangGraph。
    
    Args:
        checkpointer: 检查点保存器（可选）
        
    Returns:
        编译后的 Graph 实例
    """
    workflow = StateGraph(DataAgentState)
    
    # === 添加节点 ===
    workflow.add_node("analyze", analyze_data_intent)
    workflow.add_node("metric", metric_resolve)
    workflow.add_node("schema", schema_retrieve)
    workflow.add_node("generate", sql_generate)
    workflow.add_node("safety", sql_safety_check)
    workflow.add_node("execute", sql_execute)
    workflow.add_node("clarify", clarify_node)
    
    # === 设置入口 ===
    workflow.set_entry_point("analyze")
    
    # === 设置边 ===
    
    # analyze → 条件路由
    workflow.add_conditional_edges(
        "analyze",
        route_data_intent,
        {
            "clarify": "clarify",
            "metric": "metric",
            "schema": "schema",
            "execute": "execute",
            "end": END
        }
    )
    
    # metric → 条件路由
    workflow.add_conditional_edges(
        "metric",
        route_after_metric,
        {
            "safety": "safety",
            "schema": "schema"
        }
    )
    
    # schema → generate
    workflow.add_edge("schema", "generate")
    
    # generate → safety
    workflow.add_edge("generate", "safety")
    
    # safety → 条件路由
    workflow.add_conditional_edges(
        "safety",
        route_after_safety,
        {
            "execute": "execute",
            "clarify": "clarify"
        }
    )
    
    # execute → END
    workflow.add_edge("execute", END)
    
    # clarify → END (等待用户回复)
    workflow.add_edge("clarify", END)
    
    # 编译
    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


# 导出
__all__ = ["create_data_graph", "DataAgentState"]
