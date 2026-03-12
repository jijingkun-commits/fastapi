"""消息展示块编译器（中文注释）。

将最终文本、知识库图片映射和结构化结果统一编译为有序内容块，
作为 AI 消息的最终展示真相源。
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping

from app.core.message_content import normalize_message_content

_IMG_PLACEHOLDER_RE = re.compile(r"\[IMG-(\d+)\]")
_IMAGE_BLOCK_TYPES = {"image"}
_DIRECT_RESULT_BLOCK_TYPES = {"sql_result", "todo_list", "table", "chart", "text"}


def _to_sequence_number(event: Mapping[str, Any], index: int) -> tuple[int, int]:
    raw = event.get("sequence_number")
    if isinstance(raw, int) and raw >= 0:
        return raw, index
    envelope = event.get("envelope")
    if isinstance(envelope, Mapping):
        seq = envelope.get("sequence_number")
        if isinstance(seq, int) and seq >= 0:
            return seq, index
    return 10**9, index


def _normalize_kb_images(kb_images: Mapping[Any, Any] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    if not kb_images:
        return normalized
    for key, value in kb_images.items():
        if isinstance(value, str) and value.strip():
            normalized[str(key)] = value.strip()
    return normalized


def _append_markdown_block(blocks: list[dict[str, Any]], text: str) -> None:
    if not text:
        return
    if blocks and blocks[-1].get("type") == "markdown":
        previous = blocks[-1].get("data", {}).get("text", "")
        blocks[-1]["data"]["text"] = f"{previous}{text}"
        return
    blocks.append({"type": "markdown", "data": {"text": text}})


def _compile_text_blocks(final_text: str, kb_images: Mapping[str, str]) -> list[dict[str, Any]]:
    if not final_text:
        return []

    blocks: list[dict[str, Any]] = []
    cursor = 0
    for match in _IMG_PLACEHOLDER_RE.finditer(final_text):
        start, end = match.span()
        _append_markdown_block(blocks, final_text[cursor:start])
        image_index = match.group(1)
        image_url = kb_images.get(image_index)
        if image_url:
            blocks.append(
                {
                    "type": "image",
                    "data": {
                        "url": image_url,
                        "alt": "知识库图片",
                        "source": "knowledge",
                    },
                }
            )
        else:
            _append_markdown_block(blocks, match.group(0))
        cursor = end

    _append_markdown_block(blocks, final_text[cursor:])
    return blocks


def _build_result_block(result_event: Mapping[str, Any]) -> dict[str, Any] | None:
    data_type = str(result_event.get("data_type") or "").strip()
    data = result_event.get("data") if isinstance(result_event.get("data"), Mapping) else {}
    message = str(result_event.get("message") or "").strip()

    if data_type in _IMAGE_BLOCK_TYPES:
        url = str(data.get("url") or "").strip()
        if not url:
            return None
        return {
            "type": "image",
            "data": {
                "url": url,
                "alt": str(data.get("alt") or "生成图片").strip() or "生成图片",
                "caption": message or None,
                "source": str(data.get("source") or "tool").strip() or "tool",
            },
        }

    if data_type in _DIRECT_RESULT_BLOCK_TYPES:
        return {
            "type": data_type,
            "data": dict(data),
        }

    preview = json.dumps(data, ensure_ascii=False, default=str) if data else "{}"
    return {
        "type": "fallback_result",
        "data": {
            "data_type": data_type or "unknown",
            "preview": preview,
            "message": message or None,
        },
    }


def _dedupe_image_blocks(blocks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    previous_image_key: tuple[str, str] | None = None
    for block in blocks:
        if block.get("type") != "image":
            previous_image_key = None
            deduped.append(block)
            continue
        data = block.get("data") if isinstance(block.get("data"), Mapping) else {}
        url = str(data.get("url") or "").strip()
        source = str(data.get("source") or "").strip()
        key = (source, url)
        if url and key == previous_image_key:
            continue
        previous_image_key = key if url else None
        deduped.append(block)
    return deduped


def compile_message_display_blocks(
    final_text: Any,
    kb_images: Mapping[Any, Any] | None,
    result_events: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """将消息展示材料编译为有序内容块。"""

    text = normalize_message_content(final_text)
    normalized_kb_images = _normalize_kb_images(kb_images)
    blocks = _compile_text_blocks(text, normalized_kb_images)

    sortable_events: list[tuple[Mapping[str, Any], tuple[int, int]]] = []
    for index, event in enumerate(result_events or []):
        if isinstance(event, Mapping):
            sortable_events.append((event, _to_sequence_number(event, index)))

    for result_event, _ in sorted(sortable_events, key=lambda item: item[1]):
        block = _build_result_block(result_event)
        if block:
            blocks.append(block)

    return _dedupe_image_blocks(blocks)
