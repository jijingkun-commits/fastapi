/**
 * 记忆管理页面。
 */
"use client";

import dynamic from "next/dynamic";

import { PageLoader } from "@/components/ui/page-loader";

const MemoryAdminPanel = dynamic(
  () => import("@/components/admin/MemoryAdminPanel").then((mod) => mod.MemoryAdminPanel),
  {
    ssr: false,
    loading: () => <PageLoader text="正在加载记忆管理面板..." />,
  },
);

export default function MemoryAdminPage() {
  return <MemoryAdminPanel />;
}
