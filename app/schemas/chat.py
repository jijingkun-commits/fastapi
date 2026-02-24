"""Chat 请求/响应模型（中文注释）。"""
from typing import Optional, List
from pydantic import BaseModel


class Attachment(BaseModel):
    """附件信息模型。"""
    name: str
    url: str
    mime_type: str
    size: int
    object_key: str


class ChatRequest(BaseModel):
    """聊天请求体（用于流式输出）。
    
    幂等性由系统中间件统一处理（通过 Idempotency-Key 请求头）。
    注意：use_multi_agent 参数已废弃，系统默认使用多智能体模式。
    """
    prompt: str
    delay_ms: int = 50
    thread_id: Optional[str] = None
    run_id: Optional[str] = None  # 可选 run_id（用于重连/观测）
    enable_thinking: bool = False  # 是否启用深度思考模式
    model_id: Optional[str] = None  # 可选模型标识
    # use_multi_agent 已废弃（2026-01-31），保留字段仅为兼容旧客户端
    use_multi_agent: bool = True  # 已废弃，始终使用多智能体模式
    attachments: Optional[List[Attachment]] = None  # 用户上传的附件列表
    current_todo_id: Optional[int] = None  # 当前正在讨论的待办 ID


class FeedbackRequest(BaseModel):
    """消息反馈请求模型。"""
    message_id: int
    score: int  # 1: Like, -1: Dislike, 0: Cancel
    reason: Optional[str] = None


