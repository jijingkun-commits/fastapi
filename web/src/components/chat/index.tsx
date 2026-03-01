import { v4 as uuidv4 } from "uuid";
import { ReactNode, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useStreamContext } from "@/providers/Stream";
import { useState, FormEvent } from "react";
import { Button } from "../ui/button";
import { Checkpoint, Message } from "@langchain/langgraph-sdk";
import { AssistantMessage, AssistantMessageLoading } from "./messages/ai";
import { HumanMessage } from "./messages/human";
// 内联常量：ID 以此前缀开头的消息不会被渲染
const DO_NOT_RENDER_ID_PREFIX = "do-not-render-";
import { LangGraphLogoSVG } from "../icons/langgraph";
import { TooltipIconButton } from "./tooltip-icon-button";
import {
  ArrowDown,
  XIcon,
} from "lucide-react";
import { useQueryState, parseAsBoolean } from "nuqs";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import ThreadHistory from "./history";
import { toast } from "sonner";
import { useMediaQuery } from "@/hooks/useMediaQuery";

import { GitHubSVG } from "../icons/github";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";
import { useFileUpload } from "@/hooks/use-file-upload";
import { ContentBlocksPreview } from "./ContentBlocksPreview";
import {
  useArtifactOpen,
  ArtifactContent,
  ArtifactTitle,
  useArtifactContext,
} from "./artifact";
import { CompactApproval } from "./CompactApproval";
import { ChatHeader } from "./ChatHeader";
import { ChatInput } from "./ChatInput";
import { useModels } from "@/lib/model-config";

function StickyToBottomContent(props: {
  content: ReactNode;
  footer?: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  const context = useStickToBottomContext();
  return (
    <div
      ref={context.scrollRef}
      style={{ width: "100%", height: "100%" }}
      className={props.className}
    >
      <div
        ref={context.contentRef}
        className={props.contentClassName}
      >
        {props.content}
      </div>

      {props.footer}
    </div>
  );
}

function ScrollToBottom(props: { className?: string }) {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();

  if (isAtBottom) return null;
  return (
    <Button
      variant="outline"
      className={props.className}
      onClick={() => scrollToBottom()}
    >
      <ArrowDown className="h-4 w-4" />
      <span>Scroll to bottom</span>
    </Button>
  );
}

function OpenGitHubRepo() {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <a
            href="https://github.com/langchain-ai/agent-chat-ui"
            target="_blank"
            className="flex items-center justify-center"
          >
            <GitHubSVG
              width="24"
              height="24"
            />
          </a>
        </TooltipTrigger>
        <TooltipContent side="left">
          <p>Open GitHub repo</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function Thread() {
  const [artifactContext, setArtifactContext] = useArtifactContext();
  const [artifactOpen, closeArtifact] = useArtifactOpen();

  const [threadId, _setThreadId] = useQueryState("threadId");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(false),
  );

  const [input, setInput] = useState("");
  // 兜底引用：用于获取 textarea 的真实 DOM 值。
  // 在自动化测试或脚本直接修改 textarea.value 时，React 的 onChange 可能不会触发，
  // 导致 input state 为空。此时我们需要直接读取 ref.current.value 来确保消息能被正确提交。
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    contentBlocks,
    setContentBlocks,
    handleFileUpload,
    dropRef,
    removeBlock,
    resetBlocks: _resetBlocks,
    dragOver,
    handlePaste,
  } = useFileUpload();
  const [firstTokenReceived, setFirstTokenReceived] = useState(false);
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");

  // 加载动态模型列表
  const { models, loading: modelsLoading } = useModels();

  const stream = useStreamContext();
  const messages = stream.messages;
  const isLoading = stream.isLoading;
  // 从 Context 获取所有持久化状态
  const { selectedModel, handleModelChange, thinkingCapability } = stream as any;

  const lastError = useRef<string | undefined>(undefined);



  const setThreadId = (id: string | null) => {
    _setThreadId(id);

    // close artifact and reset artifact context
    closeArtifact();
    setArtifactContext({});
  };

  useEffect(() => {
    if (!stream.error) {
      lastError.current = undefined;
      return;
    }
    try {
      const message = (stream.error as any).message;
      if (!message || lastError.current === message) {
        // Message has already been logged. do not modify ref, return early.
        return;
      }

      // Message is defined, and it has not been logged yet. Save it, and send the error
      lastError.current = message;
      toast.error("An error occurred. Please try again.", {
        description: (
          <p>
            <strong>Error:</strong> <code>{message}</code>
          </p>
        ),
        richColors: true,
        closeButton: true,
      });
    } catch {
      // no-op
    }
  }, [stream.error]);

  // 页面级首 Token 动画状态与组件渲染时序强耦合，暂保留在组件层维护。
  const prevMessageLength = useRef(0);
  useEffect(() => {
    if (
      messages.length !== prevMessageLength.current &&
      messages?.length &&
      messages[messages.length - 1].type === "ai"
    ) {
      setFirstTokenReceived(true);
    }

    prevMessageLength.current = messages.length;
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    // 兜底逻辑：优先使用 input state，如果为空则尝试读取 textarea 真实 DOM 值。
    // 这解决了脚本直接设置 value 时（不触发 React 事件），input state 不同步导致无法提交的问题。
    const actualInput = input.trim() || textareaRef.current?.value?.trim() || '';

    if ((actualInput.length === 0 && contentBlocks.length === 0) || isLoading)
      return;
    setFirstTokenReceived(false);

    // 上传所有附件
    let attachments: any[] = [];
    if (contentBlocks.length > 0) {
      try {
        const { uploadFile } = await import("@/lib/backend");
        const uploadPromises = contentBlocks.map(async (block: any) => {
          // multimodal-utils 中保存的是 block.file，不是 block.data
          const file = block.file;
          if (file instanceof File) {
            const result = await uploadFile(file, threadId ?? undefined);
            // 构造符合 Attachment 接口的数据
            return {
              name: result.file_name,
              url: result.url,
              mime_type: result.content_type,
              size: result.size,
              object_key: result.object_key
            };
          }
          return null;
        });
        const results = await Promise.all(uploadPromises);
        attachments = results.filter(r => r !== null);
      } catch (err) {
        console.error("附件上传失败:", err);
        toast.error("附件上传失败，请重试");
        return;
      }
    }

    const newHumanMessage: Message = {
      id: uuidv4(),
      type: "human",
      content: [
        ...(actualInput.length > 0 ? [{ type: "text", text: actualInput }] : []),
        ...contentBlocks,
      ] as Message["content"],
    };

    // 工具消息响应现在由后端处理，前端无需补充
    const toolMessages: Message[] = [];

    const context =
      Object.keys(artifactContext).length > 0 ? artifactContext : undefined;

    stream.submit(
      { messages: [...toolMessages, newHumanMessage], context, attachments },
      {
        streamMode: ["values"],
        streamSubgraphs: true,
        streamResumable: true,
        optimisticValues: (prev: Record<string, unknown>) => ({
          ...prev,
          context,
          messages: [
            ...((prev.messages as unknown[]) ?? []),
            ...toolMessages,
            newHumanMessage,
          ],
        }),
      },
    );

    setInput("");
    setContentBlocks([]);
  };

  const handleRegenerate = (
    parentCheckpoint: Checkpoint | null | undefined,
  ) => {
    // Do this so the loading state is correct
    prevMessageLength.current = prevMessageLength.current - 1;
    setFirstTokenReceived(false);
    stream.submit(undefined, {
      checkpoint: parentCheckpoint,
      streamMode: ["values"],
      streamSubgraphs: true,
      streamResumable: true,
    });
  };

  const chatStarted = !!threadId || !!messages.length;
  const hasNoAIOrToolMessages = !messages.find(
    (m) => m.type === "ai" || m.type === "tool",
  );

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden">
      <div className="relative hidden lg:flex">
        <motion.div
          className="absolute z-20 h-full overflow-hidden border-r bg-white"
          style={{ width: 300 }}
          animate={
            isLargeScreen
              ? { x: chatHistoryOpen ? 0 : -300 }
              : { x: chatHistoryOpen ? 0 : -300 }
          }
          initial={{ x: -300 }}
          transition={
            isLargeScreen
              ? { type: "spring", stiffness: 300, damping: 30 }
              : { duration: 0 }
          }
        >
          <div
            className="relative h-full"
            style={{ width: 300 }}
          >
            <ThreadHistory />
          </div>
        </motion.div>
      </div>

      <div
        className={cn(
          "grid w-full grid-cols-[1fr_0fr] transition-all duration-500",
          artifactOpen && "grid-cols-[3fr_2fr]",
        )}
      >
        <motion.div
          className={cn(
            "relative flex min-w-0 flex-1 flex-col overflow-hidden",
            !chatStarted && "grid-rows-[1fr]",
          )}
          layout={isLargeScreen}
          animate={{
            marginLeft: chatHistoryOpen ? (isLargeScreen ? 300 : 0) : 0,
            width: chatHistoryOpen
              ? isLargeScreen
                ? "calc(100% - 300px)"
                : "100%"
              : "100%",
          }}
          transition={
            isLargeScreen
              ? { type: "spring", stiffness: 300, damping: 30 }
              : { duration: 0 }
          }
        >
          {/* 统一使用 ChatHeader 组件 */}
          <ChatHeader
            chatHistoryOpen={chatHistoryOpen ?? false}
            onToggleChatHistory={() => setChatHistoryOpen((p) => !p)}
            onNewThread={() => setThreadId(null)}
            isLargeScreen={isLargeScreen}
            selectedModel={selectedModel}
            onModelChange={handleModelChange}
            models={models}
            modelsLoading={modelsLoading}
            chatStarted={chatStarted}
          />

          <StickToBottom className="relative flex-1 overflow-hidden">
            <StickyToBottomContent
              className={cn(
                "absolute inset-0 overflow-y-scroll px-4 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent",
                !chatStarted && "flex flex-col items-center justify-center", // Center content when chat hasn't started
              )}
              contentClassName={cn(
                "py-8 max-w-4xl mx-auto flex flex-col gap-4 w-full transition-all duration-300",
                !chatStarted ? "items-center justify-center min-h-[50vh]" : ""
              )}
              content={
                <>
                  {!chatStarted && (
                    <div className="flex flex-col items-center gap-4 mb-4 text-center">
                      <div className="flex items-center gap-3">
                        <img
                          src="/logo.png"
                          alt="Logo"
                          className="h-12 w-12 object-contain"
                          onError={(e) => {
                            // Fallback to favicon if logo.png is not found
                            e.currentTarget.src = "/favicon.ico";
                          }}
                        />
                      </div>
                      <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-br from-gray-900 to-gray-600 bg-clip-text text-transparent">
                        嘉银助手
                      </h1>
                      <p className="text-muted-foreground max-w-md">
                        已有：知识库、联网搜索、数据查询、简单的图形（图表）生成
                        能上传文件、展示图片。
                      </p>
                    </div>
                  )}

                  {messages
                    .filter((m) => !m.id?.startsWith(DO_NOT_RENDER_ID_PREFIX))
                    .map((message, index, filteredMessages) => {
                      const isLast = index === filteredMessages.length - 1;
                      return message.type === "human" ? (
                        <HumanMessage
                          key={`${message.id ?? message.type}-${index}`}
                          message={message}
                          isLoading={isLoading && isLast}
                        />
                      ) : (
                        <AssistantMessage
                          key={`${message.id ?? message.type}-${index}`}
                          message={message}
                          isLoading={isLoading && isLast}
                          isLatestMessage={isLast}
                          handleRegenerate={handleRegenerate}
                        />
                      );
                    })}
                  {/* Special rendering case where there are no AI/tool messages, but there is an interrupt.
                    We need to render it outside of the messages list, since there are no messages to render */}
                  {hasNoAIOrToolMessages && !!stream.interrupt && (
                    <AssistantMessage
                      key="interrupt-msg"
                      message={undefined}
                      isLoading={isLoading}
                      handleRegenerate={handleRegenerate}
                    />
                  )}
                  {isLoading && !firstTokenReceived && (
                    <AssistantMessageLoading />
                  )}
                </>
              }
            />
            <ScrollToBottom className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 shadow-md rounded-full bg-white/90 hover:bg-white" />
          </StickToBottom>

          <footer className="w-full bg-white/80 backdrop-blur-md sticky bottom-0 z-10 transition-all duration-300 pb-[env(safe-area-inset-bottom)]">
            <div className="relative mx-auto max-w-4xl w-full">
              <ChatInput
                input={input}
                setInput={setInput}
                textareaRef={textareaRef}
                onSubmit={handleSubmit}
                contentBlocks={contentBlocks}
                onRemoveBlock={removeBlock}
                onFileUpload={handleFileUpload}
                onPaste={handlePaste}
                dropRef={dropRef}
                dragOver={dragOver}
              />
            </div>
          </footer>
        </motion.div>
        <div className="relative flex flex-col border-l">
          <div className="absolute inset-0 flex min-w-[30vw] flex-col">
            <div className="grid grid-cols-[1fr_auto] border-b p-4">
              <ArtifactTitle className="truncate overflow-hidden" />
              <button
                onClick={closeArtifact}
                className="cursor-pointer"
              >
                <XIcon className="size-5" />
              </button>
            </div>
            <ArtifactContent className="relative flex-grow" />
          </div>
        </div>
      </div>
    </div>
  );
}
