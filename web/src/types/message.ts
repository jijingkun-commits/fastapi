/**
 * 统一消息类型定义（中文注释）
 * 
 * 所有消息来源（后端 API / SSE 实时流 / LangChain SDK）都必须转换为此格式。
 * 这是前端消息处理的单一数据源。
 */

/**
 * 内容块类型
 * 支持多种内容格式：文本、Markdown、图片、图表、自定义 UI
 */
export interface ContentBlock {
    type: "text" | "markdown" | "image" | "chart" | "custom_ui";
    data: unknown;
    component?: string;
    props?: Record<string, unknown>;
}

/**
 * 工具调用类型
 */
export interface ToolCall {
    id: string;
    name: string;
    args: Record<string, unknown>;
    type?: "tool_call";
    status?: "pending" | "running" | "done" | "error";
    result?: string;
}

/**
 * 消息元数据
 */
export interface MessageMetadata {
    createdAt?: string;
    parentCheckpoint?: unknown;
    branch?: string;
    branchOptions?: string[];
}

/**
 * 统一消息类型
 * 
 * 所有消息（历史消息、实时消息）都应转换为此格式后再进行渲染
 */
export interface UnifiedMessage {
    /** 消息唯一标识 */
    id: string;

    /** 消息角色 */
    role: "human" | "ai" | "tool";

    /** 消息内容：字符串或内容块数组 */
    content: string | ContentBlock[];

    /** AI 消息的工具调用（可选） */
    toolCalls?: ToolCall[];

    /** AI 消息的思考内容（深度思考模式，可选） */
    thinkingContent?: string;

    /** 工具消息的工具名称（可选） */
    toolName?: string;

    /** 元数据（可选） */
    metadata?: MessageMetadata;

    /** 附加参数（用于传递自定义数据如 TodoList） */
    additionalKwargs?: Record<string, unknown>;
}

/**
 * 类型守卫：检查是否为 UnifiedMessage
 */
export function isUnifiedMessage(msg: unknown): msg is UnifiedMessage {
    if (!msg || typeof msg !== "object") return false;
    const m = msg as Record<string, unknown>;
    return (
        typeof m.id === "string" &&
        (m.role === "human" || m.role === "ai" || m.role === "tool") &&
        (typeof m.content === "string" || Array.isArray(m.content))
    );
}

/**
 * 类型守卫：检查内容是否为内容块数组
 */
export function isContentBlockArray(content: unknown): content is ContentBlock[] {
    return Array.isArray(content) && content.every(
        (c) => c && typeof c === "object" && "type" in c && "data" in c
    );
}

// 流式事件类型定义（与后端 app/ai/events.py 对应）
export type StreamEventType =
    | "token"           // AI 文本输出
    | "thinking"        // 思考过程
    | "tool_start"      // 工具调用开始
    | "tool_end"        // 工具调用结束
    | "status"          // 状态更新
    | "result"          // 结构化结果（待办列表、图片等）
    | "confirmation"    // 确认请求
    | "clarification"   // 澄清问题
    | "interrupt"       // 中断等待
    | "done"            // 完成
    | "error";          // 错误

/**
 * 流式事件结构
 */
export interface StreamEvent {
    type: StreamEventType;
    data: any;
    node?: string;  // 来源节点名称
}

/**
 * 结构化结果事件数据
 */
export interface ResultEventData {
    data_type: string;  // "todo_list" | "image" | "chart" 等
    data: any;
    message?: string;
}

/**
 * 澄清事件数据
 */
export interface ClarificationEventData {
    questions: string[];
    message?: string;
}

/**
 * 状态事件数据
 */
export interface StatusEventData {
    message: string;
}
