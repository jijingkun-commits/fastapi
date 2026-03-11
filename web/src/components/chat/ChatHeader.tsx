/**
 * 聊天头部导航组件（中文注释）
 *
 * 包含：侧边栏切换按钮、模型选择器、新对话按钮、用户菜单
 */

import { Button } from "@/components/ui/button";
import { PanelRightClose, PanelRightOpen, SquarePen, LogOut, Settings } from "lucide-react";
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
  dataRole: string | null;
  dataRoleLabel: string | null;
}

export interface ChatHeaderProps {
  chatHistoryOpen: boolean;
  onToggleChatHistory: () => void;
  onNewThread: () => void;
  isLargeScreen: boolean;
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  models: ModelConfig[];
  modelsLoading?: boolean;
  chatStarted?: boolean;
}

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
          dataRole: me.data_role ?? null,
          dataRoleLabel: me.data_role_label ?? null,
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
    return currentUser?.dataRoleLabel?.trim() || currentUser?.dataRole?.trim() || null;
  }, [currentUser]);

  const userAvatarText = useMemo(() => {
    const source = currentUser?.username?.trim() || currentUser?.mobile?.trim() || "U";
    const firstChar = source.charAt(0);
    return firstChar ? firstChar.toUpperCase() : "U";
  }, [currentUser]);

  const userMetaItems = useMemo(() => {
    const items: Array<{ label: string; value: string }> = [];

    if (typeof currentUser?.id === "number") {
      items.push({
        label: "用户 ID",
        value: String(currentUser.id),
      });
    }

    const dataRoleLabel = currentUser?.dataRoleLabel?.trim() || currentUser?.dataRole?.trim() || null;
    if (dataRoleLabel) {
      items.push({
        label: "数据角色",
        value: dataRoleLabel,
      });
    }

    return items;
  }, [currentUser]);

  const handleLogout = async () => {
    try {
      await logout();
      toast.success("已退出登录");
      router.push("/auth");
    } catch {
      router.push("/auth");
    }
  };

  return (
    <div className="chat-header-surface relative z-10">
      <header className="chat-header-row">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          {(!chatHistoryOpen || !isLargeScreen) && (
            <Button
              className="chat-header-control chat-icon-button h-[34px] w-[34px] rounded-[11px]"
              variant="ghost"
              onClick={onToggleChatHistory}
              title="切换历史对话"
              aria-label="切换历史对话"
            >
              {chatHistoryOpen ? (
                <PanelRightOpen className="size-4" />
              ) : (
                <PanelRightClose className="size-4" />
              )}
            </Button>
          )}

          <Select value={selectedModel} onValueChange={onModelChange}>
            <SelectTrigger className="chat-header-control chat-select-trigger h-[34px] w-[156px] justify-start gap-1.5 rounded-[11px] px-2.5 text-left text-[13px] font-medium font-sans shadow-none focus:ring-0 sm:w-[176px]">
              <SelectValue placeholder="选择模型" />
            </SelectTrigger>
            <SelectContent className="chat-popover-surface rounded-2xl font-sans">
              {modelsLoading ? (
                <SelectItem value="loading" disabled className="font-sans">
                  加载中...
                </SelectItem>
              ) : (
                models.map((model) => (
                  <SelectItem key={model.id} value={model.id} className="font-sans">
                    {model.name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        </div>

        <div className="flex shrink-0 items-center justify-end gap-1.5">
          {chatStarted ? (
            <Button
              type="button"
              variant="ghost"
              className="chat-header-action hidden h-[34px] rounded-[11px] px-2.5 text-[13px] font-medium font-sans sm:inline-flex"
              title="新会话"
              aria-label="新会话"
              onClick={onNewThread}
            >
              <SquarePen className="mr-1.5 size-3.5" />
              新会话
            </Button>
          ) : null}

          {chatStarted ? (
            <Button
              type="button"
              variant="ghost"
              className="chat-header-control chat-icon-button h-[34px] w-[34px] rounded-[11px] sm:hidden"
              title="新会话"
              aria-label="新会话"
              onClick={onNewThread}
            >
              <SquarePen className="size-4" />
            </Button>
          ) : null}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="chat-user-trigger h-[34px] w-[34px] rounded-[11px] p-0"
                title={userPrimaryText}
                aria-label="用户菜单"
              >
                <Avatar className="h-7 w-7">
                  <AvatarFallback className="bg-black text-[10px] font-semibold text-white">
                    {userAvatarText}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="chat-popover-surface w-64 rounded-2xl p-1 font-sans">
              <DropdownMenuLabel className="p-1 font-normal">
                <div className="rounded-xl border border-black/6 bg-black/[0.03] px-3 py-2.5">
                  <div className="flex items-center gap-2.5">
                    <Avatar className="h-7 w-7">
                      <AvatarFallback className="bg-black text-xs font-semibold text-white">
                        {userAvatarText}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] text-muted-foreground">当前登录账号</p>
                      <p className="truncate text-sm font-semibold text-foreground">{userPrimaryText}</p>
                    </div>
                  </div>
                  {userSecondaryText && (
                    <p className="mt-1.5 truncate pl-[42px] text-xs text-muted-foreground">{userSecondaryText}</p>
                  )}
                  {userMetaItems.length > 0 && (
                    <div className="mt-2 space-y-1.5 rounded-lg border border-black/6 bg-white/90 px-2.5 py-2">
                      {userMetaItems.map((item) => (
                        <div key={item.label} className="flex items-center justify-between gap-3 text-[11px]">
                          <span className="text-muted-foreground">{item.label}</span>
                          <span className="max-w-[130px] truncate font-medium text-foreground">{item.value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => router.push("/admin")}
                className="mx-1 my-0.5 rounded-xl px-3 py-2 text-[15px] font-medium focus:bg-black/5 focus:text-black"
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
      </header>
    </div>
  );
}