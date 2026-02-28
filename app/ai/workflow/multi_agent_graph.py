"""多智能体 Supervisor 图定义模块（中文注释）。

本模块实现 Supervisor 模式的多智能体系统：
- Supervisor 负责理解用户意图并路由到合适的专业 Agent
- 问数 Agent: 处理数据查询、分析、可视化
- 待办助手 Agent: 处理任务管理相关请求

架构示意（升级版）：
    User -> preprocess -> supervisor -> [experts] -> postprocess -> User
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Sequence, Optional, Literal, Any, Dict, Tuple
from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage, ToolMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from app.ai.utils.message_factory import create_ai_message
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langgraph.types import Command, Send, interrupt
from langgraph.errors import GraphInterrupt
from langgraph.prebuilt import InjectedState
from langgraph.graph import StateGraph, START, END

from app.ai.llm_util import get_scene_llm, _normalize_text_content
from app.ai.scene_registry import SCENE_KEY_MULTI_AGENT_SUPERVISOR
from app.db.postgres_checkpoint import get_checkpointer

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
    StreamingToolStartPayload,
    StreamingResultPayload,
    StreamingKbImagesPayload,
    build_streaming_tool_start_payload,
    build_streaming_result_payload,
    build_streaming_kb_images_payload,
)
from app.ai.prompts.agent_prompts import SUPERVISOR_PROMPT
from app.ai.state import AgentType, AGENT_DESCRIPTIONS, MultiAgentState

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


# AgentType, AGENT_DESCRIPTIONS, MultiAgentState 已迁移到 app/ai/state.py


# SUPERVISOR_PROMPT 已迁移到 app/ai/prompts/agent_prompts.py


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

TODO_DOMAIN_HINTS = (
    "待办",
    "任务",
    "提醒",
    "清单",
    "todo",
)

TODO_QUERY_HINTS = (
    "查询",
    "查看",
    "列出",
    "列表",
    "清单",
    "有哪些",
    "显示",
    "看看",
)

TODO_CREATE_HINTS = (
    "创建",
    "新建",
    "新增",
    "添加",
    "记录",
    "记一下",
)

TODO_ENRICHMENT_HINTS = (
    "补充",
    "添加",
    "加上",
    "写入",
    "写到",
    "备注",
    "描述",
    "追加",
)

EXTERNAL_INFO_HINTS = (
    "天气",
    "气温",
    "股价",
    "股票",
    "指数",
    "汇率",
    "黄金",
    "油价",
    "行情",
    "基金",
)

DATA_DOMAIN_HINTS = (
    "数据",
    "指标",
    "报表",
    "统计",
    "数据库",
    "sql",
    "分析",
)

DATA_STRONG_HINTS = (
    "sql",
    "报表",
    "数据库",
    "指标",
    "字段",
    "表",
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
_TRUE_VALUES = {"1", "true", "yes", "on"}


class _IntentGoalModel(BaseModel):
    """Planner 输出的单目标结构。"""

    kind: str = Field(default="general.reply")
    title: str = Field(default="")
    must_answer: bool = Field(default=True)
    confidence: float = Field(default=0.7)


class _IntentPlanModel(BaseModel):
    """Planner 输出的目标合集。"""

    goals: list[_IntentGoalModel] = Field(default_factory=list)

PLUGIN_REGISTRY_ERROR_HINTS = (
    "plugin registry",
    "plugin_registry",
    "plugin init",
    "plugin load",
    "插件注册",
    "插件加载",
)


def _is_feature_flag_enabled(env_name: str, fallback: bool = False) -> bool:
    """读取布尔开关，支持环境变量覆盖。"""
    raw_value = os.getenv(env_name)
    if raw_value is None:
        return fallback
    return raw_value.strip().lower() in _TRUE_VALUES


def _is_runtime_recovery_enabled() -> bool:
    """运行时恢复开关（默认开启）。"""
    return _is_feature_flag_enabled("ENABLE_RUNTIME_RECOVERY", True)


def _is_plugin_registry_enabled() -> bool:
    """插件注册表开关（默认关闭，后置接线）。"""
    return _is_feature_flag_enabled("ENABLE_PLUGIN_REGISTRY", False)


def _is_delivery_orchestrator_v2_enabled() -> bool:
    """交付导向编排开关（默认开启）。"""
    return _is_feature_flag_enabled("ENABLE_DELIVERY_ORCHESTRATOR_V2", True)


def _is_sse_delivery_events_v2_enabled() -> bool:
    """SSE 交付事件开关（默认开启）。"""
    return _is_feature_flag_enabled("ENABLE_SSE_DELIVERY_EVENTS_V2", True)


def _is_plugin_registry_error(error_text: str) -> bool:
    """判断异常是否命中插件注册表故障。"""
    lowered = str(error_text or "").strip().lower()
    if not lowered:
        return False
    return any(hint in lowered for hint in PLUGIN_REGISTRY_ERROR_HINTS)


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

    if (
        compact.startswith("external")
        or "weather" in compact
        or "lookup" in compact
        or "search" in compact
        or "web" in compact
    ):
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
    bucket = _goal_kind_bucket(kind)
    if bucket == "todo":
        return "待办事项"
    if bucket == "external":
        return "外部信息"
    if bucket == "data":
        return "数据查询"
    return "问题回复"


def _build_model_intent_plan_prompt(user_text: str) -> str:
    """构建模型意图规划提示词。"""
    return (
        "你是对话编排器中的目标分解节点。\n"
        "请只根据用户语义拆分本轮必须回答的目标，不要因为动作词（如“查询/看看/列出”）盲目扩增目标。\n"
        "规则：\n"
        "1) 仅当用户明确提到数据域（如 SQL、报表、数据库、指标）时，才输出 data.query。\n"
        "2) 待办相关问题输出 todo.query 或 todo.create。\n"
        "3) 天气/股价/汇率等外部信息输出 external.lookup。\n"
        "4) 无法拆分时仅输出 general.reply。\n"
        "5) goals 保持去重，同类目标最多 1 个。\n"
        f"用户问题：{str(user_text or '').strip()}"
    )


def _infer_model_intent_plan(state: MultiAgentState, llm: Any) -> Dict[str, Any]:
    """使用模型生成结构化 intent_plan。"""
    messages = _slice_messages_from_latest_human(state.get("messages", []))
    user_text = _extract_latest_human_content(messages)
    if not user_text:
        return {
            "version": 1,
            "source": "model_primary",
            "user_query": "",
            "goals": [
                {
                    "goal_id": "GOAL-01",
                    "order": 1,
                    "kind": "general.reply",
                    "title": "问题回复",
                    "must_answer": True,
                    "confidence": 0.5,
                }
            ],
        }

    if not hasattr(llm, "with_structured_output"):
        raise RuntimeError("planner_llm_structured_output_unsupported")

    structured_llm = llm.with_structured_output(_IntentPlanModel)
    prompt = _build_model_intent_plan_prompt(user_text)
    raw_output = structured_llm.invoke(prompt)
    if isinstance(raw_output, _IntentPlanModel):
        parsed = raw_output
    elif isinstance(raw_output, dict):
        parsed = _IntentPlanModel(**raw_output)
    else:
        raw_data: Dict[str, Any] = {}
        if hasattr(raw_output, "model_dump"):
            raw_data = raw_output.model_dump()  # type: ignore[assignment]
        elif hasattr(raw_output, "dict"):
            raw_data = raw_output.dict()  # type: ignore[assignment]
        parsed = _IntentPlanModel(**raw_data)

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
            }
        ]

    return {
        "version": 1,
        "source": "model_primary",
        "user_query": user_text,
        "goals": normalized_goals,
    }


def _infer_initial_intent_plan(state: MultiAgentState) -> Dict[str, Any]:
    """从用户输入推断初始问题合同（intent_plan）。"""
    messages = _slice_messages_from_latest_human(state.get("messages", []))
    user_text = _extract_latest_human_content(messages)
    normalized = user_text.lower()

    has_todo = any(hint in normalized for hint in TODO_DOMAIN_HINTS)
    has_external = any(hint in normalized for hint in EXTERNAL_INFO_HINTS)
    has_data = any(hint in normalized for hint in DATA_DOMAIN_HINTS)
    has_data_strong = any(hint in normalized for hint in DATA_STRONG_HINTS)

    goals: list[Dict[str, Any]] = []
    if has_todo:
        goals.append(
            {
                "kind": "todo.query",
                "title": "待办事项",
                "must_answer": True,
                "order_hint": _first_hint_position(user_text, TODO_DOMAIN_HINTS),
            }
        )
    if has_external:
        goals.append(
            {
                "kind": "external.lookup",
                "title": "外部信息",
                "must_answer": True,
                "order_hint": _first_hint_position(user_text, EXTERNAL_INFO_HINTS),
            }
        )
    if has_data and not has_external and (not has_todo or has_data_strong):
        goals.append(
            {
                "kind": "data.query",
                "title": "数据查询",
                "must_answer": True,
                "order_hint": _first_hint_position(user_text, DATA_DOMAIN_HINTS),
            }
        )

    if not goals:
        goals.append(
            {
                "kind": "general.reply",
                "title": "问题回复",
                "must_answer": True,
                "order_hint": 0,
            }
        )

    goals = sorted(goals, key=lambda item: int(item.get("order_hint", 10**9)))
    normalized_goals: list[Dict[str, Any]] = []
    for index, goal in enumerate(goals, start=1):
        normalized_goals.append(
            {
                "goal_id": f"GOAL-{index:02d}",
                "order": index,
                "kind": goal["kind"],
                "title": goal["title"],
                "must_answer": bool(goal.get("must_answer", True)),
            }
        )

    return {
        "version": 1,
        "source": "heuristic",
        "user_query": user_text,
        "goals": normalized_goals,
    }


def _build_planner_intent_plan(
    state: MultiAgentState,
    *,
    llm: Any,
    mode: str = "model_primary",
) -> Dict[str, Any]:
    """构建 planner 节点使用的 intent_plan（模型主判定 + 规则兜底）。"""
    normalized_mode = str(mode or "").strip().lower()
    if normalized_mode not in {"model_primary", "heuristic_only"}:
        normalized_mode = "model_primary"

    heuristic_plan = _infer_initial_intent_plan(state)
    if normalized_mode == "heuristic_only":
        return {
            "version": heuristic_plan.get("version", 1),
            "source": "heuristic_only",
            "user_query": heuristic_plan.get("user_query", ""),
            "goals": list(heuristic_plan.get("goals") or []),
        }

    try:
        return _infer_model_intent_plan(state, llm)
    except Exception as exc:
        logger.warning("planner_model_fallback_to_heuristic: %s", exc)
        return {
            "version": heuristic_plan.get("version", 1),
            "source": "heuristic_fallback",
            "user_query": heuristic_plan.get("user_query", ""),
            "goals": list(heuristic_plan.get("goals") or []),
            "fallback_meta": {
                "reason": f"planner_model_error:{type(exc).__name__}",
                "detail": str(exc)[:200],
            },
        }


def _goal_kind_bucket(kind: str) -> str:
    """将细粒度 kind 归一到匹配桶。"""
    normalized = str(kind or "").strip().lower()
    if normalized.startswith("todo"):
        return "todo"
    if normalized.startswith("external"):
        return "external"
    if normalized.startswith("data"):
        return "data"
    return "general"


def _count_must_answer_goals(intent_plan: Optional[Dict[str, Any]]) -> int:
    """统计问题合同中 must_answer 目标数量。"""
    goals = list((intent_plan or {}).get("goals") or [])
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
    return _count_must_answer_goals(state.get("intent_plan")) >= 2


def _build_multi_intent_recovery_system_context(
    base_context: str,
    intent_plan: Dict[str, Any],
    missing_goals: Sequence[Dict[str, Any]],
) -> str:
    """构造补齐未完成目标的 system_context 提示。"""
    normalized_base = str(base_context or "").strip()
    marker_idx = normalized_base.find(DELIVERY_RECOVERY_MARKER)
    if marker_idx >= 0:
        normalized_base = normalized_base[:marker_idx].rstrip()

    goal_index: Dict[str, Dict[str, Any]] = {
        str(goal.get("goal_id") or ""): goal
        for goal in list(intent_plan.get("goals") or [])
        if str(goal.get("goal_id") or "")
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
        DELIVERY_RECOVERY_MARKER,
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


def _extract_latest_structured_result(
    messages: Sequence[BaseMessage],
    *,
    data_type: str,
) -> Optional[Dict[str, Any]]:
    """提取当前轮最近的结构化结果。"""
    target_data_type = str(data_type or "").strip()
    if not target_data_type:
        return None

    for message in reversed(messages or []):
        if str(getattr(message, "type", "")).lower().strip() != "ai":
            continue
        additional = getattr(message, "additional_kwargs", {}) or {}
        if not isinstance(additional, dict):
            continue
        if str(additional.get("data_type") or "").strip() != target_data_type:
            continue
        payload = additional.get("data")
        if not isinstance(payload, dict):
            payload = {}
        return {
            "data_type": target_data_type,
            "data": payload,
            "message": _normalize_text_content(getattr(message, "content", "")),
        }
    return None


def _ensure_intent_plan_covers_runtime(
    state: MultiAgentState,
    base_plan: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """根据运行时产物补齐 intent_plan，避免遗漏必答项。"""
    plan = dict(base_plan or state.get("intent_plan") or {})
    goals = list(plan.get("goals") or [])
    seen_buckets = {_goal_kind_bucket(str(goal.get("kind") or "")) for goal in goals}

    turn_messages = _slice_messages_from_latest_human(state.get("messages", []))
    direct_findings = _build_direct_lookup_findings(turn_messages)
    trace = list(state.get("handoff_execution_trace") or [])

    def _append_goal(kind: str, title: str) -> None:
        goals.append(
            {
                "goal_id": f"GOAL-{len(goals) + 1:02d}",
                "order": len(goals) + 1,
                "kind": kind,
                "title": title,
                "must_answer": True,
            }
        )

    if direct_findings and "external" not in seen_buckets:
        _append_goal("external.lookup", "外部信息")
        seen_buckets.add("external")

    for item in trace:
        target_agent = str(item.get("target_agent") or "")
        if target_agent == AgentType.TODO and "todo" not in seen_buckets:
            _append_goal("todo.query", "待办事项")
            seen_buckets.add("todo")
        if target_agent == AgentType.DATA and "data" not in seen_buckets:
            _append_goal("data.query", "数据查询")
            seen_buckets.add("data")

    if not goals:
        goals = [
            {
                "goal_id": "GOAL-01",
                "order": 1,
                "kind": "general.reply",
                "title": "问题回复",
                "must_answer": True,
            }
        ]

    plan["goals"] = goals
    if "version" not in plan:
        plan["version"] = 1
    if "source" not in plan:
        plan["source"] = "runtime"
    return plan


def _build_delivery_artifacts(state: MultiAgentState) -> list[Dict[str, Any]]:
    """构建结构化交付物列表。"""
    turn_messages = _slice_messages_from_latest_human(state.get("messages", []))
    trace = list(state.get("handoff_execution_trace") or [])
    deliverables: list[Dict[str, Any]] = []

    direct_findings = _build_direct_lookup_findings(turn_messages)
    if direct_findings:
        summary = "；".join(f"{item['label']}：{item['summary']}" for item in direct_findings)
        deliverables.append(
            {
                "kind": "external.lookup",
                "status": "success",
                "summary": summary,
                "payload": {"findings": direct_findings},
            }
        )

    todo_structured = _extract_latest_structured_result(turn_messages, data_type="todo_list")
    data_structured = _extract_latest_structured_result(turn_messages, data_type="sql_result")

    for item in trace:
        target_agent = str(item.get("target_agent") or "")
        result_excerpt = _normalize_tool_summary_text(item.get("result_excerpt"), limit=220)
        task_description = _normalize_tool_summary_text(item.get("task_description"), limit=120)

        if target_agent == AgentType.TODO:
            payload = dict((todo_structured or {}).get("data") or {})
            summary = result_excerpt or (todo_structured or {}).get("message") or "待办处理完成"
            deliverables.append(
                {
                    "kind": "todo.query",
                    "status": "success",
                    "summary": summary,
                    "task_description": task_description,
                    "payload": payload,
                }
            )
            continue

        if target_agent == AgentType.DATA:
            payload = dict((data_structured or {}).get("data") or {})
            summary = result_excerpt or (data_structured or {}).get("message") or "数据处理完成"
            deliverables.append(
                {
                    "kind": "data.query",
                    "status": "success",
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
                    "status": "success",
                    "summary": result_excerpt,
                    "task_description": task_description,
                    "payload": {},
                }
            )

    return deliverables


def _match_goals_with_deliverables(
    goals: Sequence[Dict[str, Any]],
    deliverables: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """按顺序匹配 goal 与 deliverable。"""
    result: Dict[str, Dict[str, Any]] = {}
    used_indexes: set[int] = set()

    for goal in goals:
        goal_id = str(goal.get("goal_id") or "")
        goal_bucket = _goal_kind_bucket(str(goal.get("kind") or ""))
        matched_idx: Optional[int] = None

        for idx, deliverable in enumerate(deliverables):
            if idx in used_indexes:
                continue
            deliverable_bucket = _goal_kind_bucket(str(deliverable.get("kind") or ""))
            if goal_bucket == deliverable_bucket:
                matched_idx = idx
                break

        if matched_idx is None and goal_bucket == "general":
            for idx, deliverable in enumerate(deliverables):
                if idx in used_indexes:
                    continue
                if _goal_kind_bucket(str(deliverable.get("kind") or "")) != "external":
                    matched_idx = idx
                    break

        if matched_idx is None:
            continue

        used_indexes.add(matched_idx)
        result[goal_id] = dict(deliverables[matched_idx])

    return result


def _compute_coverage_report(
    intent_plan: Dict[str, Any],
    deliverables: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """计算问题覆盖率报告。"""
    goals = list(intent_plan.get("goals") or [])
    matched = _match_goals_with_deliverables(goals, deliverables)
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


def _render_goal_answer(goal: Dict[str, Any], deliverable: Optional[Dict[str, Any]]) -> str:
    """渲染单个 goal 的用户答复文本。"""
    title = str(goal.get("title") or goal.get("kind") or "问题").strip()
    if not deliverable:
        return f"{title}：暂未完成，缺少可用结果。"

    bucket = _goal_kind_bucket(str(goal.get("kind") or ""))
    if bucket == "todo":
        return f"{title}：{_render_todo_deliverable_text(deliverable)}"

    summary = _normalize_tool_summary_text(deliverable.get("summary"), limit=280)
    if not summary:
        summary = "已处理完成。"
    return f"{title}：{summary}"


def _render_final_answer(
    intent_plan: Dict[str, Any],
    coverage_report: Dict[str, Any],
) -> str:
    """根据问题合同与覆盖报告生成唯一最终答复。"""
    goals = sorted(
        list(intent_plan.get("goals") or []),
        key=lambda item: int(item.get("order") or 0),
    )
    goal_results = dict(coverage_report.get("goal_results") or {})

    lines: list[str] = ["按你的问题顺序，逐项回复如下："]
    for idx, goal in enumerate(goals, start=1):
        goal_id = str(goal.get("goal_id") or "")
        lines.append(f"{idx}. {_render_goal_answer(goal, goal_results.get(goal_id))}")

    missing_goals = list(coverage_report.get("missing_goals") or [])
    if missing_goals:
        missing_titles = "、".join(str(item.get("title") or item.get("goal_id") or "未命名目标") for item in missing_goals)
        lines.append(f"当前仍缺少：{missing_titles}。如果你愿意，我可以继续补齐。")
    else:
        lines.append("以上问题已全部覆盖。")

    return "\n".join(lines)


def _augment_data_handoff_payload(
    handoff_data: Dict[str, Any],
    state: MultiAgentState,
) -> Dict[str, Any]:
    """规范化 data_expert handoff，避免 task_description 过度扩写污染专家意图。"""
    if not isinstance(handoff_data, dict):
        return handoff_data

    if handoff_data.get("target_agent") != AgentType.DATA:
        return handoff_data

    enriched = dict(handoff_data)
    latest_user_text = _extract_latest_human_content(state.get("messages", []))

    base_frame = enriched.get("frame")
    enriched["frame"] = dict(base_frame) if isinstance(base_frame, dict) else None

    turn_act_hint = str(enriched.get("turn_act_hint") or "").strip().upper()
    if turn_act_hint not in TURN_ACT_HINTS:
        state_turn_act = str(state.get("turn_act") or "").strip().upper()
        if state_turn_act in TURN_ACT_HINTS:
            turn_act_hint = state_turn_act
        else:
            turn_act_hint = "NEW_QUERY"
    enriched["turn_act_hint"] = turn_act_hint

    raw_desc = str(enriched.get("task_description") or "").strip()
    user_desc = str(latest_user_text or "").strip()
    if user_desc:
        enriched["task_description"] = f"用户原始问题：{user_desc}"
    else:
        enriched["task_description"] = _normalize_tool_summary_text(raw_desc, limit=240)

    logger.info(
        "data_handoff_normalized: turn_act_hint=%s, has_frame=%s, desc_len=%s",
        enriched.get("turn_act_hint"),
        bool(enriched.get("frame")),
        len(str(enriched.get("task_description") or "")),
    )
    return enriched


def _infer_todo_handoff_from_text(user_text: str) -> Optional[Dict[str, Any]]:
    """在 Supervisor 不可用时，基于关键词构造待办兜底委派。"""
    if not user_text:
        return None

    normalized = user_text.lower().strip()
    has_todo_domain = any(hint in normalized for hint in TODO_DOMAIN_HINTS)
    if not has_todo_domain:
        return None

    has_query_signal = any(hint in normalized for hint in TODO_QUERY_HINTS)
    has_create_signal = any(hint in normalized for hint in TODO_CREATE_HINTS)

    todo_action = "query" if has_query_signal else ""
    todo_fields: Dict[str, Any] = {}
    detected_intent = "query_todo"

    if todo_action == "query":
        if "全部" in normalized or "所有" in normalized:
            pass
        elif "已完成" in normalized and "未完成" not in normalized:
            todo_fields["status"] = "completed"
        else:
            todo_fields["status"] = "pending"
    elif has_create_signal:
        todo_action = "create"
        detected_intent = "create_todo"
    else:
        todo_action = "query"
        todo_fields["status"] = "pending"

    return {
        "action": "handoff",
        "target_agent": AgentType.TODO,
        "detected_intent": detected_intent,
        "task_description": (
            "Supervisor 模型服务暂不可用，已启用关键词兜底路由。"
            f"请按待办流程处理用户请求：{user_text}"
        ),
        "frame": {
            "todo_action": todo_action,
            "todo_fields": todo_fields,
        },
    }


def _build_supervisor_fallback_handoff(state: MultiAgentState, error_text: str) -> Optional[Dict[str, Any]]:
    """构造 Supervisor 失败后的兜底委派。"""
    if not _is_model_access_error(error_text):
        return None

    latest_user_text = _extract_latest_human_content(state.get("messages", []))
    return _infer_todo_handoff_from_text(latest_user_text)


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

    if node_name == "supervisor":
        fallback_handoff = _build_supervisor_fallback_handoff(state, error_text)
        if fallback_handoff:
            target_agent = str(fallback_handoff.get("target_agent") or "unknown")
            return {
                "route": "handoff",
                "pending_handoff": fallback_handoff,
                "status_message": "模型服务暂不可用，已切换到待办兜底路由继续处理。",
                "runtime_recovery_state": _build_runtime_recovery_state(
                    state,
                    fallback_route=f"handoff:{target_agent}",
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


def _calculate_supervisor_context_budget(max_tokens: int) -> int:
    """根据模型窗口计算 Supervisor 单轮上下文预算。"""
    safe_max_tokens = max(max_tokens, SUPERVISOR_CONTEXT_MIN_TOKENS)
    budget = int(safe_max_tokens * SUPERVISOR_CONTEXT_TOKEN_BUDGET_RATIO)
    return max(budget, SUPERVISOR_CONTEXT_MIN_TOKENS)


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


def _compact_tool_message_for_inference(message: ToolMessage) -> ToolMessage:
    """仅在推理输入阶段压缩 ToolMessage，不影响持久化原始消息。"""
    content_text = _normalize_text_content(getattr(message, "content", ""))
    compacted_text = _truncate_tool_message_text(content_text)
    if compacted_text == content_text:
        return message

    if hasattr(message, "model_copy"):
        try:
            return message.model_copy(update={"content": compacted_text})
        except Exception as exc:
            logger.debug("ToolMessage 压缩失败，回退原消息: %s", exc)
            return message

    return message


def _prepare_messages_for_supervisor_inference(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """准备 Supervisor 推理输入，压缩超长工具消息。"""
    prepared: list[BaseMessage] = []
    compacted_count = 0

    for message in messages or []:
        if isinstance(message, ToolMessage):
            compacted = _compact_tool_message_for_inference(message)
            if compacted is not message:
                compacted_count += 1
            prepared.append(compacted)
            continue
        prepared.append(message)

    if compacted_count:
        logger.info("Supervisor 上下文压缩: compacted_tool_messages=%d", compacted_count)

    return prepared


def _summarize_tavily_tool_output(tool_content: str) -> str:
    """从 Tavily 工具输出中提取可用于待办补充的摘要。"""
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

    if isinstance(payload, dict):
        answer = _normalize_tool_summary_text(payload.get("answer"), limit=220)
        if answer:
            return answer
        results = payload.get("results")
    elif isinstance(payload, list):
        results = payload
    else:
        return _normalize_tool_summary_text(stripped, limit=220)

    if not isinstance(results, list):
        return _normalize_tool_summary_text(stripped, limit=220)

    lines = []
    for item in results[:2]:
        if not isinstance(item, dict):
            continue
        title = _normalize_tool_summary_text(item.get("title"), limit=36)
        snippet = _normalize_tool_summary_text(
            item.get("content") or item.get("snippet"),
            limit=140,
        )
        if title and snippet:
            lines.append(f"{title}: {snippet}")
        elif snippet:
            lines.append(snippet)

    merged = "；".join(lines)
    return _normalize_tool_summary_text(merged, limit=240)


def _extract_supervisor_tool_observations(messages: Sequence[BaseMessage]) -> list[dict[str, str]]:
    """提取 Supervisor 本轮工具观察结果，供 TodoExpert 合并描述。"""
    observations: list[dict[str, str]] = []

    for msg in messages or []:
        if not isinstance(msg, ToolMessage):
            continue

        tool_name = str(getattr(msg, "name", "") or "unknown")
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
    normalized = str(user_text or "").strip().lower()
    if not normalized:
        return False

    has_enrichment = any(hint in normalized for hint in TODO_ENRICHMENT_HINTS)
    has_external = any(hint in normalized for hint in EXTERNAL_INFO_HINTS)
    return has_enrichment and has_external


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


def _should_mute_expert_text_output(state: Dict[str, Any], node_name: str) -> bool:
    """决定是否抑制专家节点文本直出（复合任务改为最终统一汇总）。"""
    if node_name == "data_expert":
        return True
    if node_name == "todo_expert" and bool(state.get("multi_intent_mode")):
        return True
    return False


def _extract_latest_visible_ai_excerpt(messages: Sequence[BaseMessage], limit: int = 220) -> str:
    """提取最近一条可展示的 AI 输出摘要。"""
    from app.ai.protocol import AgentOutputParser

    for message in reversed(messages or []):
        if str(getattr(message, "type", "")).lower().strip() != "ai":
            continue
        content = _normalize_text_content(getattr(message, "content", ""))
        if not content:
            continue
        if AgentOutputParser.should_filter_content(content):
            continue
        return _normalize_tool_summary_text(content, limit=limit)
    return ""


def _build_direct_lookup_findings(messages: Sequence[BaseMessage]) -> list[Dict[str, str]]:
    """提取 Supervisor 直接工具（天气/知识库）结果，供最终汇总使用。"""
    findings: list[Dict[str, str]] = []
    seen: set[Tuple[str, str]] = set()

    for message in messages or []:
        if not isinstance(message, ToolMessage):
            continue

        tool_name = str(getattr(message, "name", "") or "")
        lowered_name = tool_name.lower()
        content = str(getattr(message, "content", "") or "")
        if not content:
            continue

        if "tavily" in lowered_name:
            summary = _summarize_tavily_tool_output(content)
            label = "天气/实时信息"
        elif "knowledge_search" in lowered_name:
            summary = _normalize_tool_summary_text(content, limit=220)
            label = "知识库检索"
        else:
            continue

        if not summary:
            continue

        key = (label, summary)
        if key in seen:
            continue
        seen.add(key)
        findings.append({"label": label, "summary": summary})

    return findings[:3]


def _build_multi_intent_summary_content(state: MultiAgentState) -> str:
    """构造复合任务统一交付文本（用户可读、无内部术语）。"""
    intent_plan = _ensure_intent_plan_covers_runtime(state)
    deliverables = _build_delivery_artifacts(state)
    coverage_report = _compute_coverage_report(intent_plan, deliverables)
    return _render_final_answer(intent_plan, coverage_report)


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
                    "task_description": pending_handoff.get("task_description"),
                    "result_excerpt": _extract_latest_visible_ai_excerpt(turn_messages),
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

        intent_plan = _ensure_intent_plan_covers_runtime(runtime_state)
        deliverables = _build_delivery_artifacts(runtime_state)
        coverage_preview = _compute_coverage_report(intent_plan, deliverables)
        missing_goals = list(coverage_preview.get("missing_goals") or [])

        if not missing_goals:
            if _is_delivery_orchestrator_v2_enabled():
                return {
                    "evaluation": "coverage",
                    "evaluation_route": "coverage_gate",
                    "pending_handoff": None,
                    "handoff_queue": [],
                    "completed_handoffs": completed_handoffs,
                    "handoff_execution_trace": execution_trace,
                    "intent_plan": intent_plan,
                    "deliverables": deliverables,
                    "coverage_report": coverage_preview,
                }
            return {
                "evaluation": "summarize",
                "evaluation_route": "summarize",
                "pending_handoff": None,
                "handoff_queue": [],
                "completed_handoffs": completed_handoffs,
                "handoff_execution_trace": execution_trace,
                "intent_plan": intent_plan,
                "deliverables": deliverables,
                "coverage_report": coverage_preview,
            }

        missing_goal_ids = [str(item.get("goal_id") or "") for item in missing_goals]
        missing_goal_titles = [str(item.get("title") or item.get("goal_id") or "未命名目标") for item in missing_goals]
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
                "intent_plan": intent_plan,
                "deliverables": deliverables,
                "coverage_report": coverage_preview,
                "delivery_meta": {
                    **dict(state.get("delivery_meta") or {}),
                    "pending_goal_ids": missing_goal_ids,
                    "pending_goal_titles": missing_goal_titles,
                },
            }

        return {
            "evaluation": "continue",
            "evaluation_route": "supervisor",
            "iteration_count": iteration_count + 1,
            "pending_handoff": None,
            "handoff_queue": [],
            "completed_handoffs": completed_handoffs,
            "handoff_execution_trace": execution_trace,
            "intent_plan": intent_plan,
            "deliverables": deliverables,
            "coverage_report": coverage_preview,
            "delivery_meta": {
                **dict(state.get("delivery_meta") or {}),
                "pending_goal_ids": missing_goal_ids,
                "pending_goal_titles": missing_goal_titles,
            },
            "system_context": _build_multi_intent_recovery_system_context(
                str(state.get("system_context") or ""),
                intent_plan,
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
        # 子图可能没有 checkpoint（首次调用），这是正常情况
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

    if tool_name and "tavily" in (tool_name or "").lower():
        logger.info("联网搜索返回: tool=%s, 结果长度=%s", tool_name, len(tool_content))

    new_images = AgentOutputParser.parse_kb_images(tool_content)
    if new_images:
        ctx.kb_images.update(new_images)
        logger.info("[%s] 从 ToolMessage 提取到 kb_images: %s 个", ctx.node_name, len(new_images))

    return True


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


def _inject_streaming_context_messages(
    pruned_messages: Sequence[BaseMessage],
    state: Dict[str, Any],
) -> list[BaseMessage]:
    """将 system_context / skill_context 注入裁剪后的消息列表。"""
    from langchain_core.messages import SystemMessage

    context_messages = []
    if state.get("system_context"):
        context_messages.append(SystemMessage(content=state["system_context"]))

    if state.get("skill_context"):
        context_messages.append(SystemMessage(content=state["skill_context"]))

    if not context_messages:
        return list(pruned_messages)

    insert_pos = 0
    for index, message in enumerate(pruned_messages):
        if not isinstance(message, SystemMessage):
            insert_pos = index
            break
    else:
        insert_pos = len(pruned_messages)

    return list(pruned_messages[:insert_pos]) + context_messages + list(pruned_messages[insert_pos:])


def _prepare_streaming_inference_state(
    state: Dict[str, Any],
) -> Tuple[Dict[str, Any], int, int, int, int, int]:
    """构造 streaming_wrapper 调用 agent.astream 前的推理态 state。"""
    original_messages = state.get("messages", [])
    prepared_messages = _prepare_messages_for_supervisor_inference(original_messages)

    from app.ai import config as ai_config

    token_budget = _calculate_supervisor_context_budget(
        getattr(ai_config, "MESSAGE_MAX_TOKENS", SUPERVISOR_CONTEXT_MIN_TOKENS)
    )
    pruned_messages = trim_messages(
        prepared_messages,
        max_tokens=token_budget,
        token_counter=count_tokens_approximately,
        strategy="last",
        start_on="human",
        end_on=("human", "tool", "ai"),
        include_system=True,
        allow_partial=False,
    )

    pruned_state = state.copy()
    pruned_state["messages"] = _inject_streaming_context_messages(pruned_messages, state)

    prepared_token_estimate = int(count_tokens_approximately(prepared_messages) or 0)
    pruned_token_estimate = int(count_tokens_approximately(pruned_messages) or 0)
    input_message_count = len(pruned_state.get("messages", []))

    return (
        pruned_state,
        len(original_messages),
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
        handoff_batch = AgentOutputParser.extract_all_handoffs_from_messages(delta_messages_for_scan)
        if handoff_batch:
            normalized_batch = _normalize_handoff_batch_for_supervisor(
                handoff_batch,
                delta_messages=delta_messages_for_scan,
                state=ctx.state,
            )
            first_handoff = normalized_batch[0]
            remaining_handoffs = normalized_batch[1:]
            target_agent = first_handoff.get("target_agent")
            direct_findings = _build_direct_lookup_findings(delta_messages_for_scan)
            has_direct_lookup = bool(direct_findings)
            planned_goal_count = _count_must_answer_goals(ctx.state.get("intent_plan"))
            enable_multi_intent_mode = _should_enable_multi_intent_mode(
                handoff_batch_size=len(normalized_batch),
                has_direct_lookup=has_direct_lookup,
                state=ctx.state,
            )
            logger.info(
                "[%s] values模式检测到 handoff_batch: total=%d, first_target=%s, direct_findings=%d, planned_goals=%d, multi_intent=%s",
                ctx.node_name,
                len(normalized_batch),
                target_agent,
                len(direct_findings),
                planned_goal_count,
                enable_multi_intent_mode,
            )
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
        "messages": [create_ai_message(error_msg)],
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
        ) = _prepare_streaming_inference_state(state)

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


def _build_tool_entry(tool_obj: Any, groups: Optional[set[str]] = None) -> Dict[str, Any]:
    """构造工具候选条目。"""
    return {
        "tool": tool_obj,
        "name": _resolve_tool_name(tool_obj),
        "groups": {str(item).strip().lower() for item in (groups or set()) if str(item).strip()},
    }


def _normalize_policy_tokens(raw_value: Any) -> set[str]:
    """标准化策略 token 列表。"""
    if raw_value is None:
        return set()
    if isinstance(raw_value, str):
        candidates = [raw_value]
    elif isinstance(raw_value, list):
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


def _apply_tool_governance_policy(tool_entries: list[Dict[str, Any]], agent_name: str) -> list[Any]:
    """按工具治理策略过滤工具候选集。"""
    raw_tools = [entry["tool"] for entry in tool_entries]
    fail_mode = "compat"

    try:
        from app.services.config_resolver import ConfigResolver

        settings = ConfigResolver.get_tool_governance_settings()
        fail_mode = str(settings.get("fail_mode") or "compat").strip().lower() or "compat"
        if not settings.get("enabled", False):
            return raw_tools

        policy_layers = ConfigResolver.get_tool_policy_layers(agent_name)
        merged_policy = policy_layers.get("merged_policy")
        if not isinstance(merged_policy, dict):
            merged_policy = {}

        allow_tokens = _normalize_policy_tokens(merged_policy.get("allow"))
        deny_tokens = _normalize_policy_tokens(merged_policy.get("deny"))

        default_allow = fail_mode in {"compat", "allow"}
        if allow_tokens:
            default_allow = False

        selected: list[Any] = []
        denied_names: list[str] = []

        for entry in tool_entries:
            allowed = default_allow or _match_policy_tokens(entry, allow_tokens)
            if _match_policy_tokens(entry, deny_tokens):
                allowed = False

            if allowed:
                selected.append(entry["tool"])
            else:
                denied_names.append(entry.get("name", "unknown"))

        logger.info(
            "工具治理生效: agent=%s, allow=%s, deny=%s, selected=%s, denied=%s",
            agent_name,
            sorted(allow_tokens),
            sorted(deny_tokens),
            [entry.get("name", "unknown") for entry in tool_entries if entry["tool"] in selected],
            denied_names,
        )
        return selected
    except Exception as exc:
        logger.warning(
            "工具治理过滤失败，降级继续: agent=%s, fail_mode=%s, error=%s",
            agent_name,
            fail_mode,
            exc,
        )
        if fail_mode in {"deny", "minimal"}:
            return []
        return raw_tools


def _get_common_tool_entries() -> list[Dict[str, Any]]:
    """构建共享工具候选条目（未应用治理策略）。"""
    entries: list[Dict[str, Any]] = []

    # 图片分析工具
    try:
        from app.ai.tools.vision_tool import analyze_image, is_vision_configured
        if is_vision_configured():
            entries.append(_build_tool_entry(analyze_image, {"group:vision"}))
            logger.debug("共享工具: 已加载 analyze_image")
    except Exception as e:
        logger.warning("Vision 工具加载失败: %s", e)

    # 文件读取工具
    try:
        from app.ai.tools.file_tools import read_uploaded_file, read

        entries.append(_build_tool_entry(read_uploaded_file, {"group:file"}))
        entries.append(_build_tool_entry(read, {"group:file"}))
        logger.debug("共享工具: 已加载 read_uploaded_file/read")
    except Exception as e:
        logger.warning("文件读取工具加载失败: %s", e)

    return entries


def _get_common_tools():
    """获取所有专家共享的工具（图片分析、文件读取）。"""
    return _apply_tool_governance_policy(_get_common_tool_entries(), agent_name="common")


def _get_supervisor_tools():
    """获取 Supervisor 直接使用的简单工具。
    
    包含：
    - 知识库检索 (knowledge_search)
    - 联网搜索 (tavily_search)
    - 绘图 (fig_inter)
    - 图片分析和文件读取（共享工具）
    
    注意：sql_inter 已移除，数据查询统一由 data_expert 处理，
    避免 Supervisor 直接执行 SQL 导致权限失败和无效重试。
    """
    entries = _get_common_tool_entries()
    
    # 绘图工具（sql_inter 已移至 data_expert 专用）
    try:
        from app.ai.tools.chatTools import fig_inter
        entries.append(_build_tool_entry(fig_inter, {"group:chart"}))
        logger.debug("Supervisor 工具: 已加载 fig_inter")
    except Exception as e:
        logger.warning("Supervisor 绘图工具加载失败: %s", e)
    
    # 知识库搜索工具
    try:
        from app.ai.tools.ragflow_tool import knowledge_search, is_ragflow_configured
        if is_ragflow_configured():
            entries.append(_build_tool_entry(knowledge_search, {"group:knowledge"}))
            logger.debug("Supervisor 工具: 已加载 knowledge_search")
    except Exception as e:
        logger.warning("Supervisor 知识库工具加载失败: %s", e)
    
    # 联网搜索工具 (TavilySearch)
    try:
        from app.ai.tools.chatTools import search_tool
        if search_tool is not None:
            entries.append(_build_tool_entry(search_tool, {"group:web"}))
            logger.debug("Supervisor 工具: 已加载 TavilySearch 联网搜索")
        else:
            logger.info(
                "联网搜索未加入 Supervisor: search_tool 未加载（请检查 TAVILY_API_KEY 或安装 langchain-tavily）"
            )
    except Exception as e:
        logger.warning("Supervisor 联网搜索工具加载失败: %s", e)

    return _apply_tool_governance_policy(entries, agent_name="supervisor")


def _create_task_handoff_tool(agent_name: str, description: str):
    """创建带任务描述的 Handoff 工具。
    
    该工具允许 Supervisor 将任务委派给特定的 Agent，并提供明确的任务描述。
    
    修改说明：
    - 返回 JSON 格式的委派指令，而不是 Command 对象
    - Command 对象会被 ToolNode 序列化为字符串，导致无法正确路由
    - 外层条件边会检测 pending_handoff 字段并路由到对应专家
    """
    
    name = f"assign_to_{agent_name}"
    
    @tool(name, description=description)
    def handoff_tool(
        task_description: Annotated[str, "详细描述下一个专家需要完成的任务，包含所有相关上下文和指令"],
        frame: Annotated[Optional[Dict[str, Any]], "结构化上下文（可选）：metric/time/dimensions 或 todo_action/todo_fields/tool_observations"] = None,
        turn_act_hint: Annotated[Optional[str], "回合行为提示（可选）：NEW_QUERY/SUPPLEMENT/CORRECTION/CONFIRM"] = None,
    ) -> str:
        """将任务委派给指定的专家 Agent。返回 JSON 格式的委派指令。"""
        # [Phase 2] 标准化输出：使用 HandoffResult 模型生成纯 JSON
        result = HandoffResult(
            target_agent=agent_name,
            task_description=task_description,
            frame=frame if isinstance(frame, dict) else None,
            turn_act_hint=str(turn_act_hint or "").strip() or None,
        )
        return result.model_dump_json(ensure_ascii=False)
    
    return handoff_tool



async def _preprocess_multimodal(state: MultiAgentState) -> dict:
    """预处理节点：1. 验证消息序列 2. 分析图片/文件内容。
    
    职责：
    - 验证消息完整性，移除不完整的 tool_calls
    - 修复 DeepSeek reasoning_content（如果启用思考模式）
    - 分析用户上传的图片和文件，为 Supervisor 路由提供上下文
    """
    messages = state.get("messages", [])
    if not messages:
        return {}
    
    # 获取 StreamWriter 用于发送自定义事件
    writer = get_stream_writer()
    
    # 显式标记 Graph 类型，用于 resume 时检测
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
    # TODO: 等待 DeepSeek 官方修复此 API 限制后可移除此补丁
    from app.ai.message_utils import validate_messages
    
    enable_thinking = state.get("enable_thinking", False)
    model_id = state.get("model_id")
    
    # 判断是否需要执行 DeepSeek 补丁
    should_fix_reasoning = enable_thinking
    if model_id and ("deepseek" in model_id.lower() or "reasoner" in model_id.lower()):
        should_fix_reasoning = True
    
    # 执行消息验证（包括 DeepSeek 修复）
    original_count = len(messages)
    validated = validate_messages(messages, fix_reasoning=should_fix_reasoning)
    
    if len(validated) != original_count or should_fix_reasoning:
        logger.debug(
            "预处理节点: 消息验证完成, should_fix=%s, 消息数 %d -> %d",
            should_fix_reasoning, original_count, len(validated)
        )
        updates["messages"] = validated
        messages = validated  # 使用验证后的消息继续处理
    
    # ========== 2. 护栏验证（借鉴 OpenAI Agents SDK Guardrails） ==========
    last_msg = messages[-1]
    content = str(getattr(last_msg, "content", ""))
    
    # 只对用户消息执行护栏验证
    from langchain_core.messages import HumanMessage
    if isinstance(last_msg, HumanMessage):
        from app.ai.guardrails import guardrail_runner
        
        passed, sanitized_content, reason = await guardrail_runner.validate_input(content)
        
        if not passed:
            logger.warning("护栏拦截: %s", reason)
            emit_status(writer, message=f"安全检查: {reason}", node="preprocess")
            # 返回拒绝消息（可以选择直接拦截或继续处理）
            # 这里选择记录日志但继续处理，让 LLM 自行决定
        
        if sanitized_content and sanitized_content != content:
            logger.info("护栏: 输入已脱敏处理")
            content = sanitized_content
    
    # ========== 3. 系统上下文注入 ==========
    # 为所有 Agent 提供当前时间与待办锚点等系统级信息
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
    context_parts = [f"当前时间: {current_time}"]

    current_todo_id = state.get("current_todo_id")
    if current_todo_id:
        context_parts.append(
            "当前选中待办ID: "
            f"{current_todo_id}。若用户要求“描述里补充/添加外部信息（天气、股价等）”，"
            "应优先按更新该待办处理。"
        )

    updates["system_context"] = "\n".join(context_parts)
    
    # ========== 4. Skills RAG 检索 ==========
    # 根据用户消息检索相关技能，为后续 Agent 提供专业知识上下文
    updates["skill_candidates"] = []
    updates["selected_skill_ids"] = []
    updates["skill_context"] = None
    updates["skill_injection_meta"] = None

    try:
        from app.services.skill_service import SkillService

        if content:
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
            updates["skill_injection_meta"] = skill_injection_meta

            if selected_skill_ids:
                logger.info(
                    "预处理节点: 检索到 %d 个相关技能: %s", len(selected_skill_ids), selected_skill_ids
                )
                emit_status(
                    writer,
                    message=f"已加载 {len(selected_skill_ids)} 个相关技能: {selected_skill_ids}",
                    node="preprocess",
                )
            else:
                logger.info(
                    "预处理节点: 技能检索完成但未命中，候选=%d",
                    len(skill_candidates),
                )
    except Exception as e:
        logger.warning("预处理节点: 技能检索失败 - %s", e)
    
    # 检测是否包含图片 URL（Markdown 格式）
    image_urls = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content)
    
    if image_urls:
        logger.info("预处理节点: 检测到 %d 张图片，开始分析...", len(image_urls))
        
        # 发送分析状态给前端
        emit_status(
            writer,
            message=f"正在分析 {len(image_urls)} 张图片...",
            node="preprocess",
            phase="processing",
        )
        
        try:
            from app.ai.tools.vision_tool import analyze_image, is_vision_configured
            if is_vision_configured():
                # 分析第一张图片
                analysis_result = analyze_image.invoke({"image_url": image_urls[0]})
                logger.info("预处理节点: 图片分析完成 - %s", str(analysis_result)[:100])
                updates["attachment_analysis"] = f"[图片分析结果] {analysis_result}"
                
                # 进入回答生成阶段
                emit_status(
                    writer,
                    message="正在生成回答...",
                    node="preprocess",
                    phase="generating",
                )
        except Exception as e:
            logger.warning("预处理节点: 图片分析失败 - %s", e)
    
    # 检测是否包含文件 URL
    file_patterns = re.findall(r'\[([^\]]+)\]\s+([^\s]+)\s+\(URL:\s*([^)]+)\)', content)
    if file_patterns:
        file_info = [(name, url) for _, name, url in file_patterns]
        logger.info("预处理节点: 检测到 %d 个文件", len(file_info))
        updates["attachment_analysis"] = f"[文件信息] 用户上传了文件: {', '.join([f[0] for f in file_info])}"
    logger.info("jjk-multi-agent: 预处理节点: 更新状态 - %s", updates)
    return updates


async def create_multi_agent_graph(
    checkpointer=None, 
    enable_thinking: bool = False, 
    model_id: str = None
):
    """创建多智能体 Supervisor 图（手动构建）。
    
    架构：
        START -> preprocess -> supervisor -> [data_expert  | todo_expert]
                                      |
                                      +-> Postprocess -> END
                                      
    注意：专家执行完后会直接返回 END（或者是返回结果给 Supervisor，这里使用 Command(graph=Command.PARENT) 跳转）
    实际上，由于 Handoff 工具使用了 Send()，子 Agent 执行完后，LangGraph 默认行为是结束当前步骤。
    我们需要确保子 Agent 的结果能被 postprocess 捕获（或者直接保存）。
    
    调整：
    专家 Agent 执行完毕后，流程应该汇聚到 postprocess。
    """
    
    # 获取 LLM
    llm = get_scene_llm(
        scene_key=SCENE_KEY_MULTI_AGENT_SUPERVISOR,
        force_thinking=enable_thinking,
        model_id=model_id,
    )
    
    # 1. 创建 Handoff 工具（使用常量定义）
    handoff_tools = [
        _create_task_handoff_tool(agent_type, desc)
        for agent_type, desc in AGENT_DESCRIPTIONS.items()
    ]
    
    # 2. 获取 Supervisor 的简单工具（可以直接调用）
    supervisor_simple_tools = _get_supervisor_tools()
    
    # 3. 创建 Supervisor Agent（handoff 工具 + 简单工具）
    # 使用 create_react_agent，支持工具返回 Command 对象
    supervisor_agent = create_react_agent(
        llm,
        handoff_tools + supervisor_simple_tools,
        prompt=SUPERVISOR_PROMPT,
        name="supervisor",
    )
    
    # 4. 创建 data_expert（使用 DataGraph）
    from app.ai.workflow.data_graph import create_data_graph
    data_graph_app = create_data_graph(
        model=llm,
        enable_thinking=enable_thinking,
        model_id=model_id,
        checkpointer=checkpointer
    )
    
    # 5. 创建 todo_expert（使用 TodoGraph）
    from app.ai.workflow.todo_graph import create_todo_graph
    todo_graph_app = create_todo_graph(
        model=llm, 
        enable_thinking=enable_thinking,
        checkpointer=checkpointer 
    )

    # 6. 为专家节点创建流式包装器（模块级工厂）
    # wrapper 内部通过统一 orchestrator 运行流循环并发射事件。

    # 7. 定义后处理节点
    def _postprocess(state: MultiAgentState) -> dict:
        """后处理节点：调试日志 + 保存对话到数据库 + 清理缓存。"""
        messages = state.get("messages", [])
        user_id = state.get("user_id")
        thread_id = state.get("thread_id")
        
        # 橙色 ANSI 颜色代码（便于调试）
        ORANGE = "\033[38;5;208m"
        RESET = "\033[0m"
        
        # 打印调试日志
        logger.info(f"{ORANGE}{'='*60}{RESET}")
        logger.info(f"{ORANGE}[多智能体-消息列表] 共 {len(messages)} 条消息:{RESET}")
        for i, msg in enumerate(messages):
            logger.info(f"{ORANGE}  [{i}] {msg}{RESET}")
        logger.info(f"{ORANGE}{'='*60}{RESET}")
        
        # 验证必要参数
        if not thread_id:
            logger.warning("后处理节点: 缺少 thread_id，跳过保存")
            return {}
        
        if not messages:
            logger.warning("后处理节点: 消息为空，跳过保存")
            return {}
        
        # 保存对话到数据库（使用智能图片补充逻辑）
        try:
            from app.db.session import get_db_context
            from app.repositories import chat_repo
            from langchain_core.messages import HumanMessage, AIMessage
            
            # 过滤掉内部 Handoff 消息 (name 不为空的 HumanMessage)
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
        
        # 清理 DataFrame 缓存
        if thread_id:
            try:
                from app.ai.tools.chatTools import cleanup_thread_dataframes
                cleanup_thread_dataframes(thread_id)
                logger.debug("多智能体后处理: DataFrame 缓存已清理")
            except Exception as e:
                logger.warning("多智能体后处理-清理缓存失败: %s", e)
        
        # 统一清理临时状态字段，确保下一轮从干净状态开始
        # 设计原则：出口清理，符合"资源在哪里分配就在哪里释放"
        # 详见：docs/开发文档/架构设计/AI模块设计.md - 状态生命周期管理
        return {
            # === 委派控制 ===
            "pending_handoff": None,
            "handoff_queue": [],
            "completed_handoffs": [],
            "handoff_execution_trace": [],
            "multi_intent_mode": False,
            
            # === 操作状态 ===
            "pending_operation": None,
            "user_confirmed": None,
            "quick_mode": None,
            
            # === 评估状态 ===
            "evaluation": None,
            "evaluation_route": "postprocess",
            "iteration_count": 0,  # 重置为 0，而非 None
            
            # === 意图识别 ===
            "detected_intent": None,
            "intent_route": None,
            "intent_mode": "model_primary",
            
            # === 预处理结果（下一轮会重新生成）===
            "attachment_analysis": None,
            "skill_candidates": [],
            "selected_skill_ids": [],
            "skill_context": None,
            "skill_injection_meta": None,
            "turn_id": None,

            # === 交付导向状态 ===
            "intent_plan": None,
            "task_graph": None,
            "task_runs": [],
            "deliverables": [],
            "coverage_report": None,
            "final_answer": None,
            "delivery_meta": {},

            # === 稳态恢复观测 ===
            "runtime_recovery_state": _build_runtime_recovery_state(
                state,
                fallback_route="none",
                fallback_triggered=False,
                plugin_lifecycle_status=_resolve_plugin_lifecycle_status(state),
            ),
        }

    # 8. 定义规划节点（问题合同）
    def _planner_node(state: MultiAgentState) -> dict:
        """生成当前轮 intent_plan，并向前端发送 plan_ready 事件。"""
        if not _is_delivery_orchestrator_v2_enabled():
            return {}

        planner_mode = str(state.get("intent_mode") or "model_primary")
        intent_plan = _build_planner_intent_plan(state, llm=llm, mode=planner_mode)
        source = str(intent_plan.get("source") or "unknown")
        fallback_meta = intent_plan.get("fallback_meta") if isinstance(intent_plan.get("fallback_meta"), dict) else {}
        fallback_reason = str(fallback_meta.get("reason") or "").strip()

        status_message = f"已识别 {len(intent_plan.get('goals', []))} 个待答目标，准备进入执行阶段。"
        if source == "heuristic_fallback":
            suffix = f"（模型主判定失败，已切换规则兜底：{fallback_reason or 'unknown'}）"
            status_message = f"已识别 {len(intent_plan.get('goals', []))} 个待答目标，准备进入执行阶段{suffix}。"

        writer = get_stream_writer()
        emit_status(
            writer,
            message=status_message,
            node="planner",
        )
        if _is_sse_delivery_events_v2_enabled():
            emit_plan_ready(writer, intent_plan, node="planner")

        return {"intent_plan": intent_plan}

    # 9. 定义评估节点（判断专家工作是否完成）
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
                        "task_description": pending_handoff.get("task_description"),
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
                            "task_description": latest_completed[0].get("task_description"),
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

        intent_plan = _ensure_intent_plan_covers_runtime(state)
        deliverables = _build_delivery_artifacts(state)
        coverage_report = _compute_coverage_report(intent_plan, deliverables)

        writer = get_stream_writer()
        emit_status(
            writer,
            message="已完成问题覆盖检查，正在整理最终答复。",
            node="coverage_gate",
        )
        if _is_sse_delivery_events_v2_enabled():
            emit_coverage_check(writer, coverage_report, node="coverage_gate")

        return {
            "intent_plan": intent_plan,
            "deliverables": deliverables,
            "coverage_report": coverage_report,
        }

    def _final_composer_node(state: MultiAgentState) -> dict:
        """唯一对外出口：生成最终答复并触发 final_answer 事件。"""
        if not _is_delivery_orchestrator_v2_enabled():
            return {}

        intent_plan = _ensure_intent_plan_covers_runtime(state)
        deliverables = list(state.get("deliverables") or _build_delivery_artifacts(state))
        coverage_report = dict(state.get("coverage_report") or _compute_coverage_report(intent_plan, deliverables))
        final_answer = _render_final_answer(intent_plan, coverage_report)

        writer = get_stream_writer()
        emit_status(writer, message="结论已生成，正在返回最终答复。", node="final_composer")
        if _is_sse_delivery_events_v2_enabled():
            emit_final_answer(
                writer,
                final_answer,
                meta={
                    "coverage_pass": bool(coverage_report.get("pass")),
                    "missing_goals": len(coverage_report.get("missing_goals") or []),
                    "goal_count": len(intent_plan.get("goals") or []),
                },
                node="final_composer",
            )
        else:
            emit_token(writer, final_answer, node="final_composer")

        return {
            "messages": [create_ai_message(final_answer)],
            "intent_plan": intent_plan,
            "deliverables": deliverables,
            "coverage_report": coverage_report,
            "final_answer": final_answer,
            "delivery_meta": {
                "coverage_pass": bool(coverage_report.get("pass")),
                "missing_goal_count": len(coverage_report.get("missing_goals") or []),
            },
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
            "messages": [create_ai_message(summary_text)],
            "evaluation": "complete",
            "evaluation_route": "postprocess",
        }

    # 10. 条件路由函数
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

    # 11. 构建 StateGraph（简化架构：移除 knowledge_expert）
    workflow = StateGraph(MultiAgentState)

    # 添加节点
    workflow.add_node("preprocess", _preprocess_multimodal)
    workflow.add_node("planner", _planner_node)
    # 修复: Supervisor 也需要流式包装器,确保 LLM 输出是流式的
    workflow.add_node("supervisor", _create_streaming_agent_wrapper(supervisor_agent, "supervisor"))
    workflow.add_node("data_expert", _create_streaming_agent_wrapper(data_graph_app, "data_expert"))
    workflow.add_node("todo_expert", _create_streaming_agent_wrapper(todo_graph_app, "todo_expert"))
    workflow.add_node("evaluate", _evaluate_expert_work)
    workflow.add_node("coverage_gate", _coverage_gate_node)
    workflow.add_node("final_composer", _final_composer_node)
    workflow.add_node("summarize", _summarize_multi_intent)
    workflow.add_node("postprocess", _postprocess)

    # 架构规则：不使用独立的 intent_classify 节点，由 Supervisor 统一处理意图路由
    
    # 添加边
    workflow.add_edge(START, "preprocess")
    workflow.add_edge("preprocess", "planner")
    workflow.add_edge("planner", "supervisor")
    
    # 专家执行完 -> 评估节点
    workflow.add_edge("data_expert", "evaluate")
    workflow.add_edge("todo_expert", "evaluate")
    
    # Supervisor 条件路由：检查 pending_handoff 或工具调用
    def supervisor_should_continue(state: MultiAgentState) -> str:
        """判断 Supervisor 下一步路由。
        
        路由逻辑（增强版 - 借鉴 TypeAgent Dispatcher）：
        1. 如果有 pending_handoff → 使用 Schema 路由到对应专家
        2. 如果有其他 tool_calls → 路由到 evaluate
        3. 否则 → 路由到 postprocess
        
        增强：
        - 使用 route_by_schema 进行 Schema 匹配路由
        - 添加 Handoff 校验，记录无效目标并重新路由
        """
        from app.ai.exceptions import HandoffValidationError
        
        # 优先检查 pending_handoff（由 handoff 工具设置）
        pending_handoff = state.get("pending_handoff")
        if pending_handoff:
            target_agent = pending_handoff.get("target_agent")
            detected_intent = pending_handoff.get("detected_intent", "unknown")
            
            logger.info(f"Supervisor 检测到 pending_handoff，目标: {target_agent}, 意图: {detected_intent}")
            
            # 有效的 Agent 列表（与图内实际可路由节点保持一致）
            valid_targets = set(WORKFLOW_AGENT_NODE_BY_TYPE.keys())
            
            # 使用 Schema 路由增强（借鉴 TypeAgent Dispatcher）
            # 如果 target_agent 无效但有 detected_intent，尝试使用 Schema 路由
            if target_agent not in valid_targets and detected_intent:
                schema_route = route_by_schema(detected_intent)
                if schema_route in WORKFLOW_AGENT_NODES:
                    logger.info(f"Schema 路由增强: intent={detected_intent} -> {schema_route}")
                    return schema_route
            
            if target_agent in valid_targets:
                # 有效的 Handoff
                return WORKFLOW_AGENT_NODE_BY_TYPE[target_agent]
            else:
                # 无效的 target_agent - 记录错误并处理
                error = HandoffValidationError(
                    f"无效的 Handoff 目标 Agent: {target_agent}，"
                    f"有效值为 {list(valid_targets)}",
                    invalid_target=target_agent
                )
                logger.error(str(error))

                # 策略：直接结束（也可以选择重新路由回 Supervisor 让 LLM 重试）
                # 这里选择直接结束，避免无限循环
                logger.warning("清除无效 Handoff，直接进入 postprocess")
                return "postprocess"
        
        # 检查是否有其他工具调用
        messages = state.get("messages", [])
        if not messages:
            return "postprocess"
        
        last_msg = messages[-1]
        has_tool_calls = hasattr(last_msg, 'tool_calls') and last_msg.tool_calls
        
        if has_tool_calls:
            logger.debug("Supervisor 有工具调用，路由到 evaluate")
            return "evaluate"

        if bool(state.get("multi_intent_mode")):
            logger.debug("Supervisor 处于复合任务模式，路由到 evaluate 进行覆盖检查")
            return "evaluate"

        logger.debug("Supervisor 直接回复，路由到 postprocess")
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
    
    # 评估节点 -> 条件路由
    workflow.add_conditional_edges(
        "evaluate",
        should_continue_routing,
        {
            "postprocess": "postprocess",  # 任务完成
            "supervisor": "supervisor",    # 返回 Supervisor 重新评估
            "data_expert": "data_expert",  # 队列中下一位专家
            "todo_expert": "todo_expert",  # 队列中下一位专家
            "coverage_gate": "coverage_gate",  # 完整性门禁
            "summarize": "summarize",      # 复合任务统一汇总
        }
    )

    workflow.add_edge("coverage_gate", "final_composer")
    workflow.add_edge("final_composer", "postprocess")
    workflow.add_edge("summarize", "postprocess")
    
    # Postprocess -> END
    workflow.add_edge("postprocess", END)

    # 6. 设置 Checkpointer
    if checkpointer is None:
        checkpointer = await get_checkpointer()
    
    # 7. 编译
    graph = workflow.compile(checkpointer=checkpointer)
    
    logger.info(
        "多智能体图编译完成（Manual Graph + Custom Handoff，启用思考: %s，模型: %s）", 
        enable_thinking, 
        model_id or "默认"
    )
    
    return graph


# 全局多智能体图缓存（线程安全）
_MULTI_AGENT_GRAPH_CACHE: Dict[Tuple[bool, Optional[str]], Any] = {}
_CACHE_LOCKS: Dict[Tuple[bool, Optional[str]], asyncio.Lock] = {}


async def get_multi_agent_graph(enable_thinking: bool = False, model_id: str = None):
    """获取全局多智能体图实例（缓存），线程安全。
    
    Args:
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识
        
    Returns:
        编译后的多智能体图实例
    """
    cache_key = (enable_thinking, model_id)
    
    # 获取或创建锁（防止并发创建）
    if cache_key not in _CACHE_LOCKS:
        _CACHE_LOCKS[cache_key] = asyncio.Lock()
    
    # 使用锁保护缓存访问
    async with _CACHE_LOCKS[cache_key]:
        if cache_key not in _MULTI_AGENT_GRAPH_CACHE:
            logger.info(
                "创建新的多智能体图实例: enable_thinking=%s, model_id=%s", 
                enable_thinking, model_id
            )
            _MULTI_AGENT_GRAPH_CACHE[cache_key] = await create_multi_agent_graph(
                enable_thinking=enable_thinking, 
                model_id=model_id
            )
    
    return _MULTI_AGENT_GRAPH_CACHE[cache_key]
