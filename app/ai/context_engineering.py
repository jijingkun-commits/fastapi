"""推理前上下文工程：统一装配 llm_input_messages 与预算账本。"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Optional, Sequence

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages

TokenCounter = Callable[[Any], Any]


@dataclass(frozen=True)
class ContextBudgetLedger:
    """单次模型调用的上下文预算账本。"""

    model_code: str
    provider_code: str
    context_window: int
    token_budget: int
    prepared_message_token_estimate: int
    message_token_estimate: int
    system_token_estimate: int
    skill_catalog_token_estimate: int
    loaded_skill_token_estimate: int
    legacy_skill_token_estimate: int
    prompt_token_estimate: int
    tool_schema_token_estimate: int
    total_token_estimate_before_send: int
    selected_tools_for_turn: list[str]

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_context_budget_metadata(
    state: Dict[str, Any],
    *,
    scene_key: Optional[str],
    configured_max_tokens: int,
    ratio: float,
    min_tokens: int,
) -> Dict[str, Any]:
    """解析当前轮上下文窗口与 token 预算。"""

    model_code = str(state.get("model_id") or "").strip()
    provider_code = ""
    context_window = 0

    try:
        from app.services.llm_config_service import LLMConfigService
        from app.services.llm_scene_service import LLMSceneService

        resolved_model_code = model_code
        if not resolved_model_code and scene_key:
            resolved_model_code = LLMSceneService.resolve_model_code(scene_key=scene_key)
        if resolved_model_code:
            model_code = resolved_model_code
            model_cfg = LLMConfigService.get_model_config(resolved_model_code)
            if model_cfg is not None:
                provider_code = str(getattr(model_cfg, "provider_code", "") or "")
                try:
                    context_window = int(getattr(model_cfg, "context_window", 0) or 0)
                except (TypeError, ValueError):
                    context_window = 0
    except Exception:
        pass

    safe_max_tokens = max(context_window or configured_max_tokens or min_tokens, min_tokens)
    token_budget = max(int(safe_max_tokens * ratio), min_tokens)
    return {
        "model_code": model_code,
        "provider_code": provider_code,
        "context_window": safe_max_tokens,
        "token_budget": token_budget,
    }


def build_llm_input_context(
    *,
    prepared_messages: Sequence[BaseMessage],
    state: Dict[str, Any],
    token_budget: int,
    model_code: str,
    provider_code: str,
    context_window: int,
    prompt_text: str = "",
    tool_objects: Optional[Sequence[Any]] = None,
    token_counter: TokenCounter = count_tokens_approximately,
) -> tuple[list[BaseMessage], ContextBudgetLedger, int, int]:
    """统一构造推理态 llm_input_messages 与分项 token 账本。"""

    pruned_messages = trim_messages(
        prepared_messages,
        max_tokens=token_budget,
        token_counter=token_counter,
        strategy="last",
        start_on="human",
        end_on=("human", "tool", "ai"),
        include_system=True,
        allow_partial=False,
    )

    context_messages, token_parts = build_context_messages(state, token_counter=token_counter)
    llm_input_messages = inject_context_messages(pruned_messages, context_messages)
    prepared_message_token_estimate = _estimate_messages_tokens(prepared_messages, token_counter)
    message_token_estimate = _estimate_messages_tokens(pruned_messages, token_counter)
    prompt_token_estimate = _estimate_text_tokens(prompt_text, token_counter)
    tool_schema_token_estimate = _estimate_tool_schema_tokens(tool_objects or [], token_counter)
    total_token_estimate_before_send = (
        _estimate_messages_tokens(llm_input_messages, token_counter)
        + prompt_token_estimate
        + tool_schema_token_estimate
    )
    selected_tools_for_turn = [name for name in (_resolve_tool_name(tool) for tool in tool_objects or []) if name]

    ledger = ContextBudgetLedger(
        model_code=model_code,
        provider_code=provider_code,
        context_window=context_window,
        token_budget=token_budget,
        prepared_message_token_estimate=prepared_message_token_estimate,
        message_token_estimate=message_token_estimate,
        system_token_estimate=token_parts["system_token_estimate"],
        skill_catalog_token_estimate=token_parts["skill_catalog_token_estimate"],
        loaded_skill_token_estimate=token_parts["loaded_skill_token_estimate"],
        legacy_skill_token_estimate=token_parts["legacy_skill_token_estimate"],
        prompt_token_estimate=prompt_token_estimate,
        tool_schema_token_estimate=tool_schema_token_estimate,
        total_token_estimate_before_send=total_token_estimate_before_send,
        selected_tools_for_turn=selected_tools_for_turn,
    )
    return list(llm_input_messages), ledger, prepared_message_token_estimate, message_token_estimate


def build_context_messages(
    state: Dict[str, Any],
    *,
    token_counter: TokenCounter = count_tokens_approximately,
) -> tuple[list[SystemMessage], Dict[str, int]]:
    """把运行时 state 中真正应注入模型的上下文收口为 SystemMessage。"""

    messages: list[SystemMessage] = []
    token_parts = {
        "system_token_estimate": 0,
        "skill_catalog_token_estimate": 0,
        "loaded_skill_token_estimate": 0,
        "legacy_skill_token_estimate": 0,
    }

    system_context = str(state.get("system_context") or "").strip()
    if system_context:
        messages.append(SystemMessage(content=system_context))
        token_parts["system_token_estimate"] = _estimate_text_tokens(system_context, token_counter)

    skill_catalog_context = str(state.get("skill_catalog_context") or "").strip()
    if skill_catalog_context:
        messages.append(SystemMessage(content=skill_catalog_context))
        token_parts["skill_catalog_token_estimate"] = _estimate_text_tokens(skill_catalog_context, token_counter)

    loaded_skill_summary = _build_loaded_skill_summary_from_state(state)
    if loaded_skill_summary:
        messages.append(SystemMessage(content=loaded_skill_summary))
        token_parts["loaded_skill_token_estimate"] = _estimate_text_tokens(loaded_skill_summary, token_counter)
    else:
        legacy_skill_context = str(state.get("skill_context") or "").strip()
        if legacy_skill_context:
            messages.append(SystemMessage(content=legacy_skill_context))
            token_parts["legacy_skill_token_estimate"] = _estimate_text_tokens(legacy_skill_context, token_counter)

    return messages, token_parts


def inject_context_messages(
    pruned_messages: Sequence[BaseMessage],
    context_messages: Sequence[SystemMessage],
) -> list[BaseMessage]:
    """将运行时 system 上下文插入到原始 SystemMessage 前缀之后。"""

    if not context_messages:
        return list(pruned_messages)

    insert_pos = 0
    for index, message in enumerate(pruned_messages):
        if not isinstance(message, SystemMessage):
            insert_pos = index
            break
    else:
        insert_pos = len(pruned_messages)

    return list(pruned_messages[:insert_pos]) + list(context_messages) + list(pruned_messages[insert_pos:])


def _build_loaded_skill_summary_from_state(state: Dict[str, Any], *, max_items: int = 3) -> str:
    loaded_skill_registry = state.get("loaded_skill_registry") or {}
    if isinstance(loaded_skill_registry, dict) and loaded_skill_registry:
        manifest = state.get("skill_catalog_manifest") or []
        manifest_map = {
            str(item.get("skill_id") or "").strip(): item
            for item in manifest
            if isinstance(item, dict) and str(item.get("skill_id") or "").strip()
        }
        lines = ["以下技能已加载到当前会话，可直接复用其能力摘要："]
        skill_items = list(loaded_skill_registry.items())
        for skill_id, payload in skill_items[:max_items]:
            payload_dict = payload if isinstance(payload, dict) else {}
            manifest_item = manifest_map.get(str(skill_id), {})
            display_name = str(
                manifest_item.get("display_name")
                or manifest_item.get("name")
                or manifest_item.get("skill_id")
                or skill_id
            ).strip()
            version = str(payload_dict.get("version") or manifest_item.get("effective_version") or "v1").strip()
            usage_hint = _clip_text(
                manifest_item.get("when_to_use") or manifest_item.get("description") or "",
                limit=96,
            )
            line = f"- {display_name} | skill_id={skill_id} | version={version}"
            if usage_hint:
                line += f" | 用途：{usage_hint}"
            if bool(payload_dict.get("truncated", False)):
                line += " | 正文已截断"
            lines.append(line)
        omitted = len(skill_items) - min(len(skill_items), max_items)
        if omitted > 0:
            lines.append(f"- 其余 {omitted} 个已省略，按需再从 registry 回源。")
        return "\n".join(lines)

    loaded_skill_context = str(state.get("loaded_skill_context") or "").strip()
    if loaded_skill_context:
        return "以下技能已加载到当前会话，可直接复用其能力摘要：\n- " + _clip_text(loaded_skill_context, limit=180)
    return ""


def _estimate_text_tokens(text: Any, token_counter: TokenCounter) -> int:
    content = str(text or "").strip()
    if not content:
        return 0
    return _estimate_messages_tokens([SystemMessage(content=content)], token_counter)


def _estimate_messages_tokens(messages: Sequence[BaseMessage], token_counter: TokenCounter) -> int:
    try:
        return int(token_counter(list(messages)) or 0)
    except Exception:
        return 0


def _estimate_tool_schema_tokens(tool_objects: Sequence[Any], token_counter: TokenCounter) -> int:
    if not tool_objects:
        return 0
    chunks: list[str] = []
    for tool_obj in tool_objects:
        tool_name = _resolve_tool_name(tool_obj)
        description = str(getattr(tool_obj, "description", "") or "").strip()
        args_schema = getattr(tool_obj, "args_schema", None)
        schema_text = ""
        try:
            if args_schema is not None and hasattr(args_schema, "model_json_schema"):
                schema_text = json.dumps(args_schema.model_json_schema(), ensure_ascii=False, sort_keys=True)
            elif args_schema is not None and hasattr(args_schema, "schema"):
                schema_text = json.dumps(args_schema.schema(), ensure_ascii=False, sort_keys=True)
            else:
                args_payload = getattr(tool_obj, "args", None)
                if isinstance(args_payload, dict) and args_payload:
                    schema_text = json.dumps(args_payload, ensure_ascii=False, sort_keys=True)
        except Exception:
            schema_text = ""
        if tool_name or description or schema_text:
            chunks.append(f"name={tool_name}\ndescription={description}\nschema={schema_text}")
    if not chunks:
        return 0
    return _estimate_text_tokens("\n\n".join(chunks), token_counter)


def _resolve_tool_name(tool_obj: Any) -> str:
    name = getattr(tool_obj, "name", None)
    if callable(name):
        try:
            name = name()
        except Exception:
            name = None
    if not name:
        name = getattr(tool_obj, "__name__", "")
    return str(name or "").strip().lower()


def _clip_text(raw: Any, *, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(raw or "")).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 1, 0)].rstrip() + "…"
