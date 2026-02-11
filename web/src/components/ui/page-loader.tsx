"use client";

import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

interface PageLoaderProps {
  className?: string;
  text?: string;
}

export function PageLoader({ className, text = "加载中..." }: PageLoaderProps) {
  return (
    <div className={cn("flex h-full min-h-[220px] items-center justify-center", className)}>
      <div className="flex flex-col items-center gap-3">
        <div className="rounded-full bg-[var(--color-state-loading-surface)] p-3">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--color-state-loading-indicator)]" />
        </div>
        <span className="text-sm text-muted-foreground">{text}</span>
      </div>
    </div>
  );
}
