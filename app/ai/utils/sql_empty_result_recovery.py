"""SQL 空结果恢复工具。"""
import logging
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import text

from app.db.session import analytics_engine

logger = logging.getLogger(__name__)


# 空结果重写规则：源表 -> 目标表 -> 提示原因
DEFAULT_EMPTY_RESULT_REWRITE_RULES: Sequence[Tuple[str, str, str]] = (
    (
        "fdmdata.f_mid_loan_tb",
        "fdmdata.f_mid_loan_k_tb",
        "f_mid_loan_tb 无数据，改用 f_mid_loan_k_tb",
    ),
)


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


def rewrite_sql_for_empty_result(
    sql: str,
    probe_has_rows: Optional[Callable[[str, Optional[str]], bool]] = None,
    rewrite_rules: Optional[Sequence[Tuple[str, str, str]]] = None,
) -> Tuple[str, Optional[str]]:
    """在空结果场景下按规则尝试 SQL 表替换。"""
    rules = rewrite_rules or DEFAULT_EMPTY_RESULT_REWRITE_RULES
    probe = probe_has_rows or has_rows_for_table

    data_dt = extract_data_dt_from_sql(sql)
    lowered_sql = sql.lower()

    for source_table, target_table, reason in rules:
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
            return replaced_sql, reason

    return sql, None

