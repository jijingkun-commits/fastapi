"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";

import { MemoryDetailDrawer } from "@/components/admin/memory/MemoryDetailDrawer";
import { MemorySearchDebugPanel } from "@/components/admin/memory/MemorySearchDebugPanel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ViewState } from "@/components/ui/view-state";
import {
  archiveMemory,
  deleteMemory,
  getMemoryOverview,
  listMemories,
} from "@/lib/memory-admin-api";
import type {
  MemoryListItem,
  MemoryListParams,
  MemoryOverviewResponse,
} from "@/types/memory-admin";

type ListViewState = "loading" | "ready" | "empty" | "error";
type FeedbackTone = "success" | "warning" | "error";

interface MemoryFilterDraft {
  userId: string;
  docKind: string;
  status: string;
  source: string;
  keyword: string;
  updatedFrom: string;
  updatedTo: string;
}

interface ActionFeedback {
  tone: FeedbackTone;
  title: string;
  message: string;
}

const DEFAULT_FILTERS: MemoryFilterDraft = {
  userId: "",
  docKind: "",
  status: "active",
  source: "",
  keyword: "",
  updatedFrom: "",
  updatedTo: "",
};

const PAGE_SIZE = 20;

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

function buildListParams(
  filterDraft: MemoryFilterDraft,
  page: number,
  pageSize: number,
): MemoryListParams {
  return {
    user_id: parseOptionalPositiveInt(filterDraft.userId),
    doc_kind: filterDraft.docKind.trim() || undefined,
    status: filterDraft.status === "all" ? undefined : filterDraft.status,
    source: filterDraft.source.trim() || undefined,
    keyword: filterDraft.keyword.trim() || undefined,
    updated_from: filterDraft.updatedFrom ? `${filterDraft.updatedFrom}T00:00:00` : undefined,
    updated_to: filterDraft.updatedTo ? `${filterDraft.updatedTo}T23:59:59` : undefined,
    page,
    page_size: pageSize,
  };
}

function resolveStatusBadgeClass(status: string): string {
  if (status === "active") {
    return "border-emerald-300 bg-emerald-50 text-emerald-700";
  }
  if (status === "archived") {
    return "border-amber-300 bg-amber-50 text-amber-700";
  }
  return "";
}

function resolveFeedbackAlertClass(tone: FeedbackTone): string {
  if (tone === "success") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (tone === "warning") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  return "border-destructive/40 bg-destructive/10 text-destructive";
}

export function MemoryAdminPanel() {
  const [activeTab, setActiveTab] = useState<"list" | "debug">("list");
  const [filterDraft, setFilterDraft] = useState<MemoryFilterDraft>({ ...DEFAULT_FILTERS });
  const [appliedFilters, setAppliedFilters] = useState<MemoryFilterDraft>({ ...DEFAULT_FILTERS });
  const [page, setPage] = useState(1);

  const [items, setItems] = useState<MemoryListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [viewState, setViewState] = useState<ListViewState>("loading");
  const [listErrorMessage, setListErrorMessage] = useState("");

  const [overview, setOverview] = useState<MemoryOverviewResponse | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);

  const [feedback, setFeedback] = useState<ActionFeedback | null>(null);
  const [selectedMemory, setSelectedMemory] = useState<{ memoryId: number; userId: number } | null>(null);

  const totalPages = useMemo(() => {
    if (total <= 0) {
      return 1;
    }
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }, [total]);

  const appliedUserId = useMemo(() => parseOptionalPositiveInt(appliedFilters.userId), [appliedFilters.userId]);

  const loadList = useCallback(async () => {
    setViewState("loading");
    setListErrorMessage("");
    try {
      const payload = await listMemories(buildListParams(appliedFilters, page, PAGE_SIZE));
      setItems(payload.items);
      setTotal(payload.total);
      setViewState(payload.items.length > 0 ? "ready" : "empty");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "加载记忆列表失败";
      setListErrorMessage(message);
      setViewState("error");
      toast.error(message);
    }
  }, [appliedFilters, page]);

  const loadOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const payload = await getMemoryOverview(8);
      setOverview(payload);
    } catch {
      setOverview(null);
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadList(), loadOverview()]);
  }, [loadList, loadOverview]);

  const runArchive = useCallback(async (memoryId: number, targetUserId?: number) => {
    try {
      const payload = await archiveMemory(memoryId, { user_id: targetUserId });
      let tone: FeedbackTone = "success";
      let title = "归档完成";
      let message = `记忆 ${memoryId} 已归档。`;

      if (!payload.found) {
        tone = "warning";
        title = "归档未生效";
        message = `记忆 ${memoryId} 不存在，可能已被删除。`;
        toast.warning(message);
      } else if (!payload.changed) {
        tone = "warning";
        title = "归档已是最新";
        message = `记忆 ${memoryId} 已是归档状态，无需重复操作。`;
        toast.info(message);
      } else {
        toast.success(message);
      }

      setFeedback({ tone, title, message });
      await refreshAll();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "归档记忆失败";
      setFeedback({ tone: "error", title: "归档失败", message });
      toast.error(message);
      throw error;
    }
  }, [refreshAll]);

  const runDelete = useCallback(async (memoryId: number, targetUserId?: number) => {
    try {
      const payload = await deleteMemory(memoryId, { user_id: targetUserId });
      let tone: FeedbackTone = "success";
      let title = "删除完成";
      let message = `记忆 ${memoryId} 已删除，清理 chunks ${payload.deleted_chunks} 条。`;

      if (!payload.deleted) {
        tone = "warning";
        title = "删除未执行";
        message = `记忆 ${memoryId} 不存在，跳过删除。`;
        toast.warning(message);
      } else {
        toast.success(message);
      }

      setFeedback({ tone, title, message });
      if (selectedMemory?.memoryId === memoryId) {
        setSelectedMemory(null);
      }
      await refreshAll();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "删除记忆失败";
      setFeedback({ tone: "error", title: "删除失败", message });
      toast.error(message);
      throw error;
    }
  }, [refreshAll, selectedMemory?.memoryId]);

  const handleFilterApply = () => {
    setPage(1);
    setAppliedFilters(filterDraft);
  };

  const handleFilterReset = () => {
    setFilterDraft({ ...DEFAULT_FILTERS });
    setAppliedFilters({ ...DEFAULT_FILTERS });
    setPage(1);
  };

  const handleArchiveFromRow = async (row: MemoryListItem) => {
    const confirmed = window.confirm(`确认归档记忆 ${row.memory_id} 吗？`);
    if (!confirmed) {
      return;
    }
    await runArchive(row.memory_id, row.user_id);
  };

  const handleDeleteFromRow = async (row: MemoryListItem) => {
    const confirmed = window.confirm(
      `确认删除记忆 ${row.memory_id} 吗？该操作不可撤销，将级联删除分块。`,
    );
    if (!confirmed) {
      return;
    }
    await runDelete(row.memory_id, row.user_id);
  };

  const handleArchiveFromDrawer = async (memoryId: number, userId?: number) => {
    const confirmed = window.confirm(`确认归档记忆 ${memoryId} 吗？`);
    if (!confirmed) {
      return;
    }
    await runArchive(memoryId, userId);
  };

  const handleDeleteFromDrawer = async (memoryId: number, userId?: number) => {
    const confirmed = window.confirm(
      `确认删除记忆 ${memoryId} 吗？该操作不可撤销，将级联删除分块。`,
    );
    if (!confirmed) {
      return;
    }
    await runDelete(memoryId, userId);
  };

  const renderListArea = () => {
    if (viewState === "loading") {
      return <ViewState type="loading" title="加载记忆列表中" />;
    }
    if (viewState === "error") {
      return (
        <ViewState
          type="error"
          title="记忆列表加载失败"
          description={listErrorMessage}
          actionLabel="重新加载"
          onAction={() => {
            void loadList();
          }}
        />
      );
    }
    if (viewState === "empty") {
      return (
        <ViewState
          type="empty"
          title="暂无记忆数据"
          description="可尝试放宽筛选条件，或切换状态查看 archived 数据。"
        />
      );
    }

    return (
      <div className="space-y-3">
        <div className="overflow-hidden rounded-[var(--ds-radius-md)] border border-border/80">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[78px]">ID</TableHead>
                <TableHead>标题 / 摘要</TableHead>
                <TableHead className="w-[80px]">user_id</TableHead>
                <TableHead className="w-[90px]">类型</TableHead>
                <TableHead className="w-[100px]">状态</TableHead>
                <TableHead className="w-[90px]">revision</TableHead>
                <TableHead className="w-[120px]">chunks</TableHead>
                <TableHead className="w-[180px]">更新时间</TableHead>
                <TableHead className="w-[260px] min-w-[260px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.memory_id}>
                  <TableCell className="font-mono">{item.memory_id}</TableCell>
                  <TableCell>
                    <p className="font-medium text-foreground line-clamp-1">
                      {item.title || item.doc_key || `memory-${item.memory_id}`}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                      {item.summary_md || "-"}
                    </p>
                  </TableCell>
                  <TableCell className="font-mono">{item.user_id}</TableCell>
                  <TableCell>{item.doc_kind || "-"}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={resolveStatusBadgeClass(item.status)}>
                      {item.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono">{item.revision}</TableCell>
                  <TableCell className="text-xs">
                    <p>
                      {item.ready_chunks}/{item.chunk_total}
                    </p>
                    <p className="text-muted-foreground">failed {item.failed_chunks}</p>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDateTime(item.update_time)}
                  </TableCell>
                  <TableCell className="min-w-[260px]">
                    <div className="flex min-w-max flex-nowrap items-center gap-2 whitespace-nowrap">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setSelectedMemory({
                            memoryId: item.memory_id,
                            userId: item.user_id,
                          });
                        }}
                      >
                        详情
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={item.status === "archived"}
                        onClick={() => {
                          void handleArchiveFromRow(item);
                        }}
                      >
                        归档
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => {
                          void handleDeleteFromRow(item);
                        }}
                      >
                        删除
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            共 {total} 条，当前第 {page}/{totalPages} 页
          </p>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            >
              <ChevronLeft className="mr-1 h-4 w-4" />
              上一页
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
            >
              下一页
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="admin-page-content space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="app-page-title">用户个性化永久记忆</h1>
          <p className="app-page-subtitle mt-1">
            统一通过 `memory-admin-api` 完成列表筛选、详情抽屉与治理动作。
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => {
            void refreshAll();
          }}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </Button>
      </div>

      {overview ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>活跃用户</CardDescription>
              <CardTitle className="text-xl">{overview.totals.users}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>文档总数</CardDescription>
              <CardTitle className="text-xl">{overview.totals.documents}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>分块总数</CardDescription>
              <CardTitle className="text-xl">{overview.totals.chunks}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>向量状态</CardDescription>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                pending {overview.embedding_status.pending} / ready {overview.embedding_status.ready} /
                failed {overview.embedding_status.failed}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="py-4 text-sm text-muted-foreground">
            {overviewLoading ? "记忆总览加载中..." : "总览接口暂不可用，已自动降级为列表模式。"}
          </CardContent>
        </Card>
      )}

      {feedback ? (
        <Alert className={resolveFeedbackAlertClass(feedback.tone)}>
          <AlertTitle>{feedback.title}</AlertTitle>
          <AlertDescription>{feedback.message}</AlertDescription>
        </Alert>
      ) : null}

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "list" | "debug")}>
        <TabsList>
          <TabsTrigger value="list">记忆列表</TabsTrigger>
          <TabsTrigger value="debug">调试与治理</TabsTrigger>
        </TabsList>

        <TabsContent value="list" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">筛选条件</CardTitle>
              <CardDescription>支持 user_id / doc_kind / status / source / 日期 / 关键词过滤。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="space-y-2">
                  <Label htmlFor="memory-filter-user-id">user_id</Label>
                  <Input
                    id="memory-filter-user-id"
                    value={filterDraft.userId}
                    onChange={(event) =>
                      setFilterDraft((prev) => ({ ...prev, userId: event.target.value }))
                    }
                    placeholder="例如 1001"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="memory-filter-doc-kind">doc_kind</Label>
                  <Input
                    id="memory-filter-doc-kind"
                    value={filterDraft.docKind}
                    onChange={(event) =>
                      setFilterDraft((prev) => ({ ...prev, docKind: event.target.value }))
                    }
                    placeholder="daily / preference"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="memory-filter-status">status</Label>
                  <Select
                    value={filterDraft.status}
                    onValueChange={(value) =>
                      setFilterDraft((prev) => ({ ...prev, status: value }))
                    }
                  >
                    <SelectTrigger id="memory-filter-status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">active</SelectItem>
                      <SelectItem value="archived">archived</SelectItem>
                      <SelectItem value="all">all</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="memory-filter-source">source</Label>
                  <Input
                    id="memory-filter-source"
                    value={filterDraft.source}
                    onChange={(event) =>
                      setFilterDraft((prev) => ({ ...prev, source: event.target.value }))
                    }
                    placeholder="memory"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="space-y-2 xl:col-span-2">
                  <Label htmlFor="memory-filter-keyword">keyword</Label>
                  <Input
                    id="memory-filter-keyword"
                    value={filterDraft.keyword}
                    onChange={(event) =>
                      setFilterDraft((prev) => ({ ...prev, keyword: event.target.value }))
                    }
                    placeholder="标题、key 或正文关键词"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="memory-filter-updated-from">updated_from</Label>
                  <Input
                    id="memory-filter-updated-from"
                    type="date"
                    value={filterDraft.updatedFrom}
                    onChange={(event) =>
                      setFilterDraft((prev) => ({ ...prev, updatedFrom: event.target.value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="memory-filter-updated-to">updated_to</Label>
                  <Input
                    id="memory-filter-updated-to"
                    type="date"
                    value={filterDraft.updatedTo}
                    onChange={(event) =>
                      setFilterDraft((prev) => ({ ...prev, updatedTo: event.target.value }))
                    }
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button onClick={handleFilterApply}>
                  <Search className="mr-1.5 h-4 w-4" />
                  查询
                </Button>
                <Button variant="outline" onClick={handleFilterReset}>
                  重置
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    void loadList();
                  }}
                >
                  仅刷新列表
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">记忆列表</CardTitle>
            </CardHeader>
            <CardContent>{renderListArea()}</CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="debug" className="space-y-4">
          <MemorySearchDebugPanel
            defaultUserId={appliedUserId}
            onGovernanceActionDone={() => {
              void refreshAll();
            }}
          />
        </TabsContent>
      </Tabs>

      <MemoryDetailDrawer
        open={Boolean(selectedMemory)}
        memoryId={selectedMemory?.memoryId ?? null}
        userId={selectedMemory?.userId}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedMemory(null);
          }
        }}
        onArchive={handleArchiveFromDrawer}
        onDelete={handleDeleteFromDrawer}
      />
    </div>
  );
}
