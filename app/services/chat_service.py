"""Chat 服务层：封装流式输出与 Agent 调用逻辑（中文注释）。

本模块实现：
- LangGraph 事件流处理（astream_events）
- SSE 协议升级，支持 token/thinking/tool_start/tool_end 事件
- 双写逻辑：LangGraph 自动写 PostgreSQL Checkpoint，业务数据写 PostgreSQL
"""
import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.ai.utils.message_factory import create_human_message

from app.ai.events import stopped_event
from app.ai.runtime.recovery_policy import (
    is_feature_flag_enabled,
    should_degrade_on_plugin_failure,
)
from app.ai.workflow import get_multi_agent_graph
from app.core.config import (
    DOCUMENT_MEMORY_HYBRID_MIN_SCORE,
    DOCUMENT_MEMORY_MAX_INJECTED_CHARS,
    DOCUMENT_MEMORY_MAX_RESULTS,
    DOCUMENT_MEMORY_TEXT_WEIGHT,
    DOCUMENT_MEMORY_VECTOR_WEIGHT,
    ENABLE_DOCUMENT_MEMORY,
    MEMORY_INTENT_ASYNC_ENABLED,
)
from app.core.constants import TOOL_OUTPUT_PREVIEW_LEN, TOOL_OUTPUT_STORAGE_LEN
from app.core.message_content import normalize_message_content
from app.core.utils import content_hash as _content_hash
from app.db.postgres_checkpoint import get_checkpointer, is_checkpointer_busy_error
from app.db.session import get_db_context
from app.repositories import chat_repo
from app.services.document_memory_service import (
    flush as flush_document_memory,
    recall as recall_document_memory,
)
from app.services.user_memory_intent_job_service import (
    enqueue_from_chat_message as enqueue_memory_intent_job,
)
from app.services.run_control_service import run_control_service


logger = logging.getLogger(__name__)


def _is_feature_enabled(env_name: str, fallback: bool) -> bool:
    """读取布尔开关，支持环境变量覆盖。"""

    return is_feature_flag_enabled(env_name, fallback)


def _is_document_memory_enabled(fallback: bool) -> bool:
    """读取文档化记忆总开关。"""

    try:
        from app.services.config_resolver import ConfigResolver

        resolved = ConfigResolver.get_bool("feature.enable_document_memory", fallback)
        return _is_feature_enabled("ENABLE_DOCUMENT_MEMORY", bool(resolved))
    except Exception:
        return _is_feature_enabled("ENABLE_DOCUMENT_MEMORY", fallback)


def _is_document_memory_recall_enabled(fallback: bool) -> bool:
    """单开关模式：召回链路跟随文档记忆总开关。"""

    return _is_document_memory_enabled(fallback)


def _is_document_memory_flush_enabled(fallback: bool) -> bool:
    """单开关模式：写入链路跟随文档记忆总开关。"""

    return _is_document_memory_enabled(fallback)


def _is_document_memory_hybrid_enabled(fallback: bool) -> bool:
    """单开关模式：混合检索链路跟随文档记忆总开关。"""

    return _is_document_memory_enabled(fallback)


def _is_memory_intent_async_enabled(fallback: bool) -> bool:
    """读取记忆意图异步入队开关。"""

    try:
        from app.services.config_resolver import ConfigResolver

        resolved = ConfigResolver.get_bool("memory.intent_async_enabled", fallback)
        return _is_feature_enabled("MEMORY_INTENT_ASYNC_ENABLED", bool(resolved))
    except Exception:
        return _is_feature_enabled("MEMORY_INTENT_ASYNC_ENABLED", fallback)


def _get_document_memory_max_results(fallback: int) -> int:
    """读取文档化记忆检索结果上限。"""

    try:
        from app.services.config_resolver import ConfigResolver

        resolved = ConfigResolver.get_int("memory.document.max_results", fallback)
        return max(1, int(resolved))
    except Exception:
        return max(1, int(fallback))


def _get_document_memory_max_injected_chars(fallback: int) -> int:
    """读取文档化记忆注入预算。"""

    try:
        from app.services.config_resolver import ConfigResolver

        resolved = ConfigResolver.get_int("memory.document.max_injected_chars", fallback)
        return max(120, int(resolved))
    except Exception:
        return max(120, int(fallback))


def _get_document_memory_weights(
    fallback_vector_weight: float,
    fallback_text_weight: float,
) -> tuple[float, float]:
    """读取文档化记忆混合检索权重。"""

    try:
        from app.services.config_resolver import ConfigResolver

        vector_weight = float(
            ConfigResolver.get_float("memory.document.hybrid.vector_weight", fallback_vector_weight)
        )
        text_weight = float(
            ConfigResolver.get_float("memory.document.hybrid.text_weight", fallback_text_weight)
        )
    except Exception:
        vector_weight = float(fallback_vector_weight)
        text_weight = float(fallback_text_weight)

    vector_weight = max(0.0, vector_weight)
    text_weight = max(0.0, text_weight)
    total = vector_weight + text_weight
    if total <= 0:
        return 0.7, 0.3
    return vector_weight / total, text_weight / total


def _get_document_memory_hybrid_min_score(fallback: float) -> float:
    """读取文档混合召回最小综合分。"""

    try:
        from app.services.config_resolver import ConfigResolver

        resolved = ConfigResolver.get_float("memory.document.hybrid.min_score", fallback)
        return max(0.0, float(resolved))
    except Exception:
        return max(0.0, float(fallback))


def _persist_document_memory_context(
    db: Any,
    *,
    user_id: int | None,
    prompt: str,
    thread_id: str,
    source_message_id: int | None,
    document_memory_context: str,
    document_memory_flush_enabled: bool,
    document_memory_recall_enabled: bool,
    memory_intent_async_enabled: bool,
    document_memory_max_results: int,
    document_memory_max_injected_chars: int,
    document_hybrid_min_score: float,
    document_vector_weight: float,
    document_text_weight: float,
) -> str:
    """写入阶段记忆处理：同步 flush 或异步入队。"""

    if not document_memory_flush_enabled or not user_id or not source_message_id:
        return document_memory_context

    if memory_intent_async_enabled:
        try:
            intent_job, created = enqueue_memory_intent_job(
                db,
                user_id=user_id,
                source_thread_id=thread_id,
                source_message_id=source_message_id,
                user_text=prompt,
            )
            logger.info(
                "记忆意图任务入队完成: user_id=%s, source_message_id=%s, job_id=%s, created=%s, status=%s",
                user_id,
                source_message_id,
                intent_job.id,
                created,
                intent_job.status,
            )
        except Exception as memory_error:
            logger.warning(
                "记忆意图任务入队失败，已降级跳过: user_id=%s, source_message_id=%s, error=%s",
                user_id,
                source_message_id,
                memory_error,
            )
        return document_memory_context

    try:
        persisted_doc_count = flush_document_memory(
            db,
            user_id=user_id,
            user_text=prompt,
            source_thread_id=thread_id,
            source_message_id=source_message_id,
        )
        if persisted_doc_count:
            logger.info(
                "压缩前文档记忆 flush 成功: user_id=%s, count=%d",
                user_id,
                persisted_doc_count,
            )
            if document_memory_recall_enabled:
                latest_document_context = recall_document_memory(
                    db,
                    user_id=user_id,
                    query_text=prompt,
                    max_results=document_memory_max_results,
                    max_injected_chars=document_memory_max_injected_chars,
                    min_score=document_hybrid_min_score,
                    vector_weight=document_vector_weight,
                    text_weight=document_text_weight,
                )
                if latest_document_context:
                    return latest_document_context
    except Exception as memory_error:
        logger.warning("写入文档化记忆失败，已降级: user_id=%s, error=%s", user_id, memory_error)

    return document_memory_context


def degrade_on_plugin_failure(error_text: str) -> Optional[str]:
    """识别插件链路故障并返回降级文案。"""

    if should_degrade_on_plugin_failure(error_text):
        return "插件能力暂时不可用，已自动切换到核心能力继续处理。"

    return None


# 注意：对话保存逻辑已移至 multi_agent_graph.py 的 postprocess 节点
# 不再需要在 service 层手动保存
# 单智能体模式已废弃（2026-01-31），系统默认使用多智能体模式


def _slice_current_turn_messages(messages: list, human_message_id: Optional[str]) -> list:
    """截取当前轮次的消息范围。

    目标：避免 done 事件回溯时跨轮次读取到历史结构化数据（如上一轮 todo_list）。

    规则：
    1. 若无 human_message_id，返回原消息（兼容旧行为）
    2. 从后向前找到当前 human 消息 ID，返回其后的全部消息（含该 human）
    3. 若找不到，返回原消息（降级兜底）
    """
    if not messages:
        return []

    if not human_message_id:
        return messages

    for i in range(len(messages) - 1, -1, -1):
        msg_i = messages[i]
        if isinstance(msg_i, HumanMessage) and getattr(msg_i, "id", None) == human_message_id:
            return messages[i:]

    return messages


def _normalize_message_content(content: object) -> str:
    """将消息内容统一归一化为字符串。"""
    return normalize_message_content(content)


def _infer_result_type(event_data: dict[str, Any]) -> str:
    """推断 result 事件类型。"""
    raw_type = event_data.get("type")
    if isinstance(raw_type, str) and raw_type.strip():
        return raw_type.strip()

    data_type = event_data.get("data_type")
    if isinstance(data_type, str) and data_type.strip():
        return data_type.strip()

    if "chart" in event_data:
        return "chart"
    if "table" in event_data:
        return "table"
    return "result"


def _infer_result_content(event_data: dict[str, Any]) -> Any:
    """推断 result 事件内容。"""
    if "content" in event_data and event_data.get("content") is not None:
        return event_data.get("content")

    message = event_data.get("message")
    if isinstance(message, str) and message:
        return message

    if "data" in event_data:
        return event_data.get("data")

    return ""


def _normalize_result_event_payload(event_data: dict[str, Any], *, node: str = "") -> dict[str, Any]:
    """标准化 result 事件，补齐冻结契约必填字段。"""
    payload = dict(event_data or {})

    if not isinstance(payload.get("type"), str) or not str(payload.get("type")).strip():
        payload["type"] = _infer_result_type(payload)

    if "content" not in payload or payload.get("content") is None:
        payload["content"] = _infer_result_content(payload)

    if "meta" not in payload:
        meta: dict[str, Any] = {}
        if node:
            meta["node"] = node

        data_type = payload.get("data_type")
        if isinstance(data_type, str) and data_type.strip() and data_type != payload.get("type"):
            meta["data_type"] = data_type

        if meta:
            payload["meta"] = meta

    return payload


def _is_sse_intent_goal_status_v2_enabled() -> bool:
    """SSE 目标口径双字段开关（默认开启）。"""
    return _is_feature_enabled("ENABLE_SSE_INTENT_GOAL_STATUS_V2", True)


def _is_plan_ready_compat_enabled() -> bool:
    """plan_ready 兼容期开关（默认开启）。"""
    return _is_feature_enabled("ENABLE_PLAN_READY_COMPAT", True)


def _parse_non_negative_int(value: Any, default: int = 0) -> int:
    """解析非负整数。"""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _normalize_plan_ready_event_payload(
    event_data: dict[str, Any],
    *,
    node: str = "",
) -> Optional[dict[str, Any]]:
    """标准化 plan_ready 事件，补齐初判目标计数字段。"""
    if not _is_plan_ready_compat_enabled():
        return None

    payload = dict(event_data or {})
    if not _is_sse_intent_goal_status_v2_enabled():
        return payload

    plan = payload.get("plan")
    if not isinstance(plan, dict):
        plan = {}
        payload["plan"] = plan

    goals = list(plan.get("goals") or [])
    meta = payload.get("meta")
    normalized_meta = dict(meta) if isinstance(meta, dict) else {}
    goal_count_initial = _parse_non_negative_int(
        normalized_meta.get("goal_count_initial"),
        default=len(goals),
    )

    normalized_meta["goal_count_initial"] = goal_count_initial
    if node and "node" not in normalized_meta:
        normalized_meta["node"] = node

    payload["meta"] = normalized_meta
    payload["goal_count_initial"] = goal_count_initial
    return payload


def _normalize_coverage_check_event_payload(event_data: dict[str, Any], *, node: str = "") -> dict[str, Any]:
    """标准化 coverage_check 事件，补齐确认目标计数字段。"""
    payload = dict(event_data or {})
    if not _is_sse_intent_goal_status_v2_enabled():
        return payload

    report = payload.get("report")
    if not isinstance(report, dict):
        report = {}
        payload["report"] = report

    missing_goals = list(report.get("missing_goals") or [])
    meta = payload.get("meta")
    normalized_meta = dict(meta) if isinstance(meta, dict) else {}

    goal_count_initial = _parse_non_negative_int(
        normalized_meta.get("goal_count_initial"),
        default=_parse_non_negative_int(report.get("total_goals"), default=0),
    )
    goal_count_confirmed = _parse_non_negative_int(
        normalized_meta.get("goal_count_confirmed"),
        default=_parse_non_negative_int(report.get("answered_goals"), default=0),
    )
    missing_goal_count = _parse_non_negative_int(
        normalized_meta.get("missing_goal_count"),
        default=len(missing_goals),
    )

    normalized_meta["goal_count_initial"] = goal_count_initial
    normalized_meta["goal_count_confirmed"] = goal_count_confirmed
    normalized_meta["missing_goal_count"] = missing_goal_count
    if node and "node" not in normalized_meta:
        normalized_meta["node"] = node

    payload["meta"] = normalized_meta
    payload["goal_count_initial"] = goal_count_initial
    payload["goal_count_confirmed"] = goal_count_confirmed
    payload["missing_goal_count"] = missing_goal_count
    return payload


def _normalize_final_answer_meta(meta: Any) -> dict[str, Any]:
    """标准化 final_answer 元信息，补齐目标计数字段。"""
    normalized_meta = dict(meta) if isinstance(meta, dict) else {}
    if not _is_sse_intent_goal_status_v2_enabled():
        return normalized_meta

    missing_goal_count = _parse_non_negative_int(
        normalized_meta.get("missing_goal_count"),
        default=_parse_non_negative_int(normalized_meta.get("missing_goals"), default=0),
    )
    goal_count_initial = _parse_non_negative_int(
        normalized_meta.get("goal_count_initial"),
        default=_parse_non_negative_int(normalized_meta.get("goal_count"), default=0),
    )
    goal_count_confirmed = _parse_non_negative_int(
        normalized_meta.get("goal_count_confirmed"),
        default=max(goal_count_initial - missing_goal_count, 0),
    )

    normalized_meta["missing_goal_count"] = missing_goal_count
    if goal_count_initial > 0:
        normalized_meta["goal_count_initial"] = goal_count_initial
    if goal_count_confirmed > 0 or goal_count_initial > 0:
        normalized_meta["goal_count_confirmed"] = goal_count_confirmed
    return normalized_meta


def _normalize_interrupt_event_payload(
    interrupt_value: Any,
    *,
    thread_id: str,
    interrupt_id: str,
) -> dict[str, Any]:
    """标准化 interrupt 事件，补齐冻结契约并保留兼容字段。"""
    value = interrupt_value if isinstance(interrupt_value, dict) else {"message": str(interrupt_value)}

    reason = value.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = value.get("type")

    if (not isinstance(reason, str) or not reason.strip()) and isinstance(value.get("action_requests"), list):
        action_requests = value.get("action_requests") or []
        if action_requests and isinstance(action_requests[0], dict):
            action_name = action_requests[0].get("name")
            if isinstance(action_name, str) and action_name.strip():
                reason = action_name

    if not isinstance(reason, str) or not reason.strip():
        reason = "action_required"

    message = value.get("message")
    if not isinstance(message, str) or not message.strip():
        message = None
        action_requests = value.get("action_requests")
        if isinstance(action_requests, list) and action_requests and isinstance(action_requests[0], dict):
            first_action = action_requests[0]
            args = first_action.get("args")
            if isinstance(args, dict):
                display_message = args.get("_display_message")
                if isinstance(display_message, str) and display_message.strip():
                    message = display_message.strip()

            if message is None:
                description = first_action.get("description")
                if isinstance(description, str) and description.strip():
                    message = description.strip()

        if message is None:
            message = "需要用户确认后继续执行"

    payload: dict[str, Any] = {
        "reason": reason,
        "message": message,
        "thread_id": thread_id,
        "interrupt_id": interrupt_id,
        "value": value,
    }

    recoverable = value.get("recoverable")
    payload["recoverable"] = recoverable if isinstance(recoverable, bool) else True

    suggested_action = value.get("suggested_action")
    if isinstance(suggested_action, str) and suggested_action.strip():
        payload["suggested_action"] = suggested_action.strip()
    elif reason == "action_required":
        payload["suggested_action"] = "请确认后继续"

    return payload


def _build_done_payload(
    *,
    thread_id: str,
    run_id: Optional[str],
    message_id: Optional[int],
    final_content: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """构造 done 事件载荷。"""
    payload: dict[str, Any] = {
        "thread_id": thread_id,
        "run_id": run_id,
        "message_id": message_id,
    }

    if final_content is not None:
        payload["final_content"] = final_content

    if meta:
        payload["meta"] = meta

    return payload


def _build_control_flags(
    *,
    run_control_enabled: bool,
    attachments: Optional[list],
    current_todo_id: Optional[int],
) -> dict[str, Any]:
    """构建控制面标记，供下游节点识别控制上下文。"""
    return {
        "run_control_enabled": bool(run_control_enabled),
        "has_attachments": bool(attachments),
        "has_current_todo_anchor": current_todo_id is not None,
    }


def _build_semantic_payload(
    *,
    user_query: str,
    composed_query: str,
    human_message_id: Optional[str],
) -> dict[str, Any]:
    """构建语义面载荷，避免控制层直接改写语义目标。"""
    return {
        "user_query": str(user_query or "").strip(),
        "composed_query": str(composed_query or "").strip(),
        "human_message_id": human_message_id,
    }


def _build_stopped_payload(*, thread_id: str, run_id: str, reason: str) -> dict[str, Any]:
    """构造 stopped 事件载荷。"""

    return stopped_event(thread_id=thread_id, run_id=run_id, reason=reason)



class ChatService:
    """Chat 服务类，封装与 LangGraph 的交互。"""
    
    def __init__(self, default_delay_ms: int = 0):
        self.default_delay_ms = default_delay_ms
    
    async def get_graph(self, enable_thinking: bool = False, model_id: str = None):
        """异步获取 Graph 实例（多智能体模式）。
        
        Args:
            enable_thinking: 是否启用深度思考模式
            model_id: 指定模型 ID
        """
        return await get_multi_agent_graph(enable_thinking=enable_thinking, model_id=model_id)

    async def stream(
        self,
        prompt: str,
        thread_id: Optional[str] = None,
        user_id: Optional[int] = None,
        delay_ms: Optional[int] = None,
        enable_thinking: bool = False,
        model_id: Optional[str] = None,
        attachments: Optional[list] = None,  # List[Attachment] objects
        current_todo_id: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """流式处理用户输入，返回 SSE 格式的事件流。
        
        事件类型：
        - token: AI 文字输出
        - thinking: Qwen Think 模式的思考过程
        - tool_start: 开始调用工具
        - tool_end: 工具调用结束
        - interrupt: 需要人工审核（新增）
        - done: 流结束
        - error: 错误信息
        
        Args:
            prompt: 用户输入
            thread_id: 对话 ID，用于多轮对话
            user_id: 用户 ID
            delay_ms: Token 输出延迟（毫秒）
            attachments: 附件列表
            run_id: 运行ID（可选，默认自动生成）
            
        Yields:
            SSE 格式的事件数据
        """
        d = self.default_delay_ms if delay_ms is None else delay_ms
        thread_id = thread_id or str(uuid4())

        run_control_enabled = run_control_service.is_enabled()
        resolved_run_id = run_id
        if run_control_enabled:
            with get_db_context() as db:
                run_snapshot = run_control_service.create_run(
                    thread_id=thread_id,
                    user_id=user_id,
                    run_id=resolved_run_id,
                    db=db,
                )
            resolved_run_id = run_snapshot.run_id
        else:
            resolved_run_id = resolved_run_id or f"run_{uuid4().hex}"

        # 构建输入
        # 如果有附件，将信息追加到 prompt 中，供 Agent 通过工具调用
        final_prompt = prompt
        if attachments:
            # 辅助函数：安全提取附件信息
            def _parse_attachment(att):
                if isinstance(att, dict):
                    return (
                        str(att.get("mime_type") or "unknown"),
                        str(att.get("name") or "unknown"),
                        str(att.get("url") or "")
                    )
                return (
                    str(getattr(att, "mime_type", None) or "unknown"),
                    str(getattr(att, "name", None) or "unknown"),
                    str(getattr(att, "url", None) or "")
                )

            # 分离图片和其他文件
            image_attachments = []
            other_attachments = []
            for att in attachments:
                mime, _, _ = _parse_attachment(att)
                if "image" in mime:
                    image_attachments.append(att)
                else:
                    other_attachments.append(att)
            
            # 图片使用 Markdown 格式
            if image_attachments:
                final_prompt += "\n\n"
                for att in image_attachments:
                    _, name, url = _parse_attachment(att)
                    if url:
                        final_prompt += f"![{name}]({url})\n"
                        final_prompt += f"(请使用 analyze_image 工具分析此图片: {url})\n\n"
            
            # 非图片文件使用原有格式
            if other_attachments:
                final_prompt += "\n\nUser uploaded files:"
                for att in other_attachments:
                    mime, name, url = _parse_attachment(att)
                    
                    final_prompt += f"\n- [{mime}] {name} (URL: {url})"
                    
                    if url and any(t in mime for t in ["csv", "spreadsheet", "excel"]):
                        final_prompt += "\n  (Hint: Use the read_uploaded_file tool to read this file)"
            
            logger.info("已将附件信息追加到 Prompt: %d 个附件 (%d 图片, %d 其他)", 
                       len(attachments), len(image_attachments), len(other_attachments))

        document_memory_enabled = _is_document_memory_enabled(ENABLE_DOCUMENT_MEMORY)
        document_memory_recall_enabled = (
            document_memory_enabled
            and _is_document_memory_recall_enabled(ENABLE_DOCUMENT_MEMORY)
        )
        document_memory_flush_enabled = (
            document_memory_enabled
            and _is_document_memory_flush_enabled(ENABLE_DOCUMENT_MEMORY)
        )
        memory_intent_async_enabled = _is_memory_intent_async_enabled(
            MEMORY_INTENT_ASYNC_ENABLED,
        )
        document_memory_hybrid_enabled = (
            document_memory_recall_enabled
            and _is_document_memory_hybrid_enabled(ENABLE_DOCUMENT_MEMORY)
        )
        document_memory_max_results = _get_document_memory_max_results(
            DOCUMENT_MEMORY_MAX_RESULTS,
        )
        document_memory_max_injected_chars = _get_document_memory_max_injected_chars(
            DOCUMENT_MEMORY_MAX_INJECTED_CHARS,
        )
        document_vector_weight, document_text_weight = _get_document_memory_weights(
            DOCUMENT_MEMORY_VECTOR_WEIGHT,
            DOCUMENT_MEMORY_TEXT_WEIGHT,
        )
        document_hybrid_min_score = _get_document_memory_hybrid_min_score(
            DOCUMENT_MEMORY_HYBRID_MIN_SCORE,
        )
        if not document_memory_hybrid_enabled:
            document_vector_weight = 0.0
            document_text_weight = 1.0

        document_memory_context = ""
        if document_memory_recall_enabled and user_id:
            try:
                with get_db_context() as db:
                    document_memory_context = recall_document_memory(
                        db,
                        user_id=user_id,
                        query_text=prompt,
                        max_results=document_memory_max_results,
                        max_injected_chars=document_memory_max_injected_chars,
                        min_score=document_hybrid_min_score,
                        vector_weight=document_vector_weight,
                        text_weight=document_text_weight,
                    )
            except Exception as memory_error:
                logger.warning("读取文档化记忆失败，已降级: user_id=%s, error=%s", user_id, memory_error)
        memory_context = document_memory_context
            
        input_messages = []
        if memory_context:
            input_messages.append(SystemMessage(content=memory_context))

        human_message = create_human_message(final_prompt)
        input_messages.append(human_message)
        current_human_message_id = getattr(human_message, "id", None)
        control_flags = _build_control_flags(
            run_control_enabled=run_control_enabled,
            attachments=attachments,
            current_todo_id=current_todo_id,
        )
        semantic_payload = _build_semantic_payload(
            user_query=prompt,
            composed_query=final_prompt,
            human_message_id=current_human_message_id,
        )

        if memory_context:
            logger.info(
                "已注入记忆上下文: user_id=%s, has_document=%s, has_preference=%s, document_hybrid=%s",
                user_id,
                bool(document_memory_context),
                False,
                document_memory_hybrid_enabled,
            )

        config = {"configurable": {"thread_id": thread_id, "user_id": user_id, "current_todo_id": current_todo_id, "run_id": resolved_run_id}}
        
        # 构建输入 state（包含 user_id、thread_id、enable_thinking、model_id、current_todo_id）
        input_state = {
            "messages": input_messages,
            "user_id": user_id,
            "thread_id": thread_id,
            "enable_thinking": enable_thinking,
            "model_id": model_id,
            "current_todo_id": current_todo_id,
            "run_id": resolved_run_id,
            "control_flags": control_flags,
            "semantic_payload": semantic_payload,
        }
        
        # 用于收集完整回复
        full_answer = []
        tool_data = []
        thinking_content = None
        final_answer_content: Optional[str] = None
        keyword_logged = False
        cancelled_stream = False
        cancel_reason = "user_cancelled"
        cancel_after_token_count = 0
        client_disconnected = False

        def _clear_cancelled_task_state() -> None:
            task = asyncio.current_task()
            if task is None:
                return
            try:
                while task.cancelling():
                    task.uncancel()
            except Exception:
                return

        def _mark_client_disconnected(stage: str) -> None:
            nonlocal client_disconnected
            if client_disconnected:
                return
            client_disconnected = True
            _clear_cancelled_task_state()
            logger.info(
                "检测到 SSE 客户端断开，转为后台续跑: thread_id=%s, run_id=%s, stage=%s",
                thread_id,
                resolved_run_id,
                stage,
            )
        
        logger.info("开始流式处理: thread_id=%s, run_id=%s, prompt_len=%d, thinking=%s, model=%s", 
                    thread_id, resolved_run_id, len(prompt), enable_thinking, model_id or "默认")
        
        # 在流开始时保存 human 消息（单一入口，确保顺序正确）
        # AI 消息由 interrupt 或 postprocess 保存
        with get_db_context() as db:
            title = prompt[:50] if len(prompt) > 50 else prompt
            saved_human = chat_repo.save_message(
                db,
                user_id=user_id,
                thread_id=thread_id,
                role="human",
                content_type="text",
                content=prompt,
                title=title,
            )

            document_memory_context = _persist_document_memory_context(
                db,
                user_id=user_id,
                prompt=prompt,
                thread_id=thread_id,
                source_message_id=getattr(saved_human, "id", None),
                document_memory_context=document_memory_context,
                document_memory_flush_enabled=document_memory_flush_enabled,
                document_memory_recall_enabled=document_memory_recall_enabled,
                memory_intent_async_enabled=memory_intent_async_enabled,
                document_memory_max_results=document_memory_max_results,
                document_memory_max_injected_chars=document_memory_max_injected_chars,
                document_hybrid_min_score=document_hybrid_min_score,
                document_vector_weight=document_vector_weight,
                document_text_weight=document_text_weight,
            )

            if document_memory_context:
                memory_context = document_memory_context
                input_messages = [SystemMessage(content=document_memory_context), human_message]
                input_state["messages"] = input_messages
                logger.info(
                    "本轮写入后即时注入记忆上下文: user_id=%s, has_document=%s, has_preference=%s, document_hybrid=%s",
                    user_id,
                    bool(document_memory_context),
                    False,
                    document_memory_hybrid_enabled,
                )
        
        # 发送初始化事件
        if not client_disconnected:
            try:
                yield self._format_sse("init", {"thread_id": thread_id, "run_id": resolved_run_id})
            except asyncio.CancelledError:
                _mark_client_disconnected("init")
        
        try:
            graph = await self.get_graph(enable_thinking=enable_thinking, model_id=model_id)
            try:
                # 统一架构：只使用 stream_mode="custom"
                # 所有用户可见的输出都通过 emit_token/emit_result 等发送
                # 优点：发送给前端的内容和数据库保存的内容用同一套代码处理
                async for chunk in graph.astream(
                    input_state,
                    config=config,
                    stream_mode="custom",
                ):
                    # chunk 格式: {"type": "token|result|status|...", "data": {...}, "node": "..."}
                    event_type = chunk.get("type", "custom")
                    event_data = chunk.get("data", {})

                    if run_control_enabled and run_control_service.is_cancelled(resolved_run_id):
                        if not cancelled_stream:
                            cancelled_stream = True
                            cancel_reason = run_control_service.get_cancel_reason(resolved_run_id)
                            with get_db_context() as db:
                                run_control_service.mark_stopped(
                                    run_id=resolved_run_id,
                                    reason=cancel_reason,
                                    db=db,
                                )
                            logger.info(
                                "检测到取消信号，进入 drain 模式: thread_id=%s, run_id=%s, reason=%s",
                                thread_id,
                                resolved_run_id,
                                cancel_reason,
                            )
                            if run_control_service.is_stopped_event_enabled() and not run_control_service.has_stopped_event_emitted(resolved_run_id):
                                stopped_payload = _build_stopped_payload(
                                    thread_id=thread_id,
                                    run_id=resolved_run_id,
                                    reason=cancel_reason,
                                )
                                if not client_disconnected:
                                    try:
                                        yield self._format_sse("stopped", stopped_payload)
                                    except asyncio.CancelledError:
                                        _mark_client_disconnected("stopped")
                                run_control_service.mark_stopped_event_emitted(resolved_run_id)

                        continue

                    # 收集用于保存的内容
                    if event_type == "token":
                        content = event_data.get("content", "")
                        if content:
                            full_answer.append(content)
                            if not client_disconnected:
                                try:
                                    yield self._format_sse("token", {"content": content, "node": chunk.get("node", "")})
                                except asyncio.CancelledError:
                                    _mark_client_disconnected("token")

                    elif event_type == "thinking":
                        thinking_text = event_data.get("content", "")
                        if thinking_content is None:
                            thinking_content = thinking_text
                        else:
                            thinking_content += thinking_text
                        if not client_disconnected:
                            try:
                                yield self._format_sse("thinking", {"content": thinking_text, "node": chunk.get("node", "")})
                            except asyncio.CancelledError:
                                _mark_client_disconnected("thinking")

                    elif event_type == "final_answer":
                        content = _normalize_message_content(event_data.get("content", ""))
                        if content:
                            final_answer_content = content
                            full_answer.clear()
                            full_answer.append(content)
                        final_meta = _normalize_final_answer_meta(event_data.get("meta", {}))
                        if not client_disconnected:
                            try:
                                yield self._format_sse(
                                    "final_answer",
                                    {
                                        "content": content,
                                        "meta": final_meta,
                                        "node": chunk.get("node", ""),
                                    },
                                )
                            except asyncio.CancelledError:
                                _mark_client_disconnected("final_answer")

                    elif event_type == "result":
                        # 结构化结果事件（待办列表、图片等）
                        # 如果有 message 字段，也收集到 full_answer
                        if event_data.get("message"):
                            full_answer.append(event_data["message"])
                        result_payload = _normalize_result_event_payload(
                            event_data,
                            node=chunk.get("node", ""),
                        )
                        if not client_disconnected:
                            try:
                                yield self._format_sse("result", result_payload)
                            except asyncio.CancelledError:
                                _mark_client_disconnected("result")

                    elif event_type == "plan_ready":
                        plan_payload = _normalize_plan_ready_event_payload(
                            event_data,
                            node=chunk.get("node", ""),
                        )
                        if plan_payload is None:
                            continue

                        if not client_disconnected:
                            try:
                                yield self._format_sse("plan_ready", plan_payload)
                            except asyncio.CancelledError:
                                _mark_client_disconnected("plan_ready")

                    elif event_type == "coverage_check":
                        coverage_payload = _normalize_coverage_check_event_payload(
                            event_data,
                            node=chunk.get("node", ""),
                        )
                        if not client_disconnected:
                            try:
                                yield self._format_sse("coverage_check", coverage_payload)
                            except asyncio.CancelledError:
                                _mark_client_disconnected("coverage_check")

                    elif event_type in ("status", "clarification", "confirmation", "tool_start", "tool_end", "handoff"):
                        if not client_disconnected:
                            try:
                                yield self._format_sse(event_type, event_data)
                            except asyncio.CancelledError:
                                _mark_client_disconnected(event_type)

                    else:
                        # 其他自定义事件直接转发
                        if not client_disconnected:
                            try:
                                yield self._format_sse(event_type, event_data)
                            except asyncio.CancelledError:
                                _mark_client_disconnected(f"custom:{event_type}")
            except asyncio.CancelledError:
                _mark_client_disconnected("astream")
            except Exception as e:
                # 捕获 LangGraph 中断信号。GraphInterrupt 可能被抛出导致流中断，
                # 但我们需要继续执行后面的 snapshot 检查逻辑来提取 interrupt 信息并返回给前端。
                if type(e).__name__ == "GraphInterrupt":
                    logger.info("检测到 GraphInterrupt，停止流式输出并检查状态")
                else:
                    raise e

            
            # 流结束后检查是否有 interrupt
            snapshot = None
            if client_disconnected:
                logger.info(
                    "SSE 已断开，跳过状态回读: thread_id=%s, run_id=%s",
                    thread_id,
                    resolved_run_id,
                )
            elif cancelled_stream:
                logger.info(
                    "run 已取消，跳过状态回读: thread_id=%s, run_id=%s",
                    thread_id,
                    resolved_run_id,
                )
            else:
                try:
                    snapshot = await graph.aget_state(config)
                except Exception as snapshot_error:
                    if is_checkpointer_busy_error(snapshot_error):
                        logger.warning(
                            "状态回读命中 checkpointer busy，降级跳过: thread_id=%s, run_id=%s, error=%s",
                            thread_id,
                            resolved_run_id,
                            snapshot_error,
                        )
                        snapshot = None
                    else:
                        raise

            if (not cancelled_stream) and snapshot and snapshot.tasks:
                for task in snapshot.tasks:
                    if task.interrupts:
                        # 在 interrupt 时只保存 AI 消息
                        # human 消息已在 stream 开始时保存，无需重复
                        ai_content = "".join(full_answer)
                        if ai_content:
                            self._save_conversation_fallback(
                                thread_id=thread_id,
                                user_id=user_id,
                                prompt=None,  # human 已保存，不重复
                                ai_content=ai_content,
                                is_intermediate=True,  # 标记为中间消息，避免与 postprocess 重复
                                scenario="Interrupt",
                            )
                        
                        for interrupt in task.interrupts:
                            logger.info("检测到 interrupt: %s", interrupt.value)
                            interrupt_payload = _normalize_interrupt_event_payload(
                                interrupt.value,
                                thread_id=thread_id,
                                interrupt_id=str(id(interrupt)),
                            )
                            if not client_disconnected:
                                try:
                                    yield self._format_sse("interrupt", interrupt_payload)
                                except asyncio.CancelledError:
                                    _mark_client_disconnected("interrupt")
                        # 有 interrupt 时不发送 done，等待 resume
                        return

            if cancelled_stream:
                logger.info(
                    "run 已取消并完成 drain: thread_id=%s, run_id=%s, cancel_after_token_count=%d",
                    thread_id,
                    resolved_run_id,
                    cancel_after_token_count,
                )
                if run_control_enabled:
                    with get_db_context() as db:
                        run_control_service.mark_stopped(
                            run_id=resolved_run_id,
                            reason=cancel_reason,
                            db=db,
                        )

                done_payload = _build_done_payload(
                    thread_id=thread_id,
                    run_id=resolved_run_id,
                    message_id=self._get_latest_ai_message_id(thread_id),
                    meta={
                        "status": "stopped",
                        "reason": cancel_reason,
                        "cancel_after_token_count": cancel_after_token_count,
                    },
                )
                if not client_disconnected:
                    try:
                        yield self._format_sse("done", done_payload)
                    except asyncio.CancelledError:
                        _mark_client_disconnected("done_stopped")
                return

            # 4. 如果没有中断，检查是否需要补充发送最后一条消息（针对非流式 Agent 响应）
            # 例如: TodoAgent 的 query/execute 操作直接返回 AIMessage，没有触发 on_chat_model_stream
            done_payload = _build_done_payload(thread_id=thread_id, run_id=resolved_run_id, message_id=None)
            
            if snapshot and "messages" in snapshot.values:
                messages = snapshot.values["messages"]
                if messages:
                    turn_messages = _slice_current_turn_messages(messages, current_human_message_id)

                    last_msg = turn_messages[-1]

                    # 只有 AI 消息才需要补充发送 content
                    if isinstance(last_msg, AIMessage):
                        # 检查是否有 content 需要补充 (如果 full_answer 为空，说明没有流式输出过)
                        if last_msg.content and not full_answer:
                            # 兼容 OpenAI Responses block 列表内容
                            content = _normalize_message_content(last_msg.content)
                            if content:
                                # 过滤掉看起来像 JSON 的原始分析结果
                                is_raw_json = (
                                    content.strip().startswith("{") and
                                    ("needs_clarification" in content or "intent" in content)
                                )

                                if not is_raw_json:
                                    logger.info("补充发送非流式响应: %s", content[:50])
                                    if not client_disconnected:
                                        try:
                                            yield self._format_sse("token", {"content": content})
                                        except asyncio.CancelledError:
                                            _mark_client_disconnected("token_fallback")
                                    done_payload["final_content"] = content
                                else:
                                    logger.warning("跳过原始JSON输出: %s", content[:100])

            # 流结束（对话由 postprocess 节点保存到数据库）
            streamed_content = "".join(full_answer)
            logger.info(
                "[SYNC-TRACE] 流式输出完成: thread_id=%s, content_len=%d, content_hash=%s, thinking=%s",
                thread_id, len(streamed_content), _content_hash(streamed_content), bool(thinking_content)
            )
            
            # 回传数据库消息 ID，使实时对话中的点赞/点踩立即可用
            message_id = self._get_latest_ai_message_id(thread_id)
            if message_id is not None:
                done_payload["message_id"] = message_id
            if final_answer_content:
                done_payload["final_content"] = final_answer_content

            if run_control_enabled:
                with get_db_context() as db:
                    run_control_service.complete_run(resolved_run_id, db=db)

            if not client_disconnected:
                try:
                    yield self._format_sse("done", done_payload)
                except asyncio.CancelledError:
                    _mark_client_disconnected("done")
            
        except Exception as e:
            raw_error_msg = str(e)
            display_error_msg = raw_error_msg
            busy_error = is_checkpointer_busy_error(e)
            if busy_error:
                display_error_msg = "会话状态正在收口，请稍后重试。"
                logger.warning(
                    "流式处理命中 checkpointer busy: thread_id=%s, run_id=%s, error=%s",
                    thread_id,
                    resolved_run_id,
                    raw_error_msg,
                )

            plugin_degrade_message = degrade_on_plugin_failure(raw_error_msg)
            if plugin_degrade_message:
                logger.warning("检测到插件链路异常，已启用核心能力降级: %s", raw_error_msg)
                ai_content = "".join(full_answer) if full_answer else plugin_degrade_message
                self._save_conversation_fallback(
                    thread_id=thread_id,
                    user_id=user_id,
                    prompt=None,  # human 已在 stream 开始保存，降级场景避免重复写入
                    ai_content=ai_content,
                    scenario="PluginFallback",
                )

                if run_control_enabled:
                    with get_db_context() as db:
                        run_control_service.complete_run(resolved_run_id, db=db)

                done_payload = _build_done_payload(
                    thread_id=thread_id,
                    run_id=resolved_run_id,
                    message_id=self._get_latest_ai_message_id(thread_id),
                    meta={
                        "status": "degraded",
                        "fallback_route": "core_tools_only",
                        "plugin_lifecycle_status": "unhealthy",
                    },
                )

                if not client_disconnected:
                    try:
                        yield self._format_sse(
                            "status",
                            {
                                "message": "插件能力暂不可用，已自动降级到核心能力。",
                                "node": "runtime_recovery",
                            },
                        )
                    except asyncio.CancelledError:
                        _mark_client_disconnected("status_degraded")
                if not full_answer:
                    if not client_disconnected:
                        try:
                            yield self._format_sse("token", {"content": plugin_degrade_message})
                        except asyncio.CancelledError:
                            _mark_client_disconnected("token_degraded")
                    done_payload["final_content"] = plugin_degrade_message
                if not client_disconnected:
                    try:
                        yield self._format_sse("done", done_payload)
                    except asyncio.CancelledError:
                        _mark_client_disconnected("done_degraded")
                return

            if run_control_enabled:
                with get_db_context() as db:
                    if run_control_service.is_cancelled(resolved_run_id, db=db):
                        run_control_service.mark_stopped(
                            run_id=resolved_run_id,
                            reason=run_control_service.get_cancel_reason(resolved_run_id, db=db),
                            db=db,
                        )
                    else:
                        run_control_service.fail_run(resolved_run_id, error_message=raw_error_msg, db=db)

            # 保存错误消息到数据库（确保对话历史不丢失）
            ai_content = "".join(full_answer) if full_answer else f"[System Error: {display_error_msg}]"
            self._save_conversation_fallback(
                thread_id=thread_id,
                user_id=user_id,
                prompt=None,  # human 已在 stream 开始保存，异常时避免重复写入
                ai_content=ai_content,
                scenario="Exception",
            )
            
            # 检查是否为内容审核错误
            if "inappropriate content" in raw_error_msg.lower() or "内容违规" in raw_error_msg:
                logger.warning("内容审核拦截: %s", raw_error_msg)
                # 返回友好提示并正常结束对话
                friendly_msg = "抱歉，您的请求内容或搜索结果触发了内容安全审核，无法继续处理。请尝试换一种方式提问。"
                if not client_disconnected:
                    try:
                        yield self._format_sse("token", {"content": friendly_msg})
                    except asyncio.CancelledError:
                        _mark_client_disconnected("token_moderation")
                if not client_disconnected:
                    try:
                        yield self._format_sse(
                            "done",
                            _build_done_payload(
                                thread_id=thread_id,
                                run_id=resolved_run_id,
                                message_id=self._get_latest_ai_message_id(thread_id),
                            ),
                        )
                    except asyncio.CancelledError:
                        _mark_client_disconnected("done_moderation")
            else:
                if not busy_error:
                    logger.exception("流式处理错误: %s", e)
                if not client_disconnected:
                    try:
                        yield self._format_sse("error", {"message": display_error_msg})
                    except asyncio.CancelledError:
                        _mark_client_disconnected("error")
    
    def _format_sse(self, event_type: str, data: dict) -> bytes:
        """格式化 SSE 事件。"""
        payload = json.dumps(jsonable_encoder(data), ensure_ascii=False)
        return f"event: {event_type}\ndata: {payload}\n\n".encode()

    def _save_conversation_fallback(
        self,
        thread_id: str,
        user_id: Optional[int],
        prompt: Optional[str],
        ai_content: str,
        *,
        is_intermediate: bool = False,
        scenario: str = "fallback",
    ) -> None:
        """统一的备用消息保存方法，用于异常/中断场景。
        
        Args:
            thread_id: 对话线程 ID
            user_id: 用户 ID
            prompt: 用户输入（None 表示不保存 human 消息，如 resume 场景）
            ai_content: AI 回复内容
            is_intermediate: 是否为中间消息（如 interrupt 场景）
            scenario: 场景标识，用于日志
        """
        from app.db.session import get_db_context
        from app.repositories import chat_repo
        
        try:
            with get_db_context() as db:
                # 保存 human 消息（如果提供）
                if prompt is not None:
                    title = prompt[:50] if len(prompt) > 50 else prompt
                    chat_repo.save_message(
                        db,
                        user_id=user_id,
                        thread_id=thread_id,
                        role="human",
                        content_type="text",
                        content=prompt,
                        title=title,
                    )
                
                # 保存 AI 消息
                extra_data = {"is_intermediate": True} if is_intermediate else None
                chat_repo.save_message(
                    db,
                    user_id=user_id,
                    thread_id=thread_id,
                    role="ai",
                    content_type="markdown",
                    content=ai_content,
                    extra_data=extra_data,
                )
            
            logger.info(
                "%s 场景消息已保存: thread_id=%s, human=%s, ai=%d字",
                scenario,
                thread_id,
                f"{len(prompt)}字" if prompt else "无",
                len(ai_content),
            )
        except Exception as save_error:
            logger.error("%s 场景保存消息失败: %s", scenario, save_error, exc_info=True)

    def _get_latest_ai_message_id(self, thread_id: str) -> Optional[int]:
        """获取线程最新 AI 消息 ID。"""
        try:
            from app.db.session import get_db_context
            from app.models.chat_message import ChatMessage

            with get_db_context() as db_session:
                last_saved = db_session.query(ChatMessage).filter(
                    ChatMessage.thread_id == thread_id,
                    ChatMessage.role == "ai",
                ).order_by(ChatMessage.id.desc()).first()
                if last_saved is not None:
                    return int(last_saved.id)
        except Exception as exc:
            logger.debug("获取保存消息ID失败: %s", exc)

        return None


async def sse_stream(
    prompt: str,
    delay_ms: int = 0,
    thread_id: Optional[str] = None,
    user_id: Optional[int] = None,
    enable_thinking: bool = False,
    model_id: Optional[str] = None,
    attachments: Optional[list] = None,
    current_todo_id: Optional[int] = None,
    run_id: Optional[str] = None,
) -> AsyncGenerator[bytes, None]:
    """SSE 流式输出入口函数。
    
    直接转发 ChatService.stream() 的所有事件。
    图片通过 emit_result("image", {url}) 主动推送，无需拦截处理。
    幂等性由系统中间件统一处理（通过 Idempotency-Key 请求头）。
    
    Args:
        prompt: 用户输入
        delay_ms: Token 输出延迟
        thread_id: 对话 ID
        user_id: 用户 ID
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识
        attachments: 附件列表
        current_todo_id: 当前讨论的待办 ID
        run_id: 运行ID（可选）
        
    Yields:
        SSE 格式的事件数据
    """
    svc = ChatService(default_delay_ms=delay_ms)
    
    async for chunk in svc.stream(
        prompt,
        thread_id,
        user_id,
        delay_ms,
        enable_thinking,
        model_id,
        attachments,
        current_todo_id,
        run_id,
    ):
        yield chunk


async def sse_resume_stream(
    thread_id: str,
    decision: dict,
    user_id: Optional[int] = None,
    delay_ms: int = 0,
    run_id: Optional[str] = None,
) -> AsyncGenerator[bytes, None]:
    """恢复被中断的流程，返回 SSE 格式的事件流。
    
    Args:
        thread_id: 对话 ID
        decision: 用户决定，格式：
            - {"type": "accept"}: 批准执行
            - {"type": "reject", "message": "..."}: 拒绝执行
            - {"type": "edit", "args": {...}}: 编辑参数后执行
        user_id: 用户 ID
        delay_ms: Token 输出延迟
        run_id: 运行ID（可选，默认按 thread_id 推断最近 run）
        
    Yields:
        SSE 格式的事件数据
    """
    from langgraph.types import Command
    
    resolved_run_id = run_id
    config = {"configurable": {"thread_id": thread_id}}

    # 用于收集完整回复
    full_answer = []
    final_answer_content: Optional[str] = None
    cancelled_stream = False
    cancel_after_token_count = 0
    cancel_reason = "user_cancelled"

    svc = ChatService()
    format_sse = svc._format_sse

    if run_control_service.is_enabled():
        with get_db_context() as db:
            if not resolved_run_id:
                latest_run = run_control_service.get_latest_run(thread_id=thread_id, user_id=user_id, db=db)
                if latest_run is not None:
                    resolved_run_id = latest_run.run_id

            if resolved_run_id is not None and not run_control_service.can_resume_run(resolved_run_id, db=db):
                cancel_reason = run_control_service.get_cancel_reason(resolved_run_id, db=db)
                run_control_service.mark_stopped(run_id=resolved_run_id, reason=cancel_reason, db=db)
                if run_control_service.is_stopped_event_enabled() and not run_control_service.has_stopped_event_emitted(resolved_run_id):
                    yield format_sse(
                        "stopped",
                        _build_stopped_payload(
                            thread_id=thread_id,
                            run_id=resolved_run_id,
                            reason=cancel_reason,
                        ),
                    )
                    run_control_service.mark_stopped_event_emitted(resolved_run_id)

                yield format_sse(
                    "done",
                    _build_done_payload(
                        thread_id=thread_id,
                        run_id=resolved_run_id,
                        message_id=svc._get_latest_ai_message_id(thread_id),
                        meta={"status": "stopped", "reason": cancel_reason},
                    ),
                )
                return

    if resolved_run_id:
        config["configurable"]["run_id"] = resolved_run_id

    logger.info("恢复流程: thread_id=%s, run_id=%s, decision=%s", thread_id, resolved_run_id, decision)
    
    try:
        # 1. 动态检测 Graph 类型和参数
        cp = await get_checkpointer()
        snapshot = await cp.aget(config)
        
        enable_thinking = False
        model_id = None
        
        if snapshot and "channel_values" in snapshot:
            values = snapshot["channel_values"]
            enable_thinking = values.get("enable_thinking", False)
            model_id = values.get("model_id")
        
        logger.info("Resume 自动检测: thinking=%s, model=%s", enable_thinking, model_id)

        graph = await svc.get_graph(
            enable_thinking=enable_thinking, 
            model_id=model_id
        )
        
        # 使用 Command 恢复执行
        resume_value = decision
        
        try:
            # 统一架构：只使用 stream_mode="custom"
            async for chunk in graph.astream(
                Command(resume=resume_value),
                config=config,
                stream_mode="custom",
            ):
                event_type = chunk.get("type", "custom")
                event_data = chunk.get("data", {})

                if run_control_service.is_enabled() and resolved_run_id and run_control_service.is_cancelled(resolved_run_id):
                    if not cancelled_stream:
                        cancelled_stream = True
                        cancel_reason = run_control_service.get_cancel_reason(resolved_run_id)
                        with get_db_context() as db:
                            run_control_service.mark_stopped(
                                run_id=resolved_run_id,
                                reason=cancel_reason,
                                db=db,
                            )
                        if run_control_service.is_stopped_event_enabled() and not run_control_service.has_stopped_event_emitted(resolved_run_id):
                            yield format_sse(
                                "stopped",
                                _build_stopped_payload(
                                    thread_id=thread_id,
                                    run_id=resolved_run_id,
                                    reason=cancel_reason,
                                ),
                            )
                            run_control_service.mark_stopped_event_emitted(resolved_run_id)

                    continue

                # 收集用于保存的内容
                if event_type == "token":
                    content = event_data.get("content", "")
                    if content:
                        full_answer.append(content)
                        yield format_sse("token", {"content": content, "node": chunk.get("node", "")})

                elif event_type == "thinking":
                    yield format_sse("thinking", {"content": event_data.get("content", ""), "node": chunk.get("node", "")})

                elif event_type == "final_answer":
                    content = _normalize_message_content(event_data.get("content", ""))
                    if content:
                        final_answer_content = content
                        full_answer.clear()
                        full_answer.append(content)
                    final_meta = _normalize_final_answer_meta(event_data.get("meta", {}))
                    yield format_sse(
                        "final_answer",
                        {
                            "content": content,
                            "meta": final_meta,
                            "node": chunk.get("node", ""),
                        },
                    )

                elif event_type == "result":
                    if event_data.get("message"):
                        full_answer.append(event_data["message"])
                    result_payload = _normalize_result_event_payload(
                        event_data,
                        node=chunk.get("node", ""),
                    )
                    yield format_sse("result", result_payload)

                elif event_type == "plan_ready":
                    plan_payload = _normalize_plan_ready_event_payload(
                        event_data,
                        node=chunk.get("node", ""),
                    )
                    if plan_payload is None:
                        continue

                    yield format_sse("plan_ready", plan_payload)

                elif event_type == "coverage_check":
                    coverage_payload = _normalize_coverage_check_event_payload(
                        event_data,
                        node=chunk.get("node", ""),
                    )
                    yield format_sse("coverage_check", coverage_payload)

                elif event_type in ("status", "clarification", "confirmation"):
                    yield format_sse(event_type, event_data)

                else:
                    yield format_sse(event_type, event_data)
        except Exception as e:
            if type(e).__name__ == "GraphInterrupt":
                logger.info("检测到 GraphInterrupt，停止流式输出并检查状态")
            else:
                raise e
        
        # 检查是否还有 interrupt
        snapshot = None
        if cancelled_stream:
            logger.info("resume run 已取消，跳过状态回读: thread_id=%s, run_id=%s", thread_id, resolved_run_id)
        else:
            try:
                snapshot = await graph.aget_state(config)
            except Exception as snapshot_error:
                if is_checkpointer_busy_error(snapshot_error):
                    logger.warning(
                        "resume 状态回读命中 checkpointer busy，降级跳过: thread_id=%s, run_id=%s, error=%s",
                        thread_id,
                        resolved_run_id,
                        snapshot_error,
                    )
                    snapshot = None
                else:
                    raise
        if (not cancelled_stream) and snapshot and snapshot.tasks:
            for task in snapshot.tasks:
                if task.interrupts:
                    # 有新的 interrupt，发送给前端，不保存消息（等流程结束时统一保存）
                    for interrupt in task.interrupts:
                        logger.info("检测到新的 interrupt: %s", interrupt.value)
                        interrupt_payload = _normalize_interrupt_event_payload(
                            interrupt.value,
                            thread_id=thread_id,
                            interrupt_id=str(id(interrupt)),
                        )
                        yield format_sse("interrupt", interrupt_payload)
                    return

        # 流结束
        logger.info("恢复流程完成: thread_id=%s, run_id=%s, answer_len=%d", thread_id, resolved_run_id, len("".join(full_answer)))

        # 注意：AI 消息保存已由 _postprocess 节点统一处理，此处不再重复保存
        # 这避免了 resume 和 postprocess 同时保存导致的重复记录问题

        if cancelled_stream and resolved_run_id:
            done_payload = _build_done_payload(
                thread_id=thread_id,
                run_id=resolved_run_id,
                message_id=svc._get_latest_ai_message_id(thread_id),
                meta={
                    "status": "stopped",
                    "reason": cancel_reason,
                    "cancel_after_token_count": cancel_after_token_count,
                },
            )
            yield format_sse("done", done_payload)
            return

        done_payload = _build_done_payload(thread_id=thread_id, run_id=resolved_run_id, message_id=None)

        # 检查是否需要补充发送最后一条消息（针对非流式 Agent 响应）
        if snapshot and "messages" in snapshot.values:
            messages = snapshot.values["messages"]
            if messages:
                last_msg = messages[-1]
                if last_msg.type == "ai":
                    content = _normalize_message_content(getattr(last_msg, "content", ""))
                    # 避免重复发送：只有当内容不同于已流式输出的内容时才补发
                    streamed_content = "".join(full_answer)
                    if content and content != streamed_content and not full_answer:
                         yield format_sse("token", {"content": content})
                         done_payload["final_content"] = content

        message_id = svc._get_latest_ai_message_id(thread_id)
        if message_id is not None:
            done_payload["message_id"] = message_id
        if final_answer_content:
            done_payload["final_content"] = final_answer_content

        if run_control_service.is_enabled() and resolved_run_id:
            with get_db_context() as db:
                run_control_service.complete_run(resolved_run_id, db=db)

        yield format_sse("done", done_payload)
        
    except Exception as e:
        raw_error_msg = str(e)
        display_error_msg = raw_error_msg
        busy_error = is_checkpointer_busy_error(e)
        if busy_error:
            display_error_msg = "会话状态正在收口，请稍后重试。"
            logger.warning(
                "恢复流程命中 checkpointer busy: thread_id=%s, run_id=%s, error=%s",
                thread_id,
                resolved_run_id,
                raw_error_msg,
            )
        else:
            logger.exception("恢复流程错误: %s", e)

        if run_control_service.is_enabled() and resolved_run_id:
            with get_db_context() as db:
                if run_control_service.is_cancelled(resolved_run_id, db=db):
                    run_control_service.mark_stopped(
                        run_id=resolved_run_id,
                        reason=run_control_service.get_cancel_reason(resolved_run_id, db=db),
                        db=db,
                    )
                else:
                    run_control_service.fail_run(resolved_run_id, error_message=raw_error_msg, db=db)

        # 保存错误消息到数据库（确保对话历史不丢失）
        # 注意：resume 场景不需要保存 human 消息，只保存 AI 错误响应
        ai_content = "".join(full_answer) if full_answer else f"[System Error: {display_error_msg}]"
        svc._save_conversation_fallback(
            thread_id=thread_id,
            user_id=user_id,
            prompt=None,
            ai_content=ai_content,
            scenario="ResumeException",
        )
        
        yield format_sse("error", {"message": display_error_msg})
