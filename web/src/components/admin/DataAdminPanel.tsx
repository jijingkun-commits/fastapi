/**
 * 问数管理面板（中文注释）
 * 
 * 功能：
 * - 查询日志列表展示
 * - SQL 修正对话框
 * - 反馈标记（正确/错误）
 * - 批量训练
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    QueryLog,
    getQueryLogs,
    correctSQL,
    feedbackSQL,
    trainLogs,
    trainAllPending,
} from "@/lib/data-admin-api";

export function DataAdminPanel() {
    // 状态
    const [logs, setLogs] = useState<QueryLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
    const [filter, setFilter] = useState<"all" | "correct" | "incorrect" | "pending">("all");

    // 修正对话框
    const [editingLog, setEditingLog] = useState<QueryLog | null>(null);
    const [correctedSQL, setCorrectedSQL] = useState("");
    const [savingCorrection, setSavingCorrection] = useState(false);

    // 加载日志
    const loadLogs = useCallback(async () => {
        setLoading(true);
        try {
            let params: { is_correct?: boolean; trained?: boolean } = {};
            if (filter === "correct") params.is_correct = true;
            else if (filter === "incorrect") params.is_correct = false;
            else if (filter === "pending") params.trained = false;

            const data = await getQueryLogs({ ...params, limit: 50 });
            setLogs(data);
        } catch (e: any) {
            toast.error(e.message || "加载失败");
        } finally {
            setLoading(false);
        }
    }, [filter]);

    useEffect(() => {
        loadLogs();
    }, [loadLogs]);

    // 选择处理
    const toggleSelect = (id: number) => {
        const newSet = new Set(selectedIds);
        if (newSet.has(id)) newSet.delete(id);
        else newSet.add(id);
        setSelectedIds(newSet);
    };

    const toggleSelectAll = () => {
        if (selectedIds.size === logs.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(logs.map(l => l.id)));
        }
    };

    // 反馈操作
    const handleFeedback = async (logId: number, isCorrect: boolean) => {
        try {
            await feedbackSQL(logId, isCorrect);
            toast.success(isCorrect ? "已标记为正确" : "已标记为错误");
            loadLogs();
        } catch (e: any) {
            toast.error(e.message);
        }
    };

    // 打开修正对话框
    const openCorrectDialog = (log: QueryLog) => {
        setEditingLog(log);
        setCorrectedSQL(log.corrected_sql || log.generated_sql || "");
    };

    // 保存修正
    const saveCorrection = async () => {
        if (!editingLog) return;
        setSavingCorrection(true);
        try {
            await correctSQL({
                log_id: editingLog.id,
                corrected_sql: correctedSQL,
                is_correct: true,
            });
            toast.success("修正已保存");
            setEditingLog(null);
            loadLogs();
        } catch (e: any) {
            toast.error(e.message);
        } finally {
            setSavingCorrection(false);
        }
    };

    // 训练选中
    const handleTrainSelected = async () => {
        if (selectedIds.size === 0) {
            toast.warning("请先选择要训练的记录");
            return;
        }
        try {
            const result = await trainLogs(Array.from(selectedIds));
            toast.success(result.message);
            if (result.errors?.length) {
                result.errors.forEach(err => toast.warning(err));
            }
            setSelectedIds(new Set());
            loadLogs();
        } catch (e: any) {
            toast.error(e.message);
        }
    };

    // 训练全部待训练
    const handleTrainAll = async () => {
        try {
            const result = await trainAllPending();
            toast.success(result.message);
            loadLogs();
        } catch (e: any) {
            toast.error(e.message);
        }
    };

    // 状态徽章
    const renderStatusBadge = (log: QueryLog) => {
        if (log.trained) {
            return <Badge className="bg-green-100 text-green-800">已训练</Badge>;
        }
        if (log.is_correct === true) {
            return <Badge className="bg-blue-100 text-blue-800">正确</Badge>;
        }
        if (log.is_correct === false) {
            return <Badge className="bg-red-100 text-red-800">错误</Badge>;
        }
        return <Badge className="bg-gray-100 text-gray-600">待审核</Badge>;
    };

    return (
        <div className="container mx-auto py-8 px-4">
            {/* 页头 */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-foreground">SQL 修正台</h1>
                    <p className="text-muted-foreground text-sm mt-1">
                        审核 AI 生成的 SQL，修正错误，持续改进问数能力
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={loadLogs} disabled={loading}>
                        刷新
                    </Button>
                    <Button variant="outline" onClick={handleTrainSelected} disabled={selectedIds.size === 0}>
                        训练选中 ({selectedIds.size})
                    </Button>
                    <Button onClick={handleTrainAll}>
                        训练全部待训练
                    </Button>
                </div>
            </div>

            {/* 筛选器 */}
            <Card className="mb-6">
                <CardContent className="py-4">
                    <div className="flex items-center gap-4">
                        <span className="text-sm font-medium">筛选：</span>
                        <Select value={filter} onValueChange={(v) => setFilter(v as any)}>
                            <SelectTrigger className="w-40">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">全部</SelectItem>
                                <SelectItem value="correct">已标记正确</SelectItem>
                                <SelectItem value="incorrect">已标记错误</SelectItem>
                                <SelectItem value="pending">待训练</SelectItem>
                            </SelectContent>
                        </Select>
                        <span className="text-sm text-muted-foreground">
                            共 {logs.length} 条记录
                        </span>
                    </div>
                </CardContent>
            </Card>

            {/* 日志列表 */}
            <Card>
                <CardHeader className="border-b">
                    <div className="flex items-center gap-4">
                        <Checkbox
                            checked={logs.length > 0 && selectedIds.size === logs.length}
                            onCheckedChange={toggleSelectAll}
                        />
                        <CardTitle className="text-base">查询日志</CardTitle>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                        </div>
                    ) : logs.length === 0 ? (
                        <div className="text-center py-12 text-muted-foreground">
                            暂无记录
                        </div>
                    ) : (
                        <div className="divide-y">
                            {logs.map((log) => (
                                <div
                                    key={log.id}
                                    className="p-4 hover:bg-muted/50 transition-colors"
                                >
                                    <div className="flex items-start gap-4">
                                        <Checkbox
                                            checked={selectedIds.has(log.id)}
                                            onCheckedChange={() => toggleSelect(log.id)}
                                            className="mt-1"
                                        />
                                        <div className="flex-1 min-w-0">
                                            {/* 问题 */}
                                            <div className="flex items-center gap-2 mb-2">
                                                {renderStatusBadge(log)}
                                                <span className="text-xs text-muted-foreground">
                                                    {new Date(log.created_at).toLocaleString("zh-CN")}
                                                </span>
                                            </div>
                                            <p className="font-medium text-foreground mb-2 line-clamp-2">
                                                {log.question}
                                            </p>
                                            {/* SQL */}
                                            {(log.corrected_sql || log.generated_sql) && (
                                                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-24">
                                                    {log.corrected_sql || log.generated_sql}
                                                </pre>
                                            )}
                                        </div>
                                        {/* 操作按钮 */}
                                        <div className="flex flex-col gap-2 shrink-0">
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => openCorrectDialog(log)}
                                            >
                                                修正
                                            </Button>
                                            <div className="flex gap-1">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="text-green-600 hover:text-green-700 hover:bg-green-50"
                                                    onClick={() => handleFeedback(log.id, true)}
                                                    disabled={log.is_correct === true}
                                                >
                                                    ✓
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                    onClick={() => handleFeedback(log.id, false)}
                                                    disabled={log.is_correct === false}
                                                >
                                                    ✗
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* 修正对话框 */}
            <Dialog open={!!editingLog} onOpenChange={(open) => !open && setEditingLog(null)}>
                <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>SQL 修正</DialogTitle>
                    </DialogHeader>
                    {editingLog && (
                        <div className="space-y-4">
                            {/* 原始问题 */}
                            <div>
                                <label className="text-sm font-medium text-muted-foreground">用户问题</label>
                                <p className="mt-1 p-3 bg-muted rounded-md">{editingLog.question}</p>
                            </div>
                            {/* 原始 SQL */}
                            <div>
                                <label className="text-sm font-medium text-muted-foreground">原始 SQL</label>
                                <pre className="mt-1 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                                    {editingLog.generated_sql || "(无)"}
                                </pre>
                            </div>
                            {/* 修正后 SQL */}
                            <div>
                                <label className="text-sm font-medium text-muted-foreground">修正后 SQL</label>
                                <Textarea
                                    value={correctedSQL}
                                    onChange={(e) => setCorrectedSQL(e.target.value)}
                                    placeholder="输入正确的 SQL..."
                                    className="mt-1 font-mono text-sm min-h-[150px]"
                                />
                            </div>
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditingLog(null)}>
                            取消
                        </Button>
                        <Button onClick={saveCorrection} disabled={savingCorrection || !correctedSQL.trim()}>
                            {savingCorrection ? "保存中..." : "保存修正"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
