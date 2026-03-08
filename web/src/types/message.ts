/**
 * 统一消息类型定义（中文注释）
 * 
 * 所有消息来源（后端 API / SSE 实时流 / LangChain SDK）都必须转换为此格式。
 * 这是前端消息处理的单一数据源。
 */

import type { ResultEventEnvelope } from "@/types/generated/result-event";

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

    /** 用户反馈分数：1(赞) / -1(踩) / undefined(无) */
    feedbackScore?: number;
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

// 流式事件类型定义（与后端 app/services/chat_service.py 转发口径一致）
export const STREAM_EVENT_TYPES = [
    "init",            // 流初始化
    "token",           // AI 文本输出
    "thinking",        // 思考过程
    "tool_start",      // 工具调用开始
    "tool_end",        // 工具调用结束
    "status",          // 状态更新
    "result",          // 结构化结果（待办列表、图片等）
    "plan_ready",      // 问题合同准备完成（兼容期开关）
    "task_started",    // 执行任务开始
    "task_finished",   // 执行任务结束
    "coverage_check",  // 覆盖率检查
    "final_answer",    // 最终答复
    "kb_images",       // 知识库图片映射
    "confirmation",    // 确认请求
    "clarification",   // 澄清问题
    "interrupt",       // 中断等待
    "handoff",         // 智能体切换
    "stopped",         // 运行时停止
    "done",            // 完成
    "error",           // 错误
] as const;

export type StreamEventType = (typeof STREAM_EVENT_TYPES)[number];

/**
 * 流式事件结构
 */
export interface StreamEvent {
    type: StreamEventType;
    data: unknown;
    node?: string;  // 来源节点名称
}

/**
 * 流初始化事件数据
 */
export interface InitEventData {
    thread_id: string;
    run_id?: string;
}

/**
 * Token 事件数据
 */
export interface TokenEventData {
    content?: string;
    reasoning_content?: string;
}

/**
 * 结构化结果事件数据
 */
export interface ResultEventData {
    event?: "result";
    data_type: string;  // "todo_list" | "image" | "chart" | "sql_result" 等
    data: unknown;
    message?: string;
    event_id?: string;
    retry?: number;
    sequence_number?: number;
    envelope?: ResultEventEnvelope;
    result_contract_version?: string;
    renderer_key?: string;
    fallback_used?: boolean;
    warning_code?: string;
    fallback_payload_preview?: string;
}

/**
 * 最终答复事件数据
 */
export interface FinalAnswerEventData {
    content: string;
    meta?: Record<string, unknown>;
}

export type SqlChartFieldRole = "dimension" | "measure" | "time" | "identifier";

export type SqlChartFieldSemanticType = "categorical" | "numeric" | "temporal";

export type SqlChartAxisHint = "x" | "y" | "series" | "none";

export interface SqlResultChartFieldMeta {
    role: SqlChartFieldRole;
    semantic_type: SqlChartFieldSemanticType;
    axis_hint: SqlChartAxisHint;
    agg: "none" | "sum" | "avg" | "count";
}

/**
 * 问数 SQL 结果中的可选图表载荷
 */
export interface SqlResultChartData {
    type: "bar" | "line" | "pie";
    title?: string;
    x_key: string;
    x_label?: string;
    y_key: string;
    y_label?: string;
    series_name?: string;
    field_meta?: Record<string, SqlResultChartFieldMeta>;
    data: Array<Record<string, string | number>>;
}

/**
 * 问数 SQL 结果结构（`data_type=sql_result`）
 */
export interface SqlResultData {
    rows: Record<string, unknown>[];
    columns: string[];
    total_rows?: number;
    sql?: string;
    display_sql?: string;
    column_display_names?: string[];
    permission_scope_applied?: boolean;
    permission_scope_summary?: {
        data_role?: string;
        org_code?: string;
        org_name?: string;
        dept_code?: string;
        dept_name?: string;
        has_explicit_row_filters?: boolean;
        row_scope_keys?: string[];
        display_text?: string;
    };
    chart?: SqlResultChartData;
}

/**
 * 完成事件数据
 */
export interface DoneEventData {
    thread_id: string;
    run_id?: string;
    message_id?: number;
    final_content?: string;
    meta?: Record<string, unknown>;
}

/**
 * 澄清事件数据
 */
export interface ClarificationEventData {
    questions: string[];
    message?: string;
}

export type StatusPhase = "processing" | "generating" | "done";

/**
 * 状态事件数据
 */
export interface StatusEventData {
    message: string;
    phase?: StatusPhase;
}

/**
 * 知识库图片映射事件数据
 */
export interface KbImagesEventData {
    images: Record<string, string>;
}
