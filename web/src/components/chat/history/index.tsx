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
import { useEffect, useState } from "react";
import { useQueryState, parseAsBoolean } from "nuqs";
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
} from "lucide-react";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { toast } from "sonner";
import { deleteThreadsBatch } from "@/lib/backend";
import { cn } from "@/lib/utils";

interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  onSelect: (threadId: string) => void;
  onDelete: (threadId: string) => void;
  onRename: (threadId: string, title: string) => void;
  // 批量选择相关
  isSelectMode?: boolean;
  isSelected?: boolean;
  onToggleSelect?: (threadId: string) => void;
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
  const [isHovered, setIsHovered] = useState(false);

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

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("确定要删除这个对话吗？")) {
      try {
        await onDelete(thread.thread_id);
        toast.success("对话已删除");
      } catch {
        toast.error("删除对话失败");
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleRename();
    } else if (e.key === "Escape") {
      setEditTitle(thread.title);
      setIsEditing(false);
    }
  };

  const handleClick = () => {
    if (isSelectMode && onToggleSelect) {
      onToggleSelect(thread.thread_id);
    } else {
      onSelect(thread.thread_id);
    }
  };

  return (
    <div
      className="w-full"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={cn(
          "app-sidebar-item group relative flex w-full items-center rounded-lg px-3 py-2.5 transition-all duration-150",
          (isSelected || isActive) && "app-sidebar-item-active"
        )}
        role="button"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleClick();
          }
        }}
      >
        {/* 批量选择模式：显示 Checkbox */}
        {isSelectMode ? (
          <Checkbox
            checked={isSelected}
            onClick={(e) => e.stopPropagation()}
            onCheckedChange={() => onToggleSelect?.(thread.thread_id)}
            className="mr-2.5 h-4 w-4 shrink-0"
          />
        ) : (
          <div className={cn(
            "mr-2.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
            isActive || isSelected
              ? "app-sidebar-icon-pill"
              : "app-sidebar-icon bg-white/70"
          )}>
            <MessageSquare className="h-3.5 w-3.5" />
          </div>
        )}

        {isEditing ? (
          <div
            className="flex flex-1 items-center gap-1"
            onClick={(e) => e.stopPropagation()}
          >
            <Input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleRename}
              className="h-7 flex-1 text-sm"
              autoFocus
            />
            <Button
              variant="ghost"
              size="icon"
              className="app-sidebar-item h-7 w-7 hover:text-[var(--app-sidebar-icon-active)]"
              onClick={(e) => {
                e.stopPropagation();
                void handleRename();
              }}
            >
              <Check className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="app-sidebar-item h-7 w-7"
              onClick={(e) => {
                e.stopPropagation();
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
              className={`flex-1 truncate text-left text-[13px] leading-snug ${
                isActive || isSelected
                  ? "font-medium text-[var(--app-sidebar-item-active-fg)]"
                  : "text-[var(--app-sidebar-item-fg)]"
              }`}
            >
              {thread.title || "新对话"}
            </div>

            {/* 操作按钮 - 悬停时显示（非选择模式） */}
            {!isSelectMode && isHovered && (
              <div className="absolute right-1.5 flex items-center gap-0.5 bg-gradient-to-l from-[var(--app-sidebar-bg)] via-[var(--app-sidebar-bg)] to-transparent pl-4">
                <Button
                  variant="ghost"
                  size="icon"
                  className="app-sidebar-item h-7 w-7 hover:text-[var(--app-sidebar-icon-active)]"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditing(true);
                  }}
                >
                  <Edit2 className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="app-sidebar-item h-7 w-7 text-rose-500/80 hover:text-rose-600 hover:bg-rose-50/80"
                  onClick={handleDelete}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
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
}: {
  threads: Thread[];
  onThreadClick?: (threadId: string) => void;
  isSelectMode?: boolean;
  selectedIds?: Set<string>;
  onToggleSelect?: (threadId: string) => void;
}) {
  const [threadId, setThreadId] = useQueryState("threadId");
  const { deleteThread, updateThreadTitle } = useThreads();

  const handleSelect = (id: string) => {
    onThreadClick?.(id);
    if (id !== threadId) {
      setThreadId(id);
    }
  };

  if (threads.length === 0) {
    return (
      <div className="flex h-32 w-full flex-col items-center justify-center gap-2 text-gray-400">
        <MessageSquare className="h-8 w-8 text-gray-200" />
        <span className="text-sm">暂无对话</span>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-0.5 overflow-y-auto px-2 py-1 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {threads.map((t) => (
        <ThreadItem
          key={t.thread_id}
          thread={t}
          isActive={t.thread_id === threadId}
          onSelect={handleSelect}
          onDelete={deleteThread}
          onRename={updateThreadTitle}
          isSelectMode={isSelectMode}
          isSelected={selectedIds?.has(t.thread_id)}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  );
}

function ThreadHistoryLoading() {
  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-1.5 overflow-y-auto px-2 py-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={`skeleton-${i}`} className="h-10 w-full rounded-lg" />
      ))}
    </div>
  );
}

export default function ThreadHistory() {
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(false)
  );

  const { threads, threadsLoading, refreshThreads } = useThreads();

  // 批量选择状态
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  // 页面加载时获取对话列表
  useEffect(() => {
    if (typeof window !== "undefined") {
      refreshThreads();
    }
  }, [refreshThreads]);

  // 切换选择
  const handleToggleSelect = (threadId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(threadId)) {
        next.delete(threadId);
      } else {
        next.add(threadId);
      }
      return next;
    });
  };

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedIds.size === threads.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(threads.map((t) => t.thread_id)));
    }
  };

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`确定要删除选中的 ${selectedIds.size} 个对话吗？此操作不可恢复。`)) {
      return;
    }

    setIsDeleting(true);
    try {
      await deleteThreadsBatch(Array.from(selectedIds));
      toast.success(`已删除 ${selectedIds.size} 个对话`);
      setSelectedIds(new Set());
      setIsSelectMode(false);
      refreshThreads();
    } catch (e: any) {
      toast.error(e.message || "批量删除失败");
    } finally {
      setIsDeleting(false);
    }
  };

  // 退出选择模式
  const exitSelectMode = () => {
    setIsSelectMode(false);
    setSelectedIds(new Set());
  };

  // 渲染选择模式工具栏（移动端需要 pr-8 避开 Sheet 关闭按钮）
  const renderSelectToolbar = (isMobile = false) => (
    <div className={`flex flex-col gap-1.5 px-3 py-2 overflow-hidden ${isMobile ? "pr-10" : ""}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <Button
            variant="ghost"
            size="sm"
            className="app-sidebar-item h-7 px-1.5 text-xs shrink-0 hover:text-[var(--app-sidebar-icon-active)]"
            onClick={handleSelectAll}
          >
            {selectedIds.size === threads.length ? (
              <CheckSquare className="h-3.5 w-3.5 mr-1" />
            ) : (
              <Square className="h-3.5 w-3.5 mr-1" />
            )}
            {selectedIds.size === threads.length ? "取消全选" : "全选"}
          </Button>
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {selectedIds.size} / {threads.length}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="app-sidebar-item h-7 px-2 text-xs shrink-0"
          onClick={exitSelectMode}
        >
          完成
        </Button>
      </div>
      {selectedIds.size > 0 && (
        <Button
          variant="outline"
          size="sm"
          className="h-7 w-full text-xs text-rose-600 border-rose-200 hover:bg-rose-50 hover:border-rose-300"
          onClick={handleBatchDelete}
          disabled={isDeleting}
        >
          <Trash2 className="h-3.5 w-3.5 mr-1.5" />
          {isDeleting ? "删除中..." : `删除 (${selectedIds.size})`}
        </Button>
      )}
    </div>
  );

  // 渲染桌面端工具栏
  const renderDesktopToolbar = () => (
    <div className="app-sidebar-separator w-full overflow-hidden border-b">
      {isSelectMode ? (
        renderSelectToolbar()
      ) : (
        <div className="flex items-center justify-end gap-0.5 px-2 py-2">
          {threads.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              className="app-sidebar-item h-8 w-8 hover:text-[var(--app-sidebar-icon-active)]"
              onClick={() => setIsSelectMode(true)}
              title="批量管理"
            >
              <CheckSquare className="size-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="app-sidebar-item h-8 w-8 hover:text-[var(--app-sidebar-icon-active)]"
            onClick={() => setChatHistoryOpen((p) => !p)}
          >
            {chatHistoryOpen ? (
              <PanelRightOpen className="size-4" />
            ) : (
              <PanelRightClose className="size-4" />
            )}
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* 大屏幕侧边栏 */}
      <div className="app-sidebar-surface shadow-inner-right hidden h-screen w-[300px] shrink-0 flex-col items-start justify-start border-r lg:flex">
        {renderDesktopToolbar()}
        {threadsLoading ? (
          <ThreadHistoryLoading />
        ) : (
          <ThreadList
            threads={threads}
            isSelectMode={isSelectMode}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelect}
          />
        )}
      </div>

      {/* 小屏幕抽屉 */}
      <div className="lg:hidden">
        <Sheet
          open={!!chatHistoryOpen && !isLargeScreen}
          onOpenChange={(open) => {
            if (isLargeScreen) return;
            setChatHistoryOpen(open);
            if (!open) exitSelectMode();
          }}
        >
          <SheetContent side="left" className="app-sidebar-surface flex w-[85vw] max-w-[300px] flex-col p-0 lg:hidden">
            <SheetHeader className="app-sidebar-separator border-b px-0 py-0">
              <SheetTitle className="sr-only">对话列表</SheetTitle>
              {isSelectMode ? (
                renderSelectToolbar(true)
              ) : (
                <div className="flex items-center justify-start gap-0.5 px-2 py-2">
                  {threads.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="app-sidebar-item h-8 text-xs"
                      onClick={() => setIsSelectMode(true)}
                    >
                      <CheckSquare className="h-3.5 w-3.5 mr-1" />
                      管理
                    </Button>
                  )}
                </div>
              )}
            </SheetHeader>
            {threadsLoading ? (
              <ThreadHistoryLoading />
            ) : (
              <ThreadList
                threads={threads}
                onThreadClick={() => {
                  if (!isSelectMode) setChatHistoryOpen(false);
                }}
                isSelectMode={isSelectMode}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
              />
            )}
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
