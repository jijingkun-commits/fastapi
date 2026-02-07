/**
 * 管理后台共享布局
 *
 * 提供侧边栏导航 + 内容区域的统一布局结构
 */
"use client";

import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { Toaster } from "@/components/ui/sonner";

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex h-screen overflow-hidden bg-background">
            <AdminSidebar />
            <main className="flex-1 overflow-y-auto">
                {children}
            </main>
            <Toaster richColors closeButton />
        </div>
    );
}
