"""Chat API 端点（中文注释）。

提供聊天相关的所有接口：
- 流式对话
- 对话历史查询和管理
- 恢复被中断的流程（人工审核）
"""
import logging
from datetime import datetime
from typing import Optional, List, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.services.chat_service import sse_stream, sse_resume_stream
from app.services.run_control_service import (
    ActiveRunExistsError,
    ParallelLimitExceededError,
    RunNotFoundError,
    RunPermissionDeniedError,
    RunThreadMismatchError,
    run_control_service,
)
from app.schemas.chat import ChatRequest, FeedbackRequest
from app.repositories import chat_repo
from app.api.deps import get_current_user
from app.core.utils import content_hash as _content_hash
from app.core.message_content import normalize_legacy_message_content

from app.ai.workflow.multi_agent_graph import cancel_checkpoint
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
    feedback_score: Optional[int] = None  # 用户反馈: 1(赞) / -1(踩) / None(无)

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


class BatchDeleteRequest(BaseModel):
    """批量删除请求模型。"""
    thread_ids: List[str]


class ResumeRequest(BaseModel):
    """恢复中断请求模型。"""
    thread_id: str
    run_id: Optional[str] = None
    decision: dict  # {"type": "accept"} / {"type": "reject"} / {"type": "edit", "args": {...}}
    delay_ms: int = 0


class CancelRunRequest(BaseModel):
    """取消运行请求模型。"""

    thread_id: Optional[str] = None


class ActiveRunItemResponse(BaseModel):
    """活跃运行项响应。"""

    run_id: str
    thread_id: str
    status: str
    updated_at: str
    last_activity_at: Optional[str] = None


class ActiveRunListResponse(BaseModel):
    """活跃运行列表响应。"""

    items: List[ActiveRunItemResponse]
    active_count: int
    poll_hint_seconds: int
    server_time: str


def _serialize_datetime(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


# ==================== Stream Endpoint ====================

@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """流式对话接口。
    
    支持多轮对话，返回 SSE 格式的事件流。
    幂等性由系统中间件统一处理（通过 Idempotency-Key 请求头）。
    """
    trace_id = request.headers.get("X-Trace-Id", "-")
    remote = getattr(request.client, "host", "-")
    resolved_thread_id = payload.thread_id or str(uuid4())
    resolved_run_id = payload.run_id

    logger.info(
        "Chat流请求 来自=%s 提示词长度=%d 延迟毫秒=%d trace_id=%s user_id=%d thinking=%s run_id=%s",
        remote,
        len(payload.prompt),
        payload.delay_ms,
        trace_id,
        current_user.id,
        payload.enable_thinking,
        payload.run_id,
    )

    if run_control_service.is_enabled():
        try:
            run_snapshot = run_control_service.create_run(
                thread_id=resolved_thread_id,
                user_id=current_user.id,
                run_id=resolved_run_id,
                db=db,
            )
        except ActiveRunExistsError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "active_run_exists",
                    "thread_id": exc.thread_id,
                    "run_id": exc.active_run_id,
                },
            )
        except ParallelLimitExceededError as exc:
            raise HTTPException(
                status_code=429,
                detail={
                    "error_code": "parallel_limit_exceeded",
                    "active_count": exc.active_count,
                    "limit": exc.limit,
                },
            )
        resolved_run_id = run_snapshot.run_id

    gen = sse_stream(
        payload.prompt,
        payload.delay_ms,
        resolved_thread_id,
        current_user.id,
        payload.enable_thinking,
        payload.model_id,
        payload.attachments,
        payload.current_todo_id,
        resolved_run_id,
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
        "Resume流请求 thread_id=%s run_id=%s decision=%s trace_id=%s user_id=%d",
        payload.thread_id,
        payload.run_id,
        payload.decision.get("type"),
        trace_id,
        current_user.id,
    )
    gen = sse_resume_stream(
        payload.thread_id,
        payload.decision,
        current_user.id,
        payload.delay_ms,
        payload.run_id,
    )
    return StreamingResponse(gen, media_type="text/event-stream")


@router.get("/runs/active", response_model=ActiveRunListResponse)
def list_active_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回当前用户全部 active runs。"""

    if not run_control_service.is_active_runs_query_enabled():
        raise HTTPException(
            status_code=503,
            detail={"error_code": "active_runs_unavailable", "message": "运行态暂不可用，请稍后重试"},
        )

    items = [
        ActiveRunItemResponse(
            run_id=snapshot.run_id,
            thread_id=snapshot.thread_id,
            status=snapshot.status,
            updated_at=_serialize_datetime(snapshot.updated_at) or "",
            last_activity_at=_serialize_datetime(snapshot.last_activity_at),
        )
        for snapshot in run_control_service.list_active_runs_by_user(user_id=current_user.id, db=db)
    ]
    return ActiveRunListResponse(
        items=items,
        active_count=len(items),
        poll_hint_seconds=2,
        server_time=_serialize_datetime(datetime.now()) or "",
    )


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    payload: Optional[CancelRunRequest] = None,
):
    """取消指定 run（幂等）。"""

    trace_id = request.headers.get("X-Trace-Id", "-")
    request_payload = payload or CancelRunRequest()

    if not request_payload.thread_id:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "thread_id_required", "message": "thread_id is required"},
        )

    logger.info(
        "取消 run 请求: run_id=%s, user_id=%s, thread_id=%s, trace_id=%s",
        run_id,
        current_user.id,
        request_payload.thread_id,
        trace_id,
    )

    try:
        result = run_control_service.cancel_run(
            run_id=run_id,
            requester_user_id=current_user.id,
            is_admin=getattr(current_user, "role", "") == "admin",
            reason="user_cancelled",
            cancel_mode="hard",
            thread_id=request_payload.thread_id,
            db=db,
        )
    except RunThreadMismatchError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "thread_id_mismatch",
                "message": str(exc),
                "run_id": exc.run_id,
                "thread_id": request_payload.thread_id,
            },
        )
    except ValueError as exc:
        if "thread_id" not in str(exc):
            raise
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "thread_id_mismatch",
                "message": str(exc),
                "run_id": run_id,
                "thread_id": request_payload.thread_id,
            },
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RunPermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if result.thread_id:
        await cancel_checkpoint(result.thread_id, run_id=result.run_id)

    return {
        "accepted": result.accepted,
        "run_id": result.run_id,
        "thread_id": result.thread_id,
        "status": result.status,
        "idempotent": result.idempotent,
        "reason": result.reason,
    }


# ==================== History Endpoints ====================

@router.get("/threads", response_model=List[ThreadOut])
def list_threads(
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, description="最大返回数量"),
    db: Session = Depends(get_db),
):
    """获取当前用户的对话列表。"""
    return chat_repo.get_threads_by_user(db, current_user.id, limit)


@router.get("/threads/latest", response_model=Optional[ThreadOut])
def get_latest_thread(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户最近更新的会话。"""

    latest = chat_repo.get_latest_thread_by_user(db, current_user.id)
    return latest


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
    
    # 批量查询该用户对这些消息的反馈状态
    message_ids = [m.id for m in messages]
    feedback_map = {}
    if message_ids:
        try:
            feedback_map = chat_repo.get_feedback_scores_batch(
                db, user_id=current_user.id, message_ids=message_ids
            )
        except Exception as e:
            logger.debug("批量查询反馈状态失败（不影响主流程）: %s", e)
    
    result = []
    for m in messages:
        content = normalize_legacy_message_content(m.content)
        
        # 同步追踪日志（仅对 AI 消息记录）
        if m.role == "ai":
            extra_keys = list(m.extra_data.keys()) if m.extra_data else []
            logger.info(
                "[SYNC-TRACE] 历史加载: thread_id=%s, msg_id=%d, ai_len=%d, ai_hash=%s, extra_data_keys=%s",
                thread_id, m.id, len(content) if content else 0, 
                _content_hash(content) if content else "empty", extra_keys
            )
        
        result.append(MessageOut(
            id=m.id,
            thread_id=m.thread_id,
            role=m.role,
            content_type=m.content_type,
            content=content,
            metadata=m.extra_data,
            additional_kwargs=m.extra_data,
            title=m.title,
            created_at=m.create_time.isoformat() if m.create_time else None,
            feedback_score=feedback_map.get(m.id),
        ))
    
    return result


@router.delete("/threads/batch")
def delete_threads_batch(
    request: BatchDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量删除对话线程及其资产（仅限当前用户）。
    
    注意：此接口必须在 /threads/{thread_id} 之前定义，
    否则 FastAPI 会将 "batch" 匹配为 thread_id。
    """
    if not request.thread_ids:
        raise HTTPException(status_code=400, detail="thread_ids 不能为空")
    if len(request.thread_ids) > 100:
        raise HTTPException(status_code=400, detail="单次最多删除 100 个对话")
    
    # 清理内存中的 DataFrame 缓存
    from app.ai.tools.chatTools import cleanup_thread_dataframes
    for thread_id in request.thread_ids:
        cleanup_thread_dataframes(thread_id)
    
    # 批量删除
    stats = chat_repo.delete_threads_batch(db, request.thread_ids, current_user.id)
    
    return {
        "message": f"已删除 {stats['threads_deleted']} 个对话",
        "stats": stats,
    }


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
    """提交消息反馈（点赞/点踩）。
    
    点踩数据查询类消息时，自动将该查询记录到 SQL 修正台（t_data_query_log），
    供管理员审核和修正。
    """
    try:
        feedback = chat_repo.save_feedback(
            db,
            user_id=current_user.id,
            message_id=payload.message_id,
            score=payload.score,
            reason=payload.reason,
        )
        
        # 点踩时：如果是数据查询类消息，自动记录到 SQL 修正台
        if payload.score == -1:
            _log_disliked_sql_query(db, payload.message_id, current_user.id)
        
        return {"message": "反馈已提交", "data": feedback}
    except Exception as e:
        logger.error("提交反馈失败: %s", e)
        raise HTTPException(status_code=500, detail="提交反馈失败")


def _log_disliked_sql_query(db: Session, message_id: int, user_id: int):
    """点踩时将数据查询记录到 SQL 修正台。
    
    从消息的 metadata 中提取 SQL 信息，写入 t_data_query_log。
    仅处理 data_type='sql_result' 的消息，其他类型跳过。
    """
    try:
        from app.models.chat_message import ChatMessage
        from app.models.data_agent_metadata import DataQueryLog
        
        # 查找被点踩的消息
        msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        if not msg or not msg.extra_data:
            return
        
        extra = msg.extra_data
        if not isinstance(extra, dict) or extra.get("data_type") != "sql_result":
            return
        
        data = extra.get("data", {})
        sql = data.get("sql")
        if not sql:
            return
        
        # 查找同一线程中最近的用户问题
        question = ""
        if msg.thread_id:
            human_msg = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.thread_id == msg.thread_id,
                    ChatMessage.role == "human",
                    ChatMessage.id < message_id
                )
                .order_by(ChatMessage.id.desc())
                .first()
            )
            if human_msg:
                question = human_msg.content or ""
        
        if not question:
            question = "(未找到原始问题)"
        
        # 避免重复写入（同一消息只记录一次）
        existing = (
            db.query(DataQueryLog)
            .filter(DataQueryLog.generated_sql == sql, DataQueryLog.user_id == user_id)
            .first()
        )
        if existing:
            logger.debug("SQL 修正台已存在相同记录，跳过: message_id=%d", message_id)
            return
        
        # 异步生成 embedding（失败不阻塞）
        embedding = None
        try:
            from app.ai.utils.embedding_util import get_embedding
            embedding = get_embedding(question)
        except Exception:
            pass
        
        log = DataQueryLog(
            user_id=user_id,
            thread_id=msg.thread_id,
            question=question,
            generated_sql=sql,
            sql_source=data.get("sql_source", "unknown"),
            is_correct=False,
            question_embedding=embedding,
        )
        db.add(log)
        db.commit()
        logger.info("点踩触发 SQL 修正台记录: message_id=%d, question=%s", message_id, question[:50])
        
    except Exception as e:
        logger.warning("SQL 修正台记录失败（不影响反馈流程）: %s", e)
