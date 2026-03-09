"""运行时回复策略服务。"""

from __future__ import annotations

from typing import Any, Dict, Sequence


_RESPONSE_GUIDANCE_KIND_MEMORY_ARCHIVE = "memory_archive"
_RESPONSE_GUIDANCE_STATUS_PERSISTED = "persisted"
_RESPONSE_GUIDANCE_STATUS_ALREADY_ABSENT = "already_absent"
_RESPONSE_GUIDANCE_FOLLOWUP_REUSE_RESOLVED_TARGET = "reuse_resolved_target"
_DELIVERY_RECOVERY_MARKER = "【交付补齐提示】"


def build_memory_archive_guidance_contract(
    decision_contract: dict[str, Any] | None,
    *,
    persisted_doc_count: int = 0,
) -> dict[str, Any] | None:
    """基于 archive 合同生成结构化回复约束。"""
    if not isinstance(decision_contract, dict):
        return None

    memories = decision_contract.get("memories")
    if not isinstance(memories, list) or len(memories) != 1:
        return None

    item = memories[0]
    if not isinstance(item, dict):
        return None
    if str(item.get("operation") or "").strip().lower() != "archive":
        return None

    canonical_text = str(item.get("canonical_text") or "").strip()
    slot_key = str(item.get("slot_key") or "").strip()
    if not canonical_text and not slot_key:
        return None

    return {
        "kind": _RESPONSE_GUIDANCE_KIND_MEMORY_ARCHIVE,
        "status": (
            _RESPONSE_GUIDANCE_STATUS_PERSISTED
            if int(persisted_doc_count) > 0
            else _RESPONSE_GUIDANCE_STATUS_ALREADY_ABSENT
        ),
        "target_canonical_text": canonical_text,
        "target_slot_key": slot_key,
        "followup_behavior": _RESPONSE_GUIDANCE_FOLLOWUP_REUSE_RESOLVED_TARGET,
    }


def render_response_guidance_contract(contract: dict[str, Any] | None) -> str:
    """将结构化回复约束渲染为 system_context 文本。"""
    if not isinstance(contract, dict):
        return ""

    kind = str(contract.get("kind") or "").strip().lower()
    if kind != _RESPONSE_GUIDANCE_KIND_MEMORY_ARCHIVE:
        return ""

    status = str(contract.get("status") or "").strip().lower()
    canonical_text = str(contract.get("target_canonical_text") or "").strip()
    slot_key = str(contract.get("target_slot_key") or "").strip()
    if not canonical_text and not slot_key:
        return ""

    if status == _RESPONSE_GUIDANCE_STATUS_PERSISTED:
        lines = [
            "系统已完成：用户本轮请求的长期记忆删除已经写入成功。",
            "回复要求：直接明确告知用户这条记忆已删除/已忘掉，不要说‘我会处理’或让用户去 Memory 页面手工删除。",
        ]
    elif status == _RESPONSE_GUIDANCE_STATUS_ALREADY_ABSENT:
        lines = [
            "系统状态：该长期记忆的删除目标已识别，但当前槽位已不再 active，通常表示这条记忆已经删除或已处理。",
            "回复要求：直接告知用户这条记忆已经删除或无需重复执行，不要说‘我会继续执行’或让用户去 Memory 页面手工删除。",
        ]
    else:
        return ""

    if canonical_text:
        lines.append(f"已识别删除目标：{canonical_text}")
    if slot_key:
        lines.append(f"已识别目标槽位：{slot_key}")
    if str(contract.get("followup_behavior") or "").strip().lower() == _RESPONSE_GUIDANCE_FOLLOWUP_REUSE_RESOLVED_TARGET:
        lines.append("若用户本轮只是沿用上一轮已唯一确认的删除链，也按同一目标继续回复。")
    return "\n".join(lines)


def _goal_kind_bucket(kind: str) -> str:
    """将细粒度 kind 归一到恢复提示桶。"""
    normalized = str(kind or "").strip().lower()
    if normalized.startswith("todo"):
        return "todo"
    if normalized.startswith("external"):
        return "external"
    if normalized.startswith("data"):
        return "data"
    return "general"


def build_multi_intent_recovery_system_context(
    base_context: str,
    intent_plan: Dict[str, Any] | None,
    missing_goals: Sequence[Dict[str, Any]],
) -> str:
    """构造补齐未完成目标的 system_context 提示。"""
    normalized_base = str(base_context or "").strip()
    marker_idx = normalized_base.find(_DELIVERY_RECOVERY_MARKER)
    if marker_idx >= 0:
        normalized_base = normalized_base[:marker_idx].rstrip()

    goal_index: Dict[str, Dict[str, Any]] = {
        str(goal.get("goal_id") or ""): goal
        for goal in list((intent_plan or {}).get("goals") or [])
        if isinstance(goal, dict) and str(goal.get("goal_id") or "")
    }

    pending_titles: list[str] = []
    pending_actions: list[str] = []
    seen_buckets: set[str] = set()
    for item in missing_goals:
        if not isinstance(item, dict):
            continue
        goal_id = str(item.get("goal_id") or "")
        title = str(item.get("title") or goal_id or "未命名目标").strip()
        if title:
            pending_titles.append(title)

        goal_kind = str((goal_index.get(goal_id) or {}).get("kind") or "")
        bucket = _goal_kind_bucket(goal_kind)
        if bucket in seen_buckets:
            continue
        seen_buckets.add(bucket)
        if bucket == "external":
            pending_actions.append("外部信息未完成：优先调用 tavily_search（必要时 knowledge_search）补齐结果。")
        elif bucket == "todo":
            pending_actions.append("待办事项未完成：调用 assign_to_todo_expert 获取或更新待办结果。")
        elif bucket == "data":
            pending_actions.append("数据查询未完成：调用 assign_to_data_expert 补齐数据答案。")
        else:
            pending_actions.append("通用问题未完成：请继续补齐该目标后再结束。")

    if not pending_titles:
        return normalized_base

    lines = [
        _DELIVERY_RECOVERY_MARKER,
        f"当前轮仍缺少目标：{'、'.join(pending_titles)}。",
        "请继续完成上述目标后再结束本轮回复，禁止只覆盖部分问题直接结束。",
    ]
    if pending_actions:
        lines.append("补齐动作：")
        lines.extend(f"- {action}" for action in pending_actions)

    recovery_hint = "\n".join(lines)
    if normalized_base:
        return f"{normalized_base}\n{recovery_hint}"
    return recovery_hint


def build_router_blocked_system_context(
    *,
    base_context: str,
    active_plan: Dict[str, Any] | None,
    pending_goals: Sequence[Dict[str, Any]],
) -> str:
    """构造 Router 门禁阻塞后的补齐提示上下文。"""
    missing_goals = [
        {
            "goal_id": str(goal.get("goal_id") or ""),
            "title": str(goal.get("title") or goal.get("kind") or "未命名目标"),
            "reason": "router_contract_blocked",
        }
        for goal in pending_goals
        if isinstance(goal, dict)
    ]
    if not missing_goals:
        return str(base_context or "")

    return build_multi_intent_recovery_system_context(
        str(base_context or ""),
        active_plan or {},
        missing_goals,
    )
