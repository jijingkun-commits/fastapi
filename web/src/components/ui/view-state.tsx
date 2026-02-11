"use client";

import type { ComponentType } from "react";
import { AlertTriangle, Ban, Inbox, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ViewStateType = "loading" | "empty" | "error" | "forbidden";

interface ViewStateProps {
  type: ViewStateType;
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

const STATE_META: Record<
  ViewStateType,
  {
    icon: ComponentType<{ className?: string }>;
    defaultTitle: string;
    defaultDescription: string;
    iconBgClass: string;
    iconClass: string;
  }
> = {
  loading: {
    icon: Loader2,
    defaultTitle: "加载中",
    defaultDescription: "正在准备页面内容，请稍候...",
    iconBgClass: "bg-[var(--color-state-loading-surface)]",
    iconClass: "text-[var(--color-state-loading-indicator)] animate-spin",
  },
  empty: {
    icon: Inbox,
    defaultTitle: "暂无数据",
    defaultDescription: "当前条件下没有可展示内容。",
    iconBgClass: "bg-[var(--color-state-empty-surface)]",
    iconClass: "text-[var(--color-state-empty-icon)]",
  },
  error: {
    icon: AlertTriangle,
    defaultTitle: "加载失败",
    defaultDescription: "页面数据获取失败，请重试。",
    iconBgClass: "bg-[var(--color-state-error-surface)]",
    iconClass: "text-[var(--color-state-error-icon)]",
  },
  forbidden: {
    icon: Ban,
    defaultTitle: "无访问权限",
    defaultDescription: "当前账号没有访问此内容的权限。",
    iconBgClass: "bg-[var(--color-state-forbidden-surface)]",
    iconClass: "text-[var(--color-state-forbidden-icon)]",
  },
};

export function ViewState({
  type,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: ViewStateProps) {
  const meta = STATE_META[type];
  const Icon = meta.icon;

  return (
    <div
      className={cn(
        "flex min-h-[240px] w-full items-center justify-center rounded-[var(--ds-radius-md)] border border-border/80 bg-card px-6 py-10 text-center shadow-[var(--ds-shadow-1)]",
        className,
      )}
    >
      <div className="flex max-w-sm flex-col items-center gap-3">
        <div className={cn("rounded-full p-3", meta.iconBgClass)}>
          <Icon className={cn("size-6", meta.iconClass)} />
        </div>

        <div className="space-y-1.5">
          <h3 className="text-base font-semibold text-foreground">
            {title ?? meta.defaultTitle}
          </h3>
          <p className="text-sm leading-6 text-muted-foreground">
            {description ?? meta.defaultDescription}
          </p>
        </div>

        {actionLabel && onAction ? (
          <Button
            type="button"
            variant={type === "error" || type === "forbidden" ? "default" : "outline"}
            size="sm"
            onClick={onAction}
            className="mt-2"
          >
            {actionLabel}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

