"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type ReactNode,
} from "react";
import Link from "next/link";
import {
  Activity,
  ArrowUpRight,
  DatabaseZap,
  MessageSquare,
  RefreshCcw,
  Siren,
  Timer,
  TrendingUp,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";

import {
  ADMIN_OVERVIEW_POLLING_INTERVAL_MS,
  buildEmptyAdminOverviewSnapshot,
  buildRealtimeStatus,
  getAdminOverviewSummary,
  getAdminOverviewTrends,
  mergeAdminOverviewSnapshot,
  streamAdminOverview,
} from "@/lib/admin-overview-api";
import { cn } from "@/lib/utils";
import type {
  AdminOverviewCardStatus,
  AdminOverviewHealthLevel,
  AdminOverviewRealtimeStatus,
  AdminOverviewSeverity,
  AdminOverviewSnapshot,
  AdminOverviewTrendsResponse,
} from "@/types/admin-overview";
import { Button } from "@/components/ui/button";
import { ViewState } from "@/components/ui/view-state";

type ViewStateType = "loading" | "ready" | "error";

const MODULE_ROUTE_MAP: Record<string, string> = {
  admin_overview: "/admin",
  access: "/admin/access",
  llm: "/admin/llm",
  skill: "/admin/skills",
  system: "/admin/system",
  data: "/admin/data",
  memory: "/admin/memory",
  user: "/admin/users",
};

const CARD_STATUS_META: Record<
  AdminOverviewCardStatus,
  { label: string; badgeClass: string }
> = {
  ok: {
    label: "正常",
    badgeClass:
      "border-emerald-200/80 bg-emerald-500/10 text-emerald-700 dark:border-emerald-500/30 dark:text-emerald-300",
  },
  no_data: {
    label: "无样本",
    badgeClass:
      "border-slate-200/80 bg-slate-500/10 text-slate-700 dark:border-slate-500/30 dark:text-slate-300",
  },
  stale: {
    label: "已陈旧",
    badgeClass:
      "border-amber-200/80 bg-amber-500/10 text-amber-700 dark:border-amber-500/30 dark:text-amber-300",
  },
  degraded: {
    label: "已降级",
    badgeClass:
      "border-rose-200/80 bg-rose-500/10 text-rose-700 dark:border-rose-500/30 dark:text-rose-300",
  },
  unknown: {
    label: "未知",
    badgeClass:
      "border-slate-200/80 bg-slate-500/10 text-slate-700 dark:border-slate-500/30 dark:text-slate-300",
  },
};

const HEALTH_LEVEL_META: Record<
  AdminOverviewHealthLevel,
  { label: string; textClass: string }
> = {
  healthy: {
    label: "健康",
    textClass: "text-emerald-700 dark:text-emerald-300",
  },
  warning: {
    label: "预警",
    textClass: "text-amber-700 dark:text-amber-300",
  },
  critical: {
    label: "严重",
    textClass: "text-rose-700 dark:text-rose-300",
  },
  unknown: {
    label: "未知",
    textClass: "text-slate-700 dark:text-slate-300",
  },
};

const SEVERITY_META: Record<
  AdminOverviewSeverity,
  { label: string; badgeClass: string; dotClass: string }
> = {
  critical: {
    label: "严重",
    badgeClass:
      "border-rose-200/80 bg-rose-500/10 text-rose-700 dark:border-rose-500/30 dark:text-rose-300",
    dotClass: "bg-rose-500",
  },
  warning: {
    label: "预警",
    badgeClass:
      "border-amber-200/80 bg-amber-500/10 text-amber-700 dark:border-amber-500/30 dark:text-amber-300",
    dotClass: "bg-amber-500",
  },
  info: {
    label: "提示",
    badgeClass:
      "border-sky-200/80 bg-sky-500/10 text-sky-700 dark:border-sky-500/30 dark:text-sky-300",
    dotClass: "bg-sky-500",
  },
};

function toNumericValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: digits === 0 ? 0 : Math.min(digits, 2),
    maximumFractionDigits: digits,
  });
}

function formatRatioPercent(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  return `${(value * 100).toFixed(digits)}%`;
}

function formatLatency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  return `${formatNumber(value, 0)} ms`;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "--";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }

  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatTimeLabel(value: string | null | undefined): string {
  if (!value) {
    return "--";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }

  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

const DEFAULT_CARD_STATE_TEXT: Record<AdminOverviewCardStatus, string> = {
  ok: "正常",
  no_data: "无样本",
  stale: "使用旧快照",
  degraded: "降级中",
  unknown: "未知",
};

function describeCardState(
  status: AdminOverviewCardStatus,
  overrides: Partial<Record<AdminOverviewCardStatus, string>> = {},
): string {
  return overrides[status] ?? DEFAULT_CARD_STATE_TEXT[status];
}

function withCardStateFallback(
  value: string,
  status: AdminOverviewCardStatus,
  overrides: Partial<Record<AdminOverviewCardStatus, string>> = {},
): string {
  return value === "--" ? describeCardState(status, overrides) : value;
}

function resolveFreshnessCardStatus(snapshot: AdminOverviewSnapshot): AdminOverviewCardStatus {
  const delay = snapshot.freshness.delay_sec;
  const maxDelay = snapshot.freshness.max_delay_sec;

  if (snapshot.freshness.status === "stale" || snapshot.freshness.expired) {
    return "stale";
  }

  if (delay != null && maxDelay != null && delay > maxDelay) {
    return "stale";
  }

  if (snapshot.freshness.status === "fresh") {
    return "ok";
  }

  return "unknown";
}

function formatFreshnessStatus(status: AdminOverviewSnapshot["freshness"]["status"]): string {
  if (status === "fresh") {
    return "新鲜";
  }

  if (status === "stale") {
    return "陈旧";
  }

  return "未知";
}

function sanitizeTestIdSegment(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}

function resolveModuleRoute(moduleKey?: string | null): string | null {
  if (!moduleKey) {
    return null;
  }

  return MODULE_ROUTE_MAP[moduleKey.trim().toLowerCase()] ?? null;
}

function hasRealSnapshot(snapshot: AdminOverviewSnapshot): boolean {
  return snapshot.source !== "empty" || snapshot.alerts.length > 0 || snapshot.module_matrix.length > 0;
}

function computeRealtimeBadgeMeta(status: AdminOverviewRealtimeStatus): {
  className: string;
  dotClass: string;
  label: string;
} {
  if (status.mode === "streaming") {
    return {
      className:
        "border-emerald-200/80 bg-emerald-500/10 text-emerald-700 dark:border-emerald-500/30 dark:text-emerald-300",
      dotClass: "bg-emerald-500",
      label: "实时流在线",
    };
  }

  if (status.mode === "polling") {
    return {
      className:
        "border-amber-200/80 bg-amber-500/10 text-amber-700 dark:border-amber-500/30 dark:text-amber-300",
      dotClass: "bg-amber-500",
      label: "轮询降级中",
    };
  }

  if (status.mode === "error") {
    return {
      className:
        "border-rose-200/80 bg-rose-500/10 text-rose-700 dark:border-rose-500/30 dark:text-rose-300",
      dotClass: "bg-rose-500",
      label: "实时链路异常",
    };
  }

  return {
    className:
      "border-slate-200/80 bg-slate-500/10 text-slate-700 dark:border-slate-500/30 dark:text-slate-300",
    dotClass: "bg-slate-500",
    label: "实时连接中",
  };
}

function RealtimeBadge({ status }: { status: AdminOverviewRealtimeStatus }) {
  const meta = computeRealtimeBadgeMeta(status);

  return (
    <div
      data-testid="admin-overview-realtime-status"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
        meta.className,
      )}
      title={`${status.message}（更新时间: ${formatDateTime(status.updatedAt)}）`}
    >
      <span className={cn("h-2 w-2 rounded-full", meta.dotClass)} />
      <span>{meta.label}</span>
    </div>
  );
}

function StateBadge({ status }: { status: AdminOverviewCardStatus }) {
  const meta = CARD_STATUS_META[status];

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
        meta.badgeClass,
      )}
    >
      {meta.label}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: AdminOverviewSeverity }) {
  const meta = SEVERITY_META[severity];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        meta.badgeClass,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", meta.dotClass)} />
      <span>{meta.label}</span>
    </span>
  );
}

function OverviewCard({
  title,
  subtitle,
  icon: Icon,
  testId,
  className,
  children,
}: {
  title: string;
  subtitle: string;
  icon: ComponentType<{ className?: string }>;
  testId?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      data-testid={testId}
      className={cn("admin-surface h-full p-4", className)}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-[var(--color-brand-700)]" />
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-dashed border-border/60 py-2 last:border-b-0 last:pb-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xs font-medium text-foreground">{value}</span>
    </div>
  );
}

function TrafficTrendChart({ trends }: { trends: AdminOverviewTrendsResponse }) {
  const data = useMemo(() => {
    return trends.windows["24h"].map((point) => ({
      label: formatTimeLabel(point.timestamp),
      request: point.request_qps,
      question: point.question_qps,
    }));
  }, [trends.windows]);

  if (data.length === 0) {
    return (
      <div className="flex h-[140px] items-center justify-center rounded-lg border border-dashed border-border/70 bg-background/40 text-xs text-muted-foreground">
        暂无趋势数据
      </div>
    );
  }

  return (
    <div className="h-[140px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 6, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.35} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: "var(--color-muted-foreground)" }}
            tickLine={false}
            axisLine={false}
            minTickGap={14}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--color-muted-foreground)" }}
            tickLine={false}
            axisLine={false}
            width={34}
          />
          <Tooltip
            formatter={(value, name) => [
              `${formatNumber(toNumericValue(value), 2)} QPS`,
              name === "request" ? "全业务" : "提问",
            ]}
            labelFormatter={(label) => `时间: ${label}`}
            contentStyle={{
              borderRadius: 10,
              border: "1px solid var(--color-border)",
              background: "var(--color-card)",
              fontSize: 12,
            }}
          />
          <Line type="monotone" dataKey="request" stroke="var(--chart-2)" strokeWidth={2.2} dot={false} connectNulls />
          <Line type="monotone" dataKey="question" stroke="var(--chart-4)" strokeWidth={2.2} dot={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function CockpitSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-12" data-testid="admin-overview-skeleton">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={index}
          className={cn(
            "admin-surface animate-pulse p-4",
            index < 4 ? "xl:col-span-3" : "xl:col-span-6",
          )}
        >
          <div className="h-4 w-24 rounded bg-muted/60" />
          <div className="mt-3 h-8 w-1/2 rounded bg-muted/60" />
          <div className="mt-3 h-20 rounded bg-muted/40" />
        </div>
      ))}
    </div>
  );
}

const EMPTY_TRENDS: AdminOverviewTrendsResponse = {
  windows: {
    "1h": [],
    "24h": [],
  },
};

export function AdminOverviewCockpit() {
  const [snapshot, setSnapshot] = useState<AdminOverviewSnapshot>(() =>
    buildEmptyAdminOverviewSnapshot(),
  );
  const [trends, setTrends] = useState<AdminOverviewTrendsResponse>(EMPTY_TRENDS);
  const [viewState, setViewState] = useState<ViewStateType>("loading");
  const [loadError, setLoadError] = useState("");
  const [realtimeStatus, setRealtimeStatus] = useState<AdminOverviewRealtimeStatus>(() =>
    buildRealtimeStatus("connecting", "正在加载总览数据..."),
  );

  const streamAbortRef = useRef<AbortController | null>(null);
  const pollingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
  }, []);

  const stopStream = useCallback(() => {
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
      streamAbortRef.current = null;
    }
  }, []);

  const pollSummary = useCallback(async () => {
    try {
      const nextSnapshot = await getAdminOverviewSummary();
      setSnapshot(nextSnapshot);
      setViewState("ready");
      setLoadError("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "轮询刷新失败";
      setLoadError(message);
      setRealtimeStatus(
        buildRealtimeStatus("error", "轮询刷新失败，已保留最近快照", {
          reason: "polling_error",
        }),
      );
    }
  }, []);

  const startPolling = useCallback(
    (params?: { reason?: string; message?: string; retryAfterSec?: number }) => {
      stopStream();
      stopPolling();

      setRealtimeStatus(
        buildRealtimeStatus(
          "polling",
          params?.message ?? "实时连接中断，已降级为轮询刷新",
          {
            reason: params?.reason,
            retryAfterSec: params?.retryAfterSec,
          },
        ),
      );

      void pollSummary();
      pollingTimerRef.current = setInterval(() => {
        void pollSummary();
      }, ADMIN_OVERVIEW_POLLING_INTERVAL_MS);
    },
    [pollSummary, stopPolling, stopStream],
  );

  const connectStream = useCallback(() => {
    stopStream();
    const controller = new AbortController();
    streamAbortRef.current = controller;

    setRealtimeStatus(buildRealtimeStatus("connecting", "正在建立实时流连接..."));

    void streamAdminOverview({
      signal: controller.signal,
      onOpen: () => {
        setRealtimeStatus(buildRealtimeStatus("streaming", "实时流已连接"));
      },
      onResult: (event) => {
        setSnapshot((current) =>
          mergeAdminOverviewSnapshot(current, event.data.patch, event.data.snapshot_at),
        );
        setLoadError("");
        setViewState("ready");
        setRealtimeStatus(buildRealtimeStatus("streaming", "实时流在线"));
      },
      onInterrupt: (event) => {
        startPolling({
          reason: event.data.reason,
          retryAfterSec: event.data.retry_after_sec,
          message: event.data.message ?? "实时连接中断，已降级为轮询刷新",
        });
      },
      onError: (error) => {
        const message = error instanceof Error ? error.message : "实时流连接失败";
        setLoadError(message);
        startPolling({
          reason: "stream_error",
          message: "实时流连接失败，已降级为轮询刷新",
        });
      },
    });
  }, [startPolling, stopStream]);

  const bootstrap = useCallback(async () => {
    stopPolling();
    stopStream();

    try {
      const summary = await getAdminOverviewSummary();
      setSnapshot(summary);

      const trendResult = await getAdminOverviewTrends().catch(() => EMPTY_TRENDS);
      setTrends(trendResult);

      setViewState("ready");
      connectStream();
    } catch (error) {
      const message = error instanceof Error ? error.message : "总览加载失败";
      setLoadError(message);
      setViewState("error");
      setRealtimeStatus(buildRealtimeStatus("error", "总览加载失败，请稍后重试"));
    }
  }, [connectStream, stopPolling, stopStream]);

  useEffect(() => {
    void bootstrap();

    return () => {
      stopStream();
      stopPolling();
    };
  }, [bootstrap, stopPolling, stopStream]);

  const freshnessCardStatus = resolveFreshnessCardStatus(snapshot);
  const isDataStale = freshnessCardStatus === "stale";

  const realtimeMessage = useMemo(() => {
    const retryHint =
      realtimeStatus.retryAfterSec && realtimeStatus.retryAfterSec > 0
        ? `，建议 ${realtimeStatus.retryAfterSec}s 后重试`
        : "";
    return `${realtimeStatus.message}${retryHint}`;
  }, [realtimeStatus.message, realtimeStatus.retryAfterSec]);

  const handleManualRefresh = useCallback(async () => {
    try {
      const [nextSnapshot, nextTrends] = await Promise.all([
        getAdminOverviewSummary(),
        getAdminOverviewTrends().catch(() => trends),
      ]);
      setSnapshot(nextSnapshot);
      setTrends(nextTrends);
      setLoadError("");
      if (realtimeStatus.mode === "error") {
        setRealtimeStatus(
          buildRealtimeStatus("polling", "手动刷新成功，保持轮询保护", {
            reason: "manual_refresh",
          }),
        );
      }
      toast.success("总览数据已刷新");
    } catch (error) {
      const message = error instanceof Error ? error.message : "刷新失败";
      toast.error(message);
    }
  }, [realtimeStatus.mode, trends]);

  const latestUpdateAt = formatDateTime(snapshot.snapshot_at);
  const latestTrendPoint = trends.windows["24h"].at(-1);

  if (viewState === "loading") {
    return (
      <div className="admin-page-content space-y-4">
        <header>
          <h1 className="app-page-title">总览驾驶舱</h1>
          <p className="app-page-subtitle mt-1">正在准备精简后的实时运行态数据...</p>
        </header>
        <CockpitSkeleton />
      </div>
    );
  }

  if (viewState === "error" && !hasRealSnapshot(snapshot)) {
    return (
      <div className="admin-page-content space-y-4">
        <header>
          <h1 className="app-page-title">总览驾驶舱</h1>
          <p className="app-page-subtitle mt-1">实时总览暂不可用，可稍后重试</p>
        </header>
        <ViewState
          type="error"
          title="总览加载失败"
          description={loadError || "暂时无法获取管理后台总览数据。"}
          actionLabel="重新加载"
          onAction={() => {
            void bootstrap();
          }}
        />
      </div>
    );
  }

  return (
    <div className="admin-page-content space-y-4" data-testid="admin-overview-cockpit">
      <header className="space-y-2">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="app-page-title">总览驾驶舱</h1>
            <p className="app-page-subtitle mt-1">
              聚焦业务请求质量、提问链路健康与数据可信度，支持实时流 + 轮询降级。
            </p>
          </div>

          <div className="flex items-center gap-2">
            <RealtimeBadge status={realtimeStatus} />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => {
                void handleManualRefresh();
              }}
            >
              <RefreshCcw className="h-3.5 w-3.5" />
              立即刷新
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>最新快照：{latestUpdateAt}</span>
          <span className="text-muted-foreground/50">|</span>
          <span>{realtimeMessage}</span>
          {isDataStale ? (
            <span
              data-testid="admin-overview-freshness-flag"
              className="rounded-full border border-amber-300/70 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:border-amber-500/30 dark:text-amber-300"
            >
              数据已陈旧
            </span>
          ) : null}
          {loadError ? (
            <span className="rounded-full border border-rose-300/70 bg-rose-500/10 px-2 py-0.5 text-[11px] font-medium text-rose-700 dark:border-rose-500/30 dark:text-rose-300">
              最近错误：{loadError}
            </span>
          ) : null}
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-12">
        <OverviewCard
          title="业务请求质量"
          subtitle="全业务 API 请求质量"
          icon={Activity}
          testId="overview-card-request-quality"
          className="xl:col-span-3"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <div>
              <p className="text-lg font-semibold text-foreground">
                {withCardStateFallback(
                  formatNumber(snapshot.request_quality.score, 1),
                  snapshot.request_quality.status,
                  {
                    ok: "质量正常",
                    no_data: "无业务样本",
                    stale: "沿用旧值",
                    degraded: "聚合降级",
                    unknown: "状态未知",
                  },
                )}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {snapshot.request_quality.explain || "用于回答系统对外 API 质量如何。"}
              </p>
            </div>
            <StateBadge status={snapshot.request_quality.status} />
          </div>
          <MetricRow label="请求总量" value={withCardStateFallback(formatNumber(snapshot.request_quality.request_total, 0), snapshot.request_quality.status)} />
          <MetricRow label="全业务 QPS" value={withCardStateFallback(formatNumber(snapshot.request_quality.qps, 2), snapshot.request_quality.status)} />
          <MetricRow label="成功率" value={withCardStateFallback(formatRatioPercent(snapshot.request_quality.success_rate, 2), snapshot.request_quality.status)} />
          <MetricRow label="5xx 占比" value={withCardStateFallback(formatRatioPercent(snapshot.request_quality.error_5xx_rate, 2), snapshot.request_quality.status)} />
          <MetricRow label="P95 延迟" value={withCardStateFallback(formatLatency(snapshot.request_quality.latency_p95_ms), snapshot.request_quality.status)} />
        </OverviewCard>

        <OverviewCard
          title="提问链路健康"
          subtitle="聊天提问链路的健康态"
          icon={MessageSquare}
          testId="overview-card-question-health"
          className="xl:col-span-3"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <div>
              <p className="text-lg font-semibold text-foreground">
                {withCardStateFallback(
                  formatNumber(snapshot.question_health.score, 1),
                  snapshot.question_health.status,
                  {
                    ok: "链路健康",
                    no_data: "暂无提问",
                    stale: "沿用旧值",
                    degraded: "聚合降级",
                    unknown: "状态未知",
                  },
                )}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {snapshot.question_health.explain || "用于回答聊天提问链路是否可用、是否稳定。"}
              </p>
            </div>
            <StateBadge status={snapshot.question_health.status} />
          </div>
          <MetricRow label="提问次数" value={withCardStateFallback(formatNumber(snapshot.question_health.question_total, 0), snapshot.question_health.status)} />
          <MetricRow label="提问 QPS" value={withCardStateFallback(formatNumber(snapshot.question_health.question_qps, 2), snapshot.question_health.status)} />
          <MetricRow label="成功率" value={withCardStateFallback(formatRatioPercent(snapshot.question_health.question_success_rate, 2), snapshot.question_health.status)} />
          <MetricRow label="P95 延迟" value={withCardStateFallback(formatLatency(snapshot.question_health.question_latency_p95_ms), snapshot.question_health.status)} />
        </OverviewCard>

        <OverviewCard
          title="数据新鲜度"
          subtitle="快照延迟与陈旧判定"
          icon={Timer}
          testId="overview-card-freshness"
          className="xl:col-span-3"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <div>
              <p className="text-lg font-semibold text-foreground">
                {withCardStateFallback(
                  snapshot.freshness.delay_sec == null
                    ? "--"
                    : `${formatNumber(snapshot.freshness.delay_sec, 0)} s`,
                  freshnessCardStatus,
                  {
                    ok: "新鲜",
                    no_data: "暂无快照",
                    stale: "快照陈旧",
                    degraded: "聚合降级",
                    unknown: "状态未知",
                  },
                )}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">用于判断当前快照是否仍然可信。</p>
            </div>
            <StateBadge status={freshnessCardStatus} />
          </div>
          <MetricRow label="当前状态" value={formatFreshnessStatus(snapshot.freshness.status)} />
          <MetricRow label="陈旧阈值" value={snapshot.freshness.max_delay_sec == null ? "暂无阈值" : `${formatNumber(snapshot.freshness.max_delay_sec, 0)} s`} />
          <MetricRow label="来源" value={snapshot.freshness.source || "未知"} />
          <MetricRow label="快照时间" value={latestUpdateAt} />
        </OverviewCard>

        <OverviewCard
          title="告警概览"
          subtitle="当前最值得处理的异常"
          icon={Siren}
          testId="overview-card-alerts"
          className="xl:col-span-3"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <div>
              <p className="text-lg font-semibold text-foreground">
                {snapshot.alerts.length > 0 ? `${snapshot.alerts.length} 条告警` : "当前无告警"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">只展示可动作的实时告警，不再混入空占位变更流。</p>
            </div>
            {snapshot.alerts[0] ? <SeverityBadge severity={snapshot.alerts[0].severity} /> : <StateBadge status="no_data" />}
          </div>
          {snapshot.alerts.length === 0 ? (
            <div className="flex min-h-[144px] items-center justify-center rounded-lg border border-dashed border-border/70 bg-background/40 text-sm text-muted-foreground">
              当前无告警
            </div>
          ) : (
            <div className="space-y-2">
              {snapshot.alerts.slice(0, 3).map((alert, index) => {
                const alertHref = resolveModuleRoute(alert.module);
                return (
                  <div key={`${alert.code}-${index}`} className="rounded-lg border border-border/70 bg-background/60 p-2.5">
                    <div className="mb-1.5 flex items-center justify-between gap-2">
                      <SeverityBadge severity={alert.severity} />
                      <span className="text-[11px] text-muted-foreground">{alert.code}</span>
                    </div>
                    <p className="text-sm text-foreground">{alert.message}</p>
                    {alertHref ? (
                      <Link
                        href={alertHref}
                        data-testid={`overview-alert-link-${index}`}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-[var(--color-brand-700)] hover:underline"
                      >
                        查看模块
                        <ArrowUpRight className="h-3 w-3" />
                      </Link>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </OverviewCard>

        <OverviewCard
          title="模块健康矩阵"
          subtitle="按模块聚合的健康态与跳转"
          icon={DatabaseZap}
          testId="overview-card-module-matrix"
          className="xl:col-span-6"
        >
          {snapshot.module_matrix.length === 0 ? (
            <div className="flex h-full min-h-[164px] items-center justify-center rounded-lg border border-dashed border-border/70 bg-background/40 text-sm text-muted-foreground">
              暂无模块健康样本
            </div>
          ) : (
            <div className="grid gap-2 md:grid-cols-2">
              {snapshot.module_matrix.slice(0, 6).map((moduleItem) => {
                const moduleHref = resolveModuleRoute(moduleItem.key);
                const moduleLevelMeta = HEALTH_LEVEL_META[moduleItem.health_level];
                const moduleTestId = `overview-module-link-${sanitizeTestIdSegment(moduleItem.key)}`;

                return (
                  <div key={moduleItem.key} className="rounded-lg border border-border/70 bg-background/60 p-2.5">
                    <div className="mb-1.5 flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-foreground">{moduleItem.label}</p>
                        <p className={cn("mt-0.5 text-[11px]", moduleLevelMeta.textClass)}>{moduleLevelMeta.label}</p>
                      </div>
                      <span className={cn("text-xs font-medium", moduleLevelMeta.textClass)}>
                        {formatNumber(moduleItem.score, 1)}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-[11px] text-muted-foreground">
                      <div>错误率 {formatRatioPercent(moduleItem.error_rate, 2)}</div>
                      <div>P95 {formatLatency(moduleItem.latency_p95_ms)}</div>
                      <div>延迟 {formatNumber(moduleItem.data_delay_sec, 0)}s</div>
                    </div>

                    {moduleHref ? (
                      <Link
                        href={moduleHref}
                        data-testid={moduleTestId}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-[var(--color-brand-700)] hover:underline"
                      >
                        进入模块
                        <ArrowUpRight className="h-3 w-3" />
                      </Link>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </OverviewCard>

        <OverviewCard
          title="24h 流量趋势"
          subtitle="区分瞬时抖动与趋势性变化"
          icon={TrendingUp}
          testId="overview-card-traffic-trends"
          className="xl:col-span-6"
        >
          <div className="mb-2 grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-border/70 bg-background/60 px-3 py-2">
              <p className="text-[11px] text-muted-foreground">最新全业务 QPS</p>
              <p className="mt-1 text-sm font-semibold text-foreground">{formatNumber(latestTrendPoint?.request_qps ?? null, 2)}</p>
            </div>
            <div className="rounded-lg border border-border/70 bg-background/60 px-3 py-2">
              <p className="text-[11px] text-muted-foreground">最新提问 QPS</p>
              <p className="mt-1 text-sm font-semibold text-foreground">{formatNumber(latestTrendPoint?.question_qps ?? null, 2)}</p>
            </div>
          </div>
          <TrafficTrendChart trends={trends} />
        </OverviewCard>
      </div>
    </div>
  );
}
