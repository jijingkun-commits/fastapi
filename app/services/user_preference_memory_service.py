"""用户偏好记忆服务（中文注释）。

负责三类职责：
1. 从用户输入中提取显式偏好
2. 生成可注入模型的偏好上下文
3. 持久化用户偏好记忆
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.repositories import user_memory_repo


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreferenceMemoryCandidate:
    """偏好记忆候选。"""

    memory_key: str
    memory_value: str
    confidence: Decimal


_TRIGGER_PATTERN = re.compile(r"(记住|默认|以后都|之后都|请始终|都用|一直|永远|总是)")
_PERSONA_LABEL_PATTERN = re.compile(r"AI人设\s*[:：]\s*([^\n，。！？；;]{1,40})")
_PERSONA_NAME_PATTERN = re.compile(
    r"(?:你叫|你以后叫|以后都叫你|自称|叫你|称呼你为|把你叫做)\s*[\"“'‘]?\s*([\u4e00-\u9fa5A-Za-z0-9_-]{1,24})\s*[\"”'’]?"
)
_USER_DISPLAY_NAME_PATTERN = re.compile(
    r"(?:我叫|我的名字(?:是)?|可以叫我|叫我|称呼我(?:为)?|你可以叫我)\s*[\"“'‘]?\s*([\u4e00-\u9fa5A-Za-z0-9_-]{1,24})\s*[\"”'’]?"
)

_DISPLAY_MAPPING = {
    "response.language": {
        "label": "回复语言",
        "values": {
            "zh-CN": "中文",
            "en-US": "英文",
        },
    },
    "response.length": {
        "label": "回复长度",
        "values": {
            "short": "简短",
            "detailed": "详细",
        },
    },
    "response.structure": {
        "label": "回复结构",
        "values": {
            "conclusion_first": "先结论后分析",
            "bullet_points": "分点表达",
        },
    },
    "response.style": {
        "label": "回复语气",
        "values": {
            "professional": "专业正式",
            "casual": "轻松口语化",
        },
    },
    "assistant.persona": {
        "label": "AI人设",
        "values": {},
    },
    "user.display_name": {
        "label": "用户称呼",
        "values": {},
    },
}

_FETCH_MULTIPLIER = 3
_DEFAULT_MAX_CONTEXT_CHARS = 320
USER_PREFERENCE_BOOTSTRAP_TEMPLATE_CONFIG_KEY = "memory.user_preference_bootstrap_template"
DEFAULT_USER_PREFERENCE_BOOTSTRAP_TEMPLATE = {"assistant.persona": "小嘉"}
_BOOTSTRAP_SOURCE_THREAD_ID = "system.user_bootstrap"


def _normalize_text(text: str) -> str:
    """归一化输入文本。"""

    if not text:
        return ""
    return " ".join(str(text).strip().split())


def _contains_any(text: str, patterns: Iterable[str]) -> bool:
    """判断文本是否命中任一模式。"""

    return any(re.search(pattern, text) for pattern in patterns)


def _normalize_persona_value(raw: str) -> str:
    """清洗 AI 人设值。"""

    value = str(raw or "").strip()
    value = value.strip("\"'“”‘’")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[。！!？，,；;]+$", "", value)
    if not value:
        return ""
    return value[:24]


def _normalize_controlled_memory_value(memory_key: str, raw_value: Any) -> str:
    """归一化受控记忆值。"""

    if memory_key in {"assistant.persona", "user.display_name"}:
        return _normalize_persona_value(str(raw_value or ""))

    mapping = _DISPLAY_MAPPING.get(memory_key)
    if not mapping:
        return ""

    value = str(raw_value or "").strip()
    if not value:
        return ""

    allowed_values = mapping.get("values", {})
    if not allowed_values:
        return value
    if value in allowed_values:
        return value

    lowered = value.lower()
    for candidate in allowed_values:
        if str(candidate).lower() == lowered:
            return str(candidate)

    for candidate, display_value in allowed_values.items():
        if str(display_value).strip().lower() == lowered:
            return str(candidate)

    return ""


def normalize_controlled_memory_template(template: Any) -> dict[str, str]:
    """规范化受控记忆模板，仅保留白名单 key。"""

    if not isinstance(template, dict):
        return {}

    normalized: dict[str, str] = {}
    for raw_key, raw_value in template.items():
        key = str(raw_key or "").strip()
        if not key or key not in _DISPLAY_MAPPING:
            continue

        normalized_value = _normalize_controlled_memory_value(key, raw_value)
        if not normalized_value:
            continue

        normalized[key] = normalized_value

    return normalized


def load_bootstrap_template_from_config() -> dict[str, str]:
    """读取并归一化用户偏好初始化模板。"""

    fallback = dict(DEFAULT_USER_PREFERENCE_BOOTSTRAP_TEMPLATE)

    try:
        from app.services.config_resolver import ConfigResolver

        template = ConfigResolver.get_json_dict(
            USER_PREFERENCE_BOOTSTRAP_TEMPLATE_CONFIG_KEY,
            fallback,
        )
    except Exception as config_error:
        logger.warning("读取用户偏好初始化模板失败，已使用默认模板: error=%s", config_error)
        return fallback

    normalized = normalize_controlled_memory_template(template)
    return normalized if normalized else fallback


def extract_explicit_preference_candidates(user_text: str) -> list[PreferenceMemoryCandidate]:
    """从用户输入提取显式偏好候选。

    首期策略：仅当命中触发词时进行白名单规则提取。
    """

    text = _normalize_text(user_text)
    if not text:
        return []

    if not _TRIGGER_PATTERN.search(text):
        return []

    candidates: dict[str, PreferenceMemoryCandidate] = {}

    if _contains_any(text, [r"中文", r"汉语"]):
        candidates["response.language"] = PreferenceMemoryCandidate(
            memory_key="response.language",
            memory_value="zh-CN",
            confidence=Decimal("0.980"),
        )
    elif _contains_any(text, [r"英文", r"英语"]):
        candidates["response.language"] = PreferenceMemoryCandidate(
            memory_key="response.language",
            memory_value="en-US",
            confidence=Decimal("0.980"),
        )

    if _contains_any(text, [r"简短", r"简洁", r"精炼", r"短一点"]):
        candidates["response.length"] = PreferenceMemoryCandidate(
            memory_key="response.length",
            memory_value="short",
            confidence=Decimal("0.940"),
        )
    elif _contains_any(text, [r"详细", r"展开", r"具体", r"多一点细节"]):
        candidates["response.length"] = PreferenceMemoryCandidate(
            memory_key="response.length",
            memory_value="detailed",
            confidence=Decimal("0.940"),
        )

    if _contains_any(text, [r"先结论后分析", r"先给结论", r"先说结论"]):
        candidates["response.structure"] = PreferenceMemoryCandidate(
            memory_key="response.structure",
            memory_value="conclusion_first",
            confidence=Decimal("0.930"),
        )
    elif _contains_any(text, [r"分点", r"条列", r"列表"]):
        candidates["response.structure"] = PreferenceMemoryCandidate(
            memory_key="response.structure",
            memory_value="bullet_points",
            confidence=Decimal("0.900"),
        )

    if _contains_any(text, [r"专业", r"正式"]):
        candidates["response.style"] = PreferenceMemoryCandidate(
            memory_key="response.style",
            memory_value="professional",
            confidence=Decimal("0.900"),
        )
    elif _contains_any(text, [r"轻松", r"口语化", r"随意"]):
        candidates["response.style"] = PreferenceMemoryCandidate(
            memory_key="response.style",
            memory_value="casual",
            confidence=Decimal("0.900"),
        )

    persona_raw = ""
    label_match = _PERSONA_LABEL_PATTERN.search(text)
    if label_match:
        persona_raw = label_match.group(1)
    else:
        name_match = _PERSONA_NAME_PATTERN.search(text)
        if name_match:
            persona_raw = name_match.group(1)

    persona = _normalize_persona_value(persona_raw)
    if persona:
        candidates["assistant.persona"] = PreferenceMemoryCandidate(
            memory_key="assistant.persona",
            memory_value=persona,
            confidence=Decimal("0.920"),
        )

    user_display_name_raw = ""
    user_display_name_match = _USER_DISPLAY_NAME_PATTERN.search(text)
    if user_display_name_match:
        user_display_name_raw = user_display_name_match.group(1)
    user_display_name = _normalize_persona_value(user_display_name_raw)
    if user_display_name:
        candidates["user.display_name"] = PreferenceMemoryCandidate(
            memory_key="user.display_name",
            memory_value=user_display_name,
            confidence=Decimal("0.910"),
        )

    return list(candidates.values())


def _format_memory_line(memory_key: str, memory_value: str) -> str:
    """将键值格式化为可读文本。"""

    mapping = _DISPLAY_MAPPING.get(memory_key)
    if not mapping:
        return f"- {memory_key}: {memory_value}"

    label = mapping["label"]
    readable = mapping.get("values", {}).get(memory_value, memory_value)
    return f"- {label}: {readable}"


def _format_memory_pair(memory_key: str, memory_value: str) -> str:
    """将键值格式化为摘要短语。"""

    mapping = _DISPLAY_MAPPING.get(memory_key)
    if not mapping:
        return f"{memory_key}={memory_value}"

    label = mapping["label"]
    readable = mapping.get("values", {}).get(memory_value, memory_value)
    return f"{label}={readable}"


def _dedupe_latest_memories(memories: Iterable, max_items: int) -> list:
    """按顺序去重，保留同 key 的第一条（最新）记录。"""

    deduped = []
    seen_keys: set[str] = set()

    for item in memories:
        key = str(getattr(item, "memory_key", "") or "").strip()
        if not key or key in seen_keys:
            continue

        seen_keys.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break

    return deduped


def _build_compressed_context(memories: list, max_context_chars: int) -> str:
    """当上下文过长时生成压缩摘要。"""

    if not memories:
        return ""

    pairs = [
        _format_memory_pair(
            str(getattr(item, "memory_key", "") or ""),
            str(getattr(item, "memory_value", "") or ""),
        )
        for item in memories
    ]

    kept = len(pairs)
    while kept > 0:
        omitted = len(pairs) - kept
        suffix = f"；其余{omitted}项已省略" if omitted > 0 else ""
        text = f"用户偏好摘要（按最近更新去重）：{'；'.join(pairs[:kept])}{suffix}。"
        if len(text) <= max_context_chars:
            return text
        kept -= 1

    suffix = f"；其余{len(pairs) - 1}项已省略" if len(pairs) > 1 else ""
    prefix = "用户偏好摘要（按最近更新去重）："
    min_budget = 12
    budget = max(min_budget, max_context_chars - len(prefix) - len(suffix) - 1)
    first_pair = pairs[0]
    clipped = first_pair[:budget]
    if len(first_pair) > budget:
        clipped += "…"
    return f"{prefix}{clipped}{suffix}。"


def _load_deduped_memories(
    db: Session,
    *,
    user_id: int,
    max_items: int,
) -> list:
    """加载并去重活跃记忆。"""

    if not user_id or max_items <= 0:
        return []

    fetch_limit = max(max_items, max_items * _FETCH_MULTIPLIER)
    memories = user_memory_repo.list_active_memories(
        db,
        user_id=user_id,
        scope="global",
        limit=fetch_limit,
    )
    if not memories:
        return []

    return _dedupe_latest_memories(memories, max_items=max_items)


def _render_context(memories: list, max_context_chars: int) -> str:
    """将记忆列表渲染为可注入上下文。"""

    if not memories:
        return ""

    lines = [
        "以下是用户已确认的跨会话偏好（仅在不与本轮明确指令冲突时生效）：",
    ]
    lines.extend(
        _format_memory_line(
            str(getattr(item, "memory_key", "") or ""),
            str(getattr(item, "memory_value", "") or ""),
        )
        for item in memories
    )
    if any(str(getattr(item, "memory_key", "") or "") == "assistant.persona" for item in memories):
        lines.append("执行要求：当用户未另行指定时，按 AI 人设进行自称。")
        lines.append("说明要求：该 AI 人设已写入跨会话记忆；除非用户要求删除，不要回答“无法跨会话记住该称呼”。")

    context = "\n".join(lines)
    if max_context_chars > 0 and len(context) > max_context_chars:
        return _build_compressed_context(memories, max_context_chars=max_context_chars)

    return context


def recall(
    db: Session,
    *,
    user_id: int,
    max_items: int = 8,
    max_context_chars: int = _DEFAULT_MAX_CONTEXT_CHARS,
    refresh_last_seen: bool = True,
) -> str:
    """召回用户偏好并构建上下文。"""

    memories = _load_deduped_memories(
        db,
        user_id=user_id,
        max_items=max_items,
    )
    if not memories:
        return ""

    if refresh_last_seen:
        try:
            user_memory_repo.touch_last_seen(db, memories)
            db.commit()
        except Exception as memory_error:
            logger.warning("刷新记忆命中时间失败，已降级: user_id=%s, error=%s", user_id, memory_error)
            rollback = getattr(db, "rollback", None)
            if callable(rollback):
                rollback()

    return _render_context(memories, max_context_chars=max_context_chars)


def build_user_preference_context(
    db: Session,
    user_id: int,
    max_items: int = 8,
    max_context_chars: int = _DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    """构建用户偏好上下文。"""

    deduped_memories = _load_deduped_memories(
        db,
        user_id=user_id,
        max_items=max_items,
    )
    return _render_context(deduped_memories, max_context_chars=max_context_chars)


def persist_explicit_preferences_from_input(
    db: Session,
    *,
    user_id: int,
    user_text: str,
    source_thread_id: str | None = None,
    source_message_id: int | None = None,
) -> int:
    """提取并持久化显式偏好。"""

    if not user_id:
        return 0

    candidates = extract_explicit_preference_candidates(user_text)
    if not candidates:
        return 0

    for candidate in candidates:
        user_memory_repo.upsert_active_memory(
            db,
            user_id=user_id,
            scope="global",
            memory_key=candidate.memory_key,
            memory_value=candidate.memory_value,
            confidence=candidate.confidence,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )

    db.commit()
    return len(candidates)


def bootstrap_user_preferences(
    db: Session,
    *,
    user_id: int,
    template: dict[str, Any] | None = None,
) -> int:
    """为新用户初始化受控记忆模板。"""

    if not user_id:
        return 0

    template_payload = (
        load_bootstrap_template_from_config()
        if template is None
        else normalize_controlled_memory_template(template)
    )
    if not template_payload:
        return 0

    for memory_key, memory_value in template_payload.items():
        user_memory_repo.upsert_active_memory(
            db,
            user_id=user_id,
            scope="global",
            memory_key=memory_key,
            memory_value=memory_value,
            confidence=Decimal("1.000"),
            source_thread_id=_BOOTSTRAP_SOURCE_THREAD_ID,
            source_message_id=None,
        )

    db.commit()
    return len(template_payload)


def flush(
    db: Session,
    *,
    user_id: int,
    user_text: str,
    source_thread_id: str | None = None,
    source_message_id: int | None = None,
) -> int:
    """将本轮用户显式偏好 flush 到记忆层。"""

    return persist_explicit_preferences_from_input(
        db,
        user_id=user_id,
        user_text=user_text,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
    )
