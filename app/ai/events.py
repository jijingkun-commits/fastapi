"""流式事件协议定义模块（中文注释）。

本模块定义了统一的流式事件类型和辅助函数，用于 Graph 节点通过
`get_stream_writer()` 发送结构化事件给前端。

使用方法:
    from langgraph.config import get_stream_writer
    from app.ai.events import emit_result, emit_token, emit_status
    
    def my_node(state):
        writer = get_stream_writer()
        emit_status(writer, "正在处理...")
        # ... 处理逻辑 ...
        emit_result(writer, "todo_list", {"todos": [...]})
        return state
"""
from typing import TypedDict, Literal, Optional, Any, Callable


# ==================== 事件类型定义 ====================

EventType = Literal[
    "token",           # AI 文本输出（流式 token）
    "thinking",        # 思考过程（深度思考模式）
    "tool_start",      # 工具调用开始
    "tool_end",        # 工具调用结束
    "status",          # 状态更新（如"正在查询..."）
    "result",          # 结构化结果（卡片数据：todo_list, image, chart 等）
    "confirmation",    # 确认请求（需要用户确认的操作）
    "clarification",   # 澄清问题（需要用户补充信息）
    "interrupt",       # 中断等待（Human-in-the-loop）
    "done",            # 流结束
    "error",           # 错误
]


class StreamEvent(TypedDict):
    """流式事件结构。"""
    type: EventType
    data: Any
    node: Optional[str]  # 来源节点名称（可选，用于调试）


# ==================== 辅助发送函数 ====================

# StreamWriter 类型别名（来自 langgraph.types.StreamWriter）
StreamWriter = Callable[[dict], None]


def emit_token(writer: StreamWriter, content: str, node: str = "") -> None:
    """发送文本 token 事件。
    
    Args:
        writer: LangGraph StreamWriter
        content: 文本内容
        node: 来源节点名称
    """
    writer({
        "type": "token",
        "data": {"content": content},
        "node": node
    })


def emit_thinking(writer: StreamWriter, content: str, node: str = "") -> None:
    """发送思考过程事件（深度思考模式）。
    
    Args:
        writer: LangGraph StreamWriter
        content: 思考内容
        node: 来源节点名称
    """
    writer({
        "type": "thinking",
        "data": {"content": content},
        "node": node
    })


def emit_status(writer: StreamWriter, message: str, node: str = "") -> None:
    """发送状态更新事件。
    
    用于通知前端当前处理进度，如"正在分析图片..."、"正在查询数据库..."。
    
    Args:
        writer: LangGraph StreamWriter
        message: 状态消息
        node: 来源节点名称
    """
    writer({
        "type": "status",
        "data": {"message": message},
        "node": node
    })


def emit_tool_start(
    writer: StreamWriter,
    tool_name: str,
    tool_input: dict = None,
    node: str = ""
) -> None:
    """发送工具调用开始事件。
    
    用于通知前端 AI 正在调用某个工具。
    
    Args:
        writer: LangGraph StreamWriter
        tool_name: 工具名称
        tool_input: 工具输入参数（可选，用于调试）
        node: 来源节点名称
    """
    writer({
        "type": "tool_start",
        "data": {
            "name": tool_name,
            "input": tool_input or {}
        },
        "node": node
    })


def emit_tool_end(
    writer: StreamWriter,
    tool_name: str,
    output: str = "",
    node: str = ""
) -> None:
    """发送工具调用结束事件。
    
    用于通知前端工具执行完成。
    
    Args:
        writer: LangGraph StreamWriter
        tool_name: 工具名称
        output: 工具输出（可选，用于调试）
        node: 来源节点名称
    """
    writer({
        "type": "tool_end",
        "data": {
            "name": tool_name,
            "output": output
        },
        "node": node
    })


def emit_kb_images(writer: StreamWriter, kb_images: dict, node: str = "") -> None:
    """发送知识库图片映射事件。
    
    用于通知前端图片占位符 [IMG-N] 与实际 URL 的映射关系，
    前端在渲染时进行替换。
    
    Args:
        writer: LangGraph StreamWriter
        kb_images: 图片映射字典 {索引: URL}
        node: 来源节点名称
    """
    writer({
        "type": "kb_images",
        "data": {"images": kb_images},
        "node": node
    })


def emit_result(
    writer: StreamWriter,
    data_type: str,
    data: dict,
    message: str = "",
    node: str = ""
) -> None:
    """发送结构化结果事件。
    
    用于发送需要特殊 UI 渲染的数据，如待办列表、图表、图片等。
    
    Args:
        writer: LangGraph StreamWriter
        data_type: 数据类型（如 "todo_list", "image", "chart"）
        data: 结构化数据
        message: 可选的文本消息
        node: 来源节点名称
        
    示例:
        emit_result(writer, "todo_list", {"todos": todos_data}, "找到 3 条待办")
        emit_result(writer, "image", {"url": minio_url})
    """
    writer({
        "type": "result",
        "data": {
            "data_type": data_type,
            "data": data,
            "message": message
        },
        "node": node
    })


def emit_confirmation(
    writer: StreamWriter,
    operation: dict,
    message: str,
    node: str = ""
) -> None:
    """发送确认请求事件。
    
    用于需要用户确认的操作（如创建、删除待办）。
    
    Args:
        writer: LangGraph StreamWriter
        operation: 待确认的操作详情
        message: 确认提示消息
        node: 来源节点名称
    """
    writer({
        "type": "confirmation",
        "data": {
            "operation": operation,
            "message": message
        },
        "node": node
    })


def emit_clarification(
    writer: StreamWriter,
    questions: list,
    message: str = "",
    node: str = ""
) -> None:
    """发送澄清问题事件。
    
    用于需要用户补充信息的场景。
    
    Args:
        writer: LangGraph StreamWriter
        questions: 需要澄清的问题列表
        message: 可选的引导消息
        node: 来源节点名称
    """
    writer({
        "type": "clarification",
        "data": {
            "questions": questions,
            "message": message
        },
        "node": node
    })


def emit_error(writer: StreamWriter, message: str, node: str = "") -> None:
    """发送错误事件。
    
    Args:
        writer: LangGraph StreamWriter
        message: 错误消息
        node: 来源节点名称
    """
    writer({
        "type": "error",
        "data": {"message": message},
        "node": node
    })


def emit_done(writer: StreamWriter, thread_id: str = "", node: str = "") -> None:
    """发送流结束事件。
    
    Args:
        writer: LangGraph StreamWriter
        thread_id: 对话线程 ID
        node: 来源节点名称
    """
    writer({
        "type": "done",
        "data": {"thread_id": thread_id},
        "node": node
    })
