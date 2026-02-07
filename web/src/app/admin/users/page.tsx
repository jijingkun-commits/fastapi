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

const UserAdminPanel = dynamic(
    () => import("@/components/admin/UserAdminPanel").then(mod => mod.UserAdminPanel),
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

export default function UserAdminPage() {
    return <UserAdminPanel />;
}
