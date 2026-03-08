import type {
  KnownResultDataType,
  ResultEventEnvelope,
} from "@/types/generated/result-event";
import { KNOWN_RESULT_DATA_TYPES } from "@/types/generated/result-event";
import type { ResultEventData } from "@/types/message";

export interface ResultEventValidateOptions {
  sseEventId?: string;
  sseRetryMs?: number;
}

const KNOWN_RESULT_DATA_TYPE_SET = new Set<string>(KNOWN_RESULT_DATA_TYPES);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toNonEmptyString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function toOptionalNonNegativeInt(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
    return Math.trunc(value);
  }
  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed) || parsed < 0) {
      return undefined;
    }
    return parsed;
  }
  return undefined;
}

function buildPreviewPayload(payload: unknown): string | undefined {
  if (payload === null || payload === undefined) {
    return undefined;
  }
  try {
    const serialized = JSON.stringify(payload);
    if (!serialized) {
      return undefined;
    }
    return serialized.length > 240 ? `${serialized.slice(0, 240)}...` : serialized;
  } catch {
    return String(payload);
  }
}

function normalizeEnvelope(
  rawEnvelope: unknown,
  fallbackEventId?: string,
): ResultEventEnvelope | undefined {
  if (!isRecord(rawEnvelope)) {
    return undefined;
  }

  const id = toNonEmptyString(rawEnvelope.id) ?? toNonEmptyString(fallbackEventId);
  const source = toNonEmptyString(rawEnvelope.source);
  const sequenceNumber = toOptionalNonNegativeInt(rawEnvelope.sequence_number);
  const timestamp = toNonEmptyString(rawEnvelope.timestamp);
  const threadId = toNonEmptyString(rawEnvelope.thread_id);
  const runId = toNonEmptyString(rawEnvelope.run_id);

  if (!id || !source || sequenceNumber === undefined || !timestamp || !threadId || !runId) {
    return undefined;
  }

  return {
    id,
    source,
    sequence_number: sequenceNumber,
    timestamp,
    thread_id: threadId,
    run_id: runId,
    specversion: toNonEmptyString(rawEnvelope.specversion),
    type: toNonEmptyString(rawEnvelope.type),
  };
}

export function isKnownResultDataType(dataType: string): dataType is KnownResultDataType {
  return KNOWN_RESULT_DATA_TYPE_SET.has(dataType);
}

export function validateResultEventPayload(
  payload: unknown,
  options: ResultEventValidateOptions = {},
): ResultEventData | null {
  if (!isRecord(payload)) {
    return null;
  }

  const dataType = toNonEmptyString(payload.data_type);
  if (!dataType) {
    return null;
  }

  const data = isRecord(payload.data) ? payload.data : {};
  const eventIdFromPayload = toNonEmptyString(payload.event_id);
  const normalizedEnvelope = normalizeEnvelope(payload.envelope, options.sseEventId ?? eventIdFromPayload);
  const eventId =
    toNonEmptyString(options.sseEventId)
    ?? eventIdFromPayload
    ?? normalizedEnvelope?.id;
  const sequenceNumber =
    toOptionalNonNegativeInt(payload.sequence_number)
    ?? normalizedEnvelope?.sequence_number;
  const retry =
    toOptionalNonNegativeInt(payload.retry)
    ?? toOptionalNonNegativeInt(options.sseRetryMs);

  const knownDataType = isKnownResultDataType(dataType);
  const fallbackUsed = !knownDataType;

  return {
    event: "result",
    data_type: dataType,
    data,
    message: toNonEmptyString(payload.message),
    event_id: eventId,
    retry,
    sequence_number: sequenceNumber,
    envelope: normalizedEnvelope,
    result_contract_version: toNonEmptyString(payload.result_contract_version),
    renderer_key: knownDataType ? dataType : "fallback",
    fallback_used: fallbackUsed,
    warning_code: fallbackUsed ? "RESULT_RENDERER_NOT_REGISTERED" : undefined,
    fallback_payload_preview: fallbackUsed ? buildPreviewPayload(data) : undefined,
  };
}

export function coerceResultEventData(
  payload: unknown,
  options: ResultEventValidateOptions = {},
): ResultEventData | null {
  return validateResultEventPayload(payload, options);
}
