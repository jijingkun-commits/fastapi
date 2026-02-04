/**
 * 管理后台首页
 * 
 * 提供所有管理功能的入口导航：
 * - 数据访问控制
 * - LLM 模型配置
 * - 技能管理
 * - 系统配置
 * - 用户管理
 */
"use client";

import Link from "next/link";
import { 
    Shield, 
    Bot, 
    Sparkles, 
    Settings, 
    Users,
    ChevronRight
} from "lucide-react";

const adminModules = [
    {
        title: "数据访问控制",
        description: "配置问数功能的数据库访问权限、表白名单/黑名单",
        href: "/admin/access",
        icon: Shield,
        color: "bg-blue-500",
    },
    {
        title: "LLM 模型配置",
        description: "管理 AI 模型提供商、模型启用/禁用、默认模型设置",
        href: "/admin/llm",
        icon: Bot,
        color: "bg-purple-500",
    },
    {
        title: "技能管理",
        description: "查看和管理 AI 技能列表与向量状态",
        href: "/admin/skills",
        icon: Sparkles,
        color: "bg-amber-500",
    },
    {
        title: "系统配置",
        description: "查看和编辑系统运行参数配置",
        href: "/admin/system",
        icon: Settings,
        color: "bg-slate-500",
    },
    {
        title: "用户管理",
        description: "管理系统用户、角色和权限",
        href: "/admin/users",
        icon: Users,
        color: "bg-green-500",
    },
];

export default function AdminPage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
            <div className="mx-auto max-w-5xl px-6 py-12">
                <header className="mb-10">
                    <h1 className="text-3xl font-bold text-slate-900">管理后台</h1>
                    <p className="mt-2 text-slate-600">系统配置与管理中心</p>
                </header>
                
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {adminModules.map((module) => (
                        <Link
                            key={module.href}
                            href={module.href}
                            className="group relative flex flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:border-slate-300 hover:shadow-md"
                        >
                            <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-lg ${module.color}`}>
                                <module.icon className="h-6 w-6 text-white" />
                            </div>
                            <h2 className="text-lg font-semibold text-slate-900">
                                {module.title}
                            </h2>
                            <p className="mt-1 flex-1 text-sm text-slate-500">
                                {module.description}
                            </p>
                            <div className="mt-4 flex items-center text-sm font-medium text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100">
                                进入管理
                                <ChevronRight className="ml-1 h-4 w-4" />
                            </div>
                        </Link>
                    ))}
                </div>
            </div>
        </div>
    );
}
