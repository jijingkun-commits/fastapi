"use client";

import { Suspense } from "react";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import { ArtifactProvider } from "@/components/chat/artifact";
import { ThreadProvider } from "@/providers/Thread";
import { StreamProvider } from "@/providers/Stream";
import { Thread } from "@/components/chat";

// 加载状态组件
function LoadingFallback() {
  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
        <span className="text-sm text-gray-500">加载中...</span>
      </div>
    </div>
  );
}

export function ChatContainer() {
  return (
    <NuqsAdapter>
      <Suspense fallback={<LoadingFallback />}>
        <ArtifactProvider>
          <ThreadProvider>
            <StreamProvider>
              <Thread />
            </StreamProvider>
          </ThreadProvider>
        </ArtifactProvider>
      </Suspense>
    </NuqsAdapter>
  );
}

