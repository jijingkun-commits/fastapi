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
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

export function ThreadProvider({ children }: { children: ReactNode }) {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);

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
      // 转换为 Thread 类型
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
      // 更新本地状态
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
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
      // 更新本地状态
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
