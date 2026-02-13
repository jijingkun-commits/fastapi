"""消息内容归一化工具（中文注释）。

提供两类能力：
1. 运行时消息内容归一化：将 str/list/dict 提取为可读文本。
2. 历史遗留内容兼容：识别并修复误存储为结构串的消息内容。
"""

from __future__ import annotations

import ast
import json
from typing import Any


# 仅针对明显的消息块结构串进行兼容，避免误伤普通文本
_LEGACY_TYPE_MARKERS = ("'type':", '"type":')
_LEGACY_TEXT_MARKERS = (
    "'text':",
    '"text":',
    "'content':",
    '"content":',
    "'data':",
    '"data":',
)

# 不参与用户可见正文提取的内部块
_INTERNAL_BLOCK_TYPES = {
    "function_call",
    "function_result",
    "tool_call",
    "tool_use",
    "tool_result",
}


def normalize_message_content(content: Any) -> str:
    """将消息内容统一归一化为可读文本。"""
    if isinstance(content, str):
        return content
    if content is None:
        return ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            normalized = _normalize_content_item(item)
            if normalized:
                parts.append(normalized)

        if parts:
            return "".join(parts)

        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)

    if isinstance(content, dict):
        normalized = _normalize_dict_content(content)
        if normalized:
            return normalized

        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)

    return str(content)


def normalize_legacy_message_content(content: Any) -> Any:
    """兼容历史遗留结构串，返回可直接回放的内容。"""
    if not isinstance(content, str):
        return content

    parsed = _parse_legacy_block_literal(content)
    if parsed is None:
        return content

    normalized = normalize_message_content(parsed).strip()
    return normalized if normalized else content


def _normalize_content_item(item: Any) -> str:
    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        item_type = str(item.get("type", "")).lower()
        if item_type in _INTERNAL_BLOCK_TYPES:
            return ""
        return _normalize_dict_content(item)

    return str(item)


def _normalize_dict_content(payload: dict[str, Any]) -> str:
    for key in ("text", "content", "data", "message"):
        value = payload.get(key)

        if isinstance(value, str):
            return value

        if isinstance(value, (list, dict)):
            nested = normalize_message_content(value)
            if nested:
                return nested

    return ""


def _parse_legacy_block_literal(raw_content: str) -> list[dict[str, Any]] | None:
    stripped = raw_content.strip()
    if not _looks_like_legacy_block_literal(stripped):
        return None

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(stripped)
        except Exception:
            continue

        if _is_legacy_block_payload(parsed):
            return parsed

    return None


def _looks_like_legacy_block_literal(content: str) -> bool:
    if len(content) < 4:
        return False

    if not (content.startswith("[") and content.endswith("]")):
        return False

    has_type_marker = any(marker in content for marker in _LEGACY_TYPE_MARKERS)
    has_text_marker = any(marker in content for marker in _LEGACY_TEXT_MARKERS)
    return has_type_marker and has_text_marker


def _is_legacy_block_payload(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False

    has_supported_block = False

    for item in value:
        if not isinstance(item, dict):
            return False

        block_type = str(item.get("type", "")).lower()
        if not block_type:
            return False

        if any(key in item for key in ("text", "content", "data")):
            has_supported_block = True

    return has_supported_block
