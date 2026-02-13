/**
 * 用户管理面板
 *
 * 功能：
 * - 用户列表（分页、搜索）
 * - 创建用户
 * - 启用/禁用用户
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Plus, Search, Users } from "lucide-react";
import { toast } from "sonner";

import {
  ApiError,
  CreateUserRequest,
  UserListItem,
  UserListResponse,
  createUser,
  getMe,
  listUsers,
  updateUserStatus,
} from "@/lib/backend";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ViewState } from "@/components/ui/view-state";

type ListViewState = "loading" | "ready" | "empty" | "error" | "forbidden";

const EMPTY_USER: CreateUserRequest = {
  username: "",
  password: "",
  mobile: "",
  role: "user",
  org_code: "",
  org_name: "",
  dept_code: "",
  dept_name: "",
};

export function UserAdminPanel() {
  const router = useRouter();

  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const [viewState, setViewState] = useState<ListViewState>("loading");
  const [loadErrorMessage, setLoadErrorMessage] = useState("");

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newUser, setNewUser] = useState<CreateUserRequest>(EMPTY_USER);

  const [statusConfirm, setStatusConfirm] = useState<{
    user: UserListItem;
    newStatus: boolean;
  } | null>(null);

  const loadUsers = useCallback(async () => {
    setViewState("loading");
    setLoadErrorMessage("");

    try {
      const data: UserListResponse = await listUsers(
        page,
        pageSize,
        searchQuery || undefined,
      );
      setUsers(data.items);
      setTotal(data.total);
      setViewState(data.items.length > 0 ? "ready" : "empty");
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) {
        setViewState("forbidden");
        setLoadErrorMessage("仅管理员可访问用户管理页面。");
        return;
      }

      const message =
        error instanceof Error ? error.message : "加载用户列表失败";
      setLoadErrorMessage(message);
      setViewState("error");
      toast.error(message);
    }
  }, [page, pageSize, searchQuery]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    const fetchCurrentUser = async () => {
      try {
        const me = await getMe();
        setCurrentUserId(me.id);
      } catch {
        setCurrentUserId(null);
      }
    };

    void fetchCurrentUser();
  }, []);

  const handleSearch = () => {
    const nextQuery = searchInput.trim();

    if (page === 1 && searchQuery === nextQuery) {
      void loadUsers();
      return;
    }

    setPage(1);
    setSearchQuery(nextQuery);
  };

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
      setNewUser(EMPTY_USER);

      if (page === 1) {
        await loadUsers();
      } else {
        setPage(1);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "创建用户失败";
      toast.error(message);
    } finally {
      setCreating(false);
    }
  };

  const handleStatusChange = async () => {
    if (!statusConfirm) {
      return;
    }

    try {
      await updateUserStatus(statusConfirm.user.id, statusConfirm.newStatus);
      toast.success(statusConfirm.newStatus ? "用户已启用" : "用户已禁用");
      await loadUsers();
    } catch (error) {
      const message = error instanceof Error ? error.message : "更新状态失败";
      toast.error(message);
    } finally {
      setStatusConfirm(null);
    }
  };

  const getRoleBadgeVariant = (role: string | null) => {
    switch (role) {
      case "admin":
        return "destructive";
      case "analyst":
        return "secondary";
      default:
        return "outline";
    }
  };

  const getRoleLabel = (role: string | null) => {
    switch (role) {
      case "admin":
        return "管理员";
      case "analyst":
        return "分析师";
      default:
        return "普通用户";
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  const renderListArea = () => {
    if (viewState === "loading") {
      return <ViewState type="loading" title="加载用户列表中" />;
    }

    if (viewState === "forbidden") {
      return (
        <ViewState
          type="forbidden"
          title="无法访问用户管理"
          description={loadErrorMessage || "当前账号没有访问权限。"}
          actionLabel="返回管理首页"
          onAction={() => router.push("/admin")}
        />
      );
    }

    if (viewState === "error") {
      return (
        <ViewState
          type="error"
          title="用户列表加载失败"
          description={loadErrorMessage}
          actionLabel="重新加载"
          onAction={() => {
            void loadUsers();
          }}
        />
      );
    }

    if (viewState === "empty") {
      return (
        <ViewState
          type="empty"
          title="暂无用户数据"
          description="请尝试调整搜索条件，或先创建用户。"
          actionLabel="创建用户"
          onAction={() => setCreateDialogOpen(true)}
        />
      );
    }

    return (
      <div className="overflow-hidden rounded-[var(--ds-radius-md)] border border-border/80">
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
            {users.map((user) => (
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
            ))}
          </TableBody>
        </Table>
      </div>
    );
  };

  return (
    <div className="admin-page-content admin-surface space-y-6">
      <Card className="rounded-[var(--ds-radius-md)] border-border/80 shadow-[var(--ds-shadow-1)]">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <Users className="h-6 w-6 text-[var(--color-brand-700)]" />
              <div>
                <CardTitle>用户管理</CardTitle>
                <CardDescription>管理系统用户账户与权限状态</CardDescription>
              </div>
            </div>
            <Button variant="brand" onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              创建用户
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <div className="relative flex-1 min-w-[240px] max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索用户名或手机号..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="pl-10"
              />
            </div>
            <Button variant="outline" onClick={handleSearch}>
              搜索
            </Button>
          </div>

          {renderListArea()}

          {viewState === "ready" && totalPages > 1 ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm text-muted-foreground">
                共 {total} 条记录，第 {page}/{totalPages} 页
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={page === totalPages}
                >
                  下一页
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>创建用户</DialogTitle>
            <DialogDescription>填写用户信息以创建新账户</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="username">用户名 *</Label>
              <Input
                id="username"
                value={newUser.username}
                onChange={(e) =>
                  setNewUser({ ...newUser, username: e.target.value })
                }
                placeholder="请输入用户名"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password">密码 *</Label>
              <Input
                id="password"
                type="password"
                value={newUser.password}
                onChange={(e) =>
                  setNewUser({ ...newUser, password: e.target.value })
                }
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
                onValueChange={(value) =>
                  setNewUser({
                    ...newUser,
                    role: value as CreateUserRequest["role"],
                  })
                }
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
                  onChange={(e) =>
                    setNewUser({ ...newUser, org_code: e.target.value })
                  }
                  placeholder="机构代码"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="org_name">机构名称</Label>
                <Input
                  id="org_name"
                  value={newUser.org_name}
                  onChange={(e) =>
                    setNewUser({ ...newUser, org_name: e.target.value })
                  }
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
                  onChange={(e) =>
                    setNewUser({ ...newUser, dept_code: e.target.value })
                  }
                  placeholder="部门代码"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="dept_name">部门名称</Label>
                <Input
                  id="dept_name"
                  value={newUser.dept_name}
                  onChange={(e) =>
                    setNewUser({ ...newUser, dept_name: e.target.value })
                  }
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

      <AlertDialog
        open={Boolean(statusConfirm)}
        onOpenChange={(open) => {
          if (!open) {
            setStatusConfirm(null);
          }
        }}
      >
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
            <AlertDialogAction onClick={handleStatusChange}>确定</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
