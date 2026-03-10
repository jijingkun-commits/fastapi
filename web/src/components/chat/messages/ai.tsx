/**
 * AI 消息组件（中文注释）
 *
 * 渲染 AI 助手的回复消息，包括：
 * - Markdown 文本
 * - 工具调用展示
 * - Todo 列表卡片 (TodoListCard)
 * - SQL 结果卡片（图表 + 表格）
 * - 未注册类型 fallback 卡片
 */
import { parsePartialJson } from "@langchain/core/output_parsers";
import type { ReactElement } from "react";
import { useStreamContext } from "@/providers/Stream";
import { AIMessage, Checkpoint, Message, ToolMessage } from "@langchain/langgraph-sdk";
import { getContentString, replaceImagePlaceholders } from "../utils";
import { BranchSwitcher, CommandBar } from "./shared";
import { MarkdownText } from "../markdown-text";
import { cn } from "@/lib/utils";
import { ToolCalls, ToolResult, isUserVisibleToolName } from "./tool-calls";
import { MessageContentComplex } from "@langchain/core/messages";
import { useQueryState, parseAsBoolean } from "nuqs";
import TodoListCard from "@/components/todo/TodoListCard";
import { Todo } from "@/types/todo";
import { SqlResultTable } from "@/components/chat/messages/sql-result-table";
import { SqlResultChart } from "@/components/chat/messages/sql-result-chart";
import { coerceResultEventData } from "@/lib/validators/result-event";
import type { ResultEventData, SqlResultChartData } from "@/types/message";

/**
 * 解析 Anthropic 流式工具调用
 */
function parseAnthropicStreamedToolCalls(
  content: MessageContentComplex[],
): AIMessage["tool_calls"] {
  const toolCallContents = content.filter((c) => c.type === "tool_use" && c.id);

  return toolCallContents.map((tc) => {
    const toolCall = tc as Record<string, any>;
    let json: Record<string, any> = {};
    if (toolCall?.input) {
      try {
        json = parsePartialJson(toolCall.input) ?? {};
      } catch {
        // Pass
      }
    }
    return {
      name: toolCall.name ?? "",
      id: toolCall.id ?? "",
      args: json,
      type: "tool_call",
    };
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function syncSelectedTodoSelection(todoId: string | number | null, todo?: Todo) {
  if (typeof window === "undefined") {
    return;
  }

  const currentThreadId = new URL(window.location.href).searchParams.get("threadId");
  if (todoId && todo) {
    sessionStorage.setItem("selectedTodo", JSON.stringify({
      id: todoId,
      title: todo.title,
      threadId: currentThreadId,
    }));
    window.dispatchEvent(new Event("todoSelected"));
    return;
  }

  sessionStorage.removeItem("selectedTodo");
  window.dispatchEvent(new Event("todoDeselected"));
}

function buildFallbackPreview(resultEvent: ResultEventData): string {
  if (typeof resultEvent.fallback_payload_preview === "string" && resultEvent.fallback_payload_preview.length > 0) {
    return resultEvent.fallback_payload_preview;
  }

  try {
    const serialized = JSON.stringify(resultEvent.data);
    if (!serialized) {
      return "{}";
    }
    return serialized.length > 240 ? `${serialized.slice(0, 240)}...` : serialized;
  } catch {
    return String(resultEvent.data ?? "");
  }
}

function resolveResultEventKey(resultEvent: ResultEventData, index: number): string {
  const eventId = resultEvent.event_id ?? resultEvent.envelope?.id;
  if (typeof eventId === "string" && eventId.trim().length > 0) {
    return eventId;
  }

  const sequenceNumber = typeof resultEvent.sequence_number === "number"
    ? resultEvent.sequence_number
    : resultEvent.envelope?.sequence_number;

  if (typeof sequenceNumber === "number") {
    return `${resultEvent.data_type}-${sequenceNumber}`;
  }

  return `${resultEvent.data_type}-${index}`;
}

function asSqlResultChartData(value: unknown): SqlResultChartData | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const type = value.type;
  const xKey = value.x_key;
  const yKey = value.y_key;
  const data = value.data;
  if (
    (type !== "bar" && type !== "line" && type !== "pie")
    || typeof xKey !== "string"
    || typeof yKey !== "string"
    || !Array.isArray(data)
  ) {
    return undefined;
  }

  return value as unknown as SqlResultChartData;
}

function getResultEventsFromAdditionalKwargs(additionalKwargs: unknown): ResultEventData[] {
  if (!isRecord(additionalKwargs)) {
    return [];
  }

  const events: ResultEventData[] = [];
  if (Array.isArray(additionalKwargs.result_events)) {
    for (const item of additionalKwargs.result_events) {
      const resultEvent = coerceResultEventData(item);
      if (resultEvent) {
        events.push(resultEvent);
      }
    }
    if (events.length > 0) {
      return events;
    }
  }

  if (isRecord(additionalKwargs.result_event)) {
    const legacySingle = coerceResultEventData(additionalKwargs.result_event);
    if (legacySingle) {
      return [legacySingle];
    }
  }

  const legacyDataType = additionalKwargs.data_type;
  if (typeof legacyDataType !== "string" || legacyDataType.trim().length === 0) {
    return [];
  }

  return [
    {
      event: "result",
      data_type: legacyDataType.trim(),
      data: isRecord(additionalKwargs.data) ? additionalKwargs.data : {},
      message: typeof additionalKwargs.message === "string" ? additionalKwargs.message : undefined,
    },
  ];
}

type ResultRendererProps = {
  resultEvent: ResultEventData;
  displayContent: string;
  isLatestMessage: boolean;
  onAction: (command: string) => void;
};

type ResultRenderer = (props: ResultRendererProps) => ReactElement | null;

const todoListRenderer: ResultRenderer = ({ resultEvent, onAction, isLatestMessage }) => {
  if (!isRecord(resultEvent.data)) {
    return null;
  }

  const todos = Array.isArray(resultEvent.data.todos)
    ? (resultEvent.data.todos as Todo[])
    : [];
  if (todos.length === 0) {
    return null;
  }

  return (
    <TodoListCard
      todos={todos}
      onAction={onAction}
      readonly={false}
      fetchLatest={isLatestMessage}
      onSelectionChange={(todoId, todo) => {
        syncSelectedTodoSelection(todoId ?? null, todo as Todo | undefined);
      }}
      onRefresh={() => {
        onAction("查看待办");
      }}
    />
  );
};

const sqlResultRenderer: ResultRenderer = ({ resultEvent }) => {
  if (!isRecord(resultEvent.data)) {
    return null;
  }

  const rows = Array.isArray(resultEvent.data.rows)
    ? (resultEvent.data.rows as Record<string, any>[])
    : [];
  const columns = Array.isArray(resultEvent.data.columns)
    ? (resultEvent.data.columns as string[])
    : [];
  if (rows.length === 0 && columns.length === 0) {
    return null;
  }

  const chart = asSqlResultChartData(resultEvent.data.chart);

  return (
    <>
      {chart && <SqlResultChart chart={chart} />}
      <SqlResultTable
        columns={columns}
        columnDisplayNames={
          Array.isArray(resultEvent.data.column_display_names)
            ? (resultEvent.data.column_display_names as string[])
            : undefined
        }
        rows={rows}
        totalRows={typeof resultEvent.data.total_rows === "number" ? resultEvent.data.total_rows : undefined}
        sql={
          (typeof resultEvent.data.display_sql === "string" ? resultEvent.data.display_sql : undefined)
          ?? (typeof resultEvent.data.sql === "string" ? resultEvent.data.sql : undefined)
        }
        permissionScopeApplied={Boolean(resultEvent.data.permission_scope_applied)}
        permissionScopeText={
          isRecord(resultEvent.data.permission_scope_summary)
            ? (typeof resultEvent.data.permission_scope_summary.display_text === "string"
              ? resultEvent.data.permission_scope_summary.display_text
              : undefined)
            : undefined
        }
      />
    </>
  );
};

const imageRenderer: ResultRenderer = ({ resultEvent, displayContent }) => {
  if (!isRecord(resultEvent.data)) {
    return null;
  }

  const imageUrl = typeof resultEvent.data.url === "string"
    ? resultEvent.data.url.trim()
    : "";
  if (!imageUrl) {
    return null;
  }

  if (displayContent.includes(imageUrl)) {
    return null;
  }

  const alt = typeof resultEvent.data.alt === "string"
    ? resultEvent.data.alt
    : "生成图片";

  return (
    <div className="py-1">
      <MarkdownText>{`![${alt}](${imageUrl})`}</MarkdownText>
    </div>
  );
};

const fallbackRenderer: ResultRenderer = ({ resultEvent }) => {
  const fallbackPreview = buildFallbackPreview(resultEvent);

  return (
    <div
      className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900"
      data-testid="result-fallback-card"
    >
      <div className="font-medium">未注册结构化结果类型：{resultEvent.data_type}</div>
      <div className="mt-1 text-[11px] opacity-80">
        warning_code: {resultEvent.warning_code ?? "RESULT_RENDERER_NOT_REGISTERED"}
      </div>
      <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded bg-amber-100 p-2 text-[11px]">
        {fallbackPreview}
      </pre>
    </div>
  );
};

const rendererRegistry: Record<string, ResultRenderer> = {
  todo_list: todoListRenderer,
  sql_result: sqlResultRenderer,
  image: imageRenderer,
};

/**
 * AI 消息主组件
 */
export function AssistantMessage({
  message,
  isLoading,
  isLatestMessage = false,
  handleRegenerate,
}: {
  message: Message | undefined;
  isLoading: boolean;
  isLatestMessage?: boolean;
  handleRegenerate: (parentCheckpoint: Checkpoint | null | undefined) => void;
}) {
  const content = message?.content ?? [];
  const contentString = getContentString(content);
  const [hideToolCalls] = useQueryState(
    "hideToolCalls",
    parseAsBoolean.withDefault(false),
  );

  const thread = useStreamContext();
  const meta = message ? thread.getMessagesMetadata(message) : undefined;
  const kbImages = thread.kbImages;

  // 应用图片占位符替换
  const displayContent = replaceImagePlaceholders(contentString, kbImages);

  const parentCheckpoint = meta?.firstSeenState?.parent_checkpoint;
  const anthropicStreamedToolCalls = Array.isArray(content)
    ? parseAnthropicStreamedToolCalls(content)
    : undefined;

  const hasToolCalls =
    message
    && "tool_calls" in message
    && message.tool_calls
    && message.tool_calls.length > 0;
  const hasAnthropicToolCalls = !!anthropicStreamedToolCalls?.length;
  const isToolResult = message?.type === "tool";

  const aiMessage = message as AIMessage | undefined;
  const additionalKwargs = aiMessage?.additional_kwargs;
  const resultEvents = getResultEventsFromAdditionalKwargs(additionalKwargs);

  const handleAction = (command: string) => {
    thread.submit({ messages: command });
  };

  // 如果是工具结果消息，渲染 ToolResult 组件
  if (isToolResult) {
    if (hideToolCalls || !isUserVisibleToolName((message as ToolMessage)?.name)) {
      return null;
    }
    return (
      <div className="group mr-auto flex w-full items-start gap-2" data-testid="tool-result">
        <div className="chat-content-shell mx-auto flex w-full flex-col gap-2">
          <ToolResult message={message as ToolMessage} />
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="chat-content-shell mx-auto flex flex-col gap-2">
        {hasToolCalls && <ToolCalls toolCalls={message.tool_calls} isComplete={!isLoading} />}
        <MarkdownText className="markdown-content-readable">
          {displayContent}
        </MarkdownText>
      </div>
    );
  }

  return (
    <div className="group mr-auto flex w-full items-start gap-2" data-testid="ai-message">
      <div className="chat-content-shell mx-auto flex w-full flex-col gap-2">
        {displayContent.length > 0 && (
          <div className="py-1">
            <MarkdownText className="markdown-content-readable">{displayContent}</MarkdownText>
          </div>
        )}

        {resultEvents.map((resultEvent, index) => {
          const renderer = rendererRegistry[resultEvent.data_type] ?? fallbackRenderer;
          return (
            <div key={resolveResultEventKey(resultEvent, index)}>
              {renderer({
                resultEvent,
                displayContent,
                isLatestMessage,
                onAction: handleAction,
              })}
            </div>
          );
        })}

        {!hideToolCalls && (
          <>
            {hasToolCalls && <ToolCalls toolCalls={message.tool_calls} isComplete={!isLoading} />}
            {!hasToolCalls && hasAnthropicToolCalls && (
              <ToolCalls toolCalls={anthropicStreamedToolCalls} isComplete={!isLoading} />
            )}
          </>
        )}

        {contentString.trim().length > 0 && (
          <div
            className={cn(
              "flex items-center gap-2 transition-opacity",
              "opacity-0 group-focus-within:opacity-100 group-hover:opacity-100",
            )}
          >
            <BranchSwitcher
              branch={meta?.branch}
              branchOptions={meta?.branchOptions}
              onSelect={(branch) => thread.setBranch(branch)}
              isLoading={isLoading}
            />
            <CommandBar
              content={contentString}
              isLoading={isLoading}
              isAiMessage={true}
              handleRegenerate={() => handleRegenerate(parentCheckpoint)}
              messageId={message?.id}
              feedbackScore={(message as any)?.feedback_score}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export function AssistantMessageLoading() {
  return (
    <div className="chat-content-shell mx-auto flex items-start gap-2">
      <div className="bg-muted flex h-8 items-center gap-1 rounded-2xl px-4 py-2">
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_infinite] rounded-full"></div>
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_0.5s_infinite] rounded-full"></div>
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_1s_infinite] rounded-full"></div>
      </div>
    </div>
  );
}
