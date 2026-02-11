/**
 * 聊天头部导航组件（中文注释）
 * 
 * 包含：侧边栏切换按钮、模型选择器、新对话按钮、用户菜单
 */

import { Button } from "@/components/ui/button";
import { TooltipIconButton } from "@/components/chat/tooltip-icon-button";
import { PanelRightClose, PanelRightOpen, SquarePen, LogOut, User, Settings } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ModelConfig } from "@/lib/model-config";
import { getMe, logout } from "@/lib/backend";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

interface CurrentUser {
    id: number;
    username: string | null;
    mobile: string | null;
}

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
    const router = useRouter();
    const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);

    useEffect(() => {
        let mounted = true;

        const fetchCurrentUser = async () => {
            try {
                const me = await getMe();
                if (!mounted) {
                    return;
                }

                setCurrentUser({
                    id: me.id,
                    username: me.username ?? null,
                    mobile: me.mobile ?? null,
                });
            } catch {
                if (!mounted) {
                    return;
                }
                setCurrentUser(null);
            }
        };

        void fetchCurrentUser();

        return () => {
            mounted = false;
        };
    }, []);

    const userPrimaryText = useMemo(() => {
        if (currentUser?.username?.trim()) {
            return currentUser.username;
        }
        if (currentUser?.mobile?.trim()) {
            return currentUser.mobile;
        }
        return "当前用户";
    }, [currentUser]);

    const userSecondaryText = useMemo(() => {
        if (currentUser?.username?.trim() && currentUser.mobile?.trim()) {
            return currentUser.mobile;
        }
        return null;
    }, [currentUser]);

    const userAvatarText = useMemo(() => {
        const source = currentUser?.username?.trim() || currentUser?.mobile?.trim() || "U";
        const firstChar = source.charAt(0);
        return firstChar ? firstChar.toUpperCase() : "U";
    }, [currentUser]);

    // 处理登出
    const handleLogout = async () => {
        try {
            await logout();
            toast.success("已退出登录");
            router.push("/auth");
        } catch {
            // 即使服务端失败，也已清除本地 token
            router.push("/auth");
        }
    };

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

            {/* 右侧：新对话按钮 + 用户菜单 */}
            <div className="flex items-center gap-2">
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
                
                {/* 用户菜单 */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                            <Avatar className="h-9 w-9">
                                <AvatarFallback className="bg-[#E8F4F4] text-[#2F6868]">
                                    <User className="h-4 w-4" />
                                </AvatarFallback>
                            </Avatar>
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56 rounded-2xl p-1">
                        <DropdownMenuLabel className="p-1 font-normal">
                            <div className="rounded-xl bg-muted/40 px-3 py-2.5">
                                <div className="flex items-center gap-2.5">
                                    <Avatar className="h-8 w-8">
                                        <AvatarFallback className="bg-[#E8F4F4] text-xs font-semibold text-[#2F6868]">
                                            {userAvatarText}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="min-w-0 flex-1">
                                        <p className="text-[11px] text-muted-foreground">当前登录账号</p>
                                        <p className="truncate text-sm font-semibold text-foreground">
                                            {userPrimaryText}
                                        </p>
                                    </div>
                                </div>
                                {userSecondaryText && (
                                    <p className="mt-1.5 truncate pl-[42px] text-xs text-muted-foreground">
                                        {userSecondaryText}
                                    </p>
                                )}
                            </div>
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                            onClick={() => router.push("/admin")}
                            className="mx-1 my-0.5 rounded-xl px-3 py-2 text-[15px] font-medium"
                        >
                            <Settings className="mr-2 h-4 w-4" />
                            系统设置
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                            onClick={handleLogout}
                            className="mx-1 my-0.5 rounded-xl px-3 py-2 text-[15px] font-medium text-red-600 focus:bg-red-50 focus:text-red-600"
                        >
                            <LogOut className="mr-2 h-4 w-4" />
                            退出登录
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
}
