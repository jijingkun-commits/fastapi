"use client";

import { useStreamContext } from "@/providers/Stream";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2, ClipboardList } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * 紧凑版人工审核组件
 * 
 * 美化版：
 * - 移除编辑功能，只保留批准/拒绝
 * - 卡片式布局，操作类型高亮
 * - 内容区域更好的排版
 */
export function CompactApproval() {
    const stream = useStreamContext();
    const interrupt = (stream as any).interrupt;
    const resume = (stream as any).resume;
    const [loading, setLoading] = useState(false);

    // 没有 interrupt 或没有 resume 方法时不渲染
    if (!interrupt || typeof resume !== "function") {
        return null;
    }

    // 解析 interrupt 数据
    const value = interrupt.value || {};
    const actionRequests = value.action_requests || [];
    const firstAction = actionRequests[0];
    const actionName = firstAction?.name || "操作";
    const actionArgs = firstAction?.args || {};

    // 提取显示内容：优先使用 _display_message，其次使用 sql_query
    const displayMessage = actionArgs._display_message || actionArgs.sql_query || "";

    // 操作类型映射
    const actionLabels: Record<string, string> = {
        create: "创建待办",
        update: "更新待办",
        delete: "删除待办",
        query: "查询待办",
        sql_inter: "执行 SQL",
        unknown: "待确认操作",
    };
    const actionLabel = actionLabels[actionName] || actionName;

    const handleApprove = async () => {
        setLoading(true);
        try {
            await resume({ type: "accept" });
        } finally {
            setLoading(false);
        }
    };

    const handleReject = async () => {
        setLoading(true);
        try {
            await resume({ type: "reject", message: "用户拒绝执行" });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={cn(
            "w-full flex items-center justify-between px-4 py-2.5 rounded-xl border shadow-sm",
            "bg-zinc-50 border-zinc-200 text-zinc-800",
            "dark:bg-zinc-900 dark:border-zinc-800 dark:text-zinc-200",
            "animate-in fade-in-0 slide-in-from-bottom-2 duration-300"
        )}>
            {/* 左侧：图标 + 信息 */}
            <div className="flex items-center gap-3 min-w-0 flex-1 mr-4">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-200 dark:bg-zinc-800 shrink-0">
                    <ClipboardList className="h-4 w-4 text-zinc-500" />
                </div>

                <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold whitespace-nowrap">
                            {actionLabel}
                        </span>
                        <span className="text-xs px-1.5 py-0.5 rounded-md bg-zinc-200/50 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400 whitespace-nowrap">
                            待确认
                        </span>
                    </div>
                    {displayMessage && (
                        <code className="text-xs text-zinc-600 dark:text-zinc-300 font-mono bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded max-w-xl max-h-20 overflow-auto block whitespace-pre-wrap break-all">
                            {displayMessage}
                        </code>
                    )}
                </div>
            </div>

            {/* 右侧：操作按钮 */}
            <div className="flex items-center gap-2 shrink-0">
                <Button
                    data-testid="reject-button"
                    size="sm"
                    variant="ghost"
                    className="h-8 px-3 text-sm text-zinc-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                    onClick={handleReject}
                    disabled={loading}
                >
                    取消
                </Button>
                <Button
                    data-testid="confirm-button"
                    size="sm"
                    className="h-8 px-4 text-sm bg-zinc-900 hover:bg-zinc-800 text-white dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 shadow-sm"
                    onClick={handleApprove}
                    disabled={loading}
                >
                    {loading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                        "确认"
                    )}
                </Button>
            </div>
        </div>
    );
}
