"""对话消息数据访问层（中文注释）。

提供对话消息的 CRUD 操作。
基于单表 t_chat_message 设计，title 存储在第一条 human 消息中。
"""
import json
import logging
from typing import Optional, List, Any
from datetime import datetime
from sqlalchemy import func
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.chat_asset import ChatAsset
from app.repositories import chat_assets_repository
from app.core.utils import content_hash as _content_hash


logger = logging.getLogger(__name__)


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
    tool_images = []  # 收集该轮工具返回的图片
    kb_images = {}    # 知识库图片映射 {索引: URL}
    
    for msg in reversed(messages):
        msg_type = getattr(msg, "type", None)
        msg_name = getattr(msg, "name", None)
        
        # 调试日志
        logger.debug("遍历消息: type=%s, name=%s, content_preview=%s", 
                    msg_type, msg_name, str(getattr(msg, "content", ""))[:50])
        
        if msg_type == "human" and last_human is None:
            last_human = msg
            break  # 找到 human 后停止（一轮对话结束）
        elif msg_type == "ai" and last_ai is None:
            last_ai = msg  # 只取最后一条 AI 消息
        elif msg_type == "tool":
            # 提取工具返回中的图片链接（用于图表图片补充）
            content = str(getattr(msg, "content", ""))
            img_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
            for url in re.findall(img_pattern, content):
                tool_images.append(url)
            
            # 提取知识库图片映射（用于占位符替换）
            logger.info("Tool消息内容(前500字): %s", content[:500])
            kb_images_match = re.search(r'<!--KB_IMAGES:(\{.*?\})-->', content)
            if kb_images_match:
                try:
                    import json
                    new_images = json.loads(kb_images_match.group(1))
                    kb_images.update(new_images)  # 合并而不是覆盖
                    logger.info("提取到 kb_images 映射: %s (累计: %s)", new_images, kb_images)
                except json.JSONDecodeError:
                    logger.warning("解析 kb_images 失败: %s", kb_images_match.group(1))
            else:
                logger.info("Tool消息中未找到 KB_IMAGES 标记")
    
    # 提取内容
    human_content = getattr(last_human, "content", "") if last_human else ""
    ai_content = str(getattr(last_ai, "content", "")) if last_ai else ""
    replaced_count = 0  # 用于跟踪图片占位符替换数量
    
    # ============================================================
    # Thinking 内容处理
    # ============================================================
    # 
    # 【背景】DeepSeek/Qwen 的思考内容存储在 additional_kwargs 的
    #         reasoning_content 或 thinking_content 字段
    # 【处理】如果 ai_content 中没有 <think> 标签但有 thinking 内容，
    #         将其包装后添加到内容开头，确保历史加载时前端能正确解析
    # ============================================================
    if last_ai:
        additional_kwargs = getattr(last_ai, "additional_kwargs", {}) or {}
        thinking = (
            additional_kwargs.get("reasoning_content") or 
            additional_kwargs.get("thinking_content") or 
            ""
        )
        if thinking and "<think>" not in ai_content:
            # 将 thinking 内容包装在 <think> 标签内，添加到内容开头
            ai_content = f"<think>\n{thinking}\n</think>\n\n{ai_content}"
            logger.info("已将 thinking 内容包装到 AI 回复中: %d 字符", len(thinking))
    
    # ============================================================
    # 图片占位符替换
    # ============================================================
    # 
    # 【背景】knowledge_search 工具返回 [IMG-N] 占位符和 kb_images 映射
    # 【处理】在保存前，将 LLM 输出中的 [IMG-N] 替换为实际的 Markdown 图片
    # ============================================================
    
    if kb_images and ai_content:
        import re as re2
        # 先统计 ai_content 中有多少占位符
        placeholders_in_content = re2.findall(r'\[IMG-\d+\]', ai_content)
        logger.info("AI回复中包含 %d 个占位符: %s", len(placeholders_in_content), placeholders_in_content)
        logger.info("kb_images 映射包含 %d 个图片: %s", len(kb_images), list(kb_images.keys()))
        
        replaced_count = 0
        for idx_str, url in kb_images.items():
            placeholder = f"[IMG-{idx_str}]"
            if placeholder in ai_content:
                markdown_img = f"![参考图片]({url})"
                # 使用 replace 不限制次数，替换所有匹配项（修复多次引用同一占位符的问题）
                count_before = ai_content.count(placeholder)
                ai_content = ai_content.replace(placeholder, markdown_img)
                replaced_count += count_before
                logger.info("替换图片占位符: %s -> %s (共 %d 处)", placeholder, url, count_before)
            else:
                logger.info("占位符 %s 不在 AI 回复中", placeholder)
        
        if replaced_count > 0:
            logger.info("已替换 %d 个图片占位符", replaced_count)
        else:
            logger.warning("未替换任何占位符！")
    
    # ============================================================
    # 🖼️ 图表图片保存策略（差异化处理）
    # ============================================================
    # 
    # 【背景】fig_inter（图表生成）的图片，LLM 可能忘记引用
    # 【处理】如果 LLM 未引用，自动补充到末尾
    # ============================================================
    if tool_images and ai_content:
        missing_chart_images = []
        for url in tool_images:
            # 只补充图表工具生成的图片（/charts/ 路径）
            is_chart_image = "/charts/" in url
            is_not_in_content = url not in ai_content
            
            if is_chart_image and is_not_in_content:
                missing_chart_images.append(url)
                logger.debug("图表图片未被 LLM 引用，自动补充: %s", url)
        
        if missing_chart_images:
            ai_content += "\n\n"
            for url in missing_chart_images:
                ai_content += f"![生成的图表]({url})\n"
    
    if not human_content and not ai_content:
        return
    
    # human 消息已在 stream 开始时保存，postprocess 只负责保存 AI 消息
    # 职责划分：human -> stream开始, interrupt AI -> interrupt, final AI -> postprocess
    
    # 4. 保存 ai 消息（只保存最后一条）
    extra_data = None  # 在外部定义，确保日志可访问
    if last_ai:  # 使用 last_ai 对象判断，确保能获取 metadata
        # 提取 metadata (additional_kwargs)
        extra_data = getattr(last_ai, "additional_kwargs", None)
        save_message(
            db,
            user_id=user_id,
            thread_id=thread_id,
            role="ai",
            content_type="markdown",
            content=ai_content,
            extra_data=extra_data,  # 保存 metadata
        )
    
    # 详细同步追踪日志
    saved_extra_keys = list(extra_data.keys()) if extra_data else []
    logger.info(
        "[SYNC-TRACE] 数据库保存完成: thread_id=%s, ai_len=%d, ai_hash=%s, extra_data_keys=%s, kb_images_replaced=%d",
        thread_id, len(str(ai_content)), _content_hash(str(ai_content)),
        saved_extra_keys, replaced_count
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


def get_feedback_by_message(db: Session, message_id: int, user_id: int) -> Optional[dict]:
    """获取指定消息的反馈。"""
    from sqlalchemy import text
    try:
        sql = text("SELECT * FROM t_chat_feedback WHERE message_id = :mid AND user_id = :uid")
        row = db.execute(sql, {"mid": message_id, "uid": user_id}).mappings().first()
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error("获取反馈失败: %s", e)
        return None


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


