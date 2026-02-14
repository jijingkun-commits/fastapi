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
                    "app-sidebar-surface relative flex h-screen flex-col border-r transition-all duration-200",
                    collapsed ? "w-[56px]" : "w-[196px]"
                )}
            >
                {/* 右侧内阴影 */}
                <div className="shadow-inner-right pointer-events-none absolute inset-0 z-10" />

                {/* 顶部标题区 */}
                <div
                    className={cn(
                        "app-sidebar-separator flex h-12 shrink-0 items-center border-b",
                        collapsed ? "justify-center px-1.5" : "justify-between px-3"
                    )}
                >
                    {!collapsed && (
                        <span className="app-sidebar-title text-xs font-semibold tracking-wide">
                            管理后台
                        </span>
                    )}
                    <button
                        onClick={() => setCollapsed(!collapsed)}
                        className="app-sidebar-item flex h-6 w-6 items-center justify-center rounded-md transition-colors hover:text-[var(--app-sidebar-icon-active)]"
                    >
                        {collapsed ? (
                            <PanelLeft className="h-3.5 w-3.5" />
                        ) : (
                            <PanelLeftClose className="h-3.5 w-3.5" />
                        )}
                    </button>
                </div>

                {/* 导航菜单 */}
                <nav className="flex-1 overflow-y-auto px-1.5 py-1.5">
                    <ul className="flex flex-col gap-0.5">
                        {navItems.map((item) => {
                            const active = isActive(item.href);
                            const linkContent = (
                                <Link
                                    href={item.href}
                                    className={cn(
                                        "app-sidebar-item flex items-center rounded-lg px-2.5 py-1.5 text-xs transition-all duration-150",
                                        collapsed ? "justify-center" : "gap-3",
                                        active && "app-sidebar-item-active"
                                    )}
                                >
                                    <item.icon
                                        className={cn(
                                            "app-sidebar-icon h-3.5 w-3.5 shrink-0 transition-colors",
                                            active && "app-sidebar-icon-active"
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
                <div className="app-sidebar-separator shrink-0 border-t px-1.5 py-1.5">
                    {collapsed ? (
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Link
                                    href="/"
                                    className="app-sidebar-item flex items-center justify-center rounded-lg px-2.5 py-1.5 text-xs transition-all duration-150"
                                >
                                    <MessageSquare className="app-sidebar-icon h-3.5 w-3.5 shrink-0" />
                                </Link>
                            </TooltipTrigger>
                            <TooltipContent side="right" sideOffset={8}>
                                返回聊天
                            </TooltipContent>
                        </Tooltip>
                    ) : (
                        <Link
                            href="/"
                            className="app-sidebar-item flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-xs transition-all duration-150"
                        >
                            <MessageSquare className="app-sidebar-icon h-3.5 w-3.5 shrink-0" />
                            <span>返回聊天</span>
                        </Link>
                    )}
                </div>
            </aside>
        </TooltipProvider>
    );
}
