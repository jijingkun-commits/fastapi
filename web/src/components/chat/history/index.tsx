/**
 * 对话历史组件（中文注释）
 *
 * 显示用户的对话历史列表，支持：
 * - 查看对话历史
 * - 切换对话
 * - 删除对话
 * - 重命名对话
 * - 批量删除对话
 */
import { Button } from "@/components/ui/button";
import { useThreads, Thread } from "@/providers/Thread";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";
import { useQueryState } from "nuqs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  PanelRightOpen,
  PanelRightClose,
  Trash2,
  Edit2,
  Check,
  X,
  MessageSquare,
  CheckSquare,
  Square,
  Search,
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
} from "lucide-react";
import { useChatHistoryOpen } from "@/hooks/useChatHistoryOpen";
import { toast } from "sonner";
import { deleteThreadsBatch } from "@/lib/backend";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  onSelect: (threadId: string) => void;
  onDelete: (threadId: string) => void;
  onRename: (threadId: string, title: string) => void;
  isSelectMode?: boolean;
  isSelected?: boolean;
  onToggleSelect?: (threadId: string) => void;
}

interface ThreadGroup {
  label: string;
  threads: Thread[];
}

function getThreadTimestamp(thread: Thread) {
  const source = thread.updated_at || thread.created_at;
  if (!source) {
    return 0;
  }

  const timestamp = new Date(source).getTime();
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function groupThreadsByTime(threads: Thread[]): ThreadGroup[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterday = today - 24 * 60 * 60 * 1000;
  const sevenDaysAgo = today - 7 * 24 * 60 * 60 * 1000;
  const thirtyDaysAgo = today - 30 * 24 * 60 * 60 * 1000;

  const groups: ThreadGroup[] = [
    { label: "今天", threads: [] },
    { label: "昨天", threads: [] },
    { label: "最近 7 天", threads: [] },
    { label: "最近 30 天", threads: [] },
    { label: "更早", threads: [] },
  ];

  [...threads]
    .sort((left, right) => getThreadTimestamp(right) - getThreadTimestamp(left))
    .forEach((thread) => {
      const timestamp = getThreadTimestamp(thread);
      if (timestamp >= today) {
        groups[0].threads.push(thread);
      } else if (timestamp >= yesterday) {
        groups[1].threads.push(thread);
      } else if (timestamp >= sevenDaysAgo) {
        groups[2].threads.push(thread);
      } else if (timestamp >= thirtyDaysAgo) {
        groups[3].threads.push(thread);
      } else {
        groups[4].threads.push(thread);
      }
    });

  return groups.filter((group) => group.threads.length > 0);
}

function ThreadItem({
  thread,
  isActive,
  onSelect,
  onDelete,
  onRename,
  isSelectMode = false,
  isSelected = false,
  onToggleSelect,
}: ThreadItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(thread.title);

  const handleRename = async () => {
    if (editTitle.trim() && editTitle !== thread.title) {
      try {
        await onRename(thread.thread_id, editTitle.trim());
        toast.success("标题已更新");
      } catch {
        toast.error("更新标题失败");
        setEditTitle(thread.title);
      }
    }
    setIsEditing(false);
  };

  const confirmDelete = async () => {
    if (!confirm("确定要删除这个对话吗？")) {
      return;
    }

    try {
      await onDelete(thread.thread_id);
      toast.success("对话已删除");
    } catch {
      toast.error("删除对话失败");
    }
  };

  const handleDelete = async (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    await confirmDelete();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      void handleRename();
    } else if (event.key === "Escape") {
      setEditTitle(thread.title);
      setIsEditing(false);
    }
  };

  const handleClick = () => {
    if (isSelectMode && onToggleSelect) {
      onToggleSelect(thread.thread_id);
      return;
    }

    onSelect(thread.thread_id);
  };

  const isEmphasized = isActive || isSelected;
  const actionButtonClassName = isEmphasized
    ? "app-sidebar-action text-[var(--app-sidebar-item-active-fg)]"
    : "app-sidebar-action";
  const deleteButtonClassName = isEmphasized
    ? "app-sidebar-action text-rose-600"
    : "app-sidebar-action text-rose-500/80";

  return (
    <div className="w-full">
      <div
        className={cn(
          "app-sidebar-item app-sidebar-entry group relative flex w-full cursor-pointer items-center gap-2.5 px-2.5 py-2",
          isEmphasized && "app-sidebar-item-active",
        )}
        role="button"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            handleClick();
          }
        }}
      >
        {isSelectMode ? (
          <Checkbox
            checked={isSelected}
            onClick={(event) => event.stopPropagation()}
            onCheckedChange={() => onToggleSelect?.(thread.thread_id)}
            className="mr-1 h-4 w-4 shrink-0"
          />
        ) : null}

        {isEditing ? (
          <div className="flex flex-1 items-center gap-1" onClick={(event) => event.stopPropagation()}>
            <Input
              value={editTitle}
              onChange={(event) => setEditTitle(event.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={() => void handleRename()}
              className="h-8 flex-1 rounded-xl border-black/[0.08] bg-white text-sm shadow-none focus-visible:ring-0"
              autoFocus
            />
            <Button
              variant="ghost"
              size="icon"
              className={cn("h-7 w-7 rounded-xl", actionButtonClassName)}
              onClick={(event) => {
                event.stopPropagation();
                void handleRename();
              }}
            >
              <Check className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={cn("h-7 w-7 rounded-xl", actionButtonClassName)}
              onClick={(event) => {
                event.stopPropagation();
                setEditTitle(thread.title);
                setIsEditing(false);
              }}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : (
          <>
            <div
              className={cn(
                "min-w-0 flex-1 truncate text-left text-[var(--chat-ui-font-sm)] leading-5 transition-[padding,color] duration-150",
                !isSelectMode && "pr-2 group-hover:pr-8",
                isEmphasized ? "font-normal text-[var(--app-sidebar-item-active-fg)]" : "font-normal text-[var(--app-sidebar-item-fg)]",
              )}
            >
              {thread.title || "新对话"}
            </div>

            {!isSelectMode && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn(
                      "app-sidebar-item app-sidebar-row-action absolute right-1.5 top-1/2 h-[26px] w-[26px] -translate-y-1/2 rounded-[10px] opacity-0 transition-opacity duration-150 group-hover:opacity-100",
                      isEmphasized && "opacity-100",
                    )}
                    onClick={(event) => event.stopPropagation()}
                    aria-label="更多操作"
                  >
                    <MoreHorizontal className="h-3.5 w-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="chat-popover-surface w-36 rounded-2xl p-1 font-sans">
                  <DropdownMenuItem
                    onClick={(event) => {
                      event.stopPropagation();
                      setIsEditing(true);
                    }}
                    className="mx-1 my-0.5 rounded-xl px-3 py-2 text-[var(--chat-ui-font-sm)] font-medium"
                  >
                    <Edit2 className="mr-2 h-4 w-4" />
                    重命名
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={(event) => {
                      event.stopPropagation();
                      void confirmDelete();
                    }}
                    className="mx-1 my-0.5 rounded-xl px-3 py-2 text-[var(--chat-ui-font-sm)] font-medium text-rose-600 focus:bg-rose-50 focus:text-rose-600"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    删除
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function ThreadList({
  threads,
  onThreadClick,
  isSelectMode,
  selectedIds,
  onToggleSelect,
  searchQuery,
}: {
  threads: Thread[];
  onThreadClick?: (threadId: string) => void;
  isSelectMode?: boolean;
  selectedIds?: Set<string>;
  onToggleSelect?: (threadId: string) => void;
  searchQuery?: string;
}) {
  const [threadId, setThreadId] = useQueryState("threadId");
  const { deleteThread, updateThreadTitle } = useThreads();
  const groupedThreads = useMemo(() => groupThreadsByTime(threads), [threads]);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    今天: true,
    昨天: true,
    "最近 7 天": true,
    "最近 30 天": true,
    更早: true,
  });

  const isSearching = Boolean(searchQuery?.trim());

  const handleSelect = (id: string) => {
    onThreadClick?.(id);
    if (id !== threadId) {
      setThreadId(id);
    }
  };

  const toggleGroup = (label: string) => {
    if (isSearching) {
      return;
    }

    setExpandedGroups((previous) => ({
      ...previous,
      [label]: !(previous[label] ?? true),
    }));
  };

  if (threads.length === 0) {
    const isSearchingEmpty = Boolean(searchQuery?.trim());
    return (
      <div className="mx-4 mt-3 flex min-h-28 flex-col items-center justify-center gap-2 rounded-3xl border border-black/[0.05] bg-white px-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-black/[0.03] text-[var(--app-sidebar-empty-icon)]">
          {isSearchingEmpty ? <Search className="h-5 w-5" /> : <MessageSquare className="h-5 w-5" />}
        </div>
        <div>
          <p className="text-sm font-medium text-[var(--app-sidebar-item-active-fg)]">{isSearchingEmpty ? "没有找到相关对话" : "还没有历史对话"}</p>
          <p className="mt-1 text-xs text-[var(--app-sidebar-title)]">{isSearchingEmpty ? "换个关键词试试。" : "发起一次对话后，这里会自动出现。"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-scrollable flex h-full w-full flex-col items-start justify-start gap-0.5 overflow-y-auto px-2.5 pb-2.5 pt-1">
      {groupedThreads.map((group) => {
        const isExpanded = isSearching ? true : (expandedGroups[group.label] ?? true);

        return (
          <div key={group.label} className="w-full">
            <button
              type="button"
              className={cn(
                "app-sidebar-section-toggle w-full",
                isSearching && "cursor-default opacity-90",
              )}
              onClick={() => toggleGroup(group.label)}
              aria-expanded={isExpanded}
              aria-controls={`thread-group-${group.label}`}
              disabled={isSearching}
            >
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 shrink-0" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 shrink-0" />
              )}
              <span>{group.label}</span>
              <span className="app-sidebar-section-count">{group.threads.length}</span>
            </button>
            {isExpanded ? (
              <div id={`thread-group-${group.label}`} className="flex flex-col gap-0.5">
                {group.threads.map((thread) => (
                  <ThreadItem
                    key={thread.thread_id}
                    thread={thread}
                    isActive={thread.thread_id === threadId}
                    onSelect={handleSelect}
                    onDelete={deleteThread}
                    onRename={updateThreadTitle}
                    isSelectMode={isSelectMode}
                    isSelected={selectedIds?.has(thread.thread_id)}
                    onToggleSelect={onToggleSelect}
                  />
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function ThreadHistoryLoading() {
  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-1 overflow-y-auto px-3 pb-3 pt-1.5">
      {Array.from({ length: 8 }).map((_, index) => (
        <Skeleton key={`skeleton-${index}`} className="h-10 w-full rounded-2xl bg-black/[0.05]" />
      ))}
    </div>
  );
}

export default function ThreadHistory() {
  const { chatHistoryOpen, setChatHistoryOpen, isLargeScreen } = useChatHistoryOpen();
  const { threads, threadsLoading, ensureThreadsLoaded, refreshThreads } = useThreads();

  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchVisible, setSearchVisible] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      void ensureThreadsLoaded();
    }
  }, [ensureThreadsLoaded]);

  useEffect(() => {
    if (!searchVisible) {
      return;
    }

    const timer = window.setTimeout(() => {
      searchInputRef.current?.focus();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [searchVisible]);

  const filteredThreads = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return threads;
    }

    return threads.filter((thread) =>
      thread.title?.toLowerCase().includes(normalizedQuery),
    );
  }, [threads, searchQuery]);

  const openSearch = () => {
    setSearchVisible(true);
  };

  const closeSearch = () => {
    setSearchQuery("");
    setSearchVisible(false);
  };

  const visibleThreadIds = filteredThreads.map((thread) => thread.thread_id);
  const selectedVisibleCount = visibleThreadIds.filter((threadId) => selectedIds.has(threadId)).length;

  const handleToggleSelect = (threadId: string) => {
    setSelectedIds((previous) => {
      const next = new Set(previous);
      if (next.has(threadId)) {
        next.delete(threadId);
      } else {
        next.add(threadId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (filteredThreads.length === 0) {
      return;
    }

    setSelectedIds((previous) => {
      const next = new Set(previous);
      const shouldClearVisible = selectedVisibleCount === filteredThreads.length;

      visibleThreadIds.forEach((threadId) => {
        if (shouldClearVisible) {
          next.delete(threadId);
        } else {
          next.add(threadId);
        }
      });

      return next;
    });
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) {
      return;
    }

    if (!confirm(`确定要删除选中的 ${selectedIds.size} 个对话吗？此操作不可恢复。`)) {
      return;
    }

    setIsDeleting(true);
    try {
      await deleteThreadsBatch(Array.from(selectedIds));
      toast.success(`已删除 ${selectedIds.size} 个对话`);
      setSelectedIds(new Set());
      setIsSelectMode(false);
      await refreshThreads();
    } catch (error: any) {
      toast.error(error.message || "批量删除失败");
    } finally {
      setIsDeleting(false);
    }
  };

  const enterSelectMode = () => {
    setSearchVisible(false);
    setIsSelectMode(true);
  };

  const exitSelectMode = () => {
    setIsSelectMode(false);
    setSelectedIds(new Set());
  };

  const renderSidebarHeader = (isMobile = false) => (
    <div className="w-full">
      {isSelectMode ? (
        <div className={cn("app-sidebar-header-row app-sidebar-manage-header", isMobile && "pr-10")}>
          <div className="app-sidebar-inline-manage-shell">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="app-sidebar-inline-manage-toggle"
              onClick={handleSelectAll}
            >
              {selectedVisibleCount === filteredThreads.length && filteredThreads.length > 0 ? (
                <CheckSquare className="mr-1.5 h-4 w-4" />
              ) : (
                <Square className="mr-1.5 h-4 w-4" />
              )}
              {selectedVisibleCount === filteredThreads.length && filteredThreads.length > 0 ? "取消全选" : "全选"}
            </Button>

            <span className="app-sidebar-inline-manage-count">
              {selectedVisibleCount} / {filteredThreads.length}
            </span>

            {selectedIds.size > 0 ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="app-sidebar-inline-manage-delete"
                onClick={handleBatchDelete}
                disabled={isDeleting}
              >
                <Trash2 className="mr-1.5 h-4 w-4" />
                {isDeleting ? "删除中..." : `删除 ${selectedIds.size}`}
              </Button>
            ) : <div className="min-w-0 flex-1" />}

            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="app-sidebar-inline-manage-done"
              onClick={exitSelectMode}
            >
              完成
            </Button>
          </div>
          {!isMobile && (
            <Button
              variant="ghost"
              size="icon"
              className="app-sidebar-item app-sidebar-toggle h-[34px] w-[34px] rounded-[11px]"
              onClick={() => setChatHistoryOpen((open) => !open)}
              title="收起侧边栏"
              aria-label="收起侧边栏"
            >
              {chatHistoryOpen ? <PanelRightOpen className="size-4.5" /> : <PanelRightClose className="size-4.5" />}
            </Button>
          )}
        </div>
      ) : searchVisible || searchQuery.trim() ? (
        <div className={cn("app-sidebar-header-row app-sidebar-search-header", isMobile && "pr-10")}>
          <div className="app-sidebar-inline-search-shell">
            <Search className="app-sidebar-inline-search-icon h-4 w-4" />
            <Input
              ref={searchInputRef}
              placeholder="搜索对话..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="app-sidebar-inline-search-input placeholder:text-[var(--app-sidebar-title)]"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="app-sidebar-inline-search-close"
              onClick={closeSearch}
              title="关闭搜索"
              aria-label="关闭搜索"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          {!isMobile && (
            <Button
              variant="ghost"
              size="icon"
              className="app-sidebar-item app-sidebar-toggle h-[34px] w-[34px] rounded-[11px]"
              onClick={() => setChatHistoryOpen((open) => !open)}
              title="收起侧边栏"
              aria-label="收起侧边栏"
            >
              {chatHistoryOpen ? <PanelRightOpen className="size-4.5" /> : <PanelRightClose className="size-4.5" />}
            </Button>
          )}
        </div>
      ) : (
        <div className={cn("app-sidebar-header-row", isMobile && "pr-10")}>
          <div className="app-sidebar-brand">
            <div className="app-sidebar-brand-mark">
              <img
                src="/logo.png"
                alt="嘉银助手"
                className="h-[22px] w-[22px] object-contain"
                onError={(event) => {
                  event.currentTarget.src = "/favicon.ico";
                }}
              />
            </div>
            <div className="min-w-0">
              <p className="app-sidebar-brand-text truncate font-sans">嘉银助手</p>
            </div>
          </div>
          <div className={cn("app-sidebar-header-actions", isMobile && "pr-0")}>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="app-sidebar-item app-sidebar-header-icon h-[34px] w-[34px] rounded-[11px]"
              onClick={openSearch}
              title="搜索对话"
              aria-label="搜索对话"
            >
              <Search className="h-4.5 w-4.5" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="app-sidebar-item app-sidebar-header-icon h-[34px] w-[34px] rounded-[11px]"
              onClick={enterSelectMode}
              title="对话管理"
              aria-label="对话管理"
            >
              <CheckSquare className="h-4.5 w-4.5" />
            </Button>
            {!isMobile && (
              <Button
                variant="ghost"
                size="icon"
                className="app-sidebar-item app-sidebar-toggle h-[34px] w-[34px] rounded-[11px]"
                onClick={() => setChatHistoryOpen((open) => !open)}
                title="收起侧边栏"
                aria-label="收起侧边栏"
              >
                {chatHistoryOpen ? <PanelRightOpen className="size-4.5" /> : <PanelRightClose className="size-4.5" />}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );

  const renderSearchBox = () => null;

  return (
    <>
      <div className="app-sidebar-surface shadow-inner-right hidden h-screen w-[300px] shrink-0 flex-col items-start justify-start border-r lg:flex lg:pr-0">
        {renderSidebarHeader()}
        {threadsLoading ? (
          <ThreadHistoryLoading />
        ) : (
          <ThreadList
            threads={filteredThreads}
            isSelectMode={isSelectMode}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelect}
            searchQuery={searchQuery}
          />
        )}
      </div>

      <div className="lg:hidden">
        <Sheet
          open={!!chatHistoryOpen && !isLargeScreen}
          onOpenChange={(open) => {
            if (isLargeScreen) {
              return;
            }
            setChatHistoryOpen(open);
            if (!open) {
              exitSelectMode();
            }
          }}
        >
          <SheetContent side="left" className="app-sidebar-surface flex w-[85vw] max-w-[300px] flex-col p-0 lg:hidden">
            <SheetHeader className="px-0 py-0">
              <SheetTitle className="sr-only">对话列表</SheetTitle>
              {renderSidebarHeader(true)}
            </SheetHeader>
            {threadsLoading ? (
              <ThreadHistoryLoading />
            ) : (
              <ThreadList
                threads={filteredThreads}
                onThreadClick={() => {
                  if (!isSelectMode) {
                    setChatHistoryOpen(false);
                  }
                }}
                isSelectMode={isSelectMode}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
                searchQuery={searchQuery}
              />
            )}
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
