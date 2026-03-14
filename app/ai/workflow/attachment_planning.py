"""附件合同与 planning 纯函数。"""

from typing import Any, Dict, Optional, Sequence

_ATTACHMENT_TABULAR_HINTS = ("csv", "excel", "spreadsheet", "sheet", "tsv")
_ATTACHMENT_DOCUMENT_HINTS = ("pdf", "word", "document", "text", "markdown", "json")
_ATTACHMENT_TEXT_EXTENSIONS = (".pdf", ".doc", ".docx", ".txt", ".md", ".json")
_ATTACHMENT_TABULAR_EXTENSIONS = (".csv", ".tsv", ".xls", ".xlsx")


def _normalize_text(value: Any, default: str = "") -> str:
    normalized = str(value or "").strip()
    return normalized or default


def _parse_attachment_payload(attachment: Any) -> tuple[str, str, str, int, str]:
    if isinstance(attachment, dict):
        raw_mime = attachment.get("mime_type")
        raw_name = attachment.get("name")
        raw_url = attachment.get("url")
        raw_size = attachment.get("size")
        raw_object_key = attachment.get("object_key")
    else:
        raw_mime = getattr(attachment, "mime_type", None)
        raw_name = getattr(attachment, "name", None)
        raw_url = getattr(attachment, "url", None)
        raw_size = getattr(attachment, "size", None)
        raw_object_key = getattr(attachment, "object_key", None)

    try:
        normalized_size = max(int(raw_size), 0)
    except (TypeError, ValueError):
        normalized_size = 0

    return (
        _normalize_text(raw_mime, default="unknown"),
        _normalize_text(raw_name, default="unknown"),
        _normalize_text(raw_url),
        normalized_size,
        _normalize_text(raw_object_key),
    )


def _derive_attachment_kind(*, name: str, mime_type: str) -> str:
    normalized_name = str(name or "").lower()
    normalized_mime = str(mime_type or "").lower()

    if normalized_mime.startswith("image/"):
        return "image"
    if any(hint in normalized_mime for hint in _ATTACHMENT_TABULAR_HINTS) or normalized_name.endswith(_ATTACHMENT_TABULAR_EXTENSIONS):
        return "tabular"
    if any(hint in normalized_mime for hint in _ATTACHMENT_DOCUMENT_HINTS) or normalized_name.endswith(_ATTACHMENT_TEXT_EXTENSIONS):
        return "document"
    return "binary"


def build_attachment_manifest(attachments: Optional[list]) -> list[dict[str, Any]]:
    """将附件列表收口为客观 manifest。"""

    manifest: list[dict[str, Any]] = []
    if not attachments:
        return manifest

    for index, attachment in enumerate(attachments, start=1):
        mime, name, url, size_bytes, object_key = _parse_attachment_payload(attachment)
        attachment_id = object_key or f"attachment-{index}"
        manifest.append(
            {
                "attachment_id": attachment_id,
                "name": name,
                "mime": mime,
                "size_bytes": size_bytes,
                "uri": url,
                "derived_kind": _derive_attachment_kind(name=name, mime_type=mime),
            }
        )

    return manifest


def build_lightweight_probe(attachment_manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """基于 manifest 生成轻量预检事实。"""

    probes: list[dict[str, Any]] = []
    for item in attachment_manifest:
        attachment_id = _normalize_text(item.get("attachment_id"))
        name = _normalize_text(item.get("name"), default=attachment_id)
        derived_kind = _normalize_text(item.get("derived_kind"), default="binary")
        lower_name = name.lower()

        probe: dict[str, Any] = {
            "attachment_id": attachment_id,
            "probe_status": "ready",
            "summary": f"{name}（kind={derived_kind}）",
        }

        if derived_kind == "tabular":
            probe.update(
                {
                    "sheet_names": [],
                    "column_names": [],
                    "row_count_estimate": None,
                    "sample_types": [],
                }
            )
        elif derived_kind == "document":
            probe.update(
                {
                    "title": name.rsplit(".", 1)[0] if "." in name else name,
                    "page_count": None,
                    "section_hints": [],
                    "ocr_needed": lower_name.endswith(".pdf"),
                }
            )
        elif derived_kind == "image":
            probe.update(
                {
                    "vision_hint": "analyze_image",
                    "ocr_hint": any(token in lower_name for token in ("scan", "截图", "票据", "发票", "receipt")),
                    "chart_like": any(token in lower_name for token in ("chart", "graph", "plot", "dashboard", "报表", "图")),
                }
            )

        probes.append(probe)

    return probes


def normalize_attachment_manifest_entries(raw_manifest: Any) -> list[Dict[str, Any]]:
    if not isinstance(raw_manifest, list):
        return []

    normalized: list[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_manifest, start=1):
        if not isinstance(item, dict):
            continue

        attachment_id = _normalize_text(item.get("attachment_id"), default=f"attachment-{index}")
        if not attachment_id or attachment_id in seen_ids:
            continue

        try:
            size_bytes = max(int(item.get("size_bytes")), 0)
        except (TypeError, ValueError):
            size_bytes = 0

        normalized.append(
            {
                "attachment_id": attachment_id,
                "name": _normalize_text(item.get("name"), default=attachment_id),
                "mime": _normalize_text(item.get("mime"), default="unknown"),
                "size_bytes": size_bytes,
                "uri": _normalize_text(item.get("uri")),
                "derived_kind": _normalize_text(item.get("derived_kind"), default="binary"),
            }
        )
        seen_ids.add(attachment_id)

    return normalized


def normalize_lightweight_probe_entries(raw_probe: Any) -> list[Dict[str, Any]]:
    if not isinstance(raw_probe, list):
        return []
    return [dict(item) for item in raw_probe if isinstance(item, dict)]


def _build_attachment_role(derived_kind: str, planning_route: str) -> str:
    if planning_route == "data_workflow":
        return "data_source" if derived_kind == "tabular" else "context_source"
    if planning_route == "research_subagent":
        return "visual_evidence" if derived_kind == "image" else "evidence_source"
    if planning_route == "todo_workflow":
        return "task_source"
    if planning_route == "direct_tool":
        return "image_input" if derived_kind == "image" else "file_input"
    if derived_kind == "tabular":
        return "data_source"
    if derived_kind == "image":
        return "visual_evidence"
    return "evidence_source"


def build_attachment_planning_contract(
    *,
    user_query: str,
    goal_buckets: Sequence[str],
    active_goal_count: int,
    has_explicit_multi_goal: bool,
    has_todo_context: bool,
    attachment_manifest: Sequence[Dict[str, Any]],
    lightweight_probe: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    attachment_manifest = [dict(item) for item in attachment_manifest if isinstance(item, dict)]
    if not attachment_manifest:
        return None

    normalized_goal_buckets: list[str] = []
    for bucket in goal_buckets:
        normalized_bucket = _normalize_text(bucket)
        if normalized_bucket and normalized_bucket not in normalized_goal_buckets:
            normalized_goal_buckets.append(normalized_bucket)

    non_general_goal_buckets = [bucket for bucket in normalized_goal_buckets if bucket != "general"]
    has_multiple_goal_buckets = len(non_general_goal_buckets) >= 2
    has_research_goal = "research" in non_general_goal_buckets
    has_document_probe = any(
        bool(item.get("ocr_needed"))
        or bool(item.get("section_hints"))
        or item.get("page_count") not in (None, 0, "", [])
        for item in lightweight_probe
        if isinstance(item, dict)
    )
    has_tabular_probe = any(
        bool(item.get("sheet_names"))
        or bool(item.get("column_names"))
        or item.get("row_count_estimate") not in (None, 0, "", [])
        for item in lightweight_probe
        if isinstance(item, dict)
    )

    if has_multiple_goal_buckets or (has_explicit_multi_goal and active_goal_count >= 2):
        planning_route = "mixed"
    elif has_research_goal:
        planning_route = "research_subagent"
    elif "data" in normalized_goal_buckets:
        planning_route = "data_workflow"
    elif "todo" in normalized_goal_buckets:
        planning_route = "todo_workflow"
    elif has_todo_context and not non_general_goal_buckets:
        planning_route = "todo_workflow"
    elif has_tabular_probe and not has_todo_context:
        planning_route = "data_workflow"
    else:
        planning_route = "direct_tool"

    all_attachment_ids = [
        _normalize_text(item.get("attachment_id"))
        for item in attachment_manifest
        if _normalize_text(item.get("attachment_id"))
    ]
    selected_attachment_ids = all_attachment_ids[:1] if planning_route == "direct_tool" and len(all_attachment_ids) == 1 else all_attachment_ids
    attachment_roles = [
        {
            "attachment_id": _normalize_text(item.get("attachment_id")),
            "role": _build_attachment_role(_normalize_text(item.get("derived_kind"), default="binary"), planning_route),
        }
        for item in attachment_manifest
    ]

    execution_items: list[Dict[str, Any]] = []
    if planning_route == "mixed":
        for bucket in non_general_goal_buckets:
            if bucket == "todo":
                route = "todo_workflow"
            elif bucket == "data":
                route = "data_workflow"
            elif bucket == "research":
                route = "research_subagent"
            else:
                route = "direct_tool"
            execution_items.append({"planning_route": route, "selected_attachment_ids": list(all_attachment_ids)})

    planner_reasons = [
        f"goal_buckets={','.join(normalized_goal_buckets) or 'general'}",
        f"attachment_count={len(all_attachment_ids)}",
        f"has_todo_context={str(has_todo_context).lower()}",
        f"has_research_goal={str(has_research_goal).lower()}",
        f"document_probe={str(has_document_probe).lower()}",
        f"tabular_probe={str(has_tabular_probe).lower()}",
    ]

    return {
        "planning_route": planning_route,
        "selected_attachment_ids": selected_attachment_ids,
        "attachment_roles": attachment_roles,
        "planner_reason": "; ".join(planner_reasons),
        "execution_items": execution_items,
        "requires_user_confirmation": planning_route == "todo_workflow",
    }


def render_attachment_planning_context(
    attachment_manifest: Sequence[Dict[str, Any]],
    lightweight_probe: Sequence[Dict[str, Any]],
    planning_payload: Dict[str, Any],
) -> str:
    probe_by_id = {
        _normalize_text(item.get("attachment_id")): dict(item)
        for item in lightweight_probe
        if isinstance(item, dict) and _normalize_text(item.get("attachment_id"))
    }
    selected_ids = [
        _normalize_text(item)
        for item in list(planning_payload.get("selected_attachment_ids") or [])
        if _normalize_text(item)
    ]
    role_by_id = {
        _normalize_text(item.get("attachment_id")): _normalize_text(item.get("role"), default="input")
        for item in list(planning_payload.get("attachment_roles") or [])
        if isinstance(item, dict)
    }

    lines = [
        "附件规划合同：",
        f"- planning_route: {planning_payload.get('planning_route')}",
        f"- selected_attachment_ids: {', '.join(selected_ids) if selected_ids else 'none'}",
        f"- planner_reason: {planning_payload.get('planner_reason')}",
    ]

    for item in attachment_manifest:
        attachment_id = _normalize_text(item.get("attachment_id"))
        if selected_ids and attachment_id not in selected_ids:
            continue
        probe_summary = _normalize_text(probe_by_id.get(attachment_id, {}).get("summary"))
        lines.append(
            "- attachment: "
            f"id={attachment_id}, name={item.get('name')}, kind={item.get('derived_kind')}, "
            f"role={role_by_id.get(attachment_id, 'input')}, uri={item.get('uri')}"
        )
        if probe_summary:
            lines.append(f"  probe: {probe_summary}")

    planning_route = _normalize_text(planning_payload.get("planning_route"), default="direct_tool")
    if planning_route == "data_workflow":
        lines.append("- 执行约束：先走 data_workflow，需要时再调用 read_uploaded_file。")
    elif planning_route == "research_subagent":
        lines.append("- 执行约束：走 research_subagent，附件只作为一次性研究输入，不接管主会话。")
    elif planning_route == "todo_workflow":
        lines.append("- 执行约束：只允许用于提炼待办或进入确认闭环。")
    elif planning_route == "mixed":
        lines.append("- 执行约束：mixed owner 仍是 supervisor，按 execution_items 协调执行。")
    else:
        lines.append("- 执行约束：优先 direct_tool，执行单步读取或识图。")

    return "\n".join(lines)
