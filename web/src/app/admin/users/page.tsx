/**
 * 用户管理页面
 * 
 * 管理系统用户：
 * - 用户列表
 * - 创建用户
 * - 启用/禁用用户
 */
"use client";

import dynamic from "next/dynamic";
import { PageLoader } from "@/components/ui/page-loader";

const UserAdminPanel = dynamic(
    () => import("@/components/admin/UserAdminPanel").then(mod => mod.UserAdminPanel),
    {
        ssr: false,
        loading: () => <PageLoader />,
    },
);

export default function UserAdminPage() {
    return <UserAdminPanel />;
}
