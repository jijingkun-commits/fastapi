import { AIMessage, ToolMessage } from "@langchain/langgraph-sdk";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";
import { MarkdownText } from "../markdown-text";

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

  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="flex flex-col gap-1">
      {toolCalls.map((tc, idx) => {
        const args = tc.args as Record<string, any>;
        const hasArgs = Object.keys(args).length > 0;
        const isExpanded = expanded[idx] ?? false;

        return (
          <div
            key={idx}
            className="overflow-hidden rounded border border-gray-200 text-xs"
          >
            <div
              className="flex cursor-pointer items-center justify-between bg-gray-50 px-2 py-1 hover:bg-gray-100"
              onClick={() => setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }))}
            >
              <span className="flex items-center gap-1.5">
                {/* 根据完成状态显示不同的指示器 */}
                {isComplete ? (
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-500"></span>
                ) : (
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500"></span>
                )}
                <span className="font-medium text-gray-700">{tc.name}</span>
              </span>
              {/* 始终显示箭头，提示用户可以点击查看详情 */}
              <span className="text-gray-400">
                {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </span>
            </div>
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="overflow-hidden"
                >
                  <div className="border-t border-gray-100 bg-gray-50/50 px-2 py-1">
                    {hasArgs ? (
                      Object.entries(args).map(([key, value], argIdx) => (
                        <div key={argIdx} className="flex gap-2 py-0.5">
                          <span className="font-medium text-gray-600">{key}:</span>
                          <span className="text-gray-500 break-all">
                            {isComplexValue(value) ? JSON.stringify(value) : String(value)}
                          </span>
                        </div>
                      ))
                    ) : (
                      <span className="text-gray-400 italic">无参数</span>
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
  const displayedContent = shouldTruncate && !isExpanded
    ? contentStr.slice(0, 150) + "..."
    : contentStr;

  return (
    <div className="overflow-hidden rounded border border-green-200 text-xs">
      <div
        className="flex cursor-pointer items-center justify-between bg-green-50 px-2 py-1 hover:bg-green-100"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-500"></span>
          <span className="font-medium text-green-700">
            {message.name || "结果"}
          </span>
        </span>
        <span className="text-gray-400">
          {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </span>
      </div>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="border-t border-green-100 bg-green-50/50 px-2 py-1 max-h-60 overflow-auto">
              {isJsonContent ? (
                <pre className="text-gray-600 whitespace-pre-wrap break-all">
                  {displayedContent}
                </pre>
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
