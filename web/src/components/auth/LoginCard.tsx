"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/backend";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function LoginCard() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onLogin = async () => {
    if (!identifier.trim()) {
      toast.error("请输入账号");
      return;
    }

    setLoading(true);
    try {
      const isMobile = /^\d{11}$/.test(identifier);
      const payload = isMobile ? { mobile: identifier, password } : { username: identifier, password };
      const data = await login(payload);
      try {
        // 使用 sessionStorage 存储 token，会话级别安全性更高
        window.sessionStorage.setItem("auth:token", data.access_token);
      } catch (e) {
        console.warn("写入令牌失败", e);
      }
      toast.success("登录成功");
      // 登录成功后跳转到 /chat
      router.push("/chat");
    } catch (e: any) {
      toast.error(e?.message || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md shadow-lg">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl font-bold">登录到系统</CardTitle>
        <CardDescription>开发环境：只需输入账号即可登录</CardDescription>
      </CardHeader>
      <form onSubmit={(e) => { e.preventDefault(); onLogin(); }}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="identifier">账号</Label>
            <Input
              id="identifier"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="用户名或11位手机号"
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">密码 <span className="text-muted-foreground text-xs">(开发环境可选)</span></Label>
            <PasswordInput
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="开发环境下可留空"
            />
          </div>
        </CardContent>
        <CardFooter>
          <Button
            type="submit"
            variant="brand"
            className="w-full"
            disabled={loading}
          >
            {loading ? "登录中…" : "登录"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
