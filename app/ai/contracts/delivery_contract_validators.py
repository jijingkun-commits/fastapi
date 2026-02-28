"""交付合同校验器。"""

from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from app.ai.contracts.delivery_contracts import CoverageReportContract, IntentPlanContract


def _extract_validation_error(exc: ValidationError) -> str:
    first = (exc.errors() or [{}])[0]
    err_type = str(first.get("type") or "unknown")
    err_loc = first.get("loc") or ()
    loc_text = ".".join(str(part) for part in err_loc)
    if loc_text:
        return f"validation_error:{err_type}@{loc_text}"
    return f"validation_error:{err_type}"


def _build_fallback_intent_plan(user_query: str) -> Dict[str, Any]:
    return {
        "version": 1,
        "source": "contract_fallback",
        "user_query": str(user_query or ""),
        "goals": [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "general.reply",
                "title": "问题回复",
                "must_answer": True,
                "allowed_agents": [],
                "source": "contract_fallback",
                "confidence": None,
            }
        ],
    }


def _build_fallback_coverage_report(raw_data: Any) -> Dict[str, Any]:
    source = raw_data if isinstance(raw_data, dict) else {}
    total_goals = int(source.get("total_goals") or 0)
    answered_goals = int(source.get("answered_goals") or 0)
    missing = list(source.get("missing_goals") or [])
    if not missing:
        missing = [
            {
                "goal_id": "UNKNOWN",
                "title": "未知目标",
                "reason": "coverage_contract_invalid",
            }
        ]
    return {
        "pass": False,
        "total_goals": max(total_goals, answered_goals),
        "answered_goals": max(min(answered_goals, total_goals or answered_goals), 0),
        "missing_goals": missing,
        "matched_goal_ids": list(source.get("matched_goal_ids") or []),
        "goal_results": dict(source.get("goal_results") or {}),
    }


def validate_intent_plan_contract(raw_data: Any) -> Tuple[Dict[str, Any], bool, str]:
    """校验 intent_plan 合同，失败时返回兜底合同。"""
    try:
        model = IntentPlanContract.model_validate(raw_data)
        normalized = model.model_dump()
        normalized["goals"] = sorted(
            list(normalized.get("goals") or []),
            key=lambda item: int(item.get("order") or 0),
        )
        return normalized, True, ""
    except ValidationError as exc:
        user_query = ""
        if isinstance(raw_data, dict):
            user_query = str(raw_data.get("user_query") or "")
        return _build_fallback_intent_plan(user_query), False, _extract_validation_error(exc)


def validate_coverage_report_contract(raw_data: Any) -> Tuple[Dict[str, Any], bool, str]:
    """校验 coverage_report 合同，失败时返回兜底报告。"""
    try:
        model = CoverageReportContract.model_validate(raw_data)
        normalized = model.model_dump(by_alias=True)
        normalized["goal_results"] = {
            key: value for key, value in dict(normalized.get("goal_results") or {}).items()
        }
        return normalized, True, ""
    except ValidationError as exc:
        fallback = _build_fallback_coverage_report(raw_data)
        return fallback, False, _extract_validation_error(exc)


def build_contract_validation_meta(
    *,
    existing_meta: Optional[Dict[str, Any]] = None,
    intent_plan_valid: Optional[bool] = None,
    intent_plan_error: str = "",
    coverage_valid: Optional[bool] = None,
    coverage_error: str = "",
) -> Dict[str, Any]:
    """合并 contract 校验元数据，避免覆盖其他 delivery_meta 字段。"""
    merged = dict(existing_meta or {})

    if intent_plan_valid is not None:
        merged["intent_plan_valid"] = bool(intent_plan_valid)
        merged["intent_plan_error"] = str(intent_plan_error or "")

    if coverage_valid is not None:
        merged["coverage_valid"] = bool(coverage_valid)
        merged["coverage_error"] = str(coverage_error or "")

    return merged
