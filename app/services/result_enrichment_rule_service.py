"""结果增强规则加载服务（中文注释）。"""

from __future__ import annotations

from collections import Counter
import logging
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import text

from app.core.config import ANALYTICS_SCHEMAS, RESULT_ENRICHMENT_RULE_TTL_SECONDS
from app.db.session import get_db_context
from app.models.result_enrichment_rule import ResultEnrichmentRule
from app.repositories.result_enrichment_rule_repo import ResultEnrichmentRuleRepo

logger = logging.getLogger(__name__)

_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_ALLOWED_ANALYTICS_SCHEMAS = {schema.lower() for schema in ANALYTICS_SCHEMAS}


@dataclass(frozen=True)
class ResultLookupEnrichmentRuleConfig:
    """结果查表补齐规则配置。"""

    name: str
    key_column_candidates: Tuple[str, ...]
    target_column: str
    source_table: str
    source_key_column: str
    source_value_column: str
    source_date_column: Optional[str] = None
    result_date_column_candidates: Tuple[str, ...] = ("data_dt",)


class ResultEnrichmentRuleService:
    """结果增强规则服务（带 TTL 缓存与 fallback）。"""

    def __init__(
        self,
        repo: Optional[ResultEnrichmentRuleRepo] = None,
        ttl_seconds: Optional[int] = None,
    ):
        self._repo = repo or ResultEnrichmentRuleRepo()
        self._ttl_seconds = int(ttl_seconds or RESULT_ENRICHMENT_RULE_TTL_SECONDS)
        self._lock = threading.Lock()
        self._cached_rules: Optional[Tuple[ResultLookupEnrichmentRuleConfig, ...]] = None
        self._cached_at: Optional[datetime] = None

    def get_active_rules(
        self,
        force_refresh: bool = False,
        fallback_rules: Sequence[ResultLookupEnrichmentRuleConfig] = (),
    ) -> Tuple[ResultLookupEnrichmentRuleConfig, ...]:
        """获取启用规则（缓存优先，失败回退）。"""
        if not force_refresh:
            with self._lock:
                if self._cached_rules and self._cached_at and not self._is_expired(self._cached_at):
                    return self._cached_rules

        try:
            refreshed = self.refresh_rules(fallback_rules=fallback_rules)
            if refreshed:
                return refreshed
        except Exception as exc:
            logger.warning("刷新结果增强规则失败，将尝试使用旧缓存或 fallback: %s", exc)

        with self._lock:
            if self._cached_rules:
                return self._cached_rules

        return tuple(fallback_rules)

    def refresh_rules(
        self,
        fallback_rules: Sequence[ResultLookupEnrichmentRuleConfig] = (),
    ) -> Tuple[ResultLookupEnrichmentRuleConfig, ...]:
        """强制刷新规则缓存。"""
        db_rules = self._load_active_rules_from_db()
        if db_rules:
            with self._lock:
                self._cached_rules = db_rules
                self._cached_at = datetime.now()
            return db_rules

        fallback_tuple = tuple(fallback_rules)
        if fallback_tuple:
            with self._lock:
                self._cached_rules = fallback_tuple
                self._cached_at = datetime.now()
        return fallback_tuple

    def invalidate_cache(self) -> None:
        """手动失效缓存。"""
        with self._lock:
            self._cached_rules = None
            self._cached_at = None

    def validate_rule_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """校验并标准化规则入参。"""
        rule_code = str(payload.get("rule_code") or "").strip()
        if not rule_code:
            raise ValueError("rule_code 不能为空")
        self._ensure_identifier(rule_code, "rule_code")

        rule_name = str(payload.get("rule_name") or "").strip()
        if not rule_name:
            raise ValueError("rule_name 不能为空")

        target_column = str(payload.get("target_column") or "").strip()
        if not target_column:
            raise ValueError("target_column 不能为空")

        source_schema, source_table = self._split_source_table(str(payload.get("source_table") or "").strip())
        self._ensure_identifier(source_schema, "source_table.schema")
        self._ensure_identifier(source_table, "source_table.table")
        if source_schema.lower() not in _ALLOWED_ANALYTICS_SCHEMAS:
            raise ValueError(f"source_table schema 不在白名单: {source_schema}")

        source_key_column = str(payload.get("source_key_column") or "").strip()
        self._ensure_identifier(source_key_column, "source_key_column")

        source_value_column = str(payload.get("source_value_column") or "").strip()
        self._ensure_identifier(source_value_column, "source_value_column")

        source_date_column: Optional[str] = payload.get("source_date_column")
        source_date_column = str(source_date_column).strip() if source_date_column else None
        if source_date_column:
            self._ensure_identifier(source_date_column, "source_date_column")

        key_column_candidates = self._normalize_identifier_array(
            payload.get("key_column_candidates"),
            field_name="key_column_candidates",
        )
        result_date_column_candidates = self._normalize_identifier_array(
            payload.get("result_date_column_candidates"),
            field_name="result_date_column_candidates",
        )

        priority_value = payload.get("priority", 100)
        try:
            priority = int(priority_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("priority 必须是整数") from exc
        if priority < 0:
            raise ValueError("priority 不能小于 0")

        description = payload.get("description")
        description = str(description).strip() if description is not None else None

        normalized = {
            "rule_code": rule_code,
            "rule_name": rule_name,
            "enabled": bool(payload.get("enabled", True)),
            "priority": priority,
            "key_column_candidates": key_column_candidates,
            "target_column": target_column,
            "source_table": f"{source_schema}.{source_table}",
            "source_key_column": source_key_column,
            "source_value_column": source_value_column,
            "source_date_column": source_date_column,
            "result_date_column_candidates": result_date_column_candidates,
            "description": description,
        }
        return normalized

    def build_rule_config_from_payload(self, payload: Dict[str, Any]) -> ResultLookupEnrichmentRuleConfig:
        """将请求 payload 转成运行时规则配置。"""
        normalized = self.validate_rule_payload(payload)
        return ResultLookupEnrichmentRuleConfig(
            name=normalized["rule_code"],
            key_column_candidates=tuple(normalized["key_column_candidates"]),
            target_column=normalized["target_column"],
            source_table=normalized["source_table"],
            source_key_column=normalized["source_key_column"],
            source_value_column=normalized["source_value_column"],
            source_date_column=normalized["source_date_column"],
            result_date_column_candidates=tuple(normalized["result_date_column_candidates"]),
        )

    def _is_expired(self, cached_at: datetime) -> bool:
        """判断缓存是否过期。"""
        return datetime.now() - cached_at >= timedelta(seconds=max(self._ttl_seconds, 1))

    def _load_active_rules_from_db(self) -> Tuple[ResultLookupEnrichmentRuleConfig, ...]:
        """从数据库加载启用规则并校验。"""
        with get_db_context() as db:
            orm_rules = self._repo.list_active_rules(db)
            parsed = [self._validate_and_convert_rule(rule) for rule in orm_rules]
            valid_rules = [rule for rule in parsed if rule is not None]

        return tuple(valid_rules)

    def _validate_and_convert_rule(
        self,
        rule: ResultEnrichmentRule,
    ) -> Optional[ResultLookupEnrichmentRuleConfig]:
        """校验并转换单条规则。"""
        payload = {
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "enabled": rule.enabled,
            "priority": rule.priority,
            "key_column_candidates": rule.key_column_candidates,
            "target_column": rule.target_column,
            "source_table": rule.source_table,
            "source_key_column": rule.source_key_column,
            "source_value_column": rule.source_value_column,
            "source_date_column": rule.source_date_column,
            "result_date_column_candidates": rule.result_date_column_candidates,
            "description": rule.description,
        }
        try:
            return self.build_rule_config_from_payload(payload)
        except Exception as exc:
            logger.warning("结果增强规则跳过(rule_code=%s): %s", rule.rule_code, exc)
            return None

    @staticmethod
    def _split_source_table(source_table: str) -> Tuple[str, str]:
        """拆分 source_table。"""
        raw = str(source_table or "").strip()
        if "." not in raw:
            raise ValueError("source_table 必须是 schema.table 格式")
        schema, table = raw.split(".", 1)
        if not schema or not table:
            raise ValueError("source_table 必须是 schema.table 格式")
        return schema, table

    @staticmethod
    def _ensure_identifier(value: str, field_name: str) -> None:
        """校验标识符合法性。"""
        raw = str(value or "").strip()
        if not raw or not _IDENTIFIER_PATTERN.fullmatch(raw):
            raise ValueError(f"{field_name} 非法: {value}")

    def _normalize_identifier_array(self, value: Any, field_name: str) -> List[str]:
        """标准化并校验标识符数组。"""
        if not isinstance(value, list):
            raise ValueError(f"{field_name} 必须是数组")

        normalized: List[str] = []
        for item in value:
            raw = str(item or "").strip()
            if not raw:
                continue
            self._ensure_identifier(raw, field_name)
            if raw not in normalized:
                normalized.append(raw)

        if not normalized:
            raise ValueError(f"{field_name} 不能为空")
        return normalized

    @property
    def ttl_seconds(self) -> int:
        """返回当前 TTL。"""
        return self._ttl_seconds


_service_singleton: Optional[ResultEnrichmentRuleService] = None


def get_result_enrichment_rule_service() -> ResultEnrichmentRuleService:
    """获取规则服务单例。"""
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = ResultEnrichmentRuleService()
    return _service_singleton


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
    rule: ResultLookupEnrichmentRuleConfig,
    key_values: List[str],
    date_value: Optional[str],
) -> Dict[str, str]:
    """按规则查表补齐映射（优先同日，失败回退全量）。"""
    if not key_values:
        return {}

    from app.db.session import analytics_engine

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
        except Exception as exc:
            logger.warning(
                "结果补齐规则执行失败(name=%s, date=%s): %s",
                rule.name,
                date_value,
                exc,
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
    except Exception as exc:
        logger.warning("结果补齐规则回退失败(name=%s): %s", rule.name, exc)

    merged = dict(exact_map)
    merged.update(fallback_map)
    return merged


def apply_lookup_enrichment_rule(
    rows: List[Dict[str, Any]],
    columns: List[str],
    rule: ResultLookupEnrichmentRuleConfig,
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
