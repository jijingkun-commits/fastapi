"""Chat 服务层：封装流式输出与 Agent 调用逻辑（中文注释）。

本模块实现：
- LangGraph 事件流处理（astream_events）
- SSE 协议升级，支持 token/thinking/tool_start/tool_end 事件
- 双写逻辑：LangGraph 自动写 PostgreSQL Checkpoint，业务数据写 PostgreSQL
"""
import json
import logging
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from langchain_core.messages import HumanMessage, AIMessage
from app.ai.utils.message_factory import create_human_message

from app.ai.workflow import get_multi_agent_graph
from app.core.constants import TOOL_OUTPUT_PREVIEW_LEN, TOOL_OUTPUT_STORAGE_LEN
from app.core.utils import content_hash as _content_hash


logger = logging.getLogger(__name__)


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
    """将消息内容统一归一化为字符串。

    兼容场景：
    - str: 直接返回
    - list: 提取 text/content 字段并拼接
    - dict: 优先 text 字段，否则序列化为 JSON
    - 其他类型: 转字符串
    """
    if isinstance(content, str):
        return content
    if content is None:
        return ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue

            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                    continue

                inner = item.get("content")
                if isinstance(inner, str):
                    parts.append(inner)
                    continue

            parts.append(str(item))
        return "".join(parts)

    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
        return json.dumps(content, ensure_ascii=False)

    return str(content)


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
    message_id: Optional[int],
    final_content: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """构造 done 事件载荷。"""
    payload: dict[str, Any] = {
        "thread_id": thread_id,
        "message_id": message_id,
    }

    if final_content is not None:
        payload["final_content"] = final_content

    if meta:
        payload["meta"] = meta

    return payload



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
            
        Yields:
            SSE 格式的事件数据
        """
        d = self.default_delay_ms if delay_ms is None else delay_ms
        thread_id = thread_id or str(uuid4())
        
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
            
        input_messages = [create_human_message(final_prompt)]
        current_human_message_id = getattr(input_messages[0], "id", None)
        config = {"configurable": {"thread_id": thread_id, "user_id": user_id, "current_todo_id": current_todo_id}}
        
        # 构建输入 state（包含 user_id、thread_id、enable_thinking、model_id、current_todo_id）
        input_state = {
            "messages": input_messages,
            "user_id": user_id,
            "thread_id": thread_id,
            "enable_thinking": enable_thinking,
            "model_id": model_id,
            "current_todo_id": current_todo_id,
        }
        
        # 用于收集完整回复
        full_answer = []
        tool_data = []
        thinking_content = None
        keyword_logged = False
        
        logger.info("开始流式处理: thread_id=%s, prompt_len=%d, thinking=%s, model=%s", 
                    thread_id, len(prompt), enable_thinking, model_id or "默认")
        
        # 在流开始时保存 human 消息（单一入口，确保顺序正确）
        # AI 消息由 interrupt 或 postprocess 保存
        from app.db.session import get_db_context
        from app.repositories import chat_repo
        with get_db_context() as db:
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
        
        # 发送初始化事件
        yield self._format_sse("init", {"thread_id": thread_id})
        
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
                    
                    # 收集用于保存的内容
                    if event_type == "token":
                        content = event_data.get("content", "")
                        if content:
                            full_answer.append(content)
                            yield self._format_sse("token", {"content": content, "node": chunk.get("node", "")})
                    
                    elif event_type == "thinking":
                        thinking_text = event_data.get("content", "")
                        if thinking_content is None:
                            thinking_content = thinking_text
                        else:
                            thinking_content += thinking_text
                        yield self._format_sse("thinking", {"content": thinking_text, "node": chunk.get("node", "")})
                    
                    elif event_type == "result":
                        # 结构化结果事件（待办列表、图片等）
                        # 如果有 message 字段，也收集到 full_answer
                        if event_data.get("message"):
                            full_answer.append(event_data["message"])
                        result_payload = _normalize_result_event_payload(
                            event_data,
                            node=chunk.get("node", ""),
                        )
                        yield self._format_sse("result", result_payload)
                    
                    elif event_type in ("status", "clarification", "confirmation", "tool_start", "tool_end", "handoff"):
                        yield self._format_sse(event_type, event_data)
                    
                    else:
                        # 其他自定义事件直接转发
                        yield self._format_sse(event_type, event_data)
            except Exception as e:
                # 捕获 LangGraph 中断信号。GraphInterrupt 可能被抛出导致流中断，
                # 但我们需要继续执行后面的 snapshot 检查逻辑来提取 interrupt 信息并返回给前端。
                if type(e).__name__ == "GraphInterrupt":
                    logger.info("检测到 GraphInterrupt，停止流式输出并检查状态")
                else:
                    raise e

            
            # 流结束后检查是否有 interrupt
            snapshot = await graph.aget_state(config)
            if snapshot and snapshot.tasks:
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
                            yield self._format_sse("interrupt", interrupt_payload)
                        # 有 interrupt 时不发送 done，等待 resume
                        return

            # 4. 如果没有中断，检查是否需要补充发送最后一条消息（针对非流式 Agent 响应）
            # 例如: TodoAgent 的 query/execute 操作直接返回 AIMessage，没有触发 on_chat_model_stream
            # 4. 如果没有中断，检查是否需要补充发送最后一条消息（针对非流式 Agent 响应）
            # 例如: TodoAgent 的 query/execute 操作直接返回 AIMessage，没有触发 on_chat_model_stream
            
            done_payload = _build_done_payload(thread_id=thread_id, message_id=None)
            
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
                                    yield self._format_sse("token", {"content": content})
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
            
            yield self._format_sse("done", done_payload)
            
        except Exception as e:
            error_msg = str(e)
            
            # 保存错误消息到数据库（确保对话历史不丢失）
            ai_content = "".join(full_answer) if full_answer else f"[System Error: {error_msg}]"
            self._save_conversation_fallback(
                thread_id=thread_id,
                user_id=user_id,
                prompt=None,  # human 已在 stream 开始保存，异常时避免重复写入
                ai_content=ai_content,
                scenario="Exception",
            )
            
            # 检查是否为内容审核错误
            if "inappropriate content" in error_msg.lower() or "内容违规" in error_msg:
                logger.warning("内容审核拦截: %s", error_msg)
                # 返回友好提示并正常结束对话
                friendly_msg = "抱歉，您的请求内容或搜索结果触发了内容安全审核，无法继续处理。请尝试换一种方式提问。"
                yield self._format_sse("token", {"content": friendly_msg})
                yield self._format_sse(
                    "done",
                    _build_done_payload(
                        thread_id=thread_id,
                        message_id=self._get_latest_ai_message_id(thread_id),
                    ),
                )
            else:
                logger.exception("流式处理错误: %s", e)
                yield self._format_sse("error", {"message": error_msg})
    
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
        
    Yields:
        SSE 格式的事件数据
    """
    svc = ChatService(default_delay_ms=delay_ms)
    
    async for chunk in svc.stream(
        prompt, thread_id, user_id, delay_ms, 
        enable_thinking, model_id, attachments, current_todo_id
    ):
        yield chunk


async def sse_resume_stream(
    thread_id: str,
    decision: dict,
    user_id: Optional[int] = None,
    delay_ms: int = 0,
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
        
    Yields:
        SSE 格式的事件数据
    """
    from langgraph.types import Command
    
    d = delay_ms
    config = {"configurable": {"thread_id": thread_id}}
    
    # 用于收集完整回复
    full_answer = []
    
    svc = ChatService()
    format_sse = svc._format_sse
    
    logger.info("恢复流程: thread_id=%s, decision=%s", thread_id, decision)
    
    try:
        # 1. 动态检测 Graph 类型和参数
        from app.db.postgres_checkpoint import get_checkpointer
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
                
                # 收集用于保存的内容
                if event_type == "token":
                    content = event_data.get("content", "")
                    if content:
                        full_answer.append(content)
                        yield format_sse("token", {"content": content, "node": chunk.get("node", "")})
                
                elif event_type == "thinking":
                    yield format_sse("thinking", {"content": event_data.get("content", ""), "node": chunk.get("node", "")})
                
                elif event_type == "result":
                    if event_data.get("message"):
                        full_answer.append(event_data["message"])
                    result_payload = _normalize_result_event_payload(
                        event_data,
                        node=chunk.get("node", ""),
                    )
                    yield format_sse("result", result_payload)
                
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
        snapshot = await graph.aget_state(config)
        if snapshot and snapshot.tasks:
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
        logger.info("恢复流程完成: thread_id=%s, answer_len=%d", thread_id, len("".join(full_answer)))
        
        # 注意：AI 消息保存已由 _postprocess 节点统一处理，此处不再重复保存
        # 这避免了 resume 和 postprocess 同时保存导致的重复记录问题
        
        done_payload = _build_done_payload(thread_id=thread_id, message_id=None)
        
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

        yield format_sse("done", done_payload)
        
    except Exception as e:
        error_msg = str(e)
        logger.exception("恢复流程错误: %s", e)
        
        # 保存错误消息到数据库（确保对话历史不丢失）
        # 注意：resume 场景不需要保存 human 消息，只保存 AI 错误响应
        ai_content = "".join(full_answer) if full_answer else f"[System Error: {error_msg}]"
        svc._save_conversation_fallback(
            thread_id=thread_id,
            user_id=user_id,
            prompt=None,
            ai_content=ai_content,
            scenario="ResumeException",
        )
        
        yield format_sse("error", {"message": error_msg})
