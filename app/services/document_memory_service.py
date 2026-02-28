"""文档化永久记忆服务（中文注释）。"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ai.utils.embedding_util import get_embedding
from app.repositories import document_memory_repo


logger = logging.getLogger(__name__)

_MEMORY_TRIGGER_PATTERN = re.compile(
    r"(记住|牢记|以后都|之后都|长期|永久|偏好|习惯|请始终|一直)",
)
_DEFAULT_CHUNK_MAX_LINES = 16
_DEFAULT_CHUNK_OVERLAP_LINES = 3
_DEFAULT_MEMORY_SOURCE = "memory"
_DEFAULT_MAX_RESULTS = 6
_DEFAULT_MAX_INJECTED_CHARS = 1200
_DEFAULT_VECTOR_WEIGHT = 0.70
_DEFAULT_TEXT_WEIGHT = 0.30
_DEFAULT_MIN_SCORE = 0.05


def _normalize_text(text: str) -> str:
    """归一化文本。"""

    if not text:
        return ""
    return "\n".join(line.rstrip() for line in str(text).strip().splitlines()).strip()


def _hash_text(text: str) -> str:
    """计算文本哈希。"""

    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _build_daily_entry(
    *,
    user_text: str,
    source_thread_id: str | None,
    source_message_id: int | None,
) -> str:
    """构建日记式记忆条目。"""

    now = datetime.now()
    time_label = now.strftime("%H:%M:%S")
    lines = [f"### {time_label}", f"- 用户陈述：{user_text}"]
    if source_thread_id:
        lines.append(f"- 来源线程：{source_thread_id}")
    if source_message_id:
        lines.append(f"- 来源消息：{source_message_id}")
    return "\n".join(lines)


def _should_persist_memory(user_text: str) -> bool:
    """判断是否触发文档记忆写入。"""

    text = _normalize_text(user_text)
    if not text:
        return False
    if _MEMORY_TRIGGER_PATTERN.search(text):
        return True

    # 允许用户通过“自我事实表达”形成长期记忆候选。
    # 示例：“我是产品经理”“我住在上海”“我偏好先结论后分析”
    lightweight_facts = (
        "我是",
        "我在",
        "我住",
        "我偏好",
        "我习惯",
        "我的目标",
    )
    return any(token in text for token in lightweight_facts)


def _split_document_to_chunks(
    content_md: str,
    *,
    max_lines: int = _DEFAULT_CHUNK_MAX_LINES,
    overlap_lines: int = _DEFAULT_CHUNK_OVERLAP_LINES,
) -> list[dict[str, Any]]:
    """按行分块并生成可索引片段。"""

    lines = (content_md or "").splitlines()
    if not lines:
        return []

    chunks: list[dict[str, Any]] = []
    cursor = 0
    chunk_no = 1
    safe_max_lines = max(1, int(max_lines))
    safe_overlap = max(0, min(int(overlap_lines), safe_max_lines - 1))

    while cursor < len(lines):
        end = min(len(lines), cursor + safe_max_lines)
        segment = lines[cursor:end]
        chunk_text = "\n".join(segment).strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_no": chunk_no,
                    "start_line": cursor + 1,
                    "end_line": end,
                    "chunk_text": chunk_text,
                    "chunk_hash": _hash_text(chunk_text),
                    "source": _DEFAULT_MEMORY_SOURCE,
                    "embedding": None,
                    "embedding_model": None,
                    "embedding_status": document_memory_repo.EMBEDDING_STATUS_PENDING,
                    "embedding_retry_count": 0,
                    "embedding_error": None,
                    "embedding_updated_time": None,
                }
            )
            chunk_no += 1

        if end >= len(lines):
            break
        cursor = max(end - safe_overlap, cursor + 1)

    return chunks


def _merge_weights(vector_weight: float, text_weight: float) -> tuple[float, float]:
    """归一化向量与文本权重。"""

    v = max(0.0, float(vector_weight))
    t = max(0.0, float(text_weight))
    total = v + t
    if total <= 0:
        return _DEFAULT_VECTOR_WEIGHT, _DEFAULT_TEXT_WEIGHT
    return v / total, t / total


def _build_citation(result: dict[str, Any], *, user_id: int) -> str:
    """构建引用标识。"""

    doc_kind = str(result.get("doc_kind") or "memory")
    doc_key = str(result.get("doc_key") or "unknown")
    start_line = int(result.get("start_line") or 1)
    end_line = int(result.get("end_line") or start_line)
    return f"memory://user/{user_id}/{doc_kind}/{doc_key}#L{start_line}-L{end_line}"


def _clamp_context_lines(text: str, limit: int = 8) -> str:
    """裁剪片段最大行数，降低注入噪声。"""

    lines = (text or "").splitlines()
    if len(lines) <= limit:
        return "\n".join(lines)
    kept = lines[:limit]
    kept.append("...(已截断)")
    return "\n".join(kept)


def memory_search(
    db: Session,
    *,
    user_id: int,
    query_text: str,
    max_results: int = _DEFAULT_MAX_RESULTS,
    min_score: float = _DEFAULT_MIN_SCORE,
    vector_weight: float = _DEFAULT_VECTOR_WEIGHT,
    text_weight: float = _DEFAULT_TEXT_WEIGHT,
) -> list[dict[str, Any]]:
    """检索记忆分块并返回引用。"""

    if not user_id:
        return []

    safe_limit = max(1, int(max_results))
    vector_w, text_w = _merge_weights(vector_weight, text_weight)
    query_embedding: list[float] | None = None
    if vector_w > 0:
        try:
            query_embedding = get_embedding(query_text)
        except Exception as embedding_error:  # pragma: no cover - 外部依赖异常
            logger.warning(
                "生成检索向量失败，降级为纯文本检索: user_id=%s, error=%s",
                user_id,
                embedding_error,
            )
    raw_results = document_memory_repo.search_chunks(
        db,
        user_id=user_id,
        query_text=query_text,
        limit=safe_limit,
        source=_DEFAULT_MEMORY_SOURCE,
        query_embedding=query_embedding,
        text_weight=text_w,
        vector_weight=vector_w if query_embedding is not None else 0.0,
    )

    output: list[dict[str, Any]] = []
    for row in raw_results:
        text_score = float(row.get("text_score") or 0.0)
        vector_score = float(row.get("vector_score") or 0.0)
        final_score = float(row.get("final_score") or (vector_w * vector_score + text_w * text_score))
        if final_score < float(min_score):
            continue
        chunk_text = str(row.get("chunk_text") or "")
        output.append(
            {
                "doc_id": int(row.get("doc_id")),
                "doc_kind": str(row.get("doc_kind") or ""),
                "doc_key": str(row.get("doc_key") or ""),
                "start_line": int(row.get("start_line") or 1),
                "end_line": int(row.get("end_line") or 1),
                "chunk_text": chunk_text,
                "text_score": text_score,
                "vector_score": vector_score,
                "score": final_score,
                "citation": _build_citation(row, user_id=user_id),
            }
        )
    return output


def memory_get(
    db: Session,
    *,
    user_id: int,
    doc_id: int,
    from_line: int = 1,
    lines: int = 40,
) -> dict[str, Any] | None:
    """按文档局部读取记忆。"""

    if not user_id or not doc_id:
        return None
    return document_memory_repo.get_document_excerpt(
        db,
        user_id=user_id,
        doc_id=doc_id,
        from_line=from_line,
        lines=lines,
    )


def recall(
    db: Session,
    *,
    user_id: int,
    query_text: str,
    max_results: int = _DEFAULT_MAX_RESULTS,
    max_injected_chars: int = _DEFAULT_MAX_INJECTED_CHARS,
    min_score: float = _DEFAULT_MIN_SCORE,
    vector_weight: float = _DEFAULT_VECTOR_WEIGHT,
    text_weight: float = _DEFAULT_TEXT_WEIGHT,
) -> str:
    """构建可注入模型的文档记忆上下文。"""

    results = memory_search(
        db,
        user_id=user_id,
        query_text=query_text,
        max_results=max_results,
        min_score=min_score,
        vector_weight=vector_weight,
        text_weight=text_weight,
    )
    if not results:
        return ""

    header = "以下是与当前请求相关的用户长期记忆片段（仅在不与本轮指令冲突时参考）："
    lines = [header]
    budget = max(80, int(max_injected_chars))
    current_len = len(header)

    for result in results:
        excerpt = memory_get(
            db,
            user_id=user_id,
            doc_id=int(result["doc_id"]),
            from_line=int(result["start_line"]),
            lines=max(1, int(result["end_line"]) - int(result["start_line"]) + 1),
        )
        snippet = excerpt.get("text") if excerpt else result.get("chunk_text", "")
        snippet = _clamp_context_lines(str(snippet or ""))
        line = f"- {snippet}\n  引用: {result['citation']}"
        next_len = current_len + len(line) + 1
        if next_len > budget:
            break
        lines.append(line)
        current_len = next_len

    return "\n".join(lines) if len(lines) > 1 else ""


def flush(
    db: Session,
    *,
    user_id: int,
    user_text: str,
    source_thread_id: str | None = None,
    source_message_id: int | None = None,
) -> int:
    """将用户输入沉淀到文档记忆（日记层）。"""

    if not user_id:
        return 0

    text = _normalize_text(user_text)
    if not _should_persist_memory(text):
        return 0

    now = datetime.now()
    doc_kind = "daily"
    doc_key = now.strftime("%Y-%m-%d")
    doc_title = f"记忆日记 {doc_key}"

    try:
        existing = document_memory_repo.get_active_document(
            db,
            user_id=user_id,
            doc_kind=doc_kind,
            doc_key=doc_key,
        )
        entry = _build_daily_entry(
            user_text=text,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )

        if existing and existing.content_md:
            merged = f"{existing.content_md.rstrip()}\n\n{entry}".strip()
        else:
            merged = f"# {doc_title}\n\n{entry}".strip()

        content_hash = _hash_text(merged)
        document = document_memory_repo.upsert_document(
            db,
            user_id=user_id,
            doc_kind=doc_kind,
            doc_key=doc_key,
            title=doc_title,
            content_md=merged,
            summary_md=None,
            source=_DEFAULT_MEMORY_SOURCE,
            scope="private",
            scope_ref=source_thread_id,
            content_hash=content_hash,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )

        chunks = _split_document_to_chunks(merged)
        document_memory_repo.replace_document_chunks(
            db,
            user_id=user_id,
            doc_id=document.id,
            chunks=chunks,
            source=_DEFAULT_MEMORY_SOURCE,
        )
        db.commit()
        return 1
    except Exception:
        rollback = getattr(db, "rollback", None)
        if callable(rollback):
            rollback()
        logger.exception("文档记忆 flush 失败: user_id=%s", user_id)
        return 0
