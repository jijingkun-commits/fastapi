"""Chat 服务层：封装流式输出与 Agent 调用逻辑（中文注释）。

本模块实现：
- LangGraph 事件流处理（astream_events）
- SSE 协议升级，支持 token/thinking/tool_start/tool_end 事件
- 双写逻辑：LangGraph 自动写 SQLite Checkpoint，业务数据写 MySQL
"""
import json
import logging
from typing import AsyncGenerator, Optional
from uuid import uuid4

from langchain_core.messages import HumanMessage, AIMessage

from app.ai.workflow import get_multi_agent_graph
from app.core.constants import TOOL_OUTPUT_PREVIEW_LEN, TOOL_OUTPUT_STORAGE_LEN
from app.core.utils import content_hash as _content_hash


logger = logging.getLogger(__name__)


# 注意：对话保存逻辑已移至 multi_agent_graph.py 的 postprocess 节点
# 不再需要在 service 层手动保存
# 单智能体模式已废弃（2026-01-31），系统默认使用多智能体模式



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
            
        input_messages = [HumanMessage(content=final_prompt)]
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
        # 用于收集流式过程中的结构化数据（result 事件）
        collected_additional_kwargs = {}
        keyword_logged = False
        
        logger.info("开始流式处理: thread_id=%s, prompt_len=%d, thinking=%s, model=%s", 
                    thread_id, len(prompt), enable_thinking, model_id or "默认")
        
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
                        # 收集结构化数据用于 done 事件的 additional_kwargs
                        if event_data.get("data_type"):
                            collected_additional_kwargs["data_type"] = event_data["data_type"]
                            collected_additional_kwargs["data"] = event_data.get("data")
                            logger.debug("收集结构化数据: data_type=%s", event_data["data_type"])
                        yield self._format_sse("result", event_data)
                    
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
                        # 在 interrupt 时保存已生成的消息
                        # 注意：snapshot.values.messages 不包含 Supervisor 的流式回复
                        # 因此我们直接使用 full_answer（流式收集的内容）和原始 prompt
                        ai_content = "".join(full_answer)
                        if ai_content:
                            self._save_conversation_fallback(
                                thread_id=thread_id,
                                user_id=user_id,
                                prompt=prompt,
                                ai_content=ai_content,
                                is_intermediate=True,
                                scenario="Interrupt",
                            )
                        
                        for interrupt in task.interrupts:
                            logger.info("检测到 interrupt: %s", interrupt.value)
                            yield self._format_sse("interrupt", {
                                "thread_id": thread_id,
                                "interrupt_id": str(id(interrupt)),
                                "value": interrupt.value if isinstance(interrupt.value, dict) else {"message": str(interrupt.value)},
                            })
                        # 有 interrupt 时不发送 done，等待 resume
                        return

            # 4. 如果没有中断，检查是否需要补充发送最后一条消息（针对非流式 Agent 响应）
            # 例如: TodoAgent 的 query/execute 操作直接返回 AIMessage，没有触发 on_chat_model_stream
            # 4. 如果没有中断，检查是否需要补充发送最后一条消息（针对非流式 Agent 响应）
            # 例如: TodoAgent 的 query/execute 操作直接返回 AIMessage，没有触发 on_chat_model_stream
            
            done_payload = {"thread_id": thread_id}
            
            # 1. 优先使用流式过程中收集的结构化数据（最可靠）
            if collected_additional_kwargs:
                done_payload["additional_kwargs"] = collected_additional_kwargs
                logger.debug("使用流式收集的 additional_kwargs: %s", list(collected_additional_kwargs.keys()))
            
            if snapshot and "messages" in snapshot.values:
                messages = snapshot.values["messages"]
                if messages:
                    last_msg = messages[-1]
                    
                    # 只有 AI 消息才需要补充发送 content
                    if isinstance(last_msg, AIMessage):
                        # 检查是否有 content 需要补充 (如果 full_answer 为空，说明没有流式输出过)
                        if last_msg.content and not full_answer:
                            # 过滤掉看起来像JSON的原始分析结果
                            content = last_msg.content
                            is_raw_json = (content.strip().startswith("{") and 
                                          ("needs_clarification" in content or "intent" in content))
                            
                            if not is_raw_json:
                                logger.info("补充发送非流式响应: %s", content[:50])
                                yield self._format_sse("token", {"content": content or ""})
                                done_payload["final_content"] = content
                            else:
                                logger.warning("跳过原始JSON输出: %s", content[:100])
                        
                        # 2. 如果流式未收集到，尝试从最后一条 AI 消息获取
                        if "additional_kwargs" not in done_payload and last_msg.additional_kwargs:
                            # 过滤掉不需要传给前端的字段
                            filtered = {k: v for k, v in last_msg.additional_kwargs.items() 
                                       if v is not None and k not in ("reasoning_content",)}
                            if filtered:
                                done_payload["additional_kwargs"] = filtered
                                logger.debug("使用 last_msg.additional_kwargs: %s", list(filtered.keys()))

                    # 3. 最后回溯寻找 (兼容旧逻辑)
                    if "additional_kwargs" not in done_payload:
                        for msg in reversed(messages):
                             if isinstance(msg, AIMessage) and hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
                                  additional = {k: v for k, v in msg.additional_kwargs.items() 
                                              if v is not None and k not in ("reasoning_content", )}
                                  if additional:
                                      done_payload["additional_kwargs"] = additional
                                      logger.debug("通过回溯找到 additional_kwargs: %s", list(additional.keys()))
                                      break

            # 流结束（对话由 postprocess 节点保存到数据库）
            streamed_content = "".join(full_answer)
            additional_keys = list(done_payload.get("additional_kwargs", {}).keys()) if done_payload.get("additional_kwargs") else []
            logger.info(
                "[SYNC-TRACE] 流式输出完成: thread_id=%s, content_len=%d, content_hash=%s, additional_kwargs_keys=%s, thinking=%s",
                thread_id, len(streamed_content), _content_hash(streamed_content), 
                additional_keys, bool(thinking_content)
            )
            
            yield self._format_sse("done", done_payload)
            
        except Exception as e:
            error_msg = str(e)
            
            # 保存错误消息到数据库（确保对话历史不丢失）
            ai_content = "".join(full_answer) if full_answer else f"[System Error: {error_msg}]"
            self._save_conversation_fallback(
                thread_id=thread_id,
                user_id=user_id,
                prompt=prompt,
                ai_content=ai_content,
                scenario="Exception",
            )
            
            # 检查是否为内容审核错误
            if "inappropriate content" in error_msg.lower() or "内容违规" in error_msg:
                logger.warning("内容审核拦截: %s", error_msg)
                # 返回友好提示并正常结束对话
                friendly_msg = "抱歉，您的请求内容或搜索结果触发了内容安全审核，无法继续处理。请尝试换一种方式提问。"
                yield self._format_sse("token", {"content": friendly_msg})
                yield self._format_sse("done", {"thread_id": thread_id})
            else:
                logger.exception("流式处理错误: %s", e)
                yield self._format_sse("error", {"message": error_msg})
    
    def _format_sse(self, event_type: str, data: dict) -> bytes:
        """格式化 SSE 事件。"""
        payload = json.dumps(data, ensure_ascii=False)
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
    # 用于收集流式过程中的结构化数据
    collected_additional_kwargs = {}
    
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
                    # 收集结构化数据用于 done 事件
                    if event_data.get("data_type"):
                        collected_additional_kwargs["data_type"] = event_data["data_type"]
                        collected_additional_kwargs["data"] = event_data.get("data")
                    yield format_sse("result", event_data)
                
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
                        yield format_sse("interrupt", {
                            "thread_id": thread_id,
                            "interrupt_id": str(id(interrupt)),
                            "value": interrupt.value if isinstance(interrupt.value, dict) else {"message": str(interrupt.value)},
                        })
                    return

        # 流结束
        logger.info("恢复流程完成: thread_id=%s, answer_len=%d", thread_id, len("".join(full_answer)))
        
        # 注意：AI 消息保存已由 _postprocess 节点统一处理，此处不再重复保存
        # 这避免了 resume 和 postprocess 同时保存导致的重复记录问题
        
        done_payload = {"thread_id": thread_id}
        
        # 1. 优先使用流式过程中收集的结构化数据
        if collected_additional_kwargs:
            done_payload["additional_kwargs"] = collected_additional_kwargs
        
        # 检查是否需要补充发送最后一条消息（针对非流式 Agent 响应）
        if snapshot and "messages" in snapshot.values:
            messages = snapshot.values["messages"]
            if messages:
                last_msg = messages[-1]
                if last_msg.type == "ai":
                    content = getattr(last_msg, "content", "")
                    additional = getattr(last_msg, "additional_kwargs", {})
                    
                    # 避免重复发送：只有当内容不同于已流式输出的内容时才补发
                    streamed_content = "".join(full_answer)
                    if content and content != streamed_content and not full_answer:
                         yield format_sse("token", {"content": content or ""})
                         done_payload["final_content"] = content
                    
                    # 2. 如果流式未收集到，从 snapshot 获取
                    if "additional_kwargs" not in done_payload and additional:
                        filtered = {k: v for k, v in additional.items() 
                                   if v is not None and k not in ("reasoning_content",)}
                        if filtered:
                            done_payload["additional_kwargs"] = filtered

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
