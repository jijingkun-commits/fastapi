"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { getMemoryChunks, getMemoryDetail } from "@/lib/memory-admin-api";
import type { MemoryChunkItem, MemoryChunkListResponse, MemoryDetail } from "@/types/memory-admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ViewState } from "@/components/ui/view-state";
import { getMemoryDocKindLabel, getMemoryStatusLabel } from "@/lib/memory-admin-labels";

interface MemoryDetailDrawerProps {
  open: boolean;
  memoryId: number | null;
  userId?: number;
  onOpenChange: (open: boolean) => void;
  onArchive?: (memoryId: number, userId?: number) => Promise<void>;
  onDelete?: (memoryId: number, userId?: number) => Promise<void>;
}

type ChunkFilter = "all" | "pending" | "ready" | "failed";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

export function MemoryDetailDrawer({
  open,
  memoryId,
  userId,
  onOpenChange,
  onArchive,
  onDelete,
}: MemoryDetailDrawerProps) {
  const [detail, setDetail] = useState<MemoryDetail | null>(null);
  const [chunks, setChunks] = useState<MemoryChunkItem[]>([]);
  const [chunkPagination, setChunkPagination] = useState<Pick<
    MemoryChunkListResponse,
    "total" | "page" | "page_size"
  >>({
    total: 0,
    page: 1,
    page_size: 50,
  });
  const [chunkFilter, setChunkFilter] = useState<ChunkFilter>("all");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [archiving, setArchiving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const requestIdRef = useRef(0);

  const maxChunkPage = useMemo(() => {
    if (chunkPagination.total <= 0) {
      return 1;
    }
    return Math.max(1, Math.ceil(chunkPagination.total / chunkPagination.page_size));
  }, [chunkPagination.page_size, chunkPagination.total]);

  const loadDrawerData = useCallback(async () => {
    if (!open || !memoryId) {
      return;
    }

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setLoading(true);
    setErrorMessage("");

    try {
      const [detailPayload, chunkPayload] = await Promise.all([
        getMemoryDetail(memoryId, { user_id: userId }),
        getMemoryChunks(memoryId, {
          user_id: userId,
          embedding_status: chunkFilter === "all" ? undefined : chunkFilter,
          page: chunkPagination.page,
          page_size: chunkPagination.page_size,
        }),
      ]);

      if (requestId !== requestIdRef.current) {
        return;
      }

      setDetail(detailPayload);
      setChunks(chunkPayload.items);
      setChunkPagination((prev) => ({
        ...prev,
        total: chunkPayload.total,
        page: chunkPayload.page,
        page_size: chunkPayload.page_size,
      }));
    } catch (error: unknown) {
      if (requestId !== requestIdRef.current) {
        return;
      }
      const message = error instanceof Error ? error.message : "加载记忆详情失败";
      setErrorMessage(message);
      toast.error(message);
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [chunkFilter, chunkPagination.page, chunkPagination.page_size, memoryId, open, userId]);

  useEffect(() => {
    if (!open) {
      return;
    }
    void loadDrawerData();
  }, [loadDrawerData, open]);

  useEffect(() => {
    if (!open) {
      setDetail(null);
      setChunks([]);
      setErrorMessage("");
      setChunkFilter("all");
      setChunkPagination({
        total: 0,
        page: 1,
        page_size: 50,
      });
    }
  }, [open]);

  const handleArchive = async () => {
    if (!detail || !onArchive) {
      return;
    }
    setArchiving(true);
    try {
      await onArchive(detail.memory_id, detail.user_id);
      await loadDrawerData();
    } finally {
      setArchiving(false);
    }
  };

  const handleDelete = async () => {
    if (!detail || !onDelete) {
      return;
    }
    setDeleting(true);
    try {
      await onDelete(detail.memory_id, detail.user_id);
      onOpenChange(false);
    } finally {
      setDeleting(false);
    }
  };

  const renderDrawerBody = () => {
    if (loading && !detail) {
      return <ViewState type="loading" title="加载详情中" className="min-h-[280px]" />;
    }

    if (errorMessage && !detail) {
      return (
        <ViewState
          type="error"
          title="记忆详情加载失败"
          description={errorMessage}
          actionLabel="重试"
          onAction={() => {
            void loadDrawerData();
          }}
          className="min-h-[280px]"
        />
      );
    }

    if (!detail) {
      return (
        <ViewState
          type="empty"
          title="未找到记忆详情"
          description="该记忆可能已被删除或无访问权限。"
          className="min-h-[280px]"
        />
      );
    }

    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-border/80 bg-muted/30 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">记忆编号 {detail.memory_id}</Badge>
            <Badge variant="outline">用户编号 {detail.user_id}</Badge>
            <Badge variant="outline">{getMemoryDocKindLabel(detail.doc_kind)}</Badge>
            <Badge variant="outline">{getMemoryStatusLabel(detail.status)}</Badge>
            <Badge variant="outline">版本 {detail.revision}</Badge>
          </div>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 mt-3 text-xs text-muted-foreground">
            <dt>来源</dt>
            <dd className="text-foreground">{detail.source}</dd>
            <dt>范围</dt>
            <dd className="text-foreground">{detail.scope_ref || detail.scope || "-"}</dd>
            <dt>创建时间</dt>
            <dd className="text-foreground">{formatDateTime(detail.create_time)}</dd>
            <dt>更新时间</dt>
            <dd className="text-foreground">{formatDateTime(detail.update_time)}</dd>
            <dt>分块状态</dt>
            <dd className="text-foreground">
              总分块 {detail.chunk_total} / 已就绪 {detail.ready_chunks} / 失败 {detail.failed_chunks}
            </dd>
          </dl>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">正文</p>
          <pre className="max-h-56 overflow-y-auto rounded-lg border border-border/80 bg-muted/30 p-3 text-xs leading-5 whitespace-pre-wrap break-words">
            {detail.content_md || "(无正文)"}
          </pre>
        </div>

        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium text-foreground">分块状态</p>
            <Select
              value={chunkFilter}
              onValueChange={(value) => {
                setChunkFilter(value as ChunkFilter);
                setChunkPagination((prev) => ({ ...prev, page: 1 }));
              }}
            >
              <SelectTrigger className="h-8 w-[160px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="pending">待处理</SelectItem>
                <SelectItem value="ready">已就绪</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
              </SelectContent>
            </Select>

            <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
              <span>
                第 {chunkPagination.page}/{maxChunkPage} 页，共 {chunkPagination.total} 条
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={loading || chunkPagination.page <= 1}
                onClick={() => {
                  setChunkPagination((prev) => ({ ...prev, page: Math.max(1, prev.page - 1) }));
                }}
              >
                上一页
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={loading || chunkPagination.page >= maxChunkPage}
                onClick={() => {
                  setChunkPagination((prev) => ({
                    ...prev,
                    page: Math.min(maxChunkPage, prev.page + 1),
                  }));
                }}
              >
                下一页
              </Button>
            </div>
          </div>

          {chunks.length === 0 ? (
            <ViewState
              type="empty"
              title="暂无分块数据"
              description="当前筛选条件下无分块记录。"
              className="min-h-[180px]"
            />
          ) : (
            <div className="max-h-72 overflow-auto rounded-[var(--ds-radius-md)] border border-border/80">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[64px]">#</TableHead>
                    <TableHead className="w-[110px]">行号</TableHead>
                    <TableHead>内容</TableHead>
                    <TableHead className="w-[90px]">状态</TableHead>
                    <TableHead className="w-[90px] text-right">重试</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {chunks.map((chunk) => (
                    <TableRow key={chunk.chunk_id}>
                      <TableCell className="font-mono">{chunk.chunk_no}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        L{chunk.start_line}-L{chunk.end_line}
                      </TableCell>
                      <TableCell>
                        <p className="line-clamp-2 text-xs leading-5">{chunk.chunk_text || "-"}</p>
                        {chunk.embedding_error ? (
                          <p className="mt-1 text-[11px] text-destructive">{chunk.embedding_error}</p>
                        ) : null}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{chunk.embedding_status}</Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {chunk.embedding_retry_count}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-3xl">
        <SheetHeader className="border-b border-border/70 px-6 py-4">
          <SheetTitle>记忆详情抽屉</SheetTitle>
          <SheetDescription>展示正文、分块状态与治理动作入口。</SheetDescription>
        </SheetHeader>

        <div className="flex h-full flex-col">
          <div className="flex items-center gap-2 border-b border-border/70 px-6 py-3">
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              disabled={loading}
              onClick={() => {
                void loadDrawerData();
              }}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              刷新
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={!detail || !onArchive || archiving}
              onClick={() => void handleArchive()}
            >
              {archiving ? "归档中..." : "归档记忆"}
            </Button>
            <Button
              size="sm"
              variant="destructive"
              disabled={!detail || !onDelete || deleting}
              onClick={() => void handleDelete()}
            >
              {deleting ? "删除中..." : "删除记忆"}
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-4">{renderDrawerBody()}</div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
