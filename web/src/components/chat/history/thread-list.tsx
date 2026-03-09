import { useState } from "react";
import { useQueryState } from "nuqs";
import { toast } from "sonner";
import { Check, Edit2, MessageSquare, Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { ActiveRunMap, Thread, ThreadUnreadReplyMap, useThreads } from "@/providers/Thread";

export type ThreadAttentionState = "none" | "unread" | "running";

type ThreadItemProps = {
  thread: Thread;
  isActive: boolean;
  onSelect: (threadId: string) => void;
  onDelete: (threadId: string) => void;
  onRename: (threadId: string, title: string) => void;
  activeRunStatus?: string | null;
  attentionState: ThreadAttentionState;
  isSelectMode?: boolean;
  isSelected?: boolean;
  onToggleSelect?: (threadId: string) => void;
};

type ThreadListProps = {
  threads: Thread[];
  onThreadClick?: (threadId: string) => void;
  isSelectMode?: boolean;
  selectedIds?: Set<string>;
  onToggleSelect?: (threadId: string) => void;
  activeRuns: ActiveRunMap;
  unreadReplies: ThreadUnreadReplyMap;
};

function ThreadAttentionIndicator({ attentionState }: { attentionState: ThreadAttentionState }) {
  const label =
    attentionState === "running"
      ? "会话运行中"
      : attentionState === "unread"
        ? "会话有未读回复"
        : undefined;

  return (
    <div
      className="mr-2 flex h-6 w-4 shrink-0 items-center justify-center"
      data-testid="thread-reply-status"
      data-reply-status={attentionState}
      aria-label={label}
      title={label}
    >
      {attentionState === "running" ? (
        <span className="block h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-500" />
      ) : attentionState === "unread" ? (
        <span className="block h-2.5 w-2.5 rounded-full bg-sky-500 shadow-[0_0_0_3px_rgba(59,130,246,0.14)]" />
      ) : null}
    </div>
  );
}

function ThreadItem({
  thread,
  isActive,
  onSelect,
  onDelete,
  onRename,
  activeRunStatus = null,
  attentionState,
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
      return;
    }
    onSelect(thread.thread_id);
  };

  return (
    <div
      className="w-full"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={cn(
          "app-sidebar-item group relative flex w-full items-center rounded-lg px-3 py-1.5 transition-all duration-150",
          (isSelected || isActive) && "app-sidebar-item-active"
        )}
        data-thread-id={thread.thread_id}
        data-run-status={activeRunStatus ?? undefined}
        data-reply-status={attentionState}
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
        {isSelectMode ? (
          <Checkbox
            checked={isSelected}
            onClick={(e) => e.stopPropagation()}
            onCheckedChange={() => onToggleSelect?.(thread.thread_id)}
            className="mr-2 h-4 w-4 shrink-0"
          />
        ) : (
          <ThreadAttentionIndicator attentionState={attentionState} />
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
              className="h-6 flex-1 text-sm"
              autoFocus
            />
            <Button
              variant="ghost"
              size="icon"
              className="app-sidebar-item h-6 w-6 hover:text-[var(--app-sidebar-icon-active)]"
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
              className="app-sidebar-item h-6 w-6"
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
            <div className="flex min-w-0 flex-1 items-center gap-2">
              <div
                className={`min-w-0 flex-1 truncate text-left text-[13px] leading-snug ${
                  isActive || isSelected
                    ? "font-medium text-[var(--app-sidebar-item-active-fg)]"
                    : "text-[var(--app-sidebar-item-fg)]"
                }`}
              >
                {thread.title || "新对话"}
              </div>
            </div>

            {!isSelectMode && isHovered && (
              <div className="absolute right-1 flex items-center gap-0.5 bg-gradient-to-l from-[var(--app-sidebar-bg)] via-[var(--app-sidebar-bg)] to-transparent pl-3">
                <Button
                  variant="ghost"
                  size="icon"
                  className="app-sidebar-item h-6 w-6 hover:text-[var(--app-sidebar-icon-active)]"
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
                  className="app-sidebar-item h-6 w-6 text-rose-500/80 hover:text-rose-600 hover:bg-rose-50/80"
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

function getThreadAttentionState(
  threadId: string,
  activeRuns: ActiveRunMap,
  unreadReplies: ThreadUnreadReplyMap,
): ThreadAttentionState {
  if (activeRuns[threadId]?.status === "running") {
    return "running";
  }
  if (unreadReplies[threadId]) {
    return "unread";
  }
  return "none";
}

export function ThreadList({
  threads,
  onThreadClick,
  isSelectMode,
  selectedIds,
  onToggleSelect,
  activeRuns,
  unreadReplies,
}: ThreadListProps) {
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
      <div className="app-sidebar-secondary flex h-32 w-full flex-col items-center justify-center gap-2">
        <MessageSquare className="h-8 w-8 text-gray-200" />
        <span className="text-sm">暂无对话</span>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-px overflow-y-auto px-2 py-0.5 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {threads.map((thread) => (
        <ThreadItem
          key={thread.thread_id}
          thread={thread}
          isActive={thread.thread_id === threadId}
          onSelect={handleSelect}
          onDelete={deleteThread}
          onRename={updateThreadTitle}
          activeRunStatus={activeRuns[thread.thread_id]?.status ?? null}
          attentionState={getThreadAttentionState(thread.thread_id, activeRuns, unreadReplies)}
          isSelectMode={isSelectMode}
          isSelected={selectedIds?.has(thread.thread_id)}
          onToggleSelect={onToggleSelect}
        />
      ))}
    </div>
  );
}

export function ThreadHistoryLoading() {
  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-1 overflow-y-auto px-2 py-1.5">
      {Array.from({ length: 8 }).map((_, index) => (
        <Skeleton key={`skeleton-${index}`} className="h-9 w-full rounded-lg" />
      ))}
    </div>
  );
}
