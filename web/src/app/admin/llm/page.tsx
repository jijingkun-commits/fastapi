/**
 * LLM 模型配置管理页面
 * 
 * 管理 AI 模型提供商和模型配置：
 * - 提供商管理
 * - 模型启用/禁用
 * - 默认模型设置
 * - API Key 更新
 */
"use client";

import dynamic from "next/dynamic";
import { Toaster } from "@/components/ui/sonner";

const LLMAdminPanel = dynamic(
    () => import("@/components/admin/LLMAdminPanel").then(mod => mod.LLMAdminPanel),
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

export default function LLMAdminPage() {
    return (
        <div className="min-h-screen w-full bg-background">
            <Toaster richColors closeButton />
            <LLMAdminPanel />
        </div>
    );
}
