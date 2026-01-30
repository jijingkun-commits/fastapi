/**
 * 技能管理页面
 * 
 * 管理 Agent 技能向量和配置：
 * - 技能列表
 * - 向量状态检查
 * - 向量重新生成
 */
"use client";

import dynamic from "next/dynamic";
import { Toaster } from "@/components/ui/sonner";

const SkillAdminPanel = dynamic(
    () => import("@/components/admin/SkillAdminPanel").then(mod => mod.SkillAdminPanel),
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

export default function SkillAdminPage() {
    return (
        <div className="min-h-screen w-full bg-background">
            <Toaster richColors closeButton />
            <SkillAdminPanel />
        </div>
    );
}
