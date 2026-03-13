"""Deterministic resolver / guardrails for data intent."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Iterable, Optional

from sqlalchemy import text

from app.ai.router.data_intent_contract import DataIntentContract, build_clarify_contract
from app.db.session import engine
from app.services.metric_service import get_metric_service
from app.services.time_parser import NaturalTimeParser

MetricFetcher = Callable[[str], dict[str, Any] | None]
DimensionFetcher = Callable[[list[str]], list[dict[str, Any]]]


def _compact(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip()


def _default_metric_fetcher(metric_name: str) -> dict[str, Any] | None:
    if not str(metric_name or "").strip():
        return None
    matched = get_metric_service().match_metric(metric_name)
    if matched is None:
        return None
    return {
        "metric_id": str(getattr(matched, "metric_id", "") or ""),
        "metric_name": str(getattr(matched, "metric_name", "") or metric_name),
        "query_template": str(getattr(matched, "sql_template", "") or ""),
        "source": "t_metric_definition",
    }


def _default_dimension_fetcher(names: list[str]) -> list[dict[str, Any]]:
    requested = [str(item).strip() for item in names if str(item).strip()]
    if not requested:
        return []

    clauses: list[str] = []
    params: dict[str, Any] = {}
    for idx, item in enumerate(requested):
        key = f"name_{idx}"
        params[key] = f"%{item}%"
        clauses.append(
            f"(COALESCE(display_name, column_name) ILIKE :{key} OR column_name ILIKE :{key} OR COALESCE(description, '') ILIKE :{key})"
        )
    sql = f"""
        SELECT column_name, COALESCE(display_name, column_name) AS display_name
        FROM t_meta_columns
        WHERE {' OR '.join(clauses)}
        LIMIT 100
    """

    resolved: list[dict[str, Any]] = []
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    for requested_name in requested:
        for row in rows:
            display_name = str(getattr(row, "display_name", "") or row[1] or "").strip()
            column_name = str(getattr(row, "column_name", "") or row[0] or "").strip()
            if requested_name in {display_name, column_name} or requested_name in display_name:
                resolved.append(
                    {
                        "requested": requested_name,
                        "canonical": display_name or requested_name,
                        "column_name": column_name,
                        "source": "t_meta_columns",
                    }
                )
                break
    return resolved


def resolve_metric_source_of_truth(
    metric_name: str,
    *,
    fetcher: Optional[MetricFetcher] = None,
) -> dict[str, Any]:
    resolved = (fetcher or _default_metric_fetcher)(str(metric_name or "").strip())
    if not isinstance(resolved, dict):
        return {}
    return {
        "metric_id": str(resolved.get("metric_id") or ""),
        "metric_name": str(resolved.get("metric_name") or metric_name or ""),
        "query_template": str(resolved.get("query_template") or ""),
        "source": "t_metric_definition",
    }



def resolve_dimension_with_whitelist(
    dimensions: Iterable[str],
    *,
    fetcher: Optional[DimensionFetcher] = None,
) -> list[dict[str, Any]]:
    requested = [str(item).strip() for item in dimensions if str(item).strip()]
    resolved = (fetcher or _default_dimension_fetcher)(requested)
    normalized: list[dict[str, Any]] = []
    for item in resolved or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "requested": str(item.get("requested") or "").strip(),
                "canonical": str(item.get("canonical") or item.get("requested") or "").strip(),
                "column_name": str(item.get("column_name") or "").strip(),
                "source": "t_meta_columns",
            }
        )
    return normalized



def resolve_chart_slots(slots: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(slots or {})
    chart_type = str(resolved.get("chart_type") or "").strip()
    if chart_type in {"柱形图", "条形图"}:
        resolved["chart_type"] = "柱状图"
    if not resolved.get("display_mode") and resolved.get("chart_type"):
        resolved["display_mode"] = resolved.get("chart_type")
    return resolved



def resolve_data_intent(
    contract: dict[str, Any],
    *,
    user_text: str,
    metric_source_fetcher: Optional[MetricFetcher] = None,
    dimension_source_fetcher: Optional[DimensionFetcher] = None,
    time_parser_cls: type[NaturalTimeParser] = NaturalTimeParser,
) -> dict[str, Any]:
    resolved: dict[str, Any] = dict(contract or {})
    resolved["blocked_by"] = []
    resolved["resolved_sources"] = {}

    if resolved.get("decision") != "accept":
        resolved["safe_to_execute"] = False
        return resolved

    slots = resolve_chart_slots(dict(resolved.get("slots") or {}))
    metric_name = str(slots.get("metric") or "").strip()
    metric_info = resolve_metric_source_of_truth(metric_name, fetcher=metric_source_fetcher)
    if not metric_info:
        resolved["safe_to_execute"] = False
        resolved["reason_code"] = "metric_not_found"
        resolved["blocked_by"] = ["metric_not_found"]
        resolved["slots"] = slots
        return resolved
    resolved["resolved_sources"]["metric"] = metric_info["source"]

    requested_dimensions = [str(item).strip() for item in list(slots.get("dimensions") or []) if str(item).strip()]
    dimension_rows = resolve_dimension_with_whitelist(requested_dimensions, fetcher=dimension_source_fetcher)
    if requested_dimensions and len(dimension_rows) != len(requested_dimensions):
        resolved["safe_to_execute"] = False
        resolved["reason_code"] = "dimension_not_whitelisted"
        resolved["blocked_by"] = ["dimension_not_whitelisted"]
        resolved["slots"] = slots
        return resolved
    if dimension_rows:
        resolved["resolved_sources"]["dimensions"] = "t_meta_columns"
        slots["dimensions"] = [item["canonical"] for item in dimension_rows]

    raw_time = str(slots.get("time_range") or "").strip()
    if not raw_time:
        resolved["decision"] = "needs_clarification"
        resolved["route"] = "clarification"
        resolved["reason_code"] = "missing_time_range"
        resolved["blocked_by"] = ["missing_time_range"]
        resolved["clarify"] = build_clarify_contract(
            target_slot="time_range",
            reason_code="missing_time_range",
            prompt_template_key="ask_time_range",
        )
        resolved["slots"] = slots
        resolved["safe_to_execute"] = False
        return resolved

    if raw_time:
        parsed_time = time_parser_cls().parse_data_time_range(raw_time)
        if not parsed_time:
            resolved["safe_to_execute"] = False
            resolved["reason_code"] = "time_parse_failed"
            resolved["blocked_by"] = ["time_parse_failed"]
            resolved["slots"] = slots
            return resolved
        slots["time_range"] = parsed_time

    resolved["slots"] = slots
    resolved["safe_to_execute"] = True
    return resolved
