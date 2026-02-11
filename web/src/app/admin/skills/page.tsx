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
import { PageLoader } from "@/components/ui/page-loader";

const SkillAdminPanel = dynamic(
    () => import("@/components/admin/SkillAdminPanel").then(mod => mod.SkillAdminPanel),
    {
        ssr: false,
        loading: () => <PageLoader />,
    },
);

export default function SkillAdminPage() {
    return <SkillAdminPanel />;
}
