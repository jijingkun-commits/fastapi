"""统一 research_subagent 执行单元。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langchain.tools import tool
from pydantic import BaseModel, Field

from app.ai.protocol import build_research_result_payload
from app.ai.tools.chatTools import build_web_research_source_payload
from app.ai.tools.ragflow_tool import build_knowledge_research_source_payload

_SOURCE_LABELS = {
    "knowledge": "知识库",
    "web": "网页",
}


class ResearchSubagentInput(BaseModel):
    """统一 research_subagent 输入。"""

    query: str = Field(description="多来源研究任务描述，适用于综合、对比、归纳和证据汇总")
    dataset_id: str | None = Field(default=None, description="可选知识库 ID，不填则使用默认知识库")
    include_knowledge: bool = Field(default=True, description="是否启用知识库来源")
    include_web: bool = Field(default=True, description="是否启用网页来源")


def _build_research_task_id(query: str) -> str:
    return f"research:{hashlib.sha1(str(query or '').encode('utf-8')).hexdigest()[:8]}"


def _dedupe_ordered_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _collect_source_payloads(
    *,
    query: str,
    dataset_id: str | None,
    include_knowledge: bool,
    include_web: bool,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    if include_knowledge:
        payloads.append(build_knowledge_research_source_payload(query=query, dataset_id=dataset_id))
    if include_web:
        payloads.append(build_web_research_source_payload(query=query))
    return [payload for payload in payloads if isinstance(payload, dict)]


@tool(args_schema=ResearchSubagentInput)
def research_subagent(
    query: str,
    dataset_id: str | None = None,
    include_knowledge: bool = True,
    include_web: bool = True,
) -> str:
    """统一执行 knowledge + web 多来源研究，保持 Supervisor 作为唯一主会话 owner。"""

    source_payloads = _collect_source_payloads(
        query=query,
        dataset_id=dataset_id,
        include_knowledge=include_knowledge,
        include_web=include_web,
    )

    summary_lines: list[str] = []
    markdown_parts: list[str] = []
    insufficiency_parts: list[str] = []
    evidence: list[dict[str, Any]] = []
    media_refs: list[dict[str, Any]] = []
    citation_count = 0
    source_count = 0

    for payload in source_payloads:
        mode = str(payload.get("research_mode") or "").strip() or "research"
        label = _SOURCE_LABELS.get(mode, mode)
        summary = str(payload.get("summary") or "").strip()
        summary_markdown = str(payload.get("summary_markdown") or "").strip()
        insufficiency = str(payload.get("insufficiency") or "").strip()
        if summary:
            summary_lines.append(f"{label}：{summary}")
        if summary_markdown:
            markdown_parts.append(f"### {label}\n{summary_markdown}")
        if insufficiency:
            insufficiency_parts.append(f"{label}：{insufficiency}")
        evidence.extend([item for item in list(payload.get("evidence") or []) if isinstance(item, dict)])
        media_refs.extend([item for item in list(payload.get("media_refs") or []) if isinstance(item, dict)])
        try:
            citation_count += max(int(payload.get("citation_count") or 0), 0)
        except (TypeError, ValueError):
            pass
        try:
            source_count += max(int(payload.get("source_count") or 0), 0)
        except (TypeError, ValueError):
            pass

    merged_summary_lines = _dedupe_ordered_texts(summary_lines)
    merged_markdown_parts = _dedupe_ordered_texts(markdown_parts)
    merged_insufficiency_parts = _dedupe_ordered_texts(insufficiency_parts)

    payload = build_research_result_payload(
        research_mode="multi_source",
        research_task_id=_build_research_task_id(query),
        summary="；".join(merged_summary_lines),
        summary_markdown="\n\n".join(merged_markdown_parts),
        evidence=evidence,
        insufficiency="；".join(merged_insufficiency_parts),
        source_count=source_count,
        citation_count=citation_count,
        media_refs=media_refs,
    )
    return json.dumps(payload, ensure_ascii=False)
