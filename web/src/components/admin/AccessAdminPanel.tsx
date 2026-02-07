/**
 * 数据访问控制管理面板（中文注释）
 * 
 * 功能：
 * - 表白名单管理
 * - 表黑名单管理
 * - Schema 白名单管理
 * - SQL 权限测试
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  X,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldX,
  Database,
  TableProperties,
  FlaskConical,
  ListChecks,
  Info,
} from "lucide-react";
import {
  AccessConfig,
  SQLTestResult,
  AvailableTable,
  getAccessConfig,
  updateTableWhitelist,
  updateTableBlacklist,
  updateSchemaWhitelist,
  testSQLAccess,
  getAvailableTables,
} from "@/lib/access-admin-api";

export function AccessAdminPanel() {
  // 状态
  const [config, setConfig] = useState<AccessConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // 编辑状态
  const [editedWhitelist, setEditedWhitelist] = useState<string[]>([]);
  const [editedBlacklist, setEditedBlacklist] = useState<string[]>([]);
  const [editedSchemas, setEditedSchemas] = useState<string[]>([]);
  
  // 新增输入
  const [newWhitelistTable, setNewWhitelistTable] = useState("");
  const [newBlacklistTable, setNewBlacklistTable] = useState("");
  const [newSchema, setNewSchema] = useState("");
  
  // SQL 测试
  const [testSQL, setTestSQL] = useState("");
  const [testResult, setTestResult] = useState<SQLTestResult | null>(null);
  const [testing, setTesting] = useState(false);
  
  // 可用表
  const [availableTables, setAvailableTables] = useState<AvailableTable[]>([]);
  const [loadingTables, setLoadingTables] = useState(false);

  // 加载配置
  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAccessConfig();
      setConfig(data);
      setEditedWhitelist(data.whitelist);
      setEditedBlacklist(data.blacklist);
      setEditedSchemas(data.schema_whitelist);
    } catch (e: any) {
      toast.error(e.message || "加载配置失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  // 加载可用表
  const loadAvailableTables = async () => {
    setLoadingTables(true);
    try {
      const data = await getAvailableTables();
      setAvailableTables(data.tables);
    } catch (e: any) {
      toast.error(e.message || "加载可用表失败");
    } finally {
      setLoadingTables(false);
    }
  };

  // 保存白名单
  const saveWhitelist = async () => {
    setSaving(true);
    try {
      await updateTableWhitelist(editedWhitelist);
      toast.success("白名单已保存");
      loadConfig();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  // 保存黑名单
  const saveBlacklist = async () => {
    setSaving(true);
    try {
      await updateTableBlacklist(editedBlacklist);
      toast.success("黑名单已保存");
      loadConfig();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  // 保存 Schema 白名单
  const saveSchemas = async () => {
    setSaving(true);
    try {
      await updateSchemaWhitelist(editedSchemas);
      toast.success("Schema 白名单已保存");
      loadConfig();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  // 添加到白名单
  const addToWhitelist = () => {
    if (!newWhitelistTable.trim()) return;
    const table = newWhitelistTable.trim().toLowerCase();
    if (!editedWhitelist.includes(table)) {
      setEditedWhitelist([...editedWhitelist, table].sort());
    }
    setNewWhitelistTable("");
  };

  // 从白名单移除
  const removeFromWhitelist = (table: string) => {
    setEditedWhitelist(editedWhitelist.filter(t => t !== table));
  };

  // 添加到黑名单
  const addToBlacklist = () => {
    if (!newBlacklistTable.trim()) return;
    const table = newBlacklistTable.trim().toLowerCase();
    if (!editedBlacklist.includes(table)) {
      setEditedBlacklist([...editedBlacklist, table].sort());
    }
    setNewBlacklistTable("");
  };

  // 从黑名单移除
  const removeFromBlacklist = (table: string) => {
    setEditedBlacklist(editedBlacklist.filter(t => t !== table));
  };

  // 添加 Schema
  const addSchema = () => {
    if (!newSchema.trim()) return;
    const schema = newSchema.trim().toLowerCase();
    if (!editedSchemas.includes(schema)) {
      setEditedSchemas([...editedSchemas, schema].sort());
    }
    setNewSchema("");
  };

  // 移除 Schema
  const removeSchema = (schema: string) => {
    setEditedSchemas(editedSchemas.filter(s => s !== schema));
  };

  // 测试 SQL
  const handleTestSQL = async () => {
    if (!testSQL.trim()) {
      toast.error("请输入 SQL 语句");
      return;
    }
    
    setTesting(true);
    setTestResult(null);
    
    try {
      const result = await testSQLAccess(testSQL);
      setTestResult(result);
      if (result.is_valid) {
        toast.success("SQL 权限检查通过");
      } else {
        toast.error(result.error || "权限检查失败");
      }
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setTesting(false);
    }
  };

  // 快速添加表到白名单
  const quickAddToWhitelist = (table: AvailableTable) => {
    const tableName = table.table.toLowerCase();
    if (!editedWhitelist.includes(tableName)) {
      setEditedWhitelist([...editedWhitelist, tableName].sort());
      toast.success(`已添加 ${tableName} 到白名单（需保存）`);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#A8D4D4] border-t-[#2F6868]" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">数据访问控制</h1>
          <p className="text-sm text-muted-foreground mt-1">管理 AI 问数功能的数据库访问权限</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadConfig} className="gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" />
          刷新
        </Button>
      </div>

      <Tabs defaultValue="whitelist" className="space-y-4">
        <TabsList className="h-10">
          <TabsTrigger value="whitelist" className="gap-1.5 text-sm">
            <ShieldCheck className="h-3.5 w-3.5" />
            表白名单
          </TabsTrigger>
          <TabsTrigger value="blacklist" className="gap-1.5 text-sm">
            <ShieldX className="h-3.5 w-3.5" />
            表黑名单
          </TabsTrigger>
          <TabsTrigger value="schemas" className="gap-1.5 text-sm">
            <Database className="h-3.5 w-3.5" />
            Schema 白名单
          </TabsTrigger>
          <TabsTrigger value="test" className="gap-1.5 text-sm">
            <FlaskConical className="h-3.5 w-3.5" />
            SQL 测试
          </TabsTrigger>
          <TabsTrigger value="tables" onClick={loadAvailableTables} className="gap-1.5 text-sm">
            <TableProperties className="h-3.5 w-3.5" />
            可用表
          </TabsTrigger>
        </TabsList>

        {/* 表白名单 */}
        <TabsContent value="whitelist">
          <Card>
            <CardHeader className="pb-4">
              <div className="flex items-center gap-2">
                <CardTitle className="text-lg">表白名单</CardTitle>
                {config?.whitelist_source === "default" && (
                  <Badge variant="outline" className="text-xs font-normal gap-1">
                    <Info className="h-3 w-3" />
                    默认配置
                  </Badge>
                )}
              </div>
              <CardDescription>
                只允许 AI 查询白名单中的表
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex gap-2">
                <Input
                  placeholder="输入表名（如 t_orders）"
                  value={newWhitelistTable}
                  onChange={(e) => setNewWhitelistTable(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addToWhitelist()}
                  className="font-mono text-sm"
                />
                <Button onClick={addToWhitelist} size="sm" className="gap-1 shrink-0 px-4">
                  <Plus className="h-3.5 w-3.5" />
                  添加
                </Button>
              </div>

              {editedWhitelist.length > 0 ? (
                <div className="rounded-lg border bg-muted/30 p-3">
                  <div className="flex flex-wrap gap-2">
                    {editedWhitelist.map((table) => (
                      <span
                        key={table}
                        className="group inline-flex items-center gap-1 rounded-md border bg-background px-2.5 py-1 text-sm font-mono text-foreground shadow-sm transition-colors hover:border-destructive/50 hover:bg-destructive/5"
                      >
                        {table}
                        <button
                          onClick={() => removeFromWhitelist(table)}
                          className="ml-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-sm text-muted-foreground/60 transition-colors hover:bg-destructive/15 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                  <p className="mt-2.5 text-xs text-muted-foreground">
                    共 {editedWhitelist.length} 个表，点击 <X className="inline h-3 w-3" /> 可移除
                  </p>
                </div>
              ) : (
                <div className="flex items-center justify-center rounded-lg border border-dashed py-8">
                  <div className="text-center">
                    <ListChecks className="mx-auto h-8 w-8 text-muted-foreground/40" />
                    <p className="mt-2 text-sm text-muted-foreground">暂无白名单表</p>
                    <p className="text-xs text-muted-foreground/60">在上方输入表名添加</p>
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2 border-t">
                <Button onClick={saveWhitelist} disabled={saving} size="sm">
                  {saving ? "保存中..." : "保存白名单"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 表黑名单 */}
        <TabsContent value="blacklist">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg">表黑名单</CardTitle>
              <CardDescription>
                绝对禁止 AI 访问的表（优先级高于白名单）
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex gap-2">
                <Input
                  placeholder="输入表名（如 t_user）"
                  value={newBlacklistTable}
                  onChange={(e) => setNewBlacklistTable(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addToBlacklist()}
                  className="font-mono text-sm"
                />
                <Button onClick={addToBlacklist} size="sm" className="gap-1 shrink-0 px-4">
                  <Plus className="h-3.5 w-3.5" />
                  添加
                </Button>
              </div>

              {editedBlacklist.length > 0 ? (
                <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3">
                  <div className="flex flex-wrap gap-2">
                    {editedBlacklist.map((table) => (
                      <span
                        key={table}
                        className="group inline-flex items-center gap-1 rounded-md border border-destructive/30 bg-background px-2.5 py-1 text-sm font-mono text-destructive shadow-sm transition-colors hover:bg-destructive/10"
                      >
                        {table}
                        <button
                          onClick={() => removeFromBlacklist(table)}
                          className="ml-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-sm text-destructive/50 transition-colors hover:bg-destructive/20 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                  <p className="mt-2.5 text-xs text-muted-foreground">
                    共 {editedBlacklist.length} 个表
                  </p>
                </div>
              ) : (
                <div className="flex items-center justify-center rounded-lg border border-dashed py-8">
                  <div className="text-center">
                    <ShieldX className="mx-auto h-8 w-8 text-muted-foreground/40" />
                    <p className="mt-2 text-sm text-muted-foreground">暂无黑名单表</p>
                    <p className="text-xs text-muted-foreground/60">在上方输入表名添加</p>
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2 border-t">
                <Button onClick={saveBlacklist} disabled={saving} size="sm">
                  {saving ? "保存中..." : "保存黑名单"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Schema 白名单 */}
        <TabsContent value="schemas">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg">Schema 白名单</CardTitle>
              <CardDescription>
                允许访问整个 Schema 下的所有表（如 information_schema）
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex gap-2">
                <Input
                  placeholder="输入 Schema 名（如 public）"
                  value={newSchema}
                  onChange={(e) => setNewSchema(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addSchema()}
                  className="font-mono text-sm"
                />
                <Button onClick={addSchema} size="sm" className="gap-1 shrink-0 px-4">
                  <Plus className="h-3.5 w-3.5" />
                  添加
                </Button>
              </div>

              {editedSchemas.length > 0 ? (
                <div className="rounded-lg border bg-muted/30 p-3">
                  <div className="flex flex-wrap gap-2">
                    {editedSchemas.map((schema) => (
                      <span
                        key={schema}
                        className="group inline-flex items-center gap-1 rounded-md border bg-background px-2.5 py-1 text-sm font-mono text-foreground shadow-sm transition-colors hover:border-destructive/50 hover:bg-destructive/5"
                      >
                        {schema}
                        <button
                          onClick={() => removeSchema(schema)}
                          className="ml-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-sm text-muted-foreground/60 transition-colors hover:bg-destructive/15 hover:text-destructive"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                  <p className="mt-2.5 text-xs text-muted-foreground">
                    共 {editedSchemas.length} 个 Schema
                  </p>
                </div>
              ) : (
                <div className="flex items-center justify-center rounded-lg border border-dashed py-8">
                  <div className="text-center">
                    <Database className="mx-auto h-8 w-8 text-muted-foreground/40" />
                    <p className="mt-2 text-sm text-muted-foreground">暂无 Schema 白名单</p>
                    <p className="text-xs text-muted-foreground/60">在上方输入 Schema 名添加</p>
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2 border-t">
                <Button onClick={saveSchemas} disabled={saving} size="sm">
                  {saving ? "保存中..." : "保存 Schema 白名单"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* SQL 测试 */}
        <TabsContent value="test">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg">SQL 权限测试</CardTitle>
              <CardDescription>
                测试 SQL 语句是否能通过权限检查（不实际执行）
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="输入 SQL 语句，如 SELECT * FROM t_orders WHERE ..."
                value={testSQL}
                onChange={(e) => setTestSQL(e.target.value)}
                rows={4}
                className="font-mono text-sm resize-none"
              />

              <Button onClick={handleTestSQL} disabled={testing} size="sm" className="gap-1.5">
                <FlaskConical className="h-3.5 w-3.5" />
                {testing ? "检查中..." : "检查权限"}
              </Button>

              {testResult && (
                <div className={`mt-4 rounded-lg border p-4 space-y-3 ${
                  testResult.is_valid
                    ? "border-green-200 bg-green-50 dark:border-green-900/50 dark:bg-green-950/20"
                    : "border-destructive/30 bg-destructive/5"
                }`}>
                  <div className="flex items-center gap-2">
                    {testResult.is_valid ? (
                      <ShieldCheck className="h-4.5 w-4.5 text-green-600 dark:text-green-400" />
                    ) : (
                      <ShieldX className="h-4.5 w-4.5 text-destructive" />
                    )}
                    <span className={`text-sm font-medium ${
                      testResult.is_valid
                        ? "text-green-700 dark:text-green-300"
                        : "text-destructive"
                    }`}>
                      {testResult.is_valid ? "权限检查通过" : "权限检查拒绝"}
                    </span>
                    {testResult.error && (
                      <span className="text-sm text-destructive/80">- {testResult.error}</span>
                    )}
                  </div>

                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1.5">检测到的表：</p>
                    <div className="flex flex-wrap gap-1.5">
                      {testResult.tables_found.map((table) => (
                        <span
                          key={table}
                          className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-mono ${
                            testResult.tables_allowed.includes(table)
                              ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
                              : "bg-destructive/10 text-destructive"
                          }`}
                        >
                          {table}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 可用表 */}
        <TabsContent value="tables">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg">业务数据库可用表</CardTitle>
              <CardDescription>
                点击"加入白名单"可快速添加（添加后需在白名单 Tab 保存）
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingTables ? (
                <div className="flex justify-center py-12">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#A8D4D4] border-t-[#2F6868]" />
                </div>
              ) : availableTables.length > 0 ? (
                <div className="rounded-lg border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="w-[140px]">Schema</TableHead>
                        <TableHead>表名</TableHead>
                        <TableHead className="w-[120px]">状态</TableHead>
                        <TableHead className="w-[120px] text-right">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {availableTables.map((table) => (
                        <TableRow key={table.full_name} className="group">
                          <TableCell className="text-muted-foreground text-sm">{table.schema}</TableCell>
                          <TableCell className="font-mono text-sm">{table.table}</TableCell>
                          <TableCell>
                            {editedWhitelist.includes(table.table.toLowerCase()) ? (
                              <span className="inline-flex items-center gap-1 rounded-md bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/40 dark:text-green-300">
                                <ShieldCheck className="h-3 w-3" />
                                已加白名单
                              </span>
                            ) : editedBlacklist.includes(table.table.toLowerCase()) ? (
                              <span className="inline-flex items-center gap-1 rounded-md bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">
                                <ShieldX className="h-3 w-3" />
                                黑名单
                              </span>
                            ) : (
                              <span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                                未配置
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            {!editedWhitelist.includes(table.table.toLowerCase()) &&
                             !editedBlacklist.includes(table.table.toLowerCase()) && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                                onClick={() => quickAddToWhitelist(table)}
                              >
                                <Plus className="h-3 w-3" />
                                加入白名单
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="flex items-center justify-center rounded-lg border border-dashed py-12">
                  <div className="text-center">
                    <Database className="mx-auto h-10 w-10 text-muted-foreground/30" />
                    <p className="mt-3 text-sm text-muted-foreground">暂无数据</p>
                    <p className="text-xs text-muted-foreground/60">请先连接业务数据库</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
