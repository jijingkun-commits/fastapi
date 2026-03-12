/**
 * AI 消息组件（中文注释）
 *
 * 渲染 AI 助手的回复消息，包括：
 * - canonical content blocks（主路径）
 * - 纯 Markdown 文本（兼容路径）
 * - 工具调用展示
 */
import { parsePartialJson } from "@langchain/core/output_parsers";
import { useStreamContext } from "@/providers/Stream";
import { AIMessage, Checkpoint, Message, ToolMessage } from "@langchain/langgraph-sdk";
import { getContentString } from "../utils";
import { BranchSwitcher, CommandBar } from "./shared";
import { MarkdownText } from "../markdown-text";
import { cn } from "@/lib/utils";
import { ToolCalls, ToolResult, isUserVisibleToolName } from "./tool-calls";
import { MessageContentComplex } from "@langchain/core/messages";
import { useQueryState, parseAsBoolean } from "nuqs";
import { AssistantContentBlocks } from "./assistant-content-blocks";
import { isContentBlockArray } from "@/types/message";
import type { Todo } from "@/types/todo";

function parseAnthropicStreamedToolCalls(
  content: MessageContentComplex[],
): AIMessage["tool_calls"] {
  const toolCallContents = content.filter((c) => c.type === "tool_use" && c.id);

  return toolCallContents.map((tc) => {
    const toolCall = tc as Record<string, unknown>;
    let json: Record<string, unknown> = {};
    if (typeof toolCall.input === "string" && toolCall.input) {
      try {
        json = parsePartialJson(toolCall.input) ?? {};
      } catch {
        // noop
      }
    }
    return {
      name: typeof toolCall.name === "string" ? toolCall.name : "",
      id: typeof toolCall.id === "string" ? toolCall.id : "",
      args: json,
      type: "tool_call" as const,
    };
  });
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

  const aiMessage = message as AIMessage | undefined;
  const hasCanonicalBlocks = Array.isArray(content) && isContentBlockArray(content);

  const parentCheckpoint = meta?.firstSeenState?.parent_checkpoint;
  const anthropicStreamedToolCalls = Array.isArray(content)
    ? parseAnthropicStreamedToolCalls(content)
    : undefined;

  const hasToolCalls = Boolean(
    message
    && "tool_calls" in message
    && message.tool_calls
    && message.tool_calls.length > 0,
  );
  const hasAnthropicToolCalls = Boolean(anthropicStreamedToolCalls?.length);
  const isToolResult = message?.type === "tool";

  const handleAction = (command: string) => {
    thread.submit({ messages: command });
  };

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

  const body = hasCanonicalBlocks ? (
    <AssistantContentBlocks
      blocks={content}
      isLatestMessage={isLatestMessage}
      onAction={handleAction}
      onTodoSelectionChange={(todoId, todo) => {
        syncSelectedTodoSelection(todoId, todo);
      }}
    />
  ) : (
    contentString.trim().length > 0 ? (
      <div className="py-1">
        <MarkdownText className="markdown-content-readable">{contentString}</MarkdownText>
      </div>
    ) : null
  );

  if (isLoading) {
    return (
      <div className="chat-content-shell mx-auto flex flex-col gap-2">
        {body}
        {hasToolCalls && aiMessage?.tool_calls && <ToolCalls toolCalls={aiMessage.tool_calls} isComplete={!isLoading} />}
      </div>
    );
  }

  return (
    <div className="group mr-auto flex w-full items-start gap-2" data-testid="ai-message">
      <div className="chat-content-shell mx-auto flex w-full flex-col gap-2">
        {body}

        {!hideToolCalls && (
          <>
            {hasToolCalls && aiMessage?.tool_calls && <ToolCalls toolCalls={aiMessage.tool_calls} isComplete={!isLoading} />}
            {!hasToolCalls && hasAnthropicToolCalls && (
              <ToolCalls toolCalls={anthropicStreamedToolCalls} isComplete={!isLoading} />
            )}
          </>
        )}

        {contentString.trim().length > 0 && (
          <div
            className={cn(
              "chat-message-toolbar flex w-fit items-center gap-1.5 transition-all duration-200",
              "translate-y-1 opacity-0 group-focus-within:translate-y-0 group-focus-within:opacity-100 group-hover:translate-y-0 group-hover:opacity-100",
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
              feedbackScore={(message as { feedback_score?: number }).feedback_score}
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
