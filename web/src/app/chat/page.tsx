"use client";

import { Toaster } from "@/components/ui/sonner";
import { ChatContainer } from "@/components/chat/ChatContainer";

export default function ChatPage() {
  return (
    <div className="min-h-screen w-full bg-background p-6">
      <Toaster richColors closeButton />
      <div className="mx-auto w-full max-w-6xl">
        <ChatContainer />
      </div>
    </div>
  );
}
