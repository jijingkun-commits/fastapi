"""对话消息数据访问层（中文注释）。

提供对话消息的 CRUD 操作。
基于单表 t_chat_message 设计，title 存储在第一条 human 消息中。
"""
import json
import logging
from typing import Optional, List, Any, Dict
from datetime import datetime
from sqlalchemy import func
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.chat_asset import ChatAsset
from app.repositories import chat_assets_repository
from app.core.message_content import normalize_message_content
from app.core.message_display_blocks import compile_message_display_blocks
from app.core.utils import content_hash as _content_hash


logger = logging.getLogger(__name__)


def _to_non_negative_int(value: Any) -> Optional[int]:
    """将值安全转换为非负整数。"""

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _coerce_result_event_item(raw_event: Any) -> Optional[Dict[str, Any]]:
    """规范化单条 result_event。"""

    if not isinstance(raw_event, dict):
        return None

    data_type = str(raw_event.get("data_type") or "").strip()
    if not data_type:
        return None

    normalized: Dict[str, Any] = dict(raw_event)
    normalized["data_type"] = data_type
    normalized["data"] = raw_event.get("data") if isinstance(raw_event.get("data"), dict) else {}

    message = raw_event.get("message")
    if isinstance(message, str):
        message = message.strip()
        if message:
            normalized["message"] = message
        else:
            normalized.pop("message", None)
    else:
        normalized.pop("message", None)

    sequence_number = _to_non_negative_int(raw_event.get("sequence_number"))
    if sequence_number is not None:
        normalized["sequence_number"] = sequence_number
    else:
        normalized.pop("sequence_number", None)

    envelope = raw_event.get("envelope")
    if isinstance(envelope, dict):
        normalized["envelope"] = dict(envelope)
    else:
        normalized.pop("envelope", None)

    return normalized


def _build_legacy_result_event_from_pair(additional_kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """从 legacy data_type + data 字段构建单条 result_event。"""

    data_type = str(additional_kwargs.get("data_type") or "").strip()
    if not data_type:
        return None

    legacy_event: Dict[str, Any] = {
        "data_type": data_type,
        "data": additional_kwargs.get("data") if isinstance(additional_kwargs.get("data"), dict) else {},
    }

    message = additional_kwargs.get("message")
    if isinstance(message, str) and message.strip():
        legacy_event["message"] = message.strip()

    sequence_number = _to_non_negative_int(additional_kwargs.get("sequence_number"))
    if sequence_number is not None:
        legacy_event["sequence_number"] = sequence_number

    envelope = additional_kwargs.get("envelope")
    if isinstance(envelope, dict):
        legacy_event["envelope"] = dict(envelope)

    return _coerce_result_event_item(legacy_event)


def _resolve_result_events_for_replay(additional_kwargs: Dict[str, Any]) -> tuple[list[Dict[str, Any]], str]:
    """按 read-old-write-new 语义解析 result_events。"""

    raw_events = additional_kwargs.get("result_events")
    if isinstance(raw_events, list):
        normalized_events = [
            item
            for item in (_coerce_result_event_item(raw) for raw in raw_events)
            if item is not None
        ]
        if normalized_events:
            return normalized_events, "result_events"

    legacy_single = _coerce_result_event_item(additional_kwargs.get("result_event"))
    if legacy_single is not None:
        return [legacy_single], "result_event"

    legacy_pair = _build_legacy_result_event_from_pair(additional_kwargs)
    if legacy_pair is not None:
        return [legacy_pair], "data_type_data"

    return [], "none"


def _result_event_sort_key(event: Dict[str, Any], index: int) -> tuple[int, int, int]:
    """生成 result_event 的稳定排序键（sequence_number 优先）。"""

    sequence_number = _to_non_negative_int(event.get("sequence_number"))
    if sequence_number is not None:
        return (0, sequence_number, index)

    envelope = event.get("envelope")
    if isinstance(envelope, dict):
        envelope_sequence = _to_non_negative_int(envelope.get("sequence_number"))
        if envelope_sequence is not None:
            return (0, envelope_sequence, index)

    return (1, index, index)


def _sort_result_events_by_sequence(events: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """按 sequence_number 对 result_events 保序排序。"""

    enumerated = [(idx, event) for idx, event in enumerate(events)]
    enumerated.sort(key=lambda pair: _result_event_sort_key(pair[1], pair[0]))
    return [event for _, event in enumerated]


def _normalize_result_additional_kwargs_for_replay(additional_kwargs: Any) -> Dict[str, Any]:
    """规范化 result replay 载荷：读旧写新到 result_events[]。"""

    normalized = dict(additional_kwargs) if isinstance(additional_kwargs, dict) else {}
    result_events, compat_source = _resolve_result_events_for_replay(normalized)
    if not result_events:
        return normalized

    ordered_events = _sort_result_events_by_sequence(result_events)
    latest_event = ordered_events[-1]

    normalized["result_events"] = ordered_events
    normalized["result_event"] = latest_event
    normalized["result_count"] = len(ordered_events)
    normalized["compat_source"] = compat_source
    normalized["data_type"] = latest_event.get("data_type")
    normalized["data"] = latest_event.get("data", {})

    latest_message = latest_event.get("message")
    if isinstance(latest_message, str) and latest_message.strip():
        normalized["message"] = latest_message

    return normalized


def _normalize_kb_images_payload(value: Any) -> Dict[str, str]:
    """规范化 kb_images 载荷。"""

    if not isinstance(value, dict):
        return {}

    normalized: Dict[str, str] = {}
    for key, raw_url in value.items():
        if not isinstance(raw_url, str):
            continue
        url = raw_url.strip()
        if not url:
            continue
        normalized[str(key)] = url
    return normalized


def _merge_turn_kb_images_into_additional_kwargs(
    base_additional_kwargs: Any,
    ai_messages: List[Any],
    tool_kb_images: Dict[str, str],
) -> tuple[Dict[str, Any], Dict[str, str]]:
    """将当前轮 kb_images 收敛到 AI additional_kwargs。"""

    merged = dict(base_additional_kwargs) if isinstance(base_additional_kwargs, dict) else {}
    resolved_kb_images = _normalize_kb_images_payload(tool_kb_images)

    for message in ai_messages or []:
        additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
        if not isinstance(additional_kwargs, dict):
            continue
        resolved_kb_images.update(_normalize_kb_images_payload(additional_kwargs.get("kb_images")))

    if resolved_kb_images:
        merged["kb_images"] = resolved_kb_images
    else:
        merged.pop("kb_images", None)

    return merged, resolved_kb_images


def _result_event_identity(event: Dict[str, Any]) -> tuple[Any, ...]:
    """生成 result_event 的去重键。"""

    envelope = event.get("envelope")
    if isinstance(envelope, dict):
        envelope_id = str(envelope.get("id") or "").strip()
        if envelope_id:
            return ("envelope_id", envelope_id)

    sequence_number = _to_non_negative_int(event.get("sequence_number"))
    if sequence_number is None and isinstance(envelope, dict):
        sequence_number = _to_non_negative_int(envelope.get("sequence_number"))
    if sequence_number is not None:
        return ("sequence", str(event.get("data_type") or "").strip(), sequence_number)

    try:
        normalized_data = json.dumps(event.get("data") or {}, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        normalized_data = repr(event.get("data"))
    return (
        "payload",
        str(event.get("data_type") or "").strip(),
        str(event.get("message") or "").strip(),
        normalized_data,
    )


def _merge_turn_result_events_into_additional_kwargs(
    base_additional_kwargs: Any,
    ai_messages: List[Any],
) -> Dict[str, Any]:
    """将当前轮 AI 消息中的结构化结果归并到最终落库 additional_kwargs。"""

    merged = dict(base_additional_kwargs) if isinstance(base_additional_kwargs, dict) else {}
    collected_events: list[Dict[str, Any]] = []
    seen_keys: set[tuple[Any, ...]] = set()

    for message in ai_messages or []:
        additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
        if not isinstance(additional_kwargs, dict):
            continue
        result_events, _compat_source = _resolve_result_events_for_replay(additional_kwargs)
        for event in result_events:
            identity = _result_event_identity(event)
            if identity in seen_keys:
                continue
            seen_keys.add(identity)
            collected_events.append(dict(event))

    if not collected_events:
        return _normalize_result_additional_kwargs_for_replay(merged)

    merged["result_events"] = _sort_result_events_by_sequence(collected_events)
    return _normalize_result_additional_kwargs_for_replay(merged)


def _extract_tool_image_urls(content: str) -> list[str]:
    """从 ToolMessage 内容中提取图片 URL。

    兼容两类格式：
    1. Markdown 图片：![alt](url)
    2. fig_inter JSON 返回：{"status":"success","image_url":"..."}
    """
    import re

    urls: set[str] = set()

    for url in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content):
        if url:
            urls.add(url.strip())

    stripped = content.strip()
    if not stripped:
        return list(urls)

    json_payload = None
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            json_payload = json.loads(stripped)
        except json.JSONDecodeError:
            json_payload = None

    if isinstance(json_payload, dict):
        image_url = json_payload.get("image_url")
        status = json_payload.get("status")
        if isinstance(image_url, str) and image_url.strip():
            if status in (None, "success", "success_local"):
                urls.add(image_url.strip())
    elif '"image_url"' in content:
        regex_match = re.search(r'"image_url"\s*:\s*"([^\"]+)"', content)
        if regex_match and regex_match.group(1).strip():
            urls.add(regex_match.group(1).strip())

    return list(urls)


def save_message(
    db: Session,
    *,
    user_id: Optional[int] = None,
    thread_id: str,
    role: str = "ai",
    content_type: str = "markdown",
    content: Any = None,
    extra_data: Optional[dict] = None,
    title: Optional[str] = None,
) -> ChatMessage:
    """保存对话消息。
    
    Args:
        db: 数据库会话
        user_id: 用户 ID
        thread_id: 对话线程 ID
        role: 消息角色（human/ai）
        content_type: 内容类型（text/markdown/mixed/multimodal）
        content: 消息内容（字符串或内容块数组）
        extra_data: 元数据（映射到数据库 metadata 列）
        title: 对话标题（仅 human 消息需要）
        
    Returns:
        保存后的 ChatMessage 实例
    """
    # 如果 content 是列表/字典，先做可序列化编码再转 JSON 字符串
    if isinstance(content, (list, dict)):
        content = json.dumps(jsonable_encoder(content), ensure_ascii=False)

    # metadata 兜底编码：兼容 date/datetime/Decimal 等类型
    if extra_data is not None:
        from app.ai.protocol import normalize_skill_runtime_additional_kwargs

        extra_data = normalize_skill_runtime_additional_kwargs(extra_data)
        extra_data = _normalize_result_additional_kwargs_for_replay(extra_data)
        extra_data = jsonable_encoder(extra_data)
    
    # AI 消息去除首尾换行（LLM 输出常带有多余换行）
    if role == "ai" and isinstance(content, str):
        content = content.strip('\n')
    
    message = ChatMessage(
        user_id=user_id,
        thread_id=thread_id,
        role=role,
        content_type=content_type,
        content=content,
        extra_data=extra_data,
        create_time=datetime.now(),
        title=title,
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    logger.info("对话消息已保存: id=%d, thread_id=%s, role=%s", message.id, thread_id, role)
    return message


def get_messages_by_thread(
    db: Session,
    thread_id: str,
    limit: int = 100,
    exclude_intermediate: bool = True,
) -> List[ChatMessage]:
    """根据线程 ID 获取对话历史。
    
    Args:
        db: 数据库会话
        thread_id: 对话线程 ID
        limit: 最大返回条数
        exclude_intermediate: 是否排除中间消息（interrupt 场景的临时 AI 回复）
        
    Returns:
        ChatMessage 列表，按创建时间升序
    """
    from sqlalchemy import or_, and_, text
    from sqlalchemy.sql import func
    
    query = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id)
    
    # 排除中间消息：只排除 metadata->>'is_intermediate' = 'true' 的记录
    # 保留：metadata 为 NULL、metadata 为空对象、或 is_intermediate 不是 'true'
    if exclude_intermediate:
        # 使用 COALESCE 处理 NULL 值：如果 is_intermediate 为 NULL 则视为 'false'
        is_intermediate_value = func.coalesce(
            ChatMessage.extra_data.op("->>")("is_intermediate"),
            "false"
        )
        query = query.filter(
            ~is_intermediate_value.in_(["true", "True"])
        )
    
    return (
        query
        .order_by(ChatMessage.create_time.asc())
        .limit(limit)
        .all()
    )


def get_threads_by_user(
    db: Session,
    user_id: int,
    limit: int = 50,
) -> List[dict]:
    """获取用户的对话列表。
    
    使用窗口函数一次查询获取所有线程及其第一条消息，
    避免 N+1 查询问题。
    
    Args:
        db: 数据库会话
        user_id: 用户 ID
        limit: 最大返回条数
        
    Returns:
        对话列表，包含 thread_id 和 title
    """
    from sqlalchemy import and_, literal_column
    from sqlalchemy.orm import aliased
    
    # 子查询：获取每个 thread 的第一条消息 ID
    first_msg_subq = (
        db.query(
            ChatMessage.thread_id,
            func.min(ChatMessage.id).label("first_msg_id"),
        )
        .filter(ChatMessage.user_id == user_id)
        .group_by(ChatMessage.thread_id)
        .subquery()
    )
    
    # 子查询：获取每个 thread 的时间范围
    thread_times_subq = (
        db.query(
            ChatMessage.thread_id,
            func.min(ChatMessage.create_time).label("first_time"),
            func.max(ChatMessage.create_time).label("last_time"),
        )
        .filter(ChatMessage.user_id == user_id)
        .group_by(ChatMessage.thread_id)
        .subquery()
    )
    
    # 主查询：JOIN 获取第一条消息的 title 和 content
    results = (
        db.query(
            thread_times_subq.c.thread_id,
            thread_times_subq.c.first_time,
            thread_times_subq.c.last_time,
            ChatMessage.title,
            ChatMessage.content,
        )
        .join(
            first_msg_subq,
            first_msg_subq.c.thread_id == thread_times_subq.c.thread_id,
        )
        .join(
            ChatMessage,
            ChatMessage.id == first_msg_subq.c.first_msg_id,
        )
        .order_by(thread_times_subq.c.last_time.desc())
        .limit(limit)
        .all()
    )
    
    # 构建结果
    return [
        {
            "thread_id": r.thread_id,
            "title": r.title if r.title else (str(r.content)[:50] if r.content else "新对话"),
            "created_at": r.first_time.isoformat() if r.first_time else None,
            "updated_at": r.last_time.isoformat() if r.last_time else None,
        }
        for r in results
    ]


def get_latest_thread_by_user(db: Session, user_id: int) -> Optional[dict]:
    """获取用户最近更新的对话。

    复用 get_threads_by_user 的排序语义，保证标题与时间字段一致。

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        最近会话信息，无历史时返回 None
    """

    threads = get_threads_by_user(db, user_id=user_id, limit=1)
    if not threads:
        return None
    return threads[0]


def update_thread_title(
    db: Session,
    thread_id: str,
    title: str,
    user_id: Optional[int] = None,
) -> bool:
    """更新对话标题（更新第一条消息的 title 字段）。
    
    Args:
        db: 数据库会话
        thread_id: 对话线程 ID
        title: 新标题
        user_id: 用户 ID（用于权限校验）
        
    Returns:
        是否更新成功
    """
    query = (
        db.query(ChatMessage)
        .filter(ChatMessage.thread_id == thread_id)
    )
    if user_id is not None:
        query = query.filter(ChatMessage.user_id == user_id)
    
    first_msg = query.order_by(ChatMessage.create_time.asc()).first()
    
    if first_msg:
        first_msg.title = title
        db.commit()
        logger.info("更新对话标题: thread_id=%s, title=%s", thread_id, title)
        return True
    return False


def delete_thread(db: Session, thread_id: str, user_id: Optional[int] = None) -> int:
    """删除对话线程（删除所有相关消息）。
    
    Args:
        db: 数据库会话
        thread_id: 对话线程 ID
        user_id: 用户 ID（可选，用于权限校验）
        
    Returns:
        删除的消息数量
    """
    query = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id)
    if user_id is not None:
        query = query.filter(ChatMessage.user_id == user_id)
    
    count = query.delete()
    db.commit()
    logger.info("已删除对话线程: thread_id=%s, count=%d", thread_id, count)
    return count


def delete_threads_batch(
    db: Session,
    thread_ids: List[str],
    user_id: int
) -> dict:
    """批量删除对话线程及其资产。
    
    Args:
        db: 数据库会话
        thread_ids: 要删除的对话线程 ID 列表
        user_id: 用户 ID（用于权限校验，只能删除自己的对话）
        
    Returns:
        删除统计: {"total_messages": N, "total_assets": M, "total_minio": K, "threads_deleted": L}
    """
    stats = {
        "total_messages": 0,
        "total_assets": 0,
        "total_minio": 0,
        "threads_deleted": 0
    }
    
    for thread_id in thread_ids:
        result = delete_thread_with_assets(db, thread_id, user_id)
        if result["messages"] > 0:
            stats["total_messages"] += result["messages"]
            stats["total_assets"] += result["assets"]
            stats["total_minio"] += result["minio_deleted"]
            stats["threads_deleted"] += 1
    
    logger.info(
        "批量删除完成: user_id=%d, requested=%d, deleted=%d",
        user_id, len(thread_ids), stats["threads_deleted"]
    )
    return stats


def delete_thread_with_assets(db: Session, thread_id: str, user_id: Optional[int] = None) -> dict:
    """删除对话线程及其所有资产（MinIO 文件 + 数据库记录）。
    
    Args:
        db: 数据库会话
        thread_id: 对话线程 ID
        user_id: 用户 ID（可选，用于权限校验）
        
    Returns:
        删除统计: {"messages": N, "assets": M, "minio_deleted": K}
    """
    from app.services.asset_service import get_asset_service
    from app.core import config as ai_config
    
    stats = {"messages": 0, "assets": 0, "minio_deleted": 0}
    
    # 1. 获取该对话的所有资产
    assets = chat_assets_repository.get_assets_by_chat_id(db, thread_id)
    
    # 如果指定了 user_id，过滤只属于该用户的资产
    if user_id is not None:
        assets = [a for a in assets if a.user_id == user_id]
    
    # 2. 删除 MinIO 文件
    if assets:
        try:
            asset_service = get_asset_service()
            for asset in assets:
                try:
                    asset_service.client.remove_object(
                        bucket_name=ai_config.MINIO_BUCKET_ASSETS,
                        object_name=asset.object_key,
                    )
                    stats["minio_deleted"] += 1
                except Exception as e:
                    logger.warning("删除 MinIO 文件失败 (%s): %s", asset.object_key, e)
        except Exception as e:
            logger.warning("获取 AssetService 失败: %s", e)
        
        # 3. 删除数据库中的资产记录
        asset_query = db.query(ChatAsset).filter(ChatAsset.chat_id == thread_id)
        if user_id is not None:
            asset_query = asset_query.filter(ChatAsset.user_id == user_id)
        stats["assets"] = asset_query.delete()
    
    # 4. 删除对话消息
    stats["messages"] = delete_thread(db, thread_id, user_id)
    
    logger.info(
        "已删除对话及资产: thread_id=%s, messages=%d, assets=%d, minio=%d",
        thread_id, stats["messages"], stats["assets"], stats["minio_deleted"]
    )
    return stats


def save_conversation_from_messages(
    db: Session,
    user_id: Optional[int],
    thread_id: str,
    messages: list,
):
    """从 LangGraph 消息列表保存对话到 PostgreSQL。
    
    只保存最后一轮对话：
    - 最后一条 human 消息
    - **最后一条** ai 消息（不合并多条，保持与实时流一致）
    
    如果最后一条 AI 消息中没有引用工具返回的图片，但 Tool 消息中有图片，
    则将图片补充到 AI 回复末尾。
    
    Args:
        db: 数据库会话
        user_id: 用户 ID
        thread_id: 对话线程 ID
        messages: LangGraph 消息列表（BaseMessage 对象列表）
    """
    import re
    
    if not messages or not thread_id:
        return
    
    # 1. 从后往前查找最后一条 human 消息和最后一条 ai 消息
    last_human = None
    last_ai = None
    turn_ai_messages: list[Any] = []
    tool_kb_images = {}    # 知识库图片映射 {索引: URL}

    for msg in reversed(messages):
        msg_type = getattr(msg, "type", None)
        msg_name = getattr(msg, "name", None)

        logger.debug("遍历消息: type=%s, name=%s, content_preview=%s",
                    msg_type, msg_name, str(getattr(msg, "content", ""))[:50])

        if msg_type == "human" and last_human is None:
            last_human = msg
            break
        elif msg_type == "ai":
            turn_ai_messages.append(msg)
            if last_ai is None:
                last_ai = msg
        elif msg_type == "tool":
            content = str(getattr(msg, "content", ""))
            logger.info("Tool消息内容(前500字): %s", content[:500])
            kb_images_match = re.search(r'<!--KB_IMAGES:(\{.*?\})-->', content)
            if kb_images_match:
                try:
                    import json
                    new_images = json.loads(kb_images_match.group(1))
                    tool_kb_images.update(new_images)
                    logger.info("提取到 kb_images 映射: %s (累计: %s)", new_images, tool_kb_images)
                except json.JSONDecodeError:
                    logger.warning("解析 kb_images 失败: %s", kb_images_match.group(1))
            else:
                logger.info("Tool消息中未找到 KB_IMAGES 标记")

    turn_ai_messages.reverse()

    merged_additional_kwargs = _merge_turn_result_events_into_additional_kwargs(
        getattr(last_ai, "additional_kwargs", None) if last_ai else None,
        turn_ai_messages,
    )
    merged_additional_kwargs, kb_images = _merge_turn_kb_images_into_additional_kwargs(
        merged_additional_kwargs,
        turn_ai_messages,
        tool_kb_images,
    )
    result_events, _compat_source = _resolve_result_events_for_replay(merged_additional_kwargs)

    human_content = getattr(last_human, "content", "") if last_human else ""
    ai_content = normalize_message_content(getattr(last_ai, "content", "")) if last_ai else ""

    if last_ai:
        additional_kwargs = merged_additional_kwargs
        thinking = (
            additional_kwargs.get("reasoning_content") or
            additional_kwargs.get("thinking_content") or
            ""
        )
        if thinking and "<think>" not in ai_content:
            ai_content = f"<think>\n{thinking}\n</think>\n\n{ai_content}"
            logger.info("已将 thinking 内容包装到 AI 回复中: %d 字符", len(thinking))

    display_blocks = compile_message_display_blocks(
        final_text=ai_content,
        kb_images=kb_images,
        result_events=result_events,
    )
    has_structured_display = bool(kb_images) or len(result_events) > 0

    if not human_content and not display_blocks and not ai_content:
        return

    extra_data = None
    if last_ai:
        extra_data = merged_additional_kwargs or None
        save_message(
            db,
            user_id=user_id,
            thread_id=thread_id,
            role="ai",
            content_type="multimodal" if has_structured_display else "markdown",
            content=display_blocks if has_structured_display else ai_content,
            extra_data=extra_data,
        )

    saved_extra_keys = list(extra_data.keys()) if extra_data else []
    logger.info(
        "[SYNC-TRACE] 数据库保存完成: thread_id=%s, ai_len=%d, ai_hash=%s, extra_data_keys=%s, display_block_count=%d",
        thread_id, len(str(ai_content)), _content_hash(str(ai_content)),
        saved_extra_keys, len(display_blocks)
    )


def save_feedback(
    db: Session,
    user_id: int,
    message_id: int,
    score: int,
    reason: Optional[str] = None,
) -> dict:
    """保存或更新消息反馈。
    
    Args:
        db: 数据库会话
        user_id: 用户 ID
        message_id: 消息 ID
        score: 分数 (1: Like, -1: Dislike, 0: Cancel)
        reason: 原因（可选）
        
    Returns:
        反馈记录字典
    """
    from sqlalchemy import text
    
    # 使用 ON CONFLICT 更新或插入
    # 注意：PostgreSQL 语法
    sql = text("""
        INSERT INTO t_chat_feedback (user_id, message_id, score, reason, updated_at)
        VALUES (:user_id, :message_id, :score, :reason, NOW())
        ON CONFLICT (user_id, message_id) 
        DO UPDATE SET score = EXCLUDED.score, reason = EXCLUDED.reason, updated_at = NOW()
        RETURNING id
    """)
    
    try:
        result = db.execute(sql, {
            "user_id": user_id,
            "message_id": message_id,
            "score": score,
            "reason": reason
        })
        db.commit()
        feedback_id = result.scalar()
        logger.info("用户 %d 对消息 %d 反馈: %d", user_id, message_id, score)
        return {
            "id": feedback_id,
            "user_id": user_id,
            "message_id": message_id,
            "score": score,
            "reason": reason
        }
    except Exception as e:
        db.rollback()
        logger.error("保存反馈失败: %s", e)
        raise e


def get_feedback_scores_batch(
    db: Session, user_id: int, message_ids: list[int]
) -> dict[int, int]:
    """批量查询用户对多条消息的反馈分数。
    
    Returns:
        {message_id: score} 映射，只包含有反馈的消息
    """
    from sqlalchemy import text
    
    if not message_ids:
        return {}
    
    try:
        sql = text("""
            SELECT message_id, score 
            FROM t_chat_feedback 
            WHERE user_id = :uid AND message_id = ANY(:mids) AND score != 0
        """)
        rows = db.execute(sql, {"uid": user_id, "mids": message_ids}).fetchall()
        return {row.message_id: row.score for row in rows}
    except Exception as e:
        logger.error("批量查询反馈失败: %s", e)
        return {}
