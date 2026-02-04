/**
 * 用户管理面板（中文注释）
 * 
 * 功能：
 * - 用户列表（分页、搜索）
 * - 创建用户
 * - 启用/禁用用户
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  UserListItem,
  UserListResponse,
  CreateUserRequest,
  listUsers,
  createUser,
  updateUserStatus,
  getMe,
} from "@/lib/backend";
import { Search, Plus, Users, ChevronLeft, ChevronRight } from "lucide-react";

export function UserAdminPanel() {
  // 当前登录用户 ID（用于自我禁用保护）
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);

  // 用户列表状态
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  // 创建用户对话框
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newUser, setNewUser] = useState<CreateUserRequest>({
    username: "",
    password: "",
    mobile: "",
    role: "user",
    org_code: "",
    org_name: "",
    dept_code: "",
    dept_name: "",
  });

  // 状态确认对话框
  const [statusConfirm, setStatusConfirm] = useState<{
    user: UserListItem;
    newStatus: boolean;
  } | null>(null);

  // 加载用户列表
  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data: UserListResponse = await listUsers(page, pageSize, search || undefined);
      setUsers(data.items);
      setTotal(data.total);
    } catch (e: any) {
      toast.error(e.message || "加载用户列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // 获取当前登录用户 ID
  useEffect(() => {
    const fetchCurrentUser = async () => {
      try {
        const me = await getMe();
        setCurrentUserId(me.id);
      } catch {
        // 忽略错误
      }
    };
    fetchCurrentUser();
  }, []);

  // 搜索处理
  const handleSearch = () => {
    setPage(1);
    loadUsers();
  };

  // 创建用户
  const handleCreateUser = async () => {
    if (!newUser.username || !newUser.password) {
      toast.error("用户名和密码为必填项");
      return;
    }
    if (newUser.password.length < 6) {
      toast.error("密码至少6位");
      return;
    }

    setCreating(true);
    try {
      await createUser(newUser);
      toast.success("用户创建成功");
      setCreateDialogOpen(false);
      setNewUser({
        username: "",
        password: "",
        mobile: "",
        role: "user",
        org_code: "",
        org_name: "",
        dept_code: "",
        dept_name: "",
      });
      loadUsers();
    } catch (e: any) {
      toast.error(e.message || "创建用户失败");
    } finally {
      setCreating(false);
    }
  };

  // 更新用户状态
  const handleStatusChange = async () => {
    if (!statusConfirm) return;
    
    try {
      await updateUserStatus(statusConfirm.user.id, statusConfirm.newStatus);
      toast.success(statusConfirm.newStatus ? "用户已启用" : "用户已禁用");
      loadUsers();
    } catch (e: any) {
      toast.error(e.message || "更新状态失败");
    } finally {
      setStatusConfirm(null);
    }
  };

  // 角色标签颜色
  const getRoleBadgeVariant = (role: string | null) => {
    switch (role) {
      case "admin": return "destructive";
      case "analyst": return "secondary";
      default: return "outline";
    }
  };

  // 角色显示名称
  const getRoleLabel = (role: string | null) => {
    switch (role) {
      case "admin": return "管理员";
      case "analyst": return "分析师";
      default: return "普通用户";
    }
  };

  // 分页
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-6 w-6" />
              <div>
                <CardTitle>用户管理</CardTitle>
                <CardDescription>管理系统用户账户</CardDescription>
              </div>
            </div>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              创建用户
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* 搜索栏 */}
          <div className="flex gap-2 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索用户名或手机号..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="pl-10"
              />
            </div>
            <Button variant="outline" onClick={handleSearch}>
              搜索
            </Button>
          </div>

          {/* 用户表格 */}
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[80px]">ID</TableHead>
                  <TableHead>用户名</TableHead>
                  <TableHead>手机号</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>机构</TableHead>
                  <TableHead>部门</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="w-[100px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">
                      <div className="flex items-center justify-center gap-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                        加载中...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      暂无用户数据
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-mono">{user.id}</TableCell>
                      <TableCell className="font-medium">{user.username || "-"}</TableCell>
                      <TableCell>{user.mobile || "-"}</TableCell>
                      <TableCell>
                        <Badge variant={getRoleBadgeVariant(user.role)}>
                          {getRoleLabel(user.role)}
                        </Badge>
                      </TableCell>
                      <TableCell>{user.org_name || "-"}</TableCell>
                      <TableCell>{user.dept_name || "-"}</TableCell>
                      <TableCell>
                        <Badge variant={user.is_active ? "default" : "secondary"}>
                          {user.is_active ? "启用" : "禁用"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {user.create_time
                          ? new Date(user.create_time).toLocaleDateString("zh-CN")
                          : "-"}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={user.is_active}
                          disabled={user.id === currentUserId}
                          onCheckedChange={(checked) => {
                            if (user.id === currentUserId) {
                              toast.error("不能禁用自己的账户");
                              return;
                            }
                            setStatusConfirm({ user, newStatus: checked });
                          }}
                        />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <div className="text-sm text-muted-foreground">
                共 {total} 条记录，第 {page}/{totalPages} 页
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  下一页
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 创建用户对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>创建用户</DialogTitle>
            <DialogDescription>
              填写用户信息以创建新账户
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="username">用户名 *</Label>
              <Input
                id="username"
                value={newUser.username}
                onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                placeholder="请输入用户名"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password">密码 *</Label>
              <Input
                id="password"
                type="password"
                value={newUser.password}
                onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                placeholder="请输入密码（至少6位）"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="mobile">手机号</Label>
              <Input
                id="mobile"
                value={newUser.mobile}
                onChange={(e) => setNewUser({ ...newUser, mobile: e.target.value })}
                placeholder="请输入手机号"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="role">角色</Label>
              <Select
                value={newUser.role}
                onValueChange={(v) => setNewUser({ ...newUser, role: v as any })}
              >
                <SelectTrigger id="role" aria-label="角色">
                  <SelectValue placeholder="选择角色" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">普通用户</SelectItem>
                  <SelectItem value="analyst">分析师</SelectItem>
                  <SelectItem value="admin">管理员</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="org_code">机构代码</Label>
                <Input
                  id="org_code"
                  value={newUser.org_code}
                  onChange={(e) => setNewUser({ ...newUser, org_code: e.target.value })}
                  placeholder="机构代码"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="org_name">机构名称</Label>
                <Input
                  id="org_name"
                  value={newUser.org_name}
                  onChange={(e) => setNewUser({ ...newUser, org_name: e.target.value })}
                  placeholder="机构名称"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="dept_code">部门代码</Label>
                <Input
                  id="dept_code"
                  value={newUser.dept_code}
                  onChange={(e) => setNewUser({ ...newUser, dept_code: e.target.value })}
                  placeholder="部门代码"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="dept_name">部门名称</Label>
                <Input
                  id="dept_name"
                  value={newUser.dept_name}
                  onChange={(e) => setNewUser({ ...newUser, dept_name: e.target.value })}
                  placeholder="部门名称"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreateUser} disabled={creating}>
              {creating ? "创建中..." : "创建"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 状态确认对话框 */}
      <AlertDialog open={!!statusConfirm} onOpenChange={() => setStatusConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {statusConfirm?.newStatus ? "启用用户" : "禁用用户"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {statusConfirm?.newStatus
                ? `确定要启用用户 "${statusConfirm?.user.username}" 吗？启用后该用户可以正常登录系统。`
                : `确定要禁用用户 "${statusConfirm?.user.username}" 吗？禁用后该用户将无法登录系统，且当前登录会话将失效。`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleStatusChange}>
              确定
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
