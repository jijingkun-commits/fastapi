import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface AdminCompactStatCardProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "success" | "danger" | "brand" | "muted";
  selected?: boolean;
  onClick?: () => void;
  className?: string;
  valueClassName?: string;
  hintClassName?: string;
  valueTitle?: string;
  testId?: string;
}

const TONE_CLASS_MAP: Record<NonNullable<AdminCompactStatCardProps["tone"]>, string> = {
  default: "text-foreground",
  success: "text-emerald-600 dark:text-emerald-400",
  danger: "text-rose-600 dark:text-rose-400",
  brand: "text-[var(--color-brand-700)]",
  muted: "text-muted-foreground",
};

export function AdminCompactStatCard({
  label,
  value,
  hint,
  tone = "default",
  selected = false,
  onClick,
  className,
  valueClassName,
  hintClassName,
  valueTitle,
  testId,
}: AdminCompactStatCardProps) {
  const body = (
    <div className="flex min-h-[72px] items-center justify-between gap-3 px-3.5 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-foreground">{label}</div>
        {hint ? (
          <div className={cn("mt-1 truncate text-[11px] text-muted-foreground", hintClassName)}>{hint}</div>
        ) : null}
      </div>
      <div
        className={cn(
          "shrink-0 text-[1.75rem] font-semibold leading-none tabular-nums",
          TONE_CLASS_MAP[tone],
          valueClassName,
        )}
        title={valueTitle}
      >
        {value}
      </div>
    </div>
  );

  return (
    <Card
      data-testid={testId}
      className={cn(
        "gap-0 py-0 transition-[border-color,background-color,box-shadow]",
        selected
          ? "border-primary bg-primary/5 shadow-sm"
          : "border-border/70 hover:border-primary/40 hover:shadow-sm",
        className,
      )}
    >
      {onClick ? (
        <button type="button" className="w-full text-left" onClick={onClick}>
          {body}
        </button>
      ) : (
        body
      )}
    </Card>
  );
}
