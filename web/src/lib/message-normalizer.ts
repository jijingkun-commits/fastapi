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
import { coerceResultEventData } from "@/lib/validators/result-event";
import { ConversationMessage, ContentBlock as BackendContentBlock } from "./backend";
import {
    UnifiedMessage,
    ContentBlock,
    ToolCall,
    ResultEventData,
    isContentBlockArray,
} from "@/types/message";

interface ReplayResultEventsResolution {
    events: ResultEventData[];
    compatSource: "result_events" | "result_event" | "data_type_data" | "none";
}

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

    // 从 metadata 恢复 additionalKwargs（读旧写新：统一写回 result_events[]）
    if (msg.metadata && Object.keys(msg.metadata).length > 0) {
        const replayKwargs = normalizeReplayAdditionalKwargs(msg.metadata);
        if (Object.keys(replayKwargs).length > 0) {
            normalized.additionalKwargs = replayKwargs;
        }
    }

    // 恢复用户反馈状态
    if (msg.feedback_score !== undefined && msg.feedback_score !== null) {
        normalized.feedbackScore = msg.feedback_score;
    }

    return normalized;
}

function normalizeReplayAdditionalKwargs(
    metadata: Record<string, unknown>,
): Record<string, unknown> {
    const normalized = { ...metadata };
    const resolution = resolveReplayResultEvents(metadata);
    if (resolution.events.length === 0) {
        return normalized;
    }

    const sortedEvents = sequenceNumberSort(resolution.events);
    const latestEvent = sortedEvents[sortedEvents.length - 1];
    if (!latestEvent) {
        return normalized;
    }

    normalized.result_events = sortedEvents;
    normalized.result_event = latestEvent;
    normalized.result_count = sortedEvents.length;
    normalized.compat_source = resolution.compatSource;
    normalized.data_type = latestEvent.data_type;
    normalized.data = latestEvent.data;
    if (typeof latestEvent.message === "string" && latestEvent.message.trim().length > 0) {
        normalized.message = latestEvent.message;
    }

    return normalized;
}

function resolveReplayResultEvents(metadata: Record<string, unknown>): ReplayResultEventsResolution {
    const canonicalEvents = coerceResultEventArray(metadata.result_events);
    if (canonicalEvents.length > 0) {
        return {
            events: canonicalEvents,
            compatSource: "result_events",
        };
    }

    const legacySingle = coerceResultEventData(metadata.result_event);
    if (legacySingle) {
        return {
            events: [legacySingle],
            compatSource: "result_event",
        };
    }

    const legacyPairEvent = buildLegacyPairEvent(metadata);
    if (legacyPairEvent) {
        return {
            events: [legacyPairEvent],
            compatSource: "data_type_data",
        };
    }

    return {
        events: [],
        compatSource: "none",
    };
}

function coerceResultEventArray(value: unknown): ResultEventData[] {
    if (!Array.isArray(value)) {
        return [];
    }

    const events: ResultEventData[] = [];
    for (const item of value) {
        const normalized = coerceResultEventData(item);
        if (normalized) {
            events.push(normalized);
        }
    }
    return events;
}

function buildLegacyPairEvent(metadata: Record<string, unknown>): ResultEventData | null {
    const dataType = toNonEmptyString(metadata.data_type);
    if (!dataType) {
        return null;
    }

    const legacyPayload: Record<string, unknown> = {
        event: "result",
        data_type: dataType,
        data: isRecord(metadata.data) ? metadata.data : {},
    };

    const message = toNonEmptyString(metadata.message);
    if (message) {
        legacyPayload.message = message;
    }

    const sequenceNumber = toNonNegativeInt(metadata.sequence_number);
    if (sequenceNumber !== undefined) {
        legacyPayload.sequence_number = sequenceNumber;
    }

    if (isRecord(metadata.envelope)) {
        legacyPayload.envelope = metadata.envelope;
    }

    const contractVersion = toNonEmptyString(metadata.result_contract_version);
    if (contractVersion) {
        legacyPayload.result_contract_version = contractVersion;
    }

    return coerceResultEventData(legacyPayload);
}

function sequenceNumberSort(events: ResultEventData[]): ResultEventData[] {
    return events
        .map((event, index) => ({
            event,
            index,
            sequenceNumber: resolveResultSequence(event),
        }))
        .sort((left, right) => {
            if (left.sequenceNumber === undefined && right.sequenceNumber === undefined) {
                return left.index - right.index;
            }
            if (left.sequenceNumber === undefined) {
                return 1;
            }
            if (right.sequenceNumber === undefined) {
                return -1;
            }
            if (left.sequenceNumber === right.sequenceNumber) {
                return left.index - right.index;
            }
            return left.sequenceNumber - right.sequenceNumber;
        })
        .map((item) => item.event);
}

function resolveResultSequence(event: ResultEventData): number | undefined {
    const sequenceFromEvent = toNonNegativeInt(event.sequence_number);
    if (sequenceFromEvent !== undefined) {
        return sequenceFromEvent;
    }
    return toNonNegativeInt(event.envelope?.sequence_number);
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function toNonEmptyString(value: unknown): string | undefined {
    return typeof value === "string" && value.trim().length > 0 ? value.trim() : undefined;
}

function toNonNegativeInt(value: unknown): number | undefined {
    if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
        return Math.trunc(value);
    }
    if (typeof value === "string") {
        const parsed = Number.parseInt(value, 10);
        if (!Number.isNaN(parsed) && parsed >= 0) {
            return parsed;
        }
    }
    return undefined;
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
