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
import re
from typing import Annotated, Sequence, TypedDict, Optional, Literal, Any, Dict, Tuple, Callable

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
from app.ai.events import emit_status
from app.ai.protocol import (
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


WORKFLOW_AGENT_NODE_BY_TYPE = {
    AgentType.DATA: "data_expert",
    AgentType.TODO: "todo_expert",
}
WORKFLOW_AGENT_NODES = set(WORKFLOW_AGENT_NODE_BY_TYPE.values())


class StreamingProtocolAdapter(TypedDict):
    """streaming_wrapper 协议适配层。"""

    parse_kb_images: Callable[[str], Dict[str, str]]
    should_filter_content: Callable[[Any], bool]
    extract_latest_handoff_from_messages: Callable[[Sequence[BaseMessage]], Optional[Dict[str, Any]]]


class StreamingEventEmitterAdapter(TypedDict):
    """streaming_wrapper 事件发射适配层。"""

    emit_token: Callable[..., None]
    emit_thinking: Callable[..., None]
    emit_tool_start: Callable[..., None]
    emit_tool_end: Callable[..., None]
    emit_status: Callable[..., None]
    emit_result: Callable[..., None]
    emit_kb_images: Callable[..., None]


def _build_streaming_protocol_adapter(parser: Any) -> StreamingProtocolAdapter:
    """构建协议适配器，屏蔽对具体 Parser 类的直接耦合。"""

    return {
        "parse_kb_images": parser.parse_kb_images,
        "should_filter_content": parser.should_filter_content,
        "extract_latest_handoff_from_messages": parser.extract_latest_handoff_from_messages,
    }


def _build_streaming_event_emitter_adapter(
    *,
    emit_token: Callable[..., None],
    emit_thinking: Callable[..., None],
    emit_tool_start: Callable[..., None],
    emit_tool_end: Callable[..., None],
    emit_status: Callable[..., None],
    emit_result: Callable[..., None],
    emit_kb_images: Callable[..., None],
) -> StreamingEventEmitterAdapter:
    """构建事件发射适配器，统一管理 streaming_wrapper 事件出口。"""

    def _emit_tool_start_with_schema(writer, payload: StreamingToolStartPayload, node: str = "") -> None:
        emit_tool_start(writer, payload["name"], payload["input"], node=node)

    def _emit_result_with_schema(writer, payload: StreamingResultPayload, node: str = "") -> None:
        emit_result(
            writer,
            data_type=payload["data_type"],
            data=payload["data"],
            message=payload["message"],
            node=node,
        )

    def _emit_kb_images_with_schema(writer, payload: StreamingKbImagesPayload, node: str = "") -> None:
        emit_kb_images(writer, payload["images"], node=node)

    return {
        "emit_token": emit_token,
        "emit_thinking": emit_thinking,
        "emit_tool_start": _emit_tool_start_with_schema,
        "emit_tool_end": emit_tool_end,
        "emit_status": emit_status,
        "emit_result": _emit_result_with_schema,
        "emit_kb_images": _emit_kb_images_with_schema,
    }


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
) -> Dict[str, Any]:
    """构造命中 handoff 后的增量返回结构。"""
    other_keys = {k: v for k, v in final_state.items() if k != "messages"}
    ret = other_keys.copy()
    ret["messages"] = list(delta_messages)
    ret["pending_handoff"] = handoff_data
    return ret


def _emit_kb_images_from_delta_messages(
    delta_messages: Sequence[BaseMessage],
    kb_images: Dict[str, str],
    protocol_adapter: StreamingProtocolAdapter,
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
    node_name: str,
) -> None:
    """从增量 ToolMessage 中提取 KB_IMAGES 并发送事件。"""

    for tool_msg in reversed(delta_messages):
        if not isinstance(tool_msg, ToolMessage):
            continue
        tool_content = str(getattr(tool_msg, "content", ""))
        if not tool_content:
            continue
        new_images = protocol_adapter["parse_kb_images"](tool_content)
        if new_images:
            kb_images.update(new_images)
            logger.info("[%s] 从 values 模式提取 kb_images: %s 个", node_name, len(new_images))
            kb_images_payload = build_streaming_kb_images_payload(kb_images)
            event_emitter_adapter["emit_kb_images"](writer, kb_images_payload, node=node_name)


def _emit_tool_start_events_from_ai_message(
    ai_message: Any,
    sent_tool_call_ids: set,
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
    node_name: str,
) -> bool:
    """从 AIMessage 的 tool_calls 发送 tool_start 事件。"""
    if not (hasattr(ai_message, "tool_calls") and ai_message.tool_calls):
        return False

    for tool_call in ai_message.tool_calls:
        tool_call_id = tool_call.get("id")
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        tool_start_payload = build_streaming_tool_start_payload(tool_name, tool_args)
        if tool_call_id and tool_call_id not in sent_tool_call_ids and tool_start_payload:
            sent_tool_call_ids.add(tool_call_id)
            logger.debug("发送 tool_start 事件: %s", tool_name)
            if tool_name and "tavily" in (tool_name or "").lower():
                logger.info("联网搜索被调用: tool=%s, args=%s", tool_name, tool_args)
            event_emitter_adapter["emit_tool_start"](writer, tool_start_payload, node=node_name)

    return True


def _should_skip_values_text_message(
    msg_content: Any,
    msg_id: Any,
    emitted_message_ids: set,
    collected_content: Sequence[str],
    protocol_adapter: StreamingProtocolAdapter,
) -> bool:
    """values 模式文本补发去重判断。"""
    if protocol_adapter["should_filter_content"](msg_content):
        return True

    if msg_id and msg_id in emitted_message_ids:
        return True

    full_collected = "".join(collected_content)
    if msg_content and msg_content in full_collected:
        if len(msg_content) > 10:
            return True
        return True

    return False


def _emit_values_text_message(
    writer,
    node_name: str,
    ai_message: Any,
    msg_content: str,
    event_emitter_adapter: StreamingEventEmitterAdapter,
) -> None:
    """values 模式补发文本消息（兼容 result 结构化载荷）。"""
    result_payload = build_streaming_result_payload(ai_message, msg_content)
    if result_payload:
        event_emitter_adapter["emit_result"](writer, result_payload, node=node_name)
        return

    event_emitter_adapter["emit_token"](writer, msg_content, node=node_name)


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
    protocol_adapter: StreamingProtocolAdapter,
    kb_images: Dict[str, str],
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
    node_name: str,
) -> bool:
    """处理 messages 模式下的 ToolMessage（tool_end + KB_IMAGES）。"""
    if not isinstance(message, ToolMessage):
        return False

    tool_name = getattr(message, "name", "unknown")
    tool_content = str(getattr(message, "content", ""))
    tool_output = tool_content[:200]
    event_emitter_adapter["emit_tool_end"](writer, tool_name, tool_output, node=node_name)

    if tool_name and "tavily" in (tool_name or "").lower():
        logger.info("联网搜索返回: tool=%s, 结果长度=%s", tool_name, len(tool_content))

    new_images = protocol_adapter["parse_kb_images"](tool_content)
    if new_images:
        kb_images.update(new_images)
        logger.info("[%s] 从 ToolMessage 提取到 kb_images: %s 个", node_name, len(new_images))

    return True


def _emit_messages_mode_token(
    message: Any,
    protocol_adapter: StreamingProtocolAdapter,
    collected_content: list[str],
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
    node_name: str,
) -> None:
    """messages 模式发送文本 token（过滤内部协议内容）。"""
    content = getattr(message, "content", "")
    if not (content and isinstance(content, str)):
        return

    if protocol_adapter["should_filter_content"](content):
        logger.debug("[%s] 跳过内部协议内容", node_name)
        return

    collected_content.append(content)
    event_emitter_adapter["emit_token"](writer, content, node=node_name)


def _emit_messages_mode_thinking(
    message: Any,
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
    node_name: str,
) -> None:
    """messages 模式发送思考内容（reasoning/thinking）。"""
    additional = getattr(message, "additional_kwargs", {})
    reasoning = (
        additional.get("reasoning_content") or
        additional.get("thinking_content") or
        additional.get("thinking")
    )
    if reasoning:
        event_emitter_adapter["emit_thinking"](writer, reasoning, node=node_name)


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


def _handle_messages_mode_tool_call_chunks_noop(message: Any) -> None:
    """兼容保留：messages 模式仅扫描 tool_call_chunks，不发 tool_start。"""
    if not (hasattr(message, "tool_call_chunks") and message.tool_call_chunks):
        return

    for tool_call_chunk in message.tool_call_chunks:
        if not tool_call_chunk:
            continue

        _tool_call_index = tool_call_chunk.get("index")
        tool_name = tool_call_chunk.get("name")
        _tool_args = tool_call_chunk.get("args")

        if tool_name:
            # 由于 chunk 不含稳定 ID，此处仅保留扫描语义，不发事件。
            pass


def _dispatch_messages_mode_chunk(
    chunk: Any,
    protocol_adapter: StreamingProtocolAdapter,
    emitted_message_ids: set,
    collected_content: list[str],
    kb_images: Dict[str, str],
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
    node_name: str,
) -> None:
    """分发处理 stream_mode=messages 的单个 chunk。"""
    from langchain_core.messages import AIMessage, AIMessageChunk

    if not (isinstance(chunk, tuple) and len(chunk) == 2):
        return

    message, _metadata = chunk
    _record_emitted_message_id(message, emitted_message_ids)

    if node_name == "data_expert":
        return

    handled_tool_message = _handle_messages_mode_tool_message(
        message=message,
        protocol_adapter=protocol_adapter,
        kb_images=kb_images,
        event_emitter_adapter=event_emitter_adapter,
        writer=writer,
        node_name=node_name,
    )
    if handled_tool_message:
        return

    if not isinstance(message, (AIMessage, AIMessageChunk)):
        return

    _emit_messages_mode_token(
        message=message,
        protocol_adapter=protocol_adapter,
        collected_content=collected_content,
        event_emitter_adapter=event_emitter_adapter,
        writer=writer,
        node_name=node_name,
    )

    _handle_messages_mode_tool_call_chunks_noop(message)

    _emit_messages_mode_thinking(
        message=message,
        event_emitter_adapter=event_emitter_adapter,
        writer=writer,
        node_name=node_name,
    )


def _dispatch_values_mode_chunk(
    final_state: Dict[str, Any],
    protocol_adapter: StreamingProtocolAdapter,
    state: Dict[str, Any],
    initial_input_count: int,
    input_message_count: int,
    kb_images: Dict[str, str],
    sent_tool_call_ids: set,
    emitted_message_ids: set,
    collected_content: list[str],
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
    node_name: str,
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """分发处理 stream_mode=values 的单个 chunk。"""
    from langchain_core.messages import AIMessage

    messages = final_state.get("messages", [])
    delta_messages_for_scan = messages[initial_input_count:] if len(messages) > initial_input_count else []

    handoff_data = protocol_adapter["extract_latest_handoff_from_messages"](delta_messages_for_scan)
    if handoff_data and node_name == "supervisor":
        handoff_data = _augment_todo_handoff_with_observations(
            handoff_data,
            delta_messages_for_scan,
            state,
        )
        handoff_data = _augment_data_handoff_payload(handoff_data, state)
        target_agent = handoff_data.get("target_agent")
        logger.info("[%s] values模式检测到 handoff: target=%s", node_name, target_agent)
        handoff_return = _build_streaming_handoff_return(
            final_state=final_state,
            delta_messages=delta_messages_for_scan,
            handoff_data=handoff_data,
        )
        return input_message_count, handoff_return

    _emit_kb_images_from_delta_messages(
        delta_messages=delta_messages_for_scan,
        kb_images=kb_images,
        protocol_adapter=protocol_adapter,
        event_emitter_adapter=event_emitter_adapter,
        writer=writer,
        node_name=node_name,
    )

    new_messages = messages[input_message_count:] if len(messages) > input_message_count else []
    for new_message in new_messages:
        if not isinstance(new_message, AIMessage):
            continue

        emitted_tool_calls = _emit_tool_start_events_from_ai_message(
            ai_message=new_message,
            sent_tool_call_ids=sent_tool_call_ids,
            event_emitter_adapter=event_emitter_adapter,
            writer=writer,
            node_name=node_name,
        )
        if emitted_tool_calls:
            continue

        message_content = getattr(new_message, "content", "")
        message_id = getattr(new_message, "id", None)
        should_skip_message = _should_skip_values_text_message(
            msg_content=message_content,
            msg_id=message_id,
            emitted_message_ids=emitted_message_ids,
            collected_content=collected_content,
            protocol_adapter=protocol_adapter,
        )
        if should_skip_message:
            continue

        if message_content:
            logger.info("[%s] values 模式补发消息: %s...", node_name, message_content[:30])
            _emit_values_text_message(
                writer=writer,
                node_name=node_name,
                ai_message=new_message,
                msg_content=message_content,
                event_emitter_adapter=event_emitter_adapter,
            )
            collected_content.append(message_content)
            if message_id:
                emitted_message_ids.add(message_id)

    return len(messages), None


async def _run_streaming_dispatch_loop(
    agent: Any,
    pruned_state: Dict[str, Any],
    config: Any,
    protocol_adapter: StreamingProtocolAdapter,
    initial_input_count: int,
    input_message_count: int,
    emitted_message_ids: set,
    sent_tool_call_ids: set,
    collected_content: list[str],
    kb_images: Dict[str, str],
    state: Dict[str, Any],
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
    node_name: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """运行 streaming 双模式分发循环。"""
    final_state: Optional[Dict[str, Any]] = None
    next_input_count = input_message_count

    async for mode, chunk in agent.astream(
        pruned_state,
        config,
        stream_mode=["messages", "values"],
    ):
        if mode == "messages":
            _dispatch_messages_mode_chunk(
                chunk=chunk,
                protocol_adapter=protocol_adapter,
                emitted_message_ids=emitted_message_ids,
                collected_content=collected_content,
                kb_images=kb_images,
                event_emitter_adapter=event_emitter_adapter,
                writer=writer,
                node_name=node_name,
            )
            continue

        if mode != "values":
            continue

        final_state = chunk
        next_input_count, handoff_return = _dispatch_values_mode_chunk(
            final_state=final_state,
            protocol_adapter=protocol_adapter,
            state=state,
            initial_input_count=initial_input_count,
            input_message_count=next_input_count,
            kb_images=kb_images,
            sent_tool_call_ids=sent_tool_call_ids,
            emitted_message_ids=emitted_message_ids,
            collected_content=collected_content,
            event_emitter_adapter=event_emitter_adapter,
            writer=writer,
            node_name=node_name,
        )
        if handoff_return is not None:
            return final_state, handoff_return

    return final_state, None


def _handle_streaming_wrapper_exception(
    node_name: str,
    state: Dict[str, Any],
    error_text: str,
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
) -> Dict[str, Any]:
    """处理 streaming_wrapper 异常：优先 supervisor 兜底，其次统一友好错误。"""
    if node_name == "supervisor":
        fallback_handoff = _build_supervisor_fallback_handoff(state, error_text)
        if fallback_handoff:
            logger.warning(
                "[%s] 命中模型权限错误，降级兜底路由到 %s",
                node_name,
                fallback_handoff.get("target_agent"),
            )
            event_emitter_adapter["emit_status"](
                writer,
                message="模型服务暂不可用，已切换到待办兜底路由继续处理。",
                node=node_name,
            )
            return {
                "messages": [],
                "pending_handoff": fallback_handoff,
            }

    error_msg = _build_stream_error_message(error_text)
    event_emitter_adapter["emit_token"](writer, error_msg, node=node_name)
    return {"messages": [create_ai_message(error_msg)]}


async def _execute_streaming_wrapper(
    agent: Any,
    node_name: str,
    state: Dict[str, Any],
    config: Any,
    event_emitter_adapter: StreamingEventEmitterAdapter,
    writer,
) -> Dict[str, Any]:
    """执行单个专家节点的 streaming 编排与事件发射。"""
    final_state = None
    collected_content: list[str] = []
    kb_images: Dict[str, str] = {}

    from app.ai.protocol import AgentOutputParser

    protocol_adapter = _build_streaming_protocol_adapter(AgentOutputParser)

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

        sent_tool_call_ids = set()
        emitted_message_ids = set()

        await _prefill_emitted_message_ids(
            agent=agent,
            config=config,
            state_messages=state.get("messages", []),
            emitted_message_ids=emitted_message_ids,
            node_name=node_name,
        )

        logger.debug("[%s] 预填充 emitted_message_ids: %s 个", node_name, len(emitted_message_ids))

        final_state, handoff_return = await _run_streaming_dispatch_loop(
            agent=agent,
            pruned_state=pruned_state,
            config=config,
            protocol_adapter=protocol_adapter,
            initial_input_count=initial_input_count,
            input_message_count=input_message_count,
            emitted_message_ids=emitted_message_ids,
            sent_tool_call_ids=sent_tool_call_ids,
            collected_content=collected_content,
            kb_images=kb_images,
            state=state,
            event_emitter_adapter=event_emitter_adapter,
            writer=writer,
            node_name=node_name,
        )
        if handoff_return is not None:
            return handoff_return

        _log_streaming_output_statistics(node_name=node_name, collected_content=collected_content)
        return _build_streaming_delta_return(
            final_state=final_state,
            initial_input_count=initial_input_count,
            node_name=node_name,
        )

    except GraphInterrupt:
        raise
    except Exception as exc:
        logger.error("[%s]流式输出异常: %s", node_name, exc, exc_info=True)
        return _handle_streaming_wrapper_exception(
            node_name=node_name,
            state=state,
            error_text=str(exc),
            event_emitter_adapter=event_emitter_adapter,
            writer=writer,
        )


def _create_streaming_agent_wrapper(agent: Any, node_name: str):
    """创建可复用的 streaming wrapper 工厂（模块级）。"""
    from app.ai.events import emit_token, emit_thinking, emit_tool_start, emit_tool_end, emit_result, emit_kb_images

    event_emitter_adapter = _build_streaming_event_emitter_adapter(
        emit_token=emit_token,
        emit_thinking=emit_thinking,
        emit_tool_start=emit_tool_start,
        emit_tool_end=emit_tool_end,
        emit_status=emit_status,
        emit_result=emit_result,
        emit_kb_images=emit_kb_images,
    )

    async def streaming_wrapper(state, config):
        writer = get_stream_writer()
        return await _execute_streaming_wrapper(
            agent=agent,
            node_name=node_name,
            state=state,
            config=config,
            event_emitter_adapter=event_emitter_adapter,
            writer=writer,
        )

    return streaming_wrapper


def _get_common_tools():
    """获取所有专家共享的工具（图片分析、文件读取）。"""
    tools = []
    
    # 图片分析工具
    try:
        from app.ai.tools.vision_tool import analyze_image, is_vision_configured
        if is_vision_configured():
            tools.append(analyze_image)
            logger.debug("共享工具: 已加载 analyze_image")
    except Exception as e:
        logger.warning("Vision 工具加载失败: %s", e)
    
    # 文件读取工具
    try:
        from app.ai.tools.file_tools import read_uploaded_file, read

        tools.append(read_uploaded_file)
        tools.append(read)
        logger.debug("共享工具: 已加载 read_uploaded_file/read")
    except Exception as e:
        logger.warning("文件读取工具加载失败: %s", e)
    
    return tools


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
    tools = _get_common_tools()
    
    # 绘图工具（sql_inter 已移至 data_expert 专用）
    try:
        from app.ai.tools.chatTools import fig_inter
        tools.append(fig_inter)
        logger.debug("Supervisor 工具: 已加载 fig_inter")
    except Exception as e:
        logger.warning("Supervisor 绘图工具加载失败: %s", e)
    
    # 知识库搜索工具
    try:
        from app.ai.tools.ragflow_tool import knowledge_search, is_ragflow_configured
        if is_ragflow_configured():
            tools.append(knowledge_search)
            logger.debug("Supervisor 工具: 已加载 knowledge_search")
    except Exception as e:
        logger.warning("Supervisor 知识库工具加载失败: %s", e)
    
    # 联网搜索工具 (TavilySearch)
    try:
        from app.ai.tools.chatTools import search_tool
        if search_tool is not None:
            tools.append(search_tool)
            logger.debug("Supervisor 工具: 已加载 TavilySearch 联网搜索")
        else:
            logger.info(
                "联网搜索未加入 Supervisor: search_tool 未加载（请检查 TAVILY_API_KEY 或安装 langchain-tavily）"
            )
    except Exception as e:
        logger.warning("Supervisor 联网搜索工具加载失败: %s", e)
    
    return tools


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
    updates = {"_graph_type": "multi_agent"}
    
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
    from datetime import datetime
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
            
            # === 操作状态 ===
            "pending_operation": None,
            "user_confirmed": None,
            "quick_mode": None,
            
            # === 评估状态 ===
            "evaluation": None,
            "iteration_count": 0,  # 重置为 0，而非 None
            
            # === 意图识别 ===
            "detected_intent": None,
            "intent_route": None,
            
            # === 预处理结果（下一轮会重新生成）===
            "attachment_analysis": None,
            "skill_candidates": [],
            "selected_skill_ids": [],
            "skill_context": None,
            "skill_injection_meta": None,
        }

    # 8. 定义评估节点（判断专家工作是否完成）
    def _evaluate_expert_work(state: MultiAgentState) -> dict:
        """评估专家工作节点：判断是否需要继续委派其他专家。
        
        判断逻辑：
        1. 检查是否达到最大迭代次数（3次）
        2. 检查最后一条消息是否是 AI 回复（无 tool_calls）
        3. 如果任务完成或达到迭代限制，返回 'complete'
        4. 否则返回 'continue'，让 Supervisor 重新评估
        """
        messages = state.get("messages", [])
        iteration_count = state.get("iteration_count") or 0
        
        # 防止无限循环：最多 3 轮迭代
        MAX_ITERATIONS = 3
        if iteration_count >= MAX_ITERATIONS:
            logger.warning(
                "评估节点: 达到最大迭代次数 (%d)，结束任务",
                MAX_ITERATIONS
            )
            return {"evaluation": "complete"}
        
        # 检查最后一条消息
        if not messages:
            return {"evaluation": "complete"}
        
        last_msg = messages[-1]
        
        # 如果最后一条是 AI 消息且没有 tool_calls，认为任务完成
        has_tool_calls = hasattr(last_msg, 'tool_calls') and last_msg.tool_calls
        
        if last_msg.type == "ai" and not has_tool_calls:
            logger.info("评估节点: 专家已完成任务，结束流程")
            return {"evaluation": "complete"}
        
        # 否则可能需要继续处理（由 Supervisor 重新评估）
        logger.info("评估节点: 任务可能需要继续，返回 Supervisor")
        
        # 发送协调状态给前端
        writer = get_stream_writer()
        emit_status(writer, message="专家工作需要继续，正在协调其他专家...", node="evaluate")
        
        return {
            "evaluation": "continue",
            "iteration_count": iteration_count + 1
        }
    
    # 9. 条件路由函数
    def should_continue_routing(state: MultiAgentState) -> Literal["postprocess", "supervisor"]:
        """根据评估结果决定下一步:
        - complete: 流向 postprocess 结束
        - continue: 返回 supervisor 重新评估
        """
        evaluation = state.get("evaluation", "complete")
        if evaluation == "continue":
            return "supervisor"
        return "postprocess"

    # 10. 构建 StateGraph（简化架构：移除 knowledge_expert）
    workflow = StateGraph(MultiAgentState)

    # 添加节点
    workflow.add_node("preprocess", _preprocess_multimodal)
    # 修复: Supervisor 也需要流式包装器,确保 LLM 输出是流式的
    workflow.add_node("supervisor", _create_streaming_agent_wrapper(supervisor_agent, "supervisor"))
    workflow.add_node("data_expert", _create_streaming_agent_wrapper(data_graph_app, "data_expert"))
    workflow.add_node("todo_expert", _create_streaming_agent_wrapper(todo_graph_app, "todo_expert"))
    workflow.add_node("evaluate", _evaluate_expert_work)
    workflow.add_node("postprocess", _postprocess)

    # 架构规则：不使用独立的 intent_classify 节点，由 Supervisor 统一处理意图路由
    
    # 添加边
    workflow.add_edge(START, "preprocess")
    workflow.add_edge("preprocess", "supervisor")
    
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
        else:
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
        }
    )
    
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
