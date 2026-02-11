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
import { PageLoader } from "@/components/ui/page-loader";

const SystemAdminPanel = dynamic(
    () => import("@/components/admin/SystemAdminPanel").then(mod => mod.SystemAdminPanel),
    {
        ssr: false,
        loading: () => <PageLoader />,
    },
);

export default function SystemAdminPage() {
    return <SystemAdminPanel />;
}
