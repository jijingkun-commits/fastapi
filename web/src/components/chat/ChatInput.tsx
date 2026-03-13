/**
 * 聊天输入框组件（中文注释）
 *
 * 包含：
 * - 快捷提示词选择
 * - 人工审核组件
 * - 文件上传预览
 * - 文本输入框
 * - 开关控件（隐藏工具调用、深度思考）
 * - 发送/取消按钮
 *
 * 从 index.tsx 拆分出来。
 */

import { FormEvent, RefObject, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, LoaderCircle, Mic, ArrowUp, Zap } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn, safeParseJson, SelectedTodoSchema } from "@/lib/utils";
import { CompactApproval } from "./CompactApproval";
import { ContentBlocksPreview } from "./ContentBlocksPreview";
import { ContentBlock } from "@langchain/core/messages";
import { isThinkingToggleable } from "@/lib/model-config";
import { toast } from "sonner";
import { useStreamContext } from "@/providers/StreamContext";
import { useQueryState } from "nuqs";

/** 快捷提示词配置 */
const QUICK_PROMPTS = [
  { label: "贷款余额(测试)", value: "查询2025年6月30日的贷款余额" },
  { label: "前10大户", value: "查询2025年6月30日贷款余额前10名的客户" },
  { label: "机构分布", value: "查询2025年6月30日各机构的贷款余额分布" },
  { label: "贷款余额", value: "查询本月贷款余额总额" },
  { label: "存款总额", value: "查询本月存款总额" },
  { label: "不良贷款", value: "查询本月不良贷款余额总额" },
  { label: "分行存款", value: "查询本月各分行存款余额" },
  { label: "t2sql", value: "查询我数据库中一共有几张表" },
  { label: "天气", value: "查询嘉兴近一周的天气" },
  { label: "画图", value: "使用fig_inter工具，生成一个圆形，以图片方式展示。" },
  {
    label: "知识库",
    value: "查询知识库，用户已注销无法使用该功能的问题要怎么解决？",
  },
  { label: "待办查询", value: "查询我的待办列表" },
  { label: "新渠道功能", value: "查询知识库，新渠道有哪些功能" },
  { label: "创建待办", value: "明天上午9点去陆家嘴和张三开会" },
];

export interface ChatInputProps {
  /** 输入框内容 */
  input: string;
  /** 设置输入框内容 */
  setInput: (value: string) => void;
  /** 输入框 ref */
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  /** 表单提交处理 */
  onSubmit: (e: FormEvent) => void;

  // Removed props that are now accessed via Context
  // - isLoading
  // - onStop
  // - enableThinking
  // - setEnableThinking
  // - thinkingCapability
  // 注意：useMultiAgent 已废弃（2026-01-31），系统默认使用多智能体模式

  /** 文件上传内容块 */
  contentBlocks: ContentBlock.Multimodal.Data[];
  /** 移除内容块（按索引） */
  onRemoveBlock: (idx: number) => void;
  /** 文件上传处理 */
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** 粘贴处理 */
  onPaste: (
    e: React.ClipboardEvent<HTMLTextAreaElement | HTMLInputElement>,
  ) => void;
  /** 拖放区域 ref */
  dropRef: RefObject<HTMLDivElement | null>;
  /** 是否正在拖放 */
  dragOver: boolean;
}

/**
 * 聊天输入框组件
 */
export function ChatInput({
  input,
  setInput,
  textareaRef,
  onSubmit,
  contentBlocks,
  onRemoveBlock,
  onFileUpload,
  onPaste,
  dropRef,
  dragOver,
}: ChatInputProps) {
  const stream = useStreamContext();

  // Destructure from context
  const {
    isLoading,
    stop: onStop,
    enableThinking,
    setEnableThinking,
  } = stream as any; // Cast to any because some props might be added by SSE/custom provider

  const thinkingCapability = (stream as any).thinkingCapability;
  const interrupt = (stream as any).interrupt;
  const hasInterrupt = !!interrupt;

  // 快捷提示词选择
  const handleQuickPromptSelect = (value: string) => {
    setInput(value);
  };

  // Check if input is valid
  const canSubmit =
    input.trim() ||
    textareaRef.current?.value?.trim() ||
    contentBlocks.length > 0;

  const [selectedTodo, setSelectedTodo] = useState<{
    id: number;
    title: string;
  } | null>(null);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [threadId] = useQueryState("threadId");

  useEffect(() => {
    // 监听待办选中事件
    const handleTodoSelected = () => {
      const stored = sessionStorage.getItem("selectedTodo");
      const parsed = safeParseJson(stored, SelectedTodoSchema, null);
      // 验证是否属于当前对话；threadId 任一方为空时也接受（新建会话等）
      const threadMatch =
        threadId == null ||
        parsed?.threadId == null ||
        parsed?.threadId === threadId;
      setSelectedTodo(parsed && threadMatch ? parsed : null);
    };

    const handleTodoDeselected = () => {
      setSelectedTodo(null);
    };

    // 初始加载时检查
    handleTodoSelected();

    window.addEventListener("todoSelected", handleTodoSelected);
    window.addEventListener("todoDeselected", handleTodoDeselected);

    return () => {
      window.removeEventListener("todoSelected", handleTodoSelected);
      window.removeEventListener("todoDeselected", handleTodoDeselected);
    };
  }, [threadId]);

  return (
    <div
      ref={dropRef}
      className="chat-content-shell relative z-10 mx-auto"
    >
      {/* 选中待办提示 - 仅在非审核状态下显示 */}
      {!hasInterrupt && selectedTodo && (
        <div
          className="mb-2"
          data-selected-todo={selectedTodo.id}
        >
          <div className="chat-todo-pill inline-flex max-w-full items-center gap-1.5 rounded-[14px] px-2.5 py-2 text-[var(--chat-ui-font-sm)] sm:gap-2 sm:px-3">
            <span className="min-w-0 truncate font-medium">
              已选中「{selectedTodo.title}」
            </span>
            <span className="chat-todo-pill-secondary hidden sm:inline">|</span>
            <span className="chat-todo-pill-secondary hidden whitespace-nowrap text-[var(--chat-ui-font-xs)] sm:inline">
              可补充、修改、完成或删除
            </span>
            <button
              type="button"
              className="chat-todo-dismiss flex h-6 w-6 shrink-0 items-center justify-center rounded transition-colors"
              onClick={() => {
                sessionStorage.removeItem("selectedTodo");
                setSelectedTodo(null);
                window.dispatchEvent(new Event("todoDeselected"));
              }}
              title="取消选中"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* 内容区域：审核卡片 或 输入表单 */}
      {/* data-chat-state 用于 E2E 测试判断当前状态：
                - idle: 空闲，可以输入
                - streaming: AI 正在响应
                - waiting-confirm: 等待用户确认
            */}
      <div
        className="w-full"
        data-testid="chat-input-container"
        data-chat-state={
          hasInterrupt ? "waiting-confirm" : isLoading ? "streaming" : "idle"
        }
      >
        {hasInterrupt ? (
          <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <CompactApproval />
          </div>
        ) : (
          <form
            onSubmit={onSubmit}
            className="w-full"
          >
            {/* 主输入容器 - ChatGPT 风格 */}
            <div className="chat-compose-surface relative rounded-[24px] transition-shadow">
              {/* 文件预览 - 在输入框内部顶部 */}
              {contentBlocks.length > 0 && (
                <div className="px-[var(--chat-content-inline-padding)] pt-3 pb-2">
                  <ContentBlocksPreview
                    blocks={contentBlocks}
                    onRemove={onRemoveBlock}
                  />
                </div>
              )}

              {/* 文本输入框 */}
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onPaste={onPaste}
                onKeyDown={(e) => {
                  if (
                    e.key === "Enter" &&
                    !e.shiftKey &&
                    !e.metaKey &&
                    !e.nativeEvent.isComposing
                  ) {
                    e.preventDefault();
                    const el = e.target as HTMLElement | undefined;
                    const form = el?.closest("form");
                    form?.requestSubmit();
                  }
                }}
                placeholder={
                  selectedTodo
                    ? `对「${selectedTodo.title}」说点什么...（补充、修改、完成、删除）`
                    : "请输入消息..."
                }
                className="chat-compose-field field-sizing-content"
                style={{ fieldSizing: "content" } as any}
                data-testid="chat-input"
                data-streaming={isLoading ? "true" : "false"}
              />

              {/* 底部操作栏 */}
              <div className="chat-compose-toolbar">
                {/* 左侧：+ 按钮和隐藏的开关 */}
                <div className="chat-compose-toolbar-left">
                  {/* 圆形 + 按钮 */}
                  <Label
                    htmlFor="file-input"
                    className="chat-compose-tool group flex cursor-pointer items-center justify-center transition-colors"
                  >
                    <Plus className="h-5 w-5 text-current" />
                  </Label>
                  <input
                    id="file-input"
                    type="file"
                    onChange={onFileUpload}
                    multiple
                    accept={CHAT_FILE_INPUT_ACCEPT}
                    className="hidden"
                  />

                  {/* 快捷指令 - 大屏下拉，小屏 Popover */}
                  <div className="hidden items-center gap-2 lg:flex">
                    <Select onValueChange={handleQuickPromptSelect}>
                      <SelectTrigger className="chat-select-trigger chat-compose-select h-9 w-[132px] justify-start gap-2 text-left shadow-none">
                        <SelectValue placeholder="快捷指令" />
                      </SelectTrigger>
                      <SelectContent className="chat-popover-surface rounded-2xl font-sans">
                        {QUICK_PROMPTS.map((prompt) => (
                          <SelectItem
                            key={prompt.label}
                            value={prompt.value}
                          >
                            {prompt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="lg:hidden">
                    <Popover
                      open={popoverOpen}
                      onOpenChange={setPopoverOpen}
                    >
                      <PopoverTrigger asChild>
                        <button
                          type="button"
                          className="chat-compose-tool group flex items-center justify-center transition-colors"
                          title="快捷指令"
                        >
                          <Zap className="h-4 w-4 text-current" />
                        </button>
                      </PopoverTrigger>
                      <PopoverContent
                        className="chat-popover-surface w-48 p-1"
                        align="start"
                      >
                        <div className="flex flex-col">
                          {QUICK_PROMPTS.map((prompt) => (
                            <button
                              key={prompt.label}
                              type="button"
                              className="rounded-xl px-3 py-2 text-left text-[var(--chat-ui-font-sm)] transition-colors hover:bg-black/5"
                              onClick={() => {
                                setPopoverOpen(false);
                                handleQuickPromptSelect(prompt.value);
                              }}
                            >
                              {prompt.label}
                            </button>
                          ))}
                        </div>
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>

                {/* 右侧：开关 + 麦克风和发送按钮 */}
                <div className="chat-compose-toolbar-right">
                  {/* 开关控件组 - 更紧凑 */}
                  <div className="mr-1 hidden items-center gap-2 md:flex">
                    {/* 深度思考开关 */}
                    <div className="flex items-center space-x-1">
                      <Switch
                        id="enable-thinking"
                        checked={enableThinking}
                        disabled={!isThinkingToggleable(thinkingCapability)}
                        onCheckedChange={(checked) => {
                          if (thinkingCapability === "always") {
                            toast.info("该模型始终启用深度思考，无法关闭");
                            return;
                          }
                          if (thinkingCapability === "never") {
                            toast.info("该模型不支持深度思考");
                            return;
                          }
                          setEnableThinking(checked);
                        }}
                        className="scale-75"
                      />
                      <Label
                        htmlFor="enable-thinking"
                        className={cn(
                          "chat-compose-label cursor-pointer whitespace-nowrap",
                          isThinkingToggleable(thinkingCapability)
                            ? "chat-muted-copy"
                            : "chat-soft-copy",
                        )}
                      >
                        思考
                      </Label>
                    </div>

                    {/* 多智能体模式已默认开启，无需开关 */}
                  </div>

                  {/* 麦克风按钮 */}
                  <button
                    type="button"
                    className="chat-compose-tool group flex items-center justify-center transition-colors"
                    onClick={() => toast.info("语音输入功能开发中")}
                  >
                    <Mic className="h-4 w-4 text-current" />
                  </button>

                  {/* 发送按钮 */}
                  {isLoading ? (
                    <Button
                      key="stop"
                      type="button"
                      data-testid="chat-stop-button"
                      aria-label="停止生成"
                      onClick={onStop}
                      size="icon"
                      className="chat-contrast-button h-9 w-9 rounded-[14px]"
                    >
                      <LoaderCircle className="h-4 w-4 animate-spin text-white" />
                    </Button>
                  ) : (
                    <Button
                      type="submit"
                      size="icon"
                      className="chat-contrast-button h-9 w-9 rounded-[14px] disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={isLoading || !canSubmit}
                    >
                      <ArrowUp className="h-4 w-4 text-white" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </form>
        )}
      </div>

      {/* 底部免责声明 - 始终显示 */}
      <p className="chat-compose-note mt-2 px-4 text-center transition-all duration-300">
        智能助手可能会出错，请谨慎甄别结果。
      </p>
    </div>
  );
}
