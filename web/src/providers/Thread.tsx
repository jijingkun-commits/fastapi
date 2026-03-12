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
  clearLatestThreadCache,
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
  getThreads: () => Promise<Thread[]>;
  ensureThreadsLoaded: () => Promise<void>;
  threads: Thread[];
  setThreads: Dispatch<SetStateAction<Thread[]>>;
  threadsLoading: boolean;
  setThreadsLoading: Dispatch<SetStateAction<boolean>>;
  deleteThread: (threadId: string) => Promise<void>;
  updateThreadTitle: (threadId: string, title: string) => Promise<void>;
  refreshThreads: () => Promise<void>;
  upsertThread: (thread: Thread) => void;
  activeRuns: ActiveRunMap;
  setActiveRuns: Dispatch<SetStateAction<ActiveRunMap>>;
  unreadReplies: ThreadUnreadReplyMap;
  setUnreadReplies: Dispatch<SetStateAction<ThreadUnreadReplyMap>>;
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

let cachedThreads: Thread[] | null = null;
let threadsPromise: Promise<Thread[]> | null = null;

function normalizeThreads(data: ConversationThread[]): Thread[] {
  return data.map((thread) => ({
    thread_id: thread.thread_id,
    title: thread.title,
    created_at: thread.created_at,
    updated_at: thread.updated_at,
  }));
}

function writeThreadCache(nextThreads: Thread[]) {
  cachedThreads = nextThreads;
}

function logThreadListFallback(reason: unknown) {
  if (typeof reason === "number") {
    console.warn("获取对话列表失败，已降级为空列表/缓存:", reason);
    return;
  }
  if (reason instanceof Error) {
    console.warn("获取对话列表失败，已降级为空列表/缓存:", reason.message);
    return;
  }
  console.warn("获取对话列表失败，已降级为空列表/缓存");
}

async function fetchThreadList(force = false): Promise<Thread[]> {
  if (!force && cachedThreads) {
    return cachedThreads;
  }

  if (!force && threadsPromise) {
    return threadsPromise;
  }

  threadsPromise = (async () => {
    try {
      const response = await apiFetch(`/api/v1/chat/threads?limit=50`);
      if (!response.ok) {
        logThreadListFallback(response.status);
        return cachedThreads ?? [];
      }
      const data: ConversationThread[] = await response.json();
      cachedThreads = normalizeThreads(data);
      return cachedThreads;
    } catch (error) {
      logThreadListFallback(error);
      return cachedThreads ?? [];
    } finally {
      threadsPromise = null;
    }
  })();

  return threadsPromise;
}

export function ThreadProvider({ children }: { children: ReactNode }) {
  const [threads, setThreads] = useState<Thread[]>(() => cachedThreads ?? []);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const [activeRuns, setActiveRuns] = useState<ActiveRunMap>({});
  const [unreadReplies, setUnreadReplies] = useState<ThreadUnreadReplyMap>({});

  const getThreads = useCallback(async (): Promise<Thread[]> => fetchThreadList(false), []);

  const ensureThreadsLoaded = useCallback(async () => {
    if (threads.length > 0) {
      return;
    }

    setThreadsLoading(true);
    try {
      const list = await getThreads();
      setThreads(list);
    } finally {
      setThreadsLoading(false);
    }
  }, [getThreads, threads.length]);

  const refreshThreads = useCallback(async () => {
    setThreadsLoading(true);
    try {
      const list = await fetchThreadList(true);
      setThreads(list);
    } finally {
      setThreadsLoading(false);
    }
  }, []);

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
      const next = [nextThread, ...prev.filter((item) => item.thread_id !== thread.thread_id)].slice(0, 50);
      writeThreadCache(next);
      return next;
    });
  }, []);

  const deleteThread = useCallback(async (threadId: string) => {
    const response = await apiFetch(`/api/v1/chat/threads/${threadId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("删除对话失败");
    }

    clearLatestThreadCache();
    setThreads((prev) => {
      const next = prev.filter((thread) => thread.thread_id !== threadId);
      writeThreadCache(next);
      return next;
    });
    setActiveRuns((prev) => {
      const next = { ...prev };
      delete next[threadId];
      return next;
    });
    setUnreadReplies((prev) => {
      if (!(threadId in prev)) {
        return prev;
      }
      const next = { ...prev };
      delete next[threadId];
      return next;
    });
  }, []);

  const updateThreadTitle = useCallback(async (threadId: string, title: string) => {
    const response = await apiFetch(`/api/v1/chat/threads/${threadId}/title`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!response.ok) {
      throw new Error("更新标题失败");
    }

    setThreads((prev) => {
      const next = prev.map((thread) => (
        thread.thread_id === threadId ? { ...thread, title } : thread
      ));
      writeThreadCache(next);
      return next;
    });
  }, []);

  const value: ThreadContextType = {
    getThreads,
    ensureThreadsLoaded,
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
