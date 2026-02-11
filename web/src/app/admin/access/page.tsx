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
import { PageLoader } from "@/components/ui/page-loader";

const AccessAdminPanel = dynamic(
    () => import("@/components/admin/AccessAdminPanel").then(mod => mod.AccessAdminPanel),
    {
        ssr: false,
        loading: () => <PageLoader />,
    },
);

export default function AccessAdminPage() {
    return <AccessAdminPanel />;
}
