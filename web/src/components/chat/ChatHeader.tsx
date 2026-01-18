/**
 * 聊天头部导航组件（中文注释）
 * 
 * 包含：侧边栏切换按钮、模型选择器、新对话按钮
 */

import { Button } from "@/components/ui/button";
import { TooltipIconButton } from "@/components/chat/tooltip-icon-button";
import { PanelRightClose, PanelRightOpen, SquarePen } from "lucide-react";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { ModelConfig } from "@/lib/model-config";

export interface ChatHeaderProps {
    /** 聊天历史面板是否打开 */
    chatHistoryOpen: boolean;
    /** 切换聊天历史面板 */
    onToggleChatHistory: () => void;
    /** 开始新对话 */
    onNewThread: () => void;
    /** 是否为大屏幕 */
    isLargeScreen: boolean;
    /** 当前选中的模型 ID */
    selectedModel: string;
    /** 模型变更回调 */
    onModelChange: (modelId: string) => void;
    /** 可用模型列表 */
    models: ModelConfig[];
    /** 模型列表加载中 */
    modelsLoading?: boolean;
    /** 是否已开始对话（用于控制新对话按钮显示） */
    chatStarted?: boolean;
}

/**
 * 聊天头部导航组件
 */
export function ChatHeader({
    chatHistoryOpen,
    onToggleChatHistory,
    onNewThread,
    isLargeScreen,
    selectedModel,
    onModelChange,
    models,
    modelsLoading = false,
    chatStarted = false,
}: ChatHeaderProps) {
    return (
        <div className="relative z-10 flex items-center justify-between gap-3 p-2 pl-4">
            {/* 左侧：侧边栏切换 + 模型选择 */}
            <div className="flex items-center gap-2">
                {(!chatHistoryOpen || !isLargeScreen) && (
                    <Button
                        className="hover:bg-gray-100"
                        variant="ghost"
                        onClick={onToggleChatHistory}
                    >
                        {chatHistoryOpen ? (
                            <PanelRightOpen className="size-5" />
                        ) : (
                            <PanelRightClose className="size-5" />
                        )}
                    </Button>
                )}
                {/* 模型选择器 - ChatGPT 风格 */}
                <Select value={selectedModel} onValueChange={onModelChange}>
                    <SelectTrigger className="w-auto gap-2 border-0 bg-transparent px-2 text-base font-medium text-black hover:bg-gray-100/50 focus:ring-0 data-[state=open]:bg-gray-100/50">
                        <SelectValue placeholder="选择模型" />
                    </SelectTrigger>
                    <SelectContent>
                        {modelsLoading ? (
                            <SelectItem value="loading" disabled>加载中...</SelectItem>
                        ) : (
                            models.map((model) => (
                                <SelectItem key={model.id} value={model.id}>
                                    {model.name}
                                </SelectItem>
                            ))
                        )}
                    </SelectContent>
                </Select>
            </div>

            {/* 右侧：新对话按钮（仅在对话进行中显示） */}
            {chatStarted && (
                <TooltipIconButton
                    size="lg"
                    className="p-4"
                    tooltip="New thread"
                    variant="ghost"
                    onClick={onNewThread}
                >
                    <SquarePen className="size-5" />
                </TooltipIconButton>
            )}
        </div>
    );
}
