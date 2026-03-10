"""会话意图内核（跨 data/todo 复用）。

职责：
1. 统一回合行为分类（TurnAct）
2. 统一会话帧合并（SessionFrameReducer）
3. 提供澄清状态的轻量辅助能力
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

TURN_ACT_NEW_QUERY = "NEW_QUERY"
TURN_ACT_SUPPLEMENT = "SUPPLEMENT"
TURN_ACT_CORRECTION = "CORRECTION"
TURN_ACT_CONFIRM = "CONFIRM"
TURN_ACT_UNKNOWN = "UNKNOWN"


DATA_HANDOFF_GENERIC_DESC_PREFIXES = (
    "请按模型建议处理",
    "请执行复杂口径确认后再输出",
    "请继续处理",
    "请处理",
)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    return []


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def normalize_session_frame(frame: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """规范化会话帧结构，确保下游比较稳定。"""
    raw = frame if isinstance(frame, dict) else {}
    normalized = {
        "metric": _normalize_text(raw.get("metric") or raw.get("metric_name")),
        "time_range": _normalize_text(raw.get("time_range")),
        "dimensions": _normalize_text_list(raw.get("dimensions")),
        "org_level": _normalize_text(raw.get("org_level")),
        "chart_type": _normalize_text(raw.get("chart_type")),
        "filters": _normalize_text_list(raw.get("filters")),
        "query_shape": _normalize_text(raw.get("query_shape")),
        "ranking": dict(raw.get("ranking")) if isinstance(raw.get("ranking"), dict) else {},
        "todo_action": _normalize_text(raw.get("todo_action") or raw.get("action")),
        "todo_target_id": _normalize_text(raw.get("todo_target_id") or raw.get("todo_id")),
        "todo_fields": dict(raw.get("todo_fields")) if isinstance(raw.get("todo_fields"), dict) else {},
    }
    return normalized


def reduce_session_frame(
    current_frame: Optional[Dict[str, Any]],
    handoff_frame: Optional[Dict[str, Any]],
    state_frame: Optional[Dict[str, Any]],
    default_frame: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """按优先级合并会话帧：current > handoff > state > default。"""
    current = normalize_session_frame(current_frame)
    handoff = normalize_session_frame(handoff_frame)
    state = normalize_session_frame(state_frame)
    default = normalize_session_frame(default_frame)

    merged: Dict[str, Any] = {}
    source_map: Dict[str, str] = {}

    for key in current.keys():
        candidates = (
            ("current", current.get(key)),
            ("handoff", handoff.get(key)),
            ("state", state.get(key)),
            ("default", default.get(key)),
        )
        selected_value: Any = None
        selected_source = ""
        for source, value in candidates:
            if _is_empty(value):
                continue
            selected_value = value
            selected_source = source
            break

        if selected_value is None:
            # 保持字段结构稳定
            if key in {"dimensions", "filters"}:
                selected_value = []
            elif key == "todo_fields":
                selected_value = {}
            else:
                selected_value = ""
            selected_source = "none"

        merged[key] = selected_value
        source_map[key] = selected_source

    return merged, source_map


def _match_policy_pattern(compact_text: str, patterns: list[str]) -> Optional[str]:
    for pattern in patterns:
        try:
            if re.search(pattern, compact_text, re.IGNORECASE):
                return pattern
        except re.error:
            continue
    return None


def classify_turn_act(
    text: str,
    *,
    has_prior_context: bool,
    baseline_frame: Optional[Dict[str, Any]] = None,
    current_frame: Optional[Dict[str, Any]] = None,
    policy: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """统一回合行为分类。

    返回：(turn_act, reason)
    """
    compact = re.sub(r"\s+", "", _normalize_text(text))
    if not compact:
        return TURN_ACT_UNKNOWN, "empty_input"

    baseline = normalize_session_frame(baseline_frame)
    current = normalize_session_frame(current_frame)

    if not has_prior_context:
        return TURN_ACT_NEW_QUERY, "no_prior_context"

    if "?" in compact or "？" in compact:
        return TURN_ACT_NEW_QUERY, "question_like"

    policy_data = policy if isinstance(policy, dict) else {}

    new_query_patterns = [str(item) for item in (policy_data.get("new_query_patterns") or []) if str(item).strip()]
    matched_new_query = _match_policy_pattern(compact, new_query_patterns)
    if matched_new_query:
        return TURN_ACT_NEW_QUERY, "policy_new_query_pattern"

    continuation_patterns = [str(item) for item in (policy_data.get("continuation_patterns") or []) if str(item).strip()]
    matched_continuation = _match_policy_pattern(compact, continuation_patterns)
    if matched_continuation:
        return TURN_ACT_SUPPLEMENT, "policy_continuation_pattern"

    confirm_patterns = [str(item) for item in (policy_data.get("confirm_patterns") or []) if str(item).strip()]
    matched_confirm = _match_policy_pattern(compact, confirm_patterns)
    if matched_confirm:
        return TURN_ACT_CONFIRM, "policy_confirm_pattern"

    baseline_metric = _normalize_text(baseline.get("metric"))
    current_metric = _normalize_text(current.get("metric"))
    if current_metric and baseline_metric and current_metric != baseline_metric:
        return TURN_ACT_CORRECTION, "metric_switched"
    if current_metric and not baseline_metric:
        return TURN_ACT_NEW_QUERY, "metric_without_baseline"

    baseline_time = _normalize_text(baseline.get("time_range"))
    current_time = _normalize_text(current.get("time_range"))
    if current_time and baseline_time and current_time != baseline_time:
        return TURN_ACT_CORRECTION, "time_switched"

    if current.get("chart_type"):
        return TURN_ACT_SUPPLEMENT, "chart_hint"
    if current.get("org_level"):
        return TURN_ACT_SUPPLEMENT, "org_level_hint"
    if current_time:
        return TURN_ACT_SUPPLEMENT, "time_hint"

    current_dims = _normalize_text_list(current.get("dimensions"))
    baseline_dims = set(_normalize_text_list(baseline.get("dimensions")))
    if current_dims:
        if not baseline_dims:
            return TURN_ACT_SUPPLEMENT, "dimension_hint"
        if any(dim not in baseline_dims for dim in current_dims):
            return TURN_ACT_SUPPLEMENT, "dimension_delta_hint"

    current_filters = _normalize_text_list(current.get("filters"))
    if current_filters:
        return TURN_ACT_SUPPLEMENT, "filter_hint"

    current_todo_fields = current.get("todo_fields") or {}
    if isinstance(current_todo_fields, dict) and any(not _is_empty(v) for v in current_todo_fields.values()):
        return TURN_ACT_SUPPLEMENT, "todo_field_hint"

    if _normalize_text(current.get("todo_target_id")):
        return TURN_ACT_SUPPLEMENT, "todo_target_hint"

    ack_patterns = [str(item) for item in (policy_data.get("ack_patterns") or []) if str(item).strip()]
    matched_ack = _match_policy_pattern(compact, ack_patterns)
    if matched_ack:
        return TURN_ACT_SUPPLEMENT, "policy_ack_pattern"

    if compact in {"好", "好的", "行", "可以", "确认", "对", "嗯", "ok", "OK"}:
        return TURN_ACT_CONFIRM, "short_confirm"

    if len(compact) <= 20:
        return TURN_ACT_SUPPLEMENT, "short_reply_with_context"

    return TURN_ACT_NEW_QUERY, "insufficient_signal"


def classify_data_handoff_task_description(raw_desc: str, user_desc: str) -> str:
    """判定 data handoff 描述是 specific/generic/empty。"""
    normalized_raw = re.sub(r"\s+", " ", _normalize_text(raw_desc)).strip()[:240]
    normalized_user = re.sub(r"\s+", " ", _normalize_text(user_desc)).strip()[:240]
    compact_raw = re.sub(r"\s+", "", normalized_raw)

    if not compact_raw:
        return "empty"

    if normalized_user and normalized_raw in {normalized_user, f"用户原始问题：{normalized_user}"}:
        return "generic"

    compact_prefixes = tuple(re.sub(r"\s+", "", item) for item in DATA_HANDOFF_GENERIC_DESC_PREFIXES)
    if any(compact_raw.startswith(prefix) for prefix in compact_prefixes):
        return "generic"

    if normalized_user and len(compact_raw) < 16 and not re.search(r"\d", compact_raw):
        return "generic"

    return "specific"


def advance_clarify_fsm_state(prev_state: str, missing_slots: list[str]) -> str:
    """根据缺项推进澄清状态机。"""
    slot_map = {
        "metric": "asked_metric",
        "time_range": "asked_time",
        "org_level": "asked_org",
        "todo_target": "asked_target",
        "todo_action": "asked_action",
    }
    if not missing_slots:
        return "done"
    first_slot = str(missing_slots[0]).strip()
    return slot_map.get(first_slot, prev_state or "idle")
