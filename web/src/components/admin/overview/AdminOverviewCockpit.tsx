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
  Cpu,
  DatabaseZap,
  Gauge,
  MessageSquare,
  RefreshCcw,
  ShieldAlert,
  Siren,
  Timer,
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
  AdminOverviewTrendWindow,
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
  { label: string; badgeClass: string; textClass: string }
> = {
  healthy: {
    label: "健康",
    badgeClass:
      "border-emerald-200/80 bg-emerald-500/10 text-emerald-700 dark:border-emerald-500/30 dark:text-emerald-300",
    textClass: "text-emerald-700 dark:text-emerald-300",
  },
  warning: {
    label: "预警",
    badgeClass:
      "border-amber-200/80 bg-amber-500/10 text-amber-700 dark:border-amber-500/30 dark:text-amber-300",
    textClass: "text-amber-700 dark:text-amber-300",
  },
  critical: {
    label: "严重",
    badgeClass:
      "border-rose-200/80 bg-rose-500/10 text-rose-700 dark:border-rose-500/30 dark:text-rose-300",
    textClass: "text-rose-700 dark:text-rose-300",
  },
  unknown: {
    label: "未知",
    badgeClass:
      "border-slate-200/80 bg-slate-500/10 text-slate-700 dark:border-slate-500/30 dark:text-slate-300",
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

function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  return `${value.toFixed(digits)}%`;
}

function formatLatency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  return `${formatNumber(value, 0)} ms`;
}

function formatCurrencyPerMinute(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "--";
  }

  return `¥${formatNumber(value, 2)}/min`;
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
  return snapshot.source !== "empty" || snapshot.alerts.length > 0 || snapshot.change_feed.length > 0;
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

function LevelBadge({ level }: { level: AdminOverviewHealthLevel }) {
  const meta = HEALTH_LEVEL_META[level];

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
  testId: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      data-testid={testId}
      className={cn("admin-surface flex h-full flex-col p-4", className)}
    >
      <header className="mb-3 flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold leading-none text-foreground">{title}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <div className="rounded-lg border border-border/60 bg-background/70 p-1.5">
          <Icon className="h-3.5 w-3.5 text-[var(--color-brand-700)]" />
        </div>
      </header>
      <div className="flex-1">{children}</div>
    </section>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-dashed border-border/60 py-2 last:border-b-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xs font-medium text-foreground">{value}</span>
    </div>
  );
}

function TrendChart({
  window,
  trends,
  dataKey,
  color,
  valueFormatter,
}: {
  window: AdminOverviewTrendWindow;
  trends: AdminOverviewTrendsResponse;
  dataKey: "health_score" | "request_qps";
  color: string;
  valueFormatter: (value: number | null | undefined) => string;
}) {
  const data = useMemo(() => {
    return trends.windows[window].map((point) => ({
      label: formatTimeLabel(point.timestamp),
      value: dataKey === "health_score" ? point.health_score : point.request_qps,
    }));
  }, [dataKey, trends.windows, window]);

  if (data.length === 0) {
    return (
      <div className="flex h-[104px] items-center justify-center rounded-lg border border-dashed border-border/70 bg-background/40 text-xs text-muted-foreground">
        暂无趋势数据
      </div>
    );
  }

  return (
    <div className="h-[104px] w-full">
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
            formatter={(value) => valueFormatter(toNumericValue(value))}
            labelFormatter={(label) => `时间: ${label}`}
            contentStyle={{
              borderRadius: 10,
              border: "1px solid var(--color-border)",
              background: "var(--color-card)",
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2.2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function CockpitSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-12" data-testid="admin-overview-skeleton">
      {Array.from({ length: 8 }).map((_, index) => (
        <div
          key={index}
          className={cn(
            "admin-surface animate-pulse p-4",
            index < 4 ? "xl:col-span-3" : "xl:col-span-4",
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

    const abortController = new AbortController();
    streamAbortRef.current = abortController;
    setRealtimeStatus(buildRealtimeStatus("connecting", "正在建立实时连接..."));

    void streamAdminOverview({
      signal: abortController.signal,
      onOpen: () => {
        stopPolling();
        setRealtimeStatus(buildRealtimeStatus("streaming", "实时流已连接"));
      },
      onResult: (event) => {
        setSnapshot((current) =>
          mergeAdminOverviewSnapshot(current, event.data.patch, event.data.snapshot_at),
        );
      },
      onInterrupt: (event) => {
        startPolling({
          reason: event.data.reason,
          message: event.data.message ?? "实时流中断，10 秒轮询兜底已启用",
          retryAfterSec: event.data.retry_after_sec,
        });
      },
      onDone: (event) => {
        if (event.data.final) {
          startPolling({
            reason: "stream_done",
            message: "实时批次已结束，已切换轮询刷新",
          });
        }
      },
      onError: () => {
        startPolling({
          reason: "stream_error",
          message: "实时链路异常，已切换轮询刷新",
        });
      },
    })
      .then(() => {
        if (!abortController.signal.aborted) {
          startPolling({
            reason: "stream_closed",
            message: "实时连接已关闭，已切换轮询刷新",
          });
        }
      })
      .catch((error) => {
        if ((error as Error).name === "AbortError" || abortController.signal.aborted) {
          return;
        }

        startPolling({
          reason: "stream_exception",
          message: "实时连接失败，已切换轮询刷新",
        });
      });
  }, [startPolling, stopPolling, stopStream]);

  const bootstrap = useCallback(async () => {
    stopStream();
    stopPolling();

    setViewState("loading");
    setLoadError("");
    setRealtimeStatus(buildRealtimeStatus("connecting", "正在加载总览数据..."));

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

  const systemCardStatus =
    snapshot.system_status.status !== "ok"
      ? snapshot.system_status.status
      : snapshot.traffic_health.status;
  const freshnessCardStatus = resolveFreshnessCardStatus(snapshot);
  const isDataStale = freshnessCardStatus === "stale";

  const systemPrimaryText =
    snapshot.health_score == null
      ? describeCardState(systemCardStatus, {
          ok: "系统正常",
          no_data: "业务无样本",
          stale: "使用旧快照",
          degraded: "聚合已降级",
          unknown: "状态未知",
        })
      : formatNumber(snapshot.health_score, 1);

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

  if (viewState === "loading") {
    return (
      <div className="admin-page-content space-y-4">
        <header>
          <h1 className="app-page-title">总览驾驶舱</h1>
          <p className="app-page-subtitle mt-1">正在准备实时运行态数据...</p>
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
              聚焦系统状态、业务请求质量与用户提问活跃度，支持实时流 + 轮询降级。
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
          title="系统状态"
          subtitle="聚合链路、服务可用性与最后水位"
          icon={Gauge}
          testId="overview-card-system-status"
          className="xl:col-span-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-2xl font-semibold tracking-tight text-foreground">{systemPrimaryText}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {snapshot.system_status.explain ||
                  snapshot.traffic_health.explain ||
                  "系统状态基于当前聚合链路计算。"}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <LevelBadge level={snapshot.health_level} />
              <StateBadge status={systemCardStatus} />
            </div>
          </div>
          <MetricRow
            label="聚合链路"
            value={describeCardState(snapshot.system_status.status, {
              ok: "正常",
              no_data: "无样本",
              stale: "使用旧快照",
              degraded: "聚合降级",
              unknown: "未知",
            })}
          />
          <MetricRow
            label="业务流量态"
            value={describeCardState(snapshot.traffic_health.status, {
              ok: "有业务样本",
              no_data: "无业务样本",
              stale: "样本陈旧",
              degraded: "聚合降级",
              unknown: "未知",
            })}
          />
          <MetricRow
            label="最后水位"
            value={formatDateTime(
              snapshot.system_status.watermark_at ||
                snapshot.traffic_health.watermark_at ||
                snapshot.snapshot_at,
            )}
          />
          <MetricRow
            label="数据源"
            value={
              snapshot.system_status.data_source ||
              snapshot.traffic_health.data_source ||
              snapshot.source ||
              "未知"
            }
          />
        </OverviewCard>

        <OverviewCard
          title="业务请求质量"
          subtitle="全业务 API 请求质量"
          icon={Activity}
          testId="overview-card-request-quality"
          className="xl:col-span-3"
        >
          <div className="mb-1.5 flex items-start justify-between gap-2">
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
            <div className="flex flex-col items-end gap-1">
              <LevelBadge level={snapshot.request_quality.health_level} />
              <StateBadge status={snapshot.request_quality.status} />
            </div>
          </div>
          <MetricRow
            label="请求总量"
            value={withCardStateFallback(
              formatNumber(snapshot.request_quality.request_total, 0),
              snapshot.request_quality.status,
            )}
          />
          <MetricRow
            label="全业务 QPS"
            value={withCardStateFallback(
              formatNumber(snapshot.request_quality.qps, 2),
              snapshot.request_quality.status,
            )}
          />
          <MetricRow
            label="成功率"
            value={withCardStateFallback(
              formatRatioPercent(snapshot.request_quality.success_rate, 2),
              snapshot.request_quality.status,
            )}
          />
          <MetricRow
            label="5xx 占比"
            value={withCardStateFallback(
              formatRatioPercent(snapshot.request_quality.error_5xx_rate, 2),
              snapshot.request_quality.status,
            )}
          />
          <MetricRow
            label="P95 延迟"
            value={withCardStateFallback(
              formatLatency(snapshot.request_quality.latency_p95_ms),
              snapshot.request_quality.status,
            )}
          />
        </OverviewCard>

        <OverviewCard
          title="用户提问活跃度"
          subtitle="聊天提问链路的健康与活跃度"
          icon={MessageSquare}
          testId="overview-card-question-activity"
          className="xl:col-span-3"
        >
          <div className="mb-1.5 flex items-start justify-between gap-2">
            <div>
              <p className="text-lg font-semibold text-foreground">
                {withCardStateFallback(
                  formatNumber(snapshot.question_activity.score, 1),
                  snapshot.question_activity.status,
                  {
                    ok: "链路活跃",
                    no_data: "暂无提问",
                    stale: "沿用旧值",
                    degraded: "聚合降级",
                    unknown: "状态未知",
                  },
                )}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {snapshot.question_activity.explain || "用于回答用户提问链路是否活跃、是否健康。"}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <LevelBadge level={snapshot.question_activity.health_level} />
              <StateBadge status={snapshot.question_activity.status} />
            </div>
          </div>
          <MetricRow
            label="提问次数"
            value={withCardStateFallback(
              formatNumber(snapshot.question_activity.question_total, 0),
              snapshot.question_activity.status,
            )}
          />
          <MetricRow
            label="提问 QPS"
            value={withCardStateFallback(
              formatNumber(snapshot.question_activity.question_qps, 2),
              snapshot.question_activity.status,
            )}
          />
          <MetricRow
            label="成功率"
            value={withCardStateFallback(
              formatRatioPercent(snapshot.question_activity.question_success_rate, 2),
              snapshot.question_activity.status,
            )}
          />
          <MetricRow
            label="流中断率"
            value={withCardStateFallback(
              formatRatioPercent(snapshot.question_activity.stream_interrupt_rate, 2),
              snapshot.question_activity.status,
            )}
          />
          <MetricRow
            label="P95 延迟"
            value={withCardStateFallback(
              formatLatency(snapshot.question_activity.question_latency_p95_ms),
              snapshot.question_activity.status,
            )}
          />
        </OverviewCard>

        <OverviewCard
          title="稳定性"
          subtitle="告警压力与模块异常情况"
          icon={ShieldAlert}
          testId="overview-card-stability"
          className="xl:col-span-3"
        >
          <div className="mb-1.5 flex items-start justify-between gap-2">
            <div>
              <p className="text-lg font-semibold text-foreground">
                {withCardStateFallback(
                  formatNumber(snapshot.stability.score, 1),
                  snapshot.stability.status,
                  {
                    ok: "稳定",
                    no_data: "样本不足",
                    stale: "沿用旧值",
                    degraded: "聚合降级",
                    unknown: "状态未知",
                  },
                )}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">异常项支持一键跳转到对应管理模块。</p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <LevelBadge level={snapshot.stability.health_level} />
              <StateBadge status={snapshot.stability.status} />
            </div>
          </div>
          <MetricRow
            label="严重告警"
            value={withCardStateFallback(
              formatNumber(snapshot.stability.critical_alerts, 0),
              snapshot.stability.status,
            )}
          />
          <MetricRow
            label="预警告警"
            value={withCardStateFallback(
              formatNumber(snapshot.stability.warning_alerts, 0),
              snapshot.stability.status,
            )}
          />
          <MetricRow
            label="模块稳定分"
            value={withCardStateFallback(
              formatNumber(snapshot.stability.module_score, 1),
              snapshot.stability.status,
            )}
          />
        </OverviewCard>

        <OverviewCard
          title="容量与成本"
          subtitle="全业务 QPS、提问 QPS 与预算占用"
          icon={Cpu}
          testId="overview-card-capacity-cost"
          className="xl:col-span-4"
        >
          <div className="mb-1.5 flex items-start justify-between gap-2">
            <div>
              <p className="text-lg font-semibold text-foreground">
                {withCardStateFallback(
                  formatNumber(snapshot.capacity_cost.score, 1),
                  snapshot.capacity_cost.status,
                  {
                    ok: "容量稳定",
                    no_data: "无容量样本",
                    stale: "沿用旧值",
                    degraded: "聚合降级",
                    unknown: "状态未知",
                  },
                )}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {snapshot.capacity_cost.explain || "用于观察吞吐、预算与成本占用。"}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <LevelBadge level={snapshot.capacity_cost.health_level} />
              <StateBadge status={snapshot.capacity_cost.status} />
            </div>
          </div>
          <MetricRow
            label="全业务 QPS"
            value={withCardStateFallback(
              formatNumber(snapshot.capacity_cost.qps, 2),
              snapshot.capacity_cost.status,
            )}
          />
          <MetricRow
            label="提问 QPS"
            value={withCardStateFallback(
              formatNumber(snapshot.capacity_cost.question_qps, 2),
              snapshot.capacity_cost.status,
            )}
          />
          <MetricRow
            label="每分钟成本"
            value={withCardStateFallback(
              formatCurrencyPerMinute(snapshot.capacity_cost.cost_per_minute),
              snapshot.capacity_cost.status,
            )}
          />
          <MetricRow
            label="预算占用"
            value={withCardStateFallback(
              formatPercent(snapshot.capacity_cost.budget_usage_pct, 1),
              snapshot.capacity_cost.status,
            )}
          />
          <div className="mt-2">
            <TrendChart
              window="24h"
              trends={trends}
              dataKey="request_qps"
              color="var(--chart-2)"
              valueFormatter={(value) => `${formatNumber(value, 2)} QPS`}
            />
          </div>
        </OverviewCard>

        <OverviewCard
          title="数据新鲜度"
          subtitle="快照延迟与陈旧判定"
          icon={Timer}
          testId="overview-card-freshness"
          className="xl:col-span-4"
        >
          <div className="mb-1.5 flex items-start justify-between gap-2">
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
            <div className="flex flex-col items-end gap-1">
              <LevelBadge level={snapshot.freshness.health_level} />
              <StateBadge status={freshnessCardStatus} />
            </div>
          </div>
          <MetricRow label="当前状态" value={formatFreshnessStatus(snapshot.freshness.status)} />
          <MetricRow
            label="陈旧阈值"
            value={
              snapshot.freshness.max_delay_sec == null
                ? "暂无阈值"
                : `${formatNumber(snapshot.freshness.max_delay_sec, 0)} s`
            }
          />
          <MetricRow label="来源" value={snapshot.freshness.source || "未知"} />
          <MetricRow label="快照时间" value={latestUpdateAt} />
        </OverviewCard>

        <OverviewCard
          title="模块健康矩阵"
          subtitle="按模块聚合的健康态与跳转"
          icon={DatabaseZap}
          testId="overview-card-module-matrix"
          className="xl:col-span-4"
        >
          {snapshot.module_matrix.length === 0 ? (
            <div className="flex h-full min-h-[136px] items-center justify-center rounded-lg border border-dashed border-border/70 bg-background/40 text-sm text-muted-foreground">
              暂无模块健康样本
            </div>
          ) : (
            <div className="space-y-2">
              {snapshot.module_matrix.slice(0, 5).map((moduleItem) => {
                const moduleHref = resolveModuleRoute(moduleItem.key);
                const moduleLevelMeta = HEALTH_LEVEL_META[moduleItem.health_level];
                const moduleTestId = `overview-module-link-${sanitizeTestIdSegment(moduleItem.key)}`;

                return (
                  <div
                    key={moduleItem.key}
                    className="rounded-lg border border-border/70 bg-background/60 p-2.5"
                  >
                    <div className="mb-1.5 flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium text-foreground">{moduleItem.label}</p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">{moduleLevelMeta.label}</p>
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
          title="实时告警 / 关键变更"
          subtitle="当前告警与最近配置变更统一收口"
          icon={Siren}
          testId="overview-card-alerts"
          className="xl:col-span-12"
        >
          {snapshot.alerts.length === 0 && snapshot.change_feed.length === 0 ? (
            <div className="flex min-h-[120px] items-center justify-center rounded-lg border border-dashed border-border/70 bg-background/40 text-sm text-muted-foreground">
              当前无告警，也无关键变更
            </div>
          ) : (
            <div className="grid gap-3 xl:grid-cols-2">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-muted-foreground">实时告警</p>
                  <span className="text-[11px] text-muted-foreground">{snapshot.alerts.length} 条</span>
                </div>
                {snapshot.alerts.length === 0 ? (
                  <div className="flex min-h-[96px] items-center justify-center rounded-lg border border-dashed border-border/70 bg-background/40 text-sm text-muted-foreground">
                    当前无告警
                  </div>
                ) : (
                  <div className="space-y-2">
                    {snapshot.alerts.slice(0, 5).map((alert, index) => {
                      const alertHref = resolveModuleRoute(alert.module);
                      return (
                        <div
                          key={`${alert.code}-${index}`}
                          className="rounded-lg border border-border/70 bg-background/60 p-2.5"
                        >
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
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-muted-foreground">关键变更</p>
                  <span className="text-[11px] text-muted-foreground">{snapshot.change_feed.length} 条</span>
                </div>
                {snapshot.change_feed.length === 0 ? (
                  <div className="flex min-h-[96px] items-center justify-center rounded-lg border border-dashed border-border/70 bg-background/40 text-sm text-muted-foreground">
                    暂无关键变更记录
                  </div>
                ) : (
                  <div className="grid gap-2">
                    {snapshot.change_feed.slice(0, 6).map((changeItem) => {
                      const meta = SEVERITY_META[changeItem.level] ?? SEVERITY_META.info;

                      return (
                        <article
                          key={changeItem.id}
                          className="rounded-lg border border-border/70 bg-background/60 p-2.5"
                        >
                          <div className="mb-1 flex items-center justify-between gap-2">
                            <span
                              className={cn(
                                "rounded-full border px-2 py-0.5 text-[11px]",
                                meta.badgeClass,
                              )}
                            >
                              {meta.label}
                            </span>
                            <span className="text-[11px] text-muted-foreground">
                              {formatDateTime(changeItem.occurred_at)}
                            </span>
                          </div>
                          <p className="text-sm leading-5 text-foreground">{changeItem.title}</p>
                        </article>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </OverviewCard>
      </div>
    </div>
  );
}
