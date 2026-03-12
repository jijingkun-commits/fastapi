/**
 * SSE 流消息处理 Hook（中文注释）
 *
 * 处理 SSE 模式下的消息流逻辑，包括：
 * - 加载历史消息
 * - 发送消息并处理流式响应
 * - 恢复中断的流程
 *
 * Refactored to use smaller hooks:
 * - useMessageUpdater
 * - useModelConfig
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { type Message } from "@langchain/langgraph-sdk";
import { useQueryState } from "nuqs";
import { toast } from "sonner";
import { v4 as uuidv4 } from "uuid";

import {
  cancelRun,
  getLatestThread,
  listActiveRuns,
  startLLMStream,
  getThreadMessages,
  startResumeStream,
  InterruptData,
  DecisionType,
  Attachment,
} from "@/lib/backend";
import type { ActiveRunItem, StreamResultMeta } from "@/lib/backend";
import { fromBackendMessages } from "@/lib/message-normalizer";
import { useThreads } from "@/providers/Thread";
import {
  StateType,
  StreamContextValue,
  MessageMetadata,
  StreamStatus,
} from "@/providers/StreamContext";
import {
  addToolCallToMessages,
  appendThinkingToMessages,
  appendTokenToMessages,
} from "@/hooks/use-message-updater";
import { useModelConfig } from "@/hooks/use-model-config";
import type { KbImages } from "@/components/chat/utils";
import { safeParseJson, SelectedTodoSchema } from "@/lib/utils";
import type {
  ClarificationEventData,
  DisplayBlocksEventData,
  ResultEventData,
  StatusEventData,
} from "@/types/message";
import {
  buildClarificationDisplayText,
  coerceResultEventArray,
  createEmptyThreadRuntime,
  createLocalActiveRunSnapshot,
  DRAFT_THREAD_KEY,
  isDraftThreadKey,
  getErrorMessageFromResult,
  getThreadKey,
  getToolOutputPreview,
  normalizeClarificationQuestions,
  resolveResultEventId,
  isRunningStatus,
  normalizeStatusData,
  resultEventsAccumulator,
  ThreadRuntimeState,
  toActiveRunMap,
} from "@/hooks/useSSEStream.helpers";

type MessageWithAdditionalKwargs = Message & {
  additional_kwargs?: Record<string, unknown>;
};

const NON_UNREAD_DONE_STATUSES = new Set([
  "stopped",
  "failed",
  "cancelled",
  "aborted",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function buildLocalThreadTitle(prompt: string): string {
  const firstNonEmptyLine = prompt
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.length > 0);
  return firstNonEmptyLine?.slice(0, 24) || "新对话";
}

function shouldMarkThreadUnreadAfterDone(
  doneMeta?: Record<string, unknown>,
): boolean {
  const status = doneMeta?.status;
  return typeof status !== "string" || !NON_UNREAD_DONE_STATUSES.has(status);
}

/**
 * SSE 流消息处理 Hook
 */
export function useSSEStream(): StreamContextValue {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown>(undefined);
  const [interrupt, setInterrupt] = useState<InterruptData | null>(null);
  // 当前处理状态（结构化：phase + message）
  const [currentStatus, setCurrentStatus] = useState<StreamStatus | null>(null);
  // 知识库图片映射（用于替换 [IMG-N] 占位符）
  const [kbImages, setKbImages] = useState<KbImages>({});

  // 1. Model & Thinking Config Hook
  const {
    selectedModel,
    enableThinking,
    setEnableThinking,
    thinkingCapability,
    handleModelChange,
  } = useModelConfig();

  // 2. UI Toggles (HideToolCalls)
  // 注意：useMultiAgent 已废弃（2026-01-31），系统默认使用多智能体模式
  const [hideToolCalls, setHideToolCallsState] = useState(false);

  // 从 localStorage 恢复开关状态
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedHideToolCalls = localStorage.getItem("chat:hideToolCalls");
      if (savedHideToolCalls === "true") setHideToolCallsState(true);
    }
  }, []);

  const setHideToolCalls = useCallback((value: boolean) => {
    setHideToolCallsState(value);
    if (typeof window !== "undefined") {
      localStorage.setItem("chat:hideToolCalls", value.toString());
    }
  }, []);

  const [threadId, setThreadId] = useQueryState("threadId");
  const [draftSessionId, setDraftSessionId] = useState(() => uuidv4());
  const initialThreadIdExistsRef = useRef(threadId !== null);
  const threadIdRef = useRef<string | null>(threadId);
  const draftSessionIdRef = useRef(draftSessionId);
  const latestThreadResolvedRef = useRef(false);
  const threadRuntimeRef = useRef<Record<string, ThreadRuntimeState>>({});
  const stopByThreadRef = useRef<Record<string, (() => void) | null>>({});
  const currentAiIdByThreadRef = useRef<Record<string, string | null>>({});
  const activeRunIdByThreadRef = useRef<Record<string, string | null>>({});
  const stopInFlightByThreadRef = useRef<Record<string, boolean>>({});
  const isStreamingByThreadRef = useRef<Record<string, boolean>>({});
  const pollTimeoutRef = useRef<number | null>(null);
  const pollFailureCountRef = useRef(0);
  const pollWarningShownRef = useRef(false);
  const scheduleActiveRunPollRef = useRef<((delayMs: number) => void) | null>(
    null,
  );
  const suppressUnreadOnInactiveRef = useRef<Record<string, boolean>>({});
  const { refreshThreads, upsertThread, setActiveRuns, setUnreadReplies } =
    useThreads();

  const ensureActiveRunPolling = useCallback((delayMs = 0) => {
    scheduleActiveRunPollRef.current?.(delayMs);
  }, []);

  const resolveThreadKey = useCallback(
    (
      resolvedThreadId: string | null | undefined,
      draftId = draftSessionIdRef.current,
    ) => {
      if (resolvedThreadId) {
        return getThreadKey(resolvedThreadId);
      }
      return `${DRAFT_THREAD_KEY}:${draftId}`;
    },
    [],
  );

  const getCurrentThreadKey = useCallback(() => {
    return resolveThreadKey(threadIdRef.current, draftSessionIdRef.current);
  }, [resolveThreadKey]);

  const startNewThread = useCallback(() => {
    setThreadId(null);
    setDraftSessionId(uuidv4());
  }, [setThreadId]);

  const buildLocalStreamingFallbackRuns = useCallback(
    (serverActiveRuns: Record<string, ActiveRunItem>) => {
      const fallbackRuns: Record<string, ActiveRunItem> = {};
      for (const [threadKey, isStreaming] of Object.entries(
        isStreamingByThreadRef.current,
      )) {
        if (
          !isStreaming ||
          isDraftThreadKey(threadKey) ||
          threadKey in serverActiveRuns
        ) {
          continue;
        }
        fallbackRuns[threadKey] = createLocalActiveRunSnapshot(
          threadKey,
          activeRunIdByThreadRef.current[threadKey] ?? "",
          "running",
        );
      }
      return fallbackRuns;
    },
    [],
  );

  const syncVisibleThreadRuntime = useCallback((threadKey: string) => {
    const runtime =
      threadRuntimeRef.current[threadKey] ?? createEmptyThreadRuntime();
    setMessages(runtime.messages);
    setIsLoading(runtime.isLoading);
    setError(runtime.error);
    setInterrupt(runtime.interrupt);
    setCurrentStatus(runtime.currentStatus);
    setKbImages(runtime.kbImages);
  }, []);

  const clearThreadUnread = useCallback(
    (threadKey: string) => {
      if (isDraftThreadKey(threadKey)) {
        return;
      }
      setUnreadReplies((prev) => {
        if (!(threadKey in prev)) {
          return prev;
        }
        const next = { ...prev };
        delete next[threadKey];
        return next;
      });
    },
    [setUnreadReplies],
  );

  const markThreadUnread = useCallback(
    (threadKey: string) => {
      if (isDraftThreadKey(threadKey)) {
        return;
      }
      if (getCurrentThreadKey() === threadKey) {
        clearThreadUnread(threadKey);
        return;
      }
      setUnreadReplies((prev) => {
        if (prev[threadKey]) {
          return prev;
        }
        return {
          ...prev,
          [threadKey]: true,
        };
      });
    },
    [clearThreadUnread, getCurrentThreadKey, setUnreadReplies],
  );

  const syncThreadUnreadState = useCallback(
    (threadKey: string, hasUnreadReply: boolean) => {
      if (hasUnreadReply) {
        markThreadUnread(threadKey);
        return;
      }
      clearThreadUnread(threadKey);
    },
    [clearThreadUnread, markThreadUnread],
  );

  const updateThreadRuntime = useCallback(
    (
      threadKey: string,
      updater: (prev: ThreadRuntimeState) => ThreadRuntimeState,
    ) => {
      const prev =
        threadRuntimeRef.current[threadKey] ?? createEmptyThreadRuntime();
      const next = updater(prev);
      threadRuntimeRef.current[threadKey] = next;
      if (getCurrentThreadKey() === threadKey) {
        syncVisibleThreadRuntime(threadKey);
      }
      return next;
    },
    [getCurrentThreadKey, syncVisibleThreadRuntime],
  );

  const patchThreadRuntime = useCallback(
    (threadKey: string, patch: Partial<ThreadRuntimeState>) => {
      updateThreadRuntime(threadKey, (prev) => ({ ...prev, ...patch }));
    },
    [updateThreadRuntime],
  );

  const updateThreadMessages = useCallback(
    (threadKey: string, updater: (prev: Message[]) => Message[]) => {
      updateThreadRuntime(threadKey, (prev) => ({
        ...prev,
        messages: updater(prev.messages),
      }));
    },
    [updateThreadRuntime],
  );

  const rekeyThreadRuntime = useCallback(
    (fromKey: string, toKey: string) => {
      if (fromKey === toKey) {
        return;
      }

      const sourceRuntime = threadRuntimeRef.current[fromKey];
      if (sourceRuntime) {
        const targetRuntime =
          threadRuntimeRef.current[toKey] ?? createEmptyThreadRuntime();
        threadRuntimeRef.current[toKey] = {
          ...targetRuntime,
          ...sourceRuntime,
          kbImages: { ...targetRuntime.kbImages, ...sourceRuntime.kbImages },
          historyLoaded:
            targetRuntime.historyLoaded || sourceRuntime.historyLoaded,
        };
        delete threadRuntimeRef.current[fromKey];
      }

      stopByThreadRef.current[toKey] =
        stopByThreadRef.current[fromKey] ??
        stopByThreadRef.current[toKey] ??
        null;
      currentAiIdByThreadRef.current[toKey] =
        currentAiIdByThreadRef.current[fromKey] ??
        currentAiIdByThreadRef.current[toKey] ??
        null;
      activeRunIdByThreadRef.current[toKey] =
        activeRunIdByThreadRef.current[fromKey] ??
        activeRunIdByThreadRef.current[toKey] ??
        null;
      isStreamingByThreadRef.current[toKey] =
        isStreamingByThreadRef.current[fromKey] ??
        isStreamingByThreadRef.current[toKey] ??
        false;
      stopInFlightByThreadRef.current[toKey] =
        stopInFlightByThreadRef.current[fromKey] ??
        stopInFlightByThreadRef.current[toKey] ??
        false;

      delete stopByThreadRef.current[fromKey];
      delete currentAiIdByThreadRef.current[fromKey];
      delete activeRunIdByThreadRef.current[fromKey];
      delete isStreamingByThreadRef.current[fromKey];
      delete stopInFlightByThreadRef.current[fromKey];

      if (getCurrentThreadKey() === toKey) {
        syncVisibleThreadRuntime(toKey);
      }
    },
    [getCurrentThreadKey, syncVisibleThreadRuntime],
  );

  const upsertThreadActiveRun = useCallback(
    (snapshot: ActiveRunItem) => {
      const threadKey = getThreadKey(snapshot.thread_id);
      activeRunIdByThreadRef.current[threadKey] = snapshot.run_id;
      suppressUnreadOnInactiveRef.current[threadKey] = false;
      clearThreadUnread(threadKey);
      setActiveRuns((prev) => ({
        ...prev,
        [snapshot.thread_id]: snapshot,
      }));
      ensureActiveRunPolling(500);
    },
    [clearThreadUnread, ensureActiveRunPolling, setActiveRuns],
  );

  const removeThreadActiveRun = useCallback(
    (threadKey: string) => {
      delete activeRunIdByThreadRef.current[threadKey];
      delete suppressUnreadOnInactiveRef.current[threadKey];
      setActiveRuns((prev) => {
        if (!(threadKey in prev)) {
          return prev;
        }
        const next = { ...prev };
        delete next[threadKey];
        return next;
      });
    },
    [setActiveRuns],
  );

  const bindMessageIdToAiMessage = useCallback(
    (threadKey: string, aiId: string, messageId?: number) => {
      if (!messageId) return;
      updateThreadMessages(threadKey, (prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((m) => m.id === aiId);
        if (idx !== -1) {
          updated[idx] = {
            ...updated[idx],
            id: String(messageId),
          };
        }
        return updated;
      });
    },
    [updateThreadMessages],
  );

  const storeKbImagesToMessage = useCallback(
    (threadKey: string, aiId: string, images: Record<string, string>) => {
      if (Object.keys(images).length === 0) {
        return;
      }

      updateThreadMessages(threadKey, (prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((m) => m.id === aiId);
        if (idx === -1) {
          return updated;
        }

        const message = updated[idx] as MessageWithAdditionalKwargs;
        const existingKwargs = isRecord(message.additional_kwargs)
          ? message.additional_kwargs
          : {};
        const existingKbImages = isRecord(existingKwargs.kb_images)
          ? existingKwargs.kb_images
          : {};

        updated[idx] = {
          ...updated[idx],
          additional_kwargs: {
            ...existingKwargs,
            kb_images: {
              ...existingKbImages,
              ...images,
            },
          },
        } as Message;
        return updated;
      });
    },
    [updateThreadMessages],
  );

  const applyDisplayBlocksToMessage = useCallback(
    (threadKey: string, aiId: string, data: DisplayBlocksEventData) => {
      updateThreadMessages(threadKey, (prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((m) => m.id === aiId);
        if (idx === -1) {
          return updated;
        }

        updated[idx] = {
          ...updated[idx],
          content: data.blocks,
        } as unknown as Message;
        return updated;
      });
    },
    [updateThreadMessages],
  );

  const storeStructuredResultToMessage = useCallback(
    (threadKey: string, aiId: string, data: ResultEventData) => {
      if (data.data_type === "error") {
        toast.error("操作失败", {
          description: getErrorMessageFromResult(data),
        });
        return;
      }

      let dedupDropped = false;

      updateThreadMessages(threadKey, (prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((m) => m.id === aiId);
        if (idx === -1) {
          return updated;
        }

        const message = updated[idx] as MessageWithAdditionalKwargs;
        const existingKwargs = message.additional_kwargs ?? {};
        const existingResultEvents = coerceResultEventArray(
          existingKwargs.result_events,
        );
        const accumulated = resultEventsAccumulator(existingResultEvents, data);
        dedupDropped = accumulated.dedupDropped;
        if (dedupDropped) {
          return updated;
        }

        const latestResultEvent =
          accumulated.events[accumulated.events.length - 1] ?? data;
        updated[idx] = {
          ...updated[idx],
          additional_kwargs: {
            ...existingKwargs,
            data_type: latestResultEvent.data_type,
            data: latestResultEvent.data,
            ...(latestResultEvent.message
              ? { message: latestResultEvent.message }
              : {}),
            result_event: latestResultEvent,
            result_events: accumulated.events,
            result_count: accumulated.events.length,
            fallback_used: accumulated.events.some((eventItem) =>
              Boolean(eventItem.fallback_used),
            ),
          },
        } as Message;
        return updated;
      });

      if (dedupDropped) {
        console.warn("[result-dedup] 丢弃重复 event_id", {
          thread_id: data.envelope?.thread_id,
          run_id: data.envelope?.run_id,
          event_id: resolveResultEventId(data),
          data_type: data.data_type,
        });
        return;
      }

      if (data.fallback_used || data.warning_code) {
        console.warn("[result-fallback] 使用降级渲染", {
          thread_id: data.envelope?.thread_id,
          run_id: data.envelope?.run_id,
          data_type: data.data_type,
          warning_code: data.warning_code,
        });
      }

      if (data.message) {
        updateThreadMessages(threadKey, (prev) =>
          appendTokenToMessages(prev, aiId, data.message ?? ""),
        );
      }
    },
    [updateThreadMessages],
  );

  const applyFinalAnswerToMessage = useCallback(
    (
      threadKey: string,
      aiId: string,
      content: string,
      meta?: Record<string, unknown>,
    ) => {
      const normalized = content.trim();
      if (!normalized) {
        return;
      }

      updateThreadMessages(threadKey, (prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((m) => m.id === aiId);
        if (idx === -1) {
          return updated;
        }

        const message = updated[idx] as MessageWithAdditionalKwargs;
        const existingKwargs = message.additional_kwargs ?? {};
        updated[idx] = {
          ...updated[idx],
          content: normalized,
          additional_kwargs: {
            ...existingKwargs,
            final_source: "final_answer",
            ...(meta ? { final_answer_meta: meta } : {}),
          },
        } as Message;
        return updated;
      });
    },
    [updateThreadMessages],
  );

  const applyClarificationToMessage = useCallback(
    (threadKey: string, aiId: string, data: ClarificationEventData) => {
      const questions = normalizeClarificationQuestions(data.questions);
      const message =
        typeof data.message === "string" && data.message.trim().length > 0
          ? data.message.trim()
          : undefined;
      const displayContent = buildClarificationDisplayText({
        questions,
        message,
      });
      if (!displayContent) {
        return;
      }

      updateThreadMessages(threadKey, (prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((m) => m.id === aiId);
        if (idx === -1) {
          return updated;
        }

        const messageItem = updated[idx] as MessageWithAdditionalKwargs;
        const existingKwargs = messageItem.additional_kwargs ?? {};
        updated[idx] = {
          ...updated[idx],
          content: displayContent,
          additional_kwargs: {
            ...existingKwargs,
            final_source: "clarification",
            clarification: {
              questions,
              ...(message ? { message } : {}),
            },
          },
        } as Message;
        return updated;
      });
    },
    [updateThreadMessages],
  );

  const finalizeStreamLifecycle = useCallback(
    (
      threadKey: string,
      aiId: string,
      options?: { messageId?: number; markUnread?: boolean },
    ) => {
      bindMessageIdToAiMessage(threadKey, aiId, options?.messageId);
      suppressUnreadOnInactiveRef.current[threadKey] = false;
      syncThreadUnreadState(threadKey, options?.markUnread ?? false);
      patchThreadRuntime(threadKey, {
        currentStatus: null,
        isLoading: false,
        error: undefined,
      });
      stopByThreadRef.current[threadKey] = null;
      currentAiIdByThreadRef.current[threadKey] = null;
      removeThreadActiveRun(threadKey);
      isStreamingByThreadRef.current[threadKey] = false;
      void refreshThreads();
    },
    [
      bindMessageIdToAiMessage,
      patchThreadRuntime,
      refreshThreads,
      removeThreadActiveRun,
      syncThreadUnreadState,
    ],
  );

  useEffect(() => {
    threadIdRef.current = threadId;
    draftSessionIdRef.current = draftSessionId;
    const visibleThreadKey = resolveThreadKey(threadId, draftSessionId);
    clearThreadUnread(visibleThreadKey);
    syncVisibleThreadRuntime(visibleThreadKey);
  }, [
    clearThreadUnread,
    draftSessionId,
    resolveThreadKey,
    threadId,
    syncVisibleThreadRuntime,
  ]);

  useEffect(() => {
    let cancelled = false;

    const scheduleNext = (delayMs: number) => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
      pollTimeoutRef.current = window.setTimeout(() => {
        void pollOnce();
      }, delayMs);
    };
    scheduleActiveRunPollRef.current = scheduleNext;

    const pollOnce = async () => {
      try {
        const response = await listActiveRuns();
        if (cancelled) {
          return;
        }

        pollFailureCountRef.current = 0;
        pollWarningShownRef.current = false;

        const serverActiveRuns = toActiveRunMap(response.items);
        // active 接口短暂空窗时，保留本地仍在 streaming 的线程，避免 running 图标闪没。
        const localFallbackRuns =
          buildLocalStreamingFallbackRuns(serverActiveRuns);
        const nextActiveRuns = { ...localFallbackRuns, ...serverActiveRuns };
        const activeThreadIds = new Set(Object.keys(nextActiveRuns));
        setActiveRuns(nextActiveRuns);

        for (const [activeThreadId, snapshot] of Object.entries(
          nextActiveRuns,
        )) {
          activeRunIdByThreadRef.current[activeThreadId] = snapshot.run_id;
          updateThreadRuntime(activeThreadId, (prev) => ({
            ...prev,
            isLoading:
              isRunningStatus(snapshot.status) ||
              Boolean(isStreamingByThreadRef.current[activeThreadId]),
            error: undefined,
          }));
        }

        for (const existingThreadId of Object.keys(
          activeRunIdByThreadRef.current,
        )) {
          if (isDraftThreadKey(existingThreadId)) {
            continue;
          }
          if (activeThreadIds.has(existingThreadId)) {
            continue;
          }
          if (isStreamingByThreadRef.current[existingThreadId]) {
            continue;
          }
          const shouldShowUnread =
            suppressUnreadOnInactiveRef.current[existingThreadId] !== true;
          suppressUnreadOnInactiveRef.current[existingThreadId] = false;
          syncThreadUnreadState(existingThreadId, shouldShowUnread);
          delete activeRunIdByThreadRef.current[existingThreadId];
          patchThreadRuntime(existingThreadId, {
            isLoading: false,
            currentStatus: null,
          });
        }

        if (
          response.active_count > 0 ||
          Object.keys(localFallbackRuns).length > 0
        ) {
          scheduleNext(Math.max(response.poll_hint_seconds, 1) * 1000);
        }
      } catch {
        if (cancelled) {
          return;
        }
        pollFailureCountRef.current += 1;
        if (pollFailureCountRef.current >= 3 && !pollWarningShownRef.current) {
          pollWarningShownRef.current = true;
          toast.warning("会话运行态同步存在延迟", {
            description: "侧边栏状态将在下次成功轮询后恢复。",
          });
        }
        scheduleNext(pollFailureCountRef.current <= 1 ? 5000 : 10000);
      }
    };

    void pollOnce();

    return () => {
      cancelled = true;
      scheduleActiveRunPollRef.current = null;
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
        pollTimeoutRef.current = null;
      }
    };
  }, [
    buildLocalStreamingFallbackRuns,
    patchThreadRuntime,
    setActiveRuns,
    syncThreadUnreadState,
    updateThreadRuntime,
  ]);

  const resolveLatestThread = useCallback(async (): Promise<boolean> => {
    if (latestThreadResolvedRef.current) {
      return false;
    }
    latestThreadResolvedRef.current = true;

    try {
      const latestThread = await getLatestThread();
      const latestThreadId = latestThread?.thread_id?.trim();
      if (!latestThreadId) {
        return false;
      }

      // 若用户已主动切换到某个会话，不再用“最新会话”覆盖用户选择。
      if (threadIdRef.current !== null) {
        return false;
      }

      await setThreadId(latestThreadId);
      return true;
    } catch (err) {
      console.warn("加载最近会话失败:", err);
      toast.error("加载最近会话失败", {
        description: "已进入新会话，可继续输入。",
      });
      return false;
    }
  }, [setThreadId]);

  const handleStructuredResultEvent = useCallback(
    (
      threadKey: string,
      aiId: string,
      data: ResultEventData,
      isResume: boolean,
      meta?: StreamResultMeta,
    ) => {
      const normalizedResultData: ResultEventData = {
        ...data,
        event_id: data.event_id ?? meta?.eventId,
        retry: data.retry ?? meta?.retryMs,
      };

      storeStructuredResultToMessage(threadKey, aiId, normalizedResultData);
      if (isResume) {
        console.log(`恢复流收到结构化结果: ${normalizedResultData.data_type}`);
        return;
      }
      console.log(`收到结构化结果: ${normalizedResultData.data_type}`);
    },
    [storeStructuredResultToMessage],
  );

  /**
   * 加载历史消息
   */
  const loadThreadMessages = useCallback(
    async (id: string) => {
      const threadKey = getThreadKey(id);
      try {
        patchThreadRuntime(threadKey, { isLoading: true, error: undefined });
        const rawMessages = await getThreadMessages(id);
        const normalized = fromBackendMessages(rawMessages);
        const converted = normalized.map(
          (m) =>
            ({
              id: m.id,
              type: m.role,
              content: m.content,
              ...(m.toolCalls && { tool_calls: m.toolCalls }),
              ...(m.additionalKwargs && {
                additional_kwargs: m.additionalKwargs,
              }),
              ...(m.feedbackScore !== undefined && {
                feedback_score: m.feedbackScore,
              }),
              ...(m.thinkingContent && {
                content: `<think>
${m.thinkingContent}
</think>

${typeof m.content === "string" ? m.content : ""}`,
              }),
            }) as Message,
        );
        updateThreadRuntime(threadKey, (prev) => ({
          ...prev,
          messages: converted,
          historyLoaded: true,
          isLoading:
            Boolean(activeRunIdByThreadRef.current[threadKey]) ||
            Boolean(isStreamingByThreadRef.current[threadKey]),
          error: undefined,
        }));
      } catch (err) {
        console.error("加载历史消息失败:", err);
        toast.error("加载历史消息失败");
        patchThreadRuntime(threadKey, { error: err, isLoading: false });
      }
    },
    [patchThreadRuntime, updateThreadRuntime],
  );

  useEffect(() => {
    const currentThreadKey = resolveThreadKey(threadId, draftSessionId);
    if (isStreamingByThreadRef.current[currentThreadKey]) {
      return;
    }
    let cancelled = false;

    const run = async () => {
      if (threadId) {
        const runtime = threadRuntimeRef.current[currentThreadKey];
        if (runtime?.historyLoaded) {
          syncVisibleThreadRuntime(currentThreadKey);
          return;
        }
        await loadThreadMessages(threadId);
        return;
      }

      const shouldResolveLatestOnInitialEmptyThread =
        initialThreadIdExistsRef.current === false &&
        !latestThreadResolvedRef.current;

      if (!shouldResolveLatestOnInitialEmptyThread) {
        if (!cancelled) {
          syncVisibleThreadRuntime(DRAFT_THREAD_KEY);
        }
        return;
      }

      const switchedToLatest = await resolveLatestThread();
      if (!cancelled && !switchedToLatest && threadIdRef.current === null) {
        syncVisibleThreadRuntime(DRAFT_THREAD_KEY);
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, [
    draftSessionId,
    threadId,
    loadThreadMessages,
    resolveLatestThread,
    resolveThreadKey,
    syncVisibleThreadRuntime,
  ]);

  /**
   * 获取消息元数据
   */
  const getMessagesMetadata = useCallback(
    (_msg: Message): MessageMetadata => {
      return {
        firstSeenState: { parent_checkpoint: null, values: { messages } },
        branch: undefined,
        branchOptions: undefined,
      };
    },
    [messages],
  );

  const setBranch = useCallback((_branch: unknown) => {
    /* no-op in SSE */
  }, []);

  /**
   * 停止生成
   */
  const stop = useCallback(() => {
    const currentThreadKey = getCurrentThreadKey();
    if (stopInFlightByThreadRef.current[currentThreadKey]) {
      return;
    }

    const localAbort = (preserveActiveSnapshot: boolean) => {
      stopByThreadRef.current[currentThreadKey]?.();
      stopByThreadRef.current[currentThreadKey] = null;
      currentAiIdByThreadRef.current[currentThreadKey] = null;
      activeRunIdByThreadRef.current[currentThreadKey] = preserveActiveSnapshot
        ? activeRunIdByThreadRef.current[currentThreadKey]
        : null;
      isStreamingByThreadRef.current[currentThreadKey] = false;
      patchThreadRuntime(currentThreadKey, {
        currentStatus: null,
        isLoading: false,
      });
      if (!preserveActiveSnapshot) {
        removeThreadActiveRun(currentThreadKey);
      }
    };

    const runId = activeRunIdByThreadRef.current[currentThreadKey];
    const resolvedThreadId = threadIdRef.current;
    if (!runId || !resolvedThreadId) {
      toast.warning("当前会话未分配运行编号，已在本地停止", {
        description: "服务端任务可能仍在后台执行。",
      });
      localAbort(false);
      return;
    }

    stopInFlightByThreadRef.current[currentThreadKey] = true;
    void (async () => {
      try {
        let lastError: unknown = null;
        for (let attempt = 1; attempt <= 2; attempt += 1) {
          try {
            const result = await cancelRun(runId, resolvedThreadId);
            const preserveActiveSnapshot = result.status === "stopping";
            if (preserveActiveSnapshot) {
              upsertThreadActiveRun(
                createLocalActiveRunSnapshot(
                  resolvedThreadId,
                  result.run_id,
                  result.status,
                ),
              );
            }
            suppressUnreadOnInactiveRef.current[currentThreadKey] = true;
            toast.success("已停止本轮任务");
            localAbort(preserveActiveSnapshot);
            return;
          } catch (err) {
            lastError = err;
            if (attempt < 2) {
              continue;
            }
          }
        }

        console.error("取消 run 失败:", lastError);
        toast.error("停止失败，任务可能仍在后台执行");
        localAbort(false);
      } finally {
        stopInFlightByThreadRef.current[currentThreadKey] = false;
      }
    })();
  }, [
    getCurrentThreadKey,
    patchThreadRuntime,
    removeThreadActiveRun,
    upsertThreadActiveRun,
  ]);

  /**
   * 提取文本辅助函数
   */
  const extractText = useCallback(
    (m: Message | string | Message[] | undefined): string => {
      if (!m) return "";
      if (typeof m === "string") return m;
      const msg = Array.isArray(m) ? m[m.length - 1] : m;
      if (!msg) return "";
      const c = msg.content;
      if (typeof c === "string") return c;
      if (Array.isArray(c)) {
        return c
          .map((b) => {
            if (
              typeof b === "object" &&
              b !== null &&
              "type" in b &&
              "text" in b &&
              (b as { type?: unknown }).type === "text" &&
              typeof (b as { text?: unknown }).text === "string"
            ) {
              return (b as { text: string }).text;
            }
            return "";
          })
          .filter((text) => text.length > 0)
          .join("\n");
      }
      return "";
    },
    [],
  );

  /**
   * 提交消息
   */
  const submit = useCallback(
    (
      update?: {
        messages?: Message[] | Message | string;
        context?: Record<string, unknown>;
        attachments?: Attachment[];
      },
      _options?: unknown,
    ) => {
      const requestThreadKey = resolveThreadKey(threadId, draftSessionId);
      const requestSelectionKey = requestThreadKey;
      try {
        if (update?.messages) {
          if (typeof update.messages === "string") {
            updateThreadMessages(requestThreadKey, (prev) => [
              ...prev,
              { type: "human", content: update.messages } as Message,
            ]);
          } else if (Array.isArray(update.messages)) {
            updateThreadMessages(requestThreadKey, (prev) => [
              ...prev,
              ...(update.messages as Message[]),
            ]);
          } else {
            updateThreadMessages(requestThreadKey, (prev) => [
              ...prev,
              update.messages as Message,
            ]);
          }
        }

        const prompt = extractText(update?.messages);
        if (
          !prompt.trim() &&
          (!update?.attachments || update.attachments.length === 0)
        )
          return;

        const aiId = uuidv4();
        const runtimeKeyRef = { current: requestThreadKey };
        currentAiIdByThreadRef.current[requestThreadKey] = aiId;
        activeRunIdByThreadRef.current[requestThreadKey] = null;
        isStreamingByThreadRef.current[requestThreadKey] = true;
        updateThreadMessages(requestThreadKey, (prev) => [
          ...prev,
          { id: aiId, type: "ai", content: "" } as Message,
        ]);
        patchThreadRuntime(requestThreadKey, {
          currentStatus: null,
          isLoading: true,
          error: undefined,
          interrupt: null,
        });
        if (threadId) {
          upsertThreadActiveRun(
            createLocalActiveRunSnapshot(threadId, "", "running"),
          );
        }
        const idempotencyKey = uuidv4();

        let currentTodoId: number | undefined;
        if (typeof window !== "undefined") {
          const stored = sessionStorage.getItem("selectedTodo");
          const parsed = safeParseJson(stored, SelectedTodoSchema, null);
          currentTodoId = parsed?.id;
        }

        const { stop: stopFn, promise } = startLLMStream(
          prompt,
          {
            onToken: (token: string) => {
              updateThreadMessages(runtimeKeyRef.current, (prev) =>
                appendTokenToMessages(prev, aiId, token),
              );
              patchThreadRuntime(runtimeKeyRef.current, {
                currentStatus: null,
              });
            },
            onThinking: (content: string) => {
              updateThreadMessages(runtimeKeyRef.current, (prev) =>
                appendThinkingToMessages(prev, aiId, content),
              );
            },
            onToolStart: (name: string, input: Record<string, unknown>) => {
              updateThreadMessages(runtimeKeyRef.current, (prev) =>
                addToolCallToMessages(prev, aiId, name, input),
              );
            },
            onToolEnd: (name: string, output: unknown) => {
              console.debug(
                `工具 ${name} 执行完成:`,
                getToolOutputPreview(output),
              );
            },
            onInit: (id: string, runId?: string) => {
              const resolvedThreadKey = getThreadKey(id);
              const shouldSelectInitializedThread =
                getCurrentThreadKey() === requestSelectionKey;
              rekeyThreadRuntime(runtimeKeyRef.current, resolvedThreadKey);
              runtimeKeyRef.current = resolvedThreadKey;
              if (shouldSelectInitializedThread) {
                void setThreadId(id);
              }
              upsertThread({
                thread_id: id,
                title: buildLocalThreadTitle(prompt),
                updated_at: new Date().toISOString(),
              });
              patchThreadRuntime(resolvedThreadKey, { isLoading: true });
              upsertThreadActiveRun(
                createLocalActiveRunSnapshot(id, runId ?? "", "running"),
              );
            },
            onDone: (
              _tid?: string,
              messageId?: number,
              meta?: Record<string, unknown>,
            ) => {
              finalizeStreamLifecycle(runtimeKeyRef.current, aiId, {
                messageId,
                markUnread: shouldMarkThreadUnreadAfterDone(meta),
              });
              if (messageId) {
                console.log("已更新消息数据库ID:", messageId);
              }
            },
            onError: (message: string) => {
              syncThreadUnreadState(runtimeKeyRef.current, false);
              suppressUnreadOnInactiveRef.current[runtimeKeyRef.current] = true;
              patchThreadRuntime(runtimeKeyRef.current, {
                error: new Error(message),
              });
              toast.error("请求失败", { description: message });
              removeThreadActiveRun(runtimeKeyRef.current);
            },
            onResult: (data: ResultEventData, meta?: StreamResultMeta) => {
              handleStructuredResultEvent(
                runtimeKeyRef.current,
                aiId,
                data,
                false,
                meta,
              );
            },
            onFinalAnswer: (data) => {
              applyFinalAnswerToMessage(
                runtimeKeyRef.current,
                aiId,
                data.content,
                data.meta,
              );
              patchThreadRuntime(runtimeKeyRef.current, {
                currentStatus: null,
              });
            },
            onDisplayBlocks: (data) => {
              applyDisplayBlocksToMessage(runtimeKeyRef.current, aiId, data);
              patchThreadRuntime(runtimeKeyRef.current, {
                currentStatus: null,
              });
            },
            onStatus: (statusData: StatusEventData) => {
              const normalizedStatus = normalizeStatusData(statusData);
              if (!normalizedStatus) return;
              console.log(
                `📊 状态更新(${normalizedStatus.phase}): ${normalizedStatus.message}`,
              );
              patchThreadRuntime(runtimeKeyRef.current, {
                currentStatus: normalizedStatus,
              });
            },
            onClarification: (data: ClarificationEventData) => {
              console.log(`❓ 澄清问题:`, data.questions);
              applyClarificationToMessage(runtimeKeyRef.current, aiId, data);
              patchThreadRuntime(runtimeKeyRef.current, {
                currentStatus: null,
              });
            },
            onInterrupt: (data: InterruptData) => {
              syncThreadUnreadState(runtimeKeyRef.current, false);
              patchThreadRuntime(runtimeKeyRef.current, {
                interrupt: data,
                isLoading: false,
                currentStatus: null,
              });
              stopByThreadRef.current[runtimeKeyRef.current] = null;
              removeThreadActiveRun(runtimeKeyRef.current);
              isStreamingByThreadRef.current[runtimeKeyRef.current] = false;
            },
            onKbImages: (images: Record<string, string>) => {
              console.log(
                `🖼️ 收到 kb_images 映射: ${Object.keys(images).length} 张图片`,
              );
              storeKbImagesToMessage(runtimeKeyRef.current, aiId, images);
              updateThreadRuntime(runtimeKeyRef.current, (prev) => ({
                ...prev,
                kbImages: { ...prev.kbImages, ...images },
              }));
            },
          },
          50,
          threadId ?? undefined,
          enableThinking,
          selectedModel,
          update?.attachments,
          currentTodoId,
          idempotencyKey,
        );

        if (typeof window !== "undefined" && currentTodoId) {
          sessionStorage.removeItem("selectedTodo");
          window.dispatchEvent(new Event("todoDeselected"));
        }

        stopByThreadRef.current[requestThreadKey] = stopFn;
        promise
          .catch(() => undefined)
          .finally(() => {
            const finalThreadKey = runtimeKeyRef.current;
            patchThreadRuntime(finalThreadKey, { isLoading: false });
            stopByThreadRef.current[finalThreadKey] = null;
            currentAiIdByThreadRef.current[finalThreadKey] = null;
            isStreamingByThreadRef.current[finalThreadKey] = false;
          });
      } catch (e) {
        patchThreadRuntime(requestThreadKey, { error: e, isLoading: false });
      }
    },
    [
      draftSessionId,
      threadId,
      enableThinking,
      selectedModel,
      extractText,
      setThreadId,
      updateThreadMessages,
      patchThreadRuntime,
      rekeyThreadRuntime,
      handleStructuredResultEvent,
      applyDisplayBlocksToMessage,
      storeKbImagesToMessage,
      applyFinalAnswerToMessage,
      applyClarificationToMessage,
      finalizeStreamLifecycle,
      getCurrentThreadKey,
      updateThreadRuntime,
      removeThreadActiveRun,
      syncThreadUnreadState,
      upsertThreadActiveRun,
      resolveThreadKey,
      upsertThread,
    ],
  );

  /**
   * 恢复流程
   */
  const resume = useCallback(
    async (decision: DecisionType) => {
      if (!threadId || !interrupt) return;

      const currentThreadKey = getThreadKey(threadId);
      clearThreadUnread(currentThreadKey);
      patchThreadRuntime(currentThreadKey, {
        interrupt: null,
        currentStatus: null,
        isLoading: true,
        error: undefined,
      });

      let aiId = currentAiIdByThreadRef.current[currentThreadKey];
      const runtime =
        threadRuntimeRef.current[currentThreadKey] ??
        createEmptyThreadRuntime();
      if (!aiId) {
        const lastAiMsg = runtime.messages.filter((m) => m.type === "ai").pop();
        if (lastAiMsg?.id) {
          aiId = lastAiMsg.id;
        } else {
          aiId = uuidv4();
          updateThreadMessages(currentThreadKey, (prev) => [
            ...prev,
            { id: aiId!, type: "ai", content: "" } as Message,
          ]);
        }
        currentAiIdByThreadRef.current[currentThreadKey] = aiId;
      }

      isStreamingByThreadRef.current[currentThreadKey] = true;
      const { stop: stopFn, promise } = startResumeStream(
        threadId,
        decision,
        {
          onToken: (token: string) => {
            updateThreadMessages(currentThreadKey, (prev) =>
              appendTokenToMessages(prev, aiId!, token),
            );
            patchThreadRuntime(currentThreadKey, { currentStatus: null });
          },
          onToolStart: (name: string, input: Record<string, unknown>) => {
            updateThreadMessages(currentThreadKey, (prev) =>
              addToolCallToMessages(prev, aiId!, name, input),
            );
          },
          onToolEnd: (name: string, output: unknown) => {
            console.debug(
              `工具 ${name} 执行完成:`,
              getToolOutputPreview(output),
            );
          },
          onResult: (data: ResultEventData, meta?: StreamResultMeta) => {
            handleStructuredResultEvent(
              currentThreadKey,
              aiId!,
              data,
              true,
              meta,
            );
          },
          onFinalAnswer: (data) => {
            applyFinalAnswerToMessage(
              currentThreadKey,
              aiId!,
              data.content,
              data.meta,
            );
            patchThreadRuntime(currentThreadKey, { currentStatus: null });
          },
          onDisplayBlocks: (data) => {
            applyDisplayBlocksToMessage(currentThreadKey, aiId!, data);
            patchThreadRuntime(currentThreadKey, { currentStatus: null });
          },
          onStatus: (statusData: StatusEventData) => {
            const normalizedStatus = normalizeStatusData(statusData);
            if (!normalizedStatus) return;
            console.log(
              `📊 恢复流状态更新(${normalizedStatus.phase}): ${normalizedStatus.message}`,
            );
            patchThreadRuntime(currentThreadKey, {
              currentStatus: normalizedStatus,
            });
          },
          onClarification: (data: ClarificationEventData) => {
            console.log(`❓ 恢复流澄清问题:`, data.questions);
            applyClarificationToMessage(currentThreadKey, aiId!, data);
            patchThreadRuntime(currentThreadKey, { currentStatus: null });
          },
          onKbImages: (images: Record<string, string>) => {
            console.log(
              `🖼️ 恢复流收到 kb_images 映射: ${Object.keys(images).length} 张图片`,
            );
            storeKbImagesToMessage(currentThreadKey, aiId!, images);
            updateThreadRuntime(currentThreadKey, (prev) => ({
              ...prev,
              kbImages: { ...prev.kbImages, ...images },
            }));
          },
          onDone: (
            _tid?: string,
            messageId?: number,
            meta?: Record<string, unknown>,
          ) => {
            finalizeStreamLifecycle(currentThreadKey, aiId!, {
              messageId,
              markUnread: shouldMarkThreadUnreadAfterDone(meta),
            });
          },
          onError: (message: string) => {
            syncThreadUnreadState(currentThreadKey, false);
            suppressUnreadOnInactiveRef.current[currentThreadKey] = true;
            patchThreadRuntime(currentThreadKey, {
              error: new Error(message),
              isLoading: false,
            });
            toast.error("恢复失败", { description: message });
          },
          onInterrupt: (data: InterruptData) => {
            syncThreadUnreadState(currentThreadKey, true);
            patchThreadRuntime(currentThreadKey, {
              interrupt: data,
              isLoading: false,
            });
            stopByThreadRef.current[currentThreadKey] = null;
            isStreamingByThreadRef.current[currentThreadKey] = false;
          },
        },
        50,
      );

      stopByThreadRef.current[currentThreadKey] = stopFn;
      promise
        .catch(() => undefined)
        .finally(() => {
          patchThreadRuntime(currentThreadKey, { isLoading: false });
          stopByThreadRef.current[currentThreadKey] = null;
          currentAiIdByThreadRef.current[currentThreadKey] = null;
          isStreamingByThreadRef.current[currentThreadKey] = false;
        });
    },
    [
      threadId,
      interrupt,
      clearThreadUnread,
      patchThreadRuntime,
      updateThreadMessages,
      handleStructuredResultEvent,
      storeKbImagesToMessage,
      applyDisplayBlocksToMessage,
      applyFinalAnswerToMessage,
      applyClarificationToMessage,
      finalizeStreamLifecycle,
      syncThreadUnreadState,
      updateThreadRuntime,
    ],
  );

  const values: StateType = { messages, ui: [] };

  return {
    messages,
    values,
    isLoading,
    error,
    interrupt,
    submit,
    stop,
    resume,
    getMessagesMetadata,
    setBranch,
    startNewThread,
    threadId,
    enableThinking,
    setEnableThinking,
    selectedModel,
    handleModelChange,
    thinkingCapability,
    hideToolCalls,
    setHideToolCalls,
    currentStatus, // 当前处理状态
    kbImages, // 知识库图片映射
  };
}
