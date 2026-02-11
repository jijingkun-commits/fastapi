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
import { PageLoader } from "@/components/ui/page-loader";

const LLMAdminPanel = dynamic(
    () => import("@/components/admin/LLMAdminPanel").then(mod => mod.LLMAdminPanel),
    {
        ssr: false,
        loading: () => <PageLoader />,
    },
);

export default function LLMAdminPage() {
    return <LLMAdminPanel />;
}
