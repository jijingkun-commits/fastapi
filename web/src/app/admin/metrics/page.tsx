/**
 * 指标管理页面
 *
 * 管理问数助手的指标定义，支持手动创建和 AI 从 ETL 脚本提取。
 */
"use client";

import dynamic from "next/dynamic";
import { PageLoader } from "@/components/ui/page-loader";

const MetricAdminPanel = dynamic(
    () => import("@/components/admin/MetricAdminPanel").then(mod => mod.MetricAdminPanel),
    {
        ssr: false,
        loading: () => <PageLoader />,
    },
);

export default function MetricAdminPage() {
    return <MetricAdminPanel />;
}
