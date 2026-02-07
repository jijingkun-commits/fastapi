/**
 * SQL 修正台管理页面
 * 
 * 审核 AI 生成的 SQL，修正错误，持续改进问数能力：
 * - 查询日志列表展示
 * - SQL 修正对话框
 * - 反馈标记（正确/错误）
 * - 批量训练
 */
"use client";

import dynamic from "next/dynamic";

const DataAdminPanel = dynamic(
    () => import("@/components/admin/DataAdminPanel").then(mod => mod.DataAdminPanel),
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

export default function DataAdminPage() {
    return <DataAdminPanel />;
}
