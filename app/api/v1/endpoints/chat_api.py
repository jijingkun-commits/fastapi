"""Chat API 端点（中文注释）。

提供聊天相关的所有接口：
- 流式对话
- 对话历史查询和管理
- 恢复被中断的流程（人工审核）
"""
import logging
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.services.chat_service import sse_stream, sse_resume_stream
from app.schemas.chat import ChatRequest, FeedbackRequest
from app.repositories import chat_repo
from app.api.deps import get_current_user

from app.models.user import User


router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("api.chat")


# ==================== Schemas ====================

class ContentBlock(BaseModel):
    """内容块模型。"""
    type: str  # markdown / chart / image / custom_ui
    data: Any


class MessageOut(BaseModel):
    """消息输出模型。"""
    id: int
    thread_id: str
    role: str  # human / ai
    content_type: str  # text / markdown / mixed / multimodal
    content: Any  # 字符串或 ContentBlock 数组
    metadata: Optional[dict] = None
    additional_kwargs: Optional[dict] = None  # 用于前端组件渲染
    title: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ThreadOut(BaseModel):
    """对话线程输出模型。"""
    thread_id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdateTitleRequest(BaseModel):
    """更新标题请求模型。"""
    title: str


class ResumeRequest(BaseModel):
    """恢复中断请求模型。"""
    thread_id: str
    decision: dict  # {"type": "accept"} / {"type": "reject"} / {"type": "edit", "args": {...}}
    delay_ms: int = 0


# ==================== Stream Endpoint ====================

@router.post("/stream")
async def chat_stream(
    payload: ChatRequest, 
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """流式对话接口。
    
    支持多轮对话，返回 SSE 格式的事件流。
    """
    trace_id = request.headers.get("X-Trace-Id", "-")
    remote = getattr(request.client, "host", "-")
    logger.info(
        "Chat流请求 来自=%s 提示词长度=%d 延迟毫秒=%d trace_id=%s user_id=%d thinking=%s multi_agent=%s",
        remote,
        len(payload.prompt),
        payload.delay_ms,
        trace_id,
        current_user.id,
        payload.enable_thinking,
        payload.use_multi_agent,
    )
    gen = sse_stream(
        payload.prompt, 
        payload.delay_ms, 
        payload.thread_id, 
        current_user.id,
        payload.enable_thinking,
        payload.model_id,
        payload.use_multi_agent,
        payload.attachments,
        payload.current_todo_id,
    )
    return StreamingResponse(gen, media_type="text/event-stream")


@router.post("/resume")
async def resume_stream(
    payload: ResumeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """恢复被中断的流程（人工审核后调用）。
    
    用于在用户批准/编辑/拒绝 interrupt 后继续执行 Agent。
    """
    trace_id = request.headers.get("X-Trace-Id", "-")
    logger.info(
        "Resume流请求 thread_id=%s decision=%s trace_id=%s user_id=%d",
        payload.thread_id,
        payload.decision.get("type"),
        trace_id,
        current_user.id,
    )
    gen = sse_resume_stream(
        payload.thread_id,
        payload.decision,
        current_user.id,
        payload.delay_ms,
    )
    return StreamingResponse(gen, media_type="text/event-stream")


# ==================== History Endpoints ====================

@router.get("/threads", response_model=List[ThreadOut])
def list_threads(
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, description="最大返回数量"),
    db: Session = Depends(get_db),
):
    """获取当前用户的对话列表。"""
    return chat_repo.get_threads_by_user(db, current_user.id, limit)


@router.get("/threads/{thread_id}/messages", response_model=List[MessageOut])
def get_thread_messages(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    limit: int = Query(100, description="最大返回数量"),
    db: Session = Depends(get_db),
):
    """获取指定对话的消息历史。
    
    自动将 minio:// 协议替换为有效的预签名 URL。
    """
    messages = chat_repo.get_messages_by_thread(db, thread_id, limit)
    
    result = []
    for m in messages:
        # 替换消息内容中的 minio:// URL
        content = m.content
        if content and "minio://" in content:
             # 旧数据兼容：如果仍有 minio://，保留原样或日志警告，不再尝试转换
             # 因为 message_processor 已被移除
             pass
        
        result.append(MessageOut(
            id=m.id,
            thread_id=m.thread_id,
            role=m.role,
            content_type=m.content_type,
            content=content,
            metadata=m.extra_data,
            additional_kwargs=m.extra_data,  # 映射 extra_data 到 additional_kwargs
            title=m.title,
            created_at=m.create_time.isoformat() if m.create_time else None,
        ))
    
    return result


@router.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除对话线程及其资产（仅限当前用户）。"""
    # 清理内存中的 DataFrame 缓存
    from app.ai.tools.chatTools import cleanup_thread_dataframes
    cleanup_thread_dataframes(thread_id)
    
    # 使用 delete_thread_with_assets 同时清理 MinIO 资产
    stats = chat_repo.delete_thread_with_assets(db, thread_id, current_user.id)
    if stats["messages"] == 0:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {
        "message": f"已删除 {stats['messages']} 条消息, {stats['assets']} 个资产", 
        "thread_id": thread_id,
        "stats": stats,
    }


@router.patch("/threads/{thread_id}/title")
def update_thread_title(
    thread_id: str,
    request: UpdateTitleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新对话标题（仅限当前用户）。"""
    success = chat_repo.update_thread_title(
        db, thread_id, request.title, current_user.id
    )
    if not success:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"message": "标题已更新", "thread_id": thread_id, "title": request.title}


@router.post("/feedback")
def submit_feedback(
    payload: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交消息反馈（点赞/点踩）。"""
    try:
        feedback = chat_repo.save_feedback(
            db,
            user_id=current_user.id,
            message_id=payload.message_id,
            score=payload.score,
            reason=payload.reason,
        )
        return {"message": "反馈已提交", "data": feedback}
    except Exception as e:
        logger.error("提交反馈失败: %s", e)
        raise HTTPException(status_code=500, detail="提交反馈失败")

