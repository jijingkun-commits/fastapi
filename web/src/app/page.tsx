/**
 * 主页面
 *
 * 使用 dynamic import 并禁用 SSR 来解决 useSearchParams 问题
 */
"use client";

import dynamic from "next/dynamic";

// 动态导入并禁用 SSR，避免服务端渲染时的 useSearchParams 问题
const ChatContainer = dynamic(
  () => import("@/components/chat/ChatContainer").then(mod => mod.ChatContainer),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-screen items-center justify-center bg-gray-50/50">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
          <span className="text-sm text-gray-500">加载中...</span>
        </div>
      </div>
    ),
  }
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
