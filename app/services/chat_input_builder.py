"""聊天输入 contract builder。"""

from dataclasses import dataclass
from typing import Any, Optional

from app.ai.workflow.attachment_planning import (
    build_attachment_manifest,
    build_lightweight_probe,
)


@dataclass(slots=True)
class HumanTurnPayload:
    raw_prompt: str
    model_input: str
    display_content: str
    title_text: str
    attachment_manifest: list[dict[str, Any]]
    lightweight_probe: list[dict[str, Any]]
    metadata: dict[str, Any]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _render_attachment_display(attachment_manifest: list[dict[str, Any]]) -> str:
    rendered_parts: list[str] = []
    for item in attachment_manifest:
        if not isinstance(item, dict):
            continue

        name = _normalize_text(item.get("name")) or _normalize_text(item.get("attachment_id")) or "attachment"
        uri = _normalize_text(item.get("uri"))
        derived_kind = _normalize_text(item.get("derived_kind")) or "binary"

        if derived_kind == "image" and uri:
            rendered_parts.append(f"![{name}]({uri})")
            continue

        if uri:
            rendered_parts.append(f"- [{name}]({uri})")
        else:
            rendered_parts.append(f"- {name}")

    return "\n".join(rendered_parts).strip()


def _build_title_text(prompt: str, attachment_manifest: list[dict[str, Any]]) -> str:
    normalized_prompt = _normalize_text(prompt)
    if normalized_prompt:
        return normalized_prompt

    attachment_names = [
        _normalize_text(item.get("name"))
        for item in attachment_manifest
        if isinstance(item, dict) and _normalize_text(item.get("name"))
    ]
    if attachment_names:
        return ", ".join(attachment_names)
    return "新对话"


def build_human_turn_payload(prompt: str, attachments: Optional[list] = None) -> HumanTurnPayload:
    normalized_prompt = _normalize_text(prompt)
    attachment_manifest = build_attachment_manifest(attachments)
    lightweight_probe = build_lightweight_probe(attachment_manifest)
    attachment_display = _render_attachment_display(attachment_manifest)

    display_parts = [part for part in (normalized_prompt, attachment_display) if part]
    display_content = "\n\n".join(display_parts).strip()
    title_text = _build_title_text(normalized_prompt, attachment_manifest)
    attachment_names = [
        _normalize_text(item.get("name"))
        for item in attachment_manifest
        if isinstance(item, dict) and _normalize_text(item.get("name"))
    ]

    return HumanTurnPayload(
        raw_prompt=normalized_prompt,
        model_input=normalized_prompt,
        display_content=display_content,
        title_text=title_text,
        attachment_manifest=attachment_manifest,
        lightweight_probe=lightweight_probe,
        metadata={
            "attachment_count": len(attachment_manifest),
            "attachment_names": attachment_names,
        },
    )
