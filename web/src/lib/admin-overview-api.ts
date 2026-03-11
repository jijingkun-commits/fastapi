/**
 * 管理后台总览 API 客户端。
 */

import { apiFetch } from "@/lib/backend";
import type {
  AdminOverviewAlertItem,
  AdminOverviewCardStatus,
  AdminOverviewFreshness,
  AdminOverviewHealthLevel,
  AdminOverviewModuleItem,
  AdminOverviewQuestionHealth,
  AdminOverviewRealtimeStatus,
  AdminOverviewRequestQuality,
  AdminOverviewSeverity,
  AdminOverviewSnapshot,
  AdminOverviewSnapshotPatch,
  AdminOverviewStreamDoneEvent,
  AdminOverviewStreamEvent,
  AdminOverviewStreamInterruptEvent,
  AdminOverviewStreamResultEvent,
  AdminOverviewTrendPoint,
  AdminOverviewTrendSeries,
  AdminOverviewTrendsResponse,
  AdminOverviewTrendWindow,
  DeepPartial,
} from "@/types/admin-overview";

const API_BASE = "/api/v1/admin-overview";

export const ADMIN_OVERVIEW_POLLING_INTERVAL_MS = 10_000;

interface StreamCallbacks {
  onResult?: (event: AdminOverviewStreamResultEvent) => void;
  onInterrupt?: (event: AdminOverviewStreamInterruptEvent) => void;
  onDone?: (event: AdminOverviewStreamDoneEvent) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
}

interface StreamOptions extends StreamCallbacks {
  signal?: AbortSignal;
}

interface ParsedSSEEvent {
  type: string;
  data: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return isRecord(value) && !Array.isArray(value);
}

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function toStringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function normalizeHealthLevel(value: unknown): AdminOverviewHealthLevel {
  if (value === "healthy" || value === "warning" || value === "critical") {
    return value;
  }
  return "unknown";
}

function normalizeCardStatus(value: unknown): AdminOverviewCardStatus {
  if (value === "ok" || value === "no_data" || value === "stale" || value === "degraded") {
    return value;
  }
  return "unknown";
}

function normalizeSeverity(value: unknown): AdminOverviewSeverity {
  if (value === "critical" || value === "warning" || value === "info") {
    return value;
  }
  return "warning";
}

function normalizeTrendWindow(value: unknown): AdminOverviewTrendWindow | null {
  if (value === "1h" || value === "24h") {
    return value;
  }
  return null;
}

function nowIsoString(): string {
  return new Date().toISOString();
}

function normalizeStatusMeta(raw: unknown) {
  const data = isRecord(raw) ? raw : {};

  return {
    status: normalizeCardStatus(data.status),
    health_level: normalizeHealthLevel(data.health_level),
    sample_count: toNumber(data.sample_count),
    watermark_at: data.watermark_at == null ? null : toStringValue(data.watermark_at),
    data_source: toStringValue(data.data_source || data.source) || undefined,
    explain: toStringValue(data.explain) || undefined,
    window_sec: toNumber(data.window_sec),
  };
}

function normalizeRequestQuality(raw: unknown): AdminOverviewRequestQuality {
  const data = isRecord(raw) ? raw : {};

  return {
    ...normalizeStatusMeta(data),
    score: toNumber(data.score),
    request_total: toNumber(data.request_total),
    success_rate: toNumber(data.success_rate),
    error_4xx_rate: toNumber(data.error_4xx_rate),
    error_5xx_rate: toNumber(data.error_5xx_rate),
    latency_p95_ms: toNumber(data.latency_p95_ms),
    qps: toNumber(data.qps),
  };
}

function normalizeQuestionHealth(raw: unknown): AdminOverviewQuestionHealth {
  const data = isRecord(raw) ? raw : {};

  return {
    ...normalizeStatusMeta(data),
    score: toNumber(data.score),
    question_total: toNumber(data.question_total),
    question_success_rate: toNumber(data.question_success_rate),
    question_latency_p95_ms: toNumber(data.question_latency_p95_ms),
    question_qps: toNumber(data.question_qps),
  };
}

function normalizeAlerts(raw: unknown): AdminOverviewAlertItem[] {
  if (!Array.isArray(raw)) {
    return [];
  }

  return raw.filter(isRecord).map((item, index) => ({
    code: toStringValue(item.code, `alert_${index}`),
    severity: normalizeSeverity(item.severity),
    message: toStringValue(item.message, "总览告警"),
    module: toStringValue(item.module) || undefined,
    status: toStringValue(item.status) || undefined,
  }));
}

function normalizeFreshness(raw: unknown): AdminOverviewFreshness {
  const data = isRecord(raw) ? raw : {};
  const status = data.status === "fresh" || data.status === "stale" ? data.status : "unknown";

  return {
    status,
    score: toNumber(data.score),
    health_level: normalizeHealthLevel(data.health_level),
    delay_sec: toNumber(data.delay_sec),
    expired: Boolean(data.expired),
    max_delay_sec: toNumber(data.max_delay_sec),
    source: toStringValue(data.source) || undefined,
  };
}

function normalizeModuleMatrix(raw: unknown): AdminOverviewModuleItem[] {
  if (!Array.isArray(raw)) {
    return [];
  }

  return raw.filter(isRecord).map((item, index) => ({
    key: toStringValue(item.key, `module_${index}`),
    label: toStringValue(item.label, `模块 ${index + 1}`),
    health_level: normalizeHealthLevel(item.health_level),
    score: toNumber(item.score),
    error_rate: toNumber(item.error_rate),
    latency_p95_ms: toNumber(item.latency_p95_ms),
    data_delay_sec: toNumber(item.data_delay_sec),
  }));
}

function normalizeSummaryPayload(raw: unknown): AdminOverviewSnapshot {
  const payload = isRecord(raw)
    ? isRecord(raw.snapshot)
      ? raw.snapshot
      : isRecord(raw.data)
        ? raw.data
        : raw
    : {};

  const snapshotAt = toStringValue(payload.snapshot_at, nowIsoString());

  return {
    snapshot_at: snapshotAt,
    source: toStringValue(payload.source, "unknown"),
    degraded: Boolean(payload.degraded),
    request_quality: normalizeRequestQuality(payload.request_quality),
    question_health: normalizeQuestionHealth(payload.question_health),
    alerts: normalizeAlerts(payload.alerts),
    freshness: normalizeFreshness(payload.freshness),
    module_matrix: normalizeModuleMatrix(payload.module_matrix),
    meta: {
      generated_at: isRecord(payload.meta)
        ? toStringValue(payload.meta.generated_at, snapshotAt)
        : snapshotAt,
      trace_id: isRecord(payload.meta) ? toStringValue(payload.meta.trace_id) || undefined : undefined,
      fallback_reason: isRecord(payload.meta)
        ? toStringValue(payload.meta.fallback_reason) || undefined
        : undefined,
    },
  };
}

function normalizeTrendPoint(raw: unknown): AdminOverviewTrendPoint | null {
  if (!isRecord(raw)) {
    return null;
  }

  const timestamp = toStringValue(raw.timestamp || raw.snapshot_at || raw.time);
  if (!timestamp) {
    return null;
  }

  return {
    timestamp,
    request_qps: toNumber(raw.request_qps || raw.qps),
    question_qps: toNumber(raw.question_qps),
  };
}

function normalizeTrendSeries(raw: unknown, fallbackWindow: AdminOverviewTrendWindow): AdminOverviewTrendSeries {
  const payload = isRecord(raw)
    ? isRecord(raw.data)
      ? raw.data
      : raw
    : {};

  const window = normalizeTrendWindow(payload.window) ?? fallbackWindow;
  const pointsSource = Array.isArray(payload.points) ? payload.points : [];
  const points = pointsSource
    .map(normalizeTrendPoint)
    .filter((item): item is AdminOverviewTrendPoint => item !== null);

  return { window, points };
}

function buildEmptyTrends(): AdminOverviewTrendsResponse {
  return {
    windows: {
      "1h": [],
      "24h": [],
    },
    snapshot_at: nowIsoString(),
  };
}

function normalizeTrendsPayload(raw: unknown): AdminOverviewTrendsResponse {
  const payload: Record<string, unknown> = isRecord(raw)
    ? isRecord(raw.data)
      ? raw.data
      : raw
    : {};

  const result = buildEmptyTrends();
  result.snapshot_at = toStringValue(payload.snapshot_at, nowIsoString());

  const windowsMap = isRecord(payload.windows)
    ? (payload.windows as Record<string, unknown>)
    : null;
  if (windowsMap) {
    Object.keys(windowsMap).forEach((windowKey) => {
      const normalizedWindow = normalizeTrendWindow(windowKey);
      if (!normalizedWindow) {
        return;
      }

      const source = windowsMap[windowKey];
      const points = Array.isArray(source)
        ? source.map(normalizeTrendPoint).filter((point): point is AdminOverviewTrendPoint => point !== null)
        : [];
      result.windows[normalizedWindow] = points;
    });
    return result;
  }

  const window = normalizeTrendWindow(payload.window);
  if (window) {
    const series = normalizeTrendSeries(payload, window);
    result.windows[series.window] = series.points;
  }

  return result;
}

function parseSSEEvents(buffer: string): {
  events: ParsedSSEEvent[];
  restBuffer: string;
} {
  const chunks = buffer.split("\n\n");
  const restBuffer = chunks.pop() ?? "";
  const events: ParsedSSEEvent[] = [];

  for (const chunk of chunks) {
    const lines = chunk.split("\n");
    let eventType: string | null = null;
    const dataLines: string[] = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim();
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (!eventType || dataLines.length === 0) {
      continue;
    }

    try {
      events.push({
        type: eventType,
        data: JSON.parse(dataLines.join("\n")),
      });
    } catch {
      continue;
    }
  }

  return { events, restBuffer };
}

function normalizeStreamEvent(rawEvent: ParsedSSEEvent): AdminOverviewStreamEvent | null {
  if (rawEvent.type === "result" && isRecord(rawEvent.data)) {
    const patch = isPlainRecord(rawEvent.data.patch)
      ? (rawEvent.data.patch as AdminOverviewSnapshotPatch)
      : {};

    return {
      type: "result",
      data: {
        snapshot_at: toStringValue(rawEvent.data.snapshot_at, nowIsoString()),
        patch,
        trace_id: toStringValue(rawEvent.data.trace_id) || undefined,
      },
      node: toStringValue(rawEvent.data.node) || undefined,
    };
  }

  if (rawEvent.type === "interrupt" && isRecord(rawEvent.data)) {
    return {
      type: "interrupt",
      data: {
        reason: toStringValue(rawEvent.data.reason, "stream_interrupted"),
        level: normalizeSeverity(rawEvent.data.level),
        retry_after_sec: toNumber(rawEvent.data.retry_after_sec) ?? undefined,
        message: toStringValue(rawEvent.data.message) || undefined,
      },
      node: toStringValue(rawEvent.data.node) || undefined,
    };
  }

  if (rawEvent.type === "done" && isRecord(rawEvent.data)) {
    return {
      type: "done",
      data: {
        batch_id: toStringValue(rawEvent.data.batch_id, "batch_unknown"),
        final: typeof rawEvent.data.final === "boolean" ? rawEvent.data.final : undefined,
      },
      node: toStringValue(rawEvent.data.node) || undefined,
    };
  }

  return null;
}

function deepMerge<T>(target: T, patch: DeepPartial<T>): T {
  if (Array.isArray(patch)) {
    return patch as T;
  }

  if (!isPlainRecord(target) || !isPlainRecord(patch)) {
    return patch as T;
  }

  const merged: Record<string, unknown> = { ...target };
  for (const key of Object.keys(patch)) {
    const nextValue = patch[key as keyof typeof patch];
    if (nextValue === undefined) {
      continue;
    }

    const previousValue = merged[key];
    if (Array.isArray(nextValue)) {
      merged[key] = nextValue;
      continue;
    }

    if (isPlainRecord(previousValue) && isPlainRecord(nextValue)) {
      merged[key] = deepMerge(previousValue, nextValue);
      continue;
    }

    merged[key] = nextValue;
  }

  return merged as T;
}

export function mergeAdminOverviewSnapshot(
  current: AdminOverviewSnapshot,
  patch: AdminOverviewSnapshotPatch,
  snapshotAt?: string,
): AdminOverviewSnapshot {
  const merged = deepMerge(current, patch);
  if (snapshotAt) {
    merged.snapshot_at = snapshotAt;
  }
  return normalizeSummaryPayload(merged);
}

export function buildEmptyAdminOverviewSnapshot(snapshotAt = nowIsoString()): AdminOverviewSnapshot {
  return normalizeSummaryPayload({
    snapshot_at: snapshotAt,
    source: "empty",
    degraded: true,
    request_quality: {
      status: "unknown",
      health_level: "unknown",
      score: null,
      request_total: null,
      success_rate: null,
      error_4xx_rate: null,
      error_5xx_rate: null,
      latency_p95_ms: null,
      qps: null,
      sample_count: null,
      watermark_at: null,
      data_source: "empty",
      explain: "暂无业务样本",
      window_sec: null,
    },
    question_health: {
      status: "unknown",
      health_level: "unknown",
      score: null,
      question_total: null,
      question_success_rate: null,
      question_latency_p95_ms: null,
      question_qps: null,
      sample_count: null,
      watermark_at: null,
      data_source: "empty",
      explain: "暂无用户提问样本",
      window_sec: null,
    },
    alerts: [],
    freshness: {
      status: "unknown",
      score: null,
      health_level: "unknown",
      delay_sec: null,
      expired: false,
      max_delay_sec: null,
      source: "empty",
    },
    module_matrix: [],
    meta: {
      generated_at: snapshotAt,
    },
  });
}

export async function getAdminOverviewSummary(signal?: AbortSignal): Promise<AdminOverviewSnapshot> {
  const response = await apiFetch(`${API_BASE}/summary`, { signal });
  if (!response.ok) {
    throw new Error("获取总览快照失败");
  }

  const payload = await response.json().catch(() => ({}));
  return normalizeSummaryPayload(payload);
}

async function getAdminOverviewTrendWindow(
  window: AdminOverviewTrendWindow,
  signal?: AbortSignal,
): Promise<AdminOverviewTrendSeries> {
  const response = await apiFetch(`${API_BASE}/trends?window=${window}`, { signal });
  if (!response.ok) {
    throw new Error(`获取 ${window} 趋势失败`);
  }

  const payload = await response.json().catch(() => ({}));
  return normalizeTrendSeries(payload, window);
}

export async function getAdminOverviewTrends(signal?: AbortSignal): Promise<AdminOverviewTrendsResponse> {
  const response = await apiFetch(`${API_BASE}/trends`, { signal });
  if (response.ok) {
    const payload = await response.json().catch(() => ({}));
    const normalized = normalizeTrendsPayload(payload);
    if (normalized.windows["1h"].length > 0 || normalized.windows["24h"].length > 0) {
      return normalized;
    }
  }

  const [trend1h, trend24h] = await Promise.all([
    getAdminOverviewTrendWindow("1h", signal),
    getAdminOverviewTrendWindow("24h", signal),
  ]);

  return {
    windows: {
      "1h": trend1h.points,
      "24h": trend24h.points,
    },
    snapshot_at:
      trend24h.points.at(-1)?.timestamp || trend1h.points.at(-1)?.timestamp || nowIsoString(),
  };
}

export async function streamAdminOverview(options: StreamOptions = {}): Promise<void> {
  const { signal, onOpen, onResult, onInterrupt, onDone, onError } = options;

  const response = await apiFetch(`${API_BASE}/stream`, {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
    },
    signal,
  });

  if (!response.ok || !response.body) {
    const error = new Error("建立总览实时连接失败");
    onError?.(error);
    throw error;
  }

  onOpen?.();

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        buffer += decoder.decode();
      } else {
        buffer += decoder.decode(value, { stream: true });
      }

      const parseTarget = done && buffer.trim().length > 0 ? `${buffer}

` : buffer;
      const { events, restBuffer } = parseSSEEvents(parseTarget);
      buffer = done ? "" : restBuffer;

      for (const rawEvent of events) {
        const event = normalizeStreamEvent(rawEvent);
        if (!event) {
          continue;
        }

        if (event.type === "result") {
          onResult?.(event);
          continue;
        }

        if (event.type === "interrupt") {
          onInterrupt?.(event);
          continue;
        }

        if (event.type === "done") {
          onDone?.(event);
        }
      }

      if (done) {
        break;
      }
    }
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      return;
    }

    const normalized = error instanceof Error ? error : new Error("总览实时流读取失败");
    onError?.(normalized);
    throw normalized;
  }
}

export function buildRealtimeStatus(
  mode: AdminOverviewRealtimeStatus["mode"],
  message: string,
  extras: Partial<Omit<AdminOverviewRealtimeStatus, "mode" | "message" | "updatedAt">> = {},
): AdminOverviewRealtimeStatus {
  return {
    mode,
    message,
    reason: extras.reason,
    retryAfterSec: extras.retryAfterSec,
    updatedAt: nowIsoString(),
  };
}
