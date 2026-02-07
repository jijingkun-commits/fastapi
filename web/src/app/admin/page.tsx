/**
 * 管理后台首页
 * 
 * 提供所有管理功能的入口导航：
 * - 数据访问控制
 * - LLM 模型配置
 * - 技能管理
 * - 系统配置
 * - 指标管理
 * - SQL 修正台
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
    Database,
    BarChart3,
    ChevronRight
} from "lucide-react";

const adminModules = [
    {
        title: "数据访问控制",
        description: "配置问数功能的数据库访问权限、表白名单/黑名单",
        href: "/admin/access",
        icon: Shield,
    },
    {
        title: "LLM 模型配置",
        description: "管理 AI 模型提供商、模型启用/禁用、默认模型设置",
        href: "/admin/llm",
        icon: Bot,
    },
    {
        title: "技能管理",
        description: "查看和管理 AI 技能列表与向量状态",
        href: "/admin/skills",
        icon: Sparkles,
    },
    {
        title: "系统配置",
        description: "查看和编辑系统运行参数配置",
        href: "/admin/system",
        icon: Settings,
    },
    {
        title: "指标管理",
        description: "管理问数指标定义，支持 AI 从 ETL 脚本提取 SELECT 模板",
        href: "/admin/metrics",
        icon: BarChart3,
    },
    {
        title: "SQL 修正台",
        description: "审核 AI 生成的 SQL，修正错误，持续改进问数能力",
        href: "/admin/data",
        icon: Database,
    },
    {
        title: "用户管理",
        description: "管理系统用户、角色和权限",
        href: "/admin/users",
        icon: Users,
    },
];

export default function AdminPage() {
    return (
        <div className="h-full overflow-y-auto bg-white">
            <div className="mx-auto max-w-5xl px-8 py-10">
                <header className="mb-8">
                    <h1 className="text-2xl font-semibold text-gray-900">总览</h1>
                    <p className="mt-1 text-sm text-gray-500">选择功能模块开始管理</p>
                </header>
                
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {adminModules.map((module) => (
                        <Link
                            key={module.href}
                            href={module.href}
                            className="group relative flex flex-col rounded-xl border border-gray-200/80 bg-white p-6 shadow-sm ring-1 ring-black/5 transition-all duration-150 hover:shadow-md"
                        >
                            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-[#2F6868]">
                                <module.icon className="h-5 w-5 text-white" />
                            </div>
                            <h2 className="text-base font-semibold text-gray-900">
                                {module.title}
                            </h2>
                            <p className="mt-1 flex-1 text-sm text-gray-500">
                                {module.description}
                            </p>
                            <div className="mt-4 flex items-center text-sm font-medium text-[#2F6868] opacity-0 transition-opacity group-hover:opacity-100">
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
