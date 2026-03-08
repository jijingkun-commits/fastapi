/**
 * AI 消息组件（中文注释）
 * 
 * 渲染 AI 助手的回复消息，包括：
 * - Markdown 文本
 * - 工具调用展示
 * - 确认卡片 (ConfirmationCard)
 * - Todo 列表卡片 (TodoListCard)
 */
import { parsePartialJson } from "@langchain/core/output_parsers";
import { useStreamContext } from "@/providers/Stream";
import { AIMessage, Checkpoint, Message, ToolMessage } from "@langchain/langgraph-sdk";
import { getContentString, replaceImagePlaceholders } from "../utils";
import { BranchSwitcher, CommandBar } from "./shared";
import { MarkdownText } from "../markdown-text";
import { cn } from "@/lib/utils";
import { ToolCalls, ToolResult } from "./tool-calls";
import { MessageContentComplex } from "@langchain/core/messages";
import { useQueryState, parseAsBoolean } from "nuqs";
import ConfirmationCard from "@/components/todo/ConfirmationCard";
import TodoListCard from "@/components/todo/TodoListCard";
import { Todo } from "@/types/todo";
import { SqlResultTable } from "@/components/chat/messages/sql-result-table";
import { SqlResultChart } from "@/components/chat/messages/sql-result-chart";
import type { SqlResultChartData } from "@/types/message";

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
  const threadInterrupt = thread.interrupt;
  const kbImages = thread.kbImages;

  // 应用图片占位符替换
  const displayContent = replaceImagePlaceholders(contentString, kbImages);

  const parentCheckpoint = meta?.firstSeenState?.parent_checkpoint;
  const anthropicStreamedToolCalls = Array.isArray(content)
    ? parseAnthropicStreamedToolCalls(content)
    : undefined;

  const hasToolCalls =
    message &&
    "tool_calls" in message &&
    message.tool_calls &&
    message.tool_calls.length > 0;
  const hasAnthropicToolCalls = !!anthropicStreamedToolCalls?.length;
  const isToolResult = message?.type === "tool";

  // 检查确认请求
  const aiMessage = message as AIMessage | undefined;
  const additionalKwargs = aiMessage?.additional_kwargs;
  const requiresConfirmation = additionalKwargs?.requires_confirmation;
  const operation = additionalKwargs?.operation;

  // 检查数据类型
  const dataType = additionalKwargs?.data_type;
  const responseData = additionalKwargs?.data as Record<string, any> | undefined;

  // 获取 todos 数据
  const todoData = responseData?.todos as Todo[] | undefined;

  // 获取 SQL 查询结果数据
  const sqlResultData = dataType === "sql_result" ? responseData : undefined;
  const sqlChartData = sqlResultData?.chart as SqlResultChartData | undefined;

  // 确认操作处理
  const handleConfirm = async (data?: Record<string, any>) => {
    if (threadInterrupt) {
      await (thread as any).resume(data || { confirmed: true });
    } else {
      console.warn("未检测到中断状态，但触发了确认");
    }
  };

  const handleCancel = async () => {
    console.log("用户取消操作");
  };

  const handleAction = (command: string) => {
    thread.submit({ messages: command });
  };

  // 如果是工具结果消息，渲染 ToolResult 组件
  if (isToolResult) {
    if (hideToolCalls) {
      return null;
    }
    return (
      <div className="group mr-auto flex w-full items-start gap-2" data-testid="tool-result">
        <div className="flex w-full flex-col gap-2">
          <ToolResult message={message as ToolMessage} />
        </div>
      </div>
    );
  }

  // 获取当前处理状态
  const currentStatus = thread.currentStatus;
  const statusMessage = currentStatus?.message?.trim() ?? "";
  const shouldAnimateStatus = currentStatus?.phase !== "done";

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {/* 显示当前处理状态 */}
        {statusMessage && (
          <div
            className={cn(
              "flex items-center gap-2 text-xs text-gray-500",
              shouldAnimateStatus && "animate-pulse",
            )}
          >
            <span
              className={cn(
                "inline-block h-1.5 w-1.5 rounded-full bg-blue-500",
                shouldAnimateStatus && "animate-ping",
              )}
            />
            {statusMessage}
          </div>
        )}
        {/* 流式输出中也显示工具调用 */}
        {hasToolCalls && <ToolCalls toolCalls={message.tool_calls} isComplete={!isLoading} />}
        <MarkdownText className="markdown-content-readable">
          {displayContent}
        </MarkdownText>
      </div>
    )
  }

  return (
    <div className="group mr-auto flex w-full items-start gap-2" data-testid="ai-message">
      <div className="flex w-full flex-col gap-2">
        {/* 移除旧版确认卡片，统一使用底部的 Human-in-the-loop 组件 */}
        {dataType === "todo_list" && todoData && todoData.length > 0 ? (
          <TodoListCard
            todos={todoData}
            onAction={handleAction}
            readonly={false}
            fetchLatest={isLatestMessage}
            onSelectionChange={(todoId, todo) => {
              if (typeof window !== 'undefined') {
                const currentThreadId = new URL(window.location.href).searchParams.get('threadId');
                if (todoId && todo) {
                  sessionStorage.setItem('selectedTodo', JSON.stringify({
                    id: todoId,
                    title: todo.title,
                    threadId: currentThreadId
                  }));
                  window.dispatchEvent(new Event('todoSelected'));
                } else {
                  sessionStorage.removeItem('selectedTodo');
                  window.dispatchEvent(new Event('todoDeselected'));
                }
              }
            }}
            onRefresh={() => {
              handleAction('查看待办');
            }}
          />
        ) : (
          <>
            {displayContent.length > 0 && (
              <div className="py-1">
                <MarkdownText className="markdown-content-readable">{displayContent}</MarkdownText>
              </div>
            )}

            {sqlResultData && (
              <>
                {sqlChartData && <SqlResultChart chart={sqlChartData} />}
                <SqlResultTable
                  columns={sqlResultData.columns as string[]}
                  columnDisplayNames={sqlResultData.column_display_names as string[] | undefined}
                  rows={sqlResultData.rows as Record<string, any>[]}
                  totalRows={sqlResultData.total_rows}
                  sql={(sqlResultData.display_sql as string) || (sqlResultData.sql as string)}
                  permissionScopeApplied={Boolean(sqlResultData.permission_scope_applied)}
                  permissionScopeText={
                    (sqlResultData.permission_scope_summary as { display_text?: string } | undefined)?.display_text
                  }
                />
              </>
            )}

            {!hideToolCalls && (
              <>
                {hasToolCalls && <ToolCalls toolCalls={message.tool_calls} isComplete={!isLoading} />}
                {!hasToolCalls && hasAnthropicToolCalls && (
                  <ToolCalls toolCalls={anthropicStreamedToolCalls} isComplete={!isLoading} />
                )}
              </>
            )}

            {/* 仅当消息包含实际文本内容时显示操作栏（过滤纯工具调用的中间步骤） */}
            {contentString.trim().length > 0 && (
              <div
                className={cn(
                  "mr-auto flex items-center gap-2 transition-opacity",
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
          </>
        )}
      </div>
    </div>
  );
}

export function AssistantMessageLoading() {
  return (
    <div className="mr-auto flex items-start gap-2">
      <div className="bg-muted flex h-8 items-center gap-1 rounded-2xl px-4 py-2">
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_infinite] rounded-full"></div>
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_0.5s_infinite] rounded-full"></div>
        <div className="bg-foreground/50 h-1.5 w-1.5 animate-[pulse_1.5s_ease-in-out_1s_infinite] rounded-full"></div>
      </div>
    </div>
  );
}
