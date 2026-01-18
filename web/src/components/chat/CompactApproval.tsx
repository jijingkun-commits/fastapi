"use client";

import { useStreamContext } from "@/providers/Stream";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Edit3, Loader2 } from "lucide-react";
import { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

/**
 * 紧凑版人工审核组件
 * 显示在输入框区域，与 Select 组件并排
 */
export function CompactApproval() {
    const stream = useStreamContext();
    const interrupt = (stream as any).interrupt;
    const resume = (stream as any).resume;
    const [loading, setLoading] = useState(false);
    const [editOpen, setEditOpen] = useState(false);
    const [editValue, setEditValue] = useState("");

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

    // 提取显示内容
    // 优先显示后端生成的友好摘要（针对待办等操作）
    // 其次显示 SQL 查询或其他查询内容
    // 最后回退到显示 JSON 数据
    const displayContent = actionArgs._display_message
        || actionArgs.sql_query
        || actionArgs.query
        || JSON.stringify(actionArgs, null, 2);

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

    const handleEdit = () => {
        setEditValue(displayContent);
        setEditOpen(true);
    };

    const handleEditConfirm = async () => {
        setLoading(true);
        setEditOpen(false);
        try {
            // 根据参数类型构建编辑后的 args
            const editedArgs = actionArgs.sql_query
                ? { sql_query: editValue }
                : actionArgs.query
                    ? { query: editValue }
                    : { ...actionArgs };
            await resume({ type: "edit", args: editedArgs });
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-lg",
                "bg-gray-100 border border-gray-200",
                "animate-in fade-in-0 slide-in-from-top-2 duration-300"
            )}>
                <div className="flex-1 min-w-0">
                    <div className="flex flex-col gap-1">
                        <span className="text-xs font-medium text-gray-700">
                            需要审核
                        </span>
                        <div className="text-xs text-gray-600 whitespace-pre-wrap">
                            {displayContent}
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-1.5 flex-shrink-0">
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs hover:bg-gray-200"
                        onClick={handleEdit}
                        disabled={loading}
                    >
                        <Edit3 className="h-3.5 w-3.5 mr-1" />
                        编辑
                    </Button>
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs text-red-600 hover:bg-red-50 hover:text-red-700"
                        onClick={handleReject}
                        disabled={loading}
                    >
                        <XCircle className="h-3.5 w-3.5 mr-1" />
                        拒绝
                    </Button>
                    <Button
                        size="sm"
                        className="h-7 px-3 text-xs bg-gray-800 hover:bg-gray-900"
                        onClick={handleApprove}
                        disabled={loading}
                    >
                        {loading ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                            <>
                                <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                                批准
                            </>
                        )}
                    </Button>
                </div>
            </div>

            {/* 编辑对话框 */}
            <Dialog open={editOpen} onOpenChange={setEditOpen}>
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>编辑 {actionName} 参数</DialogTitle>
                    </DialogHeader>
                    <Textarea
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="min-h-[150px] font-mono text-sm"
                        placeholder="输入修改后的内容..."
                    />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditOpen(false)}>
                            取消
                        </Button>
                        <Button onClick={handleEditConfirm} disabled={loading}>
                            {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                            确认并执行
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
