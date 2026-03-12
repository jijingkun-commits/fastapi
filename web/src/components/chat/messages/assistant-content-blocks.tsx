import { MarkdownText } from "../markdown-text";
import TodoListCard from "@/components/todo/TodoListCard";
import { SqlResultChart } from "@/components/chat/messages/sql-result-chart";
import { SqlResultTable } from "@/components/chat/messages/sql-result-table";
import type { ContentBlock, SqlResultChartData } from "@/types/message";
import type { Todo } from "@/types/todo";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getMarkdownBlockText(block: ContentBlock): string {
  if (block.type !== "markdown" && block.type !== "text") {
    return "";
  }
  if (typeof block.data === "string") {
    return block.data;
  }
  if (isRecord(block.data) && typeof block.data.text === "string") {
    return block.data.text;
  }
  return "";
}

function getSqlChartFromBlock(block: ContentBlock): SqlResultChartData | undefined {
  if (block.type !== "sql_result" || !isRecord(block.data) || !isRecord(block.data.chart)) {
    return undefined;
  }

  const chart = block.data.chart;
  if (
    (chart.type !== "bar" && chart.type !== "line" && chart.type !== "pie")
    || typeof chart.x_key !== "string"
    || typeof chart.y_key !== "string"
    || !Array.isArray(chart.data)
  ) {
    return undefined;
  }

  return chart as unknown as SqlResultChartData;
}

function buildFallbackPreview(data: unknown): string {
  if (isRecord(data) && typeof data.preview === "string") {
    return data.preview;
  }
  try {
    const serialized = JSON.stringify(data);
    if (!serialized) {
      return "{}";
    }
    return serialized.length > 240 ? `${serialized.slice(0, 240)}...` : serialized;
  } catch {
    return String(data ?? "");
  }
}

export function AssistantContentBlocks({
  blocks,
  isLatestMessage,
  onAction,
  onTodoSelectionChange,
}: {
  blocks: ContentBlock[];
  isLatestMessage: boolean;
  onAction: (command: string) => void;
  onTodoSelectionChange: (todoId: string | number | null, todo?: Todo) => void;
}) {
  return (
    <>
      {blocks.map((block, index) => {
        if (block.type === "markdown" || block.type === "text") {
          const text = getMarkdownBlockText(block);
          if (!text.trim()) {
            return null;
          }
          return (
            <div className="py-1" key={`markdown-${index}`}>
              <MarkdownText className="markdown-content-readable">{text}</MarkdownText>
            </div>
          );
        }

        if (block.type === "image") {
          const data = isRecord(block.data) ? block.data : {};
          const url = typeof data.url === "string" ? data.url.trim() : "";
          if (!url) {
            return null;
          }
          const alt = typeof data.alt === "string" && data.alt.trim() ? data.alt : "生成图片";
          return (
            <div className="py-1" key={`image-${index}`}>
              <MarkdownText>{`![${alt}](${url})`}</MarkdownText>
            </div>
          );
        }

        if (block.type === "sql_result" && isRecord(block.data)) {
          const chart = getSqlChartFromBlock(block);
          const rows = Array.isArray(block.data.rows) ? (block.data.rows as Record<string, unknown>[]) : [];
          const columns = Array.isArray(block.data.columns) ? (block.data.columns as string[]) : [];
          return (
            <div key={`sql-${index}`}>
              {chart && <SqlResultChart chart={chart as SqlResultChartData} />}
              <SqlResultTable
                columns={columns}
                columnDisplayNames={
                  Array.isArray(block.data.column_display_names)
                    ? (block.data.column_display_names as string[])
                    : undefined
                }
                rows={rows}
                totalRows={typeof block.data.total_rows === "number" ? block.data.total_rows : undefined}
                sql={
                  (typeof block.data.display_sql === "string" ? block.data.display_sql : undefined)
                  ?? (typeof block.data.sql === "string" ? block.data.sql : undefined)
                }
                permissionScopeApplied={Boolean(block.data.permission_scope_applied)}
                permissionScopeText={
                  isRecord(block.data.permission_scope_summary)
                    ? (typeof block.data.permission_scope_summary.display_text === "string"
                      ? block.data.permission_scope_summary.display_text
                      : undefined)
                    : undefined
                }
              />
            </div>
          );
        }

        if (block.type === "todo_list" && isRecord(block.data)) {
          const todos = Array.isArray(block.data.todos) ? (block.data.todos as Todo[]) : [];
          if (todos.length === 0) {
            return null;
          }
          return (
            <TodoListCard
              key={`todo-${index}`}
              todos={todos}
              onAction={onAction}
              readonly={false}
              fetchLatest={isLatestMessage}
              onSelectionChange={(todoId, todo) => onTodoSelectionChange(todoId ?? null, todo as Todo | undefined)}
              onRefresh={() => onAction("查看待办")}
            />
          );
        }

        if (block.type === "fallback_result") {
          const data = isRecord(block.data) ? block.data : {};
          const dataType = typeof data.data_type === "string" ? data.data_type : "unknown";
          return (
            <div
              key={`fallback-${index}`}
              className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900"
              data-testid="result-fallback-card"
            >
              <div className="font-medium">未注册结构化结果类型：{dataType}</div>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded bg-amber-100 p-2 text-[11px]">
                {buildFallbackPreview(block.data)}
              </pre>
            </div>
          );
        }

        return null;
      })}
    </>
  );
}
