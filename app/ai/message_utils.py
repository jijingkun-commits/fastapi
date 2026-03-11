"""消息处理工具模块（中文注释）。

提供 LangChain/LangGraph 消息序列的验证、修复、转换等通用函数。
"""
import logging
from typing import Sequence

from langchain_core.messages import BaseMessage, AIMessage, ToolMessage

from app.core.message_content import normalize_message_content


logger = logging.getLogger(__name__)


_TEXT_BLOCK_TYPES = {"text", "output_text", "refusal"}
_INTERNAL_BLOCK_TYPES = {"function_call", "function_result", "tool_call", "tool_use", "tool_result"}


def _has_readable_text_payload(block: dict) -> bool:
    """判断 text-like block 是否真的携带可读正文。"""
    for key in ("text", "content", "data", "message"):
        value = block.get(key)
        if normalize_message_content(value).strip():
            return True
    return False


def _sanitize_ai_message_content(message: AIMessage) -> AIMessage | None:
    """清理 assistant 历史消息中的空壳文本块。"""
    content = getattr(message, "content", None)
    if not isinstance(content, list):
        return message

    sanitized: list = []
    removed_count = 0
    for block in content:
        if isinstance(block, dict):
            block_type = str(block.get("type", "")).lower()
            if block_type in _INTERNAL_BLOCK_TYPES:
                removed_count += 1
                continue
            if block_type in _TEXT_BLOCK_TYPES and not _has_readable_text_payload(block):
                removed_count += 1
                continue
            if block_type and not normalize_message_content(block).strip():
                removed_count += 1
                continue
        sanitized.append(block)

    if removed_count == 0:
        return message

    logger.warning(
        "移除空 assistant 内容块: message_id=%s, removed=%d",
        getattr(message, "id", None),
        removed_count,
    )

    if sanitized:
        message.content = sanitized
        return message

    if getattr(message, "tool_calls", None):
        message.content = ""
        return message

    logger.warning("移除无有效内容的 assistant 历史消息: message_id=%s", getattr(message, "id", None))
    return None


def validate_messages(messages: Sequence[BaseMessage], fix_reasoning: bool = False) -> list[BaseMessage]:
    """验证并修复消息序列。
    
    1. 确保 tool_calls 后面有对应的 ToolMessage。
    2. (可选) 修复 DeepSeek Missing reasoning_content 问题。
    
    Args:
        messages: 原始消息序列
        fix_reasoning: 是否尝试修复 DeepSeek reasoning_content (默认 False)
    """
    if fix_reasoning:
        messages = fix_deepseek_reasoning(messages)

    if not messages:
        return list(messages)

    sanitized_messages = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            sanitized = _sanitize_ai_message_content(msg)
            if sanitized is None:
                continue
            sanitized_messages.append(sanitized)
        else:
            sanitized_messages.append(msg)

    validated = []
    i = 0
    messages = list(sanitized_messages)  # 确保可索引
    
    while i < len(messages):
        msg = messages[i]
        
        # 检查是否是包含 tool_calls 的 AIMessage
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            tool_call_ids = set()
            for tc in msg.tool_calls:
                if isinstance(tc, dict):
                    tc_id = tc.get('id') or tc.get('tool_call_id')
                    if tc_id:
                        tool_call_ids.add(tc_id)
            
            # 收集后续的 ToolMessage
            j = i + 1
            found_tool_ids = set()
            while j < len(messages) and isinstance(messages[j], ToolMessage):
                tool_call_id = getattr(messages[j], 'tool_call_id', None)
                if tool_call_id:
                    found_tool_ids.add(tool_call_id)
                j += 1
            
            # 检查是否所有 tool_calls 都有对应的响应
            if tool_call_ids and not tool_call_ids.issubset(found_tool_ids):
                # 不完整的 tool_calls 序列，跳过这条 AIMessage 及其后续的 ToolMessages
                missing_ids = tool_call_ids - found_tool_ids
                logger.warning("移除不完整的 tool_calls 消息: missing_ids=%s", missing_ids)
                i = j  # 跳过所有相关消息
                continue
            
            # 完整的序列，保留所有消息
            validated.append(msg)
            for k in range(i + 1, j):
                validated.append(messages[k])
            i = j
        else:
            validated.append(msg)
            i += 1
    
    return validated


def fix_deepseek_reasoning(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """修复 DeepSeek Reasoner 的历史消息。
    
    DeepSeek Reasoner (R1) 要求 Assistant 消息必须包含 reasoning_content 字段。
    如果历史消息（可能是由非 DeepSeek Client 生成或旧版本保存）缺失此字段，
    API 会报错 "Missing reasoning_content field"。
    
    此函数会检查 AIMessage，如果缺失 reasoning_content，则填充为空字符串。
    """
    fixed = []
    fix_count = 0
    
    for msg in messages:
        if isinstance(msg, AIMessage):
            # 检查 additional_kwargs 是否有 reasoning_content
            if "reasoning_content" not in msg.additional_kwargs:
                msg.additional_kwargs["reasoning_content"] = ""
                fix_count += 1
        fixed.append(msg)
    
    if fix_count > 0:
        logger.info("fix_deepseek_reasoning: 修复了 %d 条消息的 reasoning_content", fix_count)
    
    return fixed
