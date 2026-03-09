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
import { useThreads } from "@/providers/Thread";
import { useEffect, useState } from "react";
import { useQueryState, parseAsBoolean } from "nuqs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  PanelRightOpen,
  PanelRightClose,
  Trash2,
  CheckSquare,
  Square,
} from "lucide-react";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { toast } from "sonner";
import { deleteThreadsBatch } from "@/lib/backend";
import { ThreadHistoryLoading, ThreadList } from "@/components/chat/history/thread-list";

export default function ThreadHistory() {
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(false)
  );

  const { threads, threadsLoading, refreshThreads, activeRuns, setActiveRuns, unreadReplies, setUnreadReplies } = useThreads();

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
      setActiveRuns((prev) => {
        const next = { ...prev };
        for (const threadId of selectedIds) {
          delete next[threadId];
        }
        return next;
      });
      setUnreadReplies((prev) => {
        const next = { ...prev };
        for (const threadId of selectedIds) {
          delete next[threadId];
        }
        return next;
      });
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
          <span className="app-sidebar-secondary text-xs whitespace-nowrap">
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
            activeRuns={activeRuns}
            unreadReplies={unreadReplies}
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
                activeRuns={activeRuns}
                unreadReplies={unreadReplies}
              />
            )}
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
