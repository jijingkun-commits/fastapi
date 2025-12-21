"use client";

import Link from "next/link";
import { Toaster } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";

export default function Page() {
  return (
    <div className="min-h-screen w-full bg-background p-6">
      <Toaster richColors closeButton />
      <div className="mx-auto max-w-4xl flex flex-col items-center gap-8 py-12">
        <h1 className="text-2xl font-semibold tracking-tight">主页</h1>
        <p className="text-muted-foreground">请选择功能页面</p>
        <div className="flex items-center gap-4">
          <Link href="/auth">
            <Button size="lg" variant="brand">登录与接口</Button>
          </Link>
          <Link href="/chat">
            <Button size="lg" variant="outline">LangGraph 聊天</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
