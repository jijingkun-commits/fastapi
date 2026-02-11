/**
 * 主页面
 *
 * 使用 dynamic import 并禁用 SSR 来解决 useSearchParams 问题
 */
"use client";

import dynamic from "next/dynamic";
import { PageLoader } from "@/components/ui/page-loader";

// 动态导入并禁用 SSR，避免服务端渲染时的 useSearchParams 问题
const ChatContainer = dynamic(
  () => import("@/components/chat/ChatContainer").then(mod => mod.ChatContainer),
  {
    ssr: false,
    loading: () => <PageLoader />,
  },
);

export default function Home() {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50/50">
      <div className="flex-1 overflow-hidden relative">
        <ChatContainer />
      </div>
    </div>
  );
}
