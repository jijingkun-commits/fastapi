/**
 * 消息标准化服务（中文注释）
 * 
 * 将不同来源的消息格式统一转换为 UnifiedMessage 格式。
 * 支持的来源：
 * - 后端 API 返回的历史消息 (ConversationMessage)
 * - LangChain SDK 的 Message 类型
 * - SSE 实时流消息
 */

import { Message } from "@langchain/langgraph-sdk";
import { ConversationMessage, ContentBlock as BackendContentBlock } from "./backend";
import {
    UnifiedMessage,
    ContentBlock,
    ToolCall,
    isContentBlockArray
} from "@/types/message";

/**
 * 将后端历史消息转换为统一格式
 */
export function fromBackendMessage(msg: ConversationMessage): UnifiedMessage {
    const normalized: UnifiedMessage = {
        id: msg.id.toString(),
        role: msg.role,
        content: normalizeBackendContent(msg.content),
        metadata: {
            createdAt: msg.created_at,
        },
    };

    // 提取思考内容（如果存在于内容中）
    if (typeof normalized.content === "string") {
        const { content, thinking } = extractThinkingContent(normalized.content);
        if (thinking) {
            normalized.content = content;
            normalized.thinkingContent = thinking;
        }
    }

    // 从 metadata 恢复 additionalKwargs (用于 TodoList/SqlResult 等卡片渲染)
    if (msg.metadata && Object.keys(msg.metadata).length > 0) {
        normalized.additionalKwargs = msg.metadata;
    }

    // 恢复用户反馈状态
    if (msg.feedback_score !== undefined && msg.feedback_score !== null) {
        normalized.feedbackScore = msg.feedback_score;
    }

    return normalized;
}

/**
 * 将 LangChain Message 转换为统一格式
 */
export function fromLangChainMessage(msg: Message): UnifiedMessage {
    const role = msg.type === "human" ? "human" : msg.type === "tool" ? "tool" : "ai";

    const normalized: UnifiedMessage = {
        id: msg.id ?? generateId(),
        role,
        content: normalizeLangChainContent(msg.content),
    };

    // 处理 AI 消息特有字段
    if (msg.type === "ai") {
        const aiMsg = msg as any;
        if (aiMsg.tool_calls?.length > 0) {
            normalized.toolCalls = aiMsg.tool_calls.map(normalizeToolCall);
        }

        // 保留 additional_kwargs（用于传递自定义数据如 TodoList）
        if (aiMsg.additional_kwargs && Object.keys(aiMsg.additional_kwargs).length > 0) {
            normalized.additionalKwargs = aiMsg.additional_kwargs;
        }
    }

    // 处理 Tool 消息
    if (msg.type === "tool") {
        const toolMsg = msg as any;
        normalized.toolName = toolMsg.name;
    }

    // 提取思考内容
    if (typeof normalized.content === "string") {
        const { content, thinking } = extractThinkingContent(normalized.content);
        if (thinking) {
            normalized.content = content;
            normalized.thinkingContent = thinking;
        }
    }

    return normalized;
}

/**
 * 标准化后端内容格式
 */
function normalizeBackendContent(
    content: string | BackendContentBlock[]
): string | ContentBlock[] {
    if (typeof content === "string") {
        return content;
    }

    if (Array.isArray(content)) {
        return content.map((block) => ({
            type: block.type as ContentBlock["type"],
            data: block.data,
            component: block.component,
            props: block.props,
        }));
    }

    return String(content ?? "");
}


/**
 * 标准化 LangChain 内容格式
 */
function normalizeLangChainContent(content: Message["content"]): string | ContentBlock[] {
    if (typeof content === "string") {
        return content;
    }

    if (Array.isArray(content)) {
        // LangChain 多模态格式
        const hasOnlyText = content.every((c: any) => c.type === "text");

        // 如果只有文本，合并为字符串
        if (hasOnlyText) {
            return content
                .filter((c: any) => c.type === "text")
                .map((c: any) => c.text)
                .join("\n");
        }

        // 否则转换为内容块数组
        return content.map((c: any) => {
            if (c.type === "text") {
                return { type: "markdown" as const, data: c.text };
            }
            if (c.type === "image_url") {
                return { type: "image" as const, data: c.image_url };
            }
            return { type: "text" as const, data: JSON.stringify(c) };
        });
    }

    return String(content ?? "");
}

/**
 * 标准化工具调用
 */
function normalizeToolCall(tc: any): ToolCall {
    return {
        id: tc.id ?? generateId(),
        name: tc.name ?? "",
        args: tc.args ?? {},
        type: "tool_call",
        status: "done",
    };
}

/**
 * 从内容中提取思考部分
 * 解析 <think>...</think> 标签
 */
function extractThinkingContent(text: string): { content: string; thinking?: string } {
    const thinkRegex = /<think>([\s\S]*?)<\/think>/gi;
    const matches = [...text.matchAll(thinkRegex)];

    if (matches.length === 0) {
        return { content: text };
    }

    // 提取所有思考内容
    const thinkingParts = matches.map((m) => m[1].trim());
    const thinking = thinkingParts.join("\n\n");

    // 移除思考标签后的内容
    const content = text.replace(thinkRegex, "").trim();

    return { content, thinking };
}

/**
 * 获取消息的纯文本内容
 */
export function getMessageTextContent(msg: UnifiedMessage): string {
    if (typeof msg.content === "string") {
        return msg.content;
    }

    if (isContentBlockArray(msg.content)) {
        return msg.content
            .filter((b) => b.type === "text" || b.type === "markdown")
            .map((b) => String(b.data))
            .join("\n");
    }

    return "";
}

/**
 * 生成唯一 ID
 */
function generateId(): string {
    // 使用更可靠的 ID 生成方式，避免 SSR 环境下 crypto 不可用的问题
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    // 回退方案
    return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

/**
 * 批量转换后端消息
 */
export function fromBackendMessages(messages: ConversationMessage[]): UnifiedMessage[] {
    return messages.map(fromBackendMessage);
}

/**
 * 批量转换 LangChain 消息
 */
export function fromLangChainMessages(messages: Message[]): UnifiedMessage[] {
    return messages.map(fromLangChainMessage);
}
