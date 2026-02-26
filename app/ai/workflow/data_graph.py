"""LangGraph 问数 Agent（中文注释）。

基于 Vanna RAG 的数据查询 Agent，支持：
- 指标查询（预定义指标模板）
- 自由查询（Vanna SQL 生成）
- 数据可视化
- SQL 安全校验
"""
import logging
import json
import time
import re
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from numbers import Number
from typing import Dict, List, Optional, Literal, Any, Tuple

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from app.ai.utils.message_factory import create_ai_message
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.config import get_stream_writer

from app.ai.llm_util import get_scene_llm, _normalize_text_content
from app.ai.scene_registry import SCENE_KEY_DATA_INTENT_ANALYSIS
from app.ai.state import DataAgentState
from app.ai.semantic import get_vanna
from app.ai.prompts.data_prompts import (
    DATA_INTENT_ANALYSIS_PROMPT,
    SQL_GENERATION_PROMPT,
    RESULT_INTERPRETATION_PROMPT,
    SQL_SAFETY_CHECK_PROMPT
)
from app.ai.workflow.session_intent_kernel import (
    TURN_ACT_CONFIRM,
    TURN_ACT_CORRECTION,
    TURN_ACT_SUPPLEMENT,
    TURN_ACT_NEW_QUERY,
    classify_turn_act,
    reduce_session_frame,
    advance_clarify_fsm_state,
)
from app.ai.events import emit_token, emit_status, emit_error, emit_result
from app.ai.protocol import (
    build_streaming_result_payload_from_fields,
    build_result_additional_kwargs_payload,
)
from app.ai.utils.state_helpers import get_user_id
from app.ai.utils.schema_router import route_schema
from app.ai.utils.sql_parser import extract_tables_from_sql
from app.ai.utils.sql_empty_result_recovery import (
    is_effectively_empty_result,
    rewrite_sql_for_empty_result,
    rewrite_sql_for_column_compatibility,
)
from app.db.session import engine
from app.core.config import (
    ANALYTICS_DEFAULT_SCHEMA, ENABLE_LLM_JUDGE, ENABLE_RESULT_ENRICHMENT,
)
from app.services.result_enrichment_rule_service import (
    ResultLookupEnrichmentRuleConfig as ResultLookupEnrichmentRule,
    get_result_enrichment_rule_service,
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


_SQL_EMPTY_RESULT_FALLBACK_POLICY: Dict[str, Dict[str, str]] = {
    "metric": {
        "next_target": "training",
        "hint": "指标模板未查到数据，正在尝试训练集SQL...",
    },
    "training": {
        "next_target": "schema",
        "hint": "训练集SQL未查到数据，正在尝试通过表结构生成查询...",
    },
}


_EXECUTE_FALLBACK_ROUTE_MAP: Dict[str, str] = {
    "training": "fallback_training",
    "schema": "fallback_schema",
}


# ==================== 节点函数 ====================


@dataclass
class MetricTemplatePlan:
    """指标模板派生计划。"""

    select_items: List[str]
    from_expr: str
    where_expr: str
    measure_expr: str
    measure_alias: str


_DIMENSION_FIELD_MAP: Dict[str, List[str]] = {
    "客户": ["ecif_cust_no"],
    "机构": ["org_cd", "org_no", "legal_org_cd"],
    "分行": ["org_cd", "org_no", "legal_org_cd"],
    "支行": ["dept_cd"],
    "部门": ["dept_cd"],
    "日期": ["data_dt"],
}


_FALLBACK_RESULT_LOOKUP_ENRICHMENT_RULES: Tuple[ResultLookupEnrichmentRule, ...] = (
    ResultLookupEnrichmentRule(
        name="customer_name",
        key_column_candidates=("ecif_cust_no",),
        target_column="客户名称",
        source_table="fdmdata.f_mid_dep_tb",
        source_key_column="ecif_cust_no",
        source_value_column="cust_acct_name",
        source_date_column="data_dt",
        result_date_column_candidates=("data_dt",),
    ),
)


def _normalize_dimension_name(name: str) -> str:
    """规范化维度名称。"""
    return re.sub(r"\s+", "", str(name or "")).lower()


def _extract_top_n(question: str, default_n: int = 10) -> int:
    """从问题中提取 TopN，未命中时返回默认值。"""
    normalized = re.sub(r"\s+", "", question or "")
    m = re.search(r"前(\d+)", normalized)
    if not m:
        m = re.search(r"top(\d+)", normalized, re.IGNORECASE)
    if not m:
        return default_n

    try:
        return max(1, min(int(m.group(1)), 100))
    except Exception:
        return default_n


def _detect_query_shape(question: str, dimensions: Optional[List[str]] = None) -> str:
    """识别查询形态：total / dimension / top_n。"""
    if _is_topn_intent(question):
        return "top_n"

    dims = dimensions if isinstance(dimensions, list) else []
    if any(str(dim).strip() for dim in dims):
        return "dimension"

    return "total"


def _resolve_dimension_fields(dimensions: Optional[List[str]]) -> List[str]:
    """根据维度词解析目标字段。"""
    dims = dimensions if isinstance(dimensions, list) else []
    resolved: List[str] = []

    for dim in dims:
        normalized = _normalize_dimension_name(dim)
        if not normalized:
            continue

        for raw_key, fields in _DIMENSION_FIELD_MAP.items():
            if _normalize_dimension_name(raw_key) == normalized:
                for field in fields:
                    if field not in resolved:
                        resolved.append(field)

    return resolved


def _parse_metric_template_plan(sql: str) -> Optional[MetricTemplatePlan]:
    """解析指标模板 SQL，提取可组合结构。"""
    if not sql:
        return None

    try:
        import sqlglot
        from sqlglot import exp
    except Exception as e:
        logger.warning("sqlglot 不可用，无法解析指标模板: %s", e)
        return None

    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except Exception as e:
        logger.warning("指标模板 SQL 解析失败: %s", e)
        return None

    if not isinstance(parsed, exp.Select):
        return None

    from_expr = parsed.args.get("from_") or parsed.args.get("from")
    if from_expr is None:
        return None

    from_sql = from_expr.sql(dialect="postgres").strip()
    if not from_sql:
        return None
    if from_sql.upper().startswith("FROM "):
        from_sql = from_sql[5:].strip()

    where_expr = parsed.args.get("where")
    where_sql = ""
    if where_expr is not None and getattr(where_expr, "this", None) is not None:
        where_sql = where_expr.this.sql(dialect="postgres")

    measure_expr = None
    measure_alias = None
    other_selects: List[str] = []

    for select_item in parsed.expressions:
        item_sql = select_item.sql(dialect="postgres")

        if isinstance(select_item, exp.Alias):
            agg_expr = select_item.this
            alias_expr = select_item.alias
            alias_name = alias_expr if isinstance(alias_expr, str) else str(alias_expr or "")
        else:
            agg_expr = select_item
            alias_name = ""

        if isinstance(agg_expr, (exp.Sum, exp.Avg, exp.Count, exp.Max, exp.Min)) and measure_expr is None:
            measure_expr = agg_expr.sql(dialect="postgres")
            measure_alias = alias_name or agg_expr.sql(dialect="postgres")
            continue

        other_selects.append(item_sql)

    if not measure_expr:
        return None

    return MetricTemplatePlan(
        select_items=other_selects,
        from_expr=from_sql,
        where_expr=where_sql,
        measure_expr=measure_expr,
        measure_alias=measure_alias,
    )


def _resolve_dimension_fields_for_table(
    candidates: List[str],
    from_expr: str,
) -> List[str]:
    """根据模板 FROM 表的实际字段过滤维度候选列表。

    从 from_expr 提取 schema.table，查 t_meta_columns 获取该表的列集合，
    返回候选列表中第一个存在的字段。若元数据不可用则返回第一个候选。
    """
    if not candidates:
        return []

    # 从 from_expr 提取 schema.table（如 "fdmdata.f_mid_loan_k_tb"）
    table_match = re.match(r"([a-zA-Z_]\w*\.[a-zA-Z_]\w*)", from_expr.strip())
    if not table_match:
        return [candidates[0]]

    full_table = table_match.group(1).lower()

    try:
        from sqlalchemy import text
        from app.db.session import engine

        query = text(
            """
            SELECT LOWER(c.column_name) AS col
            FROM t_meta_columns c
            JOIN t_meta_tables t ON t.id = c.table_id
            WHERE LOWER(COALESCE(t.schema_name, 'public') || '.' || t.table_name) = :full_table
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(query, {"full_table": full_table}).fetchall()
        table_columns = {row.col for row in rows}
    except Exception as e:
        logger.warning("查询表字段元数据失败，使用首个候选: %s", e)
        return [candidates[0]]

    if not table_columns:
        return [candidates[0]]

    for candidate in candidates:
        if candidate.lower() in table_columns:
            return [candidate]

    logger.info("维度候选字段 %s 均不在表 %s 中", candidates, full_table)
    return []


def _build_metric_sql_from_plan(
    plan: MetricTemplatePlan,
    question: str,
    dimensions: Optional[List[str]] = None,
) -> Optional[str]:
    """根据模板计划和查询语义组装 SQL。"""
    shape = _detect_query_shape(question, dimensions)
    dimension_candidates = _resolve_dimension_fields(dimensions)

    if shape in ("dimension", "top_n") and not dimension_candidates:
        logger.info("指标模板派生缺少维度字段映射，shape=%s", shape)
        return None

    select_parts: List[str] = []
    group_by_fields: List[str] = []

    if shape in ("dimension", "top_n"):
        # 根据模板表的实际字段过滤候选
        dimension_fields = _resolve_dimension_fields_for_table(
            dimension_candidates, plan.from_expr
        )
        if not dimension_fields:
            logger.info("维度候选字段在模板表中均不存在，shape=%s", shape)
            return None
        for dim_field in dimension_fields:
            select_parts.append(dim_field)
            group_by_fields.append(dim_field)

    measure_part = f"{plan.measure_expr} AS {plan.measure_alias}"
    select_parts.append(measure_part)

    where_sql = f" WHERE {plan.where_expr}" if plan.where_expr else ""
    sql = f"SELECT {', '.join(select_parts)} FROM {plan.from_expr}{where_sql}"

    if group_by_fields:
        sql += f" GROUP BY {', '.join(group_by_fields)}"

    if shape == "top_n":
        top_n = _extract_top_n(question, default_n=10)
        sql += f" ORDER BY {plan.measure_alias} DESC LIMIT {top_n}"

    return sql


def _derive_metric_sql(
    query_template: str,
    time_range: Optional[str],
    question: str,
    dimensions: Optional[List[str]],
) -> Optional[str]:
    """基于指标模板派生 SQL（总量/维度/TopN）。"""
    sql_template = _replace_data_dt(query_template, time_range)
    plan = _parse_metric_template_plan(sql_template)
    if not plan:
        return sql_template

    derived = _build_metric_sql_from_plan(plan, question, dimensions)
    if derived:
        return derived

    return None


def _resolve_column(columns: List[str], candidates: Tuple[str, ...]) -> Optional[str]:
    """根据候选列名解析结果列（大小写/空白不敏感）。"""
    normalized_map = {str(col).strip().lower(): col for col in columns}
    for candidate in candidates:
        actual = normalized_map.get(str(candidate).strip().lower())
        if actual:
            return actual
    return None


def _result_has_column(columns: List[str], name: str) -> bool:
    """判断结果列是否已包含指定列。"""
    target = str(name).strip().lower()
    return any(str(col).strip().lower() == target for col in columns)


def _extract_single_date_value(
    rows: List[Dict[str, Any]],
    date_column_candidates: Tuple[str, ...],
) -> Optional[str]:
    """从结果中提取单一日期列值（如存在且唯一）。"""
    if not rows:
        return None

    row_columns = list(rows[0].keys())
    date_col = _resolve_column(row_columns, date_column_candidates)
    if not date_col:
        return None

    values = {str(row.get(date_col)) for row in rows if row.get(date_col) is not None}
    if len(values) != 1:
        return None
    return values.pop()


def _fetch_lookup_value_map(
    *,
    rule: ResultLookupEnrichmentRule,
    key_values: List[str],
    date_value: Optional[str],
) -> Dict[str, str]:
    """按规则查表补齐映射（优先同日，失败回退全量）。"""
    if not key_values:
        return {}

    from app.db.session import analytics_engine
    from sqlalchemy import text

    unique_keys = list(dict.fromkeys([str(v).strip() for v in key_values if str(v).strip()]))
    if not unique_keys:
        return {}

    exact_map: Dict[str, str] = {}
    if date_value and rule.source_date_column:
        sql_exact = text(f"""
            SELECT {rule.source_key_column}, {rule.source_value_column}
            FROM {rule.source_table}
            WHERE {rule.source_date_column} = :date_value
              AND {rule.source_key_column} = ANY(:key_values)
              AND {rule.source_value_column} IS NOT NULL
              AND {rule.source_value_column} <> ''
        """)
        try:
            with analytics_engine.connect() as conn:
                rows = conn.execute(
                    sql_exact,
                    {"date_value": date_value, "key_values": unique_keys},
                ).fetchall()
            buckets: Dict[str, List[str]] = {}
            for key_val, display_val in rows:
                key = str(key_val or "").strip()
                value = str(display_val or "").strip()
                if key and value:
                    buckets.setdefault(key, []).append(value)
            for key, values in buckets.items():
                exact_map[key] = Counter(values).most_common(1)[0][0]
        except Exception as e:
            logger.warning(
                "结果补齐规则执行失败(name=%s, date=%s): %s",
                rule.name,
                date_value,
                e,
            )

    unresolved = [key for key in unique_keys if key not in exact_map]
    if not unresolved:
        return exact_map

    sql_fallback = text(f"""
        SELECT {rule.source_key_column}, {rule.source_value_column}
        FROM {rule.source_table}
        WHERE {rule.source_key_column} = ANY(:key_values)
          AND {rule.source_value_column} IS NOT NULL
          AND {rule.source_value_column} <> ''
    """)

    fallback_map: Dict[str, str] = {}
    try:
        with analytics_engine.connect() as conn:
            rows = conn.execute(sql_fallback, {"key_values": unresolved}).fetchall()
        buckets: Dict[str, List[str]] = {}
        for key_val, display_val in rows:
            key = str(key_val or "").strip()
            value = str(display_val or "").strip()
            if key and value:
                buckets.setdefault(key, []).append(value)
        for key, values in buckets.items():
            fallback_map[key] = Counter(values).most_common(1)[0][0]
    except Exception as e:
        logger.warning("结果补齐规则回退失败(name=%s): %s", rule.name, e)

    merged = dict(exact_map)
    merged.update(fallback_map)
    return merged


def _apply_lookup_enrichment_rule(
    rows: List[Dict[str, Any]],
    columns: List[str],
    rule: ResultLookupEnrichmentRule,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """对结果应用单条查表补齐规则。"""
    if not rows or not columns:
        return rows, columns

    if _result_has_column(columns, rule.target_column):
        return rows, columns

    key_col = _resolve_column(columns, rule.key_column_candidates)
    if not key_col:
        return rows, columns

    key_values = [str(row.get(key_col) or "").strip() for row in rows if row.get(key_col)]
    if not key_values:
        return rows, columns

    date_value = _extract_single_date_value(rows, rule.result_date_column_candidates)
    value_map = _fetch_lookup_value_map(rule=rule, key_values=key_values, date_value=date_value)
    if not value_map:
        return rows, columns

    enriched_rows: List[Dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        key_value = str(copied.get(key_col) or "").strip()
        copied[rule.target_column] = value_map.get(key_value)
        enriched_rows.append(copied)

    new_columns = list(columns)
    insert_at = new_columns.index(key_col) + 1
    new_columns.insert(insert_at, rule.target_column)
    return enriched_rows, new_columns


def _load_runtime_result_enrichment_rules() -> Tuple[ResultLookupEnrichmentRule, ...]:
    """加载运行时结果增强规则（DB 优先，常量兜底）。"""
    service = get_result_enrichment_rule_service()
    return service.get_active_rules(
        force_refresh=False,
        fallback_rules=_FALLBACK_RESULT_LOOKUP_ENRICHMENT_RULES,
    )


def _enrich_result_rows_if_needed(
    rows: List[Dict[str, Any]],
    columns: List[str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """按规则链增强结果集（可扩展，不依赖单条查询写死）。"""
    if not ENABLE_RESULT_ENRICHMENT:
        return rows, columns

    try:
        rules = _load_runtime_result_enrichment_rules()
    except Exception as exc:
        logger.warning("加载结果增强规则失败，回退内置规则: %s", exc)
        rules = _FALLBACK_RESULT_LOOKUP_ENRICHMENT_RULES

    enriched_rows = rows
    enriched_columns = columns
    for rule in rules:
        enriched_rows, enriched_columns = _apply_lookup_enrichment_rule(
            enriched_rows,
            enriched_columns,
            rule,
        )
    return enriched_rows, enriched_columns


def _contains_chinese(text: str) -> bool:
    """判断字符串是否包含中文字符。"""
    return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))


def _normalize_column_key(column: str) -> str:
    """规范化列名键值（用于映射查找）。"""
    return str(column or "").strip().lower()


def _pick_most_common_stable(values: List[str]) -> Optional[str]:
    """稳定地选择高频值（频次相同取先出现）。"""
    if not values:
        return None

    counts = Counter(values)
    max_count = max(counts.values())
    for value in values:
        if counts[value] == max_count:
            return value
    return values[0]



def _normalize_column_data_type(data_type: Any) -> str:
    """规范化字段类型字符串。"""
    return re.sub(r"\s+", "", str(data_type or "")).lower()


def _is_temporal_data_type(data_type: str) -> bool:
    """判断字段类型是否为时间类型。"""
    normalized = _normalize_column_data_type(data_type)
    if not normalized:
        return False

    temporal_exact = {
        "date",
        "datetime",
        "timestamp",
        "timestamptz",
        "timestampwithouttimezone",
        "timestampwithtimezone",
        "time",
        "timetz",
    }
    if normalized in temporal_exact:
        return True

    temporal_tokens = ("date", "time", "timestamp", "datetime", "日期", "时间", "年月", "year", "month", "day")
    return any(token in normalized for token in temporal_tokens)

def _load_column_display_name_map(
    columns: List[str],
    sql: Optional[str],
) -> Dict[str, str]:
    """加载字段中文名映射（优先按 SQL 涉及表过滤，未命中则全局回退）。"""
    normalized_columns = list(
        dict.fromkeys(
            [
                _normalize_column_key(col)
                for col in columns
                if str(col or "").strip() and not _contains_chinese(str(col))
            ]
        )
    )
    if not normalized_columns:
        return {}

    sql_tables: List[str] = []
    if sql:
        try:
            sql_tables = sorted(extract_tables_from_sql(sql))
        except Exception as e:
            logger.debug("提取 SQL 涉及表失败，跳过表过滤: %s", e)

    from sqlalchemy import text

    def _query_candidates(table_filter: Optional[List[str]]) -> List[Tuple[str, str]]:
        table_clause = ""
        params: Dict[str, Any] = {"column_names": normalized_columns}
        if table_filter:
            table_clause = (
                " AND LOWER(COALESCE(t.schema_name, 'public') || '.' || t.table_name) = ANY(:table_names)"
            )
            params["table_names"] = table_filter

        query = text(
            """
            SELECT c.column_name, c.display_name
            FROM t_meta_columns c
            JOIN t_meta_tables t ON t.id = c.table_id
            WHERE c.display_name IS NOT NULL
              AND c.display_name <> ''
              AND LOWER(c.column_name) = ANY(:column_names)
            """
            + table_clause
        )

        try:
            with engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()
        except Exception as e:
            logger.warning("加载字段中文名映射失败(table_filter=%s): %s", bool(table_filter), e)
            return []

        return [
            (str(row.column_name or "").strip(), str(row.display_name or "").strip())
            for row in rows
            if str(row.column_name or "").strip() and str(row.display_name or "").strip()
        ]

    filtered_candidates = _query_candidates(sql_tables if sql_tables else None)
    all_candidates = filtered_candidates if filtered_candidates else _query_candidates(None)

    if not all_candidates:
        return {}

    grouped: Dict[str, List[str]] = {}
    for column_name, display_name in all_candidates:
        key = _normalize_column_key(column_name)
        if key in normalized_columns:
            grouped.setdefault(key, []).append(display_name)

    mapping: Dict[str, str] = {}
    for column_key, display_names in grouped.items():
        picked = _pick_most_common_stable(display_names)
        if picked:
            mapping[column_key] = picked

    return mapping

def _load_column_data_type_map(
    columns: List[str],
    sql: Optional[str],
) -> Dict[str, str]:
    """加载字段类型映射（优先按 SQL 涉及表过滤，未命中则全局回退）。"""
    normalized_columns = list(
        dict.fromkeys(
            [
                _normalize_column_key(col)
                for col in columns
                if str(col or "").strip()
            ]
        )
    )
    if not normalized_columns:
        return {}

    sql_tables: List[str] = []
    if sql:
        try:
            sql_tables = sorted(extract_tables_from_sql(sql))
        except Exception as e:
            logger.debug("提取 SQL 涉及表失败，字段类型映射降级: %s", e)

    from sqlalchemy import text

    def _query_candidates(table_filter: Optional[List[str]]) -> List[Tuple[str, str]]:
        table_clause = ""
        params: Dict[str, Any] = {"column_names": normalized_columns}
        if table_filter:
            table_clause = (
                " AND LOWER(COALESCE(t.schema_name, 'public') || '.' || t.table_name) = ANY(:table_names)"
            )
            params["table_names"] = table_filter

        query = text(
            """
            SELECT c.column_name, c.data_type
            FROM t_meta_columns c
            JOIN t_meta_tables t ON t.id = c.table_id
            WHERE c.data_type IS NOT NULL
              AND c.data_type <> ''
              AND LOWER(c.column_name) = ANY(:column_names)
            """
            + table_clause
        )

        try:
            with engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()
        except Exception as e:
            logger.debug("加载字段类型映射失败(table_filter=%s): %s", bool(table_filter), e)
            return []

        return [
            (str(row.column_name or "").strip(), str(row.data_type or "").strip())
            for row in rows
            if str(row.column_name or "").strip() and str(row.data_type or "").strip()
        ]

    filtered_candidates = _query_candidates(sql_tables if sql_tables else None)
    all_candidates = filtered_candidates if filtered_candidates else _query_candidates(None)
    if not all_candidates:
        return {}

    grouped: Dict[str, List[str]] = {}
    for column_name, data_type in all_candidates:
        key = _normalize_column_key(column_name)
        if key in normalized_columns:
            grouped.setdefault(key, []).append(data_type)

    mapping: Dict[str, str] = {}
    for column_key, data_types in grouped.items():
        picked = _pick_most_common_stable(data_types)
        if picked:
            mapping[column_key] = picked

    return mapping



def _build_column_display_names(columns: List[str], display_map: Dict[str, str]) -> List[str]:
    """构建结果表头显示名列表（索引与 columns 一一对应）。"""
    display_names: List[str] = []
    for column in columns:
        raw = str(column)
        if _contains_chinese(raw):
            display_names.append(raw)
            continue

        mapped = display_map.get(_normalize_column_key(raw))
        display_names.append(mapped or raw)
    return display_names


def _build_display_sql(sql: str, display_map: Dict[str, str]) -> str:
    """构建展示用 SQL（仅给未起别名的直出列补中文别名）。"""
    if not sql or not display_map:
        return sql

    try:
        import sqlglot
        from sqlglot import exp
    except Exception:
        return sql

    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
        target_select = parsed if isinstance(parsed, exp.Select) else parsed.find(exp.Select)
        if not target_select:
            return sql

        rewritten_expressions: List[Any] = []
        for expression in list(target_select.expressions or []):
            # 已存在别名保持不变（稳定优先）
            if isinstance(expression, exp.Alias):
                rewritten_expressions.append(expression)
                continue

            # 仅对未起别名的直出列补中文别名
            if isinstance(expression, exp.Column):
                column_name = str(expression.name or "").strip()
                mapped_alias = display_map.get(_normalize_column_key(column_name))
                if mapped_alias and not _contains_chinese(column_name) and mapped_alias != column_name:
                    rewritten_expressions.append(
                        exp.alias_(expression.copy(), mapped_alias, quoted=True)
                    )
                    continue

            rewritten_expressions.append(expression)

        target_select.set("expressions", rewritten_expressions)
        return parsed.sql(dialect="postgres")
    except Exception as e:
        logger.debug("构建展示 SQL 失败，回退原 SQL: %s", e)
        return sql


def _requires_detail_query(question: str, dimensions: Optional[List[str]] = None) -> bool:
    """判断用户问题是否要求明细/分组语义。"""
    dims = dimensions if isinstance(dimensions, list) else []
    if any(str(dim).strip() for dim in dims):
        return True

    normalized = re.sub(r"\s+", "", question or "")
    if not normalized:
        return False

    detail_patterns = [
        r"前\d+",                      # 前10、前20
        r"top\d+",                    # Top10
        r"排名|排行",                  # 排名/排行
        r"明细|列表",                  # 明细/列表
        r"按.+?(客户|机构|分行|支行|产品|条线|行业|地区|部门)",
        r"(各|每个).+?(客户|机构|分行|支行|产品|条线|行业|地区|部门)",
    ]
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in detail_patterns)


def _is_topn_intent(question: str) -> bool:
    """判断是否为 TopN/排名意图。"""
    normalized = re.sub(r"\s+", "", question or "")
    return bool(re.search(r"前\d+|top\d+|排名|排行", normalized, re.IGNORECASE))


def _is_total_aggregate_sql(sql: str) -> bool:
    """判断 SQL 是否为“总量聚合”模板。"""
    lowered = f" {sql.lower()} "
    has_aggregate = bool(re.search(r"\b(sum|count|avg|min|max)\s*\(", lowered))
    has_group_by = " group by " in lowered
    has_order_by = " order by " in lowered
    has_limit = " limit " in lowered
    has_window = " over(" in lowered or " over (" in lowered

    return has_aggregate and not (has_group_by or has_order_by or has_limit or has_window)


def _is_sql_semantically_compatible(
    sql: str,
    question: str,
    dimensions: Optional[List[str]] = None,
) -> bool:
    """判断候选 SQL 是否满足当前问题语义。"""
    if not sql:
        return False

    if not _requires_detail_query(question, dimensions):
        return True

    lowered = f" {sql.lower()} "

    # 明细/分组场景下，拒绝仅总量聚合 SQL（避免“第二问复用第一问结果”）
    if _is_total_aggregate_sql(sql):
        return False

    # TopN/排名问题要求具备 ORDER BY + LIMIT
    if _is_topn_intent(question):
        if " order by " not in lowered or " limit " not in lowered:
            return False

    return True


_DATA_GRAPH_INTENT_POLICY_KEY = "data_graph.intent_policy"
_DATA_GRAPH_INTENT_POLICY_CACHE_TTL_SECONDS = 60
_DATA_GRAPH_INTENT_POLICY_CACHE: Dict[str, Any] = {
    "payload": {},
    "loaded_at": 0.0,
    "source": "cold_start",
    "cache_hit": False,
}


def _get_data_graph_intent_policy_cache_meta() -> Dict[str, Any]:
    """返回当前策略缓存元信息（用于日志排障）。"""
    loaded_at = float(_DATA_GRAPH_INTENT_POLICY_CACHE.get("loaded_at") or 0.0)
    cache_age = time.time() - loaded_at if loaded_at > 0 else None
    return {
        "source": _DATA_GRAPH_INTENT_POLICY_CACHE.get("source", "unknown"),
        "cache_hit": bool(_DATA_GRAPH_INTENT_POLICY_CACHE.get("cache_hit", False)),
        "cache_age_sec": round(cache_age, 3) if cache_age is not None else None,
    }


def _load_data_graph_intent_policy(force_refresh: bool = False) -> Dict[str, Any]:
    """加载问数意图策略配置（数据库配置优先，带本地缓存）。"""
    now = time.time()
    loaded_at = float(_DATA_GRAPH_INTENT_POLICY_CACHE.get("loaded_at") or 0.0)
    if (
        not force_refresh
        and loaded_at > 0
        and now - loaded_at <= _DATA_GRAPH_INTENT_POLICY_CACHE_TTL_SECONDS
    ):
        cached_payload = _DATA_GRAPH_INTENT_POLICY_CACHE.get("payload")
        if isinstance(cached_payload, dict):
            _DATA_GRAPH_INTENT_POLICY_CACHE["cache_hit"] = True
            return cached_payload

    configured: Any = {}
    source = "default"
    try:
        from app.services.system_config_service import SystemConfigService

        configured = SystemConfigService.get(_DATA_GRAPH_INTENT_POLICY_KEY, {})
        source = "system_config"
    except Exception as error:
        logger.debug("读取 data_graph 意图策略配置失败: %s", error)
        configured = {}
        source = "system_config_error"

    if isinstance(configured, str):
        try:
            parsed = json.loads(configured)
            if isinstance(parsed, dict):
                configured = parsed
                source = "system_config_json"
            else:
                configured = {}
                source = "system_config_non_dict"
        except Exception:
            configured = {}
            source = "system_config_invalid_json"

    if not isinstance(configured, dict):
        configured = {}
        source = "default"

    _DATA_GRAPH_INTENT_POLICY_CACHE["payload"] = configured
    _DATA_GRAPH_INTENT_POLICY_CACHE["loaded_at"] = now
    _DATA_GRAPH_INTENT_POLICY_CACHE["source"] = source
    _DATA_GRAPH_INTENT_POLICY_CACHE["cache_hit"] = False
    return configured


def _extract_metric_alias_map_from_available_metrics() -> Dict[str, Tuple[str, ...]]:
    """从 AVAILABLE_METRICS 文本解析指标及同义词映射。"""
    alias_map: Dict[str, Tuple[str, ...]] = {}

    for line in AVAILABLE_METRICS.splitlines():
        raw_line = line.strip()
        if not raw_line.startswith("-"):
            continue

        item = raw_line.lstrip("-").strip()
        if not item:
            continue

        title, _, detail = item.partition(":")
        head_aliases = [segment.strip() for segment in re.split(r"/", title) if segment.strip()]
        if not head_aliases:
            continue

        canonical = head_aliases[0]
        synonyms = list(head_aliases)

        synonym_match = re.search(r"同义词[:：]([^；;。]+)", detail)
        if synonym_match:
            synonyms.extend(
                value.strip()
                for value in re.split(r"[、,，/]", synonym_match.group(1))
                if value.strip()
            )

        deduplicated: List[str] = []
        for synonym in synonyms:
            if synonym not in deduplicated:
                deduplicated.append(synonym)

        alias_map[canonical] = tuple(deduplicated)

    return alias_map


def _load_metric_synonym_groups() -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """加载指标同义词组（配置优先，未配置时回退 AVAILABLE_METRICS）。"""
    policy = _load_data_graph_intent_policy()
    configured = policy.get("metric_synonyms")

    pairs: List[Tuple[str, Tuple[str, ...]]] = []
    if isinstance(configured, dict):
        for canonical, synonyms in configured.items():
            canonical_name = str(canonical or "").strip()
            if not canonical_name:
                continue
            synonym_list = _ensure_text_list(synonyms)
            if canonical_name not in synonym_list:
                synonym_list.insert(0, canonical_name)
            if synonym_list:
                pairs.append((canonical_name, tuple(synonym_list)))

    if pairs:
        return tuple(pairs)

    return tuple(_extract_metric_alias_map_from_available_metrics().items())


def _normalize_user_message_for_intent(text: str) -> str:
    """归一化用户文本，提升多轮识别稳定性。"""
    normalized = str(text or "")
    normalized = re.sub(r"\s+", " ", normalized).strip()

    policy = _load_data_graph_intent_policy()
    normalization_map = policy.get("text_normalization_map")
    if isinstance(normalization_map, dict):
        for source, target in normalization_map.items():
            source_text = str(source or "")
            target_text = str(target or "")
            if source_text:
                normalized = normalized.replace(source_text, target_text)

    return normalized.strip()


def _ensure_text_list(value: Any) -> List[str]:
    """将输入统一为去重后的字符串列表。"""
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str):
        cleaned = [value.strip()] if value.strip() else []
    else:
        cleaned = []

    deduplicated: List[str] = []
    for item in cleaned:
        if item not in deduplicated:
            deduplicated.append(item)
    return deduplicated


def _pick_first_non_empty_str(*values: Optional[str]) -> str:
    """按优先级取首个非空字符串。"""
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _pick_first_non_empty_list(*values: Optional[List[str]]) -> List[str]:
    """按优先级取首个非空列表。"""
    for value in values:
        cleaned = _ensure_text_list(value)
        if cleaned:
            return cleaned
    return []


def _extract_metric_from_text(text: str) -> str:
    """从文本中抽取指标名称（配置/元数据驱动）。"""
    lowered = text.lower()
    best_metric = ""
    best_match_len = 0

    for canonical, synonyms in _load_metric_synonym_groups():
        for synonym in synonyms:
            normalized_synonym = str(synonym or "").strip().lower()
            if not normalized_synonym:
                continue
            if normalized_synonym in lowered and len(normalized_synonym) > best_match_len:
                best_metric = canonical
                best_match_len = len(normalized_synonym)

    return best_metric


def _extract_time_from_text(text: str) -> str:
    """从文本中抽取时间表达。"""
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return ""

    date_match = re.search(r"(\d{4})[-年/.](\d{1,2})[-月/.](\d{1,2})日?", compact)
    if date_match:
        year, month, day = date_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    yyyymmdd_match = re.search(r"(?<!\d)(\d{8})(?!\d)", compact)
    if yyyymmdd_match:
        raw = yyyymmdd_match.group(1)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"

    relative_match = re.search(
        r"(今(?:天|日)|昨天|昨日|本周|上周|本月|上月|本季度|上季度|今年|去年|(?:近|最近|过去)\d+(?:天|周|月|季度|年))",
        compact,
    )
    if relative_match:
        return relative_match.group(1)

    return ""


def _extract_chart_type_from_text(text: str) -> str:
    """从文本中抽取图表类型（配置优先）。"""
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return ""

    policy = _load_data_graph_intent_policy()
    chart_alias_map = policy.get("chart_alias_map")
    if isinstance(chart_alias_map, dict):
        for alias, canonical in chart_alias_map.items():
            alias_text = str(alias or "").strip()
            canonical_text = str(canonical or "").strip()
            if alias_text and canonical_text and alias_text in compact:
                return canonical_text

    chart_type_match = re.search(r"(柱状图|柱形图|条形图|饼图|折线图)", compact)
    if chart_type_match:
        detected = chart_type_match.group(1)
        if detected in {"柱形图", "条形图"}:
            return "柱状图"
        return detected

    if re.search(r"(图|可视化|画图|出图)", compact) and len(compact) <= 12:
        return "图表"

    return ""


def _extract_dimensions_from_text(text: str) -> List[str]:
    """从文本中抽取聚合维度（轻量规则）。"""
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return []

    if "总体" in compact or "汇总" in compact:
        return []

    dimensions: List[str] = []
    if "机构" in compact:
        dimensions.append("机构")
    if "客户" in compact:
        dimensions.append("客户")
    if any(token in compact for token in ("日期", "按天", "按月", "趋势")):
        dimensions.append("日期")
    if "分行" in compact:
        dimensions.append("分行")
    if "支行" in compact:
        dimensions.append("支行")

    return _ensure_text_list(dimensions)


def _extract_org_level_from_text(text: str) -> str:
    """从文本中抽取机构层级。"""
    compact = re.sub(r"\s+", "", text or "")
    if "支行" in compact:
        return "支行"
    if "分行" in compact:
        return "分行"
    if "总行" in compact:
        return "总行"
    return ""


def _extract_context_from_text(text: str) -> Dict[str, Any]:
    """从自由文本提取可复用上下文。"""
    normalized = _normalize_user_message_for_intent(text)
    return {
        "metric_name": _extract_metric_from_text(normalized),
        "time_range": _extract_time_from_text(normalized),
        "dimensions": _extract_dimensions_from_text(normalized),
        "chart_type": _extract_chart_type_from_text(normalized),
        "org_level": _extract_org_level_from_text(normalized),
    }


def _extract_handoff_context(state: DataAgentState) -> Dict[str, Any]:
    """从 pending_handoff 提取结构化上下文（frame 优先，文本兜底）。"""
    default_context = {
        "task_description": "",
        "metric_name": "",
        "time_range": "",
        "dimensions": [],
        "chart_type": "",
        "org_level": "",
        "filters": [],
        "turn_act_hint": "",
    }

    pending_handoff = state.get("pending_handoff")
    if not isinstance(pending_handoff, dict):
        return default_context

    task_description = str(pending_handoff.get("task_description") or "").strip()
    text_parsed = _extract_context_from_text(task_description) if task_description else {}

    context = dict(default_context)
    context["task_description"] = task_description

    handoff_frame = pending_handoff.get("frame")
    if isinstance(handoff_frame, dict):
        context["metric_name"] = _pick_first_non_empty_str(
            handoff_frame.get("metric"),
            handoff_frame.get("metric_name"),
        )
        context["time_range"] = _pick_first_non_empty_str(
            handoff_frame.get("time_range"),
        )
        context["dimensions"] = _pick_first_non_empty_list(
            _ensure_text_list(handoff_frame.get("dimensions")),
        )
        context["chart_type"] = _pick_first_non_empty_str(
            handoff_frame.get("chart_type"),
        )
        context["org_level"] = _pick_first_non_empty_str(
            handoff_frame.get("org_level"),
        )
        context["filters"] = _pick_first_non_empty_list(
            _ensure_text_list(handoff_frame.get("filters")),
        )
        context["turn_act_hint"] = str(
            pending_handoff.get("turn_act_hint")
            or handoff_frame.get("turn_act_hint")
            or ""
        ).strip()
        return context

    if task_description:
        context["metric_name"] = str(text_parsed.get("metric_name") or "").strip()
        context["time_range"] = str(text_parsed.get("time_range") or "").strip()
        context["dimensions"] = _ensure_text_list(text_parsed.get("dimensions"))
        context["chart_type"] = str(text_parsed.get("chart_type") or "").strip()
        context["org_level"] = str(text_parsed.get("org_level") or "").strip()

    return context


def _is_continuation_reply(
    text: str,
    *,
    has_prior_context: bool = False,
    existing_metric: str = "",
    handoff_metric: str = "",
    existing_time: str = "",
    handoff_time: str = "",
    existing_dims: Optional[List[str]] = None,
    handoff_dims: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """判断当前轮是否是补充型短回复，并返回判定原因。"""
    compact = re.sub(r"\s+", "", _normalize_user_message_for_intent(text))
    if not compact:
        return False, "empty_input"
    if not has_prior_context:
        return False, "no_prior_context"
    if len(compact) > 50:
        return False, "too_long"

    policy = _load_data_graph_intent_policy()
    current_context = _extract_context_from_text(compact)

    baseline_frame = {
        "metric": _pick_first_non_empty_str(existing_metric, handoff_metric),
        "time_range": _pick_first_non_empty_str(existing_time, handoff_time),
        "dimensions": _pick_first_non_empty_list(existing_dims, handoff_dims),
    }
    current_frame = {
        "metric": str(current_context.get("metric_name") or "").strip(),
        "time_range": str(current_context.get("time_range") or "").strip(),
        "dimensions": _ensure_text_list(current_context.get("dimensions")),
        "chart_type": str(current_context.get("chart_type") or "").strip(),
        "org_level": str(current_context.get("org_level") or "").strip(),
    }

    turn_act, reason = classify_turn_act(
        compact,
        has_prior_context=has_prior_context,
        baseline_frame=baseline_frame,
        current_frame=current_frame,
        policy=policy,
    )

    if turn_act in {TURN_ACT_SUPPLEMENT, TURN_ACT_CONFIRM}:
        return True, reason
    return False, reason


def _infer_clarify_slot(clarification: str) -> str:
    """根据澄清文案推断澄清槽位。"""
    compact = re.sub(r"\s+", "", clarification or "")
    if not compact:
        return ""
    if any(
        keyword in compact
        for keyword in ("图表", "可视化", "柱状图", "柱形图", "条形图", "饼图", "折线图", "明细", "占比", "列表")
    ):
        return "display_mode"
    if "指标" in compact and "时间" in compact:
        return "metric_time"
    if "指标" in compact:
        return "metric"
    if "时间" in compact:
        return "time_range"
    if any(keyword in compact for keyword in ("层级", "分行", "支行")):
        return "org_level"
    return "general"


def _normalize_clarify_level(value: Any) -> str:
    """标准化澄清级别：required|optional。"""
    token = str(value or "").strip().lower()
    if not token:
        return ""

    if token in {"required", "mandatory", "must", "必需", "必须"}:
        return "required"
    if token in {"optional", "suggested", "preference", "可选", "建议"}:
        return "optional"
    return ""


def _build_clarification_message(missing_slots: List[str]) -> str:
    """按缺失槽位生成最小化澄清问题。"""
    missing = set(missing_slots)
    if "metric" in missing and "time_range" in missing:
        return "请补充查询指标和时间范围（例如：查询2025-06-30贷款余额）。"
    if "metric" in missing:
        return "请补充要查询的指标（例如：贷款余额、存款余额）。"
    if "time_range" in missing:
        return "请补充时间范围（例如：2025-06-30、本月、过去30天）。"
    if "org_level" in missing:
        return "请确认机构层级（分行或支行）；未指定时默认按分行。"
    return "请补充查询所需的关键信息。"


def _is_schema_metadata_query(text: str) -> bool:
    """识别“表/字段/schema”类元数据查询，避免误追问指标与时间。"""
    compact = re.sub(r"\s+", "", str(text or "")).lower()
    if not compact:
        return False

    # 显式 schema/元数据关键词
    metadata_keywords = (
        "schema",
        "information_schema",
        "元数据",
        "表结构",
        "字段",
        "列名",
        "数据字典",
        "showtables",
        "showtable",
        "describe",
        "desc",
        "ddl",
    )
    if any(keyword in compact for keyword in metadata_keywords):
        return True

    sanitized = compact.replace("图表", "").replace("报表", "")
    metadata_patterns = (
        r"(几张|多少张|多少个|哪些|有哪些|有什么).{0,6}表",
        r"(表名|表列表|所有表)",
        r"(有几列|多少列|字段有哪些|列有哪些|字段列表)",
    )
    return any(re.search(pattern, sanitized) for pattern in metadata_patterns)


def _resolve_clarification(
    *,
    analysis_clarification: str,
    analysis_clarify_level: str,
    merged_metric: str,
    merged_time: str,
    need_org_level: bool,
    merged_org_level: str,
    require_metric_time_slots: bool,
    allow_metric_time_analysis_clarify: bool,
    continuation_mode: bool,
    last_clarify_slot: str,
    clarify_count: int,
) -> Tuple[Optional[str], Optional[str], int, str]:
    """按缺项驱动澄清，并做重复澄清保护。"""
    missing_slots: List[str] = []
    if require_metric_time_slots:
        if not merged_metric:
            missing_slots.append("metric")
        if not merged_time:
            missing_slots.append("time_range")
    if need_org_level and not merged_org_level:
        missing_slots.append("org_level")

    if missing_slots:
        slot = "metric_time" if {"metric", "time_range"}.issubset(set(missing_slots)) else missing_slots[0]
        message = _build_clarification_message(missing_slots)
        reason = f"missing_slots:{','.join(missing_slots)}"
        return message, slot, max(clarify_count, 0) + 1, reason

    clarification = str(analysis_clarification or "").strip()
    if not clarification:
        return None, None, 0, "no_clarification_needed"

    clarify_level = _normalize_clarify_level(analysis_clarify_level)
    if clarify_level == "optional":
        return None, None, 0, "skip_optional_clarify_level"

    analysis_slot = _infer_clarify_slot(clarification)

    if not allow_metric_time_analysis_clarify and analysis_slot in {"metric", "time_range", "metric_time"}:
        return None, None, 0, "skip_metric_time_clarify_for_metadata_query"

    # 重复澄清保护：上一轮已问展示方式，本轮补充后不再追问指标/时间
    if continuation_mode and last_clarify_slot == "display_mode":
        if analysis_slot in {"metric", "time_range", "metric_time", "general"}:
            return None, None, 0, "skip_redundant_clarify_after_display_mode"

    # 已具备关键槽位时，拒绝模型回退成全量追问
    if analysis_slot in {"metric", "time_range", "metric_time"} and merged_metric and merged_time:
        return None, None, 0, "skip_redundant_metric_time_clarify"

    if analysis_slot == "org_level" and merged_org_level:
        return None, None, 0, "skip_redundant_org_level_clarify"

    return clarification, analysis_slot or "general", max(clarify_count, 0) + 1, f"analysis:{analysis_slot or 'general'}"

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

    normalized_last_message = _normalize_user_message_for_intent(str(last_message))
    continuation_mode = False
    turn_act = TURN_ACT_NEW_QUERY

    # 多轮上下文：state + handoff 融合
    query_context = state.get("query_context") or {}
    if not isinstance(query_context, dict):
        query_context = {}

    session_frame = state.get("session_frame")
    if not isinstance(session_frame, dict):
        session_frame = {}

    # 关键：在 MultiAgent 父图中，data 专有字段（matched_metric/time_range）可能被 schema 裁剪；
    # 这里优先回收 session_frame 中的同义槽位，保证“生成图表”这类补充轮能继承上一轮信息。
    session_metric = _pick_first_non_empty_str(
        session_frame.get("metric"),
        session_frame.get("metric_name"),
    )
    session_time = _pick_first_non_empty_str(session_frame.get("time_range"))
    session_dims = _ensure_text_list(session_frame.get("dimensions"))
    session_filters = _ensure_text_list(session_frame.get("filters"))
    session_chart_type = _pick_first_non_empty_str(session_frame.get("chart_type"))
    session_org_level = _pick_first_non_empty_str(session_frame.get("org_level"))

    existing_metric = _pick_first_non_empty_str(state.get("matched_metric"), session_metric)
    existing_time = _pick_first_non_empty_str(state.get("time_range"), session_time)
    existing_dims = _pick_first_non_empty_list(
        _ensure_text_list(state.get("dimensions")),
        session_dims,
    )
    existing_filters = _pick_first_non_empty_list(
        _ensure_text_list(state.get("filters")),
        session_filters,
    )
    existing_viz_type = _pick_first_non_empty_str(state.get("viz_type"), session_chart_type)
    existing_org_level = _pick_first_non_empty_str(query_context.get("org_level"), session_org_level)
    existing_query_question = str(query_context.get("original_question") or "").strip()

    handoff_context = _extract_handoff_context(state)
    handoff_metric = str(handoff_context.get("metric_name") or "").strip()
    handoff_time = str(handoff_context.get("time_range") or "").strip()
    handoff_dims = _ensure_text_list(handoff_context.get("dimensions"))
    handoff_filters = _ensure_text_list(handoff_context.get("filters"))
    handoff_chart_type = str(handoff_context.get("chart_type") or "").strip()
    handoff_org_level = str(handoff_context.get("org_level") or "").strip()
    handoff_task_description = str(handoff_context.get("task_description") or "").strip()
    handoff_turn_act_hint = str(handoff_context.get("turn_act_hint") or "").strip()

    has_state_context = any([
        existing_metric,
        existing_time,
        existing_dims,
        existing_filters,
        existing_query_question,
    ])

    has_handoff_context = any([
        handoff_metric,
        handoff_time,
        handoff_dims,
        handoff_filters,
        handoff_task_description,
    ])

    has_clarify_history = bool(str(state.get("last_clarify_slot") or "").strip()) or int(state.get("clarify_count") or 0) > 0
    allow_handoff_as_prior = handoff_turn_act_hint in {
        TURN_ACT_SUPPLEMENT,
        TURN_ACT_CONFIRM,
        TURN_ACT_CORRECTION,
    }
    if not handoff_turn_act_hint and has_clarify_history:
        allow_handoff_as_prior = True

    has_prior_context = has_state_context or (has_handoff_context and allow_handoff_as_prior)

    continuation_mode, continuation_reason = _is_continuation_reply(
        normalized_last_message,
        has_prior_context=bool(has_prior_context),
        existing_metric=existing_metric,
        handoff_metric=handoff_metric,
        existing_time=existing_time,
        handoff_time=handoff_time,
        existing_dims=existing_dims,
        handoff_dims=handoff_dims,
    )

    if continuation_mode:
        turn_act = TURN_ACT_CONFIRM if continuation_reason in {"policy_confirm_pattern", "short_confirm"} else TURN_ACT_SUPPLEMENT
    elif continuation_reason in {"metric_switched", "time_switched"}:
        turn_act = TURN_ACT_CORRECTION
    else:
        turn_act = TURN_ACT_NEW_QUERY

    if (
        handoff_turn_act_hint == TURN_ACT_NEW_QUERY
        and not has_state_context
        and continuation_mode
    ):
        continuation_mode = False
        continuation_reason = "handoff_new_query_hint"
        turn_act = TURN_ACT_NEW_QUERY

    if (
        not continuation_mode
        and turn_act == TURN_ACT_NEW_QUERY
        and continuation_reason in {"insufficient_signal", "short_reply_with_context"}
        and handoff_turn_act_hint == TURN_ACT_SUPPLEMENT
        and has_prior_context
    ):
        turn_act = TURN_ACT_SUPPLEMENT
        continuation_mode = True
        continuation_reason = "handoff_turn_act_hint"

    policy_meta = _get_data_graph_intent_policy_cache_meta()

    existing_dims_str = "、".join(existing_dims) if existing_dims else ""
    existing_filters_str = "、".join(existing_filters) if existing_filters else ""
    parts = []
    baseline_metric = _pick_first_non_empty_str(existing_metric, handoff_metric)
    baseline_time = _pick_first_non_empty_str(existing_time, handoff_time)
    baseline_dims = _pick_first_non_empty_list(existing_dims, handoff_dims)
    if baseline_metric:
        parts.append(f"指标: {baseline_metric}")
    if baseline_time:
        parts.append(f"时间范围: {baseline_time}")
    if baseline_dims:
        parts.append(f"聚合维度: {'、'.join(baseline_dims)}")
    if existing_filters_str:
        parts.append(f"筛选: {existing_filters_str}")
    if handoff_task_description:
        handoff_summary = handoff_task_description.replace("\n", " ")[:180]
        parts.append(f"handoff: {handoff_summary}")
    existing_context = "；".join(parts) if parts else "（无，为首轮或尚未提供）"

    # 调用 LLM 分析意图（internal=True 自动禁用流式 + 添加 tag，防止 JSON 泄露）
    # 使用 SQL 生成/内部分析 路由配置的模型，避免推理模型浪费 thinking tokens
    llm = get_scene_llm(
        scene_key=SCENE_KEY_DATA_INTENT_ANALYSIS,
        internal=True,
    )
    prompt = DATA_INTENT_ANALYSIS_PROMPT.format(
        question=normalized_last_message,
        existing_context=existing_context,
        available_metrics=AVAILABLE_METRICS
    )

    try:
        response = llm.invoke(prompt)
        content = _normalize_text_content(
            response.content if hasattr(response, "content") else response
        )

        # 解析 JSON 响应
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            analysis = json.loads(content[json_start:json_end])
        else:
            analysis = {"intent": "free_query"}

        logger.info(f"意图分析结果: {analysis}")

        current_context = _extract_context_from_text(normalized_last_message)

        # 当前轮解析结果（优先使用 LLM；无值时由规则补齐）
        current_metric = _pick_first_non_empty_str(
            analysis.get("metric_name"),
            current_context.get("metric_name"),
        )
        current_time = _pick_first_non_empty_str(
            analysis.get("time_range"),
            current_context.get("time_range"),
        )
        current_dims = _pick_first_non_empty_list(
            _ensure_text_list(analysis.get("dimensions")),
            _ensure_text_list(current_context.get("dimensions")),
        )
        current_filters = _ensure_text_list(analysis.get("filters"))
        current_chart_type = _pick_first_non_empty_str(
            analysis.get("chart_type"),
            current_context.get("chart_type"),
        )
        current_org_level = _pick_first_non_empty_str(current_context.get("org_level"))

        # 会话帧归并：当前轮 > handoff > 历史 state
        current_frame = {
            "metric": current_metric,
            "time_range": current_time,
            "dimensions": current_dims,
            "filters": current_filters,
            "chart_type": current_chart_type,
            "org_level": current_org_level,
        }
        handoff_frame = {
            "metric": handoff_metric,
            "time_range": handoff_time,
            "dimensions": handoff_dims,
            "filters": handoff_filters,
            "chart_type": handoff_chart_type,
            "org_level": handoff_org_level,
        }
        state_frame = {
            "metric": existing_metric,
            "time_range": existing_time,
            "dimensions": existing_dims,
            "filters": existing_filters,
            "chart_type": existing_viz_type,
            "org_level": existing_org_level,
        }

        merged_frame, frame_source_map = reduce_session_frame(
            current_frame=current_frame,
            handoff_frame=handoff_frame,
            state_frame=state_frame,
        )
        merged_metric = str(merged_frame.get("metric") or "").strip()
        merged_time = str(merged_frame.get("time_range") or "").strip()
        merged_dims = _ensure_text_list(merged_frame.get("dimensions"))
        merged_filters = _ensure_text_list(merged_frame.get("filters"))
        merged_chart_type = str(merged_frame.get("chart_type") or "").strip()
        merged_org_level = str(merged_frame.get("org_level") or "").strip()

        # 新问题保护：识别到指标切换且非补充模式时，避免继承旧上下文
        baseline_metric_for_switch = _pick_first_non_empty_str(existing_metric, handoff_metric)
        context_reset_for_new_query = bool(
            current_metric
            and baseline_metric_for_switch
            and current_metric != baseline_metric_for_switch
            and turn_act in {TURN_ACT_NEW_QUERY, TURN_ACT_CORRECTION}
            and not continuation_mode
        )
        if context_reset_for_new_query:
            merged_metric = current_metric
            merged_time = current_time
            merged_dims = current_dims
            merged_filters = current_filters
            merged_chart_type = current_chart_type
            merged_org_level = current_org_level
            frame_source_map.update(
                {
                    "metric": "current",
                    "time_range": "current",
                    "dimensions": "current",
                    "filters": "current",
                    "chart_type": "current",
                    "org_level": "current",
                }
            )
            logger.info(
                "意图融合: 识别为新问题，重置历史继承(metric=%s->%s)",
                baseline_metric_for_switch,
                current_metric,
            )

        combined_text_parts = [normalized_last_message, " ".join(merged_dims)]
        if not context_reset_for_new_query:
            combined_text_parts.insert(1, handoff_task_description)
        combined_text = " ".join([part for part in combined_text_parts if part])
        compact_combined_text = re.sub(r"\s+", "", combined_text)
        org_dimension_requested = any(
            keyword in compact_combined_text for keyword in ("机构", "分行", "支行")
        )
        has_chart_request = bool(merged_chart_type) or any(
            keyword in compact_combined_text for keyword in ("图表", "柱状图", "饼图", "折线图", "可视化", "出图")
        )

        # 默认值策略：图表场景未指定层级时默认分行
        used_default_org_level = False
        if has_chart_request and org_dimension_requested and not merged_org_level:
            merged_org_level = "分行"
            used_default_org_level = True

        is_schema_metadata_query = _is_schema_metadata_query(normalized_last_message)
        require_metric_time_slots = not is_schema_metadata_query
        allow_metric_time_analysis_clarify = not is_schema_metadata_query

        previous_clarify_slot = str(state.get("last_clarify_slot") or "").strip()
        previous_clarify_count = int(state.get("clarify_count") or 0)
        previous_clarify_fsm_state = str(state.get("clarify_fsm_state") or "idle").strip() or "idle"
        previous_clarify_round = int(state.get("clarify_round") or previous_clarify_count or 0)
        clarification, clarify_slot, clarified_count, clarify_reason = _resolve_clarification(
            analysis_clarification=str(analysis.get("clarification_needed") or ""),
            analysis_clarify_level=str(analysis.get("clarify_level") or ""),
            merged_metric=merged_metric,
            merged_time=merged_time,
            need_org_level=has_chart_request and org_dimension_requested and not bool(merged_org_level),
            merged_org_level=merged_org_level,
            require_metric_time_slots=require_metric_time_slots,
            allow_metric_time_analysis_clarify=allow_metric_time_analysis_clarify,
            continuation_mode=continuation_mode,
            last_clarify_slot=previous_clarify_slot,
            clarify_count=previous_clarify_count,
        )

        missing_slots_for_fsm: List[str] = []
        if require_metric_time_slots:
            if not merged_metric:
                missing_slots_for_fsm.append("metric")
            if not merged_time:
                missing_slots_for_fsm.append("time_range")
        if has_chart_request and org_dimension_requested and not bool(merged_org_level):
            missing_slots_for_fsm.append("org_level")

        if clarification:
            next_clarify_slot = clarify_slot
            next_clarify_count = clarified_count
            next_clarify_fsm_state = advance_clarify_fsm_state(previous_clarify_fsm_state, missing_slots_for_fsm)
            next_clarify_round = max(previous_clarify_round, 0) + 1
        else:
            next_clarify_slot = None
            next_clarify_count = 0
            next_clarify_fsm_state = "done"
            next_clarify_round = 0

        # 是否实际消费了 handoff 上下文（用于日志和排障）
        used_handoff_context = False
        if handoff_task_description and not context_reset_for_new_query:
            if (not current_metric and handoff_metric) or (not current_time and handoff_time):
                used_handoff_context = True
            elif not current_dims and handoff_dims:
                used_handoff_context = True
            elif not current_chart_type and handoff_chart_type:
                used_handoff_context = True
            elif not current_org_level and handoff_org_level:
                used_handoff_context = True

        # 为 SQL 生成构造完整查询描述（多轮合并后的语义）
        full_question = normalized_last_message
        parts_desc = []
        if merged_metric:
            parts_desc.append(f"查询{merged_metric}")
        if merged_time:
            parts_desc.append(f"时间范围{merged_time}")
        if merged_dims:
            parts_desc.append(f"按{'、'.join(merged_dims)}聚合")
        if merged_org_level and org_dimension_requested and merged_org_level not in merged_dims:
            parts_desc.append(f"机构层级{merged_org_level}")
        if merged_chart_type:
            parts_desc.append(f"展示方式{merged_chart_type}")
        if merged_filters:
            parts_desc.append(f"筛选{'、'.join(merged_filters)}")

        if parts_desc:
            merged_desc = "，".join(parts_desc)
            if continuation_mode:
                full_question = merged_desc
            else:
                full_question = f"{merged_desc}。用户补充：{normalized_last_message}"

        analysis_intent = str(analysis.get("intent") or "free_query").strip() or "free_query"
        resolved_intent = analysis_intent
        if clarification:
            resolved_intent = "clarification"
        elif merged_metric:
            resolved_intent = "metric_query"
        elif has_chart_request or analysis_intent == "visualization":
            resolved_intent = "visualization"
        elif analysis_intent == "clarification":
            resolved_intent = "free_query"

        resolved_session_frame = {
            "metric": merged_metric,
            "time_range": merged_time,
            "dimensions": merged_dims,
            "filters": merged_filters,
            "chart_type": merged_chart_type,
            "org_level": merged_org_level,
        }

        logger.info(
            "意图融合: turn_act=%s, continuation=%s(reason=%s), used_handoff_context=%s, "
            "used_default_org_level=%s, clarify_reason=%s, clarify_fsm=%s, reset_for_new_query=%s, "
            "schema_metadata_query=%s, policy_source=%s, policy_cache_hit=%s, policy_cache_age_sec=%s",
            turn_act,
            continuation_mode,
            continuation_reason,
            used_handoff_context,
            used_default_org_level,
            clarify_reason,
            next_clarify_fsm_state,
            context_reset_for_new_query,
            is_schema_metadata_query,
            policy_meta.get("source"),
            policy_meta.get("cache_hit"),
            policy_meta.get("cache_age_sec"),
        )

        updates = {
            "data_intent": resolved_intent,
            "matched_metric": merged_metric or None,
            "time_range": merged_time or None,
            "filters": merged_filters,
            "dimensions": merged_dims,
            "viz_type": merged_chart_type or None,
            "clarification_needed": clarification or None,
            "last_clarify_slot": next_clarify_slot,
            "clarify_count": next_clarify_count,
            "continuation_mode": continuation_mode,
            "turn_act": turn_act,
            "session_frame": resolved_session_frame,
            "frame_source_map": frame_source_map,
            "clarify_fsm_state": next_clarify_fsm_state,
            "clarify_round": next_clarify_round,
            "query_context": {
                "original_question": full_question,
                "last_user_message": normalized_last_message,
                "analysis": analysis,
                "org_level": merged_org_level or None,
                "continuation_mode": continuation_mode,
                "continuation_reason": continuation_reason,
                "turn_act": turn_act,
                "frame_source_map": frame_source_map,
                "used_handoff_context": used_handoff_context,
                "used_default_org_level": used_default_org_level,
                "clarify_reason": clarify_reason,
                "clarify_fsm_state": next_clarify_fsm_state,
                "clarify_round": next_clarify_round,
                "is_schema_metadata_query": is_schema_metadata_query,
                "context_reset_for_new_query": context_reset_for_new_query,
                "intent_policy_source": policy_meta.get("source"),
                "intent_policy_cache_hit": policy_meta.get("cache_hit"),
                "intent_policy_cache_age_sec": policy_meta.get("cache_age_sec"),
                "handoff_task_description": handoff_task_description or None,
                "handoff_turn_act_hint": handoff_turn_act_hint or None,
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
    """指标匹配：精确名称匹配 + 向量检索 t_metric_definition，命中则直接用 query_template。
    
    职责：
    1. 优先精确名称匹配（避免语义漂移，如"贷款余额"不应匹配"个人贷款"）
    2. 精确匹配未命中时，向量检索数据库中的指标定义
    3. 命中且有 query_template 时，直接生成 SQL（跳过 LLM 生成，节省 Token）
    4. 未命中则回退到 Vanna RAG 路径
    
    改造记录：
    - 2026-02-07: 从硬编码电商模板改为数据库向量匹配 (ADR-011)
    - 2026-02-07: 增加精确名称匹配优先步骤 + 空结果降级机制
    """
    logger.info("=== metric_resolve 节点 ===")
    
    query_context = state.get("query_context", {})
    question = query_context.get("original_question", "")
    matched_metric = state.get("matched_metric")
    time_range = state.get("time_range")
    dimensions = state.get("dimensions")
    if not isinstance(dimensions, list):
        dimensions = []
    
    if not question and not matched_metric:
        return {"sql_source": "vanna"}
    
    try:
        # 第1步：精确名称匹配（优先于向量检索，避免语义漂移）
        if matched_metric:
            exact_candidates = _search_metrics_exact_name(matched_metric)
            if exact_candidates:
                for best in exact_candidates:
                    query_template = best.get("query_template")
                    if not query_template:
                        logger.info(
                            "指标精确匹配命中但无 query_template: %s",
                            best.get("metric_id")
                        )
                        continue

                    sql = _derive_metric_sql(query_template, time_range, question, dimensions)
                    if not sql:
                        logger.info(
                            "指标精确模板无法派生当前语义，跳过: %s (%s)",
                            best.get("metric_id"), best.get("metric_name")
                        )
                        continue
                    if not _is_sql_semantically_compatible(sql, question, dimensions):
                        logger.info(
                            "指标精确模板语义不匹配，跳过: %s (%s)",
                            best.get("metric_id"), best.get("metric_name")
                        )
                        continue

                    logger.info(
                        "指标精确匹配命中: %s (%s), SQL=%s...",
                        best.get("metric_id"), best.get("metric_name"), sql[:80]
                    )
                    return {
                        "generated_sql": sql,
                        "sql_source": "metric",
                        "pending_sql": sql,
                        "matched_metric": best.get("metric_name"),
                    }

                logger.info("指标精确匹配存在候选，但均不满足当前语义，继续向量检索")
        
        # 第2步：向量检索 query_template 非空的指标
        vanna = get_vanna()
        candidates = _search_metrics_by_vector(
            vanna, question or matched_metric, top_k=3
        )
        
        if not candidates:
            logger.info("指标向量匹配: 无命中，回退到 Vanna")
            return {"sql_source": "vanna"}

        # 相似度阈值：> 0.5 才使用模板（实测银行指标匹配多在 0.55-0.65 区间）
        for best in candidates:
            similarity = best.get("similarity", 0)
            if similarity < 0.5:
                continue

            query_template = best.get("query_template")
            if not query_template:
                logger.info(
                    "指标命中但无 query_template: %s，跳过",
                    best.get("metric_id")
                )
                continue

            sql = _derive_metric_sql(query_template, time_range, question, dimensions)
            if not sql:
                logger.info(
                    "指标向量模板无法派生当前语义，跳过: %s (%s), 相似度=%.3f",
                    best.get("metric_id"), best.get("metric_name"), similarity
                )
                continue
            if not _is_sql_semantically_compatible(sql, question, dimensions):
                logger.info(
                    "指标向量模板语义不匹配，跳过: %s (%s), 相似度=%.3f",
                    best.get("metric_id"), best.get("metric_name"), similarity
                )
                continue

            logger.info(
                "指标向量匹配命中: %s (%s), 相似度=%.3f, SQL=%s...",
                best.get("metric_id"), best.get("metric_name"),
                similarity, sql[:80]
            )

            return {
                "generated_sql": sql,
                "sql_source": "metric",
                "pending_sql": sql,
                "matched_metric": best.get("metric_name"),
            }

        logger.info("指标向量命中但无语义匹配模板，回退到 Vanna")
        return {"sql_source": "vanna"}
        
    except Exception as e:
        logger.warning("指标匹配异常，回退到 Vanna: %s", e)
        return {"sql_source": "vanna"}


def _search_metrics_exact_name(metric_name: str) -> list:
    """精确名称匹配指标（优先于向量检索，避免语义漂移）。
    
    匹配策略（按优先级）：
    1. 完全匹配 metric_name（如"贷款余额"精确匹配 LOAN_001）
    2. 用户关键词被 metric_name 包含（如"贷款余额"匹配"全行贷款余额"）
    
    排序规则：精确匹配优先 → 名称更短的优先（更具体）
    """
    from sqlalchemy import create_engine, text
    
    sql = text("""
        SELECT metric_id, metric_name, description,
               query_template, template_source,
               CASE 
                   WHEN metric_name = :name THEN 1.0
                   WHEN metric_name LIKE '%' || :name || '%' THEN 0.9
               END AS match_score
        FROM t_metric_definition
        WHERE is_active = TRUE
          AND query_template IS NOT NULL
          AND (metric_name = :name OR metric_name LIKE '%' || :name || '%')
        ORDER BY match_score DESC, LENGTH(metric_name) ASC
        LIMIT 5
    """)
    
    try:
        from app.core.config import DATABASE_URL
        with create_engine(DATABASE_URL).connect() as conn:
            rows = conn.execute(sql, {"name": metric_name}).fetchall()
        
        return [
            {
                "metric_id": r.metric_id,
                "metric_name": r.metric_name,
                "description": r.description,
                "query_template": r.query_template,
                "template_source": r.template_source,
                "similarity": r.match_score,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("指标精确匹配查询失败: %s", e)
        return []


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
    raw = time_range.strip()
    
    # 直接日期格式: 2025-06-30 或 20250630
    m = re.search(r'(\d{4})-?(\d{2})-?(\d{2})', raw)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    
    # 月末日期推断
    if "上月" in raw or "上个月" in raw:
        first_of_month = now.replace(day=1)
        last_of_prev = first_of_month - timedelta(days=1)
        return last_of_prev.strftime("%Y%m%d")
    
    if "本月" in raw or "这个月" in raw:
        return now.strftime("%Y%m%d")
    
    # 年月: "6月" "2025年6月"
    m = re.search(r'(\d{4})年?(\d{1,2})月', raw)
    if m:
        import calendar
        year, month = int(m.group(1)), int(m.group(2))
        last_day = calendar.monthrange(year, month)[1]
        return f"{year}{month:02d}{last_day:02d}"
    
    m = re.search(r'(\d{1,2})月', raw)
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


def training_sql_resolve(state: DataAgentState) -> Dict:
    """训练集 SQL 匹配：从 t_data_query_log 向量检索已训练的 SQL，直接执行。
    
    三级降级链中的第2级：
    1. 向量检索 t_data_query_log 中 trained=true 的记录
    2. 相似度 > 0.7 时直接使用训练集 SQL（跳过 LLM 生成）
    3. 替换日期参数后进入安全检查
    4. 未命中则回退到第3级（通用 RAG 路径）
    """
    logger.info("=== training_sql_resolve 节点 ===")
    
    query_context = state.get("query_context", {})
    question = query_context.get("original_question", "")
    time_range = state.get("time_range")
    dimensions = state.get("dimensions")
    if not isinstance(dimensions, list):
        dimensions = []
    
    # 清除上一级的降级标志，防止循环
    base_result = {"fallback_target": None}
    
    if not question:
        return {**base_result, "sql_source": "vanna"}
    
    try:
        vanna = get_vanna()
        candidates = _search_training_sql(vanna, question, top_k=3)
        
        if not candidates:
            logger.info("训练集 SQL 匹配: 无命中，回退到通用查询")
            return {**base_result, "sql_source": "vanna"}

        # 相似度阈值 0.7（训练集 SQL 需要更高置信度才能直接执行）
        for best in candidates:
            similarity = best.get("similarity", 0)
            if similarity < 0.7:
                continue

            training_sql = best.get("generated_sql")
            if not training_sql:
                continue

            # 替换日期参数
            sql = _replace_data_dt(training_sql, time_range)
            if not _is_sql_semantically_compatible(sql, question, dimensions):
                logger.info(
                    "训练集 SQL 语义不匹配，跳过: sim=%.3f, 样本问题='%s'",
                    similarity, best.get("question", "")[:50]
                )
                continue

            logger.info(
                "训练集 SQL 命中: 原始问题='%s', 相似度=%.3f, SQL=%s...",
                best.get("question", "")[:50], similarity, sql[:80]
            )

            return {
                **base_result,
                "generated_sql": sql,
                "sql_source": "training",
                "pending_sql": sql,
            }

        logger.info("训练集 SQL 命中但无语义匹配候选，回退到通用查询")
        return {**base_result, "sql_source": "vanna"}
        
    except Exception as e:
        logger.warning("训练集 SQL 匹配异常，回退到通用查询: %s", e)
        return {**base_result, "sql_source": "vanna"}


def _search_training_sql(vanna, question: str, top_k: int = 3) -> list:
    """从 t_data_query_log 向量检索已训练的 SQL。
    
    只返回 trained=true 且有 embedding 的记录，按相似度降序排列。
    """
    from sqlalchemy import create_engine, text
    
    embedding = vanna.generate_embedding(question)
    if not embedding:
        return []
    
    embedding_str = str(embedding)
    
    sql = text("""
        SELECT question, generated_sql,
               1 - (question_embedding <=> :embedding) AS similarity
        FROM t_data_query_log
        WHERE trained = true
          AND question_embedding IS NOT NULL
          AND generated_sql IS NOT NULL
        ORDER BY question_embedding <=> :embedding
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
                "question": r.question,
                "generated_sql": r.generated_sql,
                "similarity": r.similarity,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("训练集 SQL 检索失败: %s", e)
        return []


def schema_retrieve(state: DataAgentState) -> Dict:
    """检索相关表结构（Vanna RAG）。
    
    三级降级链中的第3级：
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
        # 清除降级标志，防止循环
        return {
            "retrieved_schema": retrieved_schema,
            "target_schema": target_schema,
            "fallback_target": None
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
        response = vanna.submit_prompt(
            messages,
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
                    
                    judge_result = evaluate_sql_response_sync(sql, "待执行")
                    
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
    
    使用统一策略决策模块，执行：
    1. 是否为只读查询
    2. 是否包含危险操作关键词
    3. 是否访问敏感表
    4. Schema 白名单/黑名单检查
    5. 用户权限重写（表级、行级、列级）
    6. 自动添加 LIMIT 防止超大结果集
    """
    logger.info("=== sql_safety_check 节点 ===")
    
    from app.ai.utils.sql_policy_decision import evaluate_sql_policy
    
    sql = state.get("pending_sql") or state.get("generated_sql")
    if not sql:
        return {}

    query_context = state.get("query_context")
    if isinstance(query_context, dict):
        updated_query_context = dict(query_context)
    else:
        updated_query_context = {}
    
    user_id = state.get("user_id")
    decision = evaluate_sql_policy(sql, user_id=user_id, auto_limit=True, limit=1000)
    if user_id:
        updated_query_context["permission_checked"] = True
        updated_query_context["permission_rewritten"] = bool(getattr(decision, "permission_rewritten", False))
        scope_summary = getattr(decision, "permission_scope_summary", None)
        if isinstance(scope_summary, dict):
            updated_query_context["permission_scope_summary"] = scope_summary
        updated_query_context["sql_policy_reason_code"] = decision.reason_code

    if not decision.is_allowed:
        logger.warning(
            "SQL 策略决策拒绝: stage=%s, code=%s, reason=%s",
            decision.denied_stage,
            decision.reason_code,
            decision.reason,
        )
        return {
            "clarification_needed": f"查询被拒绝：{decision.reason}",
            "last_error": decision.reason,
            "pending_sql": None,
            "query_context": updated_query_context,
        }

    processed_sql = decision.rewritten_sql

    # 如果 SQL 被修改（添加 LIMIT 或权限重写），更新状态
    if processed_sql != sql:
        logger.info("SQL 已通过策略决策重写: 原始长度=%s, 新长度=%s", len(sql), len(processed_sql))
        return {
            "generated_sql": processed_sql,
            "pending_sql": processed_sql,
            "sql_approved": True,
            "query_context": updated_query_context,
        }

    return {
        "sql_approved": True,
        "query_context": updated_query_context,
    }


def _is_chart_requested(state: DataAgentState) -> bool:
    """判断当前查询是否包含图表诉求。"""
    intent = str(state.get("data_intent") or "").strip().lower()
    viz_type = str(state.get("viz_type") or "").strip()
    return intent == "visualization" or bool(viz_type)


def _resolve_chart_type(viz_type: str, columns: List[str], rows: List[Dict[str, Any]]) -> str:
    """将图表类型归一化为前端可识别枚举。"""
    normalized_viz = re.sub(r"\s+", "", str(viz_type or "")).lower()

    alias_map = {
        "柱状图": "bar",
        "柱形图": "bar",
        "条形图": "bar",
        "bar": "bar",
        "饼图": "pie",
        "pie": "pie",
        "折线图": "line",
        "line": "line",
    }
    for alias, canonical in alias_map.items():
        if alias and alias in normalized_viz:
            return canonical

    if normalized_viz in {"pie", "bar", "line"}:
        return normalized_viz

    # v1 默认值：未指定图表类型时统一降级为柱状图
    _ = (columns, rows)  # 保留签名中的上下文参数，便于后续扩展推断策略
    return "bar"


def _coerce_chart_number(value: Any) -> Optional[float]:
    """将值转换为图表数值，无法转换时返回 None。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return None

    if isinstance(value, Number):
        numeric = float(value)
        if math.isfinite(numeric):
            return numeric
        return None

    text = str(value).strip().replace(",", "")
    if not text:
        return None

    unit_match = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(亿|万)\s*元?", text)
    if unit_match:
        base = float(unit_match.group(1))
        if not math.isfinite(base):
            return None
        unit = unit_match.group(2)
        if unit == "亿":
            return base * 1_0000_0000
        if unit == "万":
            return base * 1_0000

    try:
        numeric = float(text)
        if math.isfinite(numeric):
            return numeric
    except Exception:
        return None
    return None


def _is_valid_yyyymmdd_number(value: int) -> bool:
    """判断整数是否符合 YYYYMMDD 形式。"""
    if value < 19000101 or value > 29991231:
        return False

    year = value // 10000
    month = (value // 100) % 100
    day = value % 100
    if year < 1900 or year > 2999:
        return False
    if month < 1 or month > 12:
        return False
    if day < 1 or day > 31:
        return False
    return True


def _is_valid_yyyymm_number(value: int) -> bool:
    """判断整数是否符合 YYYYMM 形式。"""
    if value < 190001 or value > 299912:
        return False

    year = value // 100
    month = value % 100
    if year < 1900 or year > 2999:
        return False
    if month < 1 or month > 12:
        return False
    return True


def _is_date_like_value(value: Any) -> bool:
    """判断值是否呈现时间语义。"""
    if value is None:
        return False
    if isinstance(value, (date, datetime)):
        return True
    if isinstance(value, bool):
        return False

    if isinstance(value, Number):
        numeric = float(value)
        if not math.isfinite(numeric):
            return False
        if not numeric.is_integer():
            return False

        int_value = int(numeric)
        if 1900 <= int_value <= 2999:
            return True
        if _is_valid_yyyymm_number(int_value):
            return True
        if _is_valid_yyyymmdd_number(int_value):
            return True
        return False

    text = str(value).strip()
    if not text:
        return False

    if re.fullmatch(r"\d{8}", text):
        return _is_valid_yyyymmdd_number(int(text))
    if re.fullmatch(r"\d{6}", text):
        return _is_valid_yyyymm_number(int(text))
    if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
        return True
    if re.fullmatch(r"\d{4}[-/]\d{1,2}", text):
        return True
    if re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日?", text):
        return True
    if re.fullmatch(r"\d{4}年\d{1,2}月", text):
        return True

    return False


def _count_distinct_non_null_dimension_values(rows: List[Dict[str, Any]], column: str) -> int:
    """统计维度列非空去重值数量（样本上限 50）。"""
    values = set()
    for row in rows[:50]:
        if not isinstance(row, dict) or column not in row:
            continue

        raw_value = row.get(column)
        if raw_value is None:
            continue

        text = str(raw_value).strip()
        if not text:
            continue
        values.add(text)

    return len(values)


def _is_likely_temporal_column(
    rows: List[Dict[str, Any]],
    column: str,
    column_data_type_map: Optional[Dict[str, str]] = None,
) -> bool:
    """判断列是否具备时间语义。"""
    column_key = _normalize_column_key(column)
    if column_data_type_map:
        mapped_data_type = column_data_type_map.get(column_key, "")
        if _is_temporal_data_type(mapped_data_type):
            return True

    sample_rows = rows[:50]
    non_null_count = 0
    date_like_count = 0

    for row in sample_rows:
        if not isinstance(row, dict) or column not in row:
            continue

        raw_value = row.get(column)
        if raw_value is None:
            continue

        non_null_count += 1
        if _is_date_like_value(raw_value):
            date_like_count += 1

    if non_null_count == 0:
        return False

    ratio = date_like_count / non_null_count
    if ratio >= 0.6:
        return True

    if _is_date_like_column(column) and ratio >= 0.3:
        return True

    return False


def _is_numeric_column(
    rows: List[Dict[str, Any]],
    column: str,
    column_data_type_map: Optional[Dict[str, str]] = None,
) -> bool:
    """判断列是否可作为数值轴。"""
    if _is_likely_temporal_column(rows, column, column_data_type_map):
        return False

    sample_rows = rows[:50]
    numeric_count = 0
    non_null_count = 0

    for row in sample_rows:
        if not isinstance(row, dict):
            continue
        if column not in row:
            continue

        raw_value = row.get(column)
        if raw_value is None:
            continue

        non_null_count += 1
        if _coerce_chart_number(raw_value) is not None:
            numeric_count += 1

    if non_null_count == 0:
        return False

    # 只要有 80% 以上非空值可解析为数值，即视为数值列
    return numeric_count / non_null_count >= 0.8


def _build_chart_semantic_text(
    column: str,
    column_display_name_map: Optional[Dict[str, str]] = None,
) -> str:
    """合并原始列名与展示列名用于语义判别。"""
    raw_name = str(column or "").strip()
    if not raw_name:
        return ""

    if not column_display_name_map:
        return raw_name

    display_name = str(column_display_name_map.get(column) or "").strip()
    if not display_name or display_name == raw_name:
        return raw_name

    return f"{raw_name} {display_name}"


def _is_identifier_column(
    column: str,
    column_display_name_map: Optional[Dict[str, str]] = None,
) -> bool:
    """判断列是否属于标识字段（客户号/编号/ID 等）。"""
    semantic_text = _build_chart_semantic_text(column, column_display_name_map)
    if not semantic_text:
        return False

    compact_text = re.sub(r"\s+", "", semantic_text)
    lowered = compact_text.lower()

    if any(token in lowered for token in ("ecif_cust_no", "cust_no", "customer_no", "customer_id")):
        return True

    if any(token in compact_text for token in ("客户统一编号", "客户编号", "客户号", "编号", "编码", "证件号")):
        return True

    if any(token in lowered for token in ("org_no", "dept_no", "inst_no", "branch_no", "org_cd", "dept_cd", "inst_cd", "branch_cd")):
        return True

    if lowered in {"id", "no", "code"}:
        return True

    if lowered.endswith(("_id", "id", "_no", "no", "_code", "code", "_cd", "cd")):
        return True

    return False


def _is_date_like_column(column: str) -> bool:
    """根据列名判断是否为时间维度列。"""
    lowered = str(column or "").strip().lower()
    if not lowered:
        return False

    keywords = ("date", "dt", "time", "day", "month", "year", "日期", "时间", "月份", "年度")
    return any(keyword in lowered for keyword in keywords)


def _is_name_like_column(
    column: str,
    column_display_name_map: Optional[Dict[str, str]] = None,
) -> bool:
    """判断列是否更偏向名称语义（如客户名称/机构名称）。"""
    semantic_text = _build_chart_semantic_text(column, column_display_name_map)
    if not semantic_text:
        return False

    compact_text = re.sub(r"\s+", "", semantic_text)
    lowered = compact_text.lower()

    chinese_tokens = ("名称", "户名", "单位名", "公司名", "机构名", "分行名", "支行名")
    if any(token in compact_text for token in chinese_tokens):
        return True

    english_tokens = (
        "_name",
        "name",
        "_nm",
        "cust_name",
        "cust_nm",
        "customer_name",
        "org_name",
        "org_nm",
        "branch_name",
        "branch_nm",
        "dept_name",
        "dept_nm",
        "inst_name",
        "inst_nm",
        "company",
    )
    if any(token in lowered for token in english_tokens):
        return True

    return False


def _resolve_dimension_hint_flags(dimension_hints: Optional[List[str]] = None) -> Dict[str, bool]:
    """将维度提示词归一为客户/机构/时间语义开关。"""
    hints = _ensure_text_list(dimension_hints)
    flags = {
        "customer": False,
        "organization": False,
        "time": False,
    }

    for hint in hints:
        compact_hint = re.sub(r"\s+", "", str(hint or ""))
        lowered_hint = compact_hint.lower()
        if not compact_hint:
            continue

        if any(token in compact_hint for token in ("客户", "客群", "户")) or any(
            token in lowered_hint for token in ("cust", "customer", "ecif")
        ):
            flags["customer"] = True

        if any(token in compact_hint for token in ("机构", "分行", "支行", "网点", "部门", "营业部")) or any(
            token in lowered_hint for token in ("org", "branch", "dept", "inst")
        ):
            flags["organization"] = True

        if any(token in compact_hint for token in ("日期", "时间", "月份", "年度", "年", "月", "日", "趋势")) or any(
            token in lowered_hint for token in ("date", "time", "month", "year", "trend")
        ):
            flags["time"] = True

    return flags


def _pick_dimension_column_by_semantics(
    dimension_columns: List[str],
    rows: List[Dict[str, Any]],
    temporal_flags: Dict[str, bool],
    identifier_flags: Dict[str, bool],
    column_display_name_map: Optional[Dict[str, str]] = None,
    dimension_hints: Optional[List[str]] = None,
) -> str:
    """结合名称语义与维度提示词，挑选更可读的 x 轴维度列。"""
    if not dimension_columns:
        return ""

    hint_flags = _resolve_dimension_hint_flags(dimension_hints)
    best_column = ""
    best_score = -10**9
    best_index = len(dimension_columns)

    for index, column in enumerate(dimension_columns):
        semantic_text = _build_chart_semantic_text(column, column_display_name_map)
        compact_text = re.sub(r"\s+", "", semantic_text)
        lowered = compact_text.lower()

        is_identifier = bool(identifier_flags.get(column))
        is_temporal = bool(temporal_flags.get(column) or _is_date_like_column(column))
        is_name_like = _is_name_like_column(column, column_display_name_map)
        distinct_count = _count_distinct_non_null_dimension_values(rows, column)

        score = 0

        if is_name_like:
            score += 8
        if is_identifier:
            score -= 6

        if distinct_count > 1:
            score += 3
        elif distinct_count == 1:
            score -= 2
        else:
            score -= 4

        if hint_flags["time"]:
            if is_temporal:
                score += 10
            else:
                score -= 3
        elif is_temporal:
            score -= 2

        if hint_flags["customer"]:
            if any(token in compact_text for token in ("客户", "户名")) or any(
                token in lowered for token in ("cust", "customer", "ecif")
            ):
                score += 8
            elif is_name_like:
                score += 2

        if hint_flags["organization"]:
            if any(token in compact_text for token in ("机构", "分行", "支行", "网点", "部门", "营业部")) or any(
                token in lowered for token in ("org", "branch", "dept", "inst")
            ):
                score += 8
            elif is_name_like:
                score += 2

        if not any(hint_flags.values()) and is_name_like:
            score += 2

        if score > best_score or (score == best_score and index < best_index):
            best_score = score
            best_column = column
            best_index = index

    return best_column


def _pick_preferred_y_column(
    numeric_columns: List[str],
    rows: List[Dict[str, Any]],
    column_display_name_map: Optional[Dict[str, str]] = None,
    identifier_flags: Optional[Dict[str, bool]] = None,
    metric_hint: str = "",
) -> str:
    """在多个数值列中挑选更可能的指标列。"""
    if not numeric_columns:
        return ""

    measure_tokens = ("余额", "金额", "占比", "比率", "利率", "数量", "笔数", "规模", "总额", "合计")
    measure_tokens_en = ("balance", "amount", "amt", "sum", "total", "count", "avg", "ratio", "pct")
    identifier_tokens = ("编号", "编码", "客户号", "客户统一", "身份证", "证件号")

    normalized_metric_hint = re.sub(r"\s+", "", str(metric_hint or ""))
    normalized_metric_hint_lower = normalized_metric_hint.lower()

    best_column = numeric_columns[0]
    best_score = -10**9

    for column in numeric_columns:
        score = 0
        semantic_text = _build_chart_semantic_text(column, column_display_name_map)
        compact_text = re.sub(r"\s+", "", semantic_text)
        lowered = compact_text.lower()

        if any(token in compact_text for token in measure_tokens):
            score += 8
        if any(token in lowered for token in measure_tokens_en):
            score += 4

        if normalized_metric_hint_lower:
            if normalized_metric_hint_lower in lowered or lowered in normalized_metric_hint_lower:
                score += 10

        if identifier_flags and identifier_flags.get(column):
            score -= 12
        if any(token in compact_text for token in identifier_tokens):
            score -= 8

        non_null_count = 0
        decimal_count = 0
        unit_count = 0
        long_integer_count = 0

        for row in rows[:50]:
            if not isinstance(row, dict) or column not in row:
                continue

            raw_value = row.get(column)
            if raw_value is None:
                continue

            text = str(raw_value).strip()
            if not text:
                continue

            non_null_count += 1
            if re.search(r"(亿|万)\s*元?$", text):
                unit_count += 1

            numeric = _coerce_chart_number(raw_value)
            if numeric is None:
                continue

            if not float(numeric).is_integer():
                decimal_count += 1
                continue

            if _is_date_like_value(raw_value):
                continue

            digit_text = re.sub(r"\D", "", text)
            if len(digit_text) >= 8 and abs(int(round(numeric))) >= 1_000_000:
                long_integer_count += 1

        if non_null_count > 0:
            if unit_count > 0:
                score += 6
            if decimal_count / non_null_count >= 0.2:
                score += 3
            if long_integer_count / non_null_count >= 0.8 and unit_count == 0 and decimal_count == 0:
                score -= 4

        if score > best_score:
            best_score = score
            best_column = column

    return best_column


def _build_chart_semantic_flags(
    columns: List[str],
    rows: List[Dict[str, Any]],
    column_data_type_map: Optional[Dict[str, str]] = None,
    column_display_name_map: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, bool], Dict[str, bool], Dict[str, bool]]:
    """构建字段语义标记（时间/数值/标识）。"""
    temporal_flags = {
        column: _is_likely_temporal_column(rows, column, column_data_type_map)
        for column in columns
    }
    numeric_flags = {
        column: _is_numeric_column(rows, column, column_data_type_map)
        for column in columns
    }
    identifier_flags = {
        column: _is_identifier_column(column, column_display_name_map)
        for column in columns
    }
    return temporal_flags, numeric_flags, identifier_flags


def _pick_chart_axes_from_flags(
    columns: List[str],
    rows: List[Dict[str, Any]],
    temporal_flags: Dict[str, bool],
    numeric_flags: Dict[str, bool],
    identifier_flags: Dict[str, bool],
    column_display_name_map: Optional[Dict[str, str]] = None,
    dimension_hints: Optional[List[str]] = None,
    metric_hint: str = "",
) -> Tuple[str, str]:
    """根据字段语义标记选择图表 x/y 轴。"""
    numeric_columns = [
        column
        for column in columns
        if numeric_flags.get(column)
        and not temporal_flags.get(column)
        and not identifier_flags.get(column)
    ]
    if not numeric_columns:
        return "", ""

    y_key = _pick_preferred_y_column(
        numeric_columns,
        rows,
        column_display_name_map=column_display_name_map,
        identifier_flags=identifier_flags,
        metric_hint=metric_hint,
    )
    if not y_key:
        return "", ""

    dimension_columns = [
        column for column in columns
        if column != y_key and not numeric_flags.get(column)
    ]

    if dimension_columns:
        semantic_dimension = _pick_dimension_column_by_semantics(
            dimension_columns=dimension_columns,
            rows=rows,
            temporal_flags=temporal_flags,
            identifier_flags=identifier_flags,
            column_display_name_map=column_display_name_map,
            dimension_hints=dimension_hints,
        )
        if semantic_dimension:
            return semantic_dimension, y_key

        date_like_columns = [
            column
            for column in dimension_columns
            if temporal_flags.get(column) or _is_date_like_column(column)
        ]
        multi_point_date_columns = [
            column
            for column in date_like_columns
            if _count_distinct_non_null_dimension_values(rows, column) > 1
        ]
        if multi_point_date_columns:
            return multi_point_date_columns[0], y_key

        non_date_columns = [column for column in dimension_columns if column not in date_like_columns]
        if non_date_columns:
            return non_date_columns[0], y_key

        return dimension_columns[0], y_key

    identifier_columns = [
        column for column in columns
        if column != y_key and identifier_flags.get(column)
    ]
    if identifier_columns:
        return identifier_columns[0], y_key

    fallback_columns = [
        column
        for column in columns
        if column != y_key and not temporal_flags.get(column)
    ]
    if fallback_columns:
        return fallback_columns[0], y_key

    temporal_fallback_columns = [column for column in columns if column != y_key]
    if temporal_fallback_columns:
        return temporal_fallback_columns[0], y_key

    return "", ""


def _build_chart_field_meta(
    columns: List[str],
    x_key: str,
    y_key: str,
    temporal_flags: Dict[str, bool],
    numeric_flags: Dict[str, bool],
    identifier_flags: Dict[str, bool],
) -> Dict[str, Dict[str, str]]:
    """构建图表字段语义契约（field_meta）。"""
    field_meta: Dict[str, Dict[str, str]] = {}

    for column in columns:
        axis_hint = "none"
        if column == x_key:
            axis_hint = "x"
        elif column == y_key:
            axis_hint = "y"

        role = "dimension"
        if column == y_key:
            role = "measure"
        elif identifier_flags.get(column):
            role = "identifier"
        elif temporal_flags.get(column):
            role = "time"
        elif numeric_flags.get(column):
            role = "measure"

        semantic_type = "categorical"
        if temporal_flags.get(column):
            semantic_type = "temporal"
        elif numeric_flags.get(column) or column == y_key:
            semantic_type = "numeric"

        field_meta[column] = {
            "role": role,
            "semantic_type": semantic_type,
            "axis_hint": axis_hint,
            "agg": "none",
        }

    return field_meta


def _pick_chart_axes(
    columns: List[str],
    rows: List[Dict[str, Any]],
    column_data_type_map: Optional[Dict[str, str]] = None,
    column_display_name_map: Optional[Dict[str, str]] = None,
    dimension_hints: Optional[List[str]] = None,
    metric_hint: str = "",
) -> Tuple[str, str]:
    """选择图表 x/y 轴字段（优先维度列 + 数值列）。"""
    if not columns:
        return "", ""
    if not rows:
        return "", ""

    temporal_flags, numeric_flags, identifier_flags = _build_chart_semantic_flags(
        columns=columns,
        rows=rows,
        column_data_type_map=column_data_type_map,
        column_display_name_map=column_display_name_map,
    )

    return _pick_chart_axes_from_flags(
        columns=columns,
        rows=rows,
        temporal_flags=temporal_flags,
        numeric_flags=numeric_flags,
        identifier_flags=identifier_flags,
        column_display_name_map=column_display_name_map,
        dimension_hints=dimension_hints,
        metric_hint=metric_hint,
    )


def _serialize_chart_dimension_value(value: Any) -> str:
    """序列化图表维度值。"""
    if value is None:
        return "未知"

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return "未知"

    lowered = text.lower()
    if lowered in {"none", "null", "nan", "-"}:
        return "未知"

    return text


def _serialize_chart_identifier_value(value: Any) -> str:
    """序列化标识字段值（空值返回空字符串）。"""
    if value is None:
        return ""

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return ""

    lowered = text.lower()
    if lowered in {"none", "null", "nan", "未知", "-"}:
        return ""

    return text


def _ensure_chart_dimension_uniqueness(
    chart_rows: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    x_key: str,
    y_key: str,
    columns: List[str],
    column_display_name_map: Optional[Dict[str, str]] = None,
) -> None:
    """在维度重复时补齐唯一后缀，避免图表类目塌缩。"""
    if not chart_rows or _is_date_like_column(x_key):
        return

    x_counter = Counter(str(item.get(x_key, "")) for item in chart_rows)
    if not any(count > 1 for count in x_counter.values()):
        return

    identifier_columns = [
        column
        for column in columns
        if column not in {x_key, y_key} and _is_identifier_column(column, column_display_name_map)
    ]
    sequence_counter: Counter[str] = Counter()
    final_counter: Counter[str] = Counter()

    for idx, chart_item in enumerate(chart_rows):
        label = str(chart_item.get(x_key, ""))
        if x_counter.get(label, 0) <= 1:
            continue

        sequence_counter[label] += 1
        row = rows[idx] if idx < len(rows) and isinstance(rows[idx], dict) else {}
        suffix = ""
        for identifier_column in identifier_columns:
            suffix = _serialize_chart_identifier_value(row.get(identifier_column))
            if suffix:
                break

        if not suffix:
            suffix = f"#{sequence_counter[label]}"

        dedup_label = f"{label}（{suffix}）"
        final_counter[dedup_label] += 1
        if final_counter[dedup_label] > 1:
            dedup_label = f"{dedup_label}#{final_counter[dedup_label]}"

        chart_item[x_key] = dedup_label


def _collect_chart_axis_semantic_context(
    state: DataAgentState,
    question: str,
) -> Tuple[List[str], str]:
    """收集图表轴选择所需语义提示（维度/指标）。"""
    dimension_hints: List[str] = []
    dimension_hints.extend(_ensure_text_list(state.get("dimensions")))

    analysis_metric = ""
    query_context = state.get("query_context")
    if isinstance(query_context, dict):
        analysis = query_context.get("analysis")
        if isinstance(analysis, dict):
            dimension_hints.extend(_ensure_text_list(analysis.get("dimensions")))
            analysis_metric = str(analysis.get("metric_name") or "").strip()

    dimension_hints.extend(_extract_dimensions_from_text(question))
    normalized_dimension_hints = _ensure_text_list(dimension_hints)

    metric_hint = _pick_first_non_empty_str(
        str(state.get("matched_metric") or "").strip(),
        analysis_metric,
        _extract_metric_from_text(question),
    )

    return normalized_dimension_hints, metric_hint


def _build_sql_result_chart_payload(
    state: DataAgentState,
    question: str,
    sql: Optional[str],
    columns: List[str],
    column_display_names: List[str],
    rows: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """根据 SQL 结果构造图表载荷（可选）。"""
    if not _is_chart_requested(state):
        return None
    if not rows:
        return None
    if not columns:
        return None

    chart_type = _resolve_chart_type(str(state.get("viz_type") or ""), columns, rows)
    display_name_map: Dict[str, str] = {
        column: (column_display_names[idx] if idx < len(column_display_names) else column)
        for idx, column in enumerate(columns)
    }
    dimension_hints, metric_hint = _collect_chart_axis_semantic_context(state, question)

    column_data_type_map = _load_column_data_type_map(columns, sql)
    temporal_flags, numeric_flags, identifier_flags = _build_chart_semantic_flags(
        columns=columns,
        rows=rows,
        column_data_type_map=column_data_type_map,
        column_display_name_map=display_name_map,
    )
    x_key, y_key = _pick_chart_axes_from_flags(
        columns=columns,
        rows=rows,
        temporal_flags=temporal_flags,
        numeric_flags=numeric_flags,
        identifier_flags=identifier_flags,
        column_display_name_map=display_name_map,
        dimension_hints=dimension_hints,
        metric_hint=metric_hint,
    )
    if not x_key or not y_key:
        return None

    chart_rows: List[Dict[str, Any]] = []
    source_rows: List[Dict[str, Any]] = []
    for row in rows[:50]:
        if not isinstance(row, dict):
            continue

        y_value = _coerce_chart_number(row.get(y_key))
        if y_value is None:
            continue

        chart_rows.append(
            {
                x_key: _serialize_chart_dimension_value(row.get(x_key)),
                y_key: y_value,
            }
        )
        source_rows.append(row)

    if not chart_rows:
        return None

    _ensure_chart_dimension_uniqueness(
        chart_rows=chart_rows,
        rows=source_rows,
        x_key=x_key,
        y_key=y_key,
        columns=columns,
        column_display_name_map=display_name_map,
    )

    title = str(question or "").strip()
    if title:
        title = title[:80]
    else:
        title = f"{display_name_map.get(y_key, y_key)}图表"

    field_meta = _build_chart_field_meta(
        columns=columns,
        x_key=x_key,
        y_key=y_key,
        temporal_flags=temporal_flags,
        numeric_flags=numeric_flags,
        identifier_flags=identifier_flags,
    )

    return {
        "type": chart_type,
        "title": title,
        "x_key": x_key,
        "x_label": display_name_map.get(x_key, x_key),
        "y_key": y_key,
        "y_label": display_name_map.get(y_key, y_key),
        "series_name": display_name_map.get(y_key, y_key),
        "field_meta": field_meta,
        "data": chart_rows,
    }


def _build_sql_result_additional_kwargs(
    sql: str,
    display_sql: str,
    columns: List[str],
    column_display_names: List[str],
    result_data: List[Dict[str, Any]],
    sql_source: str,
    iterations: int,
    chart_payload: Optional[Dict[str, Any]],
    permission_rewritten: bool,
    permission_scope_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """构建 SQL 结果消息的 additional_kwargs。"""
    result_payload = build_result_additional_kwargs_payload(
        data_type="sql_result",
        data={
            "sql": sql,
            "display_sql": display_sql,
            "columns": columns,
            "column_display_names": column_display_names,
            "rows": result_data[:100],
            "total_rows": len(result_data),
            "sql_source": sql_source,
            "iterations": iterations,
            "chart": chart_payload,
            "permission_scope_applied": permission_rewritten,
            "permission_scope_summary": permission_scope_summary,
        },
    )
    return result_payload or {}


def _resolve_sql_empty_result_fallback_policy(sql_source: Any) -> Optional[Tuple[str, str]]:
    """解析空结果降级策略（source -> next_target/hint）。"""
    normalized_source = str(sql_source or "").strip()
    policy = _SQL_EMPTY_RESULT_FALLBACK_POLICY.get(normalized_source)
    if not isinstance(policy, dict):
        return None

    next_target = str(policy.get("next_target") or "").strip()
    hint = str(policy.get("hint") or "").strip()
    if not next_target:
        return None

    return next_target, hint


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
    
    if not sql:
        emit_error(writer, "没有可执行的 SQL", node="sql_execute")
        return {"messages": [create_ai_message("❌ 没有可执行的 SQL")]}
    
    rewrite_note = None

    try:
        vanna = get_vanna()

        compat_sql, compat_reason = rewrite_sql_for_column_compatibility(sql)
        if compat_reason and compat_sql != sql:
            logger.info("字段兼容 SQL 预重写触发: %s", compat_reason)
            emit_status(writer, f"检测到字段兼容映射，已自动调整查询：{compat_reason}", node="sql_execute")
            sql = compat_sql
            rewrite_note = compat_reason
        
        # 执行 SQL（可能已被权限重写）
        emit_status(writer, "正在执行查询...", node="sql_execute")
        df = vanna.run_sql(sql)

        # 空结果时，做一次轻量 SQL 自愈重写（表切换）
        if is_effectively_empty_result(df.to_dict(orient="records")):
            rewritten_sql, reason = rewrite_sql_for_empty_result(sql)
            if reason and rewritten_sql != sql:
                logger.info("空结果 SQL 自愈重写触发: %s", reason)
                emit_status(writer, f"检测到空结果，正在自动重试：{reason}", node="sql_execute")
                df_retry = vanna.run_sql(rewritten_sql)
                if not is_effectively_empty_result(df_retry.to_dict(orient="records")):
                    sql = rewritten_sql
                    df = df_retry
                    if rewrite_note:
                        rewrite_note = f"{rewrite_note}；{reason}"
                    else:
                        rewrite_note = reason
                    logger.info("空结果 SQL 自愈重写成功")
        
        # 转换为可序列化格式
        result_data = df.to_dict(orient="records")
        columns = list(df.columns)

        # 结果增强：按规则链补齐展示字段（仅补展示，不改 SQL）
        result_data, columns = _enrich_result_rows_if_needed(result_data, columns)

        # 列名展示增强：优先映射中文显示名（仅展示，不改 rows 键）
        column_display_map = _load_column_display_name_map(columns, sql)
        column_display_names = _build_column_display_names(columns, column_display_map)

        # SQL 展示增强：仅用于折叠区展示，保持 sql 字段可执行语义
        display_sql = _build_display_sql(sql, column_display_map)
        
        logger.info(f"查询返回 {len(result_data)} 行数据")
        
        # 空结果降级链：metric → training → schema(通用)
        sql_source = state.get("sql_source", "unknown")
        is_empty = not result_data
        # 聚合函数返回 NULL 的情况（如 SUM(...) 无匹配行时返回 None）
        if not is_empty and len(result_data) == 1:
            row = result_data[0]
            if all(v is None for v in row.values()):
                is_empty = True
        
        # 三级降级：metric 空结果 → 训练集，训练集空结果 → 通用 RAG
        fallback_policy = _resolve_sql_empty_result_fallback_policy(sql_source)
        if is_empty and fallback_policy:
            next_target, hint = fallback_policy
            logger.info(
                "空结果降级: sql_source=%s → fallback_target=%s",
                sql_source, next_target
            )
            if hint:
                emit_status(writer, hint, node="sql_execute")
            
            return {
                "fallback_target": next_target,
                "generated_sql": None,
                "pending_sql": None,
                "sql_source": None,
                "execution_success": True,
            }
        
        # 生成结果解释
        query_context = state.get("query_context", {})
        question = query_context.get("original_question", "")
        permission_rewritten = bool(query_context.get("permission_rewritten")) if isinstance(query_context, dict) else False
        permission_scope_summary = query_context.get("permission_scope_summary") if isinstance(query_context, dict) else None
        if not isinstance(permission_scope_summary, dict):
            permission_scope_summary = None

        # 可视化增强：在 sql_result 中附带前端可直接消费的 chart 规格（可选）
        chart_payload = _build_sql_result_chart_payload(
            state=state,
            question=question,
            sql=sql,
            columns=columns,
            column_display_names=column_display_names,
            rows=result_data,
        )
        
        interpretation = _interpret_result(question, sql, result_data)
        if rewrite_note:
            interpretation = f"ℹ️ 已自动调整查询策略：{rewrite_note}。\n\n{interpretation}"
        if permission_rewritten:
            scope_text = None
            if permission_scope_summary:
                scope_text = str(permission_scope_summary.get("display_text") or "").strip()

            if scope_text:
                interpretation = f"{interpretation}\n\n注：结果已按当前账号的数据权限范围过滤（{scope_text}）。"
            else:
                interpretation = f"{interpretation}\n\n注：结果已按当前账号的数据权限范围（机构/部门）过滤。"
        
        # 构建响应消息
        response_msg = create_ai_message(
            interpretation,
            additional_kwargs=_build_sql_result_additional_kwargs(
                sql=sql,
                display_sql=display_sql,
                columns=columns,
                column_display_names=column_display_names,
                result_data=result_data,
                sql_source=state.get("sql_source", "unknown"),
                iterations=iterations,
                chart_payload=chart_payload,
                permission_rewritten=permission_rewritten,
                permission_scope_summary=permission_scope_summary,
            ),
        )
        
        stream_result_payload = build_streaming_result_payload_from_fields(
            data_type="sql_result",
            data={
                "rows": result_data[:20],
                "columns": columns,
                "column_display_names": column_display_names,
                "display_sql": display_sql,
                "total_rows": len(result_data),
                "sql": sql,
                "chart": chart_payload,
                "permission_scope_applied": permission_rewritten,
                "permission_scope_summary": permission_scope_summary,
            },
            message=interpretation,
        )
        if stream_result_payload:
            emit_result(
                writer,
                data_type=stream_result_payload["data_type"],
                data=stream_result_payload["data"],
                message=stream_result_payload["message"],
                node="sql_execute",
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


def _interpret_result(question: str, sql: str, result: List[Dict]) -> str:
    """生成查询结果的自然语言解释。
    
    格式化规则：
    - 大数字自动转换为亿/万单位
    - 聚合函数列名（sum/avg/count 等）替换为更友好的标签
    - 单值结果直接展示，多行结果汇总行数
    """
    if not result:
        return (
            "查询完成，但没有找到符合条件的数据。\n\n"
            "💡 **排查建议**：\n"
            "1. **日期范围**：请检查查询日期是否与数据库中的数据匹配"
            "（当前导入数据日期为 2025-06-30）。\n"
            "2. **查询条件**：尝试放宽过滤条件或查询全量数据。"
        )
    
    row_count = len(result)
    
    if row_count == 1:
        row = result[0]
        
        # 单列 + 值为 None：聚合无匹配
        if len(row) == 1:
            key, value = list(row.items())[0]
            if value is None:
                return (
                    f"查询完成，但计算结果为空（{_friendly_col(key)}: 无数据）。\n\n"
                    "💡 **排查建议**：\n"
                    "1. 请检查查询日期是否与数据库中的数据匹配。\n"
                    "2. 当前导入测试数据日期为 2025-06-30，"
                    "建议尝试指定该日期查询。"
                )
        
        # 格式化所有字段
        formatted_parts = []
        for k, v in row.items():
            label = _friendly_col(k)
            display_val = _format_value(v)
            formatted_parts.append(f"- **{label}**：{display_val}")
        
        # 提取问题中的关键词作为标题
        title = question[:30] if question else "查询结果"
        
        if len(row) <= 3:
            # 少量字段：紧凑展示
            inline = "，".join(
                f"**{_friendly_col(k)}** {_format_value(v)}"
                for k, v in row.items()
            )
            return f"{inline}"
        else:
            return f"查询结果：\n\n" + "\n".join(formatted_parts)
    
    elif row_count <= 5:
        return f"查询完成，共返回 {row_count} 条记录。"
    else:
        display_limit = min(row_count, 100)
        if row_count > display_limit:
            return f"查询完成，共返回 {row_count} 条记录（已展示前 {display_limit} 条）。"
        else:
            return f"查询完成，共返回 {row_count} 条记录。"


# 聚合函数列名 → 友好标签的映射
_AGG_COL_MAP = {
    "sum": "合计",
    "count": "数量",
    "avg": "平均值",
    "min": "最小值",
    "max": "最大值",
}


def _friendly_col(col_name: str) -> str:
    """将列名转换为友好标签。
    
    - 聚合函数名（sum/count/avg）→ 中文标签
    - 已有中文别名的保持不变
    """
    lower = col_name.strip().lower()
    if lower in _AGG_COL_MAP:
        return _AGG_COL_MAP[lower]
    # 带括号的聚合函数: sum(prin_bal) → 合计
    for agg in _AGG_COL_MAP:
        if lower.startswith(f"{agg}("):
            return _AGG_COL_MAP[agg]
    return col_name


def _format_value(value) -> str:
    """格式化数值，大数字自动转换为亿/万单位。"""
    if value is None:
        return "无数据"
    
    # 数值格式化
    if isinstance(value, (int, float)):
        abs_val = abs(value)
        if abs_val >= 1_0000_0000:
            # 亿级别
            formatted = f"{value / 1_0000_0000:,.2f} 亿"
        elif abs_val >= 1_0000:
            # 万级别
            formatted = f"{value / 1_0000:,.2f} 万"
        elif isinstance(value, float):
            formatted = f"{value:,.2f}"
        else:
            formatted = f"{value:,}"
        return formatted
    
    return str(value)


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


def route_after_metric(state: DataAgentState) -> Literal["safety", "training"]:
    """指标解析后路由（第1级 → 第2级）。"""
    if state.get("generated_sql"):
        return "safety"
    else:
        return "training"  # 未命中指标，尝试训练集


def route_after_training(state: DataAgentState) -> Literal["safety", "schema"]:
    """训练集解析后路由（第2级 → 第3级）。"""
    if state.get("generated_sql"):
        return "safety"
    else:
        return "schema"  # 未命中训练集，回退到通用 RAG


def route_after_safety(state: DataAgentState) -> Literal["execute", "clarify"]:
    """安全检查后路由。"""
    if state.get("clarification_needed"):
        return "clarify"
    return "execute"


def route_after_execute(state: DataAgentState) -> Literal[
    "end", "retry", "fallback_training", "fallback_schema"
]:
    """执行后路由（错误自愈 + 三级降级链）。
    
    降级链：metric 空结果 → training → training 空结果 → schema(通用RAG)
    错误自愈：执行报错 → 重新生成 SQL（最多 3 次）
    """
    # 三级降级链
    fallback = str(state.get("fallback_target") or "").strip()
    fallback_route = _EXECUTE_FALLBACK_ROUTE_MAP.get(fallback)
    if fallback_route:
        if fallback == "training":
            logger.info("空结果降级: metric → training")
        elif fallback == "schema":
            logger.info("空结果降级: training → schema(通用RAG)")
        return fallback_route
    
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
    """创建问数 Agent LangGraph（三级降级链 + 错误自愈）。
    
    三级降级链：
    1. metric: 指标模板匹配（精确名称 + 向量检索）→ 直接执行
    2. training: 训练集 SQL 匹配（t_data_query_log）→ 直接执行
    3. schema + generate: DDL/文档/历史 RAG → LLM 生成 SQL → 执行
    
    每级执行后如空结果，自动降级到下一级。
    错误自愈：generate 路径执行报错可自动重试（最多 3 次）。
    """
    workflow = StateGraph(DataAgentState)
    
    # === 添加节点 ===
    workflow.add_node("analyze", analyze_data_intent)
    workflow.add_node("metric", metric_resolve)
    workflow.add_node("training", training_sql_resolve)
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
    
    # metric → 条件路由（第1级 → 第2级）
    workflow.add_conditional_edges(
        "metric",
        route_after_metric,
        {
            "safety": "safety",
            "training": "training"     # 未命中指标 → 尝试训练集
        }
    )
    
    # training → 条件路由（第2级 → 第3级）
    workflow.add_conditional_edges(
        "training",
        route_after_training,
        {
            "safety": "safety",
            "schema": "schema"         # 未命中训练集 → 通用 RAG
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
    
    # execute → 条件路由（错误自愈 + 三级降级链）
    workflow.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "end": END,
            "retry": "generate",             # 执行报错 → 重新生成
            "fallback_training": "training",  # metric 空结果 → 训练集
            "fallback_schema": "schema"       # training 空结果 → 通用 RAG
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
