import { AIMessage, ToolMessage } from "@langchain/langgraph-sdk";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";
import { MarkdownText } from "../markdown-text";

const ORCHESTRATION_TOOL_NAMES = new Set([
  "assign_to_data_expert",
  "assign_to_todo_expert",
  "decompose_goals",
  "load_skills",
]);

export function isUserVisibleToolName(name?: string | null): boolean {
  const normalized = String(name ?? "").trim();
  if (normalized.length === 0) return false;
  return !ORCHESTRATION_TOOL_NAMES.has(normalized);
}

function isComplexValue(value: any): boolean {
  return Array.isArray(value) || (typeof value === "object" && value !== null);
}

export function ToolCalls({
  toolCalls,
  isComplete = false,
}: {
  toolCalls: AIMessage["tool_calls"];
  isComplete?: boolean;
}) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  const visibleToolCalls = (toolCalls ?? []).filter((tc) =>
    isUserVisibleToolName(tc.name),
  );
  if (visibleToolCalls.length === 0) return null;

  return (
    <div className="chat-tool-call-list">
      {visibleToolCalls.map((tc, idx) => {
        const args = tc.args as Record<string, any>;
        const hasArgs = Object.keys(args).length > 0;
        const isExpanded = expanded[idx] ?? false;

        return (
          <div
            key={idx}
            className="chat-tool-call-card"
          >
            <button
              type="button"
              className="chat-tool-call-toggle"
              aria-expanded={isExpanded}
              onClick={() =>
                setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }))
              }
            >
              <span className="flex min-w-0 items-center gap-2">
                {/* 根据完成状态显示不同的指示器 */}
                {isComplete ? (
                  <span
                    data-state="done"
                    className="chat-tool-call-indicator"
                  ></span>
                ) : (
                  <span
                    data-state="running"
                    className="chat-tool-call-indicator"
                  ></span>
                )}
                <span className="chat-tool-call-label truncate">{tc.name}</span>
              </span>
              {/* 始终显示箭头，提示用户可以点击查看详情 */}
              <span className="chat-tool-call-chevron">
                {isExpanded ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </span>
            </button>
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="overflow-hidden"
                >
                  <div className="chat-tool-call-body">
                    {hasArgs ? (
                      Object.entries(args).map(([key, value], argIdx) => (
                        <div
                          key={argIdx}
                          className="chat-tool-call-kv"
                        >
                          <span className="chat-tool-call-key">{key}:</span>
                          <span className="chat-tool-call-value break-all">
                            {isComplexValue(value)
                              ? JSON.stringify(value)
                              : String(value)}
                          </span>
                        </div>
                      ))
                    ) : (
                      <span className="chat-tool-call-empty">无参数</span>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}

export function ToolResult({ message }: { message: ToolMessage }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!isUserVisibleToolName(message.name)) {
    return null;
  }

  let parsedContent: any;
  let isJsonContent = false;

  try {
    if (typeof message.content === "string") {
      parsedContent = JSON.parse(message.content);
      isJsonContent = isComplexValue(parsedContent);
    }
  } catch {
    // Content is not JSON, use as is
    parsedContent = message.content;
  }

  const contentStr = isJsonContent
    ? JSON.stringify(parsedContent, null, 2)
    : String(message.content);
  const shouldTruncate = contentStr.length > 200;
  const displayedContent =
    shouldTruncate && !isExpanded
      ? contentStr.slice(0, 150) + "..."
      : contentStr;

  return (
    <div
      className="chat-tool-call-card"
      data-variant="result"
    >
      <button
        type="button"
        className="chat-tool-call-toggle"
        aria-expanded={isExpanded}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="flex min-w-0 items-center gap-2">
          <span
            data-state="done"
            className="chat-tool-call-indicator"
          ></span>
          <span className="chat-tool-call-label">{message.name || "结果"}</span>
        </span>
        <span className="chat-tool-call-chevron">
          {isExpanded ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </span>
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="chat-tool-call-body chat-tool-call-scroll">
              {isJsonContent ? (
                <pre className="chat-tool-call-pre">{displayedContent}</pre>
              ) : (
                <MarkdownText>{displayedContent}</MarkdownText>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
