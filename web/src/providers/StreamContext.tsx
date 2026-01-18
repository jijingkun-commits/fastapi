/**
 * Stream Context 定义（中文注释）
 * 
 * 提供消息流的 Context 类型定义和 hook。
 * 从 Stream.tsx 拆分出来，用于解耦 Context 逻辑。
 */

import { createContext, useContext } from "react";
import { type Message, Checkpoint } from "@langchain/langgraph-sdk";
import { type UIMessage } from "@langchain/langgraph-sdk/react-ui";
import { InterruptData, DecisionType, Attachment } from "@/lib/backend";

/**
 * 状态类型
 */
export type StateType = { messages: Message[]; ui?: UIMessage[] };

/**
 * 消息元数据类型
 */
export interface MessageMetadata {
    firstSeenState?: {
        parent_checkpoint?: Checkpoint | null;
        values?: { messages: Message[] };
    };
    branch?: string;
    branchOptions?: string[];
}

/**
 * Stream Context 值类型
 */
export interface StreamContextValue {
    /** 消息列表 */
    messages: Message[];
    /** 完整状态值 */
    values: StateType;
    /** 是否正在加载 */
    isLoading: boolean;
    /** 错误信息 */
    error: unknown;
    /** 中断信息 */
    interrupt: InterruptData | null;
    /** 提交消息 */
    submit: (
        update?: { messages?: Message[] | Message | string; context?: Record<string, unknown>; attachments?: Attachment[] },
        options?: unknown
    ) => void;
    /** 停止生成 */
    stop: () => void;
    /** 恢复中断的流程 */
    resume: (decision: DecisionType) => Promise<void>;
    /** 获取消息元数据 */
    getMessagesMetadata: (msg: Message) => MessageMetadata | undefined;
    /** 设置分支 */
    setBranch: (branch: unknown) => void;
    /** 当前线程 ID */
    threadId: string | null;
    /** 深度思考开关 */
    enableThinking: boolean;
    /** 设置深度思考开关 */
    setEnableThinking: (value: boolean) => void;
    /** 当前选中的模型 ID */
    selectedModel: string;
    /** 模型变更处理函数 */
    handleModelChange: (modelId: string) => void;
    /** 当前模型的推理能力 */
    thinkingCapability: "always" | "never" | "optional";
    /** 多智能体模式开关 */
    useMultiAgent: boolean;
    /** 设置多智能体模式开关 */
    setUseMultiAgent: (value: boolean) => void;
    /** 隐藏工具调用开关 */
    hideToolCalls: boolean;
    /** 设置隐藏工具调用开关 */
    setHideToolCalls: (value: boolean) => void;
    /** 当前处理状态（如"正在分析..."） */
    currentStatus: string | null;
    /** 知识库图片映射（用于替换 [IMG-N] 占位符） */
    kbImages: Record<string, string>;
}

/**
 * Stream Context
 */
export const StreamContext = createContext<StreamContextValue | undefined>(undefined);

/**
 * 使用 Stream Context 的 hook
 */
export function useStreamContext(): StreamContextValue {
    const context = useContext(StreamContext);
    if (context === undefined) {
        throw new Error("useStreamContext must be used within a StreamProvider");
    }
    return context;
}

