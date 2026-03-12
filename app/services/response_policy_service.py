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


def build_multi_intent_recovery_system_context(
    base_context: str,
    intent_plan: Dict[str, Any] | None,
    missing_goals: Sequence[Dict[str, Any]],
) -> str:
    """补齐提示不再通过 system_context 注入，统一返回剥离 marker 后的基础上下文。"""
    del intent_plan, missing_goals

    normalized_base = str(base_context or "").strip()
    marker_idx = normalized_base.find(_DELIVERY_RECOVERY_MARKER)
    if marker_idx >= 0:
        normalized_base = normalized_base[:marker_idx].rstrip()
    return normalized_base
