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
      className="w-full px-1"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={`group relative flex w-full items-center rounded-md px-2 py-2 transition-colors ${
          isSelected
            ? "bg-[#E8F4F4] border border-[#A8D4D4]"
            : isActive
            ? "bg-primary/10 text-primary"
            : "hover:bg-gray-100"
          }`}
      >
        {/* 批量选择模式：显示 Checkbox */}
        {isSelectMode ? (
          <Checkbox
            checked={isSelected}
            onCheckedChange={() => onToggleSelect?.(thread.thread_id)}
            className="mr-2 h-4 w-4 shrink-0"
          />
        ) : (
          <MessageSquare className="mr-2 h-4 w-4 shrink-0 text-gray-500" />
        )}

        {isEditing ? (
          <div className="flex flex-1 items-center gap-1">
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
              className="h-6 w-6"
              onClick={handleRename}
            >
              <Check className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => {
                setEditTitle(thread.title);
                setIsEditing(false);
              }}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        ) : (
          <>
            <button
              className="flex-1 truncate text-left text-sm"
              onClick={handleClick}
            >
              {thread.title || "新对话"}
            </button>

            {/* 操作按钮 - 悬停时显示（非选择模式） */}
            {!isSelectMode && isHovered && (
              <div className="absolute right-1 flex items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-gray-500 hover:text-gray-700"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditing(true);
                  }}
                >
                  <Edit2 className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-gray-500 hover:text-red-500"
                  onClick={handleDelete}
                >
                  <Trash2 className="h-3 w-3" />
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
      <div className="flex h-32 w-full items-center justify-center text-gray-400">
        暂无对话历史
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-1 overflow-y-scroll px-2 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
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
    <div className="flex h-full w-full flex-col items-start justify-start gap-2 overflow-y-scroll px-2 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {Array.from({ length: 10 }).map((_, i) => (
        <Skeleton key={`skeleton-${i}`} className="h-9 w-full rounded-md" />
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

  // 渲染工具栏
  const renderToolbar = () => (
    <div className="flex w-full items-center justify-between border-b border-slate-200 px-4 py-3">
      {isSelectMode ? (
        <>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2"
              onClick={handleSelectAll}
            >
              {selectedIds.size === threads.length ? (
                <CheckSquare className="h-4 w-4 mr-1" />
              ) : (
                <Square className="h-4 w-4 mr-1" />
              )}
              {selectedIds.size === threads.length ? "取消全选" : "全选"}
            </Button>
            <span className="text-sm text-muted-foreground whitespace-nowrap">
              已选 {selectedIds.size} 项
            </span>
          </div>
          <div className="flex items-center gap-1">
            {selectedIds.size > 0 && (
              <Button
                variant="destructive"
                size="sm"
                className="h-8"
                onClick={handleBatchDelete}
                disabled={isDeleting}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                {isDeleting ? "删除中..." : "删除"}
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8"
              onClick={exitSelectMode}
            >
              取消
            </Button>
          </div>
        </>
      ) : (
        <>
          <h1 className="text-lg font-semibold tracking-tight">对话历史</h1>
          <div className="flex items-center gap-1">
            {threads.length > 0 && (
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-gray-200"
                onClick={() => setIsSelectMode(true)}
                title="批量管理"
              >
                <CheckSquare className="size-4" />
              </Button>
            )}
            <Button
              className="hover:bg-gray-200"
              variant="ghost"
              size="icon"
              onClick={() => setChatHistoryOpen((p) => !p)}
            >
              {chatHistoryOpen ? (
                <PanelRightOpen className="size-5" />
              ) : (
                <PanelRightClose className="size-5" />
              )}
            </Button>
          </div>
        </>
      )}
    </div>
  );

  return (
    <>
      {/* 大屏幕侧边栏 */}
      <div className="shadow-inner-right hidden h-screen w-[300px] shrink-0 flex-col items-start justify-start gap-4 border-r-[1px] border-slate-300 bg-gray-50 lg:flex">
        {renderToolbar()}
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
          <SheetContent side="left" className="flex w-[300px] flex-col lg:hidden">
            <SheetHeader className="border-b pb-3">
              {isSelectMode ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0"
                      onClick={handleSelectAll}
                      title={selectedIds.size === threads.length ? "取消全选" : "全选"}
                    >
                      {selectedIds.size === threads.length ? (
                        <CheckSquare className="h-4 w-4" />
                      ) : (
                        <Square className="h-4 w-4" />
                      )}
                    </Button>
                    <span className="text-sm text-muted-foreground whitespace-nowrap">
                      已选 {selectedIds.size} 项
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    {selectedIds.size > 0 && (
                      <Button
                        variant="destructive"
                        size="sm"
                        className="h-8 px-2"
                        onClick={handleBatchDelete}
                        disabled={isDeleting}
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        删除
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2"
                      onClick={exitSelectMode}
                    >
                      取消
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <SheetTitle>对话历史</SheetTitle>
                  {threads.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsSelectMode(true)}
                    >
                      <CheckSquare className="h-4 w-4 mr-1" />
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
