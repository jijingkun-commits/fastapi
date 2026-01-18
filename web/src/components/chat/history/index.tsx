/**
 * 对话历史组件（中文注释）
 *
 * 显示用户的对话历史列表，支持：
 * - 查看对话历史
 * - 切换对话
 * - 删除对话
 * - 重命名对话
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
import {
  PanelRightOpen,
  PanelRightClose,
  Trash2,
  Edit2,
  Check,
  X,
  MessageSquare,
} from "lucide-react";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { toast } from "sonner";

interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  onSelect: (threadId: string) => void;
  onDelete: (threadId: string) => void;
  onRename: (threadId: string, title: string) => void;
}

function ThreadItem({
  thread,
  isActive,
  onSelect,
  onDelete,
  onRename,
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

  return (
    <div
      className="w-full px-1"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={`group relative flex w-full items-center rounded-md px-2 py-2 transition-colors ${isActive
            ? "bg-primary/10 text-primary"
            : "hover:bg-gray-100"
          }`}
      >
        <MessageSquare className="mr-2 h-4 w-4 shrink-0 text-gray-500" />

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
              onClick={() => onSelect(thread.thread_id)}
            >
              {thread.title || "新对话"}
            </button>

            {/* 操作按钮 - 悬停时显示 */}
            {isHovered && (
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
}: {
  threads: Thread[];
  onThreadClick?: (threadId: string) => void;
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

  // 页面加载时获取对话列表
  useEffect(() => {
    if (typeof window !== "undefined") {
      refreshThreads();
    }
  }, [refreshThreads]);

  return (
    <>
      {/* 大屏幕侧边栏 */}
      <div className="shadow-inner-right hidden h-screen w-[300px] shrink-0 flex-col items-start justify-start gap-4 border-r-[1px] border-slate-300 bg-gray-50 lg:flex">
        <div className="flex w-full items-center justify-between border-b border-slate-200 px-4 py-3">
          <h1 className="text-lg font-semibold tracking-tight">对话历史</h1>
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
        {threadsLoading ? <ThreadHistoryLoading /> : <ThreadList threads={threads} />}
      </div>

      {/* 小屏幕抽屉 */}
      <div className="lg:hidden">
        <Sheet
          open={!!chatHistoryOpen && !isLargeScreen}
          onOpenChange={(open) => {
            if (isLargeScreen) return;
            setChatHistoryOpen(open);
          }}
        >
          <SheetContent side="left" className="flex w-[300px] flex-col lg:hidden">
            <SheetHeader>
              <SheetTitle>对话历史</SheetTitle>
            </SheetHeader>
            {threadsLoading ? (
              <ThreadHistoryLoading />
            ) : (
              <ThreadList
                threads={threads}
                onThreadClick={() => setChatHistoryOpen(false)}
              />
            )}
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
