"""多智能体 Supervisor 图定义模块（中文注释）。

本模块实现 Supervisor 模式的多智能体系统：
- Supervisor 负责理解用户意图并路由到合适的专业 Agent
- 问数 Agent: 处理数据查询、分析、可视化
- 待办助手 Agent: 处理任务管理相关请求

架构示意（升级版）：
    User -> preprocess -> supervisor -> [experts] -> postprocess -> User
"""
import asyncio
import html
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Sequence, Optional, Literal, Any, Dict, Tuple, List
from pydantic import BaseModel, Field, ValidationError

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from app.ai.utils.message_factory import create_ai_message
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.tool_node import ToolNode
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command
from langgraph.errors import GraphInterrupt
from langgraph.prebuilt import InjectedState
from langgraph.graph import StateGraph, START, END

from app.ai.llm_util import get_scene_llm, get_llm_capabilities, _normalize_text_content
from app.ai.context_engineering import build_llm_input_context, resolve_context_budget_metadata
from app.ai.scene_registry import (
    SCENE_KEY_MULTI_AGENT_SUPERVISOR,
)
from app.db.postgres_checkpoint import get_checkpointer, is_checkpointer_busy_error

# 自定义事件工具
from langgraph.config import get_stream_writer
from app.ai.events import (
    emit_status,
    emit_token,
    emit_thinking,
    emit_tool_start,
    emit_tool_end,
    emit_result,
    emit_kb_images,
    emit_plan_ready,
    emit_task_started,
    emit_task_finished,
    emit_coverage_check,
    emit_final_answer,
)
from app.ai.protocol import (
    AgentOutputParser,
    HandoffResult,
    build_conversation_state_snapshot_payload,
    build_expert_input_contract_payload,
    build_skill_runtime_additional_kwargs_payload,
    build_streaming_tool_start_payload,
    build_streaming_result_payload,
    build_streaming_kb_images_payload,
    extract_skill_runtime_from_ai_message,
)
from app.ai.prompts.agent_prompts import (
    PLANNER_INTENT_PLAN_PROMPT_TEMPLATE,
    SUPERVISOR_PROMPT,
)
from app.ai.runtime.recovery_policy import (
    is_feature_flag_enabled,
    is_plugin_registry_enabled as runtime_plugin_registry_enabled,
    is_plugin_registry_error as runtime_plugin_registry_error,
    is_runtime_recovery_enabled as runtime_recovery_enabled,
)
from app.ai.state import AgentType, AGENT_DESCRIPTIONS, MultiAgentState
from app.services import response_policy_service
from app.ai.workflow.session_intent_kernel import TURN_ACT_SUPPLEMENT, classify_turn_act_from_text
from app.ai.intent.goal_resolver import (
    infer_primary_goal_bucket_from_text,
    is_todo_external_enrichment_request as intent_is_todo_external_enrichment_request,
    resolve_runtime_goal_specs,
    should_attach_todo_observations,
    should_compile_data_handoff_from_task_description,
    split_composite_query,
)
from app.ai.contracts.delivery_contract_validators import (
    build_contract_validation_meta,
    validate_coverage_report_contract,
)
from app.ai.workflow.tool_observation_normalizer import summarize_tavily_tool_output
from app.ai.workflow.attachment_planning import (
    build_attachment_planning_contract,
    normalize_attachment_manifest_entries,
    normalize_lightweight_probe_entries,
    render_attachment_planning_context,
)

# Schema 路由增强（借鉴 TypeAgent Dispatcher）
from app.ai.schema.agent_schema import route_by_schema

logger = logging.getLogger(__name__)


async def cancel_checkpoint(thread_id: str, run_id: Optional[str] = None) -> bool:
    """取消态下触发 checkpoint 快照读取，确保队列可被及时 drain。"""

    try:
        checkpointer = await get_checkpointer()
        snapshot = await checkpointer.aget({"configurable": {"thread_id": thread_id}})
        if snapshot is None:
            return False
        logger.debug("cancel_checkpoint: thread_id=%s, run_id=%s, has_snapshot=%s", thread_id, run_id, True)
        return True
    except Exception as exc:
        if is_checkpointer_busy_error(exc):
            logger.warning(
                "cancel_checkpoint 命中 checkpointer busy，已降级跳过: thread_id=%s, run_id=%s, error=%s",
                thread_id,
                run_id,
                exc,
            )
        logger.debug("cancel_checkpoint 失败，已降级忽略: thread_id=%s, run_id=%s, error=%s", thread_id, run_id, exc)
        return False


WORKFLOW_AGENT_NODE_BY_TYPE = {
    AgentType.DATA: "data_expert",
    AgentType.TODO: "todo_expert",
}
WORKFLOW_AGENT_NODES = set(WORKFLOW_AGENT_NODE_BY_TYPE.values())


from dataclasses import dataclass


@dataclass
class StreamingContext:
    """streaming_wrapper 分发上下文，封装流式会话的共享状态。"""
    writer: Any
    node_name: str
    state: Dict[str, Any]
    collected_content: list[str]
    kb_images: Dict[str, str]
    emitted_message_ids: set
    sent_tool_call_ids: set


ROUTER_RESULT_V2_VERSION = "v2"
LEGACY_ROUTER_RESULT_FIELDS = ("route_decisions", "router_result", "router_result_v1")
DECOMPOSE_GOALS_RECENT_TURN_LIMIT = 5


MODEL_ACCESS_ERROR_HINTS = (
    "error code: 400",
    "error code: 401",
    "error code: 402",
    "error code: 403",
    "permissiondenied",
    "permission denied",
    "subscription_not_found",
    "no active subscription",
    "insufficient balance",
    "allocationquota",
    "free tier",
    "arrearage",
    "request was blocked",
    "forbidden",
    "quota",
)

DELIVERY_RECOVERY_MARKER = "【交付补齐提示】"


TURN_ACT_HINTS = {
    "NEW_QUERY",
    "SUPPLEMENT",
    "CORRECTION",
    "CONFIRM",
}

SUPERVISOR_CONTEXT_TOKEN_BUDGET_RATIO = 0.85
SUPERVISOR_CONTEXT_MIN_TOKENS = 1024
SUPERVISOR_TOOL_MESSAGE_CHAR_LIMIT = 2400
SUPERVISOR_TOOL_MESSAGE_HEAD_CHARS = 1500
SUPERVISOR_TOOL_MESSAGE_TAIL_CHARS = 600


class _IntentGoalModel(BaseModel):
    """Planner 输出的单目标结构。"""

    kind: str = Field(default="general.reply")
    title: str = Field(default="")
    must_answer: bool = Field(default=True)
    confidence: float = Field(default=0.7)
    allowed_agents: list[str] = Field(default_factory=list)


class _IntentPlanModel(BaseModel):
    """Planner 输出的目标合集。"""

    goals: list[_IntentGoalModel] = Field(default_factory=list)


class _IntentPlanToolCallModel(BaseModel):
    """Tool Calling 输出参数结构。"""

    goals: list[_IntentGoalModel] = Field(default_factory=list)


class _PlannerModelInvokeError(RuntimeError):
    """模型调用失败（含能力不兼容）。"""


class _PlannerModelTimeoutError(_PlannerModelInvokeError):
    """模型调用超时。"""


class _PlannerModelOutputError(ValueError):
    """模型输出不满足 intent_plan 结构约束。"""

def _is_feature_flag_enabled(env_name: str, fallback: bool = False) -> bool:
    """读取布尔开关，支持环境变量覆盖。"""

    return is_feature_flag_enabled(env_name, fallback)


def _is_runtime_recovery_enabled() -> bool:
    """运行时恢复开关（默认开启）。"""

    return runtime_recovery_enabled()


def _is_plugin_registry_enabled() -> bool:
    """插件注册表开关（默认关闭，后置接线）。"""

    return runtime_plugin_registry_enabled()


def _is_delivery_orchestrator_v2_enabled() -> bool:
    """交付导向编排开关（默认开启）。"""
    return _is_feature_flag_enabled("ENABLE_DELIVERY_ORCHESTRATOR_V2", True)


def _is_sse_delivery_events_v2_enabled() -> bool:
    """SSE 交付事件开关（默认开启）。"""
    return _is_feature_flag_enabled("ENABLE_SSE_DELIVERY_EVENTS_V2", True)


def _is_router_contract_guard_enabled() -> bool:
    """Router 合同门禁开关（默认开启）。"""
    return _is_feature_flag_enabled("ENABLE_ROUTER_CONTRACT_GUARD", True)


def _is_coverage_gate_enforced() -> bool:
    """Coverage Gate 强门禁开关（默认开启）。"""
    return _is_feature_flag_enabled("ENABLE_COVERAGE_GATE_ENFORCED", True)


def _is_coverage_reconcile_enabled() -> bool:
    """运行时证据对账开关（默认开启）。"""
    return _is_feature_flag_enabled("ENABLE_COVERAGE_RECONCILE", True)


def _resolve_coverage_gate_max_retries() -> int:
    """读取 Coverage Gate 最大补齐轮次（默认 2，允许 0 表示不重试）。"""
    raw = os.getenv("COVERAGE_GATE_MAX_RETRIES")
    return _parse_non_negative_int(raw, default=2)


def _is_plugin_registry_error(error_text: str) -> bool:
    """判断异常是否命中插件注册表故障。"""

    return runtime_plugin_registry_error(error_text)


def _parse_non_negative_int(value: Any, default: int = 0) -> int:
    """解析非负整数，失败时回落默认值。"""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _resolve_plugin_lifecycle_status(state: Dict[str, Any], error_text: str = "") -> str:
    """解析插件生命周期状态。"""
    if not _is_plugin_registry_enabled():
        return "disabled"

    recovery_state = state.get("runtime_recovery_state")
    if isinstance(recovery_state, dict):
        current_status = str(recovery_state.get("plugin_lifecycle_status") or "").strip().lower()
        if current_status in {"healthy", "unhealthy", "disabled"}:
            return current_status
        if current_status in {"degraded", "failed", "error"}:
            return "unhealthy"

    if _is_plugin_registry_error(error_text):
        return "unhealthy"

    return "healthy"


def _build_runtime_recovery_state(
    state: Dict[str, Any],
    *,
    fallback_route: str,
    error_text: str = "",
    fallback_triggered: bool = False,
    plugin_lifecycle_status: Optional[str] = None,
) -> Dict[str, Any]:
    """生成运行时恢复状态快照（可序列化）。"""
    previous_state = state.get("runtime_recovery_state")
    previous = dict(previous_state) if isinstance(previous_state, dict) else {}

    metrics = dict(previous.get("recovery_metrics") or {})
    metrics["recovery_attempts"] = _parse_non_negative_int(metrics.get("recovery_attempts"), default=0)
    metrics["fallback_count"] = _parse_non_negative_int(metrics.get("fallback_count"), default=0)
    if fallback_triggered:
        metrics["recovery_attempts"] += 1
        metrics["fallback_count"] += 1

    if error_text:
        metrics["last_error"] = str(error_text)[:320]
    metrics["last_observed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    status = plugin_lifecycle_status or _resolve_plugin_lifecycle_status(state, error_text)
    return {
        "recovery_metrics": metrics,
        "fallback_route": str(fallback_route or "none"),
        "plugin_lifecycle_status": status,
    }


def _is_model_access_error(error_text: str) -> bool:
    """判断是否为上游模型权限/配额/订阅类错误。"""
    lowered = str(error_text or "").strip().lower()
    if not lowered:
        return False
    return any(hint in lowered for hint in MODEL_ACCESS_ERROR_HINTS)


def _extract_latest_human_content(messages: Sequence[BaseMessage]) -> str:
    """提取最近一条用户消息文本。"""
    for message in reversed(messages or []):
        message_type = str(getattr(message, "type", "")).lower().strip()
        if message_type != "human":
            continue
        content = _normalize_text_content(getattr(message, "content", ""))
        if content and content.strip():
            return content.strip()
    return ""


def _slice_messages_from_latest_human(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """按当前轮次切片消息（从最近一条 human 开始）。"""
    if not messages:
        return []

    latest_human_index: Optional[int] = None
    for idx in range(len(messages) - 1, -1, -1):
        if str(getattr(messages[idx], "type", "")).lower().strip() == "human":
            latest_human_index = idx
            break

    if latest_human_index is None:
        return list(messages)
    return list(messages[latest_human_index:])


def _resolve_semantic_user_query(state: MultiAgentState) -> str:
    """优先读取语义层载荷，缺失时回退到消息切片。"""
    semantic_payload = state.get("semantic_payload")
    if isinstance(semantic_payload, dict):
        value = semantic_payload.get("user_query")
        text = _normalize_text_content(value)
        if text and text.strip():
            return text.strip()

    messages = _slice_messages_from_latest_human(state.get("messages", []))
    return _extract_latest_human_content(messages)


def _extract_router_result_v2(*sources: Any) -> Dict[str, Any]:
    """提取运行态 canonical Router 结果（v2）。"""
    for source in sources:
        if not isinstance(source, dict):
            continue
        payload = source.get("router_result_v2")
        if not isinstance(payload, dict):
            continue
        normalized = dict(payload)
        normalized["version"] = ROUTER_RESULT_V2_VERSION
        return normalized

    return {
        "version": ROUTER_RESULT_V2_VERSION,
        "route_decisions": [],
        "router_contract_blocked": [],
    }


def _detect_legacy_router_result_fields(*sources: Any) -> list[str]:
    """检测旧版 Router 结构化字段。"""
    detected: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        for field in LEGACY_ROUTER_RESULT_FIELDS:
            if field in source:
                detected.add(field)
    return sorted(detected)


def _build_router_result_v2_payload(
    *,
    existing_payload: Optional[Dict[str, Any]] = None,
    accepted_decisions: Optional[Sequence[Dict[str, Any]]] = None,
    blocked_handoffs: Optional[Sequence[Dict[str, Any]]] = None,
    pending_goals: Optional[Sequence[Dict[str, Any]]] = None,
    turn_id: str = "",
    event: str = "",
    reason: str = "",
    runtime_state: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构建运行态 canonical Router 结果（additional_kwargs.router_result_v2）。"""
    existing = dict(existing_payload or {})
    normalized_state = runtime_state if isinstance(runtime_state, dict) else {}
    existing_decisions = [
        dict(item)
        for item in list(existing.get("route_decisions") or [])
        if isinstance(item, dict)
    ]
    new_decisions = [
        dict(item)
        for item in list(accepted_decisions or [])
        if isinstance(item, dict)
    ]
    blocked = [
        dict(item)
        for item in list(blocked_handoffs or [])
        if isinstance(item, dict)
    ]
    pending = [
        {
            "goal_id": str(goal.get("goal_id") or ""),
            "title": str(goal.get("title") or goal.get("kind") or "未命名目标"),
        }
        for goal in list(pending_goals or [])
        if isinstance(goal, dict)
    ]
    existing_conversation_state = (
        dict(existing.get("conversation_state"))
        if isinstance(existing.get("conversation_state"), dict)
        else {}
    )

    active_goal_ids: List[str] = []
    for goal in list(normalized_state.get("decomposed_goals") or []):
        if not isinstance(goal, dict):
            continue
        goal_id = str(goal.get("goal_id") or "").strip()
        if goal_id and goal_id not in active_goal_ids:
            active_goal_ids.append(goal_id)

    pending_handoff = normalized_state.get("pending_handoff")
    if not active_goal_ids and isinstance(pending_handoff, dict):
        goal_id = str(pending_handoff.get("goal_id") or "").strip()
        if goal_id:
            active_goal_ids.append(goal_id)

    if not active_goal_ids:
        for item in list(existing_conversation_state.get("active_goal_ids") or []):
            goal_id = str(item or "").strip()
            if goal_id and goal_id not in active_goal_ids:
                active_goal_ids.append(goal_id)

    active_workflow = str(existing_conversation_state.get("active_workflow") or "supervisor").strip() or "supervisor"
    pending_user_action = str(existing_conversation_state.get("pending_user_action") or "none").strip() or "none"

    if isinstance(pending_handoff, dict):
        target_agent = str(pending_handoff.get("target_agent") or "").strip()
        if target_agent == AgentType.DATA:
            active_workflow = "data_workflow"
            pending_user_action = "workflow_dispatch"
        elif target_agent == AgentType.TODO:
            active_workflow = "todo_workflow"
            pending_user_action = "workflow_dispatch"

    pending_operation = normalized_state.get("pending_operation")
    if isinstance(pending_operation, dict) and pending_operation:
        active_workflow = "todo_workflow"
        pending_user_action = "todo_clarify" if pending_operation.get("needs_clarification") else "todo_confirm"
    elif str(normalized_state.get("pending_sql") or "").strip():
        active_workflow = "data_workflow"
        pending_user_action = "data_sql_confirm"
    elif str(normalized_state.get("clarification_needed") or "").strip():
        active_workflow = "data_workflow"
        pending_user_action = "data_clarify"

    session_frame_slots: List[str] = []
    session_frame = normalized_state.get("session_frame")
    if isinstance(session_frame, dict):
        for key, value in session_frame.items():
            slot_name = str(key or "").strip()
            if not slot_name:
                continue
            if value is None or value == "" or value == [] or value == {}:
                continue
            if slot_name not in session_frame_slots:
                session_frame_slots.append(slot_name)
    if not session_frame_slots:
        for item in list(existing_conversation_state.get("session_frame_slots") or []):
            slot_name = str(item or "").strip()
            if slot_name and slot_name not in session_frame_slots:
                session_frame_slots.append(slot_name)

    conversation_state = build_conversation_state_snapshot_payload(
        owner="supervisor",
        turn_act=normalized_state.get("turn_act") or existing_conversation_state.get("turn_act") or "UNKNOWN",
        active_goal_ids=active_goal_ids,
        active_workflow=active_workflow,
        pending_user_action=pending_user_action,
        session_frame_slots=session_frame_slots,
        snapshot_version=existing_conversation_state.get("snapshot_version") or "v1",
        clarify_fsm_state=normalized_state.get("clarify_fsm_state") or existing_conversation_state.get("clarify_fsm_state"),
        clarify_round=normalized_state.get("clarify_round") if normalized_state.get("clarify_round") is not None else existing_conversation_state.get("clarify_round"),
    )

    payload: Dict[str, Any] = {
        "version": ROUTER_RESULT_V2_VERSION,
        "route_decisions": existing_decisions + new_decisions,
        "router_contract_blocked": blocked,
        "router_contract_blocked_count": len(blocked),
        "pending_goals": pending,
        "field_version": ROUTER_RESULT_V2_VERSION,
    }
    if conversation_state is not None:
        payload["conversation_state"] = conversation_state
    if turn_id:
        payload["turn_id"] = turn_id
    if event:
        payload["event"] = event
    if reason:
        payload["reason"] = reason

    if isinstance(extra, dict):
        for key, value in extra.items():
            if value is None:
                continue
            payload[key] = value

    return payload


def _first_hint_position(text: str, hints: Sequence[str]) -> int:
    """返回首个关键词命中的位置，未命中返回大值。"""
    normalized = str(text or "").lower()
    min_idx = 10**9
    for hint in hints:
        idx = normalized.find(str(hint).lower())
        if idx >= 0:
            min_idx = min(min_idx, idx)
    return min_idx


def _normalize_model_goal_kind(raw_kind: str) -> str:
    """将模型输出的目标类型归一到当前系统支持的 kind。"""
    normalized = str(raw_kind or "").strip().lower().replace("_", ".")
    compact = normalized.replace(" ", "")

    if compact.startswith("todo"):
        if "create" in compact or "add" in compact or "new" in compact:
            return "todo.create"
        return "todo.query"

    if compact.startswith("chart") or any(token in compact for token in ("draw", "plot", "figure", "diagram")):
        return "chart.render"

    if compact.startswith("research") or any(token in compact for token in ("compare", "contrast", "synthesize")):
        return "research.execute"

    if compact.startswith("knowledge") or any(token in compact for token in ("rag", "document", "manual")):
        return "knowledge.lookup"

    if compact.startswith("weather") or "forecast" in compact:
        return "weather.lookup"

    if compact.startswith("external") or "lookup" in compact or "search" in compact or "web" in compact:
        return "external.lookup"

    if (
        compact.startswith("data")
        or "sql" in compact
        or "report" in compact
        or "metric" in compact
        or "table" in compact
    ):
        return "data.query"

    return "general.reply"


def _default_goal_title(kind: str) -> str:
    """根据标准 kind 提供默认标题。"""
    normalized = str(kind or "").strip().lower()
    if normalized.startswith("research"):
        return "综合研究"
    if normalized.startswith("weather"):
        return "天气信息"
    if normalized.startswith("knowledge"):
        return "知识库检索"
    if normalized.startswith("chart"):
        return "图表结果"
    bucket = _goal_kind_bucket(kind)
    if bucket == "todo":
        return "待办事项"
    if bucket == "external":
        return "外部信息"
    if bucket == "data":
        return "数据查询"
    return "问题回复"


def _default_allowed_agents_for_goal_kind(kind: str) -> list[str]:
    """按目标类型返回默认允许委派专家。"""
    bucket = _goal_kind_bucket(kind)
    if bucket == "todo":
        return [AgentType.TODO]
    if bucket == "data":
        return [AgentType.DATA]
    return []


def _normalize_goal_allowed_agents(raw_allowed_agents: Any, kind: str) -> list[str]:
    """规范化 allowed_agents，缺省时按 kind 自动补齐。"""
    values: list[str] = []
    if isinstance(raw_allowed_agents, (list, tuple, set)):
        values = [str(item or "").strip() for item in raw_allowed_agents]
    elif isinstance(raw_allowed_agents, str):
        values = [raw_allowed_agents.strip()]

    valid_targets = set(WORKFLOW_AGENT_NODE_BY_TYPE.keys())
    normalized: list[str] = []
    for value in values:
        if not value or value not in valid_targets:
            continue
        if value not in normalized:
            normalized.append(value)

    if normalized:
        return normalized
    return _default_allowed_agents_for_goal_kind(kind)


def _normalize_intent_plan_allowed_agents(intent_plan: Dict[str, Any]) -> Dict[str, Any]:
    """对 intent_plan 的每个 goal 补齐 allowed_agents。"""
    normalized_plan = dict(intent_plan or {})
    goals = list(normalized_plan.get("goals") or [])
    normalized_goals: list[Dict[str, Any]] = []

    for goal in goals:
        if not isinstance(goal, dict):
            continue
        normalized_goal = dict(goal)
        kind = str(normalized_goal.get("kind") or "general.reply")
        normalized_goal["allowed_agents"] = _normalize_goal_allowed_agents(
            normalized_goal.get("allowed_agents"),
            kind,
        )
        normalized_goals.append(normalized_goal)

    if normalized_goals:
        normalized_goals = sorted(
            normalized_goals,
            key=lambda item: int(item.get("order") or 0),
        )
    normalized_plan["goals"] = normalized_goals
    return normalized_plan


def _build_default_general_goal() -> Dict[str, Any]:
    """构造默认兜底目标。"""
    return {
        "goal_id": "GOAL-01",
        "order": 1,
        "kind": "general.reply",
        "title": "问题回复",
        "must_answer": True,
        "allowed_agents": [],
    }


def _normalize_active_goals(goals: Sequence[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """标准化活动目标列表，统一补齐字段与排序。"""
    raw_goals: list[Dict[str, Any]] = []
    for raw_goal in goals or []:
        if not isinstance(raw_goal, dict):
            continue
        kind = _normalize_model_goal_kind(str(raw_goal.get("kind") or "general.reply"))
        raw_goals.append(
            {
                "goal_id": str(raw_goal.get("goal_id") or "").strip(),
                "order": _parse_non_negative_int(raw_goal.get("order"), default=len(raw_goals) + 1),
                "kind": kind,
                "title": str(raw_goal.get("title") or "").strip() or _default_goal_title(kind),
                "must_answer": bool(raw_goal.get("must_answer", True)),
                "allowed_agents": raw_goal.get("allowed_agents"),
            }
        )

    if not raw_goals:
        return [_build_default_general_goal()]

    normalized_plan = _normalize_intent_plan_allowed_agents({"goals": raw_goals})
    normalized_goals = sorted(
        [goal for goal in list(normalized_plan.get("goals") or []) if isinstance(goal, dict)],
        key=lambda item: _parse_non_negative_int(item.get("order"), default=10**9),
    )
    if not normalized_goals:
        return [_build_default_general_goal()]

    finalized: list[Dict[str, Any]] = []
    for index, goal in enumerate(normalized_goals, start=1):
        kind = _normalize_model_goal_kind(str(goal.get("kind") or "general.reply"))
        finalized.append(
            {
                "goal_id": str(goal.get("goal_id") or f"GOAL-{index:02d}").strip() or f"GOAL-{index:02d}",
                "order": index,
                "kind": kind,
                "title": str(goal.get("title") or "").strip() or _default_goal_title(kind),
                "must_answer": bool(goal.get("must_answer", True)),
                "allowed_agents": _normalize_goal_allowed_agents(goal.get("allowed_agents"), kind),
            }
        )
    return finalized


def _extract_decomposed_goals_from_messages(messages: Sequence[BaseMessage]) -> list[Dict[str, Any]]:
    """从 Supervisor 本轮 ToolMessage 中提取 decompose_goals 产物。"""
    for message in reversed(messages or []):
        if not isinstance(message, ToolMessage):
            continue

        tool_name = str(getattr(message, "name", "") or "").strip()
        content = str(getattr(message, "content", "") or "").strip()
        if not content:
            continue
        if tool_name != "decompose_goals" and "decompose_goals" not in content:
            continue
        if not (content.startswith("{") and content.endswith("}")):
            continue

        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue

        if not isinstance(payload, dict):
            continue
        action = str(payload.get("action") or "").strip()
        if tool_name != "decompose_goals" and action != "decompose_goals":
            continue

        raw_goals = payload.get("goals")
        if not isinstance(raw_goals, list):
            continue
        return [goal for goal in raw_goals if isinstance(goal, dict)]

    return []


def _resolve_active_goals(
    state: MultiAgentState,
    *,
    runtime_goals: Optional[Sequence[Dict[str, Any]]] = None,
) -> list[Dict[str, Any]]:
    """统一解析活动目标：运行态仅消费 decomposed_goals。"""
    runtime_list = [goal for goal in list(runtime_goals or []) if isinstance(goal, dict)]
    if runtime_list:
        return _normalize_active_goals(runtime_list)

    decomposed = state.get("decomposed_goals")
    if isinstance(decomposed, list) and decomposed:
        return _normalize_active_goals([goal for goal in decomposed if isinstance(goal, dict)])

    return []


def _should_backfill_runtime_goals_for_handoff(
    active_goals: Sequence[Dict[str, Any]],
    handoffs: Sequence[Dict[str, Any]],
) -> bool:
    """单目标直派场景下，判定是否需要先回填 runtime goals。"""
    normalized_handoffs = [dict(item) for item in handoffs if isinstance(item, dict)]
    if len(normalized_handoffs) != 1:
        return False

    target_agent = str(normalized_handoffs[0].get("target_agent") or "").strip()
    if target_agent not in {AgentType.DATA, AgentType.TODO}:
        return False

    normalized_goals = _normalize_active_goals(active_goals)
    if not normalized_goals:
        return True
    if _count_must_answer_goals(normalized_goals) != 1:
        return False

    current_goal = normalized_goals[0]
    goal_kind = str(current_goal.get("kind") or "general.reply")
    goal_bucket = _goal_kind_bucket(goal_kind)
    allowed_agents = _normalize_goal_allowed_agents(current_goal.get("allowed_agents"), goal_kind)
    return goal_bucket == "general" and target_agent not in allowed_agents


def _build_active_goal_plan(
    state: MultiAgentState,
    *,
    runtime_goals: Optional[Sequence[Dict[str, Any]]] = None,
    source: str = "runtime",
) -> Dict[str, Any]:
    """基于活动目标构造标准化问题合同载荷。"""
    return {
        "version": 1,
        "source": source,
        "user_query": _resolve_semantic_user_query(state),
        "goals": _resolve_active_goals(state, runtime_goals=runtime_goals),
    }


def _build_model_intent_plan_prompt(user_text: str) -> str:
    """构建模型意图规划提示词。"""
    return PLANNER_INTENT_PLAN_PROMPT_TEMPLATE.format(user_text=str(user_text or "").strip())


def _build_model_intent_plan_tool_prompt(user_text: str) -> str:
    """构建 Tool Calling 主路径提示词。"""
    return (
        f"{_build_model_intent_plan_prompt(user_text)}\n"
        "请通过工具调用返回 goals，不要输出额外文本。"
    )


def _build_model_intent_plan_text_parse_prompt(user_text: str) -> str:
    """构建 text_parse 三级降级提示词。"""
    return (
        f"{_build_model_intent_plan_prompt(user_text)}\n"
        "请直接返回 JSON 对象，不要使用 Markdown 代码块。"
    )


def _coerce_model_intent_plan_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """兼容模型返回的弱结构 goals，避免字符串数组直接触发校验失败。"""
    normalized = dict(raw_data or {})
    goals = normalized.get("goals")
    if not isinstance(goals, (list, tuple)):
        return normalized

    coerced_goals: list[Any] = []
    for goal in goals:
        if isinstance(goal, dict):
            coerced_goals.append(goal)
            continue
        if isinstance(goal, str):
            normalized_kind = goal.strip()
            if normalized_kind:
                coerced_goals.append({"kind": normalized_kind})
    normalized["goals"] = coerced_goals
    return normalized


def _find_intent_plan_validation_error(exc: BaseException) -> Optional[ValidationError]:
    """从异常链中提取 _IntentPlanModel 的 ValidationError。"""
    stack: list[BaseException] = [exc]
    visited: set[int] = set()

    while stack:
        current = stack.pop()
        identity = id(current)
        if identity in visited:
            continue
        visited.add(identity)

        if isinstance(current, ValidationError):
            title = str(getattr(current, "title", "") or "").strip()
            if title == "_IntentPlanModel":
                return current

        cause = getattr(current, "__cause__", None)
        context = getattr(current, "__context__", None)
        if isinstance(cause, BaseException):
            stack.append(cause)
        if isinstance(context, BaseException):
            stack.append(context)

    return None


def _recover_intent_plan_payload_from_validation_error(exc: ValidationError) -> Optional[Dict[str, Any]]:
    """尝试从 _IntentPlanModel 校验异常恢复弱结构 payload。"""
    errors = list(exc.errors())
    if not errors:
        return None

    indexed_goals: Dict[int, Any] = {}
    for item in errors:
        loc = item.get("loc")
        if not isinstance(loc, (list, tuple)) or len(loc) != 2:
            return None
        field_name, index = loc
        if field_name != "goals" or not isinstance(index, int):
            return None
        if str(item.get("type") or "") != "model_type":
            return None

        value = item.get("input")
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            indexed_goals[index] = stripped
            continue
        if isinstance(value, dict):
            indexed_goals[index] = value
            continue
        return None

    if not indexed_goals:
        return None

    ordered_indexes = sorted(indexed_goals.keys())
    if ordered_indexes != list(range(ordered_indexes[-1] + 1)):
        return None

    return {"goals": [indexed_goals[index] for index in ordered_indexes]}


def _build_model_primary_plan_from_parsed(
    parsed: _IntentPlanModel,
    *,
    user_text: str,
) -> Dict[str, Any]:
    """将结构化输出归一为标准 intent_plan。"""
    normalized_goals: list[Dict[str, Any]] = []
    seen_buckets: set[str] = set()
    for item in list(parsed.goals or []):
        kind = _normalize_model_goal_kind(item.kind)
        bucket = _goal_kind_bucket(kind)
        if bucket in seen_buckets and bucket != "general":
            continue
        seen_buckets.add(bucket)

        title = str(item.title or "").strip() or _default_goal_title(kind)
        try:
            confidence = float(item.confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        normalized_goals.append(
            {
                "goal_id": f"GOAL-{len(normalized_goals) + 1:02d}",
                "order": len(normalized_goals) + 1,
                "kind": kind,
                "title": title,
                "must_answer": bool(item.must_answer),
                "confidence": confidence,
                "allowed_agents": _normalize_goal_allowed_agents(item.allowed_agents, kind),
            }
        )

    if not normalized_goals:
        normalized_goals = [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "general.reply",
                "title": "问题回复",
                "must_answer": True,
                "confidence": 0.5,
                "allowed_agents": [],
            }
        ]

    return _normalize_intent_plan_allowed_agents(
        {
            "version": 1,
            "source": "model_primary",
            "user_query": user_text,
            "goals": normalized_goals,
        }
    )


def _normalize_planner_structured_strategy(value: Any) -> str:
    """标准化 planner 结构化策略名。"""
    normalized = str(value or "").strip().lower()
    if normalized in {"legacy", "legacy_json", "legacy_json_object", "json", "json_object"}:
        return "legacy_json_object"
    if normalized in {"tool_call", "tool_call_primary"}:
        return "tool_call_primary"
    return "auto"


def _resolve_planner_structured_strategy(llm: Any) -> Dict[str, Any]:
    """解析 planner 结构化策略路由。"""
    forced_strategy = _normalize_planner_structured_strategy(os.getenv("PLANNER_STRUCTURED_STRATEGY"))
    capabilities = get_llm_capabilities(llm)
    supports_tool_call = bool(capabilities.get("supports_tool_call", False))
    supports_structured_output = bool(capabilities.get("supports_structured_output", False))
    tool_call_disabled = _is_feature_flag_enabled("PLANNER_DISABLE_TOOL_CALL", True)

    if tool_call_disabled:
        selected_strategy = "legacy_json_object"
    elif forced_strategy in {"tool_call_primary", "legacy_json_object"}:
        selected_strategy = forced_strategy
    elif supports_tool_call:
        selected_strategy = "tool_call_primary"
    else:
        selected_strategy = "legacy_json_object"

    return {
        "strategy": selected_strategy,
        "forced_strategy": forced_strategy,
        "tool_call_disabled": tool_call_disabled,
        "supports_tool_call": supports_tool_call,
        "supports_structured_output": supports_structured_output,
    }


def _coerce_tool_call_args(raw_args: Any) -> Dict[str, Any]:
    """解析 tool_call args，兼容 dict/json-string。"""
    if isinstance(raw_args, dict):
        return dict(raw_args)
    if isinstance(raw_args, str):
        normalized = raw_args.strip()
        if not normalized:
            return {}
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise _PlannerModelOutputError(f"planner_tool_call_args_invalid_json:{exc}") from exc
        if isinstance(parsed, dict):
            return parsed
    raise _PlannerModelOutputError("planner_tool_call_args_invalid")


def _extract_json_object_from_text(raw_text: str) -> Dict[str, Any]:
    """从文本响应中提取 JSON 对象。"""
    text = str(raw_text or "").strip()
    if not text:
        raise _PlannerModelOutputError("planner_text_parse_empty")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    last_error: Optional[Exception] = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(parsed, dict):
            return parsed
        raise _PlannerModelOutputError("planner_text_parse_not_object")

    if last_error is not None:
        raise _PlannerModelOutputError(f"planner_text_parse_invalid_json:{last_error}") from last_error
    raise _PlannerModelOutputError("planner_text_parse_invalid_json")


def _coerce_llm_text_output(raw_output: Any) -> str:
    """将 LLM 输出统一为可解析文本。"""
    if isinstance(raw_output, str):
        return raw_output
    if isinstance(raw_output, dict):
        content = raw_output.get("content")
        if isinstance(content, str):
            return content
        return json.dumps(raw_output, ensure_ascii=False)

    content = getattr(raw_output, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: list[str] = []
        for item in content:
            if isinstance(item, str):
                pieces.append(item)
                continue
            if isinstance(item, dict):
                text_part = item.get("text")
                if isinstance(text_part, str):
                    pieces.append(text_part)
        return "\n".join(piece for piece in pieces if piece)
    return ""


def _infer_model_intent_plan_via_tool_call(state: MultiAgentState, llm: Any) -> Dict[str, Any]:
    """使用 Tool Calling 主路径生成结构化 intent_plan。"""
    user_text = _resolve_semantic_user_query(state)
    if not user_text:
        return _build_model_primary_plan_from_parsed(_IntentPlanModel(goals=[]), user_text="")

    if not hasattr(llm, "bind_tools"):
        raise _PlannerModelInvokeError("planner_llm_tool_call_unsupported")

    tool_bound_llm = None
    try:
        tool_bound_llm = llm.bind_tools([_IntentPlanToolCallModel], tool_choice="required")
    except TypeError:
        try:
            tool_bound_llm = llm.bind_tools([_IntentPlanToolCallModel])
        except Exception as exc:
            raise _PlannerModelInvokeError(f"planner_tool_call_bind_failed:{exc}") from exc
    except Exception as exc:
        raise _PlannerModelInvokeError(f"planner_tool_call_bind_failed:{exc}") from exc

    prompt = _build_model_intent_plan_tool_prompt(user_text)
    try:
        raw_output = tool_bound_llm.invoke(prompt)
    except TimeoutError as exc:
        raise _PlannerModelTimeoutError(f"planner_tool_call_timeout:{exc}") from exc
    except Exception as exc:
        raise _PlannerModelInvokeError(str(exc)) from exc

    tool_calls = []
    if isinstance(raw_output, dict):
        tool_calls = list(raw_output.get("tool_calls") or [])
    else:
        tool_calls = list(getattr(raw_output, "tool_calls", []) or [])

    if not tool_calls:
        raise _PlannerModelOutputError("planner_tool_call_missing")

    try:
        raw_args = tool_calls[0].get("args")
        parsed = _IntentPlanModel(**_coerce_model_intent_plan_data(_coerce_tool_call_args(raw_args)))
    except (_PlannerModelOutputError, ValidationError, TypeError, ValueError) as exc:
        if isinstance(exc, _PlannerModelOutputError):
            raise
        raise _PlannerModelOutputError(str(exc)) from exc

    return _build_model_primary_plan_from_parsed(parsed, user_text=user_text)


def _infer_model_intent_plan_via_json_object(state: MultiAgentState, llm: Any) -> Dict[str, Any]:
    """使用 json_object 路径生成结构化 intent_plan。"""
    user_text = _resolve_semantic_user_query(state)
    if not user_text:
        return _build_model_primary_plan_from_parsed(_IntentPlanModel(goals=[]), user_text="")

    if _is_feature_flag_enabled("PLANNER_DISABLE_JSON_OBJECT", False):
        raise _PlannerModelInvokeError("planner_json_object_disabled")

    if not hasattr(llm, "with_structured_output"):
        raise _PlannerModelInvokeError("planner_llm_structured_output_unsupported")

    try:
        structured_llm = llm.with_structured_output(_IntentPlanModel)
    except Exception as exc:
        raise _PlannerModelInvokeError(f"planner_llm_bind_failed:{exc}") from exc

    prompt = _build_model_intent_plan_prompt(user_text)
    try:
        raw_output = structured_llm.invoke(prompt)
    except TimeoutError as exc:
        raise _PlannerModelTimeoutError(f"planner_llm_timeout:{exc}") from exc
    except Exception as exc:
        validation_error = _find_intent_plan_validation_error(exc)
        if validation_error is None:
            raise _PlannerModelInvokeError(str(exc)) from exc

        recovered_payload = _recover_intent_plan_payload_from_validation_error(validation_error)
        if recovered_payload is None:
            logger.warning(
                "planner_json_object_invalid_output_unrecoverable: %s",
                validation_error,
            )
            raise _PlannerModelOutputError(str(validation_error)) from exc

        logger.info(
            "planner_json_object_weak_structure_recovered: goals=%s",
            len(list(recovered_payload.get("goals") or [])),
        )
        raw_output = recovered_payload

    try:
        if isinstance(raw_output, _IntentPlanModel):
            parsed = raw_output
        elif isinstance(raw_output, dict):
            parsed = _IntentPlanModel(**_coerce_model_intent_plan_data(raw_output))
        else:
            raw_data: Dict[str, Any] = {}
            if hasattr(raw_output, "model_dump"):
                raw_data = raw_output.model_dump()  # type: ignore[assignment]
            elif hasattr(raw_output, "dict"):
                raw_data = raw_output.dict()  # type: ignore[assignment]
            else:
                raise _PlannerModelOutputError("planner_output_not_serializable")
            parsed = _IntentPlanModel(**_coerce_model_intent_plan_data(raw_data))
    except (_PlannerModelOutputError, ValidationError, TypeError, ValueError) as exc:
        if isinstance(exc, _PlannerModelOutputError):
            raise
        raise _PlannerModelOutputError(str(exc)) from exc

    return _build_model_primary_plan_from_parsed(parsed, user_text=user_text)


def _infer_model_intent_plan_via_text_parse(state: MultiAgentState, llm: Any) -> Dict[str, Any]:
    """使用 text_parse 三级降级路径生成结构化 intent_plan。"""
    user_text = _resolve_semantic_user_query(state)
    if not user_text:
        return _build_model_primary_plan_from_parsed(_IntentPlanModel(goals=[]), user_text="")

    if _is_feature_flag_enabled("PLANNER_DISABLE_TEXT_PARSE", True):
        raise _PlannerModelInvokeError("planner_text_parse_disabled")

    if not hasattr(llm, "invoke"):
        raise _PlannerModelInvokeError("planner_llm_text_parse_unsupported")

    prompt = _build_model_intent_plan_text_parse_prompt(user_text)
    try:
        raw_output = llm.invoke(prompt)
    except TimeoutError as exc:
        raise _PlannerModelTimeoutError(f"planner_text_parse_timeout:{exc}") from exc
    except Exception as exc:
        raise _PlannerModelInvokeError(f"planner_text_parse_invoke_failed:{exc}") from exc

    parsed_text = _coerce_llm_text_output(raw_output)
    if not parsed_text:
        raise _PlannerModelOutputError("planner_text_parse_empty")

    payload = _extract_json_object_from_text(parsed_text)
    try:
        parsed = _IntentPlanModel(**_coerce_model_intent_plan_data(payload))
    except (ValidationError, TypeError, ValueError) as exc:
        raise _PlannerModelOutputError(f"planner_text_parse_schema_invalid:{exc}") from exc

    return _build_model_primary_plan_from_parsed(parsed, user_text=user_text)


def _infer_model_intent_plan(state: MultiAgentState, llm: Any) -> Dict[str, Any]:
    """兼容旧调用，默认走 json_object 路径。"""
    return _infer_model_intent_plan_via_json_object(state, llm)


def _infer_model_intent_plan_by_strategy(
    state: MultiAgentState,
    llm: Any,
) -> Dict[str, Any]:
    """按能力路由执行 planner 结构化主链路。"""
    strategy_meta = _resolve_planner_structured_strategy(llm)
    strategy = str(strategy_meta.get("strategy") or "legacy_json_object")

    def _json_object_then_text_parse(
        *,
        previous_error: Optional[Exception] = None,
        previous_stage: str = "",
    ) -> Dict[str, Any]:
        previous_reason = str(previous_error)[:160] if previous_error is not None else ""
        try:
            plan = _infer_model_intent_plan(state, llm)
            plan["planner_strategy"] = "legacy_json_object"
            if previous_reason:
                plan["planner_strategy_fallback"] = previous_stage
                plan["planner_strategy_fallback_reason"] = previous_reason
            return plan
        except Exception as json_exc:
            logger.warning("planner_json_object_failed_fallback_to_text_parse: %s", json_exc)
            try:
                plan = _infer_model_intent_plan_via_text_parse(state, llm)
            except _PlannerModelInvokeError as text_exc:
                text_error = str(text_exc)
                if (
                    "planner_llm_text_parse_unsupported" in text_error
                    or "planner_text_parse_disabled" in text_error
                ):
                    raise json_exc
                raise
            plan["planner_strategy"] = "text_parse"
            plan["planner_strategy_fallback"] = "json_object_failed"
            plan["planner_strategy_fallback_reason"] = str(json_exc)[:160]
            return plan

    if strategy == "tool_call_primary":
        try:
            plan = _infer_model_intent_plan_via_tool_call(state, llm)
            plan["planner_strategy"] = strategy
            return plan
        except Exception as tool_exc:
            logger.warning("planner_tool_call_failed_fallback_to_json_object: %s", tool_exc)
            return _json_object_then_text_parse(previous_error=tool_exc, previous_stage="tool_call_failed")

    return _json_object_then_text_parse()


def _classify_planner_fallback(exc: Exception) -> Optional[Tuple[str, str]]:
    """分类 planner 兜底触发原因。"""
    if isinstance(exc, (_PlannerModelTimeoutError, TimeoutError, asyncio.TimeoutError)):
        return ("planner_fallback.timeout", "timeout")
    if isinstance(exc, (_PlannerModelOutputError, ValidationError, TypeError, ValueError, json.JSONDecodeError)):
        return ("planner_fallback.invalid_output", "invalid_output")
    if isinstance(exc, (_PlannerModelInvokeError, RuntimeError, ConnectionError, OSError)):
        return ("planner_fallback.model_failure", "model_failure")
    return None


def _resolve_planner_fallback_strategy(exc: Exception) -> Tuple[bool, str, str]:
    """决定是否进入 heuristic_fallback 及其规则标识。"""
    gate_enabled = _is_feature_flag_enabled("ENABLE_INTENT_FALLBACK_GATE", True)
    if not gate_enabled:
        return True, "planner_fallback.legacy_catch_all", "legacy"

    classified = _classify_planner_fallback(exc)
    if classified is None:
        return False, "", ""
    return True, classified[0], classified[1]


def _resolve_planner_reason_code(
    *,
    fallback_rule_id: str,
    fallback_trigger: str,
) -> str:
    """标准化 planner fallback reason_code。"""
    trigger = str(fallback_trigger or "").strip().lower()
    if trigger in {"timeout", "invalid_output", "model_failure", "legacy"}:
        return trigger

    normalized_rule = str(fallback_rule_id or "").strip().lower()
    if normalized_rule.endswith(".timeout"):
        return "timeout"
    if normalized_rule.endswith(".invalid_output"):
        return "invalid_output"
    if normalized_rule.endswith(".model_failure"):
        return "model_failure"
    if normalized_rule.endswith(".legacy_catch_all"):
        return "legacy"
    return "unknown"


def _build_planner_status_message(
    intent_plan: Dict[str, Any],
    *,
    raw_intent_plan: Optional[Dict[str, Any]] = None,
) -> str:
    """构造 planner 阶段状态文案。"""
    goal_count = len(list((intent_plan or {}).get("goals") or []))
    status_message = f"已识别 {goal_count} 个待答目标，准备进入执行阶段。"

    source = str((intent_plan or {}).get("source") or "")
    if not source and isinstance(raw_intent_plan, dict):
        source = str(raw_intent_plan.get("source") or "")

    if source == "heuristic_fallback":
        suffix = "（已自动切换规则兜底）"
        return f"已识别 {goal_count} 个待答目标，准备进入执行阶段{suffix}。"
    if source == "heuristic_only":
        return f"已识别 {goal_count} 个待答目标，当前运行于 heuristic_only 回滚模式。"

    return status_message


def _infer_initial_intent_plan(state: MultiAgentState) -> Dict[str, Any]:
    """从用户输入推断初始问题合同（intent_plan）。"""
    user_text = _resolve_semantic_user_query(state)
    goals = resolve_runtime_goal_specs(user_text)

    normalized_goals: list[Dict[str, Any]] = []
    for index, goal in enumerate(goals, start=1):
        goal_kind = str(goal.get("kind") or "general.reply")
        normalized_goals.append(
            {
                "goal_id": f"GOAL-{index:02d}",
                "order": index,
                "kind": goal_kind,
                "title": str(goal.get("title") or _default_goal_title(goal_kind)),
                "must_answer": bool(goal.get("must_answer", True)),
                "allowed_agents": _normalize_goal_allowed_agents(goal.get("allowed_agents"), goal_kind),
            }
        )

    return _normalize_intent_plan_allowed_agents(
        {
            "version": 1,
            "source": "heuristic",
            "user_query": user_text,
            "goals": normalized_goals,
        }
    )


def _normalize_intent_mode(mode: Any, default: str = "model_primary") -> str:
    """归一化意图模式，兼容 shadow_compare 别名。"""
    normalized = str(mode or "").strip().lower()
    if normalized == "shadow_compare":
        return "model_primary"
    if normalized in {"model_primary", "heuristic_only"}:
        return normalized

    fallback = str(default or "model_primary").strip().lower()
    if fallback == "shadow_compare":
        return "model_primary"
    if fallback in {"model_primary", "heuristic_only"}:
        return fallback
    return "model_primary"


def _build_planner_intent_plan(
    state: MultiAgentState,
    *,
    llm: Any,
    mode: str = "model_primary",
) -> Dict[str, Any]:
    """构建 planner 节点使用的 intent_plan（模型主判定 + 规则兜底）。"""
    normalized_mode = _normalize_intent_mode(mode, default="model_primary")

    heuristic_plan = _infer_initial_intent_plan(state)
    if normalized_mode == "heuristic_only":
        return _normalize_intent_plan_allowed_agents(
            {
                "version": heuristic_plan.get("version", 1),
                "source": "heuristic_only",
                "user_query": heuristic_plan.get("user_query", ""),
                "goals": list(heuristic_plan.get("goals") or []),
                "planner_strategy": "heuristic_only",
            }
        )

    strategy_meta = _resolve_planner_structured_strategy(llm)
    planner_strategy = str(strategy_meta.get("strategy") or "legacy_json_object")
    try:
        structured_plan = _infer_model_intent_plan_by_strategy(state, llm)
        structured_plan.setdefault("planner_strategy", planner_strategy)
        return _normalize_intent_plan_allowed_agents(structured_plan)
    except Exception as exc:
        should_fallback, fallback_rule_id, fallback_trigger = _resolve_planner_fallback_strategy(exc)
        if not should_fallback:
            logger.exception("planner_model_error_without_fallback: %s", exc)
            raise

        fallback_reason_code = _resolve_planner_reason_code(
            fallback_rule_id=fallback_rule_id,
            fallback_trigger=fallback_trigger,
        )

        logger.warning("planner_model_fallback_to_heuristic: %s", exc)
        return _normalize_intent_plan_allowed_agents(
            {
                "version": heuristic_plan.get("version", 1),
                "source": "heuristic_fallback",
                "user_query": heuristic_plan.get("user_query", ""),
                "goals": list(heuristic_plan.get("goals") or []),
                "fallback_meta": {
                    "reason": f"planner_model_error:{type(exc).__name__}",
                    "detail": str(exc)[:200],
                    "fallback_rule_id": fallback_rule_id,
                    "trigger": fallback_trigger,
                    "reason_code": fallback_reason_code,
                },
                "planner_strategy": planner_strategy,
            }
        )


def _extract_goal_kind_signature(intent_plan: Optional[Dict[str, Any]]) -> list[str]:
    """提取目标类型签名（按目标顺序）。"""
    goals = list((intent_plan or {}).get("goals") or [])
    signatures: list[str] = []
    for goal in goals:
        if not isinstance(goal, dict):
            continue
        signatures.append(_normalize_model_goal_kind(str(goal.get("kind") or "general.reply")))
    return signatures


def _compute_intent_diff_rate(primary_plan: Optional[Dict[str, Any]], shadow_plan: Optional[Dict[str, Any]]) -> float:
    """计算主判定与 shadow 对账的差异率。"""
    primary_signatures = _extract_goal_kind_signature(primary_plan)
    shadow_signatures = _extract_goal_kind_signature(shadow_plan)
    total = max(len(primary_signatures), len(shadow_signatures), 1)

    diff_count = 0
    for idx in range(total):
        primary_kind = primary_signatures[idx] if idx < len(primary_signatures) else ""
        shadow_kind = shadow_signatures[idx] if idx < len(shadow_signatures) else ""
        if primary_kind != shadow_kind:
            diff_count += 1

    return round(diff_count / total, 4)


def _build_intent_shadow_metrics(
    *,
    state: MultiAgentState,
    intent_plan: Dict[str, Any],
    planner_mode: str,
    intent_shadow_enabled: bool,
) -> Dict[str, Any]:
    """构建意图灰度观测指标。"""
    normalized_mode = _normalize_intent_mode(planner_mode)
    source = str(intent_plan.get("source") or "").strip().lower()

    fallback_hit_rate = 1.0 if source == "heuristic_fallback" else 0.0
    effective_shadow_enabled = bool(intent_shadow_enabled) and normalized_mode == "model_primary"

    metrics: Dict[str, Any] = {
        "intent_mode": normalized_mode,
        "intent_shadow_enabled": effective_shadow_enabled,
        "intent_diff_rate": 0.0,
        "fallback_hit_rate": fallback_hit_rate,
    }
    if not effective_shadow_enabled:
        return metrics

    shadow_plan = _infer_initial_intent_plan(state)
    metrics["intent_diff_rate"] = _compute_intent_diff_rate(intent_plan, shadow_plan)
    metrics["intent_shadow_goal_count"] = len(shadow_plan.get("goals") or [])
    return metrics


def _resolve_intent_planner_settings(state: MultiAgentState) -> Dict[str, Any]:
    """读取 planner 运行配置，支持快速回滚与 shadow 灰度。"""
    default_mode = _normalize_intent_mode(state.get("intent_mode"), default="model_primary")
    settings: Dict[str, Any] = {
        "intent_mode": default_mode,
        "intent_shadow_enabled": False,
    }
    try:
        from app.services.config_resolver import ConfigResolver

        resolved = ConfigResolver.get_intent_shadow_settings(default_mode=default_mode)
    except Exception as exc:
        logger.warning("intent_planner_settings_resolve_failed: %s", exc)
        return settings

    settings["intent_mode"] = _normalize_intent_mode(
        resolved.get("intent_mode"),
        default=default_mode,
    )
    settings["intent_shadow_enabled"] = bool(resolved.get("intent_shadow_enabled", False))
    if settings["intent_mode"] == "heuristic_only":
        settings["intent_shadow_enabled"] = False
    return settings


def _goal_kind_bucket(kind: str) -> str:
    """将细粒度 kind 归一到匹配桶。"""
    normalized = str(kind or "").strip().lower()
    if normalized.startswith("todo"):
        return "todo"
    if normalized.startswith("data"):
        return "data"
    if normalized.startswith("chart"):
        return "chart"
    if normalized.startswith("research"):
        return "research"
    if normalized.startswith(("weather", "knowledge", "external")):
        return "external"
    return "general"


def _count_must_answer_goals(
    goal_source: Optional[Sequence[Dict[str, Any]] | Dict[str, Any]],
) -> int:
    """统计活动目标中 must_answer 数量。"""
    if isinstance(goal_source, dict):
        goals = [goal for goal in list(goal_source.get("goals") or []) if isinstance(goal, dict)]
    elif isinstance(goal_source, (list, tuple)):
        goals = [goal for goal in goal_source if isinstance(goal, dict)]
    else:
        goals = []
    return sum(1 for goal in goals if bool(goal.get("must_answer", True)))


def _should_enable_multi_intent_mode(
    *,
    handoff_batch_size: int,
    has_direct_lookup: bool,
    state: MultiAgentState,
) -> bool:
    """判定是否启用复合任务模式（优先使用问题合同，避免单 handoff 丢目标）。"""
    if handoff_batch_size > 1 or has_direct_lookup:
        return True
    return _count_must_answer_goals(_resolve_active_goals(state)) >= 2


def _coerce_replay_result_event(raw_event: Any) -> Optional[Dict[str, Any]]:
    """规范化回放 result_event 结构。"""

    if not isinstance(raw_event, dict):
        return None

    data_type = str(raw_event.get("data_type") or "").strip()
    if not data_type:
        return None

    normalized: Dict[str, Any] = dict(raw_event)
    normalized["data_type"] = data_type
    normalized["data"] = raw_event.get("data") if isinstance(raw_event.get("data"), dict) else {}

    message = _normalize_text_content(raw_event.get("message"))
    if message:
        normalized["message"] = message
    else:
        normalized.pop("message", None)

    return normalized


def _resolve_replay_result_events(additional_kwargs: Dict[str, Any]) -> tuple[list[Dict[str, Any]], str]:
    """按 read-old-write-new 语义解析 result_events。"""

    raw_events = additional_kwargs.get("result_events")
    if isinstance(raw_events, list):
        normalized_events = [
            item
            for item in (_coerce_replay_result_event(raw) for raw in raw_events)
            if item is not None
        ]
        if normalized_events:
            return normalized_events, "result_events"

    legacy_single = _coerce_replay_result_event(additional_kwargs.get("result_event"))
    if legacy_single is not None:
        return [legacy_single], "result_event"

    legacy_data_type = str(additional_kwargs.get("data_type") or "").strip()
    if legacy_data_type:
        legacy_pair_event = _coerce_replay_result_event(
            {
                "data_type": legacy_data_type,
                "data": additional_kwargs.get("data"),
                "message": additional_kwargs.get("message"),
                "sequence_number": additional_kwargs.get("sequence_number"),
                "envelope": additional_kwargs.get("envelope"),
            }
        )
        if legacy_pair_event is not None:
            return [legacy_pair_event], "data_type_data"

    return [], "none"


def _result_event_sort_key(event: Dict[str, Any], index: int) -> tuple[int, int, int]:
    """生成回放 result_event 稳定排序键。"""

    sequence_number = _parse_non_negative_int(event.get("sequence_number"), default=-1)
    if sequence_number >= 0:
        return (0, sequence_number, index)

    envelope = event.get("envelope")
    if isinstance(envelope, dict):
        envelope_sequence = _parse_non_negative_int(envelope.get("sequence_number"), default=-1)
        if envelope_sequence >= 0:
            return (0, envelope_sequence, index)

    return (1, index, index)


def _sort_result_events_by_sequence(events: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """按 sequence_number 对 result_events 保序。"""

    enumerated = [(idx, event) for idx, event in enumerate(events)]
    enumerated.sort(key=lambda pair: _result_event_sort_key(pair[1], pair[0]))
    return [event for _, event in enumerated]


def _extract_latest_structured_result(
    messages: Sequence[BaseMessage],
    *,
    data_type: str,
) -> Optional[Dict[str, Any]]:
    """提取当前轮最近的结构化结果（优先 canonical result_events[]）。"""
    target_data_type = str(data_type or "").strip()
    if not target_data_type:
        return None

    for message in reversed(messages or []):
        if str(getattr(message, "type", "")).lower().strip() != "ai":
            continue

        additional = getattr(message, "additional_kwargs", {}) or {}
        if not isinstance(additional, dict):
            continue

        replay_events, compat_source = _resolve_replay_result_events(additional)
        if not replay_events:
            continue

        ordered_events = _sort_result_events_by_sequence(replay_events)
        for event in reversed(ordered_events):
            if str(event.get("data_type") or "").strip() != target_data_type:
                continue

            payload = event.get("data")
            if not isinstance(payload, dict):
                payload = {}

            message_text = _normalize_text_content(event.get("message")) or _normalize_text_content(
                getattr(message, "content", "")
            )
            return {
                "data_type": target_data_type,
                "data": payload,
                "message": message_text,
                "compat_source": compat_source,
            }

    return None


def _extract_latest_research_result_payload(messages: Sequence[BaseMessage]) -> Optional[Dict[str, Any]]:
    """提取当前轮最近的 research_subagent 结构化结果。"""
    for message in reversed(messages or []):
        if not isinstance(message, ToolMessage):
            continue
        payload = AgentOutputParser.parse_research_result(str(getattr(message, "content", "")))
        if payload:
            return dict(payload)
    return None


def _build_research_display_markdown(payload: Dict[str, Any]) -> str:
    """将 research contract 渲染为用户可见 Markdown。"""
    summary_markdown = str(payload.get("summary_markdown") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    insufficiency = str(payload.get("insufficiency") or "").strip()

    display_markdown = summary_markdown or summary
    if display_markdown and insufficiency:
        return f"{display_markdown}\n\n> 证据不足：{insufficiency}"
    return display_markdown


def _build_research_deliverable(
    payload: Dict[str, Any],
    *,
    goal_id: str = "",
) -> Dict[str, Any]:
    """将 research contract 收口为统一交付物。"""
    normalized_payload = dict(payload or {})
    display_markdown = _build_research_display_markdown(normalized_payload)
    insufficiency = str(normalized_payload.get("insufficiency") or "").strip()
    evidence = [
        item
        for item in list(normalized_payload.get("evidence") or [])
        if isinstance(item, dict)
    ]

    summary = _normalize_tool_summary_text(normalized_payload.get("summary"), limit=220)
    if not summary:
        summary = _normalize_tool_summary_text(display_markdown, limit=220)
    if not summary and insufficiency:
        summary = _normalize_tool_summary_text(insufficiency, limit=220)

    kb_images = AgentOutputParser.parse_kb_images(json.dumps(normalized_payload, ensure_ascii=False)) or {}
    deliverable_payload: Dict[str, Any] = {
        "research_payload": normalized_payload,
        "evidence": evidence,
        "media_refs": list(normalized_payload.get("media_refs") or []),
    }
    if display_markdown:
        deliverable_payload["display_markdown"] = display_markdown
    if insufficiency:
        deliverable_payload["insufficiency"] = insufficiency
    if kb_images:
        deliverable_payload["kb_images"] = kb_images

    if summary or display_markdown or evidence:
        status = "success"
    elif insufficiency:
        status = "failed"
        deliverable_payload["failure_message"] = insufficiency
    else:
        status = "missing"
        deliverable_payload["failure_message"] = "综合研究仍待补齐"

    return {
        "kind": "research.execute",
        "goal_id": goal_id,
        "status": status,
        "summary": summary,
        "payload": deliverable_payload,
    }


def _ensure_active_goals_covers_runtime(
    state: MultiAgentState,
    base_goals: Optional[Sequence[Dict[str, Any]]] = None,
) -> list[Dict[str, Any]]:
    """根据运行时产物补齐活动目标，避免遗漏必答项。"""
    if isinstance(base_goals, Sequence) and not isinstance(base_goals, (str, bytes)):
        goals = [dict(goal) for goal in _normalize_active_goals(base_goals)]
    else:
        goals = [dict(goal) for goal in _resolve_active_goals(state)]

    seen_buckets = {_goal_kind_bucket(str(goal.get("kind") or "")) for goal in goals}
    turn_messages = _slice_messages_from_latest_human(state.get("messages", []))
    direct_findings = _build_direct_lookup_findings(turn_messages)
    research_payload = _extract_latest_research_result_payload(turn_messages)
    trace = list(state.get("handoff_execution_trace") or [])

    def _append_goal(kind: str, title: str) -> None:
        goals.append(
            {
                "goal_id": f"GOAL-{len(goals) + 1:02d}",
                "order": len(goals) + 1,
                "kind": kind,
                "title": title,
                "must_answer": True,
                "allowed_agents": _default_allowed_agents_for_goal_kind(kind),
            }
        )

    if direct_findings and "external" not in seen_buckets:
        _append_goal("external.lookup", "外部信息")
        seen_buckets.add("external")

    if research_payload and "research" not in seen_buckets:
        _append_goal("research.execute", "综合研究")
        seen_buckets.add("research")

    for item in trace:
        target_agent = str(item.get("target_agent") or "")
        if target_agent == AgentType.TODO and "todo" not in seen_buckets:
            _append_goal("todo.query", "待办事项")
            seen_buckets.add("todo")
        if target_agent == AgentType.DATA and "data" not in seen_buckets:
            _append_goal("data.query", "数据查询")
            seen_buckets.add("data")

    if not goals:
        return [_build_default_general_goal()]

    return _normalize_active_goals(goals)


def _build_delivery_artifacts(state: MultiAgentState) -> list[Dict[str, Any]]:
    """构建结构化交付物列表。"""
    turn_messages = _slice_messages_from_latest_human(state.get("messages", []))
    trace = list(state.get("handoff_execution_trace") or [])
    deliverables: list[Dict[str, Any]] = []

    active_goals = _coerce_active_goals_input(state.get("decomposed_goals") or [])
    direct_findings = _build_direct_lookup_findings(turn_messages)
    research_payload = _extract_latest_research_result_payload(turn_messages)
    weather_findings = [dict(item) for item in direct_findings if str(item.get("kind") or "") == "external.lookup"]
    knowledge_findings = [dict(item) for item in direct_findings if str(item.get("kind") or "") == "knowledge.lookup"]
    has_atomic_direct_goals = any(
        str(goal.get("kind") or "") in {"external.lookup", "knowledge.lookup", "chart.render"}
        for goal in active_goals
    )

    direct_answer_markdowns = [
        _sanitize_direct_answer_markdown(
            item.get("direct_answer_markdown"),
            handoff_display_text=_normalize_tool_summary_text(item.get("task_description"), limit=120),
        )
        for item in trace
        if _sanitize_direct_answer_markdown(
            item.get("direct_answer_markdown"),
            handoff_display_text=_normalize_tool_summary_text(item.get("task_description"), limit=120),
        )
    ]
    consumed_direct_answer_markdowns: set[str] = set()

    image_structured = _extract_latest_structured_result(turn_messages, data_type="image")
    if has_atomic_direct_goals:
        image_payload = dict((image_structured or {}).get("data") or {})
        image_url = str(image_payload.get("url") or "").strip()
        image_markdown = f"![生成的图表]({image_url})" if image_url else ""
        image_summary = _normalize_tool_summary_text((image_structured or {}).get("message"), limit=220) or "图表已生成"

        for goal in active_goals:
            goal_id = str(goal.get("goal_id") or "")
            goal_kind = str(goal.get("kind") or "")
            if goal_kind == "external.lookup" and weather_findings:
                finding = weather_findings.pop(0)
                payload = {"findings": [finding]}
                display_markdown = str(finding.get("display_markdown") or "").strip()
                if display_markdown:
                    payload["display_markdown"] = display_markdown
                deliverables.append(
                    {
                        "kind": goal_kind,
                        "goal_id": goal_id,
                        "status": "success",
                        "summary": str(finding.get("summary") or "").strip(),
                        "payload": payload,
                    }
                )
                continue

            if goal_kind == "knowledge.lookup" and knowledge_findings:
                finding = knowledge_findings.pop(0)
                deliverables.append(
                    {
                        "kind": goal_kind,
                        "goal_id": goal_id,
                        "status": "success",
                        "summary": str(finding.get("summary") or "").strip(),
                        "payload": {"findings": [finding]},
                    }
                )
                continue

            if goal_kind == "chart.render" and (image_markdown or image_summary):
                payload = dict(image_payload)
                if image_markdown:
                    payload["display_markdown"] = image_markdown
                deliverables.append(
                    {
                        "kind": goal_kind,
                        "goal_id": goal_id,
                        "status": "success",
                        "summary": image_summary,
                        "payload": payload,
                    }
                )
    elif direct_findings:
        direct_answer_markdown = direct_answer_markdowns[-1] if direct_answer_markdowns else ""
        display_markdown = direct_answer_markdown or _build_external_lookup_display_markdown_from_findings(direct_findings)
        summary = _normalize_tool_summary_text(display_markdown, limit=220) if display_markdown else "；".join(
            str(item.get("summary") or "").strip()
            for item in direct_findings
            if str(item.get("summary") or "").strip()
        )
        payload = {"findings": direct_findings}
        if display_markdown:
            payload["display_markdown"] = display_markdown
        if direct_answer_markdown:
            consumed_direct_answer_markdowns.add(direct_answer_markdown)
        deliverables.append(
            {
                "kind": "external.lookup",
                "status": "success",
                "summary": summary,
                "payload": payload,
            }
        )

    research_goals = [
        goal for goal in active_goals
        if str(goal.get("kind") or "") == "research.execute"
    ]
    if research_payload and research_goals:
        for goal in research_goals:
            deliverables.append(
                _build_research_deliverable(
                    research_payload,
                    goal_id=str(goal.get("goal_id") or ""),
                )
            )
    elif research_payload:
        deliverables.append(_build_research_deliverable(research_payload))

    todo_structured = _extract_latest_structured_result(turn_messages, data_type="todo_list")
    data_structured = _extract_latest_structured_result(turn_messages, data_type="sql_result")
    seen_general_reply_summaries: set[str] = set()

    for item in trace:
        target_agent = str(item.get("target_agent") or "")
        goal_id = str(item.get("goal_id") or "")
        result_excerpt = _normalize_tool_summary_text(item.get("result_excerpt"), limit=220)
        task_description = _normalize_tool_summary_text(item.get("task_description"), limit=120)
        direct_answer_markdown = _sanitize_direct_answer_markdown(
            item.get("direct_answer_markdown"),
            handoff_display_text=task_description,
        )
        direct_answer_summary = _normalize_tool_summary_text(direct_answer_markdown, limit=220)

        if direct_answer_markdown and direct_answer_markdown not in consumed_direct_answer_markdowns and direct_answer_summary and direct_answer_summary not in seen_general_reply_summaries:
            seen_general_reply_summaries.add(direct_answer_summary)
            consumed_direct_answer_markdowns.add(direct_answer_markdown)
            deliverables.append(
                {
                    "kind": "general.reply",
                    "status": "success",
                    "summary": direct_answer_summary,
                    "payload": {"display_markdown": direct_answer_markdown},
                }
            )

        if target_agent == AgentType.TODO:
            payload = dict((todo_structured or {}).get("data") or {})
            summary = result_excerpt or (todo_structured or {}).get("message") or ""
            if _is_coverage_reconcile_enabled():
                status = "success" if (summary or payload) else "missing"
                if status != "success" and not summary:
                    summary = "待办结果仍待补齐"
            else:
                status = "success"
                if not summary:
                    summary = "待办处理完成"
            deliverables.append(
                {
                    "kind": "todo.query",
                    "goal_id": goal_id,
                    "status": status,
                    "summary": summary,
                    "task_description": task_description,
                    "payload": payload,
                }
            )
            continue

        if target_agent == AgentType.DATA:
            payload = dict((data_structured or {}).get("data") or {})
            structured_message = _normalize_tool_summary_text((data_structured or {}).get("message"), limit=220)
            has_structured_result = data_structured is not None and bool(payload or structured_message)
            summary = structured_message or result_excerpt or ""
            if _is_coverage_reconcile_enabled():
                status = "success" if has_structured_result else ("failed" if summary else "missing")
                if status != "success" and summary:
                    payload["failure_message"] = summary
                if status == "missing" and not summary:
                    summary = "数据结果仍待补齐"
            else:
                status = "success"
                if not summary:
                    summary = "数据处理完成"
            deliverables.append(
                {
                    "kind": "data.query",
                    "goal_id": goal_id,
                    "status": status,
                    "summary": summary,
                    "task_description": task_description,
                    "payload": payload,
                }
            )
            continue

        if result_excerpt:
            deliverables.append(
                {
                    "kind": "general.reply",
                    "goal_id": goal_id,
                    "status": "success",
                    "summary": result_excerpt,
                    "task_description": task_description,
                    "payload": {},
                }
            )

    return deliverables


def _deliverable_has_runtime_evidence(deliverable: Dict[str, Any]) -> bool:
    """判定交付物是否具备可验证的运行时证据。"""
    summary = _normalize_tool_summary_text(deliverable.get("summary"), limit=280)
    if summary:
        return True

    payload = deliverable.get("payload")
    if isinstance(payload, dict):
        return bool(payload)
    if isinstance(payload, list):
        return bool(payload)
    if payload is None:
        return False
    return bool(str(payload).strip())


def _can_match_deliverable_for_coverage(deliverable: Dict[str, Any]) -> bool:
    """判定交付物是否可参与 coverage 对账。"""
    if not _is_coverage_reconcile_enabled():
        return True

    status = str(deliverable.get("status") or "").strip().lower()
    if status and status != "success":
        return False
    if status == "success":
        return True
    return _deliverable_has_runtime_evidence(deliverable)


def _can_render_goal_attempt(deliverable: Dict[str, Any]) -> bool:
    """判定交付物是否可作为“已尝试但未完成”的用户可见证据。"""
    status = str(deliverable.get("status") or "").strip().lower()
    if status == "success":
        return True
    return _deliverable_has_runtime_evidence(deliverable)


def _match_goals_with_deliverables(
    goals: Sequence[Dict[str, Any]],
    deliverables: Sequence[Dict[str, Any]],
    *,
    include_non_success: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """按顺序匹配 goal 与 deliverable。"""
    result: Dict[str, Dict[str, Any]] = {}
    used_indexes: set[int] = set()
    matcher = _can_render_goal_attempt if include_non_success else _can_match_deliverable_for_coverage

    for goal in goals:
        goal_id = str(goal.get("goal_id") or "")
        goal_bucket = _goal_kind_bucket(str(goal.get("kind") or ""))
        matched_idx: Optional[int] = None

        for idx, deliverable in enumerate(deliverables):
            if idx in used_indexes:
                continue
            if not matcher(deliverable):
                continue
            deliverable_goal_id = str(deliverable.get("goal_id") or "")
            if goal_id and deliverable_goal_id and deliverable_goal_id == goal_id:
                matched_idx = idx
                break

        if matched_idx is None:
            for idx, deliverable in enumerate(deliverables):
                if idx in used_indexes:
                    continue
                if not matcher(deliverable):
                    continue
                deliverable_bucket = _goal_kind_bucket(str(deliverable.get("kind") or ""))
                if goal_bucket == deliverable_bucket:
                    matched_idx = idx
                    break

        if matched_idx is None and goal_bucket == "general":
            for idx, deliverable in enumerate(deliverables):
                if idx in used_indexes:
                    continue
                if not matcher(deliverable):
                    continue
                if _goal_kind_bucket(str(deliverable.get("kind") or "")) != "external":
                    matched_idx = idx
                    break

        if matched_idx is None:
            continue

        used_indexes.add(matched_idx)
        matched_deliverable = dict(deliverables[matched_idx])
        if goal_id and not str(matched_deliverable.get("goal_id") or "").strip():
            matched_deliverable["goal_id"] = goal_id
        result[goal_id] = matched_deliverable

    return result


def _coerce_active_goals_input(active_goals: Any) -> list[Dict[str, Any]]:
    """将活动目标输入归一为 goals 列表（兼容 intent_plan 字典）。"""
    if isinstance(active_goals, dict):
        raw_goals = active_goals.get("goals")
        if isinstance(raw_goals, list):
            return _normalize_active_goals([goal for goal in raw_goals if isinstance(goal, dict)])
        return [_build_default_general_goal()]

    if isinstance(active_goals, Sequence) and not isinstance(active_goals, (str, bytes)):
        return _normalize_active_goals([goal for goal in active_goals if isinstance(goal, dict)])

    return [_build_default_general_goal()]


def _compute_coverage_report(
    active_goals: Sequence[Dict[str, Any]],
    deliverables: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """计算问题覆盖率报告。"""
    goals = _coerce_active_goals_input(active_goals)
    matched = _match_goals_with_deliverables(goals, deliverables)
    attempts = _match_goals_with_deliverables(goals, deliverables, include_non_success=True)
    missing: list[Dict[str, str]] = []

    for goal in goals:
        goal_id = str(goal.get("goal_id") or "")
        if not bool(goal.get("must_answer", True)):
            continue
        if goal_id not in matched:
            missing.append(
                {
                    "goal_id": goal_id,
                    "title": str(goal.get("title") or goal.get("kind") or "未命名目标"),
                    "reason": "missing_deliverable",
                }
            )

    pass_flag = len(missing) == 0
    return {
        "pass": pass_flag,
        "total_goals": len(goals),
        "answered_goals": len(matched),
        "missing_goals": missing,
        "matched_goal_ids": list(matched.keys()),
        "goal_results": matched,
        "goal_attempts": attempts,
    }


def _render_todo_deliverable_text(deliverable: Dict[str, Any]) -> str:
    """渲染待办交付内容。"""
    payload = deliverable.get("payload") or {}
    todos = payload.get("todos") if isinstance(payload, dict) else None
    if not isinstance(todos, list):
        return str(deliverable.get("summary") or "待办处理完成")

    if not todos:
        return "当前没有符合条件的待办事项。"

    head = f"共 {len(todos)} 项待办。"
    item_texts: list[str] = []
    for todo in todos[:5]:
        if not isinstance(todo, dict):
            continue
        title = str(todo.get("title") or "未命名待办").strip()
        status = str(todo.get("status") or "").strip()
        due = str(todo.get("due_date") or "").strip()
        meta_parts = [part for part in (status, due) if part]
        if meta_parts:
            item_texts.append(f"{title}（{' / '.join(meta_parts)}）")
        else:
            item_texts.append(title)

    if not item_texts:
        return head
    return f"{head} 重点：{'；'.join(item_texts)}。"


def _extract_deliverable_display_markdown(deliverable: Dict[str, Any]) -> str:
    """提取交付物中的用户可见 Markdown 正文。"""
    payload = deliverable.get("payload") or {}
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("display_markdown") or "").strip()


def _render_external_lookup_deliverable_text(deliverable: Dict[str, Any]) -> str:
    """渲染外部信息交付内容，优先保留结构化富文本格式。"""
    payload = deliverable.get("payload") or {}
    if isinstance(payload, dict):
        display_markdown = str(payload.get("display_markdown") or "").strip()
        if display_markdown:
            return display_markdown

        findings = payload.get("findings")
        if isinstance(findings, list):
            summaries: list[str] = []
            for item in findings[:3]:
                if not isinstance(item, dict):
                    continue
                summary = str(item.get("summary") or "").strip()
                if not summary:
                    continue
                summaries.append(summary)
            if len(summaries) > 1:
                return "\n".join(f"- {summary}" for summary in summaries)
            if summaries:
                return summaries[0]

    return str(deliverable.get("summary") or "已处理完成。")


def _extract_incomplete_goal_message(deliverable: Dict[str, Any]) -> str:
    """提取未完成 goal 的稳定失败/缺口说明。"""
    payload = deliverable.get("payload") or {}
    if isinstance(payload, dict):
        for field in ("failure_message", "message"):
            text = _normalize_tool_summary_text(payload.get(field), limit=280)
            if text:
                return text

    return _normalize_tool_summary_text(deliverable.get("summary"), limit=280)


def _render_goal_answer(goal: Dict[str, Any], deliverable: Optional[Dict[str, Any]]) -> str:
    """渲染单个 goal 的用户答复文本。"""
    title = str(goal.get("title") or goal.get("kind") or "问题").strip()
    if not deliverable:
        return f"{title}：暂未完成，缺少可用结果。"

    status = str(deliverable.get("status") or "success").strip().lower() or "success"
    if status != "success":
        incomplete_message = _extract_incomplete_goal_message(deliverable)
        if not incomplete_message:
            return f"{title}：暂未完成，缺少可用结果。"
        if "\n" in incomplete_message:
            return f"{title}：暂未完成。\n{incomplete_message}"
        return f"{title}：暂未完成，{incomplete_message}"

    display_markdown = _extract_deliverable_display_markdown(deliverable)
    if display_markdown:
        if "\n" in display_markdown:
            return f"{title}：\n{display_markdown}"
        return f"{title}：{display_markdown}"

    bucket = _goal_kind_bucket(str(goal.get("kind") or ""))
    if bucket == "todo":
        return f"{title}：{_render_todo_deliverable_text(deliverable)}"
    if bucket == "external":
        external_text = _render_external_lookup_deliverable_text(deliverable).strip()
        if "\n" in external_text:
            return f"{title}：\n{external_text}"
        return f"{title}：{external_text or '已处理完成。'}"

    summary = _normalize_tool_summary_text(deliverable.get("summary"), limit=280)
    if not summary:
        summary = "已处理完成。"
    return f"{title}：{summary}"


def _collect_missing_goal_titles(
    active_goals: Sequence[Dict[str, Any]],
    coverage_report: Dict[str, Any],
) -> list[str]:
    """收集 coverage 缺口对应的用户可见目标标题。"""
    goals = sorted(
        _coerce_active_goals_input(active_goals),
        key=lambda item: int(item.get("order") or 0),
    )
    missing_goals = list(coverage_report.get("missing_goals") or [])
    missing_ids = {str(item.get("goal_id") or "") for item in missing_goals}

    pending_titles: list[str] = []
    for goal in goals:
        goal_id = str(goal.get("goal_id") or "")
        if goal_id in missing_ids:
            pending_titles.append(str(goal.get("title") or goal.get("kind") or "未命名目标"))

    if pending_titles:
        return pending_titles

    return [
        str(item.get("title") or item.get("goal_id") or "未命名目标")
        for item in missing_goals
    ]


def _render_final_answer(
    active_goals: Sequence[Dict[str, Any]],
    coverage_report: Dict[str, Any],
) -> str:
    """根据问题合同与覆盖报告生成唯一最终答复。"""
    goals = sorted(
        _coerce_active_goals_input(active_goals),
        key=lambda item: int(item.get("order") or 0),
    )
    goal_results = dict(coverage_report.get("goal_results") or {})
    goal_attempts = dict(coverage_report.get("goal_attempts") or {})

    lines: list[str] = ["按你的问题顺序，逐项回复如下："]
    for idx, goal in enumerate(goals, start=1):
        goal_id = str(goal.get("goal_id") or "")
        deliverable = goal_results.get(goal_id) or goal_attempts.get(goal_id)
        answer = _render_goal_answer(goal, deliverable)
        answer_lines = str(answer).splitlines() or [""]
        lines.append(f"{idx}. {answer_lines[0]}")
        for extra_line in answer_lines[1:]:
            lines.append(f"    {extra_line}" if extra_line else "")

    missing_titles = _collect_missing_goal_titles(goals, coverage_report)
    if missing_titles:
        lines.append(
            f"未完成部分：{'、'.join(missing_titles)}。本轮先返回已确认结果，剩余部分请稍后重试。"
        )
    else:
        lines.append("以上问题已全部覆盖。")

    return "\n".join(lines)


def _render_coverage_blocked_message(
    active_goals: Sequence[Dict[str, Any]],
    coverage_report: Dict[str, Any],
) -> str:
    """渲染 coverage 未通过时的用户可见阻塞说明。"""
    pending_titles = _collect_missing_goal_titles(active_goals, coverage_report)
    if pending_titles:
        lines = ["本轮还有以下部分暂未取得可用结果："]
        lines.extend([f"- {title}" for title in pending_titles])
        lines.append("")
        lines.append("这属于系统内部补齐未完成，不需要你额外回复。请稍后重试。")
        return "\n".join(lines)

    return "本轮仍有内容暂未完成，不需要你额外回复。请稍后重试。"


def _resolve_handoff_display_text(handoff: Dict[str, Any], *, limit: int = 240) -> str:
    """返回 handoff 的可展示摘要；data.query 仅消费 frame.query_text。"""
    if not isinstance(handoff, dict):
        return ""

    frame = handoff.get("frame")
    if handoff.get("target_agent") == AgentType.DATA:
        if isinstance(frame, dict):
            return _normalize_tool_summary_text(frame.get("query_text"), limit=limit)
        return ""

    task_description = _normalize_tool_summary_text(handoff.get("task_description"), limit=limit)
    if task_description:
        return task_description

    if isinstance(frame, dict):
        return _normalize_tool_summary_text(frame.get("query_text"), limit=limit)

    return ""


def _augment_data_handoff_payload(
    handoff_data: Dict[str, Any],
    state: MultiAgentState,
) -> Dict[str, Any]:
    """规范化 data_expert handoff，仅消费结构化 frame。"""
    if not isinstance(handoff_data, dict):
        return handoff_data

    if handoff_data.get("target_agent") != AgentType.DATA:
        return handoff_data

    enriched = dict(handoff_data)
    base_frame = enriched.get("frame")
    frame = dict(base_frame) if isinstance(base_frame, dict) else {}

    turn_act_hint = str(enriched.get("turn_act_hint") or "").strip().upper()
    if turn_act_hint not in TURN_ACT_HINTS:
        state_turn_act = str(state.get("turn_act") or "").strip().upper()
        if state_turn_act in TURN_ACT_HINTS:
            turn_act_hint = state_turn_act
        else:
            turn_act_hint = "NEW_QUERY"
    enriched["turn_act_hint"] = turn_act_hint

    query_text = _normalize_text_content(frame.get("query_text"))
    task_description = _normalize_text_content(enriched.get("task_description"))
    if not query_text and should_compile_data_handoff_from_task_description(task_description):
        query_text = task_description

    if query_text:
        try:
            from app.ai.workflow.data_graph import build_data_query_handoff_frame

            enriched["frame"] = build_data_query_handoff_frame(query_text, base_frame=frame)
        except Exception as exc:
            logger.warning("data_handoff_frame_build_failed: %s", exc)
            enriched["frame"] = {**frame, "query_text": query_text} if frame else {"query_text": query_text}
    else:
        enriched["frame"] = frame or None

    logger.info(
        "data_handoff_normalized: turn_act_hint=%s, has_frame=%s, has_query_text=%s",
        enriched.get("turn_act_hint"),
        bool(enriched.get("frame")),
        bool(query_text),
    )
    return enriched


def _build_stream_error_message(error_text: str) -> str:
    """将底层异常转换为面向用户的稳定文案。"""
    if _is_model_access_error(error_text):
        return "模型服务当前不可用（配额/订阅或权限异常），请稍后重试或联系管理员检查模型配置。"
    return "系统繁忙，当前请求暂时无法处理，请稍后重试。"


def fallback_router(node_name: str, state: MultiAgentState, error_text: str) -> Dict[str, Any]:
    """统一决定流式异常 fallback 路由。"""
    if not _is_runtime_recovery_enabled():
        return {
            "route": "friendly_error",
            "message": _build_stream_error_message(error_text),
            "runtime_recovery_state": _build_runtime_recovery_state(
                state,
                fallback_route="recovery_disabled",
                error_text=error_text,
                fallback_triggered=False,
                plugin_lifecycle_status=_resolve_plugin_lifecycle_status(state, error_text),
            ),
        }

    if node_name == "supervisor" and _is_model_access_error(error_text):
        return {
            "route": "friendly_error",
            "message": _build_stream_error_message(error_text),
            "runtime_recovery_state": _build_runtime_recovery_state(
                state,
                fallback_route="supervisor_fallback",
                error_text=error_text,
                fallback_triggered=True,
                plugin_lifecycle_status=_resolve_plugin_lifecycle_status(state, error_text),
            ),
        }

    if _resolve_plugin_lifecycle_status(state, error_text) == "unhealthy":
        degrade_message = "插件能力暂不可用，已自动降级为核心能力回答。"
        return {
            "route": "core_tools_only",
            "message": degrade_message,
            "runtime_recovery_state": _build_runtime_recovery_state(
                state,
                fallback_route="core_tools_only",
                error_text=error_text,
                fallback_triggered=True,
                plugin_lifecycle_status="unhealthy",
            ),
        }

    return {
        "route": "friendly_error",
        "message": _build_stream_error_message(error_text),
        "runtime_recovery_state": _build_runtime_recovery_state(
            state,
            fallback_route="friendly_error",
            error_text=error_text,
            fallback_triggered=True,
            plugin_lifecycle_status=_resolve_plugin_lifecycle_status(state, error_text),
        ),
    }


def _normalize_tool_summary_text(value: Any, limit: int = 180) -> str:
    """清洗并截断工具文本，避免把噪声大段透传给待办。"""
    raw = str(value or "")
    cleaned = re.sub(r"\s+", " ", raw).strip()
    if not cleaned:
        return ""
    return cleaned[:limit]


def _truncate_tool_message_text(
    text: str,
    *,
    char_limit: int = SUPERVISOR_TOOL_MESSAGE_CHAR_LIMIT,
    head_chars: int = SUPERVISOR_TOOL_MESSAGE_HEAD_CHARS,
    tail_chars: int = SUPERVISOR_TOOL_MESSAGE_TAIL_CHARS,
) -> str:
    """压缩超长工具结果，保留首尾关键信息，避免污染后续路由。"""
    raw = str(text or "")
    if len(raw) <= char_limit:
        return raw

    head = raw[:head_chars].rstrip()
    tail = raw[-tail_chars:].lstrip()
    omitted_chars = max(len(raw) - len(head) - len(tail), 0)
    omitted_notice = (
        f"\n\n...[工具输出过长，已省略 {omitted_chars} 字符，"
        "完整内容已保存在消息存储中]...\n\n"
    )
    return f"{head}{omitted_notice}{tail}"


def _build_truncated_tool_message(
    message: ToolMessage,
    *,
    compacted_text: str,
    raw_chars: int,
    compacted_chars: int,
) -> ToolMessage:
    """构造带诊断字段的压缩 ToolMessage。"""
    additional_kwargs = dict(getattr(message, "additional_kwargs", {}) or {})
    additional_kwargs.update(
        {
            "truncation_flag": True,
            "tool_message_chars_before": raw_chars,
            "tool_message_chars_after": compacted_chars,
        }
    )

    if hasattr(message, "model_copy"):
        return message.model_copy(update={"content": compacted_text, "additional_kwargs": additional_kwargs})

    return ToolMessage(
        content=compacted_text,
        tool_call_id=str(getattr(message, "tool_call_id", "unknown_tool_call")),
        name=getattr(message, "name", None),
        id=getattr(message, "id", None),
        additional_kwargs=additional_kwargs,
        response_metadata=dict(getattr(message, "response_metadata", {}) or {}),
        artifact=getattr(message, "artifact", None),
        status=getattr(message, "status", "success"),
    )


def _compact_tool_message_for_inference(message: ToolMessage) -> tuple[ToolMessage, bool, int, int]:
    """仅在推理输入阶段压缩 ToolMessage，不影响持久化原始消息。"""
    content_text = _normalize_text_content(getattr(message, "content", ""))
    raw_chars = len(content_text)
    compacted_text = _truncate_tool_message_text(content_text)
    if compacted_text == content_text:
        return message, False, raw_chars, raw_chars

    compacted_chars = len(compacted_text)
    try:
        compacted_message = _build_truncated_tool_message(
            message,
            compacted_text=compacted_text,
            raw_chars=raw_chars,
            compacted_chars=compacted_chars,
        )
    except Exception as exc:
        logger.debug("ToolMessage 压缩失败，回退原消息: %s", exc)
        return message, False, raw_chars, raw_chars

    return compacted_message, True, raw_chars, compacted_chars


def _is_ragflow_tool_message(message: ToolMessage) -> bool:
    """判断是否为知识库检索 ToolMessage。"""
    tool_name = str(getattr(message, "name", "") or "").strip().lower()
    return tool_name in {"knowledge_search", "knowledge-search"}


def _resolve_rollout_stage(default: str = "baseline") -> str:
    """读取 RAGFlow 当前灰度档位。"""
    from app.ai import config as ai_config

    raw_stage = getattr(ai_config, "RAGFLOW_ROLLOUT_STAGE", None)
    if raw_stage is None:
        raw_stage = os.getenv("RAGFLOW_ROLLOUT_STAGE", default)
    stage = str(raw_stage or default).strip()
    return stage or default


def _resolve_rollout_traffic_percent(default: int = 100) -> int:
    """读取 RAGFlow 当前灰度流量比例（0-100）。"""
    from app.ai import config as ai_config

    raw_value = getattr(ai_config, "RAGFLOW_ROLLOUT_TRAFFIC_PERCENT", None)
    if raw_value is None:
        raw_value = os.getenv("RAGFLOW_ROLLOUT_TRAFFIC_PERCENT", default)

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(parsed, 100))


def _prepare_messages_for_supervisor_inference(
    messages: Sequence[BaseMessage],
    *,
    diagnostics: Optional[Dict[str, Any]] = None,
) -> list[BaseMessage]:
    """准备 Supervisor 推理输入，压缩超长工具消息。"""
    prepared: list[BaseMessage] = []
    tool_message_count = 0
    compacted_count = 0
    tool_message_chars_before = 0
    tool_message_chars_after = 0
    retrieval_tool_message_count = 0
    retrieval_truncated_tool_message_count = 0
    retrieval_tool_message_chars_before = 0
    retrieval_tool_message_chars_after = 0

    for message in messages or []:
        if isinstance(message, ToolMessage):
            tool_message_count += 1
            compacted, truncated, chars_before, chars_after = _compact_tool_message_for_inference(message)
            if truncated:
                compacted_count += 1
            tool_message_chars_before += chars_before
            tool_message_chars_after += chars_after
            if _is_ragflow_tool_message(message):
                retrieval_tool_message_count += 1
                retrieval_tool_message_chars_before += chars_before
                retrieval_tool_message_chars_after += chars_after
                if truncated:
                    retrieval_truncated_tool_message_count += 1
            prepared.append(compacted)
            continue
        prepared.append(message)

    truncation_flag = compacted_count > 0
    if diagnostics is not None:
        diagnostics.update(
            {
                "tool_message_count": tool_message_count,
                "truncated_tool_message_count": compacted_count,
                "tool_message_chars_before": tool_message_chars_before,
                "tool_message_chars_after": tool_message_chars_after,
                "truncation_flag": truncation_flag,
                "retrieval_tool_message_count": retrieval_tool_message_count,
                "retrieval_truncated_tool_message_count": retrieval_truncated_tool_message_count,
                "retrieval_tool_message_chars_before": retrieval_tool_message_chars_before,
                "retrieval_tool_message_chars_after": retrieval_tool_message_chars_after,
                "retrieval_truncation_flag": retrieval_truncated_tool_message_count > 0,
            }
        )

    if compacted_count:
        logger.info(
            "Supervisor 上下文压缩: compacted_tool_messages=%d, tool_chars=%d->%d",
            compacted_count,
            tool_message_chars_before,
            tool_message_chars_after,
        )

    return prepared


def _is_tool_message_error(message: ToolMessage) -> bool:
    """判定 ToolMessage 是否为错误状态。"""
    status = str(getattr(message, "status", "") or "").strip().lower()
    return status in {"error", "failed", "failure"}


def _extract_supervisor_tool_observations(messages: Sequence[BaseMessage]) -> list[dict[str, str]]:
    """提取 Supervisor 本轮工具观察结果，供 TodoExpert 合并描述。"""
    observations: list[dict[str, str]] = []

    for msg in messages or []:
        if not isinstance(msg, ToolMessage):
            continue

        tool_name = str(getattr(msg, "name", "") or "unknown")
        if _is_tool_message_error(msg):
            continue

        tool_content = str(getattr(msg, "content", "") or "")
        if not tool_content:
            continue

        lowered_name = tool_name.lower()
        if "tavily" not in lowered_name:
            continue

        summary = _summarize_tavily_tool_output(tool_content)
        if not summary:
            continue

        observations.append(
            {
                "tool": tool_name,
                "topic": "web_search",
                "summary": summary,
                "status": "ok",
            }
        )

    return observations[:2]


def _is_todo_external_enrichment_request(user_text: str) -> bool:
    """判断是否是“待办补充外部信息”的表达。"""
    return intent_is_todo_external_enrichment_request(user_text)


def _augment_todo_handoff_with_observations(
    handoff_data: Dict[str, Any],
    delta_messages: Sequence[BaseMessage],
    state: MultiAgentState,
) -> Dict[str, Any]:
    """将 Supervisor 工具观察结果并入 todo handoff 结构化 frame。"""
    if not isinstance(handoff_data, dict):
        return handoff_data

    if handoff_data.get("target_agent") != AgentType.TODO:
        return handoff_data

    observations = _extract_supervisor_tool_observations(delta_messages)
    if not observations:
        return handoff_data

    enriched = dict(handoff_data)
    frame = dict(enriched.get("frame") or {})
    todo_fields = dict(frame.get("todo_fields") or {})

    current_todo_id = state.get("current_todo_id")
    if current_todo_id and not todo_fields.get("todo_id"):
        todo_fields["todo_id"] = current_todo_id
        frame.setdefault("todo_target_id", str(current_todo_id))

    if current_todo_id and not str(frame.get("todo_action") or "").strip():
        frame["todo_action"] = "update"

    user_text = _extract_latest_human_content(state.get("messages", []))
    todo_action = str(frame.get("todo_action") or "").strip()
    has_todo_target = bool(current_todo_id or todo_fields.get("todo_id") or frame.get("todo_target_id"))
    should_attach_observations = should_attach_todo_observations(
        user_text,
        str(enriched.get("task_description") or ""),
        todo_action=todo_action,
        has_todo_target=has_todo_target,
    )
    if not should_attach_observations:
        return handoff_data

    frame["tool_observations"] = observations

    summary_lines = [obs.get("summary", "") for obs in observations if obs.get("summary")]
    summary_text = "；".join(summary_lines)
    summary_text = _normalize_tool_summary_text(summary_text, limit=280)

    if summary_text:
        existing_desc = _normalize_tool_summary_text(todo_fields.get("description"), limit=280)
        if not existing_desc:
            todo_fields["description"] = f"外部信息补充：{summary_text}"
        elif summary_text not in existing_desc:
            todo_fields["description"] = f"{existing_desc}\n外部信息补充：{summary_text}"

        task_description = str(enriched.get("task_description") or "").strip()
        if "外部信息摘要" not in task_description:
            addon = f"外部信息摘要：{summary_text}"
            enriched["task_description"] = f"{task_description}\n{addon}" if task_description else addon

    if todo_fields:
        frame["todo_fields"] = todo_fields

    user_text = _extract_latest_human_content(state.get("messages", []))
    if (
        current_todo_id
        and _is_todo_external_enrichment_request(user_text)
        and not str(enriched.get("turn_act_hint") or "").strip()
    ):
        enriched["turn_act_hint"] = "SUPPLEMENT"

    enriched["frame"] = frame
    logger.info(
        "handoff_with_observation: target=%s, observations=%d, todo_id=%s",
        enriched.get("target_agent"),
        len(observations),
        todo_fields.get("todo_id"),
    )
    return enriched


def _build_streaming_handoff_return(
    final_state: Dict[str, Any],
    delta_messages: Sequence[BaseMessage],
    handoff_data: Dict[str, Any],
    *,
    handoff_queue: Optional[list[Dict[str, Any]]] = None,
    multi_intent_mode: bool = False,
) -> Dict[str, Any]:
    """构造命中 handoff 后的增量返回结构。"""
    other_keys = {k: v for k, v in final_state.items() if k != "messages"}
    ret = other_keys.copy()
    ret["messages"] = list(delta_messages)
    ret["pending_handoff"] = handoff_data
    ret["handoff_queue"] = list(handoff_queue or [])
    ret["multi_intent_mode"] = bool(multi_intent_mode)
    ret["completed_handoffs"] = []
    ret["handoff_execution_trace"] = []
    return ret


def _resolve_loaded_skill_ids_for_handoff(state: Optional[Dict[str, Any]]) -> List[str]:
    """从运行态或历史消息恢复 handoff 可见的已加载 skill 列表。"""
    normalized_state = state if isinstance(state, dict) else {}
    loaded_skill_registry = normalized_state.get("loaded_skill_registry") or {}
    if loaded_skill_registry:
        return [str(skill_id).strip() for skill_id in loaded_skill_registry if str(skill_id or "").strip()]

    messages = list(normalized_state.get("messages") or [])
    tool_message_skill_ids: List[str] = []
    for message in messages:
        if not isinstance(message, ToolMessage) or str(getattr(message, "name", "") or "").strip() != "load_skills":
            continue
        additional_kwargs = getattr(message, "additional_kwargs", None)
        load_result = additional_kwargs.get("load_skills_result") if isinstance(additional_kwargs, dict) else None
        if not isinstance(load_result, dict):
            continue
        for item in load_result.get("loaded_skills") or []:
            if not isinstance(item, dict):
                continue
            skill_id = str(item.get("skill_id") or "").strip()
            if skill_id and skill_id not in tool_message_skill_ids:
                tool_message_skill_ids.append(skill_id)
    if tool_message_skill_ids:
        return tool_message_skill_ids

    restored_registry = _restore_loaded_skill_registry_from_messages(messages)
    return [str(skill_id).strip() for skill_id in restored_registry if str(skill_id or "").strip()]


def _build_handoff_status_message(target_agent: str, state: Optional[Dict[str, Any]] = None) -> str:
    """构造专家委派状态文案。"""
    normalized_agent = str(target_agent or "").strip()
    loaded_skill_ids = _resolve_loaded_skill_ids_for_handoff(state)
    prefix = ""
    if loaded_skill_ids:
        preview = "、".join(loaded_skill_ids[:3])
        if len(loaded_skill_ids) > 3:
            preview = f"{preview} 等 {len(loaded_skill_ids)} 个"
        prefix = f"已加载 {preview}，"
    if normalized_agent == AgentType.DATA:
        return f"{prefix}正在委派 data_expert。" if prefix else "已识别为数据查询，正在委派 data_expert。"
    if normalized_agent == AgentType.TODO:
        return f"{prefix}正在委派 todo_expert。" if prefix else "已识别为待办请求，正在委派 todo_expert。"
    return f"{prefix}正在委派 {normalized_agent or 'expert'}。" if prefix else f"正在委派 {normalized_agent or 'expert'}。"


def _build_handoff_event_payload(target_agent: str, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构造 handoff 事件载荷。"""
    normalized_agent = str(target_agent or "").strip() or "expert"
    loaded_skill_ids = _resolve_loaded_skill_ids_for_handoff(state)
    return {
        "target_agent": normalized_agent,
        "loaded_skill_ids": loaded_skill_ids,
        "message": _build_handoff_status_message(normalized_agent, state),
    }


def _normalize_handoff_batch_for_supervisor(
    handoffs: Sequence[Dict[str, Any]],
    *,
    delta_messages: Sequence[BaseMessage],
    state: MultiAgentState,
) -> list[Dict[str, Any]]:
    """标准化 Supervisor 当前轮提取到的 handoff 列表。"""
    normalized: list[Dict[str, Any]] = []
    for handoff in handoffs or []:
        handoff_data = _augment_todo_handoff_with_observations(handoff, delta_messages, state)
        handoff_data = _augment_data_handoff_payload(handoff_data, state)
        normalized.append(handoff_data)
    return normalized

def _infer_primary_goal_bucket_from_query_text(query_text: str) -> str:
    """粗判片段主目标桶。"""
    return infer_primary_goal_bucket_from_text(query_text)


def _split_user_query_for_goal_compile(user_query: str) -> list[str]:
    """按复合请求连接词切分用户问题，供 goal compiler 选择子任务文本。"""
    return split_composite_query(user_query)


def _compile_data_goal_query_text(
    *,
    user_query: str,
    goal: Dict[str, Any],
) -> str:
    """根据 user_query + 当前 data goal 编译稳定 query_text。"""
    goal_title = _normalize_text_content(goal.get("title"))
    if goal_title and goal_title != _default_goal_title("data.query"):
        if _infer_primary_goal_bucket_from_query_text(goal_title) == "data":
            return goal_title

    segments = _split_user_query_for_goal_compile(user_query)
    for segment in segments:
        if _infer_primary_goal_bucket_from_query_text(segment) == "data":
            return segment

    return user_query


def _build_compiled_data_goal_handoff(
    *,
    state: MultiAgentState,
    goal: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """基于当前 data goal 直接编译 canonical handoff，不再依赖 Supervisor data tool。"""
    if _goal_kind_bucket(str(goal.get("kind") or "")) != "data":
        return None

    user_query = _resolve_semantic_user_query(state)
    query_text = _compile_data_goal_query_text(user_query=user_query, goal=goal)
    if not query_text:
        return None

    try:
        from app.ai.workflow.data_graph import build_data_query_handoff_frame
    except Exception as exc:
        logger.warning("data_goal_compile_import_failed: %s", exc)
        return None

    base_frame = state.get("session_frame") if isinstance(state.get("session_frame"), dict) else None
    frame = build_data_query_handoff_frame(query_text, base_frame=base_frame)
    turn_act_hint = str(state.get("turn_act") or "").strip().upper()
    if turn_act_hint not in TURN_ACT_HINTS:
        turn_act_hint = "NEW_QUERY"

    compiled = {
        "action": "handoff",
        "target_agent": AgentType.DATA,
        "frame": frame,
        "turn_act_hint": turn_act_hint,
        "compiled_by": "goal_contract",
    }
    logger.info(
        "data_goal_compiled: goal_id=%s, title=%s, query_text=%s",
        goal.get("goal_id"),
        goal.get("title"),
        _normalize_tool_summary_text(query_text, limit=160),
    )
    return _augment_data_handoff_payload(compiled, state)


def _resolve_dispatch_queue_with_query_fallback(
    state: Optional[Dict[str, Any]],
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], str]:
    """优先用现有 active_goals，缺失时再用最近用户 query 回推 dispatch queue。"""

    normalized_state = dict(state or {})
    active_goals = _resolve_active_goals(normalized_state)
    dispatch_queue = _build_router_dispatch_goal_queue(active_goals)
    if dispatch_queue:
        return active_goals, dispatch_queue, ""

    latest_user_text = _extract_latest_human_content(normalized_state.get("messages", []))
    if not latest_user_text:
        return active_goals, [], ""

    fallback_goals = _build_decomposed_goals_for_query(latest_user_text)
    return fallback_goals, _build_router_dispatch_goal_queue(fallback_goals), latest_user_text


def _inject_compiled_data_handoff_for_supervisor(
    handoffs: Sequence[Dict[str, Any]],
    *,
    state: MultiAgentState,
    active_goals: Sequence[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    """当当前 pending goal 为 data.query 时，用 goal compiler 生成单真源 handoff。"""
    normalized_handoffs = [dict(item) for item in handoffs if isinstance(item, dict)]
    dispatch_queue = _build_router_dispatch_goal_queue(active_goals)
    if not dispatch_queue:
        return normalized_handoffs

    current_goal = dict(dispatch_queue[0])
    if _goal_kind_bucket(str(current_goal.get("kind") or "")) != "data":
        return normalized_handoffs

    compiled_handoff = _build_compiled_data_goal_handoff(state=state, goal=current_goal)
    if not compiled_handoff:
        return normalized_handoffs

    remaining = [
        dict(item)
        for item in normalized_handoffs
        if str(item.get("target_agent") or "").strip() != AgentType.DATA
    ]
    return [compiled_handoff, *remaining]


def _build_router_dispatch_goal_queue(
    goals_or_plan: Optional[Sequence[Dict[str, Any]] | Dict[str, Any]],
) -> list[Dict[str, Any]]:
    """按活动目标顺序构建 Router 待委派目标队列。"""
    if isinstance(goals_or_plan, dict):
        source_goals = [goal for goal in list(goals_or_plan.get("goals") or []) if isinstance(goal, dict)]
    else:
        source_goals = [goal for goal in list(goals_or_plan or []) if isinstance(goal, dict)]

    goals = sorted(
        source_goals,
        key=lambda item: int(item.get("order") or 0),
    )
    queue: list[Dict[str, Any]] = []
    for goal in goals:
        if not bool(goal.get("must_answer", True)):
            continue
        kind = str(goal.get("kind") or "general.reply")
        allowed_agents = _normalize_goal_allowed_agents(goal.get("allowed_agents"), kind)
        if not allowed_agents:
            continue
        queue.append(
            {
                "goal_id": str(goal.get("goal_id") or ""),
                "order": int(goal.get("order") or 0),
                "kind": kind,
                "title": str(goal.get("title") or kind or "未命名目标"),
                "allowed_agents": allowed_agents,
            }
        )
    return queue


def _build_router_blocked_entry(
    *,
    handoff: Dict[str, Any],
    reason: str,
    goal: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构造 Router 合同门禁阻塞条目。"""
    target_agent = str(handoff.get("target_agent") or "")
    blocked = {
        "reason": reason,
        "target_agent": target_agent or "unknown",
        "task_description": _resolve_handoff_display_text(handoff, limit=220),
    }
    if goal:
        blocked["goal_id"] = str(goal.get("goal_id") or "")
        blocked["goal_title"] = str(goal.get("title") or "")
        blocked["allowed_agents"] = list(goal.get("allowed_agents") or [])
    return blocked


def _is_sql_like_data_query_text(query_text: str) -> bool:
    """校验 data.query.query_text 是否被错误写成 SQL。"""
    normalized = str(query_text or "").strip()
    if not normalized:
        return False

    compact = re.sub(r"\s+", " ", normalized).strip().lower()
    if not compact.startswith(("select ", "with ")):
        return False

    try:
        import sqlglot

        sqlglot.parse_one(normalized, dialect="postgres")
        return True
    except Exception:
        return any(token in compact for token in (" from ", " group by ", " order by ", " limit "))


def _validate_data_query_handoff_contract(handoff: Dict[str, Any]) -> str:
    """校验 data.query handoff contract 是否具备最小可执行性。"""
    frame = handoff.get("frame")
    if not isinstance(frame, dict):
        return "frame_missing"

    query_text = _normalize_text_content(frame.get("query_text"))
    if not query_text:
        return "query_text_missing"
    if _is_sql_like_data_query_text(query_text):
        return "query_text_sql_like"

    query_shape = str(frame.get("query_shape") or "").strip().lower()
    if query_shape == "top_n":
        ranking = frame.get("ranking")
        if not isinstance(ranking, dict):
            return "ranking_missing"
        limit = _parse_non_negative_int(ranking.get("limit"), default=0)
        if limit <= 0:
            return "ranking_limit_missing"

    return ""


def _apply_router_contract_guard(
    handoffs: Sequence[Dict[str, Any]],
    *,
    state: MultiAgentState,
) -> Tuple[list[Dict[str, Any]], list[Dict[str, Any]], list[Dict[str, Any]]]:
    """按运行态单轨合同筛选 handoff，并返回阻塞原因。"""
    normalized_handoffs = [dict(item) for item in handoffs if isinstance(item, dict)]
    if not normalized_handoffs:
        return [], [], []

    if not _is_router_contract_guard_enabled():
        return normalized_handoffs, [], []

    legacy_fields = _detect_legacy_router_result_fields(state)
    if legacy_fields:
        blocked: list[Dict[str, Any]] = []
        for handoff in normalized_handoffs:
            entry = _build_router_blocked_entry(
                handoff=handoff,
                reason="legacy_field_detected",
            )
            entry["legacy_fields"] = list(legacy_fields)
            blocked.append(entry)
        pending = _build_router_dispatch_goal_queue(_resolve_active_goals(state))
        return [], blocked, pending

    active_goals, dispatch_queue, _latest_user_text = _resolve_dispatch_queue_with_query_fallback(state)

    normalized_handoffs = _inject_compiled_data_handoff_for_supervisor(
        normalized_handoffs,
        state=state,
        active_goals=active_goals,
    )

    if not dispatch_queue:
        blocked = [
            _build_router_blocked_entry(
                handoff=handoff,
                reason="no_pending_goal",
            )
            for handoff in normalized_handoffs
        ]
        return [], blocked, []

    accepted: list[Dict[str, Any]] = []
    blocked: list[Dict[str, Any]] = []
    pending_goals = [dict(goal) for goal in dispatch_queue]

    for handoff in normalized_handoffs:
        target_agent = str(handoff.get("target_agent") or "").strip()
        if not target_agent:
            blocked.append(
                _build_router_blocked_entry(
                    handoff=handoff,
                    reason="invalid_target_agent",
                )
            )
            continue

        if not pending_goals:
            blocked.append(
                _build_router_blocked_entry(
                    handoff=handoff,
                    reason="no_pending_goal",
                )
            )
            continue

        current_goal = pending_goals[0]
        goal_bucket = _goal_kind_bucket(str(current_goal.get("kind") or ""))
        if goal_bucket != "data":
            task_description = str(handoff.get("task_description") or "").strip()
            if not task_description:
                blocked.append(
                    _build_router_blocked_entry(
                        handoff=handoff,
                        reason="invalid_task_description",
                    )
                )
                continue
        allowed_agents = list(current_goal.get("allowed_agents") or [])
        if target_agent not in allowed_agents:
            blocked.append(
                _build_router_blocked_entry(
                    handoff=handoff,
                    reason="target_not_in_allowed_agents",
                    goal=current_goal,
                )
            )
            continue

        if goal_bucket == "data":
            contract_error = _validate_data_query_handoff_contract(handoff)
            if contract_error:
                blocked_entry = _build_router_blocked_entry(
                    handoff=handoff,
                    reason="invalid_data_query_contract",
                    goal=current_goal,
                )
                blocked_entry["contract_error"] = contract_error
                blocked.append(blocked_entry)
                continue

        enriched_handoff = dict(handoff)
        enriched_handoff["goal_id"] = str(current_goal.get("goal_id") or "")
        dispatch_reason = "compiled_data_goal_frame" if str(handoff.get("compiled_by") or "").strip() == "goal_contract" else "decomposed_goals_allowed_agents"
        route_decision = {
            "goal_id": str(current_goal.get("goal_id") or ""),
            "target_agent": target_agent,
            "dispatch_reason": dispatch_reason,
            "priority": int(current_goal.get("order") or 0),
            "blocked_by": [],
        }
        if goal_bucket == "data":
            frame = handoff.get("frame") if isinstance(handoff.get("frame"), dict) else {}
            query_text = _normalize_text_content(frame.get("query_text"))
            if query_text:
                from app.ai.router.data_intent_router import decide_data_intent
                from app.ai.router.data_intent_resolver import resolve_data_intent

                route_decision["data_intent"] = resolve_data_intent(
                    decide_data_intent(query_text, session_frame=frame),
                    user_text=query_text,
                )
        enriched_handoff["route_decision"] = route_decision
        accepted.append(enriched_handoff)
        pending_goals.pop(0)

    return accepted, blocked, pending_goals

def _should_mute_expert_text_output(state: Dict[str, Any], node_name: str) -> bool:
    """决定是否抑制专家节点文本直出（复合任务改为最终统一汇总）。"""
    if node_name == "data_expert":
        return True
    if node_name == "todo_expert" and bool(state.get("multi_intent_mode")):
        return True
    return False


def _extract_latest_visible_ai_markdown(messages: Sequence[BaseMessage]) -> str:
    """提取最近一条可展示的 AI Markdown 正文，保留换行与格式。"""
    from app.ai.protocol import AgentOutputParser

    for message in reversed(messages or []):
        if str(getattr(message, "type", "")).lower().strip() != "ai":
            continue
        content = _normalize_text_content(getattr(message, "content", ""))
        if not content:
            continue
        content = str(content).strip()
        if not content:
            continue
        if AgentOutputParser.should_filter_content(content):
            continue
        return content
    return ""


def _sanitize_direct_answer_markdown(markdown: Any, *, handoff_display_text: str = "") -> str:
    """清理直答 Markdown 中的调度/委派说明，仅保留用户可见正文。"""
    text = str(markdown or "").strip()
    if not text:
        return ""

    text = re.split(r"\n\s*---+\s*\n", text, maxsplit=1)[0].strip()
    handoff_hint = _normalize_tool_summary_text(re.sub(r"[*_`]", "", handoff_display_text), limit=240)
    blocked_markers = (
        "decompose_goals",
        "assign_to_",
        "接下来我将",
        "已为你发起",
        "将由系统继续处理",
        "系统继续处理",
        "后续执行",
    )

    kept_blocks: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        candidate = str(block or "").strip()
        if not candidate:
            continue
        normalized_candidate = _normalize_tool_summary_text(candidate, limit=400)
        compare_candidate = _normalize_tool_summary_text(re.sub(r"[*_`]", "", candidate), limit=400)
        lowered_candidate = normalized_candidate.lower()
        if handoff_hint and handoff_hint in compare_candidate:
            break
        if any(marker.lower() in lowered_candidate for marker in blocked_markers):
            break
        kept_blocks.append(candidate)

    cleaned = "\n\n".join(kept_blocks).strip()
    return cleaned or text


def _extract_latest_visible_ai_excerpt(messages: Sequence[BaseMessage], limit: int = 220) -> str:
    """提取最近一条可展示的 AI 输出摘要。"""
    return _normalize_tool_summary_text(_extract_latest_visible_ai_markdown(messages), limit=limit)


def _build_external_lookup_display_markdown_from_findings(findings: Sequence[Dict[str, Any]]) -> str:
    """根据外部查询 findings 构建用户可见富文本。"""
    rich_blocks: list[str] = []
    plain_summaries: list[str] = []
    for item in findings or []:
        if not isinstance(item, dict):
            continue
        display_markdown = str(item.get("display_markdown") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if display_markdown:
            rich_blocks.append(display_markdown)
            continue
        if summary:
            plain_summaries.append(summary)

    blocks: list[str] = []
    if rich_blocks:
        blocks.extend(rich_blocks)
    if plain_summaries:
        blocks.append("\n".join(f"- {summary}" for summary in plain_summaries) if len(plain_summaries) > 1 else plain_summaries[0])
    if blocks:
        return "\n\n".join(blocks)
    return ""


TAVILY_ERROR_HINTS = (
    "no search results found for",
    "suggestions: remove time_range argument",
    "try a more detailed search using 'advanced' search_depth",
)


def _is_tool_message_error(message: ToolMessage) -> bool:
    """判定 ToolMessage 是否为错误状态。"""
    status = str(getattr(message, "status", "") or "").strip().lower()
    return status in {"error", "failed", "failure"}


def _is_tavily_tool_error_output(tool_content: str, payload: Any = None) -> bool:
    """识别 Tavily 的无结果/报错输出，避免直接回显给用户。"""
    normalized = str(tool_content or "").strip().lower()
    if any(hint in normalized for hint in TAVILY_ERROR_HINTS):
        return True

    if isinstance(payload, dict):
        status = str(payload.get("status") or "").strip().lower()
        if status in {"error", "failed", "failure"}:
            return True
        if payload.get("error"):
            return True
        answer = str(payload.get("answer") or "").strip().lower()
        if answer.startswith("no search results found for"):
            return True

    return False


def _sanitize_tavily_text(tool_content: str) -> str:
    """对 Tavily 原始文本做通用标记清洗，避免网页属性碎片直出。"""
    text = html.unescape(str(tool_content or ""))
    if not text.strip():
        return ""
    text = re.sub(r'\b(?:alt|style|class|id|src|href)\s*=\s*"[^"]*"', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:alt|style|class|id|src|href)\s*=\s*'[^']*'", ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(?:alt|style|class|id|src|href)\s*=\s*\S+', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'(?:首页|国内天气|空气质量|全国天气网)', ' ', text)
    text = text.replace('#', ' ').replace('【', ' ').replace('】', ' ')
    text = text.replace('>', ' ').replace('"', ' ').replace('_', ' ')
    text = re.sub(r'\s+', ' ', text).strip(' ：:；;,，')
    return _normalize_tool_summary_text(text, limit=220)


def _normalize_weather_label(raw_label: str) -> str:
    """标准化天气标签。"""
    label = str(raw_label or "").strip().replace('（', '(').replace('）', ')')
    if not label:
        return ""

    alias_match = re.search(r'(今天|明天|后天|周[一二三四五六日天])', label)
    if alias_match:
        alias = alias_match.group(1)
        date_match = re.search(r'(\d{2}-\d{2})', label)
        if date_match:
            return f"{alias}（{date_match.group(1)}）"
        return alias

    return label


def _localize_weather_english_text(text: str) -> str:
    """将英文天气摘要收敛为更适合中文用户阅读的短句。"""
    localized = str(text or "").strip()
    if not localized:
        return ""

    replacements = (
        (r"\bMostly dry\b", "大部时段无明显降水"),
        (r"\bSome drizzle\b", "有零星小雨"),
        (r"\bLight rain\b", "小雨"),
        (r"\bModerate rain\b", "中雨"),
        (r"\bHeavy rain\b", "大雨"),
        (r"\bVery mild\b", "体感温和"),
        (r"\bWind will be generally light\b", "风力较小"),
        (r"\bWind will be light\b", "风力较小"),
        (r"\bPartly cloudy\b", "局部多云"),
        (r"\bMostly cloudy\b", "大部多云"),
        (r"\bCloudy\b", "多云"),
        (r"\bSunny\b", "晴朗"),
    )
    for pattern, replacement in replacements:
        localized = re.sub(pattern, replacement, localized, flags=re.IGNORECASE)

    localized = re.sub(r"\btotal\s*(\d+(?:\.\d+)?)mm\b", r"累计约\1mm", localized, flags=re.IGNORECASE)
    localized = re.sub(r"\bheaviest during [A-Za-z]{3} night\b", "夜间更明显", localized, flags=re.IGNORECASE)
    localized = re.sub(r"\bmostly falling on [A-Za-z]{3} morning\b", "主要出现在上午", localized, flags=re.IGNORECASE)
    localized = re.sub(r"\bmostly falling on [A-Za-z]{3} night\b", "主要出现在夜间", localized, flags=re.IGNORECASE)
    localized = localized.replace('|', ' ')
    localized = localized.replace(". ", "；").replace(".", "")
    localized = re.sub(r"\s+", " ", localized).strip(" ：:；;,，")
    return localized


def _score_weather_display_markdown(markdown: str) -> int:
    """给天气展示文案打分，优先更像人话、信息更完整的候选。"""
    text = str(markdown or '').strip()
    if not text:
        return -10_000

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    english_words = len(re.findall(r"\b[a-zA-Z]{3,}\b", text))
    temp_hits = len(re.findall(r"\d+\s*[°℃]", text))
    line_hits = sum(1 for line in text.splitlines() if line.strip().startswith('- '))
    score = chinese_chars + temp_hits * 30 + line_hits * 8
    score -= english_words * 6
    score -= text.count('|') * 20
    if '摘要：' in text:
        score -= 120

    noise_hints = (
        '公司地址', '联系电话', '首页', '下载', '资讯', '15天预报', '风景名胜区', '正月', '联系电话', '融新科技中心', '当前时间', '预警信号', '排行榜', '全国天气网'
    )
    for hint in noise_hints:
        if hint in text:
            score -= 80

    return score


def _extract_weather_segments_from_text(text: str) -> list[dict[str, str]]:
    """从天气网页正文中提取日期段。"""
    normalized = html.unescape(str(text or ""))
    if not normalized.strip():
        return []

    normalized = re.sub(r'<[^>]+>', ' ', normalized)
    normalized = normalized.replace('（', '(').replace('）', ')')
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    if not normalized:
        return []

    label_pattern = re.compile(
        r'(?:\d{1,2}日\((?:今天|明天|后天|周[一二三四五六日天])\)|(?:今天|明天|后天|周[一二三四五六日天])(?:\s*\(\d{2}-\d{2}\))?(?=(?:\s|$)))'
    )
    matches = list(label_pattern.finditer(normalized))

    weather_pattern = re.compile(
        r'(晴转多云|晴转小雨|晴转阴|多云转晴|多云转阴|多云转小雨|小雨转多云|小雨转阴|阴转多云|阴转小雨|雷阵雨|阵雨|小雨|中雨|大雨|暴雨|雨夹雪|小雪|中雪|大雪|多云|晴|阴)'
    )
    temp_pattern = re.compile(r'(-?\d+\s*[°℃]\s*/\s*-?\d+\s*[°℃]|-?\d+~?-?\d*\s*[°℃])')

    segments: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        raw_label = match.group(0)
        start_idx = match.end()
        end_idx = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        segment_text = normalized[start_idx:end_idx].strip(' ：:；;,，')
        if not segment_text:
            continue

        weather_match = weather_pattern.search(segment_text)
        temp_match = temp_pattern.search(segment_text)
        weather = weather_match.group(1).strip() if weather_match else ""
        temperature = temp_match.group(1).replace(' ', '') if temp_match else ""

        extra_text = segment_text
        if weather_match:
            extra_text = extra_text.replace(weather_match.group(0), ' ', 1)
        if temp_match:
            extra_text = extra_text.replace(temp_match.group(0), ' ', 1)
        extra_text = re.sub(r'\b\d+\s*[优良轻中重]\b', ' ', extra_text)
        extra_text = re.sub(r'今日天气提示[^今天明天后天周一二三四五六日天]*', ' ', extra_text)
        extra_text = re.sub(r'\s+', ' ', extra_text).strip(' ：:；;,，')

        if not any((weather, temperature, extra_text)):
            continue
        segments.append(
            {
                'label': _normalize_weather_label(raw_label),
                'weather': weather,
                'temperature': temperature,
                'extra': extra_text,
            }
        )

    if segments:
        return segments[:5]

    chinese_labels = ('今天', '明天', '后天', '周一', '周二', '周三', '周四', '周五', '周六', '周日', '周天')
    weather_by_label: dict[str, str] = {}
    high_by_label: dict[str, tuple[str, str]] = {}
    low_by_label: dict[str, str] = {}

    chinese_weather_pattern = re.compile(
        r'(今天|明天|后天|周[一二三四五六日天])[^。；]*?'
        r'(晴转多云|晴转小雨|晴转阴|多云转晴|多云转阴|多云转小雨|小雨转多云|小雨转阴|阴转多云|阴转小雨|雷阵雨|阵雨|小雨|中雨|大雨|暴雨|雨夹雪|小雪|中雪|大雪|晴到多云|多云到晴|多云|晴|阴)'
    )
    for label, weather in chinese_weather_pattern.findall(normalized):
        weather_by_label.setdefault(label, weather)

    high_temp_pattern = re.compile(r'(今天|明天|后天|周[一二三四五六日天])(?:白天)?最高温度\s*(\d+)\s*[～~\-]\s*(\d+)\s*[°℃]')
    for label, low, high in high_temp_pattern.findall(normalized):
        high_by_label[label] = (low, high)

    low_temp_pattern = re.compile(r'(今天|明天|后天|周[一二三四五六日天])(?:早晨)?最低温度\s*(\d+)\s*[°℃]')
    for label, low in low_temp_pattern.findall(normalized):
        low_by_label[label] = low

    for label in chinese_labels:
        weather = weather_by_label.get(label, '')
        temperature = ''
        high_range = high_by_label.get(label)
        low_temp = low_by_label.get(label)
        if high_range and low_temp:
            temperature = f'{low_temp}℃~{high_range[1]}℃'
        elif high_range:
            temperature = f'{high_range[0]}℃~{high_range[1]}℃'
        elif low_temp:
            temperature = f'{low_temp}℃'
        if any((weather, temperature)):
            segments.append({'label': label, 'weather': weather, 'temperature': temperature, 'extra': ''})

    if segments:
        return segments[:5]

    table_pattern = re.compile(
        r'\|\s*(\d{4}年\d{2}月\d{2}日\(星期[一二三四五六日天]\))\s*\|\s*\|?\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|'
    )
    for match in table_pattern.finditer(normalized):
        weather = str(match.group(2) or '').strip(' ：:；;,，')
        temperature = re.sub(r'\s+', '', str(match.group(3) or ''))
        extra_text = re.sub(r'\s+', ' ', str(match.group(4) or '')).strip(' ：:；;,，')
        if not any((weather, temperature, extra_text)):
            continue
        segments.append(
            {
                'label': str(match.group(1) or '').strip(),
                'weather': weather,
                'temperature': temperature,
                'extra': extra_text,
            }
        )

    if segments:
        return segments[:5]

    forecast_pattern = re.compile(
        r'(?:\d+\s*日\s*)?([一-鿿]{2,6})\s*(今日天气|天气|下周天气预报)\s*\((\d+\s*[–-]\s*\d+\s*天数)\)\s*:?',
        re.IGNORECASE,
    )
    matches = list(forecast_pattern.finditer(normalized))
    for index, match in enumerate(matches):
        descriptor = str(match.group(2) or '').strip()
        period = re.sub(r'\s+', '', str(match.group(3) or '')).replace('–', '-').replace('天数', '天')
        start_idx = match.end()
        end_idx = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        segment_text = normalized[start_idx:end_idx].strip(' ：:；;,，')
        if not segment_text:
            continue

        if descriptor == '今日天气':
            label = f'今日（{period}）'
        elif descriptor == '下周天气预报':
            label = f'下周（{period}）'
        else:
            label = period or descriptor

        temp_match = re.search(r'max\s*(-?\d+)\s*°\s*c.*?min\s*(-?\d+)\s*°\s*c', segment_text, re.IGNORECASE)
        temperature = ''
        if temp_match:
            max_temp, min_temp = temp_match.groups()
            temperature = f'{min_temp}°C~{max_temp}°C'

        sentences = [part.strip(' .') for part in re.split(r'(?<=[.。])\s+', segment_text) if part.strip(' .')]
        cleaned_sentences: list[str] = []
        for sentence in sentences:
            cleaned_sentence = re.sub(r'\(max[^)]*min[^)]*\)', '', sentence, flags=re.IGNORECASE)
            cleaned_sentence = re.sub(r'\s+', ' ', cleaned_sentence).strip(' .')
            if cleaned_sentence:
                cleaned_sentences.append(cleaned_sentence)

        weather = _localize_weather_english_text(cleaned_sentences[0]) if cleaned_sentences else ''
        extra = '；'.join(_localize_weather_english_text(sentence) for sentence in cleaned_sentences[1:3] if sentence)
        if not any((weather, temperature, extra)):
            continue
        segments.append(
            {
                'label': label,
                'weather': weather,
                'temperature': temperature,
                'extra': extra,
            }
        )

    return segments[:5]


def _score_tavily_weather_result(item: Dict[str, Any]) -> int:
    """为天气类结果做轻量排序，优先真实天气页，降权新闻/门户噪声。"""
    if not isinstance(item, dict):
        return 0

    title = str(item.get('title') or '').lower()
    url = str(item.get('url') or '').lower()
    content = str(item.get('content') or item.get('snippet') or '').lower()
    merged = ' '.join(part for part in (title, url, content) if part)
    score = 0

    weather_hints = (
        '天气', 'weather', 'forecast', '气温', '实时天气', '天气预报', '墨迹天气', 'weather.com', 'weatherspark', 'weather-forecast', '1543天气网'
    )
    noise_hints = (
        '网易', 'entertainment', '娱乐', '财经', '汽车', '科技', '时尚', '特别声明', '自媒体平台', '卫视', '日报', 'article', 'dy/article'
    )
    for hint in weather_hints:
        if hint.lower() in merged:
            score += 2
    for hint in noise_hints:
        if hint.lower() in merged:
            score -= 3

    return score


def _extract_weather_city_name(title: str, content: str) -> str:
    """从标题/正文提取城市名，避免把“72小时实时”等修饰词带进标题。"""
    source_texts = [str(title or ''), str(content or '')]
    patterns = (
        r'([一-鿿]{2,6})市?未来\d+天(?:天气预报|天气)',
        r'([一-鿿]{2,6})市?明[日天]天气',
        r'([一-鿿]{2,6})市?后天(?:天气|的天气情况)',
        r'([一-鿿]{2,6})市?72小时实时天气',
        r'([一-鿿]{2,6})市?天气',
    )
    for source in source_texts:
        for pattern in patterns:
            match = re.search(pattern, source)
            if match:
                return match.group(1)
    return '天气'


def _extract_tavily_display_markdown(tool_content: str) -> str:
    """从 Tavily 结果中提取用户可见富文本，优先识别天气网页。"""
    stripped = str(tool_content or "").strip()
    if not stripped:
        return ""

    payload: Any = None
    if (stripped.startswith('{') and stripped.endswith('}')) or (
        stripped.startswith('[') and stripped.endswith(']')
    ):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None

    if _is_tavily_tool_error_output(stripped, payload=payload):
        return ""

    if isinstance(payload, dict):
        answer = str(payload.get('answer') or '').strip()
        if answer:
            return answer
        results = payload.get('results')
    elif isinstance(payload, list):
        results = payload
    else:
        return ""

    if not isinstance(results, list):
        return ""

    ranked_results = sorted(
        [item for item in results if isinstance(item, dict)],
        key=_score_tavily_weather_result,
        reverse=True,
    )

    weather_candidates: list[str] = []
    fallback_blocks: list[str] = []
    for item in ranked_results[:3]:
        if not isinstance(item, dict):
            continue
        title = str(item.get('title') or '').strip()
        content = str(item.get('content') or item.get('snippet') or '').strip()
        if not content:
            continue

        segments = _extract_weather_segments_from_text(content)
        if segments:
            city = _extract_weather_city_name(title, content)
            lines = [f"{city}天气："]
            for segment in segments[:4]:
                detail_parts = [part for part in (segment.get('weather'), segment.get('temperature'), segment.get('extra')) if part]
                if not detail_parts:
                    continue
                lines.append(f"- {segment.get('label') or '近期'}：{'，'.join(detail_parts)}")
            if len(lines) > 1:
                weather_candidates.append("\n".join(lines))
                continue

        cleaned_content = _sanitize_tavily_text(content)
        cleaned_title = _sanitize_tavily_text(title)
        weather_like_result = _score_tavily_weather_result(item) > 0
        if weather_like_result:
            city = _extract_weather_city_name(title, content)
            summary_text = _localize_weather_english_text(cleaned_content or cleaned_title)
            if summary_text:
                weather_candidates.append(f"{city}天气：\n- 摘要：{summary_text}")
                continue

        if cleaned_content and cleaned_title:
            fallback_blocks.append(f"{cleaned_title}\n\n{cleaned_content}")
            continue
        if cleaned_content:
            fallback_blocks.append(cleaned_content)
            continue
        if cleaned_title:
            fallback_blocks.append(cleaned_title)

    if weather_candidates:
        return max(weather_candidates, key=_score_weather_display_markdown)

    return fallback_blocks[0] if fallback_blocks else ""


def _summarize_tavily_tool_output(tool_content: str) -> str:
    """从 Tavily 工具输出中提取可用于待办补充的摘要。"""
    rich_text = _extract_tavily_display_markdown(tool_content)
    if rich_text:
        return _normalize_tool_summary_text(rich_text, limit=240)

    stripped = str(tool_content or "").strip()
    if not stripped:
        return ""

    payload: Any = None
    if (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    ):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None

    if _is_tavily_tool_error_output(stripped, payload=payload):
        return ""

    if isinstance(payload, dict):
        answer = _normalize_tool_summary_text(payload.get("answer"), limit=220)
        if answer:
            return answer
        results = payload.get("results")
    elif isinstance(payload, list):
        results = payload
    else:
        return _sanitize_tavily_text(stripped)

    if not isinstance(results, list):
        return _sanitize_tavily_text(stripped)

    ranked_results = sorted(
        [item for item in results if isinstance(item, dict)],
        key=_score_tavily_weather_result,
        reverse=True,
    )
    lines = []
    for item in ranked_results[:2]:
        snippet = _sanitize_tavily_text(item.get("content") or item.get("snippet"))
        title = _sanitize_tavily_text(item.get("title"))
        if snippet:
            lines.append(snippet)
        elif title:
            lines.append(title)

    merged = "；".join(lines)
    if merged:
        return _normalize_tool_summary_text(merged, limit=240)
    return _sanitize_tavily_text(stripped)

def _build_direct_lookup_findings(messages: Sequence[BaseMessage]) -> list[Dict[str, Any]]:
    """提取 Supervisor 直接工具（天气/知识库）结果，供最终汇总使用。"""
    findings: list[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()

    for message in messages or []:
        if not isinstance(message, ToolMessage):
            continue

        tool_name = str(getattr(message, "name", "") or "")
        if _is_tool_message_error(message):
            continue

        lowered_name = tool_name.lower()
        content = str(getattr(message, "content", "") or "")
        if not content:
            continue

        display_markdown = ""
        kind = "external.lookup"
        if "tavily" in lowered_name:
            display_markdown = _extract_tavily_display_markdown(content)
            summary = _normalize_tool_summary_text(display_markdown, limit=220) if display_markdown else _summarize_tavily_tool_output(content)
            label = "天气/实时信息"
            kind = "external.lookup"
        elif "knowledge_search" in lowered_name:
            summary = _normalize_tool_summary_text(content, limit=220)
            label = "知识库检索"
            kind = "knowledge.lookup"
        else:
            continue

        if not summary:
            continue

        key = (label, summary)
        if key in seen:
            continue
        seen.add(key)
        finding: Dict[str, Any] = {"label": label, "summary": summary, "kind": kind, "tool_name": tool_name}
        if display_markdown:
            finding["display_markdown"] = display_markdown
        findings.append(finding)

    return findings[:3]


def _build_multi_intent_summary_content(state: MultiAgentState) -> str:
    """构造复合任务统一交付文本（用户可读、无内部术语）。"""
    active_goals = _ensure_active_goals_covers_runtime(state)
    deliverables = _build_delivery_artifacts(state)
    coverage_report = _compute_coverage_report(active_goals, deliverables)
    return _render_final_answer(active_goals, coverage_report)


def _evaluate_handoff_progress(state: MultiAgentState) -> Dict[str, Any]:
    """评估复合任务进度，返回带 evaluation_route 的状态更新。"""
    messages = state.get("messages", [])
    turn_messages = _slice_messages_from_latest_human(messages)
    iteration_count = state.get("iteration_count") or 0
    pending_handoff = state.get("pending_handoff")
    handoff_queue = list(state.get("handoff_queue") or [])
    completed_handoffs = list(state.get("completed_handoffs") or [])
    execution_trace = list(state.get("handoff_execution_trace") or [])

    max_iterations = 6
    if iteration_count >= max_iterations:
        logger.warning("评估节点: 达到最大迭代次数 (%d)，结束任务", max_iterations)
        return {
            "evaluation": "complete",
            "evaluation_route": "postprocess",
            "pending_handoff": None,
            "handoff_queue": handoff_queue,
            "completed_handoffs": completed_handoffs,
            "handoff_execution_trace": execution_trace,
        }

    if pending_handoff:
        latest_completed = completed_handoffs[-1] if completed_handoffs else None
        if latest_completed != pending_handoff:
            completed_handoffs.append(dict(pending_handoff))
            execution_trace.append(
                {
                    "target_agent": pending_handoff.get("target_agent"),
                    "goal_id": pending_handoff.get("goal_id"),
                    "task_description": _resolve_handoff_display_text(pending_handoff, limit=220),
                    "result_excerpt": _extract_latest_visible_ai_excerpt(turn_messages),
                    "direct_answer_markdown": _sanitize_direct_answer_markdown(
                        pending_handoff.get("direct_answer_markdown"),
                        handoff_display_text=_resolve_handoff_display_text(pending_handoff, limit=220),
                    ),
                }
            )

    if handoff_queue:
        next_handoff = handoff_queue.pop(0)
        next_agent = str(next_handoff.get("target_agent") or "")
        route = WORKFLOW_AGENT_NODE_BY_TYPE.get(next_agent, "supervisor")
        return {
            "evaluation": "continue",
            "evaluation_route": route,
            "iteration_count": iteration_count + 1,
            "pending_handoff": next_handoff,
            "handoff_queue": handoff_queue,
            "completed_handoffs": completed_handoffs,
            "handoff_execution_trace": execution_trace,
        }

    if bool(state.get("multi_intent_mode")):
        runtime_state = dict(state)
        runtime_state["pending_handoff"] = pending_handoff
        runtime_state["handoff_queue"] = handoff_queue
        runtime_state["completed_handoffs"] = completed_handoffs
        runtime_state["handoff_execution_trace"] = execution_trace

        active_goals = _ensure_active_goals_covers_runtime(runtime_state)
        active_goal_plan = _build_active_goal_plan(
            runtime_state,
            runtime_goals=active_goals,
            source="evaluate_runtime",
        )
        deliverables = _build_delivery_artifacts(runtime_state)
        coverage_preview = _compute_coverage_report(active_goals, deliverables)
        missing_goals = list(coverage_preview.get("missing_goals") or [])
        missing_goal_ids = [str(item.get("goal_id") or "") for item in missing_goals]
        missing_goal_titles = [str(item.get("title") or item.get("goal_id") or "未命名目标") for item in missing_goals]

        delivery_meta = {
            **dict(state.get("delivery_meta") or {}),
            "pending_goal_ids": missing_goal_ids,
            "pending_goal_titles": missing_goal_titles,
        }

        if _is_delivery_orchestrator_v2_enabled():
            return {
                "evaluation": "coverage",
                "evaluation_route": "coverage_gate",
                "pending_handoff": None,
                "handoff_queue": [],
                "completed_handoffs": completed_handoffs,
                "handoff_execution_trace": execution_trace,
                "decomposed_goals": list(active_goals),
                "deliverables": deliverables,
                "coverage_report": coverage_preview,
                "delivery_meta": delivery_meta,
            }

        if not missing_goals:
            return {
                "evaluation": "summarize",
                "evaluation_route": "summarize",
                "pending_handoff": None,
                "handoff_queue": [],
                "completed_handoffs": completed_handoffs,
                "handoff_execution_trace": execution_trace,
                "decomposed_goals": list(active_goals),
                "deliverables": deliverables,
                "coverage_report": coverage_preview,
            }

        logger.info(
            "评估节点: 复合任务仍有未完成目标，missing=%s，iteration=%d",
            missing_goal_ids,
            iteration_count,
        )

        if iteration_count + 1 >= max_iterations:
            logger.warning(
                "评估节点: 复合任务到达迭代上限，带缺口输出（missing=%s）",
                missing_goal_ids,
            )
            final_route = "coverage_gate" if _is_delivery_orchestrator_v2_enabled() else "summarize"
            final_evaluation = "coverage" if final_route == "coverage_gate" else "summarize"
            return {
                "evaluation": final_evaluation,
                "evaluation_route": final_route,
                "pending_handoff": None,
                "handoff_queue": [],
                "completed_handoffs": completed_handoffs,
                "handoff_execution_trace": execution_trace,
                "decomposed_goals": list(active_goals),
                "deliverables": deliverables,
                "coverage_report": coverage_preview,
                "delivery_meta": delivery_meta,
            }

        return {
            "evaluation": "continue",
            "evaluation_route": "supervisor",
            "iteration_count": iteration_count + 1,
            "pending_handoff": None,
            "handoff_queue": [],
            "completed_handoffs": completed_handoffs,
            "handoff_execution_trace": execution_trace,
            "decomposed_goals": list(active_goals),
            "deliverables": deliverables,
            "coverage_report": coverage_preview,
            "delivery_meta": delivery_meta,
            "system_context": response_policy_service.build_multi_intent_recovery_system_context(
                str(state.get("system_context") or ""),
                active_goal_plan,
                missing_goals,
            ),
        }

    if not messages:
        return {
            "evaluation": "complete",
            "evaluation_route": "postprocess",
            "pending_handoff": None,
            "handoff_queue": handoff_queue,
            "completed_handoffs": completed_handoffs,
            "handoff_execution_trace": execution_trace,
        }

    last_msg = messages[-1]
    has_tool_calls = hasattr(last_msg, "tool_calls") and last_msg.tool_calls
    if last_msg.type == "ai" and not has_tool_calls:
        return {
            "evaluation": "complete",
            "evaluation_route": "postprocess",
            "pending_handoff": None,
            "handoff_queue": handoff_queue,
            "completed_handoffs": completed_handoffs,
            "handoff_execution_trace": execution_trace,
        }

    return {
        "evaluation": "continue",
        "evaluation_route": "supervisor",
        "iteration_count": iteration_count + 1,
        "pending_handoff": pending_handoff,
        "handoff_queue": handoff_queue,
        "completed_handoffs": completed_handoffs,
        "handoff_execution_trace": execution_trace,
    }


def _is_partial_gap_delivery_allowed(
    *,
    active_goals: Optional[Sequence[Dict[str, Any]]] = None,
    coverage_report: Dict[str, Any],
) -> bool:
    """判定是否允许“主问题完成 + 子任务缺口”直接收口输出。"""
    normalized_active_goals = _coerce_active_goals_input(active_goals or [])
    if not normalized_active_goals:
        return False

    missing_goals = list(coverage_report.get("missing_goals") or [])
    if not missing_goals:
        return False

    goal_index: Dict[str, Dict[str, Any]] = {
        str(goal.get("goal_id") or ""): goal
        for goal in normalized_active_goals
        if str(goal.get("goal_id") or "")
    }
    if not goal_index:
        return False

    for item in missing_goals:
        goal_id = str(item.get("goal_id") or "")
        if not goal_id:
            return False
        goal = goal_index.get(goal_id)
        if not isinstance(goal, dict):
            return False

        goal_kind = str(goal.get("kind") or "general.reply")
        allowed_agents = _normalize_goal_allowed_agents(goal.get("allowed_agents"), goal_kind)
        if not allowed_agents:
            return False

    return True


def _resolve_coverage_gate_route(
    *,
    state: MultiAgentState,
    coverage_report: Dict[str, Any],
    active_goals: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """决定 coverage_gate 下一跳与补齐轮次。"""
    previous_retry = _parse_non_negative_int(state.get("coverage_retry_count"), default=0)
    pass_flag = bool(coverage_report.get("pass"))
    if pass_flag or not _is_coverage_gate_enforced():
        return {
            "route": "final_composer",
            "coverage_retry_count": 0,
            "retry_exhausted": False,
            "partial_gap_allowed": False,
        }

    if _is_partial_gap_delivery_allowed(
        active_goals=active_goals,
        coverage_report=coverage_report,
    ):
        return {
            "route": "final_composer",
            "coverage_retry_count": previous_retry,
            "retry_exhausted": False,
            "partial_gap_allowed": True,
        }

    coverage_retry_count = previous_retry + 1
    max_retries = _resolve_coverage_gate_max_retries()
    retry_exhausted = coverage_retry_count > max_retries
    return {
        "route": "postprocess" if retry_exhausted else "supervisor",
        "coverage_retry_count": coverage_retry_count,
        "retry_exhausted": retry_exhausted,
        "max_retries": max_retries,
        "partial_gap_allowed": False,
    }


def _emit_kb_images_from_delta_messages(
    delta_messages: Sequence[BaseMessage],
    ctx: StreamingContext,
) -> None:
    """从增量 ToolMessage 中提取 KB_IMAGES 并发送事件。"""

    for tool_msg in reversed(delta_messages):
        if not isinstance(tool_msg, ToolMessage):
            continue
        tool_content = str(getattr(tool_msg, "content", ""))
        if not tool_content:
            continue
        new_images = AgentOutputParser.parse_kb_images(tool_content)
        if new_images:
            ctx.kb_images.update(new_images)
            logger.info("[%s] 从 values 模式提取 kb_images: %s 个", ctx.node_name, len(new_images))
            kb_images_payload = build_streaming_kb_images_payload(ctx.kb_images)
            emit_kb_images(ctx.writer, kb_images_payload["images"], node=ctx.node_name)


def _emit_tool_start_events_from_ai_message(
    ai_message: Any,
    ctx: StreamingContext,
) -> bool:
    """从 AIMessage 的 tool_calls 发送 tool_start 事件。"""
    if not (hasattr(ai_message, "tool_calls") and ai_message.tool_calls):
        return False

    for tool_call in ai_message.tool_calls:
        tool_call_id = tool_call.get("id")
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        tool_start_payload = build_streaming_tool_start_payload(tool_name, tool_args)
        if tool_call_id and tool_call_id not in ctx.sent_tool_call_ids and tool_start_payload:
            ctx.sent_tool_call_ids.add(tool_call_id)
            logger.debug("发送 tool_start 事件: %s", tool_name)
            if tool_name and "tavily" in (tool_name or "").lower():
                logger.info("联网搜索被调用: tool=%s, args=%s", tool_name, tool_args)
            emit_tool_start(ctx.writer, tool_start_payload["name"], tool_start_payload["input"], node=ctx.node_name)

    return True


def _should_skip_values_text_message(
    msg_content: Any,
    msg_id: Any,
    ctx: StreamingContext,
) -> bool:
    """values 模式文本补发去重判断。"""
    if AgentOutputParser.should_filter_content(msg_content):
        return True

    if msg_id and msg_id in ctx.emitted_message_ids:
        return True

    full_collected = "".join(ctx.collected_content)
    if msg_content and msg_content in full_collected:
        if len(msg_content) > 10:
            return True
        return True

    return False


def _emit_values_text_message(
    ai_message: Any,
    msg_content: str,
    ctx: StreamingContext,
) -> None:
    """values 模式补发文本消息（兼容 result 结构化载荷）。"""
    result_payload = build_streaming_result_payload(ai_message, msg_content)
    if result_payload:
        emit_result(ctx.writer, data_type=result_payload["data_type"], data=result_payload["data"], message=result_payload["message"], node=ctx.node_name)
        return

    emit_token(ctx.writer, msg_content, node=ctx.node_name)


def _record_emitted_message_id(message: Any, emitted_message_ids: set) -> None:
    """记录消息 ID（若存在）用于去重。"""
    message_id = getattr(message, "id", None)
    if message_id:
        emitted_message_ids.add(message_id)


async def _prefill_emitted_message_ids(
    agent: Any,
    config: Any,
    state_messages: Sequence[BaseMessage],
    emitted_message_ids: set,
    node_name: str,
) -> None:
    """预填充已发消息 ID，覆盖主图 state 与子图 checkpoint。"""
    for existing_msg in state_messages:
        _record_emitted_message_id(existing_msg, emitted_message_ids)

    try:
        subgraph_state = await agent.aget_state(config)
        if subgraph_state and hasattr(subgraph_state, "values"):
            subgraph_messages = subgraph_state.values.get("messages", [])
            for subgraph_msg in subgraph_messages:
                _record_emitted_message_id(subgraph_msg, emitted_message_ids)
            if subgraph_messages:
                logger.debug("[%s] 从子图 checkpoint 预填充 %s 条消息 ID", node_name, len(subgraph_messages))
    except Exception as exc:
        logger.debug("[%s] 无法获取子图状态（可能是首次调用）: %s", node_name, exc)


def _handle_messages_mode_tool_message(
    message: Any,
    ctx: StreamingContext,
) -> bool:
    """处理 messages 模式下的 ToolMessage（tool_end + KB_IMAGES）。"""
    if not isinstance(message, ToolMessage):
        return False

    tool_name = getattr(message, "name", "unknown")
    tool_content = str(getattr(message, "content", ""))
    tool_output = tool_content[:200]
    emit_tool_end(ctx.writer, tool_name, tool_output, node=ctx.node_name)

    if tool_name == "load_skills":
        load_status_message = _build_load_skills_status_message(
            message,
            fallback_visible_skill_count=ctx.state.get("visible_skill_count"),
        )
        if load_status_message:
            emit_status(ctx.writer, message=load_status_message, node=ctx.node_name)

    if tool_name and "tavily" in (tool_name or "").lower():
        logger.info("联网搜索返回: tool=%s, 结果长度=%s", tool_name, len(tool_content))

    new_images = AgentOutputParser.parse_kb_images(tool_content)
    if new_images:
        ctx.kb_images.update(new_images)
        logger.info("[%s] 从 ToolMessage 提取到 kb_images: %s 个", ctx.node_name, len(new_images))

    return True


def _build_load_skills_status_message(
    message: ToolMessage,
    fallback_visible_skill_count: Any = 0,
) -> Optional[str]:
    """将 load_skills 结果压缩为单行运行态提示。"""

    additional_kwargs = getattr(message, "additional_kwargs", None)
    runtime_payload = additional_kwargs.get("skill_runtime") if isinstance(additional_kwargs, dict) else None
    loaded_skills_payload = []
    visible_skill_count: Optional[int] = None

    if isinstance(runtime_payload, dict):
        raw_visible_skill_count = runtime_payload.get("visible_skill_count")
        try:
            visible_skill_count = max(int(raw_visible_skill_count or 0), 0)
        except (TypeError, ValueError):
            visible_skill_count = 0
        if isinstance(runtime_payload.get("loaded_skills"), list):
            loaded_skills_payload = runtime_payload.get("loaded_skills") or []

    if visible_skill_count is None:
        try:
            visible_skill_count = max(int(fallback_visible_skill_count or 0), 0)
        except (TypeError, ValueError):
            visible_skill_count = 0

    loaded_skill_ids: List[str] = []
    for item in loaded_skills_payload:
        if not isinstance(item, dict):
            continue
        skill_id = str(item.get("skill_id") or "").strip()
        if not skill_id or skill_id in loaded_skill_ids:
            continue
        loaded_skill_ids.append(skill_id)

    if not loaded_skill_ids:
        return f"已预装 {visible_skill_count} 个可见技能目录，尚未加载具体技能。"

    preview = "、".join(loaded_skill_ids[:3])
    if len(loaded_skill_ids) > 3:
        preview = f"{preview} 等 {len(loaded_skill_ids)} 个"
    return f"已预装 {visible_skill_count} 个可见技能目录，已加载技能：{preview}。"


def _emit_messages_mode_token(
    message: Any,
    ctx: StreamingContext,
) -> None:
    """messages 模式发送文本 token（过滤内部协议内容）。"""
    content = getattr(message, "content", "")
    if not (content and isinstance(content, str)):
        return

    if AgentOutputParser.should_filter_content(content):
        logger.debug("[%s] 跳过内部协议内容", ctx.node_name)
        return

    ctx.collected_content.append(content)
    emit_token(ctx.writer, content, node=ctx.node_name)


def _emit_messages_mode_thinking(
    message: Any,
    ctx: StreamingContext,
) -> None:
    """messages 模式发送思考内容（reasoning/thinking）。"""
    additional = getattr(message, "additional_kwargs", {})
    reasoning = (
        additional.get("reasoning_content") or
        additional.get("thinking_content") or
        additional.get("thinking")
    )
    if reasoning:
        emit_thinking(ctx.writer, reasoning, node=ctx.node_name)


def _build_expert_inference_messages(
    state: Dict[str, Any],
    node_name: str,
) -> list[BaseMessage]:
    """为专家节点裁剪输入消息，避免子任务继续消费整句复合问题。"""
    original_messages = state.get("messages", [])
    if node_name != "data_expert":
        return list(original_messages or [])

    pending_handoff = state.get("pending_handoff")
    if not isinstance(pending_handoff, dict):
        return list(original_messages or [])
    if str(pending_handoff.get("target_agent") or "").strip() != AgentType.DATA:
        return list(original_messages or [])

    handoff_frame = pending_handoff.get("frame")
    if not isinstance(handoff_frame, dict):
        return list(original_messages or [])

    query_text = _normalize_text_content(handoff_frame.get("query_text"))
    if not query_text:
        return list(original_messages or [])

    expert_input_contract = build_expert_input_contract_payload(
        contract_id="data_handoff_query_text",
        target_agent=AgentType.DATA,
        state_owner="supervisor",
        source_fields=["pending_handoff.frame.query_text"],
    )
    return [
        HumanMessage(
            content=query_text,
            name="__internal_data_handoff__",
            additional_kwargs={"expert_input_contract": expert_input_contract} if expert_input_contract else None,
        )
    ]


def _validate_state_messages_for_runtime(
    state: Dict[str, Any],
    messages: Sequence[BaseMessage],
) -> list[BaseMessage]:
    """统一复用消息契约层清洗，避免 checkpoint 脏历史直达运行态。"""
    from app.ai.message_utils import validate_messages

    model_id = str(state.get("model_id") or "").lower()
    should_fix_reasoning = bool(state.get("enable_thinking"))
    if "deepseek" in model_id or "reasoner" in model_id:
        should_fix_reasoning = True

    return validate_messages(messages, fix_reasoning=should_fix_reasoning)


def _prepare_streaming_inference_state(
    state: Dict[str, Any],
    *,
    node_name: str = "supervisor",
) -> Tuple[Dict[str, Any], int, int, int, int, int]:
    """构造 streaming_wrapper 调用 agent.astream 前的推理态 state。"""
    raw_messages = _build_expert_inference_messages(state, node_name)
    original_messages = _validate_state_messages_for_runtime(state, raw_messages)
    if len(original_messages) != len(raw_messages):
        logger.info(
            "[%s] 推理态消息清洗: %d -> %d",
            node_name,
            len(raw_messages),
            len(original_messages),
        )
    inference_diagnostics: Dict[str, Any] = {}
    prepared_messages = _prepare_messages_for_supervisor_inference(
        original_messages,
        diagnostics=inference_diagnostics,
    )

    from app.ai import config as ai_config

    scene_key = SCENE_KEY_MULTI_AGENT_SUPERVISOR if node_name == "supervisor" else None
    budget_meta = resolve_context_budget_metadata(
        state,
        scene_key=scene_key,
        configured_max_tokens=getattr(ai_config, "MESSAGE_MAX_TOKENS", SUPERVISOR_CONTEXT_MIN_TOKENS),
        ratio=SUPERVISOR_CONTEXT_TOKEN_BUDGET_RATIO,
        min_tokens=SUPERVISOR_CONTEXT_MIN_TOKENS,
    )
    token_budget = int(budget_meta["token_budget"])

    tool_objects: list[Any] = []
    prompt_text = ""
    if node_name == "supervisor":
        prompt_text = SUPERVISOR_PROMPT
        tool_objects = [
            *_get_runtime_visible_supervisor_handoff_tools(state=state),
            decompose_goals,
            *_get_runtime_visible_supervisor_tools(state=state),
        ]

    llm_input_messages, ledger, prepared_token_estimate, pruned_token_estimate = build_llm_input_context(
        prepared_messages=prepared_messages,
        state=state,
        token_budget=token_budget,
        model_code=str(budget_meta.get("model_code") or ""),
        provider_code=str(budget_meta.get("provider_code") or ""),
        context_window=int(budget_meta.get("context_window") or token_budget),
        prompt_text=prompt_text,
        tool_objects=tool_objects,
        token_counter=count_tokens_approximately,
    )

    pruned_state = state.copy()
    pruned_state["messages"] = llm_input_messages
    existing_delivery_meta = pruned_state.get("delivery_meta")
    delivery_meta = dict(existing_delivery_meta) if isinstance(existing_delivery_meta, dict) else {}
    delivery_meta.update(
        {
            "truncation_flag": bool(inference_diagnostics.get("truncation_flag", False)),
            "tool_message_count": int(inference_diagnostics.get("tool_message_count") or 0),
            "truncated_tool_message_count": int(
                inference_diagnostics.get("truncated_tool_message_count") or 0
            ),
            "tool_message_chars_before": int(inference_diagnostics.get("tool_message_chars_before") or 0),
            "tool_message_chars_after": int(inference_diagnostics.get("tool_message_chars_after") or 0),
            "retrieval_tool_message_count": int(inference_diagnostics.get("retrieval_tool_message_count") or 0),
            "retrieval_truncated_tool_message_count": int(
                inference_diagnostics.get("retrieval_truncated_tool_message_count") or 0
            ),
            "retrieval_tool_message_chars_before": int(
                inference_diagnostics.get("retrieval_tool_message_chars_before") or 0
            ),
            "retrieval_tool_message_chars_after": int(
                inference_diagnostics.get("retrieval_tool_message_chars_after") or 0
            ),
            "retrieval_truncation_flag": bool(inference_diagnostics.get("retrieval_truncation_flag", False)),
            "ragflow_rollout_stage": _resolve_rollout_stage(),
            "ragflow_rollout_traffic_percent": _resolve_rollout_traffic_percent(),
            "context_budget_ledger": ledger.to_payload(),
        }
    )
    pruned_state["delivery_meta"] = delivery_meta

    input_message_count = len(pruned_state.get("messages", []))

    return (
        pruned_state,
        len(raw_messages),
        input_message_count,
        prepared_token_estimate,
        pruned_token_estimate,
        token_budget,
    )


def _log_streaming_output_statistics(node_name: str, collected_content: Sequence[str]) -> None:
    """记录 streaming 输出统计，辅助排障。"""
    full_output = "".join(collected_content)
    output_image_count = len(re.findall(r'!\[[^\]]*\]\([^)]+\)', full_output))

    logger.debug("=" * 60)
    logger.debug("[%s] LLM 输出统计:", node_name)
    logger.debug("  总长度: %s 字符", len(full_output))
    logger.debug("  包含图片: %s 张", output_image_count)
    logger.debug("  输出预览（前 500 字符）:")
    logger.debug("  %s", full_output[:500])
    logger.debug("=" * 60)


def _build_streaming_delta_return(
    final_state: Optional[Dict[str, Any]],
    initial_input_count: int,
    node_name: str,
) -> Dict[str, Any]:
    """构造 streaming_wrapper 结束时的增量消息返回。"""
    if not final_state:
        return {}

    messages = final_state.get("messages", [])
    delta_messages = messages[initial_input_count:] if len(messages) > initial_input_count else []

    other_keys = {k: v for k, v in final_state.items() if k != "messages"}
    ret = other_keys.copy()
    ret["messages"] = delta_messages

    logger.debug(
        "[%s] 返回增量消息: %s 条 (原 %s 条, 初始 %s 条)",
        node_name,
        len(delta_messages),
        len(messages),
        initial_input_count,
    )
    return ret


def _dispatch_messages_mode_chunk(
    chunk: Any,
    ctx: StreamingContext,
) -> None:
    """分发处理 stream_mode=messages 的单个 chunk。"""
    from langchain_core.messages import AIMessage, AIMessageChunk

    if not (isinstance(chunk, tuple) and len(chunk) == 2):
        return

    message, _metadata = chunk
    _record_emitted_message_id(message, ctx.emitted_message_ids)

    if _should_mute_expert_text_output(ctx.state, ctx.node_name):
        return

    handled_tool_message = _handle_messages_mode_tool_message(
        message=message,
        ctx=ctx,
    )
    if handled_tool_message:
        return

    if not isinstance(message, (AIMessage, AIMessageChunk)):
        return

    _emit_messages_mode_token(
        message=message,
        ctx=ctx,
    )

    _emit_messages_mode_thinking(
        message=message,
        ctx=ctx,
    )


def _collect_custom_mode_text_segments(chunk: Any) -> list[str]:
    """提取 custom 事件中的用户可见文本，用于跨模式去重。"""
    if not isinstance(chunk, dict):
        return []

    data = chunk.get("data")
    if not isinstance(data, dict):
        return []

    texts: list[str] = []
    for key in ("message", "content"):
        value = data.get(key)
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if normalized:
            texts.append(normalized)

    deduped: list[str] = []
    seen: set[str] = set()
    for text in texts:
        if text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


def _remember_custom_mode_text(chunk: Any, ctx: StreamingContext) -> None:
    """custom 文本透传后同步登记，避免 values 模式重复补发。"""
    if not ctx.collected_content:
        collected_text = ""
    else:
        collected_text = "".join(ctx.collected_content)

    for text in _collect_custom_mode_text_segments(chunk):
        if text in collected_text:
            continue
        ctx.collected_content.append(text)
        collected_text += text


def _dispatch_custom_mode_chunk(
    chunk: Any,
    ctx: StreamingContext,
) -> None:
    """分发处理 stream_mode=custom 的单个 chunk。

    custom 模式的事件由子图节点通过 get_stream_writer() 主动发射，
    格式已经是标准的 {"type": ..., "data": ..., "node": ...}，
    直接透传到顶层 writer。
    """
    if not (isinstance(chunk, dict) and "type" in chunk and "data" in chunk):
        logger.debug("[%s] 跳过非标准 custom chunk: %s", ctx.node_name, type(chunk))
        return
    logger.debug("[%s] 透传 custom 事件: type=%s", ctx.node_name, chunk.get("type"))
    ctx.writer(chunk)
    _remember_custom_mode_text(chunk, ctx)


def _maybe_compile_supervisor_data_handoff_after_stream(
    final_state: Dict[str, Any],
    *,
    initial_input_count: int,
    ctx: StreamingContext,
) -> Optional[Dict[str, Any]]:
    """在 supervisor 流结束后补编 data.query handoff，避免过早打断直接工具调用。"""
    if ctx.node_name != "supervisor":
        return None

    messages = final_state.get("messages", [])
    delta_messages_for_scan = messages[initial_input_count:] if len(messages) > initial_input_count else []
    if AgentOutputParser.extract_all_handoffs_from_messages(delta_messages_for_scan):
        return None

    extracted_goals = _extract_decomposed_goals_from_messages(delta_messages_for_scan)
    if extracted_goals:
        decompose_plan = _build_active_goal_plan(
            ctx.state,
            runtime_goals=extracted_goals,
            source="decompose_goals",
        )
        final_state["decomposed_goals"] = list(decompose_plan.get("goals") or [])

    runtime_goals = final_state.get("decomposed_goals")
    if not isinstance(runtime_goals, list):
        runtime_goals = ctx.state.get("decomposed_goals")

    active_goals = _resolve_active_goals(
        ctx.state,
        runtime_goals=runtime_goals if isinstance(runtime_goals, list) else None,
    )
    if not active_goals:
        user_query = _resolve_semantic_user_query(ctx.state)
        fallback_goals = _build_decomposed_goals_for_query(user_query) if user_query else []
        active_goals = _resolve_active_goals(
            ctx.state,
            runtime_goals=fallback_goals,
        )
        if active_goals:
            final_state["decomposed_goals"] = list(active_goals)
    if not active_goals:
        return None

    guard_state = dict(ctx.state)
    final_state["decomposed_goals"] = list(active_goals)
    guard_state["decomposed_goals"] = list(active_goals)

    normalized_batch = _inject_compiled_data_handoff_for_supervisor(
        [],
        state=guard_state,
        active_goals=active_goals,
    )
    if not normalized_batch:
        return None

    direct_findings = _build_direct_lookup_findings(delta_messages_for_scan)
    has_direct_lookup = bool(direct_findings)
    planned_goal_count = _count_must_answer_goals(active_goals)
    enable_multi_intent_mode = _should_enable_multi_intent_mode(
        handoff_batch_size=len(normalized_batch),
        has_direct_lookup=has_direct_lookup,
        state=guard_state,
    )

    legacy_fields = _detect_legacy_router_result_fields(final_state, guard_state)
    if legacy_fields:
        return None

    guarded_batch, blocked_handoffs, pending_goals = _apply_router_contract_guard(
        normalized_batch,
        state=guard_state,
    )
    if blocked_handoffs or not guarded_batch:
        return None

    existing_router_result = _extract_router_result_v2(final_state, guard_state)
    final_state["router_result_v2"] = _build_router_result_v2_payload(
        existing_payload=existing_router_result,
        accepted_decisions=[dict(item.get("route_decision") or {}) for item in guarded_batch],
        blocked_handoffs=[],
        pending_goals=pending_goals,
        turn_id=str(guard_state.get("turn_id") or ""),
        event="intent_router_dispatch_ready",
        reason="",
        runtime_state=guard_state,
    )
    first_handoff = dict(guarded_batch[0])
    direct_answer_markdown = _sanitize_direct_answer_markdown(
        _extract_latest_visible_ai_markdown(delta_messages_for_scan),
        handoff_display_text=_resolve_handoff_display_text(first_handoff, limit=240),
    )
    if direct_answer_markdown:
        first_handoff["direct_answer_markdown"] = direct_answer_markdown

    partial_preview = direct_answer_markdown or _build_external_lookup_display_markdown_from_findings(direct_findings)
    preview_summary = _normalize_tool_summary_text(partial_preview, limit=220)
    emitted_snapshot = _normalize_tool_summary_text("".join(ctx.collected_content), limit=600)
    if enable_multi_intent_mode and callable(ctx.writer) and preview_summary and preview_summary not in emitted_snapshot:
        emit_status(
            ctx.writer,
            message="已完成可直答子问题，先返回当前结果，剩余问题继续处理中...",
            node=ctx.node_name,
        )
        emit_token(ctx.writer, partial_preview, node=ctx.node_name)
        ctx.collected_content.append(partial_preview)

    logger.info(
        "[%s] supervisor流结束后自动编译 data handoff: accepted=%d, direct_findings=%d, planned_goals=%d, multi_intent=%s",
        ctx.node_name,
        len(guarded_batch),
        len(direct_findings),
        planned_goal_count,
        enable_multi_intent_mode,
    )
    return _build_streaming_handoff_return(
        final_state=final_state,
        delta_messages=delta_messages_for_scan,
        handoff_data=first_handoff,
        handoff_queue=guarded_batch[1:],
        multi_intent_mode=enable_multi_intent_mode,
    )


def _dispatch_values_mode_chunk(
    final_state: Dict[str, Any],
    initial_input_count: int,
    input_message_count: int,
    ctx: StreamingContext,
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """分发处理 stream_mode=values 的单个 chunk。"""
    from langchain_core.messages import AIMessage

    messages = final_state.get("messages", [])
    delta_messages_for_scan = messages[initial_input_count:] if len(messages) > initial_input_count else []

    if ctx.node_name == "supervisor":
        extracted_goals = _extract_decomposed_goals_from_messages(delta_messages_for_scan)
        if extracted_goals:
            decompose_plan = _build_active_goal_plan(
                ctx.state,
                runtime_goals=extracted_goals,
                source="decompose_goals",
            )
            final_state["decomposed_goals"] = list(decompose_plan.get("goals") or [])

        handoff_batch = AgentOutputParser.extract_all_handoffs_from_messages(delta_messages_for_scan)

        runtime_goals = final_state.get("decomposed_goals")
        active_goals = _resolve_active_goals(
            ctx.state,
            runtime_goals=runtime_goals if isinstance(runtime_goals, list) else ctx.state.get("decomposed_goals"),
        )

        if handoff_batch and _should_backfill_runtime_goals_for_handoff(active_goals, handoff_batch):
            backfilled_goals, _source = _resolve_decomposed_goals_for_query(
                _resolve_semantic_user_query(ctx.state),
                runtime_state=ctx.state,
            )
            if backfilled_goals:
                active_goals = _normalize_active_goals(backfilled_goals)
                final_state["decomposed_goals"] = list(active_goals)

        normalized_active_goals = list(active_goals)
        guard_state = {
            **dict(ctx.state),
            **{k: v for k, v in final_state.items() if k != "messages"},
            "messages": list(messages),
            "decomposed_goals": normalized_active_goals,
        }
        final_state["decomposed_goals"] = normalized_active_goals

        if handoff_batch:
            normalized_batch = _normalize_handoff_batch_for_supervisor(
                handoff_batch,
                delta_messages=delta_messages_for_scan,
                state=ctx.state,
            )
            direct_findings = _build_direct_lookup_findings(delta_messages_for_scan)
            has_direct_lookup = bool(direct_findings)
            planned_goal_count = _count_must_answer_goals(active_goals)
            enable_multi_intent_mode = _should_enable_multi_intent_mode(
                handoff_batch_size=len(normalized_batch),
                has_direct_lookup=has_direct_lookup,
                state=guard_state,
            )
            legacy_fields = _detect_legacy_router_result_fields(final_state, guard_state)
            if legacy_fields:
                guarded_batch = []
                blocked_handoffs = []
                for handoff in normalized_batch:
                    blocked_entry = _build_router_blocked_entry(
                        handoff=handoff,
                        reason="legacy_field_detected",
                    )
                    blocked_entry["legacy_fields"] = list(legacy_fields)
                    blocked_handoffs.append(blocked_entry)
                pending_goals = _build_router_dispatch_goal_queue(active_goals)
            else:
                guarded_batch, blocked_handoffs, pending_goals = _apply_router_contract_guard(
                    normalized_batch,
                    state=guard_state,
                )

            existing_meta = (
                final_state.get("delivery_meta")
                if isinstance(final_state.get("delivery_meta"), dict)
                else ctx.state.get("delivery_meta")
            )
            delivery_meta = dict(existing_meta or {})
            blocked_goal_ids = [
                str(item.get("goal_id") or "")
                for item in blocked_handoffs
                if str(item.get("goal_id") or "")
            ]
            accepted_decisions = [
                dict(item.get("route_decision") or {})
                for item in guarded_batch
                if isinstance(item.get("route_decision"), dict)
            ]
            if blocked_handoffs:
                delivery_meta.update(
                    {
                        "router_contract_blocked_count": len(blocked_handoffs),
                        "router_contract_blocked": blocked_handoffs,
                        "router_contract_blocked_goal_ids": blocked_goal_ids,
                    }
                )
                emit_status(
                    ctx.writer,
                    message=f"路由门禁拦截 {len(blocked_handoffs)} 条无效委派，正在整理可返回结果。",
                    node=ctx.node_name,
                )

            router_event, router_reason = (
                ("intent_router_legacy_field_detected", "legacy_field_detected")
                if legacy_fields
                else ("intent_router_handoff_blocked", "router_contract_blocked")
                if blocked_handoffs
                else ("intent_router_dispatch_ready", "")
            )

            existing_router_result = _extract_router_result_v2(final_state, guard_state)
            final_state["router_result_v2"] = _build_router_result_v2_payload(
                existing_payload=existing_router_result,
                accepted_decisions=accepted_decisions,
                blocked_handoffs=blocked_handoffs,
                pending_goals=pending_goals,
                turn_id=str(guard_state.get("turn_id") or ""),
                event=router_event,
                reason=router_reason,
                runtime_state=guard_state,
                extra={
                    "legacy_fields": list(legacy_fields) if legacy_fields else None,
                },
            )
            final_state["delivery_meta"] = delivery_meta

            if not guarded_batch and blocked_handoffs:
                unresolved_goals = [dict(goal) for goal in (pending_goals or active_goals) if isinstance(goal, dict)]
                pending_titles = [str(goal.get("title") or goal.get("goal_id") or "未命名目标") for goal in unresolved_goals]
                if pending_titles:
                    final_state["delivery_meta"] = {
                        **dict(final_state.get("delivery_meta") or {}),
                        "pending_goal_titles": pending_titles,
                        "pending_goal_ids": [
                            str(goal.get("goal_id") or "")
                            for goal in unresolved_goals
                            if str(goal.get("goal_id") or "")
                        ],
                    }

                blocked_answer = _render_coverage_blocked_message(
                    unresolved_goals or active_goals,
                    {
                        "pass": False,
                        "missing_goals": [
                            {
                                "goal_id": str(goal.get("goal_id") or ""),
                                "title": str(goal.get("title") or goal.get("goal_id") or "未命名目标"),
                                "reason": "router_contract_blocked",
                            }
                            for goal in unresolved_goals or active_goals
                            if isinstance(goal, dict)
                        ],
                    },
                )
                preview_markdown = _sanitize_direct_answer_markdown(
                    _extract_latest_visible_ai_markdown(delta_messages_for_scan)
                ) or _build_external_lookup_display_markdown_from_findings(direct_findings)
                if preview_markdown:
                    blocked_answer = f"{preview_markdown}\n\n{blocked_answer}"

                final_state["messages"] = [
                    *list(ctx.state.get("messages") or []),
                    _create_ai_message_with_skill_runtime(
                        blocked_answer,
                        {**guard_state, **final_state},
                    ),
                ]
                final_state["final_answer"] = blocked_answer
                final_state["pending_handoff"] = None
                final_state["handoff_queue"] = []
                final_state.pop("system_context", None)
                final_state["multi_intent_mode"] = True
                return input_message_count, None

            if not guarded_batch:
                logger.info(
                    "[%s] values模式检测到 handoff，但标准化后无可执行委派，回退到常规消息分发。",
                    ctx.node_name,
                )
            else:
                first_handoff = dict(guarded_batch[0])
                direct_answer_markdown = _sanitize_direct_answer_markdown(
                    _extract_latest_visible_ai_markdown(delta_messages_for_scan),
                    handoff_display_text=_resolve_handoff_display_text(first_handoff, limit=240),
                )
                if direct_answer_markdown:
                    first_handoff["direct_answer_markdown"] = direct_answer_markdown
                remaining_handoffs = guarded_batch[1:]
                target_agent = str(first_handoff.get("target_agent") or "unknown")
                logger.info(
                    "[%s] values模式检测到 handoff_batch: total=%d, accepted=%d, blocked=%d, first_target=%s, direct_findings=%d, planned_goals=%d, multi_intent=%s",
                    ctx.node_name,
                    len(normalized_batch),
                    len(guarded_batch),
                    len(blocked_handoffs),
                    target_agent,
                    len(direct_findings),
                    planned_goal_count,
                    enable_multi_intent_mode,
                )
                emit_status(
                    ctx.writer,
                    message=_build_handoff_status_message(target_agent, guard_state),
                    node=ctx.node_name,
                )
                ctx.writer({
                    "type": "handoff",
                    "data": _build_handoff_event_payload(target_agent, guard_state),
                    "node": ctx.node_name,
                })
                handoff_return = _build_streaming_handoff_return(
                    final_state=final_state,
                    delta_messages=delta_messages_for_scan,
                    handoff_data=first_handoff,
                    handoff_queue=remaining_handoffs,
                    multi_intent_mode=enable_multi_intent_mode,
                )
                return input_message_count, handoff_return

    _emit_kb_images_from_delta_messages(
        delta_messages=delta_messages_for_scan,
        ctx=ctx,
    )

    new_messages = messages[input_message_count:] if len(messages) > input_message_count else []
    for new_message in new_messages:
        if not isinstance(new_message, AIMessage):
            continue

        if _should_mute_expert_text_output(ctx.state, ctx.node_name):
            continue

        emitted_tool_calls = _emit_tool_start_events_from_ai_message(
            ai_message=new_message,
            ctx=ctx,
        )
        if emitted_tool_calls:
            continue

        message_content = getattr(new_message, "content", "")
        message_id = getattr(new_message, "id", None)
        should_skip_message = _should_skip_values_text_message(
            msg_content=message_content,
            msg_id=message_id,
            ctx=ctx,
        )
        if should_skip_message:
            continue

        if message_content:
            logger.info("[%s] values 模式补发消息: %s...", ctx.node_name, message_content[:30])
            _emit_values_text_message(
                ai_message=new_message,
                msg_content=message_content,
                ctx=ctx,
            )
            ctx.collected_content.append(message_content)
            if message_id:
                ctx.emitted_message_ids.add(message_id)

    return len(messages), None


async def _run_streaming_dispatch_loop(
    agent: Any,
    pruned_state: Dict[str, Any],
    config: Any,
    input_message_count: int,
    ctx: StreamingContext,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """运行 streaming 双模式分发循环。"""
    final_state: Optional[Dict[str, Any]] = None
    initial_input_count = input_message_count
    next_input_count = input_message_count

    async for mode, chunk in agent.astream(
        pruned_state,
        config,
        stream_mode=["messages", "values", "custom"],
    ):
        if mode == "messages":
            _dispatch_messages_mode_chunk(
                chunk=chunk,
                ctx=ctx,
            )
            continue

        if mode == "custom":
            _dispatch_custom_mode_chunk(chunk=chunk, ctx=ctx)
            continue

        if mode != "values":
            continue

        final_state = chunk
        next_input_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            initial_input_count=initial_input_count,
            input_message_count=next_input_count,
            ctx=ctx,
        )
        if handoff_return is not None:
            return final_state, handoff_return

    if final_state is not None:
        compiled_handoff = _maybe_compile_supervisor_data_handoff_after_stream(
            final_state,
            initial_input_count=initial_input_count,
            ctx=ctx,
        )
        if compiled_handoff is not None:
            return final_state, compiled_handoff

    return final_state, None


def _handle_streaming_wrapper_exception(
    error_text: str,
    ctx: StreamingContext,
) -> Dict[str, Any]:
    """处理 streaming_wrapper 异常：优先 supervisor 兜底，其次统一友好错误。"""
    route_decision = fallback_router(node_name=ctx.node_name, state=ctx.state, error_text=error_text)
    route = str(route_decision.get("route") or "friendly_error")
    runtime_recovery_state = route_decision.get("runtime_recovery_state")

    if route == "handoff":
        fallback_handoff = route_decision.get("pending_handoff") or {}
        logger.warning(
            "[%s] 命中模型权限错误，降级兜底路由到 %s",
            ctx.node_name,
            fallback_handoff.get("target_agent"),
        )
        emit_status(
            ctx.writer,
            message=str(route_decision.get("status_message") or "已触发运行时兜底路由。"),
            node=ctx.node_name,
        )
        return {
            "messages": [],
            "pending_handoff": fallback_handoff,
            "handoff_queue": [],
            "completed_handoffs": [],
            "handoff_execution_trace": [],
            "multi_intent_mode": False,
            "runtime_recovery_state": runtime_recovery_state,
        }

    error_msg = str(route_decision.get("message") or _build_stream_error_message(error_text))
    if route == "core_tools_only":
        emit_status(
            ctx.writer,
            message="插件链路异常，已回退到核心能力路径。",
            node=ctx.node_name,
        )
    emit_token(ctx.writer, error_msg, node=ctx.node_name)
    return {
        "messages": [_create_ai_message_with_skill_runtime(error_msg, ctx.state)],
        "runtime_recovery_state": runtime_recovery_state,
    }


async def _execute_streaming_wrapper(
    agent: Any,
    node_name: str,
    state: Dict[str, Any],
    config: Any,
    writer,
) -> Dict[str, Any]:
    """执行单个专家节点的 streaming 编排与事件发射。"""
    final_state = None
    collected_content: list[str] = []
    kb_images: Dict[str, str] = {}

    try:
        (
            pruned_state,
            original_message_count,
            input_message_count,
            prepared_token_estimate,
            pruned_token_estimate,
            token_budget,
        ) = _prepare_streaming_inference_state(state, node_name=node_name)

        initial_input_count = input_message_count

        logger.info(
            "[%s] Context Budget: msgs %d->%d, tokens %d->%d, budget=%d",
            node_name,
            original_message_count,
            input_message_count,
            prepared_token_estimate,
            pruned_token_estimate,
            token_budget,
        )

        sent_tool_call_ids: set = set()
        emitted_message_ids: set = set()

        await _prefill_emitted_message_ids(
            agent=agent,
            config=config,
            state_messages=state.get("messages", []),
            emitted_message_ids=emitted_message_ids,
            node_name=node_name,
        )

        logger.debug("[%s] 预填充 emitted_message_ids: %s 个", node_name, len(emitted_message_ids))

        ctx = StreamingContext(
            writer=writer,
            node_name=node_name,
            state=state,
            collected_content=collected_content,
            kb_images=kb_images,
            emitted_message_ids=emitted_message_ids,
            sent_tool_call_ids=sent_tool_call_ids,
        )

        final_state, handoff_return = await _run_streaming_dispatch_loop(
            agent=agent,
            pruned_state=pruned_state,
            config=config,
            input_message_count=input_message_count,
            ctx=ctx,
        )
        if handoff_return is not None:
            handoff_return["runtime_recovery_state"] = _build_runtime_recovery_state(
                state,
                fallback_route="none",
                fallback_triggered=False,
                plugin_lifecycle_status=_resolve_plugin_lifecycle_status(state),
            )
            return handoff_return

        _log_streaming_output_statistics(node_name=node_name, collected_content=collected_content)
        delta_return = _build_streaming_delta_return(
            final_state=final_state,
            initial_input_count=initial_input_count,
            node_name=node_name,
        )
        delta_return["runtime_recovery_state"] = _build_runtime_recovery_state(
            state,
            fallback_route="none",
            fallback_triggered=False,
            plugin_lifecycle_status=_resolve_plugin_lifecycle_status(state),
        )
        return delta_return

    except GraphInterrupt:
        raise
    except Exception as exc:
        logger.error("[%s]流式输出异常: %s", node_name, exc, exc_info=True)
        ctx = StreamingContext(
            writer=writer,
            node_name=node_name,
            state=state,
            collected_content=collected_content,
            kb_images=kb_images,
            emitted_message_ids=set(),
            sent_tool_call_ids=set(),
        )
        return _handle_streaming_wrapper_exception(
            error_text=str(exc),
            ctx=ctx,
        )


def _create_streaming_agent_wrapper(agent: Any, node_name: str):
    """创建可复用的 streaming wrapper 工厂（模块级）。"""

    async def streaming_wrapper(state, config):
        writer = get_stream_writer()
        return await _execute_streaming_wrapper(
            agent=agent,
            node_name=node_name,
            state=state,
            config=config,
            writer=writer,
        )

    return streaming_wrapper


def _resolve_tool_name(tool_obj: Any) -> str:
    """解析工具名称，兼容 LangChain Tool / 函数对象。"""
    name = getattr(tool_obj, "name", None)
    if callable(name):
        try:
            name = name()
        except Exception:
            name = None
    if not name:
        name = getattr(tool_obj, "__name__", "")
    return str(name or "").strip().lower()


def _build_tool_entry(
    tool_obj: Any,
    groups: Optional[set[str]] = None,
    *,
    runtime_visibility: str = "always",
    required_runtime_tools: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """构造工具候选条目。"""

    normalized_visibility = str(runtime_visibility or "always").strip().lower() or "always"
    tool_name = _resolve_tool_name(tool_obj)
    normalized_required_runtime_tools = _normalize_policy_tokens(required_runtime_tools or [])
    if normalized_visibility == "catalog_after_load" and not normalized_required_runtime_tools and tool_name:
        normalized_required_runtime_tools = {tool_name}

    return {
        "tool": tool_obj,
        "name": tool_name,
        "groups": {str(item).strip().lower() for item in (groups or set()) if str(item).strip()},
        "runtime_visibility": normalized_visibility,
        "required_runtime_tools": normalized_required_runtime_tools,
    }


def _normalize_policy_tokens(raw_value: Any) -> set[str]:
    """标准化策略 token 列表。"""
    if raw_value is None:
        return set()
    if isinstance(raw_value, str):
        candidates = [raw_value]
    elif isinstance(raw_value, (list, tuple, set)):
        candidates = raw_value
    else:
        return set()

    normalized = set()
    for item in candidates:
        token = str(item or "").strip().lower()
        if token:
            normalized.add(token)
    return normalized


def _match_policy_tokens(entry: Dict[str, Any], tokens: set[str]) -> bool:
    """判断工具条目是否命中策略 token。"""
    if not tokens:
        return False

    name = str(entry.get("name", "")).strip().lower()
    groups = {
        str(item).strip().lower()
        for item in (entry.get("groups") or set())
        if str(item).strip()
    }
    entry_tokens = {name, f"tool:{name}", *groups}
    return bool(entry_tokens & tokens)


def _select_tool_entries_by_governance_policy(
    tool_entries: list[Dict[str, Any]],
    agent_name: str,
) -> list[Dict[str, Any]]:
    """按工具治理策略过滤工具候选条目，并保留条目元数据。"""
    fail_mode = "compat"

    try:
        from app.services.config_resolver import ConfigResolver

        settings = ConfigResolver.get_tool_governance_settings()
        fail_mode = str(settings.get("fail_mode") or "compat").strip().lower() or "compat"
        if not settings.get("enabled", False):
            return list(tool_entries)

        policy_layers = ConfigResolver.get_tool_policy_layers(agent_name)
        merged_policy = policy_layers.get("merged_policy")
        if not isinstance(merged_policy, dict):
            merged_policy = {}

        allow_tokens = _normalize_policy_tokens(merged_policy.get("allow"))
        deny_tokens = _normalize_policy_tokens(merged_policy.get("deny"))

        default_allow = fail_mode in {"compat", "allow"}
        if allow_tokens:
            default_allow = False

        selected_entries: list[Dict[str, Any]] = []
        denied_names: list[str] = []

        for entry in tool_entries:
            allowed = default_allow or _match_policy_tokens(entry, allow_tokens)
            if _match_policy_tokens(entry, deny_tokens):
                allowed = False

            if allowed:
                selected_entries.append(entry)
            else:
                denied_names.append(entry.get("name", "unknown"))

        logger.info(
            "工具治理生效: agent=%s, allow=%s, deny=%s, selected=%s, denied=%s",
            agent_name,
            sorted(allow_tokens),
            sorted(deny_tokens),
            [entry.get("name", "unknown") for entry in selected_entries],
            denied_names,
        )
        return selected_entries
    except Exception as exc:
        logger.warning(
            "工具治理过滤失败，降级继续: agent=%s, fail_mode=%s, error=%s",
            agent_name,
            fail_mode,
            exc,
        )
        if fail_mode in {"deny", "minimal"}:
            return []
        return list(tool_entries)


def _apply_tool_governance_policy(tool_entries: list[Dict[str, Any]], agent_name: str) -> list[Any]:
    """按工具治理策略过滤工具候选集。"""
    return [entry["tool"] for entry in _select_tool_entries_by_governance_policy(tool_entries, agent_name)]


def _get_common_tool_entries() -> list[Dict[str, Any]]:
    """构建共享工具候选条目（未应用治理策略）。"""
    entries: list[Dict[str, Any]] = []

    try:
        from app.ai.tools.vision_tool import analyze_image, is_vision_configured
        if is_vision_configured():
            entries.append(_build_tool_entry(analyze_image, {"group:vision"}))
            logger.debug("共享工具: 已加载 analyze_image")
    except Exception as e:
        logger.warning("Vision 工具加载失败: %s", e)

    try:
        from app.ai.tools.file_tools import read_uploaded_file, read

        entries.append(_build_tool_entry(read_uploaded_file, {"group:file"}))
        entries.append(_build_tool_entry(read, {"group:file"}))
        logger.debug("共享工具: 已加载 read_uploaded_file/read")
    except Exception as e:
        logger.warning("文件读取工具加载失败: %s", e)

    return entries


def _normalize_allowed_tool_registry(raw_value: Any) -> Dict[str, Dict[str, Any]]:
    """标准化会话级领域工具授权状态。"""

    if not isinstance(raw_value, dict):
        return {}

    normalized: Dict[str, Dict[str, Any]] = {}
    for raw_name, payload in raw_value.items():
        tool_name = str(raw_name or '').strip().lower()
        if not tool_name:
            continue
        payload_dict = payload if isinstance(payload, dict) else {}
        normalized[tool_name] = {
            'tool_name': tool_name,
            'skill_ids': list(payload_dict.get('skill_ids') or []),
            'versions': list(payload_dict.get('versions') or []),
            'tool_groups': list(payload_dict.get('tool_groups') or []),
        }
    return normalized


def _resolve_allowed_tool_names(state: Dict[str, Any]) -> List[str]:
    """从当前 state 提取允许使用的领域工具名。"""

    registry = _normalize_allowed_tool_registry(state.get('allowed_tool_registry') or {})
    return sorted(registry.keys())


def _restore_allowed_tool_registry_from_messages(
    messages: Sequence[BaseMessage],
) -> Dict[str, Dict[str, Any]]:
    """优先从历史 AIMessage.additional_kwargs.skill_runtime 恢复领域工具授权。"""

    for message in reversed(list(messages or [])):
        skill_runtime = extract_skill_runtime_from_ai_message(message)
        if not skill_runtime:
            continue

        allowed_tools = skill_runtime.get('allowed_tools') or []
        if not isinstance(allowed_tools, list):
            continue

        restored: Dict[str, Dict[str, Any]] = {}
        for item in allowed_tools:
            tool_name = str(item or '').strip().lower()
            if not tool_name:
                continue
            restored[tool_name] = {
                'tool_name': tool_name,
                'skill_ids': [],
                'versions': [],
                'tool_groups': [],
            }
        if restored:
            return restored

    return {}


def _normalize_catalog_tool_contract(raw_value: Any) -> Dict[str, Any]:
    """标准化 catalog descriptor 内的 tool_contract。"""

    payload = raw_value if isinstance(raw_value, dict) else {}
    required_tools = _normalize_policy_tokens(payload.get('required_tools'))
    optional_tools = _normalize_policy_tokens(payload.get('optional_tools')) - required_tools
    tool_groups = _normalize_policy_tokens(payload.get('tool_groups'))
    expose_after_load_raw = payload.get('expose_after_load')
    expose_after_load = True if expose_after_load_raw is None else bool(expose_after_load_raw)
    return {
        'required_tools': required_tools,
        'optional_tools': optional_tools,
        'tool_groups': tool_groups,
        'expose_after_load': expose_after_load,
    }


def _build_catalog_load_gate_index(state: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
    """从 skill_catalog_manifest 派生“需先 load 才暴露”的运行时工具索引。"""

    normalized_state = dict(state or {})
    manifest = normalized_state.get('skill_catalog_manifest') or []
    if not isinstance(manifest, list):
        return {}

    gate_index: Dict[str, List[str]] = {}
    for item in manifest:
        if not isinstance(item, dict):
            continue
        skill_id = str(item.get('skill_id') or '').strip()
        if not skill_id:
            continue
        tool_contract = _normalize_catalog_tool_contract(item.get('tool_contract'))
        if not tool_contract['expose_after_load']:
            continue
        contract_tools = tool_contract['required_tools'] | tool_contract['optional_tools']
        for tool_name in contract_tools:
            skill_ids = gate_index.setdefault(tool_name, [])
            if skill_id not in skill_ids:
                skill_ids.append(skill_id)
    return gate_index


def _resolve_entry_required_runtime_tools(entry: Dict[str, Any]) -> set[str]:
    """解析条目的运行时授权工具集合。"""

    required_tools = _normalize_policy_tokens(entry.get('required_runtime_tools'))
    if required_tools:
        return required_tools

    visibility = str(entry.get('runtime_visibility') or 'always').strip().lower() or 'always'
    tool_name = str(entry.get('name') or '').strip().lower()
    if visibility == 'catalog_after_load' and tool_name:
        return {tool_name}
    return set()


def _resolve_handoff_target_agent_from_entry(entry: Dict[str, Any]) -> str:
    """从 handoff 工具条目解析目标 agent 名称。"""

    tool_name = str(entry.get("name") or "").strip().lower()
    if tool_name.startswith("assign_to_"):
        return tool_name.removeprefix("assign_to_")
    return ""


def _is_handoff_entry_goal_visible(entry: Dict[str, Any], state: Optional[Dict[str, Any]]) -> bool:
    """按当前活动目标约束 handoff 工具可见性。"""

    target_agent = _resolve_handoff_target_agent_from_entry(entry)
    if not target_agent:
        return True

    _active_goals, dispatch_queue, latest_user_text = _resolve_dispatch_queue_with_query_fallback(state)
    if not dispatch_queue and not latest_user_text:
        return True
    if not dispatch_queue:
        return False

    allowed_agents = {
        agent
        for goal in dispatch_queue
        for agent in _normalize_goal_allowed_agents(goal.get("allowed_agents"), str(goal.get("kind") or ""))
    }
    return target_agent in allowed_agents


def _is_tool_entry_runtime_visible(entry: Dict[str, Any], state: Optional[Dict[str, Any]]) -> bool:
    """判断某个工具条目在当前会话是否可见/可执行。"""

    normalized_state = dict(state or {})
    visibility = str(entry.get("runtime_visibility") or "always").strip().lower() or "always"
    required_tools = _resolve_entry_required_runtime_tools(entry)

    if visibility == "after_load":
        if not required_tools:
            return False

        allowed_tools = set(_resolve_allowed_tool_names(normalized_state))
        if not required_tools.issubset(allowed_tools):
            return False
    elif visibility == "catalog_after_load":
        gated_tool_index = _build_catalog_load_gate_index(normalized_state)
        gated_required_tools = {tool_name for tool_name in required_tools if tool_name in gated_tool_index}
        if gated_required_tools:
            allowed_tools = set(_resolve_allowed_tool_names(normalized_state))
            if not gated_required_tools.issubset(allowed_tools):
                return False

    return _is_handoff_entry_goal_visible(entry, normalized_state)


def _build_runtime_tool_denied_message(entry: Dict[str, Any], state: Optional[Dict[str, Any]] = None) -> str:
    """构造运行态越权工具调用提示。"""

    tool_name = str(entry.get("name") or "该工具").strip() or "该工具"
    required_tools = _resolve_entry_required_runtime_tools(entry)
    gate_index = _build_catalog_load_gate_index(state)
    required_skill_ids = sorted({
        skill_id
        for runtime_tool in required_tools
        for skill_id in gate_index.get(runtime_tool, [])
    })
    if len(required_skill_ids) == 1:
        return f"{tool_name} 尚未授权：请先调用 load_skills 加载 {required_skill_ids[0]} skill。"
    return f"{tool_name} 尚未授权：请先调用 load_skills 加载对应 skill。"


def _build_tool_entry_index(tool_entries: list[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """按工具名构建候选条目索引。"""

    return {
        str(entry.get("name") or "").strip().lower(): entry
        for entry in tool_entries
        if str(entry.get("name") or "").strip()
    }


def _build_runtime_tool_call_wrapper(
    tool_entries: list[Dict[str, Any]],
    *,
    agent_name: str,
):
    """构造统一的运行态工具执行拦截器。"""

    entry_index = _build_tool_entry_index(tool_entries)

    def _extract_request_state(request: Any) -> Dict[str, Any]:
        runtime = getattr(request, "runtime", None)
        runtime_state = getattr(runtime, "state", None)
        if isinstance(runtime_state, dict):
            return runtime_state
        request_state = getattr(request, "state", None)
        if isinstance(request_state, dict):
            return request_state
        return {}

    def _maybe_block(request: Any) -> Optional[ToolMessage]:
        call = getattr(request, "tool_call", None) or {}
        tool_name = str(call.get("name") or "").strip().lower()
        entry = entry_index.get(tool_name)
        if not entry:
            return None

        state = _extract_request_state(request)
        if _is_tool_entry_runtime_visible(entry, state):
            return None

        denied_message = _build_runtime_tool_denied_message(entry, state)
        logger.info(
            "运行态工具执行被拦截: agent=%s, tool=%s, allowed_tools=%s",
            agent_name,
            tool_name,
            _resolve_allowed_tool_names(state),
        )
        return ToolMessage(
            content=denied_message,
            tool_call_id=str(call.get("id") or tool_name or "tool_call"),
            name=tool_name or None,
        )

    def _wrap(request: Any, execute: Any):
        blocked_message = _maybe_block(request)
        if blocked_message is not None:
            return blocked_message
        return execute(request)

    async def _awrap(request: Any, execute: Any):
        blocked_message = _maybe_block(request)
        if blocked_message is not None:
            return blocked_message
        return await execute(request)

    return _wrap, _awrap


def _apply_runtime_tool_visibility_policy(
    tool_entries: list[Dict[str, Any]],
    state: Optional[Dict[str, Any]],
    *,
    agent_name: str,
) -> list[Dict[str, Any]]:
    """按会话 skill 授权裁剪当前轮对模型可见的工具集合。"""

    normalized_state = dict(state or {})

    try:
        from app.services.skill_service import SkillService

        runtime_mode = SkillService.resolve_runtime_mode()
        if runtime_mode != SkillService.SKILL_RUNTIME_MODE_PROGRESSIVE:
            return list(tool_entries)
    except Exception as exc:
        logger.warning("运行态工具可见性判定失败，降级保留原工具: agent=%s, error=%s", agent_name, exc)
        return list(tool_entries)

    allowed_tools = set(_resolve_allowed_tool_names(normalized_state))
    selected_entries: list[Dict[str, Any]] = []
    hidden_names: list[str] = []

    for entry in tool_entries:
        if not _is_tool_entry_runtime_visible(entry, normalized_state):
            hidden_names.append(entry.get("name", "unknown"))
            continue
        selected_entries.append(entry)

    logger.info(
        "运行态工具可见性生效: agent=%s, allowed_tools=%s, visible=%s, hidden=%s",
        agent_name,
        sorted(allowed_tools),
        [entry.get("name", "unknown") for entry in selected_entries],
        hidden_names,
    )
    return selected_entries


def _restore_loaded_skill_registry_from_messages(
    messages: Sequence[BaseMessage],
) -> Dict[str, Dict[str, Any]]:
    """优先从历史 AIMessage.additional_kwargs.skill_runtime 恢复会话级 Skill registry。"""

    for message in reversed(list(messages or [])):
        skill_runtime = extract_skill_runtime_from_ai_message(message)
        if not skill_runtime:
            continue

        registry: Dict[str, Dict[str, Any]] = {}
        for item in skill_runtime.get("loaded_skills") or []:
            if not isinstance(item, dict):
                continue
            skill_id = str(item.get("skill_id") or "").strip()
            if not skill_id:
                continue
            registry[skill_id] = {
                "skill_id": skill_id,
                "version": str(item.get("version") or "v1").strip() or "v1",
                "truncated": bool(item.get("truncated", False)),
                "source_turn_id": None,
            }
        if registry:
            return registry

    return {}


def _resolve_skill_runtime_replay_source(state: Dict[str, Any]) -> str:
    """判断当前轮 skill_runtime 的 replay_source。"""

    messages = list(state.get("messages") or [])
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            break
        if isinstance(message, ToolMessage) and str(getattr(message, "name", "") or "").strip() == "load_skills":
            return "live"

    if state.get("loaded_skill_registry") or state.get("loaded_skill_context"):
        return "rehydrated"
    return "live"


def _build_skill_runtime_state_payload(
    state: Dict[str, Any],
    *,
    replay_source: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """根据当前 LangGraph state 构造 canonical skill_runtime 载荷。"""

    from app.services.skill_service import SkillService

    if not SkillService._is_skill_runtime_trace_enabled():
        return None

    resolved_replay_source = str(replay_source or _resolve_skill_runtime_replay_source(state)).strip() or "live"
    loaded_skill_registry = state.get("loaded_skill_registry") or {}
    loaded_skills: List[Dict[str, Any]] = []
    if isinstance(loaded_skill_registry, dict):
        for skill_id, payload in loaded_skill_registry.items():
            if not str(skill_id or "").strip():
                continue
            payload_dict = payload if isinstance(payload, dict) else {}
            loaded_skills.append(
                {
                    "skill_id": str(skill_id),
                    "version": str(payload_dict.get("version") or SkillService.DEFAULT_VERSION),
                    "truncated": bool(payload_dict.get("truncated", False)),
                }
            )

    catalog_version = state.get("catalog_version")
    manifest = state.get("skill_catalog_manifest") or []
    if not catalog_version and isinstance(manifest, list):
        try:
            catalog_version = SkillService._compute_catalog_version(manifest)
        except Exception:
            catalog_version = "-"

    visible_skill_count = state.get("visible_skill_count")
    if visible_skill_count is None:
        visible_skill_count = len(manifest) if isinstance(manifest, list) else 0

    return build_skill_runtime_additional_kwargs_payload(
        runtime_mode=SkillService.resolve_runtime_mode(),
        catalog_version=catalog_version,
        visible_skill_count=visible_skill_count,
        loaded_skills=loaded_skills,
        allowed_tools=_resolve_allowed_tool_names(state),
        replay_source=resolved_replay_source,
    )


def _create_ai_message_with_skill_runtime(content: str, state: Dict[str, Any]):
    """创建带 canonical skill_runtime/router_result_v2 的 AIMessage。"""

    additional_kwargs: Dict[str, Any] = {}
    runtime_payload = _build_skill_runtime_state_payload(state)
    if runtime_payload is not None:
        additional_kwargs["skill_runtime"] = runtime_payload

    router_result_v2 = state.get("router_result_v2")
    if isinstance(router_result_v2, dict):
        additional_kwargs["router_result_v2"] = _build_router_result_v2_payload(
            existing_payload=router_result_v2,
            event=str(router_result_v2.get("event") or "intent_router_replay"),
            reason=str(router_result_v2.get("reason") or ""),
            runtime_state=state,
        )

    return create_ai_message(content, additional_kwargs=additional_kwargs or None)


def _create_load_skills_tool():
    """创建固定暴露给 Supervisor 的 Skill 正文加载工具。"""

    @tool(
        "load_skills",
        description="加载当前技能目录里的完整 Skill 正文。仅能传入当前 catalog 中可见的 skill_id；一次最多 3 个。",
    )
    def load_skills(
        skill_ids: Annotated[list[str], "来自当前技能目录的 skill_id 列表，一次最多 3 个。"],
        reason: Annotated[Optional[str], "为什么要加载这些技能（可选，便于调试）。"] = None,
        state: Annotated[Dict[str, Any], InjectedState] = None,
        tool_call_id: Annotated[str, InjectedToolCallId] = "load_skills",
    ) -> Command:
        """加载 Skill 正文并回写会话 registry/context。"""

        from app.services.skill_service import SkillService

        runtime_state = dict(state or {})
        load_result = SkillService.load_skills_for_session(
            skill_ids=list(skill_ids or []),
            user_id=runtime_state.get("user_id"),
            loaded_skill_registry=runtime_state.get("loaded_skill_registry") or {},
            source_turn_id=runtime_state.get("turn_id"),
        )
        next_loaded_skill_registry = load_result.get("loaded_skill_registry") or runtime_state.get("loaded_skill_registry") or {}
        next_allowed_tool_registry = load_result.get("allowed_tool_registry") or runtime_state.get("allowed_tool_registry") or {}
        next_loaded_skill_context = load_result.get("loaded_skill_context") or runtime_state.get("loaded_skill_context")
        merged_state = {
            **runtime_state,
            "loaded_skill_registry": next_loaded_skill_registry,
            "allowed_tool_registry": next_allowed_tool_registry,
            "loaded_skill_context": next_loaded_skill_context,
            "catalog_version": load_result.get("catalog_version") or runtime_state.get("catalog_version"),
            "visible_skill_count": load_result.get("visible_skill_count", runtime_state.get("visible_skill_count", 0)),
        }
        runtime_payload = _build_skill_runtime_state_payload(merged_state, replay_source="live")
        tool_payload = {
            "loaded_skills": load_result.get("loaded_skills") or [],
            "errors": load_result.get("errors") or [],
            "truncated_count": int(load_result.get("truncated_count") or 0),
            "requested_skill_ids": load_result.get("requested_skill_ids") or [],
            "reason": str(reason or "").strip() or None,
        }
        additional_kwargs: Dict[str, Any] = {
            "load_skills_result": tool_payload,
        }
        if runtime_payload is not None:
            additional_kwargs["skill_runtime"] = runtime_payload

        return Command(
            update={
                "loaded_skill_registry": next_loaded_skill_registry,
                "allowed_tool_registry": next_allowed_tool_registry,
                "loaded_skill_context": next_loaded_skill_context,
                "messages": [
                    ToolMessage(
                        content=json.dumps(tool_payload, ensure_ascii=False),
                        tool_call_id=str(tool_call_id or "load_skills"),
                        name="load_skills",
                        additional_kwargs=additional_kwargs,
                    )
                ],
            }
        )

    return load_skills


def _get_supervisor_tool_entries() -> list[Dict[str, Any]]:
    """构建 Supervisor 简单工具候选条目。"""

    entries = _get_common_tool_entries()
    progressive_mode = False
    knowledge_available = False
    web_available = False

    try:
        from app.services.skill_service import SkillService

        progressive_mode = SkillService.resolve_runtime_mode() == SkillService.SKILL_RUNTIME_MODE_PROGRESSIVE
    except Exception as exc:
        logger.warning("Supervisor 运行模式解析失败，按非 progressive 继续: %s", exc)

    try:
        from app.ai.tools.chatTools import fig_inter

        entries.append(_build_tool_entry(fig_inter, {"group:chart"}))
        logger.debug("Supervisor 工具: 已加载 fig_inter")
    except Exception as exc:
        logger.warning("Supervisor 绘图工具加载失败: %s", exc)

    try:
        from app.ai.tools.ragflow_tool import knowledge_search, is_ragflow_configured

        if is_ragflow_configured():
            knowledge_available = True
            entries.append(
                _build_tool_entry(
                    knowledge_search,
                    {"group:knowledge"},
                    runtime_visibility="catalog_after_load" if progressive_mode else "always",
                )
            )
            logger.debug("Supervisor 工具: 已加载 knowledge_search")
    except Exception as exc:
        logger.warning("Supervisor 知识库工具加载失败: %s", exc)

    try:
        from app.ai.tools.chatTools import search_tool

        if search_tool is not None:
            web_available = True
            entries.append(_build_tool_entry(search_tool, {"group:web"}))
            logger.debug("Supervisor 工具: 已加载 TavilySearch 联网搜索")
        else:
            logger.info(
                "联网搜索未加入 Supervisor: search_tool 未加载（请检查 TAVILY_API_KEY 或安装 langchain-tavily）"
            )
    except Exception as exc:
        logger.warning("Supervisor 联网搜索工具加载失败: %s", exc)

    try:
        from app.ai.agents.research_subagent import research_subagent

        if knowledge_available or web_available:
            entries.append(
                _build_tool_entry(
                    research_subagent,
                    {"group:research", "research:unified"},
                    runtime_visibility="catalog_after_load" if progressive_mode else "always",
                )
            )
            logger.debug("Supervisor 工具: 已加载统一 research_subagent")
    except Exception as exc:
        logger.warning("Supervisor 研究子代理加载失败: %s", exc)

    try:
        if progressive_mode:
            entries.append(_build_tool_entry(_create_load_skills_tool(), {"group:skill", "runtime:progressive"}))
            logger.debug("Supervisor 工具: 已加载 progressive load_skills")
    except Exception as exc:
        logger.warning("Supervisor load_skills 工具加载失败: %s", exc)

    return entries


def _get_runtime_visible_supervisor_tools(
    state: Optional[Dict[str, Any]] = None,
    *,
    tool_entries: Optional[list[Dict[str, Any]]] = None,
) -> list[Any]:
    """获取当前轮对 Supervisor 模型可见的简单工具。"""

    entries = list(tool_entries) if tool_entries is not None else _get_supervisor_tool_entries()
    runtime_visible_entries = _apply_runtime_tool_visibility_policy(entries, state, agent_name="supervisor")
    return _apply_tool_governance_policy(runtime_visible_entries, agent_name="supervisor")


def _get_supervisor_handoff_tool_entries() -> list[Dict[str, Any]]:
    """获取 Supervisor 的专家委派工具条目。"""

    progressive_mode = False
    try:
        from app.services.skill_service import SkillService

        progressive_mode = SkillService.resolve_runtime_mode() == SkillService.SKILL_RUNTIME_MODE_PROGRESSIVE
    except Exception as exc:
        logger.warning("Supervisor handoff 运行模式解析失败，按非 progressive 继续: %s", exc)

    entries: list[Dict[str, Any]] = []
    for agent_type, desc in AGENT_DESCRIPTIONS.items():
        tool_obj = _create_task_handoff_tool(agent_type, desc)
        entries.append(
            _build_tool_entry(
                tool_obj,
                {"group:handoff", f"handoff:{agent_type}"},
                runtime_visibility="catalog_after_load" if progressive_mode else "always",
            )
        )

    return entries


def _get_runtime_visible_supervisor_handoff_tools(
    state: Optional[Dict[str, Any]] = None,
    *,
    tool_entries: Optional[list[Dict[str, Any]]] = None,
) -> list[Any]:
    """获取当前轮对 Supervisor 模型可见的专家委派工具。"""

    entries = list(tool_entries) if tool_entries is not None else _get_supervisor_handoff_tool_entries()
    runtime_visible_entries = _apply_runtime_tool_visibility_policy(entries, state, agent_name="supervisor")
    return _apply_tool_governance_policy(runtime_visible_entries, agent_name="supervisor")


def _get_supervisor_tools():
    """获取 Supervisor 可执行的简单工具全集。"""

    return _apply_tool_governance_policy(_get_supervisor_tool_entries(), agent_name="supervisor")


def _build_decomposed_goals_for_query(user_query: str) -> list[Dict[str, Any]]:
    """根据用户问题做最小规则拆解，生成活动目标。"""
    state_seed: MultiAgentState = {
        "messages": [HumanMessage(content=str(user_query or "").strip())],
    }
    heuristic_plan = _infer_initial_intent_plan(state_seed)
    raw_goals = [goal for goal in list(heuristic_plan.get("goals") or []) if isinstance(goal, dict)]
    return _normalize_active_goals(raw_goals)


def _has_explicit_multi_goal_markers(user_query: str) -> bool:
    """检测用户是否显式表达“多目标请求”。"""
    text = str(user_query or "").strip()
    if not text:
        return False
    if len(re.findall(r"(?:^|\n)\s*\d+\s*[、\.\)]", text)) >= 2:
        return True
    if "\n" in text and len([line for line in text.splitlines() if line.strip()]) >= 2:
        return True
    lowered = text.lower()
    return any(token in lowered for token in ("然后", "再", "并且", "以及", "同时", "and then"))


def _merge_goal_candidates(
    primary_goals: Sequence[Dict[str, Any]],
    supplemental_goals: Sequence[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    """合并两组 goals，按语义桶去重并保持首见顺序。"""
    merged: list[Dict[str, Any]] = []
    seen_keys: set[str] = set()

    for raw_goal in [*list(primary_goals or []), *list(supplemental_goals or [])]:
        if not isinstance(raw_goal, dict):
            continue
        kind = _normalize_model_goal_kind(str(raw_goal.get("kind") or "general.reply"))
        bucket = _goal_kind_bucket(kind)
        dedupe_key = bucket if bucket != "general" else kind
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        merged.append(
            {
                "goal_id": str(raw_goal.get("goal_id") or "").strip(),
                "order": _parse_non_negative_int(raw_goal.get("order"), default=len(merged) + 1),
                "kind": kind,
                "title": str(raw_goal.get("title") or "").strip() or _default_goal_title(kind),
                "must_answer": bool(raw_goal.get("must_answer", True)),
                "allowed_agents": raw_goal.get("allowed_agents"),
            }
        )

    return _normalize_active_goals(merged)


def _normalize_persisted_chat_role(raw_role: Any) -> str:
    """将落库角色归一为 decompose_goals 输入角色。"""
    normalized = str(raw_role or "").strip().lower()
    if normalized in {"human", "user"}:
        return "user"
    if normalized in {"ai", "assistant"}:
        return "assistant"
    return ""


def _load_recent_persisted_user_visible_messages(
    *,
    thread_id: str,
    user_query: str,
    turn_limit: int = DECOMPOSE_GOALS_RECENT_TURN_LIMIT,
) -> list[BaseMessage]:
    """读取已落库且面向用户可见的最近对话窗口（user/assistant）。"""
    normalized_thread_id = str(thread_id or "").strip()
    if not normalized_thread_id:
        return []

    try:
        from app.db.session import get_db_context
        from app.repositories import chat_repo

        with get_db_context() as db:
            persisted_messages = chat_repo.get_messages_by_thread(
                db,
                normalized_thread_id,
                limit=200,
                exclude_intermediate=True,
            )
    except Exception as exc:
        logger.warning("decompose_goals_persisted_messages_load_failed: %s", exc)
        return []

    user_visible_messages: list[Dict[str, str]] = []
    for item in persisted_messages or []:
        role = _normalize_persisted_chat_role(getattr(item, "role", ""))
        if role not in {"user", "assistant"}:
            continue
        content = _normalize_text_content(getattr(item, "content", ""))
        if not content:
            continue
        if role == "assistant" and AgentOutputParser.should_filter_content(content):
            continue
        user_visible_messages.append({"role": role, "content": content})

    normalized_query = str(user_query or "").strip()
    if user_visible_messages and user_visible_messages[-1]["role"] == "user":
        latest_user_content = str(user_visible_messages[-1].get("content") or "").strip()
        if normalized_query and latest_user_content == normalized_query:
            user_visible_messages = user_visible_messages[:-1]

    turns: list[list[Dict[str, str]]] = []
    current_turn: list[Dict[str, str]] = []
    for message in user_visible_messages:
        if message["role"] == "user":
            if current_turn:
                turns.append(current_turn)
            current_turn = [message]
            continue

        if not current_turn:
            continue
        current_turn.append(message)
        turns.append(current_turn)
        current_turn = []

    if current_turn:
        turns.append(current_turn)

    selected_turns = turns[-max(turn_limit, 0) :]
    flattened_messages: list[BaseMessage] = []
    for turn in selected_turns:
        for message in turn:
            content = str(message.get("content") or "")
            if message.get("role") == "user":
                flattened_messages.append(HumanMessage(content=content))
            else:
                flattened_messages.append(AIMessage(content=content))

    return flattened_messages


def _build_decompose_goals_state_seed(
    *,
    user_query: str,
    runtime_state: Optional[MultiAgentState] = None,
) -> MultiAgentState:
    """构建 decompose_goals 的规划态输入（user_query + persisted messages）。"""
    thread_id = ""
    if isinstance(runtime_state, dict):
        thread_id = str(runtime_state.get("thread_id") or "").strip()

    messages = _load_recent_persisted_user_visible_messages(
        thread_id=thread_id,
        user_query=user_query,
    )
    return {
        "messages": messages,
        "semantic_payload": {"user_query": str(user_query or "")},
    }


def _should_reconcile_single_goal(
    primary_goals: Sequence[Dict[str, Any]],
    fallback_goals: Sequence[Dict[str, Any]],
) -> bool:
    """单目标场景下，若模型给出 general 而规则兜底更具体，则执行纠偏。"""
    normalized_primary = _normalize_active_goals(primary_goals)
    normalized_fallback = _normalize_active_goals(fallback_goals)
    if _count_must_answer_goals(normalized_primary) != 1:
        return False
    if _count_must_answer_goals(normalized_fallback) != 1:
        return False

    primary_bucket = _goal_kind_bucket(str(normalized_primary[0].get("kind") or "general.reply"))
    fallback_bucket = _goal_kind_bucket(str(normalized_fallback[0].get("kind") or "general.reply"))
    return primary_bucket == "general" and fallback_bucket != "general"


def _history_has_recent_data_query_context(messages: Sequence[BaseMessage]) -> bool:
    """判断最近用户可见历史是否已形成 data.query 上下文。"""
    latest_user_query = _extract_latest_human_content(messages)
    if not latest_user_query:
        return False

    prior_goals = _normalize_active_goals(_build_decomposed_goals_for_query(latest_user_query))
    return any(
        bool(goal.get("must_answer", True)) and _goal_kind_bucket(str(goal.get("kind") or "general.reply")) == "data"
        for goal in prior_goals
    )


def _has_structured_data_supplement_signal(frame: Optional[Dict[str, Any]]) -> bool:
    """补充回合需带有结构化图表/维度/时间/筛选信号，避免确认短句误扩。"""
    if not isinstance(frame, dict):
        return False
    return any(
        [
            str(frame.get("chart_type") or "").strip(),
            str(frame.get("org_level") or "").strip(),
            str(frame.get("time_range") or "").strip(),
            bool(frame.get("dimensions")),
            bool(frame.get("filters")),
        ]
    )


def _build_single_data_query_goal() -> list[Dict[str, Any]]:
    """构造单一 data.query 纠偏目标。"""
    return _normalize_active_goals(
        [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "data.query",
                "title": "数据查询",
                "must_answer": True,
            }
        ]
    )


def _should_reconcile_data_supplement_goal(
    user_query: str,
    *,
    primary_goals: Sequence[Dict[str, Any]],
    fallback_goals: Sequence[Dict[str, Any]],
    history_messages: Sequence[BaseMessage],
) -> bool:
    """补图/补维度/补时间等短回合若承接上一轮问数，应纠偏回 data.query。"""
    normalized_primary = _normalize_active_goals(primary_goals)
    normalized_fallback = _normalize_active_goals(fallback_goals)
    if _count_must_answer_goals(normalized_primary) != 1:
        return False
    if _count_must_answer_goals(normalized_fallback) != 1:
        return False

    primary_bucket = _goal_kind_bucket(str(normalized_primary[0].get("kind") or "general.reply"))
    fallback_bucket = _goal_kind_bucket(str(normalized_fallback[0].get("kind") or "general.reply"))
    if primary_bucket != "general" or fallback_bucket not in {"general", "chart"}:
        return False

    if not _history_has_recent_data_query_context(history_messages):
        return False

    turn_act, _reason, current_frame = classify_turn_act_from_text(
        user_query,
        has_prior_context=True,
    )
    return turn_act == TURN_ACT_SUPPLEMENT and _has_structured_data_supplement_signal(current_frame)


def _resolve_decomposed_goals_for_query(
    user_query: str,
    *,
    llm: Any = None,
    runtime_state: Optional[MultiAgentState] = None,
) -> Tuple[list[Dict[str, Any]], str]:
    """生成 decompose_goals 产物：优先模型规划，失败时回退规则拆解。"""
    normalized_query = str(user_query or "").strip()
    fallback_goals = _build_decomposed_goals_for_query(normalized_query)

    if _has_explicit_multi_goal_markers(normalized_query) and _count_must_answer_goals(fallback_goals) >= 2:
        return fallback_goals, "explicit_multi_goal_fast_path"

    state_seed = _build_decompose_goals_state_seed(
        user_query=normalized_query,
        runtime_state=runtime_state,
    )
    history_messages = [message for message in list(state_seed.get("messages") or []) if isinstance(message, BaseMessage)]

    if llm is None:
        if _should_reconcile_data_supplement_goal(
            normalized_query,
            primary_goals=fallback_goals,
            fallback_goals=fallback_goals,
            history_messages=history_messages,
        ):
            return _build_single_data_query_goal(), "supervisor_rule_based+supplement_data_reconcile"
        return fallback_goals, "supervisor_rule_based"

    planner_settings = _resolve_intent_planner_settings(state_seed)
    planner_mode = _normalize_intent_mode(planner_settings.get("intent_mode"), default="model_primary")

    try:
        intent_plan = _build_planner_intent_plan(
            state_seed,
            llm=llm,
            mode=planner_mode,
        )
    except Exception as exc:
        logger.warning("decompose_goals_model_failed_fallback_to_rule: %s", exc)
        if _should_reconcile_data_supplement_goal(
            normalized_query,
            primary_goals=fallback_goals,
            fallback_goals=fallback_goals,
            history_messages=history_messages,
        ):
            return _build_single_data_query_goal(), "supervisor_rule_based+supplement_data_reconcile"
        return fallback_goals, "supervisor_rule_based"

    plan_goals = [
        goal
        for goal in list((intent_plan or {}).get("goals") or [])
        if isinstance(goal, dict)
    ]
    normalized_plan_goals = _normalize_active_goals(plan_goals)
    source = str((intent_plan or {}).get("source") or planner_mode or "model_primary")

    if _has_explicit_multi_goal_markers(normalized_query) and _count_must_answer_goals(normalized_plan_goals) < 2:
        reconciled_goals = _merge_goal_candidates(normalized_plan_goals, fallback_goals)
        return reconciled_goals, f"{source}+rule_reconcile"

    if _should_reconcile_data_supplement_goal(
        normalized_query,
        primary_goals=normalized_plan_goals,
        fallback_goals=fallback_goals,
        history_messages=history_messages,
    ):
        return _build_single_data_query_goal(), f"{source}+supplement_data_reconcile"

    if _should_reconcile_single_goal(normalized_plan_goals, fallback_goals):
        return _normalize_active_goals(fallback_goals), f"{source}+single_goal_reconcile"

    return normalized_plan_goals, source


@tool("decompose_goals", description="将复合请求拆解为结构化目标列表，供 Supervisor 路由与门禁使用")
def decompose_goals(
    user_query: Annotated[str, "用户原始请求（可包含复合目标）"],
    state: Annotated[Dict[str, Any], InjectedState] = None,
) -> str:
    """将用户请求拆解为 goals（规则兜底版本），返回标准 JSON。"""
    goals, source = _resolve_decomposed_goals_for_query(
        str(user_query or ""),
        runtime_state=state,
    )
    payload = {
        "action": "decompose_goals",
        "source": source,
        "goals": goals,
    }
    return json.dumps(payload, ensure_ascii=False)


def _create_decompose_goals_tool(llm: Any):
    """创建模型优先的 decompose_goals 工具。"""

    @tool("decompose_goals", description="将复合请求拆解为结构化目标列表，供 Supervisor 路由与门禁使用")
    def _decompose_goals_with_model(
        user_query: Annotated[str, "用户原始请求（可包含复合目标）"],
        state: Annotated[Dict[str, Any], InjectedState] = None,
    ) -> str:
        goals, source = _resolve_decomposed_goals_for_query(
            str(user_query or ""),
            llm=llm,
            runtime_state=state,
        )
        payload = {
            "action": "decompose_goals",
            "source": source,
            "goals": goals,
        }
        return json.dumps(payload, ensure_ascii=False)

    return _decompose_goals_with_model


def _create_task_handoff_tool(agent_name: str, description: str):
    """创建 Handoff 工具。"""

    name = f"assign_to_{agent_name}"

    if agent_name == AgentType.DATA:
        @tool(name, description=description)
        def handoff_tool(
            frame: Annotated[Dict[str, Any], "data.query 结构化合同（必填）：至少包含 query_text；query_text 必须是自然语言子任务描述，禁止直接填写 SQL；可选携带 metric/time_range/dimensions/chart_type/org_level/filters/query_shape/ranking"],
            turn_act_hint: Annotated[Optional[str], "回合行为提示（可选）：NEW_QUERY/SUPPLEMENT/CORRECTION/CONFIRM"] = None,
        ) -> str:
            """将数据查询子任务委派给 data_expert。"""
            result = HandoffResult(
                target_agent=agent_name,
                frame=frame if isinstance(frame, dict) else None,
                turn_act_hint=str(turn_act_hint or "").strip() or None,
            )
            return result.model_dump_json(ensure_ascii=False, exclude_none=True)

        return handoff_tool

    @tool(name, description=description)
    def handoff_tool(
        task_description: Annotated[str, "详细描述下一个专家需要完成的任务，包含所有相关上下文和指令"],
        frame: Annotated[Optional[Dict[str, Any]], "结构化上下文（可选）：metric/time/dimensions 或 todo_action/todo_fields/tool_observations"] = None,
        turn_act_hint: Annotated[Optional[str], "回合行为提示（可选）：NEW_QUERY/SUPPLEMENT/CORRECTION/CONFIRM"] = None,
    ) -> str:
        """将任务委派给指定的专家 Agent。返回 JSON 格式的委派指令。"""
        result = HandoffResult(
            target_agent=agent_name,
            task_description=task_description,
            frame=frame if isinstance(frame, dict) else None,
            turn_act_hint=str(turn_act_hint or "").strip() or None,
        )
        return result.model_dump_json(ensure_ascii=False, exclude_none=True)

    return handoff_tool


async def _preprocess_multimodal(state: MultiAgentState) -> dict:
    """预处理节点：验证消息、执行输入护栏、注入系统上下文。"""
    messages = state.get("messages", [])
    if not messages:
        return {}
    
    writer = get_stream_writer()

    updates = {
        "_graph_type": "multi_agent",
        "runtime_recovery_state": _build_runtime_recovery_state(
            state,
            fallback_route="none",
            fallback_triggered=False,
            plugin_lifecycle_status=_resolve_plugin_lifecycle_status(state),
        ),
        "turn_id": f"{state.get('thread_id') or 'thread'}:{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
    }
    
    # 注意：临时状态（pending_handoff 等）在 postprocess 节点统一清理
    # 详见：_postprocess 函数的状态清理逻辑
    
    # ========== 1. 消息验证与修复 ==========
    # 【补丁代码】修复 DeepSeek Reasoner 的 reasoning_content 缺失问题
    # 详见: app.ai.message_utils.fix_deepseek_reasoning
    # 原因: DeepSeek R1 要求历史消息必须包含 reasoning_content 字段
    # 方案: 已将修复逻辑封装为独立函数 validate_messages，保持代码整洁
    # 兼容策略：待 DeepSeek 官方修复 reasoning_content 历史消息校验后再评估移除
    original_count = len(messages)
    validated = _validate_state_messages_for_runtime(state, messages)
    
    if len(validated) != original_count or bool(state.get("enable_thinking")):
        logger.debug(
            "预处理节点: 消息验证完成, 消息数 %d -> %d",
            original_count,
            len(validated),
        )
        updates["messages"] = validated
        messages = validated

    last_msg = messages[-1]
    content = str(getattr(last_msg, "content", ""))
    
    from langchain_core.messages import HumanMessage
    if isinstance(last_msg, HumanMessage):
        from app.ai.guardrails import guardrail_runner
        
        passed, sanitized_content, reason = await guardrail_runner.validate_input(content)
        
        if not passed:
            logger.warning("护栏拦截: %s", reason)
            emit_status(writer, message=f"安全检查: {reason}", node="preprocess")
        if sanitized_content and sanitized_content != content:
            logger.info("护栏: 输入已脱敏处理")
            content = sanitized_content
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
    context_parts = [f"当前时间: {current_time}"]

    current_todo_id = state.get("current_todo_id")
    if current_todo_id:
        context_parts.append(
            "当前选中待办ID: "
            f"{current_todo_id}。若用户要求“描述里补充/添加外部信息（天气、股价等）”，"
            "应优先按更新该待办处理。"
        )

    memory_context = str(state.get("memory_context") or "").strip()
    if memory_context:
        context_parts.append(memory_context)

    response_guidance_contract = state.get("response_guidance_contract")
    rendered_response_guidance = response_policy_service.render_response_guidance_contract(response_guidance_contract)
    if rendered_response_guidance:
        context_parts.append(rendered_response_guidance)

    updates["system_context"] = "\n".join(context_parts)

    normalized_user_query = _normalize_text_content(content)
    if isinstance(last_msg, HumanMessage) and normalized_user_query:
        fast_lane_goals, fast_lane_source = _resolve_decomposed_goals_for_query(
            normalized_user_query,
            runtime_state=state,
        )
        fast_lane_goal_buckets = {
            _goal_kind_bucket(str(goal.get("kind") or ""))
            for goal in list(fast_lane_goals or [])
            if bool(goal.get("must_answer", True))
        }
        if fast_lane_source == "explicit_multi_goal_fast_path" and "data" in fast_lane_goal_buckets:
            updates["decomposed_goals"] = list(fast_lane_goals)
            emit_plan_ready(
                writer,
                _build_active_goal_plan(state, runtime_goals=fast_lane_goals, source=fast_lane_source),
                node="preprocess",
            )

            compiled_data_handoff = next(
                (
                    _build_compiled_data_goal_handoff(state={**state, **updates}, goal=goal)
                    for goal in fast_lane_goals
                    if _goal_kind_bucket(str(goal.get("kind") or "")) == "data"
                ),
                None,
            )
            if compiled_data_handoff:
                updates["pending_handoff"] = compiled_data_handoff
                updates["handoff_queue"] = []
                updates["completed_handoffs"] = []
                updates["handoff_execution_trace"] = []
                updates["multi_intent_mode"] = bool(len(fast_lane_goals) >= 2)

            if "external" in fast_lane_goal_buckets:
                external_query = next(
                    (
                        segment
                        for segment in _split_user_query_for_goal_compile(normalized_user_query)
                        if _infer_primary_goal_bucket_from_query_text(segment) == "external"
                    ),
                    normalized_user_query,
                )
                try:
                    from app.ai.tools.chatTools import search_tool

                    if search_tool is not None:
                        emit_tool_start(writer, "tavily_search", {"query": external_query}, node="preprocess")
                        if hasattr(search_tool, "ainvoke"):
                            search_result = await search_tool.ainvoke({"query": external_query})
                        else:
                            search_result = await asyncio.to_thread(search_tool.invoke, {"query": external_query})

                        tool_content = search_result if isinstance(search_result, str) else json.dumps(search_result, ensure_ascii=False)
                        preprocess_messages = list(updates.get("messages") or [])
                        preprocess_messages.append(
                            ToolMessage(
                                content=tool_content,
                                tool_call_id="preprocess-fast-lane-external",
                                name="tavily_search",
                            )
                        )
                        updates["messages"] = preprocess_messages

                        external_preview = _extract_tavily_display_markdown(tool_content)
                        if external_preview:
                            emit_status(
                                writer,
                                message="已完成可直答子问题，先返回当前结果，剩余问题继续处理中...",
                                node="preprocess",
                            )
                            emit_token(writer, external_preview, node="preprocess")
                    else:
                        logger.info("预处理 fast lane 跳过外部预取：search_tool 未配置")
                except Exception as exc:
                    logger.warning("预处理 fast lane 外部预取失败，已回退主链: %s", exc)
    
    updates["skill_candidates"] = []
    updates["selected_skill_ids"] = []
    updates["skill_context"] = None
    updates["skill_injection_meta"] = None
    updates["skill_catalog_manifest"] = []
    updates["skill_catalog_context"] = None
    updates["catalog_version"] = "-"
    updates["visible_skill_count"] = 0
    updates["allowed_tool_registry"] = _normalize_allowed_tool_registry(state.get("allowed_tool_registry") or {})

    try:
        from app.services.skill_service import SkillService

        runtime_mode = SkillService.resolve_runtime_mode()
        loaded_skill_registry = state.get("loaded_skill_registry") or {}
        if not isinstance(loaded_skill_registry, dict):
            loaded_skill_registry = {}

        if not loaded_skill_registry:
            restored_registry = _restore_loaded_skill_registry_from_messages(messages)
            if restored_registry:
                loaded_skill_registry = restored_registry
                updates["loaded_skill_registry"] = restored_registry
                logger.info(
                    "预处理节点: 已从历史 AIMessage.skill_runtime 恢复 loaded_skill_registry, count=%d",
                    len(restored_registry),
                )

        if loaded_skill_registry and not state.get("loaded_skill_context"):
            context_payload = SkillService.build_loaded_skill_context_from_registry(loaded_skill_registry)
            updates["loaded_skill_context"] = context_payload.get("loaded_skill_context") or None
            missing_skills = context_payload.get("missing_skills") or []
            if missing_skills:
                logger.warning("预处理节点: loaded_skill_context 回源缺失 skills=%s", missing_skills)
                emit_status(
                    writer,
                    message="部分已加载技能版本缺失，已按可回源正文继续本轮推理。",
                    node="preprocess",
                )

        current_allowed_tool_registry = _normalize_allowed_tool_registry(state.get("allowed_tool_registry") or {})
        if not current_allowed_tool_registry:
            restored_allowed_tools = _restore_allowed_tool_registry_from_messages(messages)
            if restored_allowed_tools:
                current_allowed_tool_registry = restored_allowed_tools
        if loaded_skill_registry and not current_allowed_tool_registry:
            current_allowed_tool_registry = _normalize_allowed_tool_registry(
                SkillService.build_allowed_tool_registry_from_loaded_registry(loaded_skill_registry)
            )
        updates["allowed_tool_registry"] = current_allowed_tool_registry

        if runtime_mode == SkillService.SKILL_RUNTIME_MODE_PROGRESSIVE:
            catalog_payload = SkillService.build_skill_catalog_manifest(user_id=state.get("user_id"))
            manifest = list(catalog_payload.get("manifest") or [])
            catalog_context, catalog_meta = SkillService.format_skill_catalog_as_context_with_meta(manifest)
            visible_skill_count = int(catalog_payload.get("visible_skill_count") or len(manifest))

            updates["skill_catalog_manifest"] = manifest
            updates["skill_catalog_context"] = catalog_context or None
            updates["catalog_version"] = str(catalog_payload.get("catalog_version") or "-")
            updates["visible_skill_count"] = visible_skill_count
            updates["skill_injection_meta"] = {
                "runtime_mode": runtime_mode,
                "catalog_build_source": catalog_payload.get("catalog_build_source"),
                **catalog_meta,
            }

            logger.info(
                "预处理节点: progressive skill catalog 已装载, visible_skill_count=%d, catalog_version=%s",
                visible_skill_count,
                updates["catalog_version"],
            )
            emit_status(
                writer,
                message=f"已预装 {visible_skill_count} 个技能目录，可按需加载。",
                node="preprocess",
            )
        elif content:
            debug_payload = SkillService.search_skills_debug(
                content,
                top_k=2,
                auto_only=True,
                user_id=state.get("user_id"),
            )
            skill_candidates = debug_payload.get("skill_candidates", [])
            selected_skill_ids = debug_payload.get("selected_skill_ids", [])
            skill_context = debug_payload.get("context_preview", "")
            skill_injection_meta = debug_payload.get("skill_injection_meta", {})

            updates["skill_candidates"] = skill_candidates
            updates["selected_skill_ids"] = selected_skill_ids
            updates["skill_context"] = skill_context or None
            updates["skill_injection_meta"] = {
                "runtime_mode": runtime_mode,
                **(skill_injection_meta if isinstance(skill_injection_meta, dict) else {}),
            }

            if selected_skill_ids:
                logger.info(
                    "预处理节点: hybrid 技能检索命中 %d 个技能: %s", len(selected_skill_ids), selected_skill_ids
                )
                emit_status(
                    writer,
                    message=f"已加载 {len(selected_skill_ids)} 个相关技能: {selected_skill_ids}",
                    node="preprocess",
                )
            else:
                logger.info(
                    "预处理节点: hybrid 技能检索完成但未命中，候选=%d",
                    len(skill_candidates),
                )
    except Exception as e:
        from app.services.skill_service import SkillService

        if SkillService.resolve_runtime_mode() == SkillService.SKILL_RUNTIME_MODE_PROGRESSIVE:
            logger.warning("预处理节点: progressive skill catalog 构建失败 - %s", e)
            updates["skill_injection_meta"] = {
                "runtime_mode": SkillService.SKILL_RUNTIME_MODE_PROGRESSIVE,
                "catalog_warning": str(e),
                "visible_skill_count": 0,
            }
            emit_status(
                writer,
                message="技能目录构建失败，本轮将以无 catalog 继续，不回退 hybrid 注入。",
                node="preprocess",
            )
        else:
            logger.warning("预处理节点: 技能检索失败 - %s", e)
    
    attachment_manifest = normalize_attachment_manifest_entries(state.get("attachment_manifest"))
    lightweight_probe = normalize_lightweight_probe_entries(state.get("lightweight_probe"))
    attachment_planning = None
    if attachment_manifest:
        user_query = _resolve_semantic_user_query(state)
        active_goals = [
            goal
            for goal in _build_decomposed_goals_for_query(user_query)
            if isinstance(goal, dict) and bool(goal.get("must_answer", True))
        ]
        goal_buckets = list(dict.fromkeys(
            _goal_kind_bucket(str(goal.get("kind") or "general.reply"))
            for goal in active_goals
        ))
        attachment_planning = build_attachment_planning_contract(
            user_query=user_query,
            goal_buckets=goal_buckets,
            active_goal_count=len(active_goals),
            has_explicit_multi_goal=_has_explicit_multi_goal_markers(user_query),
            has_todo_context=state.get("current_todo_id") is not None or bool(state.get("pending_operation")),
            attachment_manifest=attachment_manifest,
            lightweight_probe=lightweight_probe,
        )
    if attachment_planning:
        planning_context = render_attachment_planning_context(
            attachment_manifest,
            lightweight_probe,
            attachment_planning,
        )
        updates["attachment_manifest"] = attachment_manifest
        updates["lightweight_probe"] = lightweight_probe
        updates["attachment_planning"] = attachment_planning
        context_parts.append(planning_context)
        updates["system_context"] = "\n".join(context_parts)
    logger.info("jjk-multi-agent: 预处理节点: 更新状态 - %s", updates)
    return updates


async def create_multi_agent_graph(
    checkpointer=None,
    enable_thinking: bool = False,
    model_id: str = None
):
    """创建多智能体 Supervisor 图。"""

    llm = get_scene_llm(
        scene_key=SCENE_KEY_MULTI_AGENT_SUPERVISOR,
        force_thinking=enable_thinking,
        model_id=model_id,
    )

    handoff_tool_entries = _get_supervisor_handoff_tool_entries()
    handoff_tools = _apply_tool_governance_policy(handoff_tool_entries, agent_name="supervisor")

    supervisor_simple_tool_entries = _get_supervisor_tool_entries()
    supervisor_simple_tools = _apply_tool_governance_policy(supervisor_simple_tool_entries, agent_name="supervisor")
    decompose_goals_tool = _create_decompose_goals_tool(llm)
    supervisor_wrap_tool_call, supervisor_awrap_tool_call = _build_runtime_tool_call_wrapper(
        handoff_tool_entries + supervisor_simple_tool_entries,
        agent_name="supervisor",
    )
    supervisor_tool_node = ToolNode(
        handoff_tools + [decompose_goals_tool] + supervisor_simple_tools,
        wrap_tool_call=supervisor_wrap_tool_call,
        awrap_tool_call=supervisor_awrap_tool_call,
    )

    def _resolve_supervisor_model(state: MultiAgentState, _runtime):
        visible_handoff_tools = _get_runtime_visible_supervisor_handoff_tools(
            state=state,
            tool_entries=handoff_tool_entries,
        )
        visible_simple_tools = _get_runtime_visible_supervisor_tools(
            state=state,
            tool_entries=supervisor_simple_tool_entries,
        )
        bound_tools = visible_handoff_tools + [decompose_goals_tool] + visible_simple_tools
        logger.debug(
            "Supervisor 运行时工具绑定: %s",
            [_resolve_tool_name(tool_obj) for tool_obj in bound_tools],
        )
        return llm.bind_tools(bound_tools)

    supervisor_agent = create_react_agent(
        _resolve_supervisor_model,
        supervisor_tool_node,
        prompt=SUPERVISOR_PROMPT,
        name="supervisor",
    )
    
    from app.ai.workflow.data_graph import create_data_graph
    data_graph_app = create_data_graph(
        model=llm,
        enable_thinking=enable_thinking,
        model_id=model_id,
        checkpointer=checkpointer
    )
    
    from app.ai.workflow.todo_graph import create_todo_graph
    todo_graph_app = create_todo_graph(
        model=llm, 
        enable_thinking=enable_thinking,
        checkpointer=checkpointer 
    )

    def _postprocess(state: MultiAgentState) -> dict:
        """后处理节点：调试日志 + 保存对话到数据库 + 清理缓存。"""
        messages = state.get("messages", [])
        user_id = state.get("user_id")
        thread_id = state.get("thread_id")
        
        logger.debug("多智能体后处理: messages=%d, thread_id=%s, user_id=%s", len(messages), thread_id, user_id)

        if not thread_id:
            logger.warning("后处理节点: 缺少 thread_id，跳过保存")
            return {}
        
        if not messages:
            logger.warning("后处理节点: 消息为空，跳过保存")
            return {}
        
        try:
            from app.db.session import get_db_context
            from app.repositories import chat_repo
            from langchain_core.messages import HumanMessage, AIMessage
            
            filtered_messages = [
                msg for msg in messages 
                if not (isinstance(msg, HumanMessage) and msg.name)
            ]
            
            has_ai_message = any(isinstance(msg, AIMessage) for msg in filtered_messages)
            if not has_ai_message:
                logger.info("后处理节点: 消息列表中没有 AI 回复，跳过保存")
            else:
                with get_db_context() as db:
                    chat_repo.save_conversation_from_messages(db, user_id, thread_id, filtered_messages)
                logger.info(
                    "多智能体对话已保存: thread_id=%s, user_id=%s, messages_count=%d", 
                    thread_id, user_id, len(messages)
                )
        except Exception as e:
            logger.error("多智能体后处理-保存失败: %s", e, exc_info=True)
        
        try:
            from app.ai.tools.chatTools import cleanup_thread_dataframes
            cleanup_thread_dataframes(thread_id)
            logger.debug("多智能体后处理: DataFrame 缓存已清理")
        except Exception as e:
            logger.warning("多智能体后处理-清理缓存失败: %s", e)
        
        return {
            "pending_handoff": None,
            "handoff_queue": [],
            "completed_handoffs": [],
            "handoff_execution_trace": [],
            "multi_intent_mode": False,
            "pending_operation": None,
            "user_confirmed": None,
            "quick_mode": None,
            "evaluation": None,
            "evaluation_route": "postprocess",
            "iteration_count": 0,
            "detected_intent": None,
            "intent_route": None,
            "intent_mode": "model_primary",
            "attachment_manifest": [],
            "lightweight_probe": [],
            "attachment_planning": None,
            "skill_candidates": [],
            "selected_skill_ids": [],
            "skill_context": None,
            "skill_injection_meta": None,
            "skill_catalog_manifest": [],
            "skill_catalog_context": None,
            "catalog_version": None,
            "visible_skill_count": 0,
            "allowed_tool_registry": {},
            "turn_id": None,
            "decomposed_goals": [],
            "task_graph": None,
            "task_runs": [],
            "deliverables": [],
            "coverage_report": None,
            "final_answer": None,
            "delivery_meta": {},
            "coverage_retry_count": 0,
            "coverage_gate_route": "final_composer",
            "coverage_partial_gap_allowed": False,
            "router_result_v2": {},

            "runtime_recovery_state": _build_runtime_recovery_state(
                state,
                fallback_route="none",
                fallback_triggered=False,
                plugin_lifecycle_status=_resolve_plugin_lifecycle_status(state),
            ),
        }

    def _evaluate_expert_work(state: MultiAgentState) -> dict:
        """评估专家工作节点：支持 handoff 队列串行消费与复合任务汇总收口。"""
        decision = _evaluate_handoff_progress(state)
        route = str(decision.get("evaluation_route") or "postprocess")

        writer = get_stream_writer()
        if route in WORKFLOW_AGENT_NODES:
            pending_handoff = decision.get("pending_handoff") or {}
            target_agent = pending_handoff.get("target_agent") or "unknown"
            queue_left = len(decision.get("handoff_queue") or [])
            emit_status(
                writer,
                message=f"复合任务继续执行：即将委派 {target_agent}，剩余队列 {queue_left} 项。",
                node="evaluate",
            )
            if _is_sse_delivery_events_v2_enabled():
                emit_task_started(
                    writer,
                    {
                        "target_agent": target_agent,
                        "task_description": _resolve_handoff_display_text(pending_handoff, limit=220),
                        "queue_left": queue_left,
                    },
                    node="evaluate",
                )
        elif route == "summarize":
            emit_status(
                writer,
                message="复合任务子步骤已完成，正在统一汇总输出...",
                node="evaluate",
            )
        elif route == "coverage_gate":
            emit_status(
                writer,
                message="复合任务子步骤已完成，正在执行完整性检查...",
                node="evaluate",
            )
            if _is_sse_delivery_events_v2_enabled():
                latest_completed = (decision.get("completed_handoffs") or [])[-1:] or []
                if latest_completed:
                    emit_task_finished(
                        writer,
                        {
                            "target_agent": latest_completed[0].get("target_agent"),
                            "task_description": _resolve_handoff_display_text(latest_completed[0], limit=220),
                        },
                        node="evaluate",
                    )
        elif route == "supervisor":
            emit_status(writer, message="专家工作需要继续，正在协调其他专家...", node="evaluate")

        return decision

    def _coverage_gate_node(state: MultiAgentState) -> dict:
        """覆盖率门禁：保证 must_answer 目标有对应交付物。"""
        if not _is_delivery_orchestrator_v2_enabled():
            return {}

        active_goals = _ensure_active_goals_covers_runtime(state)
        active_goal_plan = _build_active_goal_plan(
            state,
            runtime_goals=active_goals,
            source="coverage_gate_runtime",
        )
        deliverables = _build_delivery_artifacts(state)
        raw_coverage_report = _compute_coverage_report(active_goals, deliverables)
        coverage_report, coverage_valid, coverage_error = validate_coverage_report_contract(raw_coverage_report)
        route_state = _resolve_coverage_gate_route(
            state=state,
            coverage_report=coverage_report,
            active_goals=active_goals,
        )
        route = str(route_state.get("route") or "final_composer")
        partial_gap_allowed = bool(route_state.get("partial_gap_allowed"))
        missing_goals = list(coverage_report.get("missing_goals") or [])
        missing_goal_ids = [str(item.get("goal_id") or "") for item in missing_goals]
        missing_goal_titles = [
            str(item.get("title") or item.get("goal_id") or "未命名目标")
            for item in missing_goals
        ]

        writer = get_stream_writer()
        if route == "final_composer":
            status_message = "已完成问题覆盖检查，正在整理最终答复。"
            if missing_goals and partial_gap_allowed:
                status_message = "检测到专家子任务缺口，已按部分交付策略整理当前可用答复。"
            emit_status(
                writer,
                message=status_message,
                node="coverage_gate",
            )
        elif route == "supervisor":
            emit_status(
                writer,
                message="检测到未覆盖目标，已返回执行层继续补齐。",
                node="coverage_gate",
            )
        else:
            emit_status(
                writer,
                message="未覆盖目标仍未补齐，已输出缺口说明。",
                node="coverage_gate",
            )
        if _is_sse_delivery_events_v2_enabled():
            emit_coverage_check(writer, coverage_report, node="coverage_gate")

        coverage_retry_count = _parse_non_negative_int(route_state.get("coverage_retry_count"), default=0)
        delivery_meta = build_contract_validation_meta(
            existing_meta=state.get("delivery_meta") if isinstance(state.get("delivery_meta"), dict) else {},
            coverage_valid=coverage_valid,
            coverage_error=coverage_error,
        )
        delivery_meta = {
            **delivery_meta,
            "coverage_pass": bool(coverage_report.get("pass")),
            "pending_goal_ids": missing_goal_ids,
            "pending_goal_titles": missing_goal_titles,
            "coverage_retry_count": coverage_retry_count,
            "coverage_retry_exhausted": bool(route_state.get("retry_exhausted")),
            "coverage_partial_gap_allowed": partial_gap_allowed,
        }

        base_state = {
            "decomposed_goals": list(active_goals),
            "deliverables": deliverables,
            "coverage_report": coverage_report,
            "delivery_meta": delivery_meta,
            "coverage_retry_count": coverage_retry_count,
        }

        if route == "supervisor":
            return {
                **base_state,
                "coverage_gate_route": "supervisor",
                "coverage_partial_gap_allowed": False,
                "evaluation": "continue",
                "evaluation_route": "supervisor",
                "pending_handoff": None,
                "handoff_queue": [],
                "system_context": response_policy_service.build_multi_intent_recovery_system_context(
                    str(state.get("system_context") or ""),
                    active_goal_plan,
                    missing_goals,
                ),
            }

        if route == "postprocess":
            blocked_answer = _render_coverage_blocked_message(active_goals, coverage_report)
            return {
                **base_state,
                "messages": [_create_ai_message_with_skill_runtime(blocked_answer, state)],
                "final_answer": blocked_answer,
                "coverage_gate_route": "postprocess",
                "coverage_partial_gap_allowed": False,
                "evaluation": "complete",
                "evaluation_route": "postprocess",
            }

        return {
            **base_state,
            "coverage_gate_route": "final_composer",
            "coverage_partial_gap_allowed": partial_gap_allowed,
        }

    def _final_composer_node(state: MultiAgentState) -> dict:
        """唯一对外出口：生成最终答复并触发 final_answer 事件。"""
        if not _is_delivery_orchestrator_v2_enabled():
            return {}

        active_goals = _ensure_active_goals_covers_runtime(state)
        deliverables = list(state.get("deliverables") or _build_delivery_artifacts(state))
        coverage_report = dict(state.get("coverage_report") or _compute_coverage_report(active_goals, deliverables))
        delivery_meta = dict(state.get("delivery_meta") or {})
        partial_gap_allowed = bool(
            state.get("coverage_partial_gap_allowed")
            or delivery_meta.get("coverage_partial_gap_allowed")
        )
        base_state = {
            "decomposed_goals": list(active_goals),
            "deliverables": deliverables,
            "coverage_report": coverage_report,
        }
        missing_goal_count = len(coverage_report.get("missing_goals") or [])

        if _is_coverage_gate_enforced() and not bool(coverage_report.get("pass")) and not partial_gap_allowed:
            blocked_answer = _render_coverage_blocked_message(active_goals, coverage_report)
            writer = get_stream_writer()
            emit_status(writer, message="覆盖门禁未通过，已阻止最终结论输出。", node="final_composer")
            return {
                **base_state,
                "messages": [_create_ai_message_with_skill_runtime(blocked_answer, state)],
                "final_answer": blocked_answer,
                "delivery_meta": {
                    **delivery_meta,
                    "coverage_pass": False,
                    "missing_goal_count": missing_goal_count,
                    "composer_guard_blocked": True,
                },
                "evaluation": "complete",
                "evaluation_route": "postprocess",
            }

        final_answer = _render_final_answer(active_goals, coverage_report)

        writer = get_stream_writer()
        status_message = "结论已生成，正在返回最终答复。"
        if partial_gap_allowed and not bool(coverage_report.get("pass")):
            status_message = "主问题已完成，专家子任务存在缺口，正在返回当前可用答复。"
        emit_status(writer, message=status_message, node="final_composer")
        if _is_sse_delivery_events_v2_enabled():
            goal_count_initial = len(active_goals)
            goal_count_confirmed = _parse_non_negative_int(
                coverage_report.get("answered_goals"),
                default=max(goal_count_initial - missing_goal_count, 0),
            )
            emit_final_answer(
                writer,
                final_answer,
                meta={
                    "coverage_pass": bool(coverage_report.get("pass")),
                    "missing_goals": len(coverage_report.get("missing_goals") or []),
                    "goal_count": goal_count_initial,
                    "goal_count_initial": goal_count_initial,
                    "goal_count_confirmed": goal_count_confirmed,
                    "missing_goal_count": missing_goal_count,
                },
                node="final_composer",
            )
        else:
            emit_token(writer, final_answer, node="final_composer")

        return {
            **base_state,
            "messages": [_create_ai_message_with_skill_runtime(final_answer, state)],
            "final_answer": final_answer,
            "delivery_meta": {
                **delivery_meta,
                "coverage_pass": bool(coverage_report.get("pass")),
                "missing_goal_count": missing_goal_count,
                "coverage_partial_gap_allowed": partial_gap_allowed,
            },
            "coverage_gate_route": "final_composer",
            "evaluation": "complete",
            "evaluation_route": "postprocess",
        }

    def _summarize_multi_intent(state: MultiAgentState) -> dict:
        """复合任务汇总节点：将 direct tool + 专家执行结果合并为单条总结。"""
        if _is_delivery_orchestrator_v2_enabled():
            return {}

        trace = list(state.get("handoff_execution_trace") or [])
        direct_findings = _build_direct_lookup_findings(state.get("messages", []))
        has_enough_inputs = len(trace) >= 2 or (len(trace) >= 1 and bool(direct_findings))
        if not bool(state.get("multi_intent_mode")) or not has_enough_inputs:
            return {}

        summary_text = _build_multi_intent_summary_content(state)
        writer = get_stream_writer()
        emit_status(writer, message="复合任务汇总完成，正在输出结论...", node="summarize")
        emit_token(writer, summary_text, node="summarize")

        return {
            "messages": [_create_ai_message_with_skill_runtime(summary_text, state)],
            "evaluation": "complete",
            "evaluation_route": "postprocess",
        }

    def should_continue_routing(
        state: MultiAgentState,
    ) -> Literal[
        "postprocess",
        "supervisor",
        "data_expert",
        "todo_expert",
        "summarize",
        "coverage_gate",
    ]:
        """根据评估结果决定下一步。"""
        evaluation_route = str(state.get("evaluation_route") or "").strip()
        if evaluation_route in {"postprocess", "supervisor", "data_expert", "todo_expert", "summarize", "coverage_gate"}:
            return evaluation_route  # type: ignore[return-value]

        evaluation = state.get("evaluation", "complete")
        if evaluation == "continue":
            return "supervisor"
        return "postprocess"

    def coverage_gate_should_continue(
        state: MultiAgentState,
    ) -> Literal["final_composer", "supervisor", "postprocess"]:
        """coverage_gate 条件路由：通过后进入 composer，否则回补齐或收口。"""
        route = str(state.get("coverage_gate_route") or "").strip()
        if route in {"final_composer", "supervisor", "postprocess"}:
            return route  # type: ignore[return-value]

        coverage_report = state.get("coverage_report")
        if isinstance(coverage_report, dict) and not bool(coverage_report.get("pass")) and _is_coverage_gate_enforced():
            return "supervisor"
        return "final_composer"

    workflow = StateGraph(MultiAgentState)

    workflow.add_node("preprocess", _preprocess_multimodal)
    workflow.add_node("supervisor", _create_streaming_agent_wrapper(supervisor_agent, "supervisor"))
    workflow.add_node("data_expert", _create_streaming_agent_wrapper(data_graph_app, "data_expert"))
    workflow.add_node("todo_expert", _create_streaming_agent_wrapper(todo_graph_app, "todo_expert"))
    workflow.add_node("evaluate", _evaluate_expert_work)
    workflow.add_node("coverage_gate", _coverage_gate_node)
    workflow.add_node("final_composer", _final_composer_node)
    workflow.add_node("summarize", _summarize_multi_intent)
    workflow.add_node("postprocess", _postprocess)

    workflow.add_edge(START, "preprocess")

    def preprocess_should_continue(state: MultiAgentState) -> Literal["supervisor", "data_expert", "todo_expert"]:
        pending_handoff = state.get("pending_handoff")
        target_agent = str((pending_handoff or {}).get("target_agent") or "").strip()
        if target_agent in WORKFLOW_AGENT_NODE_BY_TYPE and bool(state.get("multi_intent_mode")):
            return WORKFLOW_AGENT_NODE_BY_TYPE[target_agent]  # type: ignore[return-value]
        return "supervisor"

    workflow.add_conditional_edges(
        "preprocess",
        preprocess_should_continue,
        {
            "supervisor": "supervisor",
            "data_expert": "data_expert",
            "todo_expert": "todo_expert",
        },
    )
    workflow.add_edge("data_expert", "evaluate")
    workflow.add_edge("todo_expert", "evaluate")
    def supervisor_should_continue(state: MultiAgentState) -> str:
        """判断 Supervisor 下一步路由。"""
        from app.ai.exceptions import HandoffValidationError

        pending_handoff = state.get("pending_handoff")
        if pending_handoff:
            target_agent = pending_handoff.get("target_agent")
            valid_targets = set(WORKFLOW_AGENT_NODE_BY_TYPE.keys())
            if target_agent in valid_targets:
                return WORKFLOW_AGENT_NODE_BY_TYPE[target_agent]

            detected_intent = pending_handoff.get("detected_intent", "unknown")
            if detected_intent:
                schema_route = route_by_schema(detected_intent)
                if schema_route in WORKFLOW_AGENT_NODES:
                    return schema_route

            logger.error(
                str(
                    HandoffValidationError(
                        f"无效的 Handoff 目标 Agent: {target_agent}，有效值为 {list(valid_targets)}",
                        invalid_target=target_agent,
                    )
                )
            )
            return "postprocess"

        messages = state.get("messages") or []
        if not messages:
            return "postprocess"
        if getattr(messages[-1], "tool_calls", None) or bool(state.get("multi_intent_mode")):
            return "evaluate"
        return "postprocess"
    
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_should_continue,
        {
            "data_expert": "data_expert",
            "todo_expert": "todo_expert",
            "evaluate": "evaluate",
            "postprocess": "postprocess"
        }
    )
    
    workflow.add_conditional_edges(
        "evaluate",
        should_continue_routing,
        {
            "postprocess": "postprocess",
            "supervisor": "supervisor",
            "data_expert": "data_expert",
            "todo_expert": "todo_expert",
            "coverage_gate": "coverage_gate",
            "summarize": "summarize",
        }
    )

    workflow.add_conditional_edges(
        "coverage_gate",
        coverage_gate_should_continue,
        {
            "final_composer": "final_composer",
            "supervisor": "supervisor",
            "postprocess": "postprocess",
        },
    )
    workflow.add_edge("final_composer", "postprocess")
    workflow.add_edge("summarize", "postprocess")
    
    workflow.add_edge("postprocess", END)

    if checkpointer is None:
        checkpointer = await get_checkpointer()
    
    graph = workflow.compile(checkpointer=checkpointer)
    logger.info("多智能体图编译完成（启用思考: %s，模型: %s）", enable_thinking, model_id or "默认")
    return graph
