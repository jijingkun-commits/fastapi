"use client";

import { Toaster } from "@/components/ui/sonner";
import { LoginCard } from "@/components/auth/LoginCard";
import { SseCard } from "@/components/llm/SseCard";

export default function AuthPage() {
  return (
    <div className="min-h-screen w-full bg-background p-6">
      <Toaster richColors closeButton />
      <div className="mx-auto w-full max-w-6xl grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LoginCard />
        <SseCard />
      </div>
    </div>
  );
}
