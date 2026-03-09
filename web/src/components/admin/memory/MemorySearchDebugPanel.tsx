"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";

import {
  getDocumentEmbeddingStatus,
  rebuildDocumentEmbeddings,
  retryFailedDocumentEmbeddings,
  searchMemoryDebug,
} from "@/lib/memory-admin-api";
import type { DocumentEmbeddingStatusResponse, MemorySearchDebugResponse } from "@/types/memory-admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ViewState } from "@/components/ui/view-state";
import { getMemoryStatusLabel } from "@/lib/memory-admin-labels";

interface MemorySearchDebugPanelProps {
  defaultUserId?: number;
  onGovernanceActionDone?: () => void;
}

function parseOptionalPositiveInt(raw: string): number | undefined {
  const trimmed = raw.trim();
  if (!trimmed) {
    return undefined;
  }

  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return undefined;
  }
  return parsed;
}

function parseOptionalFloat(raw: string): number | undefined {
  const trimmed = raw.trim();
  if (!trimmed) {
    return undefined;
  }
  const parsed = Number.parseFloat(trimmed);
  if (!Number.isFinite(parsed)) {
    return undefined;
  }
  return parsed;
}

export function MemorySearchDebugPanel({
  defaultUserId,
  onGovernanceActionDone,
}: MemorySearchDebugPanelProps) {
  const [queryUserId, setQueryUserId] = useState(defaultUserId ? String(defaultUserId) : "");
  const [queryText, setQueryText] = useState("");
  const [queryLimit, setQueryLimit] = useState("10");
  const [queryMinScore, setQueryMinScore] = useState("0");
  const [debugLoading, setDebugLoading] = useState(false);
  const [debugResult, setDebugResult] = useState<MemorySearchDebugResponse | null>(null);

  const [actionUserId, setActionUserId] = useState(defaultUserId ? String(defaultUserId) : "");
  const [actionDocId, setActionDocId] = useState("");
  const [actionLimit, setActionLimit] = useState("200");
  const [runAsync, setRunAsync] = useState(true);
  const [includePending, setIncludePending] = useState(true);
  const [includeFailed, setIncludeFailed] = useState(true);

  const [statusLoading, setStatusLoading] = useState(false);
  const [rebuildLoading, setRebuildLoading] = useState(false);
  const [retryLoading, setRetryLoading] = useState(false);
  const [statusData, setStatusData] = useState<DocumentEmbeddingStatusResponse | null>(null);
  const [lastActionMessage, setLastActionMessage] = useState("");

  useEffect(() => {
    if (!defaultUserId) {
      return;
    }
    setQueryUserId((prev) => (prev.trim() ? prev : String(defaultUserId)));
    setActionUserId((prev) => (prev.trim() ? prev : String(defaultUserId)));
  }, [defaultUserId]);

  const statusLabel = useMemo(() => {
    if (!statusData) {
      return "未加载";
    }
    return `待处理 ${statusData.pending} / 已就绪 ${statusData.ready} / 失败 ${statusData.failed}`;
  }, [statusData]);

  const loadEmbeddingStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const payload = await getDocumentEmbeddingStatus({
        user_id: parseOptionalPositiveInt(actionUserId),
        doc_id: parseOptionalPositiveInt(actionDocId),
      });
      setStatusData(payload);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "加载向量状态失败";
      toast.error(message);
    } finally {
      setStatusLoading(false);
    }
  }, [actionDocId, actionUserId]);

  useEffect(() => {
    void loadEmbeddingStatus();
  }, [loadEmbeddingStatus]);

  const handleSearchDebug = async () => {
    const userId = parseOptionalPositiveInt(queryUserId);
    if (!userId) {
      toast.warning("调试查询需要填写合法用户编号");
      return;
    }
    const normalizedQuery = queryText.trim();
    if (!normalizedQuery) {
      toast.warning("请输入调试查询词");
      return;
    }

    const limit = parseOptionalPositiveInt(queryLimit);
    const minScore = parseOptionalFloat(queryMinScore);

    setDebugLoading(true);
    try {
      const payload = await searchMemoryDebug({
        user_id: userId,
        query_text: normalizedQuery,
        ...(limit ? { limit } : {}),
        ...(minScore !== undefined ? { min_score: minScore } : {}),
      });
      setDebugResult(payload);
      toast.success(`调试完成，命中 ${payload.total} 条片段`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "执行调试查询失败";
      toast.error(message);
    } finally {
      setDebugLoading(false);
    }
  };

  const handleRebuild = async () => {
    const statusFilter = [
      includePending ? "pending" : null,
      includeFailed ? "failed" : null,
    ].filter((item): item is string => Boolean(item));

    if (statusFilter.length === 0) {
      toast.warning("至少选择一种重建状态");
      return;
    }

    setRebuildLoading(true);
    try {
      const payload = await rebuildDocumentEmbeddings({
        user_id: parseOptionalPositiveInt(actionUserId),
        doc_id: parseOptionalPositiveInt(actionDocId),
        limit: parseOptionalPositiveInt(actionLimit) ?? 200,
        run_async: runAsync,
        status_filter: statusFilter,
      });
      setLastActionMessage(
        `重建任务状态：${getMemoryStatusLabel(payload.status)}，总量 ${payload.total}，成功 ${payload.ready}，失败 ${payload.failed}`,
      );
      toast.success(`重建任务已提交（${getMemoryStatusLabel(payload.status)}）`);
      await loadEmbeddingStatus();
      onGovernanceActionDone?.();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "触发重建失败";
      toast.error(message);
    } finally {
      setRebuildLoading(false);
    }
  };

  const handleRetryFailed = async () => {
    setRetryLoading(true);
    try {
      const payload = await retryFailedDocumentEmbeddings({
        user_id: parseOptionalPositiveInt(actionUserId),
        doc_id: parseOptionalPositiveInt(actionDocId),
        limit: parseOptionalPositiveInt(actionLimit) ?? 200,
        run_async: runAsync,
      });
      setLastActionMessage(
        `失败重试状态：${getMemoryStatusLabel(payload.status)}，重置 ${payload.reset}，处理 ${payload.processed}，成功 ${payload.ready}`,
      );
      toast.success(`失败重试已触发（${getMemoryStatusLabel(payload.status)}）`);
      await loadEmbeddingStatus();
      onGovernanceActionDone?.();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "重试失败分块失败";
      toast.error(message);
    } finally {
      setRetryLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">召回调试与向量治理</CardTitle>
        <CardDescription>
          调试面板统一使用记忆管理接口，可查看召回分数并触发重建/重试。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="space-y-4 rounded-lg border border-border/80 p-4">
            <div className="space-y-2">
              <Label htmlFor="memory-debug-user-id">调试用户编号</Label>
              <Input
                id="memory-debug-user-id"
                value={queryUserId}
                onChange={(event) => setQueryUserId(event.target.value)}
                placeholder="例如 1001"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="memory-debug-query">调试查询词</Label>
              <Input
                id="memory-debug-query"
                value={queryText}
                onChange={(event) => setQueryText(event.target.value)}
                placeholder="例如 退款进度"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="memory-debug-limit">返回条数</Label>
                <Input
                  id="memory-debug-limit"
                  value={queryLimit}
                  onChange={(event) => setQueryLimit(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="memory-debug-min-score">最小分数</Label>
                <Input
                  id="memory-debug-min-score"
                  value={queryMinScore}
                  onChange={(event) => setQueryMinScore(event.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => void handleSearchDebug()} disabled={debugLoading}>
                <Search className="mr-1.5 h-4 w-4" />
                {debugLoading ? "调试中..." : "执行调试"}
              </Button>
              <Button
                variant="outline"
                onClick={() => setDebugResult(null)}
                disabled={debugLoading || !debugResult}
              >
                清空结果
              </Button>
            </div>
          </div>

          <div className="space-y-4 rounded-lg border border-border/80 p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-foreground">向量状态</p>
                <p className="text-xs text-muted-foreground mt-1">{statusLabel}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => void loadEmbeddingStatus()}
                disabled={statusLoading}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                刷新
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Badge variant="outline" className="justify-center py-1.5">
                总量 {statusData?.total ?? "-"}
              </Badge>
              <Badge variant="outline" className="justify-center py-1.5">
                待处理 {statusData?.pending ?? "-"}
              </Badge>
              <Badge variant="outline" className="justify-center py-1.5">
                已就绪 {statusData?.ready ?? "-"}
              </Badge>
              <Badge variant="outline" className="justify-center py-1.5">
                失败 {statusData?.failed ?? "-"}
              </Badge>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="memory-action-user-id">治理用户编号（可选）</Label>
                <Input
                  id="memory-action-user-id"
                  value={actionUserId}
                  onChange={(event) => setActionUserId(event.target.value)}
                  placeholder="留空表示全量"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="memory-action-doc-id">治理文档编号（可选）</Label>
                <Input
                  id="memory-action-doc-id"
                  value={actionDocId}
                  onChange={(event) => setActionDocId(event.target.value)}
                  placeholder="留空表示全量"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="memory-action-limit">处理上限</Label>
              <Input
                id="memory-action-limit"
                value={actionLimit}
                onChange={(event) => setActionLimit(event.target.value)}
              />
            </div>

            <div className="flex flex-wrap gap-4">
              <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                <Switch checked={includePending} onCheckedChange={setIncludePending} />
                包含待处理
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                <Switch checked={includeFailed} onCheckedChange={setIncludeFailed} />
                包含失败
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                <Switch checked={runAsync} onCheckedChange={setRunAsync} />
                异步执行
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void handleRebuild()} disabled={rebuildLoading}>
                {rebuildLoading ? "触发中..." : "重建向量"}
              </Button>
              <Button
                variant="outline"
                onClick={() => void handleRetryFailed()}
                disabled={retryLoading}
              >
                {retryLoading ? "重试中..." : "重试失败分块"}
              </Button>
            </div>

            {lastActionMessage ? (
              <p className="text-xs text-muted-foreground rounded-md bg-muted px-3 py-2">
                {lastActionMessage}
              </p>
            ) : null}
          </div>
        </div>

        {debugResult ? (
          debugResult.items.length > 0 ? (
            <div className="overflow-hidden rounded-[var(--ds-radius-md)] border border-border/80">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[72px]">文档编号</TableHead>
                    <TableHead>引用</TableHead>
                    <TableHead className="w-[90px] text-right">文本分</TableHead>
                    <TableHead className="w-[90px] text-right">向量分</TableHead>
                    <TableHead className="w-[90px] text-right">综合分</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {debugResult.items.map((item) => (
                    <TableRow key={`${item.doc_id}-${item.start_line}-${item.end_line}-${item.citation}`}>
                      <TableCell className="font-mono">{item.doc_id}</TableCell>
                      <TableCell>
                        <p className="font-mono text-[11px] text-muted-foreground">{item.citation || "-"}</p>
                        <p className="mt-1 line-clamp-2 text-xs text-foreground">{item.chunk_text || "-"}</p>
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {item.text_score.toFixed(3)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {item.vector_score.toFixed(3)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs font-semibold">
                        {item.final_score.toFixed(3)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <ViewState
              type="empty"
              title="调试无命中"
              description="请调整 query 或降低最小分数后重试。"
            />
          )
        ) : null}
      </CardContent>
    </Card>
  );
}
