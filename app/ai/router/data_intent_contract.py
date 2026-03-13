"""Data intent contract definitions."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict

DecisionType = Literal["accept", "reject", "needs_clarification"]
RouteType = Literal["metric_query", "detail_query", "visualization", "clarification", "handoff_data"]
ClarifySlot = Literal["metric", "time_range", "dimensions", "chart_type", "org_level", "display_mode"]


class ClarifyContract(TypedDict):
    target_slot: ClarifySlot
    reason_code: str
    prompt_template_key: str


class DataIntentSlots(TypedDict, total=False):
    metric: str
    time_range: str | None
    dimensions: List[str]
    chart_type: str | None
    org_level: str | None
    top_n: int | None
    display_mode: str | None
    query_shape: str | None
    ranking: Dict[str, Any]


class DataIntentContract(TypedDict, total=False):
    decision: DecisionType
    route: RouteType
    confidence: float
    reason_code: str
    evidence_codes: List[str]
    conflict_codes: List[str]
    slots: DataIntentSlots
    safe_to_execute: bool
    detector: str
    shadow_compare: Dict[str, Any]
    clarify: ClarifyContract


_EMPTY_SLOTS: DataIntentSlots = {
    "metric": "",
    "time_range": None,
    "dimensions": [],
    "chart_type": None,
    "org_level": None,
    "top_n": None,
    "display_mode": None,
    "query_shape": None,
    "ranking": {},
}


def empty_slots() -> DataIntentSlots:
    return {
        "metric": "",
        "time_range": None,
        "dimensions": [],
        "chart_type": None,
        "org_level": None,
        "top_n": None,
        "display_mode": None,
        "query_shape": None,
        "ranking": {},
    }


def build_clarify_contract(
    *,
    target_slot: ClarifySlot,
    reason_code: str,
    prompt_template_key: str,
) -> ClarifyContract:
    return {
        "target_slot": target_slot,
        "reason_code": reason_code,
        "prompt_template_key": prompt_template_key,
    }


def build_data_intent_contract(
    *,
    decision: DecisionType,
    route: RouteType,
    confidence: float,
    reason_code: str,
    evidence_codes: list[str] | None = None,
    conflict_codes: list[str] | None = None,
    slots: DataIntentSlots | None = None,
    safe_to_execute: bool = False,
    detector: str = "rule_primary",
    clarify: ClarifyContract | None = None,
    shadow_compare: Dict[str, Any] | None = None,
) -> DataIntentContract:
    contract: DataIntentContract = {
        "decision": decision,
        "route": route,
        "confidence": round(float(confidence), 4),
        "reason_code": reason_code,
        "evidence_codes": list(evidence_codes or []),
        "conflict_codes": list(conflict_codes or []),
        "slots": dict(empty_slots() if slots is None else slots),
        "safe_to_execute": bool(safe_to_execute),
        "detector": detector,
    }
    if clarify:
        contract["clarify"] = dict(clarify)
    if shadow_compare:
        contract["shadow_compare"] = dict(shadow_compare)
    return contract
