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
import { Toaster } from "@/components/ui/sonner";

const UserAdminPanel = dynamic(
    () => import("@/components/admin/UserAdminPanel").then(mod => mod.UserAdminPanel),
    {
        ssr: false,
        loading: () => (
            <div className="flex h-screen items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
                    <span className="text-sm text-gray-500">加载中...</span>
                </div>
            </div>
        ),
    }
);

export default function UserAdminPage() {
    return (
        <div className="min-h-screen w-full bg-background">
            <Toaster richColors closeButton />
            <UserAdminPanel />
        </div>
    );
}
