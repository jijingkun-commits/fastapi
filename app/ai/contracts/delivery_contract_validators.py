"""交付合同校验器。"""

from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from app.ai.contracts.delivery_contracts import (
    ActiveGoalsContract,
    CoverageReportContract,
)


def _extract_validation_error(exc: ValidationError) -> str:
    first = (exc.errors() or [{}])[0]
    err_type = str(first.get("type") or "unknown")
    err_loc = first.get("loc") or ()
    loc_text = ".".join(str(part) for part in err_loc)
    if loc_text:
        return f"validation_error:{err_type}@{loc_text}"
    return f"validation_error:{err_type}"


def _build_fallback_active_goals_contract(user_query: str) -> Dict[str, Any]:
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


def _coerce_active_goals_payload(
    raw_data: Any,
    *,
    source: str,
    user_query: str,
) -> Dict[str, Any]:
    default_source = str(source or "runtime_active_goals")
    default_user_query = str(user_query or "")

    if isinstance(raw_data, dict):
        source_data = dict(raw_data)
        if isinstance(source_data.get("goals"), list):
            return {
                "version": source_data.get("version") or 1,
                "source": str(source_data.get("source") or default_source),
                "user_query": str(source_data.get("user_query") or default_user_query),
                "goals": [goal for goal in list(source_data.get("goals") or []) if isinstance(goal, dict)],
            }

        decomposed_goals = source_data.get("decomposed_goals")
        if isinstance(decomposed_goals, list):
            return {
                "version": source_data.get("version") or 1,
                "source": str(source_data.get("source") or default_source),
                "user_query": str(source_data.get("user_query") or default_user_query),
                "goals": [goal for goal in decomposed_goals if isinstance(goal, dict)],
            }

    if isinstance(raw_data, (list, tuple)):
        return {
            "version": 1,
            "source": default_source,
            "user_query": default_user_query,
            "goals": [goal for goal in raw_data if isinstance(goal, dict)],
        }

    return {
        "version": 1,
        "source": default_source,
        "user_query": default_user_query,
        "goals": [],
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


def validate_active_goals_contract(
    raw_data: Any,
    *,
    source: str = "runtime_active_goals",
    user_query: str = "",
) -> Tuple[Dict[str, Any], bool, str]:
    """校验活动目标合同，失败时返回最小可执行兜底。"""
    normalized_raw = _coerce_active_goals_payload(
        raw_data,
        source=source,
        user_query=user_query,
    )
    try:
        model = ActiveGoalsContract.model_validate(normalized_raw)
        normalized = model.model_dump()
        normalized["goals"] = sorted(
            list(normalized.get("goals") or []),
            key=lambda item: int(item.get("order") or 0),
        )
        return normalized, True, ""
    except ValidationError as exc:
        fallback_query = str(normalized_raw.get("user_query") or user_query or "")
        return _build_fallback_active_goals_contract(fallback_query), False, _extract_validation_error(exc)


def validate_intent_plan_contract(raw_data: Any) -> Tuple[Dict[str, Any], bool, str]:
    """兼容入口：转发到 active_goals 合同校验。"""
    compat_source = "compat_intent_plan"
    compat_user_query = ""
    if isinstance(raw_data, dict):
        compat_source = str(raw_data.get("source") or compat_source)
        compat_user_query = str(raw_data.get("user_query") or "")

    return validate_active_goals_contract(
        raw_data,
        source=compat_source,
        user_query=compat_user_query,
    )


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
    active_goals_valid: Optional[bool] = None,
    active_goals_error: str = "",
    intent_plan_valid: Optional[bool] = None,
    intent_plan_error: str = "",
    coverage_valid: Optional[bool] = None,
    coverage_error: str = "",
) -> Dict[str, Any]:
    """合并 contract 校验元数据，避免覆盖其他 delivery_meta 字段。"""
    merged = dict(existing_meta or {})

    if active_goals_valid is not None:
        merged["active_goals_valid"] = bool(active_goals_valid)
        merged["active_goals_error"] = str(active_goals_error or "")

    compat_valid: Optional[bool] = intent_plan_valid
    compat_error = str(intent_plan_error or "")
    if compat_valid is None and active_goals_valid is not None:
        compat_valid = bool(active_goals_valid)
    if not compat_error and active_goals_error:
        compat_error = str(active_goals_error)
    if compat_valid is not None:
        merged["intent_plan_valid"] = bool(compat_valid)
        merged["intent_plan_error"] = compat_error

    if coverage_valid is not None:
        merged["coverage_valid"] = bool(coverage_valid)
        merged["coverage_error"] = str(coverage_error or "")

    return merged
