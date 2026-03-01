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
    startLLMStream,
    getThreadMessages,
    startResumeStream,
    InterruptData,
    DecisionType,
    Attachment,
} from "@/lib/backend";
import { fromBackendMessages } from "@/lib/message-normalizer";
import { useThreads } from "@/providers/Thread";
import { StateType, StreamContextValue, MessageMetadata, StreamStatus } from "@/providers/StreamContext";
import { useMessageUpdater } from "@/hooks/use-message-updater";
import { useModelConfig } from "@/hooks/use-model-config";
import type { KbImages } from "@/components/chat/utils";
import { safeParseJson, SelectedTodoSchema } from "@/lib/utils";
import type { ClarificationEventData, ResultEventData, StatusEventData } from "@/types/message";

type MessageWithAdditionalKwargs = Message & {
    additional_kwargs?: Record<string, unknown>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function getImageUrlFromResult(data: ResultEventData): string | null {
    if (data.data_type !== "image" || !isRecord(data.data)) {
        return null;
    }

    const value = data.data.url;
    if (typeof value !== "string") {
        return null;
    }

    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
}

function getErrorMessageFromResult(data: ResultEventData): string {
    if (typeof data.message === "string" && data.message.trim().length > 0) {
        return data.message;
    }
    if (isRecord(data.data) && typeof data.data.message === "string" && data.data.message.trim().length > 0) {
        return data.data.message;
    }
    return "未知错误";
}

function getToolOutputPreview(output: unknown): string {
    if (typeof output === "string") {
        return output.slice(0, 100);
    }
    try {
        const serialized = JSON.stringify(output);
        if (typeof serialized === "string") {
            return serialized.slice(0, 100);
        }
        return String(output).slice(0, 100);
    } catch {
        return String(output).slice(0, 100);
    }
}

function normalizeStatusData(statusData: StatusEventData): StreamStatus | null {
    const message = statusData.message.trim();
    if (message.length === 0) {
        return null;
    }
    return {
        message,
        phase: statusData.phase ?? "processing",
    };
}

function normalizeClarificationQuestions(questions: string[]): string[] {
    const normalized: string[] = [];
    for (const question of questions) {
        const trimmed = question.trim();
        if (!trimmed || normalized.includes(trimmed)) {
            continue;
        }
        normalized.push(trimmed);
    }
    return normalized;
}

function buildClarificationDisplayText(data: ClarificationEventData): string {
    const message = typeof data.message === "string" ? data.message.trim() : "";
    const questions = normalizeClarificationQuestions(data.questions);
    const formattedQuestions = questions
        .map((question, index) => `${index + 1}. ${question}`)
        .join("\n");

    if (message && formattedQuestions) {
        return `${message}\n\n${formattedQuestions}`;
    }
    if (formattedQuestions) {
        return formattedQuestions;
    }
    return message;
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
        handleModelChange
    } = useModelConfig();

    // 2. Message Updater Hook
    const {
        appendToAiMessage,
        appendImageToAiMessage,
        addToolCallToMessage,
        handleThinking
    } = useMessageUpdater(setMessages);

    // 3. UI Toggles (HideToolCalls)
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

    const stopRef = useRef<(() => void) | null>(null);
    const currentAiIdRef = useRef<string | null>(null);
    const activeRunIdRef = useRef<string | null>(null);
    const stopInFlightRef = useRef(false);
    const latestThreadResolvedRef = useRef(false);
    const isStreamingRef = useRef<boolean>(false);

    const [threadId, setThreadId] = useQueryState("threadId");
    const { refreshThreads } = useThreads();

    const bindMessageIdToAiMessage = useCallback((aiId: string, messageId?: number) => {
        if (!messageId) return;
        setMessages((prev) => {
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
    }, []);

    const storeStructuredResultToMessage = useCallback((
        aiId: string,
        data: ResultEventData,
    ) => {
        if (data.data_type === "error") {
            toast.error("操作失败", { description: getErrorMessageFromResult(data) });
            return;
        }

        setMessages((prev) => {
            const updated = [...prev];
            const idx = updated.findIndex((m) => m.id === aiId);
            if (idx === -1) {
                return updated;
            }

            const message = updated[idx] as MessageWithAdditionalKwargs;
            const existingKwargs = message.additional_kwargs ?? {};
            updated[idx] = {
                ...updated[idx],
                additional_kwargs: {
                    ...existingKwargs,
                    data_type: data.data_type,
                    data: data.data,
                },
            } as Message;
            return updated;
        });

        if (data.message) {
            appendToAiMessage(aiId, data.message);
        }
    }, [appendToAiMessage]);

    const applyFinalAnswerToMessage = useCallback((
        aiId: string,
        content: string,
        meta?: Record<string, unknown>,
    ) => {
        const normalized = content.trim();
        if (!normalized) {
            return;
        }

        setMessages((prev) => {
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
    }, []);

    const applyClarificationToMessage = useCallback((
        aiId: string,
        data: ClarificationEventData,
    ) => {
        const questions = normalizeClarificationQuestions(data.questions);
        const message = typeof data.message === "string" && data.message.trim().length > 0
            ? data.message.trim()
            : undefined;
        const displayContent = buildClarificationDisplayText({ questions, message });
        if (!displayContent) {
            return;
        }

        setMessages((prev) => {
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
    }, []);

    const completeStreamLifecycle = useCallback((aiId: string, messageId?: number) => {
        bindMessageIdToAiMessage(aiId, messageId);
        setCurrentStatus(null);
        setIsLoading(false);
        stopRef.current = null;
        currentAiIdRef.current = null;
        activeRunIdRef.current = null;
        isStreamingRef.current = false;
        refreshThreads();
    }, [bindMessageIdToAiMessage, refreshThreads]);

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
            setThreadId(latestThreadId);
            return true;
        } catch (err) {
            console.warn("加载最近会话失败:", err);
            toast.error("加载最近会话失败", {
                description: "已进入新会话，可继续输入。",
            });
            return false;
        }
    }, [setThreadId]);

    const handleStructuredResultEvent = useCallback((aiId: string, data: ResultEventData, isResume: boolean) => {
        const imageUrl = getImageUrlFromResult(data);
        if (imageUrl) {
            appendImageToAiMessage(aiId, imageUrl);
        }

        storeStructuredResultToMessage(aiId, data);
        if (isResume) {
            console.log(`恢复流收到结构化结果: ${data.data_type}`);
            return;
        }
        console.log(`收到结构化结果: ${data.data_type}`);
    }, [appendImageToAiMessage, storeStructuredResultToMessage]);

    /**
     * 加载历史消息
     */
    const loadThreadMessages = useCallback(async (id: string) => {
        try {
            setIsLoading(true);
            const rawMessages = await getThreadMessages(id);
            const normalized = fromBackendMessages(rawMessages);
            const converted = normalized.map((m) => ({
                id: m.id,
                type: m.role,
                content: m.content,
                ...(m.toolCalls && { tool_calls: m.toolCalls }),
                ...(m.additionalKwargs && { additional_kwargs: m.additionalKwargs }),
                ...(m.feedbackScore !== undefined && { feedback_score: m.feedbackScore }),
                ...(m.thinkingContent && {
                    content: `<think>\n${m.thinkingContent}\n</think>\n\n${typeof m.content === 'string' ? m.content : ''}`
                }),
            } as Message));
            setMessages(converted);
        } catch (err) {
            console.error("加载历史消息失败:", err);
            toast.error("加载历史消息失败");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (isStreamingRef.current) return;
        let cancelled = false;

        const run = async () => {
            if (threadId) {
                await loadThreadMessages(threadId);
                return;
            }

            const switchedToLatest = await resolveLatestThread();
            if (!cancelled && !switchedToLatest) {
                setMessages([]);
            }
        };

        void run();
        return () => {
            cancelled = true;
        };
    }, [threadId, loadThreadMessages, resolveLatestThread]);

    /**
     * 获取消息元数据
     */
    const getMessagesMetadata = useCallback((_msg: Message): MessageMetadata => {
        return {
            firstSeenState: { parent_checkpoint: null, values: { messages } },
            branch: undefined,
            branchOptions: undefined,
        };
    }, [messages]);

    const setBranch = useCallback((_branch: unknown) => { /* no-op in SSE */ }, []);

    /**
     * 停止生成
     */
    const stop = useCallback(() => {
        if (stopInFlightRef.current) {
            return;
        }

        const localAbort = () => {
            stopRef.current?.();
            stopRef.current = null;
            currentAiIdRef.current = null;
            activeRunIdRef.current = null;
            setCurrentStatus(null);
            setIsLoading(false);
            isStreamingRef.current = false;
        };

        const runId = activeRunIdRef.current;
        if (!runId) {
            toast.warning("当前会话未分配 run_id，已本地停止", {
                description: "服务端任务可能仍在后台执行。",
            });
            localAbort();
            return;
        }

        stopInFlightRef.current = true;
        void (async () => {
            try {
                let lastError: unknown = null;
                for (let attempt = 1; attempt <= 2; attempt += 1) {
                    try {
                        const result = await cancelRun(runId, {
                            reason: "user_cancelled",
                            cancel_mode: "hard",
                        });

                        const runControlDisabled = result.status === "disabled" || result.reason === "run_control_disabled";
                        if (runControlDisabled) {
                            toast.warning("当前环境未开启强停止，已本地停止", {
                                description: "服务端任务可能仍在后台执行。",
                            });
                        } else {
                            toast.success("已停止本轮任务");
                        }
                        localAbort();
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
                localAbort();
            } finally {
                stopInFlightRef.current = false;
            }
        })();
    }, []);

    /**
     * 提取文本辅助函数
     */
    const extractText = useCallback((m: Message | string | Message[] | undefined): string => {
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
                        typeof b === "object"
                        && b !== null
                        && "type" in b
                        && "text" in b
                        && (b as { type?: unknown }).type === "text"
                        && typeof (b as { text?: unknown }).text === "string"
                    ) {
                        return (b as { text: string }).text;
                    }
                    return "";
                })
                .filter((text) => text.length > 0)
                .join("\n");
        }
        return "";
    }, []);

    /**
     * 提交消息
     */
    const submit = useCallback((
        update?: { messages?: Message[] | Message | string; context?: Record<string, unknown>; attachments?: Attachment[] },
        _options?: unknown,
    ) => {
        try {
            // Optimistic update
            if (update?.messages) {
                if (typeof update.messages === "string") {
                    setMessages((prev) => [...prev, { type: "human", content: update.messages } as Message]);
                } else if (Array.isArray(update.messages)) {
                    setMessages((prev) => [...prev, ...(update.messages as Message[])]);
                } else {
                    setMessages((prev) => [...prev, update.messages as Message]);
                }
            }

            const prompt = extractText(update?.messages);
            if (!prompt.trim() && (!update?.attachments || update.attachments.length === 0)) return;

            const aiId = uuidv4();
            currentAiIdRef.current = aiId;
            activeRunIdRef.current = null;
            setMessages((prev) => [...prev, { id: aiId, type: "ai", content: "" } as Message]);
            setCurrentStatus(null);
            setIsLoading(true);
            isStreamingRef.current = true;
            const idempotencyKey = uuidv4();

            // 读取当前选中的待办 ID（使用 Zod 校验）
            // 注意：不要在发送前清除，避免 current_todo_id 丢失
            let currentTodoId: number | undefined;
            if (typeof window !== 'undefined') {
                const stored = sessionStorage.getItem('selectedTodo');
                const parsed = safeParseJson(stored, SelectedTodoSchema, null);
                currentTodoId = parsed?.id;
            }

            const { stop: stopFn, promise } = startLLMStream(
                prompt,
                {
                    onToken: (token: string) => {
                        appendToAiMessage(aiId, token);
                        setCurrentStatus(null);
                    },
                    onThinking: (content: string) => handleThinking(aiId, content),
                    onToolStart: (name: string, input: Record<string, unknown>) => addToolCallToMessage(aiId, name, input),
                    onToolEnd: (name: string, output: unknown) => {
                        console.debug(`工具 ${name} 执行完成:`, getToolOutputPreview(output));
                    },
                    onInit: (id: string, runId?: string) => {
                        setThreadId(id);
                        activeRunIdRef.current = runId ?? null;
                    },
                    onDone: (_tid?: string, messageId?: number) => {
                        completeStreamLifecycle(aiId, messageId);
                        if (messageId) {
                            console.log("已更新消息数据库ID:", messageId);
                        }
                    },
                    onError: (message: string) => {
                        setError(new Error(message));
                        toast.error("请求失败", { description: message });
                        activeRunIdRef.current = null;
                    },
                    // 处理结构化结果事件（待办列表等）
                    // 图片完全依赖 LLM 在回复中保留 Markdown 语法
                    onResult: (data: ResultEventData) => {
                        handleStructuredResultEvent(aiId, data, false);
                    },
                    onFinalAnswer: (data) => {
                        applyFinalAnswerToMessage(aiId, data.content, data.meta);
                        setCurrentStatus(null);
                    },
                    // 处理状态更新事件
                    onStatus: (statusData: StatusEventData) => {
                        const normalizedStatus = normalizeStatusData(statusData);
                        if (!normalizedStatus) return;
                        console.log(`📊 状态更新(${normalizedStatus.phase}): ${normalizedStatus.message}`);
                        setCurrentStatus(normalizedStatus);
                    },
                    // 处理澄清问题事件
                    onClarification: (data: ClarificationEventData) => {
                        console.log(`❓ 澄清问题:`, data.questions);
                        applyClarificationToMessage(aiId, data);
                        setCurrentStatus(null);
                    },
                    onInterrupt: (data: InterruptData) => {
                        setInterrupt(data);
                        setIsLoading(false);
                        stopRef.current = null;
                        activeRunIdRef.current = null;
                        isStreamingRef.current = false;
                    },
                    // 处理知识库图片映射事件
                    onKbImages: (images: Record<string, string>) => {
                        console.log(`🖼️ 收到 kb_images 映射: ${Object.keys(images).length} 张图片`);
                        setKbImages(prev => ({ ...prev, ...images }));
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

            // 请求已发起后再清理选中态，确保 current_todo_id 已携带进请求
            if (typeof window !== 'undefined' && currentTodoId) {
                sessionStorage.removeItem('selectedTodo');
                window.dispatchEvent(new Event('todoDeselected'));
            }

            stopRef.current = stopFn;
            promise.catch(() => undefined).finally(() => {
                setIsLoading(false);
                stopRef.current = null;
                currentAiIdRef.current = null;
                activeRunIdRef.current = null;
                isStreamingRef.current = false;
            });
        } catch (e) {
            setError(e);
            setIsLoading(false);
        }
    }, [
        threadId,
        enableThinking,
        selectedModel,
        extractText,
        handleThinking,
        addToolCallToMessage,
        setThreadId,
        appendToAiMessage,
        handleStructuredResultEvent,
        applyFinalAnswerToMessage,
        applyClarificationToMessage,
        completeStreamLifecycle,
    ]);

    /**
     * 恢复流程
     */
    const resume = useCallback(async (decision: DecisionType) => {
        if (!threadId || !interrupt) return;

        setInterrupt(null);
        setCurrentStatus(null);
        setIsLoading(true);

        // 复用最后一条 AI 消息，避免重复创建
        let aiId = currentAiIdRef.current;
        if (!aiId) {
            // 查找最后一条 AI 消息的 ID
            const lastAiMsg = messages.filter(m => m.type === "ai").pop();
            if (lastAiMsg?.id) {
                aiId = lastAiMsg.id;
            } else {
                // 只有在没有任何 AI 消息时才创建新的
                aiId = uuidv4();
                setMessages((prev) => [...prev, { id: aiId, type: "ai", content: "" } as Message]);
            }
            currentAiIdRef.current = aiId;
        }

        const { stop: stopFn, promise } = startResumeStream(
            threadId,
            decision,
            {
                onToken: (token: string) => {
                    appendToAiMessage(aiId, token);
                    setCurrentStatus(null);
                },
                onToolStart: (name: string, input: Record<string, unknown>) => addToolCallToMessage(aiId, name, input),
                onToolEnd: (name: string, output: unknown) => {
                    console.debug(`工具 ${name} 执行完成:`, getToolOutputPreview(output));
                },
                onResult: (data: ResultEventData) => {
                    handleStructuredResultEvent(aiId, data, true);
                },
                onFinalAnswer: (data) => {
                    applyFinalAnswerToMessage(aiId, data.content, data.meta);
                    setCurrentStatus(null);
                },
                onStatus: (statusData: StatusEventData) => {
                    const normalizedStatus = normalizeStatusData(statusData);
                    if (!normalizedStatus) return;
                    console.log(`📊 恢复流状态更新(${normalizedStatus.phase}): ${normalizedStatus.message}`);
                    setCurrentStatus(normalizedStatus);
                },
                onClarification: (data: ClarificationEventData) => {
                    console.log(`❓ 恢复流澄清问题:`, data.questions);
                    applyClarificationToMessage(aiId, data);
                    setCurrentStatus(null);
                },
                onKbImages: (images: Record<string, string>) => {
                    console.log(`🖼️ 恢复流收到 kb_images 映射: ${Object.keys(images).length} 张图片`);
                    setKbImages(prev => ({ ...prev, ...images }));
                },
                onDone: (_tid?: string, messageId?: number) => {
                    completeStreamLifecycle(aiId, messageId);
                },
                onError: (message: string) => {
                    setError(new Error(message));
                    toast.error("恢复失败", { description: message });
                },
                onInterrupt: (data: InterruptData) => {
                    setInterrupt(data);
                    setIsLoading(false);
                    stopRef.current = null;
                    isStreamingRef.current = false;
                },
            },
            50,
        );

        stopRef.current = stopFn;
        promise.catch(() => undefined).finally(() => {
            setIsLoading(false);
            stopRef.current = null;
            currentAiIdRef.current = null;
        });
    }, [threadId, interrupt, messages, appendToAiMessage, addToolCallToMessage, handleStructuredResultEvent, applyFinalAnswerToMessage, applyClarificationToMessage, completeStreamLifecycle]);

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
