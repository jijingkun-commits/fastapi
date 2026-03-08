"""文档化永久记忆服务（中文注释）。"""

from __future__ import annotations

import json
import hashlib
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ai.utils.embedding_util import get_embedding
from app.repositories import document_memory_repo, user_memory_repo
from app.services.memory_slot_governance_service import MemorySlotGovernanceService


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
_DEFAULT_PREFERENCE_DOC_KIND = "preference"
_DEFAULT_PREFERENCE_SCOPE = "global"
_DECISION_ACCEPT = "accept"
_DECISION_REJECT = "reject"
_VALID_MEMORY_KINDS = {
    "user_identity",
    "response_preference",
    "assistant_persona",
    "profile_fact",
}
_VALID_OPERATIONS = {"upsert", "archive"}
_PREFERENCE_BOOTSTRAP_TEMPLATE_CONFIG_KEY = "memory.user_preference_bootstrap_template"
_PREFERENCE_BOOTSTRAP_TEMPLATE_DEFAULT = {"assistant.persona": "小嘉"}
_PREFERENCE_BOOTSTRAP_SOURCE_THREAD_ID = "system.user_bootstrap"
_SOURCE_METADATA_PATTERNS = (
    re.compile(r"^- (来源线程|来源消息)："),
    re.compile(r"^- source_(thread_id|message_id):", re.IGNORECASE),
    re.compile(r"^# 记忆日记 \d{4}-\d{2}-\d{2}$"),
    re.compile(r"^### \d{2}:\d{2}:\d{2}$"),
)


def _normalize_text(text: str) -> str:
    """归一化文本。"""

    if not text:
        return ""
    return "\n".join(line.rstrip() for line in str(text).strip().splitlines()).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


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


def _build_daily_summary(user_text: str, *, max_chars: int = 180) -> str:
    """构建 daily 文档摘要，避免后台列表为空。"""

    plain = " ".join(str(user_text or "").split()).strip()
    if not plain:
        return "用户记忆片段"
    if len(plain) <= max_chars:
        return plain
    return f"{plain[:max_chars].rstrip()}..."


def _build_slot_canonical_content(
    *,
    slot_key: str,
    canonical_text: str,
    memory_kind: str | None,
    normalized_value: str | None,
    evidence_span: str | None,
    decision_id: str | None,
    confidence: float | None,
    reason_code: str | None,
    memories_count: int | None,
    rejected_items_count: int | None,
    item_errors: list[dict[str, Any]] | None,
    operation: str,
    event_time: datetime | None,
    source_thread_id: str | None,
    source_message_id: int | None,
) -> str:
    """构建槽位记忆文档正文。"""

    normalized_slot_key = str(slot_key or "").strip() or "unknown.slot"
    lines = [
        f"# 槽位记忆 {normalized_slot_key}",
        "",
        f"- slot_key: {normalized_slot_key}",
        f"- canonical_text: {canonical_text}",
        f"- operation: {str(operation or 'upsert').strip() or 'upsert'}",
    ]
    if memory_kind:
        lines.append(f"- memory_kind: {memory_kind}")
    if normalized_value:
        lines.append(f"- normalized_value: {normalized_value}")
    if evidence_span:
        lines.append(f"- evidence_span: {evidence_span}")
    if decision_id:
        lines.append(f"- decision_id: {decision_id}")
    if reason_code:
        lines.append(f"- reason_code: {reason_code}")
    if confidence is not None:
        lines.append(f"- confidence: {float(confidence):.4f}")
    if memories_count is not None:
        lines.append(f"- memories_count: {int(memories_count)}")
    if rejected_items_count is not None:
        lines.append(f"- rejected_items_count: {int(rejected_items_count)}")
    if item_errors is not None:
        lines.append(f"- item_errors_json: {json.dumps(item_errors, ensure_ascii=False)}")
    if event_time:
        lines.append(f"- event_time: {event_time.isoformat()}")
    if source_thread_id:
        lines.append(f"- source_thread_id: {source_thread_id}")
    if source_message_id:
        lines.append(f"- source_message_id: {source_message_id}")
    return "\n".join(lines).strip()


def _resolve_canonical_doc_key(
    *,
    doc_kind: str,
    doc_key: str | None,
    slot_key: str | None,
    event_time: datetime,
) -> str:
    """解析 canonical flush 的文档键。"""

    normalized_doc_key = str(doc_key or "").strip()
    if normalized_doc_key:
        return normalized_doc_key
    if doc_kind == "daily":
        return event_time.strftime("%Y-%m-%d")
    return str(slot_key or "").strip()


def _is_source_metadata_line(line: str) -> bool:
    stripped = str(line or "").strip()
    if not stripped:
        return False
    return any(pattern.search(stripped) for pattern in _SOURCE_METADATA_PATTERNS)


def _strip_source_metadata_lines(text: str) -> str:
    """移除来源元数据行，降低 UUID/消息号对检索与注入的噪声。"""

    lines = (text or "").splitlines()
    cleaned = [line for line in lines if not _is_source_metadata_line(line)]
    while cleaned and not cleaned[0].strip():
        cleaned.pop(0)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    return "\n".join(cleaned).strip()


def _normalize_bootstrap_template(raw_template: Any) -> dict[str, str]:
    """规范化偏好模板，过滤非法值。"""

    if not isinstance(raw_template, dict):
        return {}

    normalized: dict[str, str] = {}
    for raw_key, raw_value in raw_template.items():
        memory_key = str(raw_key or "").strip()
        memory_value = str(raw_value or "").strip()
        if not memory_key or not memory_value:
            continue
        normalized[memory_key] = memory_value[:200]
    return normalized


def _load_preference_bootstrap_template() -> dict[str, str]:
    """读取偏好初始化模板。"""

    fallback = dict(_PREFERENCE_BOOTSTRAP_TEMPLATE_DEFAULT)
    try:
        from app.services.config_resolver import ConfigResolver

        raw_template = ConfigResolver.get_json_dict(
            _PREFERENCE_BOOTSTRAP_TEMPLATE_CONFIG_KEY,
            fallback,
        )
    except Exception as config_error:
        logger.warning("读取偏好初始化模板失败，使用默认模板: error=%s", config_error)
        return fallback

    normalized = _normalize_bootstrap_template(raw_template)
    return normalized if normalized else fallback


def _build_preference_document_content(
    *,
    memory_key: str,
    memory_value: str,
    scope: str,
    source_thread_id: str | None,
    source_message_id: int | None,
    updated_time: datetime | None,
) -> str:
    """构建偏好记忆文档正文。"""

    lines = [
        f"# 用户偏好 {memory_key}",
        "",
        f"- key: {memory_key}",
        f"- value: {memory_value}",
        f"- scope: {scope}",
    ]
    if source_thread_id:
        lines.append(f"- source_thread_id: {source_thread_id}")
    if source_message_id:
        lines.append(f"- source_message_id: {source_message_id}")
    if updated_time:
        lines.append(f"- updated_at: {updated_time.isoformat()}")
    return "\n".join(lines).strip()


def _upsert_preference_document(
    db: Session,
    *,
    user_id: int,
    memory_key: str,
    memory_value: str,
    scope: str,
    source_thread_id: str | None,
    source_message_id: int | None,
    updated_time: datetime | None,
) -> None:
    """写入单条 preference 文档。"""

    doc_key = f"{scope}:{memory_key}"
    content_md = _build_preference_document_content(
        memory_key=memory_key,
        memory_value=memory_value,
        scope=scope,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        updated_time=updated_time,
    )
    content_hash = _hash_text(content_md)

    document = document_memory_repo.upsert_document(
        db,
        user_id=user_id,
        doc_kind=_DEFAULT_PREFERENCE_DOC_KIND,
        doc_key=doc_key,
        title=f"偏好记忆 {memory_key}",
        content_md=content_md,
        summary_md=memory_value[:200],
        source=_DEFAULT_MEMORY_SOURCE,
        scope="private",
        scope_ref=scope,
        content_hash=content_hash,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
    )

    chunks = _split_document_to_chunks(content_md)
    document_memory_repo.replace_document_chunks(
        db,
        user_id=user_id,
        doc_id=document.id,
        chunks=chunks,
        source=_DEFAULT_MEMORY_SOURCE,
    )


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
        chunk_text = _strip_source_metadata_lines("\n".join(segment))
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


def _build_preference_context(
    db: Session,
    *,
    user_id: int,
    max_items: int = 6,
    max_chars: int = 360,
) -> str:
    """构建稳定偏好上下文（与 query 无关，始终注入）。"""

    if not user_id:
        return ""

    documents, _ = document_memory_repo.list_documents(
        db,
        user_id=user_id,
        doc_kind=_DEFAULT_PREFERENCE_DOC_KIND,
        status="active",
        source=_DEFAULT_MEMORY_SOURCE,
        page=1,
        page_size=max(1, int(max_items)),
    )
    if not documents:
        return ""

    header = "以下是用户稳定偏好（跨会话生效，若与本轮明确指令冲突则以本轮为准）："
    lines = [header]
    budget = max(120, int(max_chars))
    current_len = len(header)
    has_assistant_persona = False

    for item in documents:
        summary = str(item.get("summary_md") or "").strip()
        doc_key = str(item.get("doc_key") or "").strip()
        if not summary or not doc_key:
            continue

        display_key = doc_key.split(":", 1)[-1] if ":" in doc_key else doc_key
        if display_key == "assistant.persona":
            has_assistant_persona = True
        citation = f"memory://user/{user_id}/{_DEFAULT_PREFERENCE_DOC_KIND}/{doc_key}#L1-L5"
        line = f"- {display_key}: {summary}\n  引用: {citation}"
        next_len = current_len + len(line) + 1
        if next_len > budget:
            break
        lines.append(line)
        current_len = next_len

    if has_assistant_persona:
        guidance_lines = (
            "执行要求：当用户未另行指定时，按 AI 人设进行自称。",
            "说明要求：该 AI 人设已写入跨会话记忆；除非用户要求删除，不要回答“无法跨会话记住该称呼”。",
        )
        for guidance in guidance_lines:
            next_len = current_len + len(guidance) + 1
            if next_len > budget:
                break
            lines.append(guidance)
            current_len = next_len

    return "\n".join(lines) if len(lines) > 1 else ""


def _build_retrieval_context(
    db: Session,
    *,
    user_id: int,
    query_text: str,
    max_results: int,
    max_injected_chars: int,
    min_score: float,
    vector_weight: float,
    text_weight: float,
) -> str:
    """构建与 query 相关的检索记忆上下文。"""

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
        snippet = _strip_source_metadata_lines(str(result.get("chunk_text") or ""))
        snippet = _clamp_context_lines(snippet)
        citation = str(result.get("citation") or "").strip()
        if not snippet or not citation:
            continue

        line = f"- {snippet}\n  引用: {citation}"
        next_len = current_len + len(line) + 1
        if next_len > budget:
            break
        lines.append(line)
        current_len = next_len

    return "\n".join(lines) if len(lines) > 1 else ""


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

    total_budget = max(120, int(max_injected_chars))
    preference_budget = max(120, min(360, int(total_budget * 0.4)))
    retrieval_budget = max(80, total_budget - preference_budget)

    preference_context = _build_preference_context(
        db,
        user_id=user_id,
        max_items=max_results,
        max_chars=preference_budget,
    )
    retrieval_context = _build_retrieval_context(
        db,
        user_id=user_id,
        query_text=query_text,
        max_results=max_results,
        max_injected_chars=retrieval_budget,
        min_score=min_score,
        vector_weight=vector_weight,
        text_weight=text_weight,
    )

    if preference_context and retrieval_context:
        return f"{preference_context}\n\n{retrieval_context}"
    return preference_context or retrieval_context


def bootstrap_preference_documents(
    db: Session,
    *,
    user_id: int,
    template: dict[str, Any] | None = None,
) -> int:
    """新用户初始化 preference 文档记忆。"""

    if not user_id:
        return 0

    template_payload = (
        _load_preference_bootstrap_template()
        if template is None
        else _normalize_bootstrap_template(template)
    )
    if not template_payload:
        return 0

    for memory_key, memory_value in template_payload.items():
        _upsert_preference_document(
            db,
            user_id=user_id,
            memory_key=memory_key,
            memory_value=memory_value,
            scope=_DEFAULT_PREFERENCE_SCOPE,
            source_thread_id=_PREFERENCE_BOOTSTRAP_SOURCE_THREAD_ID,
            source_message_id=None,
            updated_time=None,
        )

    db.commit()
    return len(template_payload)


def upsert_preference_documents_from_input(
    db: Session,
    *,
    user_id: int,
    user_text: str,
    source_thread_id: str | None = None,
    source_message_id: int | None = None,
    scope: str = _DEFAULT_PREFERENCE_SCOPE,
) -> int:
    """从用户输入提取显式偏好并写入 preference 文档。"""

    if not user_id:
        return 0

    normalized_text = _normalize_text(user_text)
    if not normalized_text:
        return 0

    try:
        from app.services.user_preference_memory_service import extract_explicit_preference_candidates
    except Exception as import_error:
        logger.warning("加载偏好候选提取器失败，跳过 preference 文档写入: error=%s", import_error)
        return 0

    candidates = extract_explicit_preference_candidates(normalized_text)
    if not candidates:
        return 0

    persisted = 0
    try:
        for candidate in candidates:
            memory_key = str(getattr(candidate, "memory_key", "") or "").strip()
            memory_value = str(getattr(candidate, "memory_value", "") or "").strip()
            if not memory_key or not memory_value:
                continue
            _upsert_preference_document(
                db,
                user_id=user_id,
                memory_key=memory_key,
                memory_value=memory_value,
                scope=scope,
                source_thread_id=source_thread_id,
                source_message_id=source_message_id,
                updated_time=None,
            )
            persisted += 1

        if persisted > 0:
            db.commit()
        return persisted
    except Exception:
        rollback = getattr(db, "rollback", None)
        if callable(rollback):
            rollback()
        logger.exception("从输入同步 preference 文档失败: user_id=%s", user_id)
        return 0


def migrate_legacy_preference_kv(
    db: Session,
    *,
    user_id: int,
    scope: str = _DEFAULT_PREFERENCE_SCOPE,
    limit: int = 100,
) -> int:
    """将 legacy KV 偏好迁移为 preference 文档记忆（幂等）。"""

    if not user_id:
        return 0

    if document_memory_repo.count_documents(
        db,
        user_id=user_id,
        doc_kind=_DEFAULT_PREFERENCE_DOC_KIND,
        status=None,
        source=_DEFAULT_MEMORY_SOURCE,
    ) > 0:
        return 0

    memories = user_memory_repo.list_active_memories(
        db,
        user_id=user_id,
        scope=scope,
        limit=max(1, int(limit)),
    )
    if not memories:
        return 0

    migrated = 0
    migrated_keys: set[str] = set()
    for memory in memories:
        memory_key = str(getattr(memory, "memory_key", "") or "").strip()
        memory_value = str(getattr(memory, "memory_value", "") or "").strip()
        if not memory_key or not memory_value:
            continue
        _upsert_preference_document(
            db,
            user_id=user_id,
            memory_key=memory_key,
            memory_value=memory_value,
            scope=str(getattr(memory, "scope", "") or scope),
            source_thread_id=getattr(memory, "source_thread_id", None),
            source_message_id=getattr(memory, "source_message_id", None),
            updated_time=getattr(memory, "update_time", None),
        )
        migrated += 1
        migrated_keys.add(memory_key)

    if migrated > 0:
        user_memory_repo.archive_active_memories(
            db,
            user_id=user_id,
            scope=scope,
            memory_keys=sorted(migrated_keys),
        )
        db.commit()
    return migrated


def _build_memory_item_error(
    *,
    item_index: int,
    slot_key: str,
    reason_code: str,
    memory_kind: str | None = None,
    normalized_value: str | None = None,
    canonical_text: str | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "item_index": int(item_index),
        "slot_key": str(slot_key or "").strip(),
        "reason_code": str(reason_code or "memory_item_invalid"),
    }
    if memory_kind is not None:
        error["memory_kind"] = str(memory_kind or "").strip().lower()
    if normalized_value is not None:
        error["normalized_value"] = str(normalized_value or "").strip()
    if canonical_text is not None:
        error["canonical_text"] = str(canonical_text or "").strip()
    return error


def _normalize_decision_contract_payload(
    decision_contract: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(decision_contract or {})
    decision = str(payload.get("decision") or _DECISION_REJECT).strip().lower()
    reason_code = str(payload.get("reason_code") or "contract_missing_required").strip()
    confidence = _safe_float(payload.get("confidence"), default=0.0)
    if confidence < 0.0:
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0

    raw_memories = payload.get("memories")
    if isinstance(raw_memories, list):
        memories = [item for item in raw_memories if isinstance(item, dict)]
    elif isinstance(raw_memories, dict):
        memories = [raw_memories]
    else:
        memories = []

    audit_payload = payload.get("audit")
    if isinstance(audit_payload, dict):
        audit = dict(audit_payload)
    else:
        audit = {}

    return {
        "decision": decision,
        "reason_code": reason_code,
        "confidence": confidence,
        "memories": memories,
        "audit": audit,
    }


def _build_atomic_reject_contract(
    *,
    reason_code: str,
    confidence: float,
    detector: str,
    item_errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors = list(item_errors or [])
    return {
        "decision": _DECISION_REJECT,
        "reason_code": str(reason_code),
        "confidence": max(0.0, min(float(confidence), 1.0)),
        "memories": [],
        "audit": {
            "detector": detector,
            "rejected_items_count": len(errors),
            "item_errors": errors,
        },
    }


def _validate_atomic_batch_memories(
    memories: list[dict[str, Any]],
    *,
    slot_governance: MemorySlotGovernanceService,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_memories: list[dict[str, Any]] = []
    item_errors: list[dict[str, Any]] = []

    for index, raw_item in enumerate(memories):
        memory_kind = str(raw_item.get("memory_kind") or "").strip().lower()
        operation = str(raw_item.get("operation") or "").strip().lower()
        slot_key = str(raw_item.get("slot_key") or "").strip().lower()
        normalized_value = str(raw_item.get("normalized_value") or "").strip()
        canonical_text = str(raw_item.get("canonical_text") or "").strip()
        evidence_span = str(raw_item.get("evidence_span") or "").strip()

        required_fields = {
            "memory_kind": memory_kind,
            "operation": operation,
            "slot_key": slot_key,
            "normalized_value": normalized_value,
            "canonical_text": canonical_text,
            "evidence_span": evidence_span,
        }
        missing_required = any(not value for value in required_fields.values())
        if missing_required:
            item_errors.append(
                _build_memory_item_error(
                    item_index=index,
                    slot_key=slot_key,
                    reason_code="contract_missing_required",
                    memory_kind=memory_kind,
                    normalized_value=normalized_value,
                    canonical_text=canonical_text,
                )
            )
            continue

        if memory_kind not in _VALID_MEMORY_KINDS:
            item_errors.append(
                _build_memory_item_error(
                    item_index=index,
                    slot_key=slot_key,
                    reason_code="contract_invalid_memory_kind",
                    memory_kind=memory_kind,
                    normalized_value=normalized_value,
                    canonical_text=canonical_text,
                )
            )
            continue

        if operation not in _VALID_OPERATIONS:
            item_errors.append(
                _build_memory_item_error(
                    item_index=index,
                    slot_key=slot_key,
                    reason_code="contract_invalid_operation",
                    memory_kind=memory_kind,
                    normalized_value=normalized_value,
                    canonical_text=canonical_text,
                )
            )
            continue

        normalized_slot_key = slot_governance.normalize_slot_key(slot_key)
        if not normalized_slot_key:
            item_errors.append(
                _build_memory_item_error(
                    item_index=index,
                    slot_key=slot_key,
                    reason_code="slot_taxonomy_invalid",
                    memory_kind=memory_kind,
                    normalized_value=normalized_value,
                    canonical_text=canonical_text,
                )
            )
            continue

        normalized_item: dict[str, Any] = {
            "memory_kind": memory_kind,
            "operation": operation,
            "slot_key": normalized_slot_key,
            "normalized_value": normalized_value,
            "canonical_text": canonical_text,
            "evidence_span": evidence_span,
        }
        if raw_item.get("durability") is not None:
            normalized_item["durability"] = max(0.0, min(_safe_float(raw_item.get("durability"), 0.0), 1.0))
        normalized_memories.append(normalized_item)

    return normalized_memories, item_errors


def _persist_canonical_document_no_commit(
    db: Session,
    *,
    user_id: int,
    canonical_text: str,
    doc_kind: str,
    doc_key: str | None,
    slot_key: str | None,
    source_thread_id: str | None,
    source_message_id: int | None,
    source: str,
    scope: str,
    scope_ref: str | None,
    operation: str,
    event_time: datetime | None,
    memory_kind: str | None = None,
    normalized_value: str | None = None,
    evidence_span: str | None = None,
    decision_id: str | None = None,
    confidence: float | None = None,
    reason_code: str | None = None,
    memories_count: int | None = None,
    rejected_items_count: int | None = None,
    item_errors: list[dict[str, Any]] | None = None,
) -> int:
    normalized_text = _normalize_text(canonical_text)
    if not normalized_text:
        return 0

    normalized_doc_kind = str(doc_kind or "daily").strip().lower()
    if normalized_doc_kind == "permanent":
        normalized_doc_kind = _DEFAULT_PREFERENCE_DOC_KIND

    resolved_event_time = event_time or datetime.now()
    resolved_doc_key = _resolve_canonical_doc_key(
        doc_kind=normalized_doc_kind,
        doc_key=doc_key,
        slot_key=slot_key,
        event_time=resolved_event_time,
    )
    if not resolved_doc_key:
        logger.warning(
            "flush_canonical_memory 缺少 doc_key: user_id=%s, doc_kind=%s",
            user_id,
            normalized_doc_kind,
        )
        return 0

    resolved_slot_key = str(slot_key or "").strip() or None
    if resolved_slot_key is None and normalized_doc_kind == _DEFAULT_PREFERENCE_DOC_KIND:
        resolved_slot_key = resolved_doc_key

    resolved_scope_ref = scope_ref
    if normalized_doc_kind == "daily":
        resolved_title = f"记忆日记 {resolved_doc_key}"
        existing = document_memory_repo.get_active_document(
            db,
            user_id=user_id,
            doc_kind=normalized_doc_kind,
            doc_key=resolved_doc_key,
        )
        entry = _build_daily_entry(
            user_text=normalized_text,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )
        if existing and existing.content_md:
            content_md = f"{existing.content_md.rstrip()}\n\n{entry}".strip()
        else:
            content_md = f"# {resolved_title}\n\n{entry}".strip()
        summary_md = _build_daily_summary(normalized_text)
        if resolved_scope_ref is None:
            resolved_scope_ref = source_thread_id
    else:
        resolved_title = (
            f"槽位记忆 {resolved_slot_key or resolved_doc_key}"
            if normalized_doc_kind == _DEFAULT_PREFERENCE_DOC_KIND
            else f"记忆文档 {resolved_doc_key}"
        )
        content_md = _build_slot_canonical_content(
            slot_key=resolved_slot_key or resolved_doc_key,
            canonical_text=normalized_text,
            memory_kind=memory_kind,
            normalized_value=normalized_value,
            evidence_span=evidence_span,
            decision_id=decision_id,
            confidence=confidence,
            reason_code=reason_code,
            memories_count=memories_count,
            rejected_items_count=rejected_items_count,
            item_errors=item_errors,
            operation=operation,
            event_time=resolved_event_time,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )
        summary_md = normalized_text[:200]

    content_hash = _hash_text(content_md)
    document = document_memory_repo.upsert_document(
        db,
        user_id=user_id,
        doc_kind=normalized_doc_kind,
        doc_key=resolved_doc_key,
        slot_key=resolved_slot_key,
        title=resolved_title,
        content_md=content_md,
        summary_md=summary_md,
        source=source,
        scope=scope,
        scope_ref=resolved_scope_ref,
        content_hash=content_hash,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        operation=operation,
        last_event_time=resolved_event_time,
    )

    chunks = _split_document_to_chunks(content_md)
    document_memory_repo.replace_document_chunks(
        db,
        user_id=user_id,
        doc_id=document.id,
        chunks=chunks,
        source=source,
    )
    return 1


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

    return flush_canonical_memory(
        db,
        user_id=user_id,
        canonical_text=text,
        doc_kind="daily",
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
    )


def flush_canonical_memory(
    db: Session,
    *,
    user_id: int,
    canonical_text: str = "",
    doc_kind: str = "daily",
    doc_key: str | None = None,
    slot_key: str | None = None,
    source_thread_id: str | None = None,
    source_message_id: int | None = None,
    source: str = _DEFAULT_MEMORY_SOURCE,
    scope: str = "private",
    scope_ref: str | None = None,
    operation: str = "upsert",
    event_time: datetime | None = None,
    decision_contract: dict[str, Any] | None = None,
) -> int:
    """将 canonical_text 落库到 document/chunk 两表。"""

    if not user_id:
        return 0

    if decision_contract is not None:
        normalized_contract = _normalize_decision_contract_payload(decision_contract)
        detector = str((normalized_contract.get("audit") or {}).get("detector") or "llm_primary")

        if normalized_contract["decision"] != _DECISION_ACCEPT:
            decision_contract.clear()
            decision_contract.update(normalized_contract)
            return 0

        slot_governance = MemorySlotGovernanceService(repo=document_memory_repo)
        normalized_memories, item_errors = _validate_atomic_batch_memories(
            normalized_contract["memories"],
            slot_governance=slot_governance,
        )
        if item_errors:
            rejected_contract = _build_atomic_reject_contract(
                reason_code="memory_batch_atomic_reject",
                confidence=normalized_contract["confidence"],
                detector=detector,
                item_errors=item_errors,
            )
            decision_contract.clear()
            decision_contract.update(rejected_contract)
            return 0

        audit_payload = normalized_contract.get("audit") or {}
        decision_id = str(audit_payload.get("decision_id") or "").strip()
        if not decision_id:
            if source_message_id is not None:
                decision_id = f"decision-{int(source_message_id)}"
            else:
                decision_id = f"decision-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        persisted_count = 0
        resolved_event_time = event_time or datetime.now()
        try:
            for item in normalized_memories:
                persisted_count += _persist_canonical_document_no_commit(
                    db,
                    user_id=user_id,
                    canonical_text=str(item["canonical_text"]),
                    doc_kind=_DEFAULT_PREFERENCE_DOC_KIND,
                    doc_key=str(item["slot_key"]),
                    slot_key=str(item["slot_key"]),
                    source_thread_id=source_thread_id,
                    source_message_id=source_message_id,
                    source=source,
                    scope=scope,
                    scope_ref=scope_ref,
                    operation=str(item["operation"]),
                    event_time=resolved_event_time,
                    memory_kind=str(item["memory_kind"]),
                    normalized_value=str(item["normalized_value"]),
                    evidence_span=str(item["evidence_span"]),
                    decision_id=decision_id,
                    confidence=float(normalized_contract["confidence"]),
                    reason_code=str(normalized_contract["reason_code"]),
                    memories_count=len(normalized_memories),
                    rejected_items_count=0,
                    item_errors=[],
                )
            if persisted_count > 0:
                db.commit()
            normalized_contract["audit"] = {
                **audit_payload,
                "detector": detector,
                "decision_id": decision_id,
                "memories_count": len(normalized_memories),
                "rejected_items_count": 0,
                "item_errors": [],
            }
            decision_contract.clear()
            decision_contract.update(normalized_contract)
            return persisted_count
        except Exception:
            rollback = getattr(db, "rollback", None)
            if callable(rollback):
                rollback()
            logger.exception("atomic_batch 写入失败: user_id=%s", user_id)
            rejected_contract = _build_atomic_reject_contract(
                reason_code="memory_batch_atomic_reject",
                confidence=normalized_contract["confidence"],
                detector=detector,
                item_errors=[
                    _build_memory_item_error(
                        item_index=-1,
                        slot_key="",
                        reason_code="batch_write_failed",
                    )
                ],
            )
            decision_contract.clear()
            decision_contract.update(rejected_contract)
            return 0

    try:
        persisted = _persist_canonical_document_no_commit(
            db,
            user_id=user_id,
            canonical_text=canonical_text,
            doc_kind=doc_kind,
            doc_key=doc_key,
            slot_key=slot_key,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
            source=source,
            scope=scope,
            scope_ref=scope_ref,
            operation=operation,
            event_time=event_time,
        )
        if persisted > 0:
            db.commit()
        return persisted
    except Exception:
        rollback = getattr(db, "rollback", None)
        if callable(rollback):
            rollback()
        logger.exception("文档记忆 flush 失败: user_id=%s", user_id)
        return 0
