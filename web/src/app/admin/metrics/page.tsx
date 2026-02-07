/**
 * 指标管理页面
 *
 * 管理问数助手的指标定义，支持手动创建和 AI 从 ETL 脚本提取。
 */
"use client";

import dynamic from "next/dynamic";

const MetricAdminPanel = dynamic(
    () => import("@/components/admin/MetricAdminPanel").then(mod => mod.MetricAdminPanel),
    {
        ssr: false,
        loading: () => (
            <div className="flex h-full items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#A8D4D4] border-t-[#2F6868]" />
                    <span className="text-sm text-gray-500">加载中...</span>
                </div>
            </div>
        ),
    }
);

export default function MetricAdminPage() {
    return <MetricAdminPanel />;
}
