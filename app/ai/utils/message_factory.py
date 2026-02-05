"""消息工厂模块 - 统一创建带唯一 ID 的 LangChain 消息。

背景：
    LangChain 消息默认 id=None，导致 LangGraph 的 add_messages reducer 无法正确去重。
    本模块为所有消息分配唯一 ID，从根源解决消息重复问题。

使用方式：
    from app.ai.utils.message_factory import create_ai_message, create_human_message

    # 替代 AIMessage(content="...")
    msg = create_ai_message("回复内容")
    
    # 替代 HumanMessage(content="...")
    msg = create_human_message("用户输入")

参见：
    - docs/开发文档/架构设计/防屎山记录手册.md SP-001（消息去重机制）
    - docs/开发文档/架构设计/防屎山记录手册.md SP-013（streaming_wrapper 上帝函数）
"""
import uuid
import time
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


def _generate_id(content: str, prefix: str = "", use_timestamp: bool = True) -> str:
    """生成唯一消息 ID。
    
    策略：
    1. 基于内容生成 UUID5（确定性，相同内容生成相同 ID）
    2. 可选添加时间戳和随机数（避免同一内容在同一时刻的消息冲突）
    
    Args:
        content: 消息内容
        prefix: ID 前缀（如 "ai", "human", "sys"）
        use_timestamp: 是否添加时间戳（默认 True，用于区分同内容不同时间的消息）
    
    Returns:
        格式：{prefix}-{timestamp}-{random}-{uuid5} 或 {prefix}-{uuid5}
    """
    # 基于内容生成确定性 UUID5
    content_hash = str(uuid.uuid5(uuid.NAMESPACE_URL, content or ""))[:8]
    
    if use_timestamp:
        # 微秒级时间戳 + 4 位随机数，确保同一内容在同一时刻也有不同 ID
        ts = int(time.time() * 1000000)  # 微秒级
        rand = uuid.uuid4().hex[:4]  # 4 位随机数
        return f"{prefix}-{ts}-{rand}-{content_hash}"
    else:
        return f"{prefix}-{content_hash}"


def create_ai_message(
    content: str,
    *,
    id: Optional[str] = None,
    additional_kwargs: Optional[Dict[str, Any]] = None,
    use_timestamp: bool = True,
    **kwargs
) -> AIMessage:
    """创建带唯一 ID 的 AI 消息。
    
    Args:
        content: 消息内容
        id: 可选，手动指定 ID（不指定则自动生成）
        additional_kwargs: 附加参数（如 data_type, operation 等）
        use_timestamp: 生成 ID 时是否加时间戳（默认 True，同内容不同时刻不同 ID；
            False 时同内容生成相同 ID，可用于「同内容去重」场景）
        **kwargs: 其他 AIMessage 参数
    
    Returns:
        AIMessage 实例，保证 id 不为 None
    
    Example:
        # 简单用法
        msg = create_ai_message("回复内容")
        
        # 带附加数据
        msg = create_ai_message(
            "操作成功",
            additional_kwargs={"data_type": "todo_list", "data": [...]}
        )
    """
    msg_id = id or _generate_id(content, "ai", use_timestamp=use_timestamp)
    return AIMessage(
        content=content,
        id=msg_id,
        additional_kwargs=additional_kwargs or {},
        **kwargs
    )


def create_human_message(
    content: str,
    *,
    id: Optional[str] = None,
    use_timestamp: bool = True,
    **kwargs
) -> HumanMessage:
    """创建带唯一 ID 的用户消息。
    
    Args:
        content: 消息内容
        id: 可选，手动指定 ID
        use_timestamp: 生成 ID 时是否加时间戳（默认 True；False 时同内容同 ID）
        **kwargs: 其他 HumanMessage 参数
    
    Returns:
        HumanMessage 实例，保证 id 不为 None
    """
    msg_id = id or _generate_id(content, "human", use_timestamp=use_timestamp)
    return HumanMessage(content=content, id=msg_id, **kwargs)


def create_system_message(
    content: str,
    *,
    id: Optional[str] = None,
    use_timestamp: bool = False,
    **kwargs
) -> SystemMessage:
    """创建带唯一 ID 的系统消息。
    
    注意：系统消息通常是静态的（如 prompt 模板），默认不使用时间戳，
    避免每次调用生成不同 ID。
    
    Args:
        content: 消息内容
        id: 可选，手动指定 ID
        use_timestamp: 是否使用时间戳（默认 False）
        **kwargs: 其他 SystemMessage 参数
    
    Returns:
        SystemMessage 实例，保证 id 不为 None
    """
    msg_id = id or _generate_id(content, "sys", use_timestamp=use_timestamp)
    return SystemMessage(content=content, id=msg_id, **kwargs)


def create_tool_message(
    content: str,
    *,
    tool_call_id: str,
    name: Optional[str] = None,
    id: Optional[str] = None,
    **kwargs
) -> ToolMessage:
    """创建带唯一 ID 的工具消息。
    
    Args:
        content: 工具返回内容
        tool_call_id: 对应的 tool_call ID（必填）
        name: 工具名称
        id: 可选，手动指定消息 ID
        **kwargs: 其他 ToolMessage 参数
    
    Returns:
        ToolMessage 实例，保证 id 不为 None
    """
    msg_id = id or _generate_id(f"{tool_call_id}:{content[:50]}", "tool")
    return ToolMessage(
        content=content,
        tool_call_id=tool_call_id,
        name=name,
        id=msg_id,
        **kwargs
    )
