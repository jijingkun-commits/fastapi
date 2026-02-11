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
import { PageLoader } from "@/components/ui/page-loader";

const DataAdminPanel = dynamic(
    () => import("@/components/admin/DataAdminPanel").then(mod => mod.DataAdminPanel),
    {
        ssr: false,
        loading: () => <PageLoader />,
    },
);

export default function DataAdminPage() {
    return <DataAdminPanel />;
}
