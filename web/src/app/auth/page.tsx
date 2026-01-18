"use client";

import { Toaster } from "@/components/ui/sonner";
import { LoginCard } from "@/components/auth/LoginCard";

export default function AuthPage() {
  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-6">
      <Toaster richColors closeButton />
      <LoginCard />
    </div>
  );
}
