"""LangChain Agent 中间件模块（中文注释）。

提供 LangChain 1.0 风格的 Agent 中间件，使用官方的装饰器 API。
这些中间件可以传递给 create_agent 的 middleware 参数。

使用示例:
    from langchain.agents import create_agent
    from app.ai.middleware import message_trim_middleware
    
    agent = create_agent(
        model=llm,
        tools=tools,
        middleware=[message_trim_middleware],
        system_prompt="You are a helpful assistant."
    )
"""
import logging

from typing import Any, Optional
from langchain_core.messages import AIMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately

logger = logging.getLogger(__name__)


def _ensure_reasoning_content(messages: list) -> list:
    """确保 AIMessage 包含 reasoning_content 字段。
    
    DeepSeek Reasoner 模型在 Thinking Mode + Tool Calling 场景下要求：
    - 回答同一问题的多轮工具调用期间，必须将 reasoning_content 传回 API
    - 如果 AIMessage 缺少 reasoning_content，API 会返回 400 错误
    - 当新问题开始时（遇到新的 HumanMessage），可以清除之前的 reasoning_content
    
    该函数为缺少 reasoning_content 的 AIMessage 添加空字符串占位。
    注意：必须为所有带 tool_calls 的 AIMessage 添加此字段，即使已回复的消息也需要保留。
    
    参考: https://api-docs.deepseek.com/guides/thinking_mode#tool-calls
    """
    from app.ai import config as ai_config
    from langchain_core.messages import HumanMessage
    
    # 仅对 DeepSeek 提供商生效
    if getattr(ai_config, 'MODEL_PROVIDER', 'qwen') != 'deepseek':
        return messages
    
    # 检查是否启用了 thinking 模式
    if not getattr(ai_config, 'ENABLE_THINKING', False):
        return messages
    
    fixed_messages = []
    
    # 找到最后一条 HumanMessage 的索引（用于判断当前轮次）
    last_human_idx = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            last_human_idx = i
    
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage):
            # 检查是否有 tool_calls
            has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
            additional = getattr(msg, 'additional_kwargs', {}) or {}
            has_reasoning = 'reasoning_content' in additional
            
            # 只有在当前问题轮次内（最后一个 HumanMessage 之后）的带 tool_calls 消息需要 reasoning_content
            # 之前轮次的消息可以不需要 reasoning_content（DeepSeek 会忽略）
            is_current_turn = i > last_human_idx
            
            if has_tool_calls and not has_reasoning:
                # 需要添加 reasoning_content 占位符
                new_additional = dict(additional)
                new_additional['reasoning_content'] = ''
                
                # 创建新的 AIMessage（保留所有原始属性）
                fixed_msg = AIMessage(
                    content=msg.content,
                    tool_calls=msg.tool_calls,
                    additional_kwargs=new_additional,
                    response_metadata=getattr(msg, 'response_metadata', {}),
                    id=getattr(msg, 'id', None),
                    name=getattr(msg, 'name', None),
                )
                fixed_messages.append(fixed_msg)
                logger.debug("为 AIMessage (index=%d, is_current_turn=%s) 添加 reasoning_content 占位符", i, is_current_turn)
            else:
                fixed_messages.append(msg)
        else:
            fixed_messages.append(msg)
    
    return fixed_messages


def trim_and_fix_messages(messages: list, max_tokens: int = None) -> list:
    """裁剪并修复消息列表。
    
    执行以下操作：
    1. 裁剪历史消息，控制 token 消耗，防止超出上下文限制
    2. 确保 AIMessage 包含 reasoning_content（DeepSeek Reasoner 要求）
    
    Args:
        messages: 原始消息列表
        max_tokens: 最大 token 数，如果为 None 则使用默认配置
    
    Returns:
        处理后的消息列表
    """
    from app.ai import config as ai_config
    
    if max_tokens is None:
        max_tokens = ai_config.MESSAGE_MAX_TOKENS
    
    original_count = len(messages)
    
    # 使用官方的 trim_messages 工具裁剪
    trimmed = trim_messages(
        messages,
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=max_tokens,
        start_on="human",
        end_on=("human", "tool", "ai"),
        include_system=True,
    )
    
    if len(trimmed) < original_count:
        logger.info("消息裁剪: %d -> %d 条消息", original_count, len(trimmed))
    
    # 确保 AIMessage 包含 reasoning_content（DeepSeek Reasoner 要求）
    fixed = _ensure_reasoning_content(trimmed)
    
    return fixed


def message_trim_middleware(state: dict[str, Any], runtime: Any = None) -> Optional[dict[str, Any]]:
    """消息裁剪中间件（手动调用）。
    
    在调用模型前：
    1. 裁剪历史消息，控制 token 消耗，防止超出上下文限制
    2. 确保 AIMessage 包含 reasoning_content（DeepSeek Reasoner 要求）
    
    Args:
        state: Agent 状态字典，包含 messages 等字段
        runtime: LangGraph 运行时对象（保留参数位置，暂不使用）
    
    Returns:
        更新后的状态字典（仅包含需要更新的字段），或 None（无需更新）
    """
    messages = state.get("messages", [])
    
    if not messages:
        return None
    
    # 使用 trim_and_fix_messages 处理消息
    fixed = trim_and_fix_messages(messages)
    
    # 如果消息被修改了，返回更新
    if fixed is not messages and fixed != messages:
        logger.debug("消息裁剪中间件: 消息列表已更新")
        return {"messages": fixed}
    
    return None
