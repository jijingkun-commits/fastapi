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
from app.ai.utils.message_factory import create_ai_message
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
from app.ai.utils.schema_router import route_schema
from app.core.config import (
    ANALYTICS_DEFAULT_SCHEMA, ENABLE_LLM_JUDGE, LLM_JUDGE_MODEL,
    SQL_GENERATION_MODEL,
    MODEL_ROUTING_LLM_JUDGE, MODEL_ROUTING_SQL_GENERATION, get_routing_model
)

logger = logging.getLogger(__name__)


# ==================== 系统提示词 ====================

AVAILABLE_METRICS = """
- 贷款余额 / 贷款总额: 贷款类指标，同义词：贷款、放款余额
- 存款余额 / 存款总额: 存款类指标，同义词：存款、储蓄
- 不良贷款率: 风控类指标，同义词：NPL 比率
- 贷款户数: 贷款类指标，同义词：贷款客户数
- 存款户数: 存款类指标，同义词：存款客户数
- 分机构存款余额 / 分行存款: 按机构维度的存款统计
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

    # 多轮上下文：从 state 取已有信息，避免重复询问
    existing_metric = (state.get("matched_metric") or "").strip()
    existing_time = (state.get("time_range") or "").strip()
    existing_dims = state.get("dimensions") or []
    existing_filters = state.get("filters") or []
    if isinstance(existing_dims, list):
        existing_dims_str = "、".join(existing_dims) if existing_dims else ""
    else:
        existing_dims_str = str(existing_dims) if existing_dims else ""
    if isinstance(existing_filters, list):
        existing_filters_str = "、".join(existing_filters) if existing_filters else ""
    else:
        existing_filters_str = str(existing_filters) if existing_filters else ""
    parts = []
    if existing_metric:
        parts.append(f"指标: {existing_metric}")
    if existing_time:
        parts.append(f"时间范围: {existing_time}")
    if existing_dims_str:
        parts.append(f"聚合维度: {existing_dims_str}")
    if existing_filters_str:
        parts.append(f"筛选: {existing_filters_str}")
    existing_context = "；".join(parts) if parts else "（无，为首轮或尚未提供）"

    # 调用 LLM 分析意图（internal=True 自动禁用流式 + 添加 tag，防止 JSON 泄露）
    # 使用 SQL 生成/内部分析 路由配置的模型，避免推理模型浪费 thinking tokens
    sql_gen_model = get_routing_model(MODEL_ROUTING_SQL_GENERATION, SQL_GENERATION_MODEL)
    llm = get_llm(internal=True, model_id=sql_gen_model)
    prompt = DATA_INTENT_ANALYSIS_PROMPT.format(
        question=last_message,
        existing_context=existing_context,
        available_metrics=AVAILABLE_METRICS
    )

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        # 解析 JSON 响应
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            analysis = json.loads(content[json_start:json_end])
        else:
            analysis = {"intent": "free_query"}

        logger.info(f"意图分析结果: {analysis}")

        # 合并多轮结果：新值为空时保留已有值，避免覆盖用户已提供的信息
        new_metric = (analysis.get("metric_name") or "").strip()
        new_time = (analysis.get("time_range") or "").strip()
        new_dims = analysis.get("dimensions")
        if not isinstance(new_dims, list):
            new_dims = []
        new_filters = analysis.get("filters")
        if not isinstance(new_filters, list):
            new_filters = []
        merged_metric = new_metric or existing_metric
        merged_time = new_time or existing_time
        merged_dims = new_dims if new_dims else existing_dims
        merged_filters = new_filters if new_filters else existing_filters
        clarification = (analysis.get("clarification_needed") or "").strip()
        # 若合并后已具备指标+时间，且用户当前轮像是补充（短句），则不再要求澄清
        if clarification and merged_metric and merged_time:
            if len(last_message.strip()) <= 20 or any(kw in last_message for kw in ("本月", "总体", "汇总", "全部", "过去")):
                clarification = ""
                logger.info("多轮合并后已具备指标与时间，取消重复澄清")

        # 为 SQL 生成构造完整查询描述（多轮合并后的语义），避免仅用当前句「总体的」生成
        full_question = last_message
        if merged_metric or merged_time:
            parts_desc = []
            if merged_metric:
                parts_desc.append(f"查询{merged_metric}")
            if merged_time:
                parts_desc.append(f"时间范围{merged_time}")
            if merged_dims:
                parts_desc.append(f"按{merged_dims}聚合" if isinstance(merged_dims, list) else f"按{merged_dims}聚合")
            if merged_filters:
                parts_desc.append(f"筛选{merged_filters}" if isinstance(merged_filters, list) else str(merged_filters))
            if parts_desc and last_message.strip() not in ("本月", "总体", "总体的", "汇总", "全部"):
                full_question = "，".join(parts_desc) + "。" + (f" 用户补充：{last_message}" if last_message else "")
            elif parts_desc:
                full_question = "，".join(parts_desc)

        updates = {
            "data_intent": analysis.get("intent", "free_query"),
            "matched_metric": merged_metric or None,
            "time_range": merged_time or None,
            "filters": merged_filters,
            "dimensions": merged_dims,
            "viz_type": analysis.get("chart_type"),
            "clarification_needed": clarification or None,
            "query_context": {
                "original_question": full_question,
                "last_user_message": last_message,
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
    """指标匹配：向量检索 t_metric_definition，命中则直接用 query_template。
    
    职责：
    1. 根据用户问题向量检索数据库中的指标定义
    2. 命中且有 query_template 时，直接生成 SQL（跳过 LLM 生成，节省 Token）
    3. 未命中则回退到 Vanna RAG 路径
    
    改造记录：
    - 2026-02-07: 从硬编码电商模板改为数据库向量匹配 (ADR-011)
    """
    logger.info("=== metric_resolve 节点 ===")
    
    query_context = state.get("query_context", {})
    question = query_context.get("original_question", "")
    matched_metric = state.get("matched_metric")
    time_range = state.get("time_range")
    
    if not question and not matched_metric:
        return {"sql_source": "vanna"}
    
    try:
        vanna = get_vanna()
        
        # 向量检索 query_template 非空的指标
        candidates = _search_metrics_by_vector(
            vanna, question or matched_metric, top_k=3
        )
        
        if not candidates:
            logger.info("指标向量匹配: 无命中，回退到 Vanna")
            return {"sql_source": "vanna"}
        
        best = candidates[0]
        similarity = best.get("similarity", 0)
        
        # 相似度阈值：> 0.5 才使用模板（实测银行指标匹配多在 0.55-0.65 区间）
        if similarity < 0.5:
            logger.info(
                "指标向量匹配: 最佳相似度 %.3f < 0.5，回退到 Vanna (指标: %s)",
                similarity, best.get("metric_name")
            )
            return {"sql_source": "vanna"}
        
        query_template = best.get("query_template")
        if not query_template:
            logger.info(
                "指标命中但无 query_template: %s，回退到 Vanna",
                best.get("metric_id")
            )
            return {"sql_source": "vanna"}
        
        # 替换 ${data_dt} 参数
        sql = _replace_data_dt(query_template, time_range)
        
        logger.info(
            "指标命中: %s (%s), 相似度=%.3f, SQL=%s...",
            best.get("metric_id"), best.get("metric_name"),
            similarity, sql[:80]
        )
        
        return {
            "generated_sql": sql,
            "sql_source": "metric",
            "pending_sql": sql,
            "matched_metric": best.get("metric_name"),
        }
        
    except Exception as e:
        logger.warning("指标向量匹配异常，回退到 Vanna: %s", e)
        return {"sql_source": "vanna"}


def _search_metrics_by_vector(vanna, question: str, top_k: int = 3) -> list:
    """从 t_metric_definition 向量检索指标。
    
    只返回有 query_template 的指标，按相似度降序排列。
    """
    from sqlalchemy import create_engine, text
    
    embedding = vanna.generate_embedding(question)
    if not embedding:
        return []
    
    embedding_str = str(embedding)
    
    sql = text("""
        SELECT metric_id, metric_name, description,
               query_template, template_source,
               1 - (embedding <=> :embedding) AS similarity
        FROM t_metric_definition
        WHERE is_active = TRUE
          AND embedding IS NOT NULL
          AND query_template IS NOT NULL
          AND 1 - (embedding <=> :embedding) > 0.5
        ORDER BY embedding <=> :embedding
        LIMIT :top_k
    """)
    
    try:
        from app.core.config import DATABASE_URL
        with create_engine(DATABASE_URL).connect() as conn:
            rows = conn.execute(sql, {
                "embedding": embedding_str, "top_k": top_k
            }).fetchall()
        
        return [
            {
                "metric_id": r.metric_id,
                "metric_name": r.metric_name,
                "description": r.description,
                "query_template": r.query_template,
                "template_source": r.template_source,
                "similarity": r.similarity,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("指标向量检索失败: %s", e)
        return []


def _replace_data_dt(sql: str, time_range: str = None) -> str:
    """将 query_template 中的 ${data_dt} 替换为实际日期。
    
    策略：
    1. 如果用户指定了时间范围（如"上月""6月"），解析为具体日期
    2. 否则查询分析库中最新的数据日期
    3. 兜底使用当天日期
    """
    if "${data_dt}" not in sql:
        return sql
    
    date_val = None
    
    # 尝试从用户时间范围推断
    if time_range:
        date_val = _parse_business_date(time_range)
    
    # 查询分析库最新数据日期
    if not date_val:
        date_val = _get_latest_data_date()
    
    # 兜底
    if not date_val:
        from datetime import datetime
        date_val = datetime.now().strftime("%Y%m%d")
    
    logger.info("${data_dt} 替换为: %s (time_range=%s)", date_val, time_range)
    return sql.replace("${data_dt}", date_val)


def _parse_business_date(time_range: str) -> str:
    """从自然语言时间范围解析业务日期（格式 YYYYMMDD）。"""
    from datetime import datetime, timedelta
    import re
    
    now = datetime.now()
    text = time_range.strip()
    
    # 直接日期格式: 2025-06-30 或 20250630
    m = re.search(r'(\d{4})-?(\d{2})-?(\d{2})', text)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    
    # 月末日期推断
    if "上月" in text or "上个月" in text:
        first_of_month = now.replace(day=1)
        last_of_prev = first_of_month - timedelta(days=1)
        return last_of_prev.strftime("%Y%m%d")
    
    if "本月" in text or "这个月" in text:
        return now.strftime("%Y%m%d")
    
    # 年月: "6月" "2025年6月"
    m = re.search(r'(\d{4})年?(\d{1,2})月', text)
    if m:
        import calendar
        year, month = int(m.group(1)), int(m.group(2))
        last_day = calendar.monthrange(year, month)[1]
        return f"{year}{month:02d}{last_day:02d}"
    
    m = re.search(r'(\d{1,2})月', text)
    if m:
        import calendar
        month = int(m.group(1))
        year = now.year if month <= now.month else now.year - 1
        last_day = calendar.monthrange(year, month)[1]
        return f"{year}{month:02d}{last_day:02d}"
    
    return None


def _get_latest_data_date() -> str:
    """查询分析库中 f_mid_index_result 最新数据日期。"""
    try:
        from app.db.session import analytics_engine
        from sqlalchemy import text
        
        with analytics_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT MAX(data_dt) FROM fdmdata.f_mid_index_result"
            )).scalar()
            if result:
                return str(result).replace("-", "")
    except Exception as e:
        logger.debug("查询最新数据日期失败: %s", e)
    
    return None


def schema_retrieve(state: DataAgentState) -> Dict:
    """检索相关表结构（Vanna RAG）。
    
    职责：
    1. 使用 schema 路由确定目标 schema
    2. 使用 Vanna 检索相关 DDL（限定 schema 范围）
    3. 检索相关指标文档
    4. 检索类似历史问题
    """
    logger.info("=== schema_retrieve 节点 ===")
    
    query_context = state.get("query_context", {})
    question = query_context.get("original_question", "")
    
    if not question:
        return {}
    
    try:
        vanna = get_vanna()
        
        # 使用 schema 路由确定目标 schema
        target_schema = route_schema(question)
        logger.info(f"Schema 路由结果: {target_schema}")
        
        # 检索相关 DDL（传递 schema 参数，缩小检索范围）
        ddl_list = vanna.get_related_ddl(question, schema=target_schema)
        
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
        
        # 返回检索结果和目标 schema，供后续节点使用
        return {
            "retrieved_schema": retrieved_schema,
            "target_schema": target_schema
        }
        
    except Exception as e:
        logger.exception(f"Schema 检索失败: {e}")
        return {"retrieved_schema": []}


def sql_generate(state: DataAgentState) -> Dict:
    """使用检索结果生成 SQL（支持错误自愈）。
    
    职责：
    1. 将 RAG 检索结果整合到 prompt
    2. 调用 LLM 生成 SQL（显式传递上下文）
    3. 如果有上次执行错误，将错误信息反馈给 LLM 重新生成
    
    关键改进：
    - 使用 SQL_GENERATION_PROMPT 模板显式注入 DDL、文档、历史问答
    - 调用 vanna.submit_prompt() 而非 generate_sql()，避免双重检索
    - 支持错误自愈：利用 last_error 和 sql_history 改进生成
    """
    logger.info("=== sql_generate 节点 ===")
    
    # 获取迭代计数
    iterations = state.get("iterations", 0) + 1
    last_error = state.get("last_error")
    sql_history = state.get("sql_history", [])
    
    # 如果是重试，清除之前的 SQL
    if last_error:
        logger.info(f"第 {iterations} 次尝试生成 SQL（上次错误: {last_error[:50]}...）")
    
    # 如果已有生成的 SQL（来自 metric_resolve）且没有错误，跳过
    if state.get("generated_sql") and not last_error:
        return {"iterations": iterations}
    
    query_context = state.get("query_context", {})
    question = query_context.get("original_question", "")
    retrieved_schema = state.get("retrieved_schema", [])
    
    if not question:
        return {"clarification_needed": "请输入您的数据查询问题", "iterations": iterations}
    
    # 构建上下文（从 schema_retrieve 节点检索的结果）
    ddl_context = "\n\n".join([s["content"] for s in retrieved_schema if s["type"] == "ddl"])
    doc_context = "\n\n".join([s["content"] for s in retrieved_schema if s["type"] == "documentation"])
    
    # 构建历史问答示例
    similar_items = [s for s in retrieved_schema if s["type"] == "similar_query"]
    similar_context_parts = []
    for item in similar_items:
        content = item.get("content", {})
        if isinstance(content, dict):
            q = content.get("question", "")
            s = content.get("sql", "")
            if q and s:
                similar_context_parts.append(f"问题: {q}\nSQL:\n```sql\n{s}\n```")
    similar_context = "\n\n".join(similar_context_parts)
    
    # 如果没有任何检索结果，提供默认提示
    if not ddl_context:
        ddl_context = "（未检索到相关表结构，请根据通用 SQL 知识生成）"
    if not doc_context:
        doc_context = "（未检索到相关文档）"
    if not similar_context:
        similar_context = "（未检索到相关历史查询）"
    
    # 获取目标 Schema（由 schema_retrieve 节点确定）
    target_schema = state.get("target_schema", ANALYTICS_DEFAULT_SCHEMA)
    logger.info(f"RAG 上下文: DDL={len(ddl_context)}字符, Doc={len(doc_context)}字符, Similar={len(similar_context_parts)}条, Schema={target_schema}")
    
    try:
        vanna = get_vanna()
        
        # 构建 Schema 约束提示
        schema_constraint = f"""
**重要约束**：
- 生成的 SQL 必须使用 schema 前缀 `{target_schema}`
- 表名格式示例：`{target_schema}.table_name`
- 如果检索到的 DDL 中已包含 schema 前缀，请直接使用该前缀
"""
        
        # 按需加载 SQL 指南（复杂查询时提供更多上下文）
        sql_guide_section = ""
        if len(question) > 50 or state.get("data_intent") == "free_query":
            try:
                from app.ai.prompts.prompt_loader import load_reference
                sql_guide = load_reference("sql_guide")
                if sql_guide:
                    sql_guide_section = f"\n\n## SQL 编写指南\n\n{sql_guide}"
                    logger.debug("已加载 sql_guide 参考文档")
            except Exception as e:
                logger.debug(f"加载 sql_guide 失败（不影响主流程）: {e}")
        
        # 构建完整的 prompt（显式注入 RAG 检索结果 + Schema 约束 + 可选指南）
        full_prompt = SQL_GENERATION_PROMPT.format(
            ddl=ddl_context,
            documentation=doc_context,
            similar_queries=similar_context,
            question=question
        ) + schema_constraint + sql_guide_section
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": "你是一个专业的 SQL 专家，根据提供的数据库结构和用户问题生成精准的 SQL 查询。"},
            {"role": "user", "content": full_prompt}
        ]
        
        # 如果有上次执行错误，添加错误反馈（错误自愈机制）
        if last_error and sql_history:
            error_feedback = _build_error_feedback(sql_history, last_error)
            messages.append({"role": "assistant", "content": sql_history[-1].get("sql", "")})
            messages.append({"role": "user", "content": error_feedback})
            logger.info(f"添加错误反馈到 prompt: {error_feedback[:100]}...")
        
        # 使用 submit_prompt 直接提交，避免 generate_sql 内部的重复检索
        # 使用 SQL 生成路由配置的模型（标准模型，非推理），避免浪费 thinking tokens
        sql_model = get_routing_model(MODEL_ROUTING_SQL_GENERATION, SQL_GENERATION_MODEL)
        response = vanna.submit_prompt(
            messages,
            model_id=sql_model,
            enable_thinking=state.get("enable_thinking", False),
        )
        
        if not response:
            return {
                "clarification_needed": "SQL 生成失败，请稍后重试",
                "iterations": iterations
            }
        
        # 从响应中提取 SQL
        sql = _extract_sql_from_response(response)
        
        if sql:
            logger.info(f"生成 SQL (含 RAG 上下文): {sql[:100]}...")
            
            # 更新 SQL 历史
            new_history = sql_history + [{"sql": sql, "error": None}]
            
            # LLM Judge 质量评估（可选）
            judge_feedback = None
            if ENABLE_LLM_JUDGE:
                try:
                    from app.ai.llm_judge import evaluate_sql_response_sync
                    
                    judge_result = evaluate_sql_response_sync(
                        sql, "待执行", get_routing_model(MODEL_ROUTING_LLM_JUDGE, LLM_JUDGE_MODEL)
                    )
                    
                    if judge_result.score == "fail":
                        logger.warning(f"SQL 质量评估失败: {judge_result.feedback}")
                        judge_feedback = judge_result.feedback
                    else:
                        logger.info(f"SQL 质量评估通过: {judge_result.score}")
                except Exception as e:
                    logger.warning(f"SQL 质量评估异常（不阻塞主流程）: {e}")
            
            result = {
                "generated_sql": sql,
                "sql_source": "vanna_rag",
                "pending_sql": sql,
                "iterations": iterations,
                "last_error": None,
                "sql_history": new_history
            }
            
            if judge_feedback:
                result["judge_feedback"] = judge_feedback
            
            return result
        else:
            return {
                "clarification_needed": "无法理解您的查询需求，请重新描述或提供更多细节",
                "iterations": iterations
            }
            
    except Exception as e:
        logger.exception(f"SQL 生成失败: {e}")
        return {
            "clarification_needed": f"SQL 生成失败: {str(e)}",
            "iterations": iterations
        }


def _build_error_feedback(sql_history: List[Dict], last_error: str) -> str:
    """构建错误反馈提示，帮助 LLM 修正 SQL。
    
    Args:
        sql_history: 历史 SQL 列表
        last_error: 最后一次错误信息
        
    Returns:
        错误反馈提示字符串
    """
    feedback_parts = [
        "上一次生成的 SQL 执行失败，请根据错误信息修正：",
        "",
        f"**错误信息**: {last_error}",
        "",
        "**要求**:",
        "1. 分析错误原因（可能是表名、列名错误，或语法问题）",
        "2. 根据提供的 DDL 结构，使用正确的表名和列名",
        "3. 确保 SQL 语法正确",
        "4. 只返回修正后的 SQL，不要其他解释",
    ]
    
    # 如果历史中有多次失败，提醒避免重复错误
    if len(sql_history) > 1:
        feedback_parts.append("")
        feedback_parts.append("**历史尝试**（请避免重复这些错误）:")
        for i, item in enumerate(sql_history[-3:], 1):  # 只显示最近 3 次
            if item.get("error"):
                feedback_parts.append(f"  {i}. SQL: {item['sql'][:80]}... → 错误: {item['error'][:50]}...")
    
    return "\n".join(feedback_parts)


def _extract_sql_from_response(response: str) -> Optional[str]:
    """从 LLM 响应中提取 SQL 语句。
    
    支持多种格式：
    - 直接的 SQL 语句
    - ```sql ... ``` 代码块
    - ```...``` 代码块
    """
    if not response:
        return None
    
    response = response.strip()
    
    # 尝试提取 ```sql ... ``` 代码块
    import re
    sql_block_pattern = r"```(?:sql)?\s*([\s\S]*?)```"
    matches = re.findall(sql_block_pattern, response, re.IGNORECASE)
    if matches:
        # 返回第一个非空的 SQL 块
        for match in matches:
            sql = match.strip()
            if sql and sql.upper().startswith(("SELECT", "WITH")):
                return sql
    
    # 如果没有代码块，尝试直接提取 SELECT/WITH 语句
    lines = response.split('\n')
    sql_lines = []
    in_sql = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith(("SELECT", "WITH")):
            in_sql = True
        if in_sql:
            sql_lines.append(line)
            # 判断 SQL 结束：支持 ; 和 ; -- comment 两种结尾
            stripped_no_comment = re.sub(r'--.*$', '', stripped).rstrip()
            if stripped_no_comment.endswith(';'):
                break
    
    if sql_lines:
        sql = '\n'.join(sql_lines).strip()
        # 移除末尾的 ; 或 ; -- comment
        sql = re.sub(r';\s*--[^\n]*$', '', sql).rstrip()
        if sql.endswith(';'):
            sql = sql[:-1].strip()
        return sql
    
    # 最后尝试：如果整个响应看起来像 SQL
    if response.upper().startswith(("SELECT", "WITH")):
        sql = re.sub(r';\s*--[^\n]*$', '', response).rstrip()
        return sql.rstrip(';').strip()
    
    return None


def sql_safety_check(state: DataAgentState) -> Dict:
    """SQL 安全检查节点。
    
    使用统一的 SQL 安全检查工具，检查：
    1. 是否为只读查询
    2. 是否包含危险操作关键词
    3. 是否访问敏感表
    4. 是否包含多条语句
    5. 自动添加 LIMIT 防止超大结果集
    """
    logger.info("=== sql_safety_check 节点 ===")
    
    from app.ai.utils.sql_safety import sanitize_sql
    
    sql = state.get("pending_sql") or state.get("generated_sql")
    if not sql:
        return {}
    
    # 使用统一的安全检查和处理
    processed_sql, is_safe, error = sanitize_sql(sql, auto_limit=True, limit=1000)
    
    if not is_safe:
        logger.warning(f"SQL 安全检查失败: {error}")
        return {
            "clarification_needed": f"查询被拒绝：{error}",
            "pending_sql": None
        }
    
    # 如果 SQL 被修改（添加了 LIMIT），更新状态
    if processed_sql != sql:
        logger.info("SQL 已自动添加 LIMIT 1000")
        return {
            "generated_sql": processed_sql,
            "pending_sql": processed_sql,
            "sql_approved": True
        }
    
    return {"sql_approved": True}


def sql_execute(state: DataAgentState) -> Dict:
    """执行 SQL 并返回结果（支持错误自愈）。
    
    职责：
    1. 在 Analytics DB 执行 SQL
    2. 将结果转换为可序列化格式
    3. 生成结果解释
    4. 如果执行失败，记录错误信息供重试使用
    
    错误自愈：
    - 执行失败时，设置 last_error 和更新 sql_history
    - 路由函数会根据 iterations 决定是否重试
    """
    logger.info("=== sql_execute 节点 ===")
    
    try:
        writer = get_stream_writer()
    except Exception:
        writer = lambda x: None
    
    sql = state.get("generated_sql")
    iterations = state.get("iterations", 1)
    sql_history = state.get("sql_history", [])
    user_id = state.get("user_id")
    
    if not sql:
        emit_error(writer, "没有可执行的 SQL", node="sql_execute")
        return {"messages": [create_ai_message("❌ 没有可执行的 SQL")]}
    
    # === 权限检查与 SQL 重写 ===
    if user_id:
        try:
            from app.ai.utils.sql_rewriter import check_and_rewrite_sql
            
            rewritten_sql, is_allowed, perm_error = check_and_rewrite_sql(sql, user_id)
            
            if not is_allowed:
                logger.warning(f"SQL 权限检查失败: user_id={user_id}, error={perm_error}")
                emit_error(writer, f"权限不足: {perm_error}", node="sql_execute")
                return {
                    "messages": [create_ai_message(f"❌ 权限不足：{perm_error}")],
                    "last_error": perm_error,
                }
            
            if rewritten_sql != sql:
                logger.info(f"SQL 已被权限重写: 原始长度={len(sql)}, 重写后={len(rewritten_sql)}")
                sql = rewritten_sql
                
        except Exception as e:
            logger.error(f"权限检查异常，拒绝执行: {e}", exc_info=True)
            emit_error(writer, "权限检查失败，请稍后重试", node="sql_execute")
            return {
                "messages": [create_ai_message("❌ 权限检查失败，请稍后重试")],
                "last_error": f"权限检查异常: {str(e)}",
            }
    
    try:
        vanna = get_vanna()
        
        # 执行 SQL（可能已被权限重写）
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
        response_msg = create_ai_message(
            interpretation,
            additional_kwargs={
                "data_type": "sql_result",
                "data": {
                    "sql": sql,
                    "columns": columns,
                    "rows": result_data[:100],  # 限制返回行数
                    "total_rows": len(result_data),
                    "sql_source": state.get("sql_source", "unknown"),
                    "iterations": iterations  # 记录重试次数
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
        
        # 执行成功后进行质量评估（异步，不阻塞主流程）
        evaluation_result = None
        try:
            from app.ai.utils.sql_evaluator import quick_evaluate
            
            # 快速评估（不调用 LLM）
            evaluation_result = quick_evaluate(sql)
            
            # 构建 DDL 上下文用于评估
            ddl_context = [
                s["content"] for s in state.get("retrieved_schema", []) 
                if s.get("type") == "ddl"
            ]
            
            logger.info(
                "SQL 评估完成: valid=%s, complexity=%s, warnings=%s",
                evaluation_result.get("is_valid"),
                evaluation_result.get("complexity"),
                evaluation_result.get("warnings", [])
            )
            
        except Exception as eval_error:
            logger.warning(f"SQL 评估失败（不影响主流程）: {eval_error}")
        
        # 执行成功，清除错误状态
        result_data_dict = {
            "messages": [response_msg],
            "sql_result": result_data,
            "last_error": None,
            "execution_success": True
        }
        
        # 附加评估结果（如果有）
        if evaluation_result:
            result_data_dict["sql_evaluation"] = evaluation_result
        
        # 记录查询日志（用于 SQL 修正台）
        try:
            from app.ai.semantic.data_access_control import get_access_control
            thread_id = state.get("thread_id")
            dac = get_access_control(user_id=user_id)
            dac.log_query(
                question=question,
                sql=sql,
                success=True,
                thread_id=thread_id
            )
        except Exception as log_error:
            logger.warning(f"查询日志记录失败（不影响主流程）: {log_error}")
        
        return result_data_dict
        
    except Exception as e:
        logger.exception(f"SQL 执行失败 (第 {iterations} 次): {e}")
        error_str = str(e)
        
        # 更新 SQL 历史，记录错误
        updated_history = []
        for item in sql_history:
            if item.get("sql") == sql and item.get("error") is None:
                # 更新当前 SQL 的错误信息
                updated_history.append({"sql": sql, "error": error_str})
            else:
                updated_history.append(item)
        
        # 如果历史中没有当前 SQL，添加它
        if not any(item.get("sql") == sql for item in updated_history):
            updated_history.append({"sql": sql, "error": error_str})
        
        # 使用统一的错误处理模块
        from app.ai.utils.error_handler import (
            is_recoverable as check_recoverable,
            format_retry_message,
            build_final_error_message
        )
        
        # 判断是否应该重试（错误自愈）
        is_recoverable = check_recoverable(error_str)
        
        if is_recoverable and iterations < MAX_RETRY_ITERATIONS:
            logger.info(f"可恢复错误，将进行重试 (当前: {iterations}/{MAX_RETRY_ITERATIONS})")
            retry_msg = format_retry_message(iterations, MAX_RETRY_ITERATIONS)
            emit_status(writer, retry_msg, node="sql_execute")
            
            return {
                "last_error": error_str,
                "sql_history": updated_history,
                "generated_sql": None,  # 清除当前 SQL，触发重新生成
                "pending_sql": None,
                "execution_success": False
            }
        else:
            # 不可恢复或已达最大重试次数
            # 构建上下文信息（用于智能建议）
            context = {}
            retrieved_schema = state.get("retrieved_schema", [])
            ddl_tables = []
            for item in retrieved_schema:
                if item.get("type") == "ddl":
                    content = item.get("content", "")
                    import re
                    match = re.search(r'CREATE TABLE\s+(\S+)', content, re.IGNORECASE)
                    if match:
                        ddl_tables.append(match.group(1))
            if ddl_tables:
                context["available_tables"] = ddl_tables
            
            # 使用统一的错误消息格式化
            error_msg = build_final_error_message(error_str, iterations, sql, context)
            
            emit_error(writer, error_msg, node="sql_execute")
            
            # 记录失败的查询日志（用于 SQL 修正台）
            try:
                from app.ai.semantic.data_access_control import get_access_control
                query_context = state.get("query_context", {})
                question = query_context.get("original_question", "")
                thread_id = state.get("thread_id")
                dac = get_access_control(user_id=user_id)
                dac.log_query(
                    question=question,
                    sql=sql,
                    success=False,
                    thread_id=thread_id
                )
            except Exception as log_error:
                logger.warning(f"查询日志记录失败: {log_error}")
            
            return {
                "messages": [create_ai_message(error_msg)],
                "last_error": error_str,
                "sql_history": updated_history,
                "execution_success": False
            }


# 最大重试次数
MAX_RETRY_ITERATIONS = 3


def clarify_node(state: DataAgentState) -> Dict:
    """澄清节点：向用户询问更多信息。"""
    logger.info("=== clarify_node 节点 ===")
    
    clarification = state.get("clarification_needed", "请提供更多信息")
    
    return {
        "messages": [create_ai_message(f"🤔 {clarification}")]
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
        return "查询完成，但没有找到符合条件的数据。\n\n💡 **排查建议**：\n1. **日期范围**：请检查查询日期是否与数据库中的数据匹配（当前导入数据日期为 2025-06-30）。\n2. **查询条件**：尝试放宽过滤条件或查询全量数据。"
    
    # 简单解释
    row_count = len(result)
    if row_count == 1:
        # 单值结果，直接展示
        row = result[0]
        
        # 特殊处理：如果只有一列且值为 None (常见于 SUM/AVG 等聚合函数未匹配到数据)
        if len(row) == 1:
            key, value = list(row.items())[0]
            if value is None:
                return f"查询完成，但计算结果为空 ({key}: None)。\n\n💡 **排查建议**：\n1. **日期范围**：请检查查询日期是否与数据库中的数据匹配。\n   *(当前导入测试数据日期为: 2025-06-30，如果您查询的是'本月'或'今天'，可能会查不到数据)*\n2. **指定日期**：建议尝试指定具体日期查询，例如 `2025-06-30`。"
        
        # 格式化 None 值
        formatted_values = []
        for k, v in row.items():
            display_val = "无数据" if v is None else str(v)
            formatted_values.append(f"{k}: {display_val}")
            
        values = ", ".join(formatted_values)
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


def route_after_execute(state: DataAgentState) -> Literal["end", "retry"]:
    """执行后路由（错误自愈机制）。
    
    根据执行结果决定是否重试：
    - 成功：结束
    - 失败且可重试：回到 generate 节点重新生成 SQL
    - 失败且不可重试/已达上限：结束
    """
    execution_success = state.get("execution_success", True)
    iterations = state.get("iterations", 1)
    last_error = state.get("last_error")
    
    # 执行成功，结束
    if execution_success:
        return "end"
    
    # 有错误且未达最大重试次数，尝试重试
    if last_error and iterations < MAX_RETRY_ITERATIONS:
        logger.info(f"触发错误自愈: 第 {iterations} 次失败，将重试")
        return "retry"
    
    # 其他情况结束（已有 messages 或达到重试上限）
    return "end"


# ==================== 图构建 ====================

def create_data_graph(model=None, enable_thinking: bool = False, model_id: str = None, checkpointer=None):
    """创建问数 Agent LangGraph（含错误自愈机制）。
    
    工作流程：
    1. analyze: 分析用户意图
    2. metric/schema: 指标匹配或 Schema 检索
    3. generate: SQL 生成
    4. safety: 安全检查
    5. execute: 执行 SQL
    6. 如果执行失败且可重试，回到 generate 重新生成（最多 3 次）
    
    Args:
        model: LLM 实例（可选，未使用但保留以保持接口一致）
        enable_thinking: 是否启用深度思考（可选）
        model_id: 模型 ID（可选）
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
    
    # execute → 条件路由（错误自愈机制）
    workflow.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "end": END,
            "retry": "generate"  # 重试时回到 generate 节点
        }
    )
    
    # clarify → END (等待用户回复)
    workflow.add_edge("clarify", END)
    
    # 编译
    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


# 导出
__all__ = ["create_data_graph", "DataAgentState"]
