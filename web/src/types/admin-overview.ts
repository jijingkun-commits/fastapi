/**
 * 管理后台总览驾驶舱类型定义。
 */

export type AdminOverviewHealthLevel =
  | "healthy"
  | "warning"
  | "critical"
  | "unknown";

export type AdminOverviewSeverity = "critical" | "warning" | "info";

export type AdminOverviewCardStatus = "ok" | "no_data" | "stale" | "degraded" | "unknown";

export type AdminOverviewFreshnessStatus = "fresh" | "stale" | "unknown";

export type AdminOverviewRealtimeMode =
  | "connecting"
  | "streaming"
  | "polling"
  | "error";

export interface AdminOverviewNumericSignal {
  value: number | null;
  score: number | null;
  level: AdminOverviewHealthLevel;
}

export interface AdminOverviewStatusMeta {
  status: AdminOverviewCardStatus;
  health_level: AdminOverviewHealthLevel;
  sample_count?: number | null;
  watermark_at?: string | null;
  data_source?: string;
  explain?: string;
  window_sec?: number | null;
}

export type AdminOverviewSystemStatus = AdminOverviewStatusMeta;

export type AdminOverviewTrafficHealth = AdminOverviewStatusMeta;

export interface AdminOverviewRequestQuality extends AdminOverviewStatusMeta {
  score: number | null;
  request_total: number | null;
  success_rate: number | null;
  error_4xx_rate: number | null;
  error_5xx_rate: number | null;
  latency_p95_ms: number | null;
  qps: number | null;
}

export interface AdminOverviewQuestionActivity extends AdminOverviewStatusMeta {
  score: number | null;
  question_total: number | null;
  question_success_rate: number | null;
  question_latency_p95_ms: number | null;
  question_qps: number | null;
  stream_interrupt_rate: number | null;
}

export interface AdminOverviewStability {
  status: AdminOverviewCardStatus;
  health_level: AdminOverviewHealthLevel;
  score: number | null;
  critical_alerts: number | null;
  warning_alerts: number | null;
  module_score?: number | null;
}

export interface AdminOverviewCapacityCost extends AdminOverviewStatusMeta {
  score: number | null;
  qps: number | null;
  question_qps: number | null;
  cost_per_minute: number | null;
  budget_per_minute: number | null;
  budget_usage_pct: number | null;
}

export interface AdminOverviewAlertItem {
  code: string;
  severity: AdminOverviewSeverity;
  message: string;
  module?: string | null;
  status?: string;
}

export interface AdminOverviewFreshness {
  status: AdminOverviewFreshnessStatus;
  score: number | null;
  health_level: AdminOverviewHealthLevel;
  delay_sec: number | null;
  expired: boolean;
  max_delay_sec: number | null;
  source?: string;
}

export interface AdminOverviewModuleItem {
  key: string;
  label: string;
  health_level: AdminOverviewHealthLevel;
  score: number | null;
  error_rate: number | null;
  latency_p95_ms: number | null;
  data_delay_sec: number | null;
}

export interface AdminOverviewChangeItem {
  id: string;
  title: string;
  level: AdminOverviewSeverity;
  occurred_at: string;
}

export interface AdminOverviewMeta {
  generated_at: string;
  trace_id?: string | null;
  fallback_reason?: string;
}

export interface AdminOverviewSnapshot {
  snapshot_at: string;
  source: string;
  degraded: boolean;
  system_status: AdminOverviewSystemStatus;
  traffic_health: AdminOverviewTrafficHealth;
  health_score: number | null;
  health_level: AdminOverviewHealthLevel;
  budget_usage_pct: number | null;
  request_quality: AdminOverviewRequestQuality;
  question_activity: AdminOverviewQuestionActivity;
  stability: AdminOverviewStability;
  capacity_cost: AdminOverviewCapacityCost;
  alerts: AdminOverviewAlertItem[];
  freshness: AdminOverviewFreshness;
  module_matrix: AdminOverviewModuleItem[];
  change_feed: AdminOverviewChangeItem[];
  meta: AdminOverviewMeta;
}

export interface AdminOverviewTrendPoint {
  timestamp: string;
  health_score?: number | null;
  request_qps?: number | null;
  question_qps?: number | null;
  budget_usage_pct?: number | null;
}

export type AdminOverviewTrendWindow = "1h" | "24h";

export interface AdminOverviewTrendSeries {
  window: AdminOverviewTrendWindow;
  points: AdminOverviewTrendPoint[];
}

export interface AdminOverviewTrendsResponse {
  windows: Record<AdminOverviewTrendWindow, AdminOverviewTrendPoint[]>;
  snapshot_at?: string;
}

export interface AdminOverviewStreamResultEvent {
  type: "result";
  data: {
    snapshot_at: string;
    patch: AdminOverviewSnapshotPatch;
    trace_id?: string;
  };
  node?: string;
}

export interface AdminOverviewStreamInterruptEvent {
  type: "interrupt";
  data: {
    reason: string;
    level: AdminOverviewSeverity;
    retry_after_sec?: number;
    message?: string;
  };
  node?: string;
}

export interface AdminOverviewStreamDoneEvent {
  type: "done";
  data: {
    batch_id: string;
    final?: boolean;
  };
  node?: string;
}

export type AdminOverviewStreamEvent =
  | AdminOverviewStreamResultEvent
  | AdminOverviewStreamInterruptEvent
  | AdminOverviewStreamDoneEvent;

export type DeepPartial<T> = T extends (infer U)[]
  ? DeepPartial<U>[]
  : T extends object
    ? { [K in keyof T]?: DeepPartial<T[K]> }
    : T;

export type AdminOverviewSnapshotPatch = DeepPartial<AdminOverviewSnapshot>;

export interface AdminOverviewRealtimeStatus {
  mode: AdminOverviewRealtimeMode;
  reason?: string;
  message: string;
  retryAfterSec?: number;
  updatedAt: string;
}
