"use client";

import { useState } from "react";
import { login, getMe } from "@/lib/backend";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function LoginCard() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [meInfo, setMeInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const onLogin = async () => {
    setLoading(true);
    try {
      const isMobile = /^\d{11}$/.test(identifier);
      const payload = isMobile ? { mobile: identifier, password } : { username: identifier, password };
      const data = await login(payload);
      setToken(data.access_token);
      toast.success("登录成功");
    } catch (e: any) {
      toast.error(e?.message || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  const onMe = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await getMe(token);
      setMeInfo(data);
      toast.success("已获取用户信息");
    } catch (e: any) {
      toast.error(e?.message || "获取失败");
    } finally {
      setLoading(false);
    }
  };

  const onLogout = () => {
    setToken(null);
    setMeInfo(null);
    setIdentifier("");
    setPassword("");
    toast("已退出登录");
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>登录到系统</CardTitle>
          <CardDescription>请输入用户名或手机号进行登录</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="identifier">账号</Label>
            <Input id="identifier" value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="用户名或11位手机号" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">密码</Label>
            <PasswordInput id="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="请输入密码" />
          </div>
        </CardContent>
        <CardFooter className="justify-between">
          <Button variant="outline" onClick={onLogout} disabled={!token}>退出登录</Button>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onMe} disabled={!token || loading}>获取 /me</Button>
            <Button variant="brand" onClick={onLogin} disabled={loading}>{loading ? "处理中…" : "登录"}</Button>
          </div>
        </CardFooter>
      </Card>

      {token && (
        <Card>
          <CardHeader>
            <CardTitle>当前令牌</CardTitle>
            <CardDescription>请求受保护接口时使用</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-xs break-all bg-muted rounded-md p-3">{token}</div>
          </CardContent>
        </Card>
      )}

      {meInfo && (
        <Card>
          <CardHeader>
            <CardTitle>当前用户信息</CardTitle>
            <CardDescription>来自 /api/v1/me</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="text-sm whitespace-pre-wrap">{JSON.stringify(meInfo, null, 2)}</pre>
          </CardContent>
        </Card>
      )}
    </>
  );
}

