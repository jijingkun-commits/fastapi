"""第三方工具观察结果归一化辅助。"""

from __future__ import annotations

import html
import json
import re
from typing import Any

TAVILY_ERROR_HINTS = (
    "no search results found for",
    "suggestions: remove time_range argument",
    "try a more detailed search using 'advanced' search_depth",
)
TAVILY_RAW_NOISE_PATTERNS = (
    r'alt\s*=\s*"[^"]*"',
    r'style\s*=\s*"[^"]*"',
)
TAVILY_RAW_BOILERPLATE_HINTS = (
    "首页",
    "国内天气",
    "空气质量",
    "国际天气",
    "景点天气",
    "天气新闻",
    "专业天气",
    "收藏",
    "切换",
)


def _normalize_summary_text(value: Any, limit: int = 180) -> str:
    raw = str(value or "")
    cleaned = re.sub(r"\s+", " ", raw).strip()
    if not cleaned:
        return ""
    return cleaned[:limit]


def is_tavily_tool_error_output(tool_content: str, payload: Any = None) -> bool:
    """识别 Tavily 的无结果/报错输出。"""
    normalized = str(tool_content or "").strip().lower()
    if any(hint in normalized for hint in TAVILY_ERROR_HINTS):
        return True

    if isinstance(payload, dict):
        status = str(payload.get("status") or "").strip().lower()
        if status in {"error", "failed", "failure"}:
            return True
        if payload.get("error"):
            return True
        answer = str(payload.get("answer") or "").strip().lower()
        if answer.startswith("no search results found for"):
            return True

    return False


def _sanitize_tavily_raw_text(tool_content: str) -> str:
    """清洗 Tavily 原始网页文本中的 HTML/站点噪声。"""
    text = html.unescape(str(tool_content or ""))
    if not text.strip():
        return ""

    for pattern in TAVILY_RAW_NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("#", " ")
    text = text.replace(">", " ")
    text = text.replace('"', " ")
    text = text.replace("_", " ")
    text = text.replace("【", " ").replace("】", " ")

    for stop_hint in ("当前时间", "全国天气网 首页", "全国天气网"):
        if stop_hint in text:
            text = text.split(stop_hint, 1)[0]

    for hint in TAVILY_RAW_BOILERPLATE_HINTS:
        text = text.replace(hint, " ")

    text = re.sub(r"\s+", " ", text).strip(" ：:；;，,")
    return _normalize_summary_text(text, limit=220)


def summarize_tavily_tool_output(tool_content: str) -> str:
    """从 Tavily 工具输出中提取可用于用户可见摘要的内容。"""
    stripped = str(tool_content or "").strip()
    if not stripped:
        return ""

    payload: Any = None
    if (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    ):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = None

    if is_tavily_tool_error_output(stripped, payload=payload):
        return ""

    if isinstance(payload, dict):
        answer = _normalize_summary_text(payload.get("answer"), limit=220)
        if answer:
            return answer
        results = payload.get("results")
    elif isinstance(payload, list):
        results = payload
    else:
        return _sanitize_tavily_raw_text(stripped)

    if not isinstance(results, list):
        return _sanitize_tavily_raw_text(stripped)

    lines = []
    for item in results[:2]:
        if not isinstance(item, dict):
            continue
        title = _normalize_summary_text(item.get("title"), limit=36)
        snippet = _normalize_summary_text(item.get("content") or item.get("snippet"), limit=140)
        if title and snippet:
            lines.append(f"{title}: {snippet}")
        elif snippet:
            lines.append(snippet)

    merged = "；".join(lines)
    if merged:
        return _normalize_summary_text(merged, limit=240)
    return _sanitize_tavily_raw_text(stripped)
