"""Agent 通信协议解析。"""
import re
import json
import logging
from typing import Optional, Dict, Any, Tuple, List, Set, TypedDict, NotRequired, Literal, cast
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage

from app.ai.utils.message_factory import create_ai_message
from app.contracts.result_event_contract import build_result_event_payload

logger = logging.getLogger(__name__)


def _normalize_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _normalize_unique_strings(values: Any, *, lowercase: bool = False) -> List[str]:
    if not isinstance(values, list):
        return []

    normalized: List[str] = []
    seen: Set[str] = set()
    for item in values:
        text = _normalize_text(item)
        if lowercase:
            text = text.lower()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


def _normalize_non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 0)

class AgentProtocol:
    HANDOFF_PATTERN = r'<!--HANDOFF:(\{.*?\})-->'
    KB_IMAGES_PATTERN = r'<!--KB_IMAGES:(\{.*?\})-->'
    IMG_PLACEHOLDER_PATTERN = r'\[IMG-\d+\]'

class HandoffResult(BaseModel):
    action: str = Field(default="handoff", description="操作类型")
    target_agent: str = Field(..., description="目标专家 Agent 名称")
    task_description: Optional[str] = Field(default=None, description="任务描述与上下文（非 data.query 必填）")
    frame: Optional[Dict[str, Any]] = Field(default=None, description="结构化会话帧（可选）")
    turn_act_hint: Optional[str] = Field(default=None, description="回合行为提示（可选）")

class StreamingToolStartPayload(TypedDict):

    name: str
    input: Dict[str, Any]


class StreamingResultEnvelope(TypedDict):

    id: str
    source: str
    specversion: str
    type: str
    sequence_number: int
    timestamp: str
    thread_id: str
    run_id: str


class StreamingResultPayload(TypedDict):

    data_type: str
    data: Dict[str, Any]
    message: str
    envelope: NotRequired[StreamingResultEnvelope]
    result_contract_version: NotRequired[str]


class StreamingKbImagesPayload(TypedDict):

    images: Dict[str, str]


class ResultAdditionalKwargsPayload(TypedDict):

    data_type: str
    data: Dict[str, Any]


class OperationAdditionalKwargsPayload(TypedDict):

    operation: Dict[str, Any]


class SkillRuntimeLoadedSkillPayload(TypedDict):

    skill_id: str
    version: str
    truncated: bool


class SkillRuntimeAdditionalKwargsPayload(TypedDict):

    runtime_mode: str
    catalog_version: str
    visible_skill_count: int
    loaded_skills: List[SkillRuntimeLoadedSkillPayload]
    allowed_tools: List[str]
    replay_source: str


class ConversationStateSnapshotPayload(TypedDict):

    owner: Literal["supervisor"]
    turn_act: str
    active_goal_ids: List[str]
    active_workflow: str
    pending_user_action: str
    session_frame_slots: List[str]
    snapshot_version: str
    clarify_fsm_state: NotRequired[str]
    clarify_round: NotRequired[int]


class ExpertInputContractPayload(TypedDict):

    contract_id: str
    contract_version: str
    target_agent: str
    state_owner: str
    source_fields: List[str]


class ResearchEvidencePayload(TypedDict):

    source: str
    excerpt: str


class ResearchResultPayload(TypedDict):

    contract_version: str
    research_mode: str
    research_task_id: str
    summary: str
    evidence: List[ResearchEvidencePayload]
    insufficiency: str
    source_count: int
    citation_count: int


def build_conversation_state_snapshot_payload(
    *,
    owner: Any,
    turn_act: Any,
    active_goal_ids: Any,
    active_workflow: Any,
    pending_user_action: Any,
    session_frame_slots: Any,
    snapshot_version: Any,
    clarify_fsm_state: Any = None,
    clarify_round: Any = None,
) -> Optional[ConversationStateSnapshotPayload]:

    if _normalize_text(owner, "supervisor") != "supervisor":
        return None

    payload: ConversationStateSnapshotPayload = {
        "owner": "supervisor",
        "turn_act": _normalize_text(turn_act, "UNKNOWN"),
        "active_goal_ids": _normalize_unique_strings(active_goal_ids),
        "active_workflow": _normalize_text(active_workflow, "supervisor"),
        "pending_user_action": _normalize_text(pending_user_action, "none"),
        "session_frame_slots": _normalize_unique_strings(session_frame_slots),
        "snapshot_version": _normalize_text(snapshot_version, "v1"),
    }

    normalized_clarify_state = _normalize_text(clarify_fsm_state)
    if normalized_clarify_state:
        payload["clarify_fsm_state"] = normalized_clarify_state

    normalized_clarify_round = _normalize_non_negative_int(clarify_round, -1)
    if normalized_clarify_round >= 0:
        payload["clarify_round"] = normalized_clarify_round

    return payload


def build_expert_input_contract_payload(
    *,
    contract_id: Any,
    target_agent: Any,
    state_owner: Any,
    source_fields: Any,
    contract_version: Any = "v1",
) -> Optional[ExpertInputContractPayload]:

    normalized_contract_id = _normalize_text(contract_id)
    normalized_target_agent = _normalize_text(target_agent)
    if not normalized_contract_id or not normalized_target_agent:
        return None

    return {
        "contract_id": normalized_contract_id,
        "contract_version": _normalize_text(contract_version, "v1"),
        "target_agent": normalized_target_agent,
        "state_owner": _normalize_text(state_owner, "supervisor"),
        "source_fields": _normalize_unique_strings(source_fields),
    }


def build_research_result_payload(
    *,
    research_mode: Any,
    research_task_id: Any,
    summary: Any,
    evidence: Any,
    insufficiency: Any,
    source_count: Any = None,
    citation_count: Any = None,
    contract_version: Any = "v1",
) -> ResearchResultPayload:

    normalized_evidence: List[ResearchEvidencePayload] = []
    seen_pairs: Set[Tuple[str, str]] = set()
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                source = _normalize_text(item.get("source"), "unknown")
                excerpt = _normalize_text(item.get("excerpt"))
            else:
                source = "unknown"
                excerpt = _normalize_text(item)
            if not excerpt:
                continue
            pair = (source, excerpt)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            normalized_evidence.append({"source": source, "excerpt": excerpt})

    normalized_mode = _normalize_text(research_mode, "research")
    inferred_source_count = len({item["source"] for item in normalized_evidence})
    return {
        "contract_version": _normalize_text(contract_version, "v1"),
        "research_mode": normalized_mode,
        "research_task_id": _normalize_text(research_task_id, f"{normalized_mode}:unknown"),
        "summary": _normalize_text(summary),
        "evidence": normalized_evidence,
        "insufficiency": _normalize_text(insufficiency),
        "source_count": _normalize_non_negative_int(source_count, inferred_source_count),
        "citation_count": _normalize_non_negative_int(citation_count, 0),
    }


def _normalize_skill_runtime_loaded_skills(loaded_skills: Any) -> List[SkillRuntimeLoadedSkillPayload]:

    if not isinstance(loaded_skills, list):
        return []

    normalized: List[SkillRuntimeLoadedSkillPayload] = []
    seen: Set[Tuple[str, str]] = set()
    for item in loaded_skills:
        if not isinstance(item, dict):
            continue
        skill_id = str(item.get("skill_id") or "").strip()
        version = str(item.get("version") or item.get("effective_version") or "v1").strip() or "v1"
        if not skill_id:
            continue
        dedupe_key = (skill_id, version)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append({
            "skill_id": skill_id,
            "version": version,
            "truncated": bool(item.get("truncated", False)),
        })
    return normalized


def _normalize_skill_runtime_allowed_tools(allowed_tools: Any) -> List[str]:

    return _normalize_unique_strings(allowed_tools, lowercase=True)


def build_skill_runtime_additional_kwargs_payload(
    runtime_mode: Any,
    catalog_version: Any,
    visible_skill_count: Any,
    loaded_skills: Any,
    allowed_tools: Any,
    replay_source: Any,
) -> Optional[SkillRuntimeAdditionalKwargsPayload]:

    normalized_runtime_mode = str(runtime_mode or "").strip()
    if not normalized_runtime_mode:
        return None

    normalized_catalog_version = str(catalog_version or "").strip()
    if not normalized_catalog_version:
        normalized_catalog_version = "-"

    try:
        normalized_visible_skill_count = max(int(visible_skill_count or 0), 0)
    except (TypeError, ValueError):
        normalized_visible_skill_count = 0

    normalized_replay_source = str(replay_source or "live").strip() or "live"
    return {
        "runtime_mode": normalized_runtime_mode,
        "catalog_version": normalized_catalog_version,
        "visible_skill_count": normalized_visible_skill_count,
        "loaded_skills": _normalize_skill_runtime_loaded_skills(loaded_skills),
        "allowed_tools": _normalize_skill_runtime_allowed_tools(allowed_tools),
        "replay_source": normalized_replay_source,
    }


def normalize_skill_runtime_additional_kwargs(additional_kwargs: Any) -> Dict[str, Any]:

    normalized = dict(additional_kwargs) if isinstance(additional_kwargs, dict) else {}
    runtime_payload = normalized.get("skill_runtime")
    if not isinstance(runtime_payload, dict):
        return normalized

    canonical_payload = build_skill_runtime_additional_kwargs_payload(
        runtime_mode=runtime_payload.get("runtime_mode"),
        catalog_version=runtime_payload.get("catalog_version"),
        visible_skill_count=runtime_payload.get("visible_skill_count"),
        loaded_skills=runtime_payload.get("loaded_skills"),
        allowed_tools=runtime_payload.get("allowed_tools"),
        replay_source=runtime_payload.get("replay_source"),
    )
    if canonical_payload is not None:
        normalized["skill_runtime"] = canonical_payload
    return normalized


def extract_skill_runtime_from_ai_message(message: BaseMessage) -> Optional[Dict[str, Any]]:

    if not isinstance(message, AIMessage):
        return None

    additional_kwargs = normalize_skill_runtime_additional_kwargs(getattr(message, "additional_kwargs", {}) or {})
    skill_runtime = additional_kwargs.get("skill_runtime")
    if not isinstance(skill_runtime, dict):
        return None
    return skill_runtime


def build_streaming_tool_start_payload(
    tool_name: Any,
    tool_args: Any,
) -> Optional[StreamingToolStartPayload]:
    normalized_name = str(tool_name or "").strip()
    if not normalized_name:
        return None

    normalized_args = tool_args if isinstance(tool_args, dict) else {}
    return {
        "name": normalized_name,
        "input": normalized_args,
    }


def build_streaming_result_payload(
    ai_message: Any,
    msg_content: str,
) -> Optional[StreamingResultPayload]:
    additional = getattr(ai_message, "additional_kwargs", {})
    return build_streaming_result_payload_from_fields(
        data_type=additional.get("data_type"),
        data=additional.get("data", {}),
        message=msg_content,
    )


def build_streaming_result_payload_from_fields(
    data_type: Any,
    data: Any,
    message: Any,
) -> Optional[StreamingResultPayload]:
    payload = build_result_event_payload(
        data_type=data_type,
        data=data,
        message=message,
        include_envelope=False,
        strict_required=False,
    )
    if not payload:
        return None

    return cast(StreamingResultPayload, payload)


def build_streaming_kb_images_payload(
    kb_images: Dict[str, str],
) -> StreamingKbImagesPayload:
    return {"images": dict(kb_images)}


def build_result_additional_kwargs_payload(
    data_type: Any,
    data: Any,
) -> Optional[ResultAdditionalKwargsPayload]:
    result_payload = build_streaming_result_payload_from_fields(
        data_type=data_type,
        data=data,
        message="",
    )
    if not result_payload:
        return None

    return {
        "data_type": result_payload["data_type"],
        "data": result_payload["data"],
    }


def build_operation_additional_kwargs_payload(
    operation: Any,
) -> Optional[OperationAdditionalKwargsPayload]:
    if not isinstance(operation, dict):
        return None

    normalized_operation = dict(operation)
    action = str(normalized_operation.get("action") or "").strip()
    if not action:
        return None

    normalized_operation["action"] = action
    if not isinstance(normalized_operation.get("data"), dict):
        normalized_operation["data"] = {}

    return {"operation": normalized_operation}


def extract_operation_from_ai_message(message: BaseMessage) -> Optional[Dict[str, Any]]:
    if not isinstance(message, AIMessage):
        return None

    additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
    if not isinstance(additional_kwargs, dict):
        return None

    operation = additional_kwargs.get("operation")
    if not isinstance(operation, dict):
        return None

    return operation

class AgentOutputParser:
    
    @staticmethod
    def parse_handoff(content: str) -> Optional[Dict[str, Any]]:
        match = re.search(AgentProtocol.HANDOFF_PATTERN, content)
        if match:
            try:
                data = json.loads(match.group(1))
                return data
            except json.JSONDecodeError:
                logger.warning("Handoff Regex JSON 解析失败")
        
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                if data.get("action") == "handoff":
                    return data
            except json.JSONDecodeError:
                pass
                
        return None

    @staticmethod
    def extract_latest_handoff_from_messages(messages: List[BaseMessage]) -> Optional[Dict[str, Any]]:
        if not messages:
            return None
        
        for msg in reversed(messages):
            if not isinstance(msg, ToolMessage):
                continue
            content = str(getattr(msg, "content", ""))
            if not content:
                continue
            handoff = AgentOutputParser.parse_handoff(content)
            if handoff:
                return handoff
        
        return None

    @staticmethod
    def extract_all_handoffs_from_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        if not messages:
            return []

        handoffs: List[Dict[str, Any]] = []
        for msg in messages:
            if not isinstance(msg, ToolMessage):
                continue

            content = str(getattr(msg, "content", ""))
            if not content:
                continue

            handoff = AgentOutputParser.parse_handoff(content)
            if handoff:
                handoffs.append(handoff)

        return handoffs
    
    @staticmethod
    def parse_handoff_typed(content: str) -> Optional["HandoffResult"]:
        data = AgentOutputParser.parse_handoff(content)
        if data is None:
            return None
        
        try:
            return HandoffResult(**data)
        except Exception as e:
            logger.warning(f"HandoffResult 验证失败: {e}")
            return None

    @staticmethod
    def parse_kb_images(content: str) -> Optional[Dict[str, str]]:
        match = re.search(AgentProtocol.KB_IMAGES_PATTERN, content)
        if match:
            try:
                data = json.loads(match.group(1))
                return data
            except json.JSONDecodeError:
                logger.warning("KB Images JSON 解析失败")
        return None

    @staticmethod
    def should_filter_content(content: str) -> bool:
        if not content or not isinstance(content, str):
            return False
        
        stripped = content.strip()
        if not stripped:
            return False
        
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                INTERNAL_KEYS = {"intent", "action", "target_agent", "task_description"}
                if isinstance(data, dict) and data.get("action") == "handoff":
                    return True
                if isinstance(data, dict) and any(k in data for k in INTERNAL_KEYS) and len(data) <= 5:
                    return True
            except (json.JSONDecodeError, TypeError):
                pass
                
        if stripped.startswith("```json") and stripped.endswith("```"):
            return True
            
        if "<!--HANDOFF:" in stripped:
            return True
            
        return False

class MessageFilter:

    @staticmethod
    def filter_for_tool_whitelist(messages: List[BaseMessage], allowed_tools: Set[str]) -> List[BaseMessage]:
        filtered = []
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                safe_calls = [tc for tc in msg.tool_calls if tc.get("name") in allowed_tools]
                
                if not safe_calls:
                    if msg.content:
                        filtered.append(create_ai_message(msg.content, id=msg.id))
                    continue
                
                if len(safe_calls) != len(msg.tool_calls):
                    new_msg = create_ai_message(msg.content, id=msg.id, tool_calls=safe_calls)
                    filtered.append(new_msg)
                else:
                    filtered.append(msg)
                continue
            
            if isinstance(msg, ToolMessage):
                if msg.name not in allowed_tools:
                    continue
            
            filtered.append(msg)
            
        return filtered
