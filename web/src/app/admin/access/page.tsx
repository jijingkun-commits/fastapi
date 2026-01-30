/**
 * 数据访问控制管理页面
 * 
 * 配置 AI 问数功能的数据库访问权限：
 * - 表白名单/黑名单管理
 * - Schema 白名单管理
 * - SQL 权限测试
 */
"use client";

import dynamic from "next/dynamic";
import { Toaster } from "@/components/ui/sonner";

const AccessAdminPanel = dynamic(
    () => import("@/components/admin/AccessAdminPanel").then(mod => mod.AccessAdminPanel),
    {
        ssr: false,
        loading: () => (
            <div className="flex h-screen items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
                    <span className="text-sm text-gray-500">加载中...</span>
                </div>
            </div>
        ),
    }
);

export default function AccessAdminPage() {
    return (
        <div className="min-h-screen w-full bg-background">
            <Toaster richColors closeButton />
            <AccessAdminPanel />
        </div>
    );
}
