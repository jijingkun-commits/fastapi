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
    startLLMStream,
    getThreadMessages,
    startResumeStream,
    InterruptData,
    DecisionType,
    Attachment,
} from "@/lib/backend";
import { fromBackendMessages } from "@/lib/message-normalizer";
import { useThreads } from "@/providers/Thread";
import { StateType, StreamContextValue, MessageMetadata } from "@/providers/StreamContext";
import { useMessageUpdater } from "@/hooks/use-message-updater";
import { useModelConfig } from "@/hooks/use-model-config";
import type { KbImages } from "@/components/chat/utils";
import { safeParseJson, SelectedTodoSchema } from "@/lib/utils";
import type { ClarificationEventData, ResultEventData } from "@/types/message";

type MessageWithAdditionalKwargs = Message & {
    additional_kwargs?: Record<string, unknown>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
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

/**
 * SSE 流消息处理 Hook
 */
export function useSSEStream(): StreamContextValue {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<unknown>(undefined);
    const [interrupt, setInterrupt] = useState<InterruptData | null>(null);
    // 当前处理状态（显示如"正在分析..."）
    const [currentStatus, setCurrentStatus] = useState<string | null>(null);
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

    const completeStreamLifecycle = useCallback((aiId: string, messageId?: number) => {
        bindMessageIdToAiMessage(aiId, messageId);
        setCurrentStatus(null);
        setIsLoading(false);
        stopRef.current = null;
        currentAiIdRef.current = null;
        isStreamingRef.current = false;
        refreshThreads();
    }, [bindMessageIdToAiMessage, refreshThreads]);

    const handleStructuredResultEvent = useCallback((aiId: string, data: ResultEventData, isResume: boolean) => {
        storeStructuredResultToMessage(aiId, data);
        if (isResume) {
            console.log(`恢复流收到结构化结果: ${data.data_type}`);
            return;
        }
        console.log(`收到结构化结果: ${data.data_type}`);
    }, [storeStructuredResultToMessage]);

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
        if (threadId) {
            loadThreadMessages(threadId);
        } else {
            setMessages([]);
        }
    }, [threadId, loadThreadMessages]);

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
        stopRef.current?.();
        stopRef.current = null;
        currentAiIdRef.current = null;
        setIsLoading(false);
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
            setMessages((prev) => [...prev, { id: aiId, type: "ai", content: "" } as Message]);
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
                    onToken: (token: string) => appendToAiMessage(aiId, token),
                    onThinking: (content: string) => handleThinking(aiId, content),
                    onToolStart: (name: string, input: Record<string, unknown>) => addToolCallToMessage(aiId, name, input),
                    onToolEnd: (name: string, output: unknown) => {
                        console.debug(`工具 ${name} 执行完成:`, getToolOutputPreview(output));
                    },
                    onInit: (id: string) => setThreadId(id),
                    onDone: (_tid?: string, messageId?: number) => {
                        completeStreamLifecycle(aiId, messageId);
                        if (messageId) {
                            console.log("已更新消息数据库ID:", messageId);
                        }
                    },
                    onError: (message: string) => {
                        setError(new Error(message));
                        toast.error("请求失败", { description: message });
                    },
                    // 处理结构化结果事件（待办列表等）
                    // 图片完全依赖 LLM 在回复中保留 Markdown 语法
                    onResult: (data: ResultEventData) => {
                        handleStructuredResultEvent(aiId, data, false);
                    },
                    // 处理状态更新事件
                    onStatus: (statusMsg: string) => {
                        console.log(`📊 状态更新: ${statusMsg}`);
                        // 设置状态消息，在 UI 中显示
                        setCurrentStatus(statusMsg);
                    },
                    // 处理澄清问题事件
                    onClarification: (data: ClarificationEventData) => {
                        console.log(`❓ 澄清问题:`, data.questions);
                        // 澄清问题通常由 AI 消息内容展示，这里只是日志
                    },
                    onInterrupt: (data: InterruptData) => {
                        setInterrupt(data);
                        setIsLoading(false);
                        stopRef.current = null;
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
        completeStreamLifecycle,
    ]);

    /**
     * 恢复流程
     */
    const resume = useCallback(async (decision: DecisionType) => {
        if (!threadId || !interrupt) return;

        setInterrupt(null);
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
                onToken: (token: string) => appendToAiMessage(aiId, token),
                onToolStart: (name: string, input: Record<string, unknown>) => addToolCallToMessage(aiId, name, input),
                onToolEnd: (name: string, output: unknown) => {
                    console.debug(`工具 ${name} 执行完成:`, getToolOutputPreview(output));
                },
                onResult: (data: ResultEventData) => {
                    handleStructuredResultEvent(aiId, data, true);
                },
                onStatus: (statusMsg: string) => {
                    console.log(`📊 恢复流状态更新: ${statusMsg}`);
                    setCurrentStatus(statusMsg);
                },
                onClarification: (data: ClarificationEventData) => {
                    console.log(`❓ 恢复流澄清问题:`, data.questions);
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
    }, [threadId, interrupt, messages, appendToAiMessage, addToolCallToMessage, handleStructuredResultEvent, completeStreamLifecycle]);

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
