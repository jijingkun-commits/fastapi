"""Result 事件契约源（Pydantic）。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

RESULT_EVENT_NAME = "result"
RESULT_EVENT_SPEC_VERSION = "1.0"
RESULT_CONTRACT_VERSION = "1.0.0"
DEFAULT_RESULT_EVENT_SOURCE = "chat_service"


class ResultEventEnvelope(BaseModel):
    """SSE result 事件统一 envelope。"""

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    specversion: str = Field(default=RESULT_EVENT_SPEC_VERSION, min_length=1)
    type: str = Field(default=RESULT_EVENT_NAME, min_length=1)
    sequence_number: int = Field(ge=0)
    timestamp: datetime
    thread_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)

    model_config = ConfigDict(extra="ignore")


class _ResultEventBase(BaseModel):
    """结构化 result 事件基础字段。"""

    event: Literal["result"] = RESULT_EVENT_NAME
    data_type: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    envelope: ResultEventEnvelope
    result_contract_version: str = Field(default=RESULT_CONTRACT_VERSION, min_length=1)

    model_config = ConfigDict(extra="allow")


class TodoListResultEvent(_ResultEventBase):
    data_type: Literal["todo_list"]


class SqlResultEvent(_ResultEventBase):
    data_type: Literal["sql_result"]


class ImageResultEvent(_ResultEventBase):
    data_type: Literal["image"]


class TableResultEvent(_ResultEventBase):
    data_type: Literal["table"]


class ChartResultEvent(_ResultEventBase):
    data_type: Literal["chart"]


class TextResultEvent(_ResultEventBase):
    data_type: Literal["text"]


class GenericResultEvent(_ResultEventBase):
    """兜底结果类型（兼容未来 data_type）。"""


KnownResultEventUnion = Annotated[
    (
        TodoListResultEvent
        | SqlResultEvent
        | ImageResultEvent
        | TableResultEvent
        | ChartResultEvent
        | TextResultEvent
    ),
    Field(discriminator="data_type"),
]

ResultEventUnion = KnownResultEventUnion | GenericResultEvent

_KNOWN_RESULT_DATA_TYPES = frozenset({"todo_list", "sql_result", "image", "table", "chart", "text"})
_KNOWN_RESULT_EVENT_ADAPTER = TypeAdapter(KnownResultEventUnion)
_RESULT_EVENT_ADAPTER = TypeAdapter(ResultEventUnion)


def _normalize_non_empty_string(value: Any, *, default: str) -> str:
    normalized = str(value or "").strip()
    return normalized or default


def _normalize_non_negative_int(value: Any, *, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = fallback
    return parsed if parsed >= 0 else fallback


def _normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        dt = datetime.now(timezone.utc)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def envelope_backfill(
    envelope: Any,
    *,
    source: Any = DEFAULT_RESULT_EVENT_SOURCE,
    sequence_number: Any = 0,
    thread_id: Any = "-",
    run_id: Any = "-",
    event_type: Any = RESULT_EVENT_NAME,
) -> dict[str, Any]:
    """补齐并标准化 result envelope。"""

    raw = dict(envelope) if isinstance(envelope, dict) else {}
    fallback_sequence = _normalize_non_negative_int(sequence_number, fallback=0)

    raw["id"] = _normalize_non_empty_string(raw.get("id"), default=uuid4().hex)
    raw["source"] = _normalize_non_empty_string(raw.get("source"), default=str(source or DEFAULT_RESULT_EVENT_SOURCE))
    raw["specversion"] = _normalize_non_empty_string(
        raw.get("specversion"),
        default=RESULT_EVENT_SPEC_VERSION,
    )
    raw["type"] = _normalize_non_empty_string(raw.get("type"), default=str(event_type or RESULT_EVENT_NAME))
    raw["sequence_number"] = _normalize_non_negative_int(raw.get("sequence_number"), fallback=fallback_sequence)
    raw["timestamp"] = _normalize_timestamp(raw.get("timestamp"))
    raw["thread_id"] = _normalize_non_empty_string(raw.get("thread_id"), default=str(thread_id or "-"))
    raw["run_id"] = _normalize_non_empty_string(raw.get("run_id"), default=str(run_id or "-"))

    normalized = ResultEventEnvelope.model_validate(raw)
    return normalized.model_dump(mode="json")


def _validate_result_event_union(payload: dict[str, Any]) -> _ResultEventBase:
    data_type = str(payload.get("data_type") or "").strip()
    if data_type in _KNOWN_RESULT_DATA_TYPES:
        validated = _KNOWN_RESULT_EVENT_ADAPTER.validate_python(payload)
        return validated

    return GenericResultEvent.model_validate(payload)


def build_result_event_payload(
    *,
    data_type: Any,
    data: Any,
    message: Any,
    envelope: Any = None,
    source: Any = DEFAULT_RESULT_EVENT_SOURCE,
    sequence_number: Any = 0,
    thread_id: Any = "-",
    run_id: Any = "-",
    include_envelope: bool = True,
    strict_required: bool = False,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """构建并校验 result 事件。"""

    normalized_data_type = str(data_type or "").strip()
    if not normalized_data_type:
        if strict_required:
            raise ValueError("result payload missing required field: data_type")
        return None

    if strict_required and data is None:
        raise ValueError("result payload missing required field: data")

    normalized_data = data if isinstance(data, dict) else {}
    payload: dict[str, Any] = {
        "event": RESULT_EVENT_NAME,
        "data_type": normalized_data_type,
        "data": normalized_data,
        "message": str(message or ""),
        "result_contract_version": RESULT_CONTRACT_VERSION,
        "envelope": envelope_backfill(
            envelope,
            source=source,
            sequence_number=sequence_number,
            thread_id=thread_id,
            run_id=run_id,
            event_type=RESULT_EVENT_NAME,
        ),
    }

    if isinstance(extra_fields, dict):
        for key, value in extra_fields.items():
            if key in {"event", "data_type", "data", "message", "envelope", "result_contract_version"}:
                continue
            payload[key] = value

    try:
        validated = _validate_result_event_union(payload)
    except ValidationError as exc:
        if strict_required:
            raise ValueError(f"invalid result payload: {exc}") from exc
        return None

    normalized_payload = validated.model_dump(mode="json")
    if not include_envelope:
        normalized_payload.pop("event", None)
        normalized_payload.pop("envelope", None)
        normalized_payload.pop("result_contract_version", None)

    return normalized_payload


def result_event_union_json_schema() -> dict[str, Any]:
    """导出 ResultEventUnion JSON Schema。"""

    return _RESULT_EVENT_ADAPTER.json_schema()


__all__ = [
    "DEFAULT_RESULT_EVENT_SOURCE",
    "RESULT_CONTRACT_VERSION",
    "RESULT_EVENT_NAME",
    "RESULT_EVENT_SPEC_VERSION",
    "ResultEventUnion",
    "build_result_event_payload",
    "envelope_backfill",
    "result_event_union_json_schema",
]
