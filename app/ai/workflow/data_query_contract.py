"""问数 query contract 归一工具。"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Sequence

_VALID_QUERY_SHAPES = {"total", "dimension", "top_n"}
_VALID_SORT_ORDERS = {"asc", "desc"}


def _positive_int(value: Any) -> int:
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed_value if parsed_value > 0 else 0


def extract_top_n(question: str, default_n: int = 10) -> int:
    normalized = re.sub(r"\s+", "", question or "")
    match = re.search(r"前(\d+)", normalized)
    if not match:
        match = re.search(r"top(\d+)", normalized, re.IGNORECASE)
    if not match:
        return default_n

    try:
        return max(1, min(int(match.group(1)), 100))
    except Exception:
        return default_n


def detect_query_shape(
    question: str,
    dimensions: Optional[Sequence[str]] = None,
    *,
    fallback_total: bool = True,
) -> str:
    normalized = re.sub(r"\s+", "", question or "")
    if re.search(r"前\d+|top\d+|排名|排行", normalized, re.IGNORECASE):
        return "top_n"

    dims = dimensions if isinstance(dimensions, (list, tuple)) else []
    if any(str(dim).strip() for dim in dims):
        return "dimension"

    return "total" if fallback_total else ""


def build_query_contract(
    question: str,
    *,
    dimensions: Optional[Sequence[str]] = None,
    metric: str = "",
    query_shape: Any = "",
    ranking: Any = None,
    fallback_total: bool = True,
) -> Dict[str, Any]:
    resolved_shape = str(query_shape or "").strip().lower()
    if resolved_shape not in _VALID_QUERY_SHAPES:
        resolved_shape = detect_query_shape(
            question,
            dimensions,
            fallback_total=fallback_total,
        )
    if not resolved_shape:
        return {}

    contract: Dict[str, Any] = {"query_shape": resolved_shape}
    if resolved_shape != "top_n":
        return contract

    raw_ranking = dict(ranking) if isinstance(ranking, dict) else {}
    limit = _positive_int(raw_ranking.get("limit")) or extract_top_n(question, default_n=10)
    if limit <= 0:
        return contract

    sort_order = str(raw_ranking.get("sort_order") or "desc").strip().lower() or "desc"
    if sort_order not in _VALID_SORT_ORDERS:
        sort_order = "desc"

    contract["ranking"] = {
        "limit": limit,
        "sort_by": str(raw_ranking.get("sort_by") or metric or "").strip(),
        "sort_order": sort_order,
    }
    return contract
