import { type Message } from "@langchain/langgraph-sdk";

import type { ActiveRunItem, InterruptData } from "@/lib/backend";
import type { KbImages } from "@/components/chat/utils";
import type { StreamStatus } from "@/providers/StreamContext";
import { coerceResultEventData } from "@/lib/validators/result-event";
import type { ClarificationEventData, ResultEventData, StatusEventData } from "@/types/message";

export type ThreadRuntimeState = {
  messages: Message[];
  isLoading: boolean;
  error: unknown;
  interrupt: InterruptData | null;
  currentStatus: StreamStatus | null;
  kbImages: KbImages;
  historyLoaded: boolean;
};

export const DRAFT_THREAD_KEY = "__draft__";

export function createEmptyThreadRuntime(): ThreadRuntimeState {
  return {
    messages: [],
    isLoading: false,
    error: undefined,
    interrupt: null,
    currentStatus: null,
    kbImages: {},
    historyLoaded: false,
  };
}

export function getThreadKey(threadId: string | null | undefined): string {
  if (!threadId) {
    return DRAFT_THREAD_KEY;
  }
  const trimmed = threadId.trim();
  return trimmed.length > 0 ? trimmed : DRAFT_THREAD_KEY;
}

export function isRunningStatus(status: string | null | undefined): boolean {
  return status === "running";
}

export function toActiveRunMap(items: ActiveRunItem[]): Record<string, ActiveRunItem> {
  return items.reduce<Record<string, ActiveRunItem>>((acc, item) => {
    acc[item.thread_id] = item;
    return acc;
  }, {});
}

export function createLocalActiveRunSnapshot(threadId: string, runId: string, status: string): ActiveRunItem {
  return {
    run_id: runId,
    thread_id: threadId,
    status,
    updated_at: new Date().toISOString(),
    last_activity_at: null,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function getImageUrlFromResult(data: ResultEventData): string | null {
  if (data.data_type !== "image" || !isRecord(data.data)) {
    return null;
  }

  const value = data.data.url;
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function getErrorMessageFromResult(data: ResultEventData): string {
  if (typeof data.message === "string" && data.message.trim().length > 0) {
    return data.message;
  }
  if (isRecord(data.data) && typeof data.data.message === "string" && data.data.message.trim().length > 0) {
    return data.data.message;
  }
  return "未知错误";
}

export function getToolOutputPreview(output: unknown): string {
  if (typeof output === "string") {
    return output.slice(0, 100);
  }
  try {
    const serialized = JSON.stringify(output);
    if (typeof serialized === "string") {
      return serialized.slice(0, 100);
    }
    return String(output).slice(0, 100);
  } catch {
    return String(output).slice(0, 100);
  }
}

export function normalizeStatusData(statusData: StatusEventData): StreamStatus | null {
  const message = statusData.message.trim();
  if (message.length === 0) {
    return null;
  }
  return {
    message,
    phase: statusData.phase ?? "processing",
  };
}

export function normalizeClarificationQuestions(questions: string[]): string[] {
  const normalized: string[] = [];
  for (const question of questions) {
    const trimmed = question.trim();
    if (!trimmed || normalized.includes(trimmed)) {
      continue;
    }
    normalized.push(trimmed);
  }
  return normalized;
}

export function buildClarificationDisplayText(data: ClarificationEventData): string {
  const message = typeof data.message === "string" ? data.message.trim() : "";
  const questions = normalizeClarificationQuestions(data.questions);
  const formattedQuestions = questions
    .map((question, index) => `${index + 1}. ${question}`)
    .join("\n");

  if (message && formattedQuestions) {
    return `${message}\n\n${formattedQuestions}`;
  }
  if (formattedQuestions) {
    return formattedQuestions;
  }
  return message;
}

export function resolveResultEventId(resultEvent: ResultEventData): string | undefined {
  if (typeof resultEvent.event_id === "string" && resultEvent.event_id.trim().length > 0) {
    return resultEvent.event_id;
  }

  const envelopeId = resultEvent.envelope?.id;
  if (typeof envelopeId === "string" && envelopeId.trim().length > 0) {
    return envelopeId;
  }

  return undefined;
}

function resolveResultSequence(resultEvent: ResultEventData): number | undefined {
  if (typeof resultEvent.sequence_number === "number" && Number.isFinite(resultEvent.sequence_number)) {
    return Math.trunc(resultEvent.sequence_number);
  }

  const envelopeSequence = resultEvent.envelope?.sequence_number;
  if (typeof envelopeSequence === "number" && Number.isFinite(envelopeSequence)) {
    return Math.trunc(envelopeSequence);
  }

  return undefined;
}

export function coerceResultEventArray(value: unknown): ResultEventData[] {
  if (!Array.isArray(value)) {
    return [];
  }

  const normalized: ResultEventData[] = [];
  for (const item of value) {
    const resultEvent = coerceResultEventData(item);
    if (resultEvent) {
      normalized.push(resultEvent);
    }
  }
  return normalized;
}

function dedupByEventId(
  existingEvents: ResultEventData[],
  incomingEvent: ResultEventData,
): { events: ResultEventData[]; dedupDropped: boolean } {
  const incomingEventId = resolveResultEventId(incomingEvent);
  if (!incomingEventId) {
    return {
      events: [...existingEvents, incomingEvent],
      dedupDropped: false,
    };
  }

  const duplicated = existingEvents.some((eventItem) => resolveResultEventId(eventItem) === incomingEventId);
  if (duplicated) {
    return {
      events: existingEvents,
      dedupDropped: true,
    };
  }

  return {
    events: [...existingEvents, incomingEvent],
    dedupDropped: false,
  };
}

export function resultEventsAccumulator(
  existingEvents: ResultEventData[],
  incomingEvent: ResultEventData,
): { events: ResultEventData[]; dedupDropped: boolean } {
  const deduped = dedupByEventId(existingEvents, incomingEvent);
  if (deduped.dedupDropped) {
    return deduped;
  }

  const sortedEvents = [...deduped.events].sort((left, right) => {
    const leftSequence = resolveResultSequence(left);
    const rightSequence = resolveResultSequence(right);

    if (leftSequence === undefined || rightSequence === undefined) {
      return 0;
    }
    if (leftSequence === rightSequence) {
      return 0;
    }
    return leftSequence - rightSequence;
  });

  return {
    events: sortedEvents,
    dedupDropped: false,
  };
}
