/**
 * 管理后台总览驾驶舱页面。
 */
"use client";

import dynamic from "next/dynamic";

import { PageLoader } from "@/components/ui/page-loader";

const AdminOverviewCockpit = dynamic(
  () =>
    import("@/components/admin/overview").then(
      (mod) => mod.AdminOverviewCockpit,
    ),
  {
    ssr: false,
    loading: () => <PageLoader text="正在加载总览驾驶舱..." />,
  },
);

export default function AdminPage() {
  return <AdminOverviewCockpit />;
}
