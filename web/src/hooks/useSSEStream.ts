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
import { replaceImagePlaceholders, type KbImages } from "@/components/chat/utils";

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

    // 3. UI Toggles (MultiAgent, HideToolCalls)
    const [useMultiAgent, setUseMultiAgentState] = useState(false);
    const [hideToolCalls, setHideToolCallsState] = useState(false);

    // 从 localStorage 恢复开关状态
    useEffect(() => {
        if (typeof window !== "undefined") {
            const savedMultiAgent = localStorage.getItem("chat:useMultiAgent");
            if (savedMultiAgent === "true") setUseMultiAgentState(true);

            const savedHideToolCalls = localStorage.getItem("chat:hideToolCalls");
            if (savedHideToolCalls === "true") setHideToolCallsState(true);
        }
    }, []);

    const setUseMultiAgent = useCallback((value: boolean) => {
        setUseMultiAgentState(value);
        if (typeof window !== "undefined") {
            localStorage.setItem("chat:useMultiAgent", value.toString());
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
                ...(m.additionalKwargs && { additional_kwargs: m.additionalKwargs }), // 保留 additionalKwargs
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
        const c = (msg as Message).content as any;
        if (typeof c === "string") return c;
        if (Array.isArray(c)) {
            return c
                .filter((b: any) => b && b.type === "text" && typeof b.text === "string")
                .map((b: any) => b.text)
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

            const { stop: stopFn, promise } = startLLMStream(
                prompt,
                {
                    onToken: (token: string) => appendToAiMessage(aiId, token),
                    onThinking: (content: string) => handleThinking(aiId, content),
                    onToolStart: (name: string, input: any) => addToolCallToMessage(aiId, name, input),
                    onToolEnd: (name: string, output: any) => {
                        console.debug(`工具 ${name} 执行完成:`, output?.slice?.(0, 100));
                    },
                    onInit: (id: string) => setThreadId(id),
                    onDone: (_tid?: string, additionalKwargs?: Record<string, unknown>) => {
                        // 如果有 additional_kwargs，更新最后一条 AI 消息
                        if (additionalKwargs && Object.keys(additionalKwargs).length > 0) {
                            setMessages((prev) => {
                                const updated = [...prev];
                                // 找到当前正在流式输出的 AI 消息
                                const idx = updated.findIndex(m => m.id === aiId);
                                if (idx !== -1) {
                                    updated[idx] = {
                                        ...updated[idx],
                                        additional_kwargs: additionalKwargs,
                                    };
                                    console.log("已更新消息 additional_kwargs:", Object.keys(additionalKwargs));
                                }
                                return updated;
                            });
                        }
                        setCurrentStatus(null); // 清除状态消息
                        setIsLoading(false);
                        stopRef.current = null;
                        currentAiIdRef.current = null;
                        isStreamingRef.current = false;
                        refreshThreads();
                    },
                    onError: (message: string) => {
                        setError(new Error(message));
                        toast.error("请求失败", { description: message });
                    },
                    // 处理结构化结果事件（待办列表等）
                    // 图片完全依赖 LLM 在回复中保留 Markdown 语法
                    onResult: (data: { data_type: string; data: any; message?: string }) => {
                        // 处理错误类型：显示 toast 提示
                        if (data.data_type === "error") {
                            toast.error("操作失败", { description: data.message || data.data?.message || "未知错误" });
                            return;
                        }

                        setMessages((prev) => {
                            const updated = [...prev];
                            const idx = updated.findIndex(m => m.id === aiId);
                            if (idx !== -1) {
                                // 将结构化数据存入 additional_kwargs
                                const existingKwargs = (updated[idx] as any).additional_kwargs || {};
                                updated[idx] = {
                                    ...updated[idx],
                                    additional_kwargs: {
                                        ...existingKwargs,
                                        data_type: data.data_type,  // 注意：使用 snake_case 以匹配 ai.tsx
                                        data: data.data,
                                    },
                                };
                                console.log(`收到结构化结果: ${data.data_type}`);
                            }
                            return updated;
                        });
                        // 如果有文本消息，追加到内容
                        if (data.message) {
                            appendToAiMessage(aiId, data.message);
                        }
                    },
                    // 处理状态更新事件
                    onStatus: (statusMsg: string) => {
                        console.log(`📊 状态更新: ${statusMsg}`);
                        // 设置状态消息，在 UI 中显示
                        setCurrentStatus(statusMsg);
                    },
                    // 处理澄清问题事件
                    onClarification: (data: { questions: string[]; message?: string }) => {
                        console.log(`❓ 澄清问题:`, data.questions);
                        // 澄清问题通常由 AI 消息内容展示，这里只是日志
                    },
                    onInterrupt: (data: InterruptData) => {
                        setInterrupt(data);
                        setIsLoading(false);
                        stopRef.current = null;
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
                useMultiAgent,
                update?.attachments,
            );

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
        useMultiAgent,
        extractText,
        appendToAiMessage,
        handleThinking,
        addToolCallToMessage,
        setThreadId,
        refreshThreads,
    ]);

    /**
     * 恢复流程
     */
    const resume = useCallback(async (decision: DecisionType) => {
        if (!threadId || !interrupt) return;

        setInterrupt(null);
        setIsLoading(true);

        const aiId = currentAiIdRef.current || uuidv4();
        if (!currentAiIdRef.current) {
            currentAiIdRef.current = aiId;
            setMessages((prev) => [...prev, { id: aiId, type: "ai", content: "" } as Message]);
        }

        const { stop: stopFn, promise } = startResumeStream(
            threadId,
            decision,
            {
                onToken: (token: string) => appendToAiMessage(aiId, token),
                onToolStart: (name: string, input: any) => addToolCallToMessage(aiId, name, input),
                onToolEnd: (name: string, output: any) => {
                    console.debug(`工具 ${name} 执行完成:`, output?.slice?.(0, 100));
                },
                onDone: (_tid?: string) => {
                    setIsLoading(false);
                    stopRef.current = null;
                    currentAiIdRef.current = null;
                    refreshThreads();
                },
                onError: (message: string) => {
                    setError(new Error(message));
                    toast.error("恢复失败", { description: message });
                },
                onInterrupt: (data: InterruptData) => {
                    setInterrupt(data);
                    setIsLoading(false);
                    stopRef.current = null;
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
    }, [threadId, interrupt, appendToAiMessage, addToolCallToMessage, refreshThreads]);

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
        useMultiAgent,
        setUseMultiAgent,
        hideToolCalls,
        setHideToolCalls,
        currentStatus, // 当前处理状态
        kbImages, // 知识库图片映射
    };
}
