"""SQL 空结果恢复工具。"""
import logging
import re
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from sqlalchemy import text

from app.db.session import analytics_engine

logger = logging.getLogger(__name__)


# 空结果重写规则：源表 -> 目标表 -> 提示原因 -> 字段映射（可选）
DEFAULT_EMPTY_RESULT_REWRITE_RULES: Sequence[Tuple[str, str, str, Dict[str, str]]] = (
    (
        "fdmdata.f_mid_loan_tb",
        "fdmdata.f_mid_loan_k_tb",
        "f_mid_loan_tb 无数据，改用 f_mid_loan_k_tb",
        {
            "org_cd": "dept_cd",
            "level7_val": "dept_val",
        },
    ),
)


RewriteRule = Union[
    Tuple[str, str, str],
    Tuple[str, str, str, Mapping[str, str]],
]


DEFAULT_COLUMN_COMPATIBILITY_RULES: Mapping[str, Mapping[str, str]] = {
    "fdmdata.f_mid_loan_k_tb": {
        "org_cd": "dept_cd",
        "level7_val": "dept_val",
    }
}


def is_effectively_empty_result(rows: List[Dict]) -> bool:
    """判断结果是否可视为空。"""
    if not rows:
        return True
    if len(rows) == 1 and all(value is None for value in rows[0].values()):
        return True
    return False


def extract_data_dt_from_sql(sql: str) -> Optional[str]:
    """从 SQL 提取 data_dt 字面值（YYYY-MM-DD）。"""
    match = re.search(r"\bdata_dt\b\s*=\s*'?(\d{4}-?\d{2}-?\d{2})'?", sql, re.IGNORECASE)
    if not match:
        return None

    raw = match.group(1).replace("-", "")
    if len(raw) != 8:
        return None
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def has_rows_for_table(table_name: str, data_dt: Optional[str]) -> bool:
    """检查分析库指定表在给定日期下是否存在数据。"""
    sql = f"SELECT 1 FROM {table_name}"
    params = {}
    if data_dt:
        sql += " WHERE data_dt = :data_dt"
        params["data_dt"] = data_dt
    sql += " LIMIT 1"

    with analytics_engine.connect() as conn:
        row = conn.execute(text(sql), params).first()
    return row is not None


def _normalize_rewrite_rule(rule: RewriteRule) -> Tuple[str, str, str, Dict[str, str]]:
    """标准化重写规则，兼容旧三元组配置。"""
    if len(rule) == 3:
        source_table, target_table, reason = rule
        return source_table, target_table, reason, {}

    if len(rule) == 4:
        source_table, target_table, reason, column_map = rule
        normalized_map = {
            str(src).strip().lower(): str(dst).strip().lower()
            for src, dst in dict(column_map or {}).items()
            if str(src).strip() and str(dst).strip()
        }
        return source_table, target_table, reason, normalized_map

    raise ValueError(f"无效的空结果重写规则: {rule}")


def _rewrite_columns_for_target_table(
    sql: str,
    target_table: str,
    column_mapping: Mapping[str, str],
) -> str:
    """将目标表中不存在的历史字段名映射为兼容字段。"""
    if not column_mapping:
        return sql

    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except ParseError:
        logger.debug("字段映射 SQL 解析失败，跳过字段重写")
        return sql

    normalized_target = target_table.lower()
    target_table_name = normalized_target.split(".")[-1]

    aliases: set[str] = set()
    table_nodes = list(parsed.find_all(exp.Table))

    for table in table_nodes:
        schema_name = (table.db or "public").lower()
        table_name = (table.name or "").lower()
        full_name = f"{schema_name}.{table_name}"

        if full_name != normalized_target and table_name != target_table_name:
            continue

        alias = str(table.alias_or_name or table.name or "").strip().lower()
        if alias:
            aliases.add(alias)
        if table_name:
            aliases.add(table_name)

    if not aliases:
        return sql

    single_table_query = len(table_nodes) == 1
    has_rewrite = False

    for column in parsed.find_all(exp.Column):
        source_column = str(column.name or "").strip().lower()
        mapped_column = column_mapping.get(source_column)
        if not mapped_column:
            continue

        table_qualifier = str(column.table or "").strip().lower()
        if table_qualifier:
            if table_qualifier not in aliases:
                continue
        elif not single_table_query:
            # 多表场景下，不改无前缀列，避免误改。
            continue

        column.set("this", exp.to_identifier(mapped_column))
        has_rewrite = True

    if not has_rewrite:
        return sql

    return parsed.sql(dialect="postgres")


def _extract_missing_columns_from_error(error_message: str) -> Set[str]:
    """从数据库报错中提取缺失字段名。"""
    if not error_message:
        return set()

    missing_columns: Set[str] = set()
    patterns = (
        r'column\s+"([^"]+)"\s+does not exist',
        r"column\s+([a-zA-Z0-9_.]+)\s+does not exist",
    )

    for pattern in patterns:
        for match in re.findall(pattern, error_message, flags=re.IGNORECASE):
            normalized = str(match or "").strip().lower()
            if not normalized:
                continue
            missing_columns.add(normalized.split(".")[-1])

    return missing_columns


def rewrite_sql_for_column_compatibility(
    sql: str,
    error_message: Optional[str] = None,
    compatibility_rules: Optional[Mapping[str, Mapping[str, str]]] = None,
) -> Tuple[str, Optional[str]]:
    """按字段兼容规则改写 SQL（用于 UndefinedColumn 自愈）。"""
    if not sql:
        return sql, None

    missing_columns = _extract_missing_columns_from_error(error_message or "")
    if error_message:
        lowered_error = error_message.lower()
        if "column" not in lowered_error or "does not exist" not in lowered_error:
            return sql, None
        if not missing_columns:
            return sql, None

    rewritten_sql = sql
    applied_items: List[str] = []

    for target_table, full_mapping in (compatibility_rules or DEFAULT_COLUMN_COMPATIBILITY_RULES).items():
        if not full_mapping:
            continue

        if missing_columns:
            effective_mapping = {
                source: target
                for source, target in full_mapping.items()
                if source in missing_columns
            }
            if not effective_mapping:
                continue
        else:
            effective_mapping = dict(full_mapping)

        candidate_sql = _rewrite_columns_for_target_table(
            rewritten_sql,
            target_table=target_table,
            column_mapping=effective_mapping,
        )
        if candidate_sql == rewritten_sql:
            continue

        for source, target in effective_mapping.items():
            applied_items.append(f"{source}->{target}")
        rewritten_sql = candidate_sql

    if rewritten_sql == sql:
        return sql, None

    reason = "检测到字段不兼容，已自动替换字段: " + ", ".join(applied_items)
    return rewritten_sql, reason


def rewrite_sql_for_empty_result(
    sql: str,
    probe_has_rows: Optional[Callable[[str, Optional[str]], bool]] = None,
    rewrite_rules: Optional[Sequence[RewriteRule]] = None,
) -> Tuple[str, Optional[str]]:
    """在空结果场景下按规则尝试 SQL 表替换。"""
    rules = rewrite_rules or DEFAULT_EMPTY_RESULT_REWRITE_RULES
    probe = probe_has_rows or has_rows_for_table

    data_dt = extract_data_dt_from_sql(sql)
    lowered_sql = sql.lower()

    for raw_rule in rules:
        try:
            source_table, target_table, reason, column_mapping = _normalize_rewrite_rule(raw_rule)
        except ValueError as exc:
            logger.warning("跳过无效空结果重写规则: %s", exc)
            continue

        if source_table not in lowered_sql:
            continue

        try:
            if not probe(target_table, data_dt):
                continue
        except Exception as exc:
            logger.debug("空结果重写预检查失败: %s", exc)
            continue

        replaced_sql = re.sub(
            rf"\b{re.escape(source_table)}\b",
            target_table,
            sql,
            flags=re.IGNORECASE,
        )

        if replaced_sql != sql:
            rewritten_sql = _rewrite_columns_for_target_table(replaced_sql, target_table, column_mapping)
            return rewritten_sql, reason

    return sql, None
