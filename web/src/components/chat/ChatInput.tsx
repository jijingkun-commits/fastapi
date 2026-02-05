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

import { FormEvent, RefObject, useState, useEffect } from "react";
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
import { Plus, LoaderCircle, Mic, ArrowUp } from "lucide-react";
import { cn, safeParseJson, SelectedTodoSchema } from "@/lib/utils";
import { CompactApproval } from "./CompactApproval";
import { ContentBlocksPreview } from "./ContentBlocksPreview";
import { ContentBlock } from "@langchain/core/messages";
import { ThinkingCapability, isThinkingToggleable } from "@/lib/model-config";
import { toast } from "sonner";
import { useStreamContext } from "@/providers/StreamContext";
import { useQueryState } from "nuqs";

/** 快捷提示词配置 */
export const QUICK_PROMPTS = [
    { label: "贷款余额", value: "查询贷款余额" },
    { label: "存款总额", value: "存款总额是多少" },
    { label: "不良贷款", value: "不良贷款余额" },
    { label: "分行存款", value: "按分行统计存款" },
    { label: "t2sql", value: "查询我数据库中一个有几张表" },
    { label: "天气", value: "查询我嘉兴近一周的天气" },
    { label: "minio", value: "使用fig_inter工具，生成一个圆形，以图片方式展示。" },
    { label: "知识库", value: "查询知识库，用户已注销无法使用该功能的问题要怎么解决？" },
    { label: "待办查询", value: "待办查询" },
    { label: "新渠道有哪些功能", value: "查询知识库，新渠道有哪些功能" },
    { label: "待办", value: "明天我要去上海" },
    { label: "待办1", value: "早上9点，和张三一起，去陆家嘴开会" },
    { label: "待办2", value: "好的" },
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
    onPaste: (e: React.ClipboardEvent<HTMLTextAreaElement | HTMLInputElement>) => void;
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
        (input.trim() || textareaRef.current?.value?.trim()) ||
        contentBlocks.length > 0;

    const [mounted, setMounted] = useState(false);
    const [selectedTodo, setSelectedTodo] = useState<{ id: number, title: string } | null>(null);
    const [threadId] = useQueryState("threadId");

    useEffect(() => {
        setMounted(true);

        // 监听待办选中事件
        const handleTodoSelected = () => {
            const stored = sessionStorage.getItem('selectedTodo');
            const parsed = safeParseJson(stored, SelectedTodoSchema, null);
            // 验证是否属于当前对话
            if (parsed && parsed.threadId === threadId) {
                setSelectedTodo(parsed);
            } else {
                setSelectedTodo(null);
            }
        };

        const handleTodoDeselected = () => {
            setSelectedTodo(null);
        };

        // 初始加载时检查
        handleTodoSelected();

        window.addEventListener('todoSelected', handleTodoSelected);
        window.addEventListener('todoDeselected', handleTodoDeselected);

        return () => {
            window.removeEventListener('todoSelected', handleTodoSelected);
            window.removeEventListener('todoDeselected', handleTodoDeselected);
        };
    }, [threadId]);

    return (
        <div ref={dropRef} className="relative z-10 w-full max-w-4xl mx-auto">
            {/* 选中待办提示 - 仅在非审核状态下显示 */}
            {!hasInterrupt && selectedTodo && (
                <div className="mb-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#E8F4F4] text-[#2F6868] text-xs rounded-lg border border-[#A8D4D4]">
                        <span className="font-medium">🎯 当前讨论:</span>
                        <span className="font-semibold">{selectedTodo.title}</span>
                        <span className="text-gray-400">|</span>
                        <span className="text-[#2F6868]">ID {selectedTodo.id}</span>
                        <button
                            type="button"
                            className="ml-1 text-[#67B0B0] hover:text-[#2F6868] transition-colors"
                            onClick={() => {
                                sessionStorage.removeItem('selectedTodo');
                                setSelectedTodo(null);
                                window.dispatchEvent(new Event('todoDeselected'));
                            }}
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
                data-chat-state={hasInterrupt ? "waiting-confirm" : (isLoading ? "streaming" : "idle")}
            >
                {hasInterrupt ? (
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <CompactApproval />
                    </div>
                ) : (
                    <form onSubmit={onSubmit} className="w-full">
                        {/* 主输入容器 - ChatGPT 风格 */}
                        <div className="relative bg-white rounded-[20px] border border-gray-200 shadow-sm hover:shadow transition-shadow">
                            {/* 文件预览 - 在输入框内部顶部 */}
                            {contentBlocks.length > 0 && (
                                <div className="px-4 pt-3 pb-2">
                                    <ContentBlocksPreview blocks={contentBlocks} onRemove={onRemoveBlock} />
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
                                placeholder={selectedTodo ? `讨论待办: ${selectedTodo.title}...` : "Type your message..."}
                                className="field-sizing-content resize-none border-none bg-transparent w-full px-4 py-3 shadow-none ring-0 outline-none focus:ring-0 focus:outline-none text-[15px] leading-relaxed min-h-[52px] max-h-[200px]"
                                style={{ fieldSizing: 'content' } as any}
                                data-testid="chat-input"
                                data-streaming={isLoading ? "true" : "false"}
                            />

                            {/* 底部操作栏 */}
                            <div className="flex items-center justify-between px-3 pb-3 pt-0">
                                {/* 左侧：+ 按钮和隐藏的开关 */}
                                <div className="flex items-center gap-2">
                                    {/* 圆形 + 按钮 */}
                                    <Label
                                        htmlFor="file-input"
                                        className="flex cursor-pointer items-center justify-center w-8 h-8 rounded-lg hover:bg-gray-100 transition-colors group"
                                    >
                                        <Plus className="w-5 h-5 text-gray-600 group-hover:text-gray-900" />
                                    </Label>
                                    <input
                                        id="file-input"
                                        type="file"
                                        onChange={onFileUpload}
                                        multiple
                                        accept="image/jpeg,image/png,image/gif,image/webp,application/pdf,.xlsx,.xls,.csv,.txt,.md,.docx"
                                        className="hidden"
                                    />

                                    {/* 开关控件 - 折叠到下拉菜单或隐藏 */}
                                    <div className="hidden lg:flex items-center gap-2">
                                        <Select onValueChange={handleQuickPromptSelect}>
                                            <SelectTrigger className="w-[120px] h-7 text-xs bg-transparent border-gray-200 text-gray-600">
                                                <SelectValue placeholder="快捷指令" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {QUICK_PROMPTS.map((prompt) => (
                                                    <SelectItem key={prompt.label} value={prompt.value}>
                                                        {prompt.label}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                {/* 右侧：开关 + 麦克风和发送按钮 */}
                                <div className="flex items-center gap-2">
                                    {/* 开关控件组 - 更紧凑 */}
                                    <div className="hidden md:flex items-center gap-2 mr-1">
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
                                                    "text-[11px] whitespace-nowrap cursor-pointer",
                                                    isThinkingToggleable(thinkingCapability)
                                                        ? "text-gray-600"
                                                        : "text-gray-400"
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
                                        className="flex items-center justify-center w-8 h-8 rounded-lg hover:bg-gray-100 transition-colors group"
                                        onClick={() => toast.info("语音输入功能开发中")}
                                    >
                                        <Mic className="w-4 h-4 text-gray-600 group-hover:text-gray-900" />
                                    </button>

                                    {/* 发送按钮 */}
                                    {isLoading ? (
                                        <Button
                                            key="stop"
                                            onClick={onStop}
                                            size="icon"
                                            className="w-8 h-8 rounded-lg bg-gray-900 hover:bg-gray-800"
                                        >
                                            <LoaderCircle className="h-4 w-4 animate-spin text-white" />
                                        </Button>
                                    ) : (
                                        <Button
                                            type="submit"
                                            size="icon"
                                            className="w-8 h-8 rounded-lg bg-gray-900 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
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
            <p className="text-center text-xs text-gray-500 mt-2 px-4 transition-all duration-300">
                AI 可能会出错。请谨慎甄别，要是出错了它可不负责哦~
            </p>
        </div>
    );
}
