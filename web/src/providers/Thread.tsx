/**
 * Thread Provider（中文注释）
 *
 * 管理对话线程的状态和操作：
 * - 获取对话列表
 * - 删除对话
 * - 更新对话标题
 */
import {
  createContext,
  useContext,
  ReactNode,
  useCallback,
  useState,
  Dispatch,
  SetStateAction,
} from "react";
import {
  ActiveRunItem,
  ConversationThread,
  apiFetch,
} from "@/lib/backend";

/**
 * 对话线程类型（与后端 ThreadOut 对应）
 */
export interface Thread {
  thread_id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export type ActiveRunMap = Record<string, ActiveRunItem>;
export type ThreadUnreadReplyMap = Record<string, true>;

interface ThreadContextType {
  /** 获取对话列表 */
  getThreads: () => Promise<Thread[]>;
  /** 对话列表 */
  threads: Thread[];
  /** 设置对话列表 */
  setThreads: Dispatch<SetStateAction<Thread[]>>;
  /** 是否正在加载 */
  threadsLoading: boolean;
  /** 设置加载状态 */
  setThreadsLoading: Dispatch<SetStateAction<boolean>>;
  /** 删除对话 */
  deleteThread: (threadId: string) => Promise<void>;
  /** 更新对话标题 */
  updateThreadTitle: (threadId: string, title: string) => Promise<void>;
  /** 刷新对话列表 */
  refreshThreads: () => Promise<void>;
  /** 本地插入或前置线程（用于新线程 init 后立即显示） */
  upsertThread: (thread: Thread) => void;
  /** 当前活跃运行快照 */
  activeRuns: ActiveRunMap;
  /** 设置当前活跃运行快照 */
  setActiveRuns: Dispatch<SetStateAction<ActiveRunMap>>;
  /** 当前页面内未读回复的线程 */
  unreadReplies: ThreadUnreadReplyMap;
  /** 设置当前页面内未读回复的线程 */
  setUnreadReplies: Dispatch<SetStateAction<ThreadUnreadReplyMap>>;
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

export function ThreadProvider({ children }: { children: ReactNode }) {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const [activeRuns, setActiveRuns] = useState<ActiveRunMap>({});
  const [unreadReplies, setUnreadReplies] = useState<ThreadUnreadReplyMap>({});

  /**
   * 获取对话列表
   */
  const getThreads = useCallback(async (): Promise<Thread[]> => {
    try {
      const r = await apiFetch(`/api/v1/chat/threads?limit=50`);
      if (!r.ok) {
        console.error("获取对话列表失败:", r.status);
        return [];
      }
      const data: ConversationThread[] = await r.json();
      return data.map((t) => ({
        thread_id: t.thread_id,
        title: t.title,
        created_at: t.created_at,
        updated_at: t.updated_at,
      }));
    } catch (error) {
      console.error("获取对话列表失败:", error);
      return [];
    }
  }, []);

  /**
   * 刷新对话列表
   */
  const refreshThreads = useCallback(async () => {
    setThreadsLoading(true);
    try {
      const list = await getThreads();
      setThreads(list);
    } finally {
      setThreadsLoading(false);
    }
  }, [getThreads]);

  /**
   * 本地插入或更新线程，用于新线程 init 后立即反映到侧边栏。
   */
  const upsertThread = useCallback((thread: Thread) => {
    setThreads((prev) => {
      const title = thread.title?.trim() || "新对话";
      const existing = prev.find((item) => item.thread_id === thread.thread_id);
      const nextThread: Thread = {
        ...existing,
        ...thread,
        title,
        created_at: thread.created_at ?? existing?.created_at,
        updated_at: thread.updated_at ?? existing?.updated_at ?? new Date().toISOString(),
      };
      const next = [nextThread, ...prev.filter((item) => item.thread_id !== thread.thread_id)];
      return next.slice(0, 50);
    });
  }, []);

  /**
   * 删除对话
   */
  const deleteThread = useCallback(
    async (threadId: string) => {
      const r = await apiFetch(`/api/v1/chat/threads/${threadId}`, {
        method: "DELETE",
      });
      if (!r.ok) {
        throw new Error("删除对话失败");
      }
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
      setActiveRuns((prev) => {
        const next = { ...prev };
        delete next[threadId];
        return next;
      });
      setUnreadReplies((prev) => {
        if (!(threadId in prev)) return prev;
        const next = { ...prev };
        delete next[threadId];
        return next;
      });
    },
    []
  );

  /**
   * 更新对话标题
   */
  const updateThreadTitle = useCallback(
    async (threadId: string, title: string) => {
      const r = await apiFetch(`/api/v1/chat/threads/${threadId}/title`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (!r.ok) {
        throw new Error("更新标题失败");
      }
      setThreads((prev) =>
        prev.map((t) => (t.thread_id === threadId ? { ...t, title } : t))
      );
    },
    []
  );

  const value: ThreadContextType = {
    getThreads,
    threads,
    setThreads,
    threadsLoading,
    setThreadsLoading,
    deleteThread,
    updateThreadTitle,
    refreshThreads,
    upsertThread,
    activeRuns,
    setActiveRuns,
    unreadReplies,
    setUnreadReplies,
  };

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}

export function useThreads() {
  const context = useContext(ThreadContext);
  if (context === undefined) {
    throw new Error("useThreads must be used within a ThreadProvider");
  }
  return context;
}
