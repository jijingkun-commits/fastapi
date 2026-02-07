/**
 * 管理后台侧边栏导航
 *
 * 功能：
 * - 模块导航菜单
 * - 当前路由高亮
 * - 可折叠/展开
 * - 返回聊天入口
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Shield,
    Bot,
    Sparkles,
    Settings,
    Users,
    Database,
    BarChart3,
    LayoutDashboard,
    PanelLeftClose,
    PanelLeft,
    MessageSquare,
} from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const navItems = [
    {
        title: "总览",
        href: "/admin",
        icon: LayoutDashboard,
    },
    {
        title: "数据访问控制",
        href: "/admin/access",
        icon: Shield,
    },
    {
        title: "LLM 模型配置",
        href: "/admin/llm",
        icon: Bot,
    },
    {
        title: "技能管理",
        href: "/admin/skills",
        icon: Sparkles,
    },
    {
        title: "系统配置",
        href: "/admin/system",
        icon: Settings,
    },
    {
        title: "指标管理",
        href: "/admin/metrics",
        icon: BarChart3,
    },
    {
        title: "SQL 修正台",
        href: "/admin/data",
        icon: Database,
    },
    {
        title: "用户管理",
        href: "/admin/users",
        icon: Users,
    },
];

export function AdminSidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    const isActive = (href: string) => {
        if (href === "/admin") return pathname === "/admin";
        return pathname.startsWith(href);
    };

    return (
        <TooltipProvider delayDuration={0}>
            <aside
                className={cn(
                    "relative flex h-screen flex-col border-r border-gray-200/80 bg-[#f8f9fa] transition-all duration-200",
                    collapsed ? "w-[60px]" : "w-[220px]"
                )}
            >
                {/* 右侧内阴影 */}
                <div className="shadow-inner-right pointer-events-none absolute inset-0 z-10" />

                {/* 顶部标题区 */}
                <div
                    className={cn(
                        "flex h-14 shrink-0 items-center border-b border-gray-200/80",
                        collapsed ? "justify-center px-2" : "justify-between px-4"
                    )}
                >
                    {!collapsed && (
                        <span className="text-sm font-semibold text-gray-800">
                            管理后台
                        </span>
                    )}
                    <button
                        onClick={() => setCollapsed(!collapsed)}
                        className="flex h-7 w-7 items-center justify-center rounded-md text-gray-400 transition-colors hover:bg-[#2F6868]/10 hover:text-[#2F6868]"
                    >
                        {collapsed ? (
                            <PanelLeft className="h-3.5 w-3.5" />
                        ) : (
                            <PanelLeftClose className="h-3.5 w-3.5" />
                        )}
                    </button>
                </div>

                {/* 导航菜单 */}
                <nav className="flex-1 overflow-y-auto px-2 py-2">
                    <ul className="flex flex-col gap-0.5">
                        {navItems.map((item) => {
                            const active = isActive(item.href);
                            const linkContent = (
                                <Link
                                    href={item.href}
                                    className={cn(
                                        "flex items-center rounded-lg px-3 py-2 text-[13px] transition-all duration-150",
                                        collapsed ? "justify-center" : "gap-3",
                                        active
                                            ? "bg-white text-gray-900 shadow-sm ring-1 ring-black/5"
                                            : "text-gray-600 hover:bg-white/70 hover:text-gray-900"
                                    )}
                                >
                                    <item.icon
                                        className={cn(
                                            "h-4 w-4 shrink-0 transition-colors",
                                            active
                                                ? "text-[#2F6868]"
                                                : "text-gray-400"
                                        )}
                                    />
                                    {!collapsed && (
                                        <span className="truncate">
                                            {item.title}
                                        </span>
                                    )}
                                </Link>
                            );

                            return (
                                <li key={item.href}>
                                    {collapsed ? (
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                {linkContent}
                                            </TooltipTrigger>
                                            <TooltipContent
                                                side="right"
                                                sideOffset={8}
                                            >
                                                {item.title}
                                            </TooltipContent>
                                        </Tooltip>
                                    ) : (
                                        linkContent
                                    )}
                                </li>
                            );
                        })}
                    </ul>
                </nav>

                {/* 底部返回聊天入口 */}
                <div className="shrink-0 border-t border-gray-200/80 px-2 py-2">
                    {collapsed ? (
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Link
                                    href="/"
                                    className="flex items-center justify-center rounded-lg px-3 py-2 text-[13px] text-gray-600 transition-all duration-150 hover:bg-white/70 hover:text-gray-900"
                                >
                                    <MessageSquare className="h-4 w-4 shrink-0 text-gray-400" />
                                </Link>
                            </TooltipTrigger>
                            <TooltipContent side="right" sideOffset={8}>
                                返回聊天
                            </TooltipContent>
                        </Tooltip>
                    ) : (
                        <Link
                            href="/"
                            className="flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] text-gray-600 transition-all duration-150 hover:bg-white/70 hover:text-gray-900"
                        >
                            <MessageSquare className="h-4 w-4 shrink-0 text-gray-400" />
                            <span>返回聊天</span>
                        </Link>
                    )}
                </div>
            </aside>
        </TooltipProvider>
    );
}
