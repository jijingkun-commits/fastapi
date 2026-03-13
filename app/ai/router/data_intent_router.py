"""Rule-primary data intent router."""

from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

from sqlalchemy import text as sql_text

from app.db.session import engine

from app.ai.router.data_intent_contract import (
    DataIntentContract,
    DataIntentSlots,
    build_clarify_contract,
    build_data_intent_contract,
    empty_slots,
)
from app.ai.workflow.data_query_contract import build_query_contract
from app.ai.workflow.session_intent_kernel import normalize_session_frame

ShadowRunner = Callable[[str], Awaitable[dict]]


def _compact(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip()


def _normalize_catalog_items(items: Optional[Iterable[dict]]) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        normalized.append(dict(item))
    return normalized


def _default_metric_catalog() -> list[dict]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(sql_text("SELECT metric_name, aliases FROM t_metric_definition WHERE is_active = TRUE"))
            return [
                {
                    "metric_name": str(getattr(row, "metric_name", "") or row[0] or "").strip(),
                    "aliases": [alias.strip() for alias in str(getattr(row, "aliases", "") or row[1] or "").split(",") if alias.strip()],
                }
                for row in rows
                if str(getattr(row, "metric_name", "") or row[0] or "").strip()
            ]
    except Exception:
        return []


def _default_dimension_catalog() -> list[dict]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(sql_text("SELECT DISTINCT COALESCE(display_name, column_name) AS name FROM t_meta_columns WHERE COALESCE(display_name, column_name) IS NOT NULL LIMIT 1000"))
            return [
                {"name": str(getattr(row, "name", "") or row[0] or "").strip()}
                for row in rows
                if str(getattr(row, "name", "") or row[0] or "").strip()
            ]
    except Exception:
        return []


def _extract_metric_from_catalog(text: str, metric_catalog: list[dict]) -> str:
    lowered = text.lower()
    best_metric = ""
    best_len = 0
    for item in metric_catalog:
        metric_name = str(item.get("metric_name") or item.get("name") or "").strip()
        aliases = item.get("aliases") or []
        candidates = [metric_name, *[str(alias).strip() for alias in aliases if str(alias).strip()]]
        for candidate in candidates:
            if not candidate:
                continue
            normalized = candidate.lower()
            if normalized in lowered and len(normalized) > best_len:
                best_metric = metric_name or candidate
                best_len = len(normalized)
    return best_metric


def _extract_time_range(text: str) -> str:
    compact = _compact(text)
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
    return relative_match.group(1) if relative_match else ""


def _extract_chart_type(text: str) -> str:
    compact = _compact(text)
    if not compact:
        return ""

    match = re.search(r"(柱状图|柱形图|条形图|饼图|折线图)", compact)
    if match:
        detected = match.group(1)
        return "柱状图" if detected in {"柱形图", "条形图"} else detected
    if re.search(r"(图表|图标|可视化|画图|出图|图看看|改成图)", compact):
        return "图表"
    return ""


def _extract_dimensions(text: str, dimension_catalog: list[dict]) -> list[str]:
    compact = _compact(text)
    if not compact:
        return []

    matched: list[str] = []
    explicit_dimension_patterns = (
        r"按(?P<name>[^，。；、\s]{1,8})(?:统计|分布|汇总|展示|查看|排序)?",
        r"(?P<name>[^，。；、\s]{1,8})(?:统计|分布)",
    )

    dimension_names = [str(item.get("name") or item.get("display_name") or "").strip() for item in dimension_catalog]
    dimension_names = [item for item in dimension_names if item]

    for pattern in explicit_dimension_patterns:
        for match in re.finditer(pattern, compact):
            name = str(match.groupdict().get("name") or "").strip()
            if not name:
                continue
            if dimension_names and name not in dimension_names:
                continue
            if name not in matched:
                matched.append(name)

    if not matched:
        for name in dimension_names:
            if name in {"分行", "支行", "机构", "客户", "日期"} and re.search(rf"按{name}|{name}(统计|分布)", compact):
                matched.append(name)

    return matched


def _extract_org_level(text: str) -> str:
    compact = _compact(text)
    if "支行" in compact:
        return "支行"
    if "分行" in compact:
        return "分行"
    if "总行" in compact:
        return "总行"
    return ""


def _build_slots(
    *,
    text: str,
    metric_catalog: list[dict],
    dimension_catalog: list[dict],
    session_frame: dict[str, Any],
    handoff_frame: dict[str, Any],
) -> DataIntentSlots:
    slots = empty_slots()
    slots["metric"] = _extract_metric_from_catalog(text, metric_catalog)
    slots["time_range"] = _extract_time_range(text) or None
    slots["dimensions"] = _extract_dimensions(text, dimension_catalog)
    chart_type = _extract_chart_type(text)
    slots["chart_type"] = chart_type or None
    slots["display_mode"] = chart_type or None
    slots["org_level"] = _extract_org_level(text) or None
    query_contract = build_query_contract(text, dimensions=slots["dimensions"], metric=slots["metric"])
    slots["query_shape"] = str(query_contract.get("query_shape") or "") or None
    ranking = query_contract.get("ranking") if isinstance(query_contract.get("ranking"), dict) else {}
    slots["ranking"] = dict(ranking)
    slots["top_n"] = int(ranking.get("limit")) if ranking.get("limit") else None

    if frame_supported_supplement(text, session_frame=session_frame, handoff_frame=handoff_frame):
        frame = session_frame if any(session_frame.get(key) for key in ("metric", "time_range", "dimensions", "chart_type")) else handoff_frame
        if not slots["metric"]:
            slots["metric"] = str(frame.get("metric") or frame.get("metric_name") or "")
        if not slots["time_range"]:
            slots["time_range"] = str(frame.get("time_range") or "") or None
        if not slots["dimensions"]:
            slots["dimensions"] = [str(item).strip() for item in list(frame.get("dimensions") or []) if str(item).strip()]
        if not slots["chart_type"]:
            inherited_chart = str(frame.get("chart_type") or "").strip()
            slots["chart_type"] = inherited_chart or slots["chart_type"]
        if not slots["display_mode"]:
            slots["display_mode"] = slots["chart_type"]
        if not slots["org_level"]:
            org_level = str(frame.get("org_level") or "").strip()
            slots["org_level"] = org_level or slots["org_level"]
    return slots


def build_candidate_signals(
    user_text: str,
    *,
    session_frame: Optional[dict[str, Any]] = None,
    handoff_frame: Optional[dict[str, Any]] = None,
    metric_catalog: Optional[Iterable[dict]] = None,
    dimension_catalog: Optional[Iterable[dict]] = None,
) -> list[dict[str, Any]]:
    session = normalize_session_frame(session_frame)
    handoff = normalize_session_frame(handoff_frame)
    metrics = _normalize_catalog_items(metric_catalog) or _default_metric_catalog()
    dimensions = _normalize_catalog_items(dimension_catalog) or _default_dimension_catalog()
    compact = _compact(user_text)
    if not compact:
        return []

    signals: list[dict[str, Any]] = []
    chart_type = _extract_chart_type(compact)
    if chart_type:
        signals.append({"code": "phrase_pattern_candidate.chart_request", "family": "lexical", "value": chart_type})

    extracted_dimensions = _extract_dimensions(compact, dimensions)
    for item in extracted_dimensions:
        signals.append({"code": f"keyword_candidate.dimension:{item}", "family": "lexical", "value": item})

    metric_name = _extract_metric_from_catalog(compact, metrics)
    if metric_name:
        signals.append({"code": f"metric_metadata_support:{metric_name}", "family": "support", "value": metric_name})

    time_range = _extract_time_range(compact)
    if time_range:
        signals.append({"code": f"resolver_precheck_support.time:{time_range}", "family": "support", "value": time_range})

    if frame_supported_supplement(compact, session_frame=session, handoff_frame=handoff):
        support_code = "session_frame_support" if any(session.get(key) for key in ("metric", "time_range", "dimensions", "chart_type")) else "handoff_frame_support"
        signals.append({"code": support_code, "family": "frame", "value": support_code})

    return signals


def frame_supported_supplement(
    user_text: str,
    *,
    session_frame: Optional[dict[str, Any]] = None,
    handoff_frame: Optional[dict[str, Any]] = None,
) -> bool:
    compact = _compact(user_text)
    if not compact:
        return False

    session = normalize_session_frame(session_frame)
    handoff = normalize_session_frame(handoff_frame)
    frame = session if any(session.get(key) for key in ("metric", "time_range", "dimensions", "chart_type")) else handoff
    has_frame_support = any(frame.get(key) for key in ("metric", "time_range", "dimensions", "chart_type"))
    if not has_frame_support:
        return False

    if len(compact) > 24:
        return False

    return bool(
        _extract_chart_type(compact)
        or _extract_dimensions(compact, [{"name": name} for name in ("机构", "客户", "日期", "分行", "支行")])
        or _extract_org_level(compact)
        or re.search(r"前\d+|top\d+|继续|改成|换成|图看看", compact, re.IGNORECASE)
    )


def decide_data_intent(
    user_text: str,
    *,
    session_frame: Optional[dict[str, Any]] = None,
    handoff_frame: Optional[dict[str, Any]] = None,
    metric_catalog: Optional[Iterable[dict]] = None,
    dimension_catalog: Optional[Iterable[dict]] = None,
) -> DataIntentContract:
    session = normalize_session_frame(session_frame)
    handoff = normalize_session_frame(handoff_frame)
    metrics = _normalize_catalog_items(metric_catalog) or _default_metric_catalog()
    dimensions = _normalize_catalog_items(dimension_catalog) or _default_dimension_catalog()
    compact = _compact(user_text)
    signals = build_candidate_signals(
        compact,
        session_frame=session,
        handoff_frame=handoff,
        metric_catalog=metrics,
        dimension_catalog=dimensions,
    )
    slots = _build_slots(
        text=compact,
        metric_catalog=metrics,
        dimension_catalog=dimensions,
        session_frame=session,
        handoff_frame=handoff,
    )

    lexical_signals = [item for item in signals if item.get("family") == "lexical"]
    support_signals = [item for item in signals if item.get("family") in {"support", "frame"}]
    evidence_codes = [str(item.get("code") or "") for item in signals if str(item.get("code") or "")]

    has_frame_supplement = frame_supported_supplement(compact, session_frame=session, handoff_frame=handoff)
    has_metric = bool(slots.get("metric"))
    has_time = bool(slots.get("time_range"))
    has_chart = bool(slots.get("chart_type"))
    has_dimensions = bool(slots.get("dimensions"))

    route = "metric_query"
    has_dimension_hint = any(str(item.get("code") or "").startswith("keyword_candidate.dimension") for item in lexical_signals)
    if has_chart:
        route = "visualization"
    elif has_dimensions or slots.get("query_shape") == "top_n":
        route = "detail_query"
    elif has_dimension_hint and not has_metric:
        route = "detail_query"

    if has_chart and not has_metric and not has_frame_supplement:
        return build_data_intent_contract(
            decision="needs_clarification",
            route="clarification",
            confidence=0.46,
            reason_code="missing_metric_time",
            evidence_codes=evidence_codes,
            conflict_codes=[],
            slots=slots,
            safe_to_execute=False,
            clarify=build_clarify_contract(
                target_slot="metric",
                reason_code="missing_metric_time",
                prompt_template_key="ask_metric_time_range",
            ),
        )

    if has_frame_supplement and (has_chart or has_dimensions or slots.get("top_n")):
        return build_data_intent_contract(
            decision="accept",
            route="visualization" if has_chart else route,
            confidence=0.9,
            reason_code="frame_supported_supplement",
            evidence_codes=evidence_codes or ["session_frame_support"],
            conflict_codes=[],
            slots=slots,
            safe_to_execute=False,
        )

    if len(lexical_signals) == 1 and not has_metric and not has_time and not support_signals:
        return build_data_intent_contract(
            decision="reject",
            route=route,
            confidence=0.18,
            reason_code="single_lexical_signal_forbidden",
            evidence_codes=evidence_codes,
            conflict_codes=[],
            slots=slots,
            safe_to_execute=False,
        )

    independent_signal_count = len(lexical_signals) + len(support_signals)
    if has_metric and independent_signal_count >= 2:
        return build_data_intent_contract(
            decision="accept",
            route=route,
            confidence=0.88 if has_chart else 0.81,
            reason_code="multi_signal_accept",
            evidence_codes=evidence_codes,
            conflict_codes=[],
            slots=slots,
            safe_to_execute=False,
        )

    if has_metric:
        return build_data_intent_contract(
            decision="accept",
            route="metric_query",
            confidence=0.74,
            reason_code="metric_supported_accept",
            evidence_codes=evidence_codes,
            conflict_codes=[],
            slots=slots,
            safe_to_execute=False,
        )

    return build_data_intent_contract(
        decision="reject",
        route=route,
        confidence=0.2,
        reason_code="insufficient_signal",
        evidence_codes=evidence_codes,
        conflict_codes=[],
        slots=slots,
        safe_to_execute=False,
    )


async def shadow_compare_async(
    *,
    user_text: str,
    primary_contract: dict,
    shadow_runner: Optional[ShadowRunner] = None,
) -> dict[str, Any]:
    if shadow_runner is None:
        return {"status": "disabled", "diff_fields": []}

    try:
        shadow_contract = dict(await shadow_runner(user_text) or {})
    except Exception as exc:  # pragma: no cover - defensive only
        return {
            "status": "shadow_failed",
            "error": str(exc),
            "diff_fields": [],
        }

    diff_fields = sorted(
        key
        for key in {*(primary_contract or {}).keys(), *shadow_contract.keys()}
        if (primary_contract or {}).get(key) != shadow_contract.get(key)
    )
    status = "match" if not diff_fields else "mismatch"
    return {
        "status": status,
        "diff_fields": diff_fields,
        "shadow_decision": shadow_contract.get("decision"),
        "shadow_reason_code": shadow_contract.get("reason_code"),
    }
