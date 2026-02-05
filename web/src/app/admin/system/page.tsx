/**
 * 系统配置管理页面
 * 
 * 管理系统运行参数和配置项：
 * - 配置列表
 * - 配置编辑
 * - 分类筛选
 */
"use client";

import dynamic from "next/dynamic";
import { Toaster } from "@/components/ui/sonner";

const SystemAdminPanel = dynamic(
    () => import("@/components/admin/SystemAdminPanel").then(mod => mod.SystemAdminPanel),
    {
        ssr: false,
        loading: () => (
            <div className="flex h-screen items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#A8D4D4] border-t-[#2F6868]" />
                    <span className="text-sm text-gray-500">加载中...</span>
                </div>
            </div>
        ),
    }
);

export default function SystemAdminPage() {
    return (
        <div className="min-h-screen w-full bg-background">
            <Toaster richColors closeButton />
            <SystemAdminPanel />
        </div>
    );
}
