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
          <h1 className="text-2xl font-bold">数据访问控制</h1>
          <p className="text-muted-foreground">管理 AI 问数功能的数据库访问权限</p>
        </div>
        <Button variant="outline" onClick={loadConfig}>
          刷新
        </Button>
      </div>

      <Tabs defaultValue="whitelist" className="space-y-4">
        <TabsList>
          <TabsTrigger value="whitelist">表白名单</TabsTrigger>
          <TabsTrigger value="blacklist">表黑名单</TabsTrigger>
          <TabsTrigger value="schemas">Schema 白名单</TabsTrigger>
          <TabsTrigger value="test">SQL 测试</TabsTrigger>
          <TabsTrigger value="tables" onClick={loadAvailableTables}>可用表</TabsTrigger>
        </TabsList>

        {/* 表白名单 */}
        <TabsContent value="whitelist">
          <Card>
            <CardHeader>
              <CardTitle>表白名单</CardTitle>
              <CardDescription>
                只允许 AI 查询白名单中的表。
                {config?.whitelist_source === "default" && (
                  <Badge variant="outline" className="ml-2">使用默认配置</Badge>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="输入表名（如 t_orders）"
                  value={newWhitelistTable}
                  onChange={(e) => setNewWhitelistTable(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addToWhitelist()}
                />
                <Button onClick={addToWhitelist}>添加</Button>
              </div>
              
              <div className="flex flex-wrap gap-2">
                {editedWhitelist.map((table) => (
                  <Badge
                    key={table}
                    variant="secondary"
                    className="cursor-pointer hover:bg-destructive hover:text-destructive-foreground"
                    onClick={() => removeFromWhitelist(table)}
                  >
                    {table} ×
                  </Badge>
                ))}
                {editedWhitelist.length === 0 && (
                  <span className="text-muted-foreground text-sm">暂无白名单表</span>
                )}
              </div>

              <div className="flex justify-end">
                <Button onClick={saveWhitelist} disabled={saving}>
                  {saving ? "保存中..." : "保存白名单"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 表黑名单 */}
        <TabsContent value="blacklist">
          <Card>
            <CardHeader>
              <CardTitle>表黑名单</CardTitle>
              <CardDescription>
                绝对禁止 AI 访问的表（优先级高于白名单）
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="输入表名（如 t_user）"
                  value={newBlacklistTable}
                  onChange={(e) => setNewBlacklistTable(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addToBlacklist()}
                />
                <Button onClick={addToBlacklist}>添加</Button>
              </div>
              
              <div className="flex flex-wrap gap-2">
                {editedBlacklist.map((table) => (
                  <Badge
                    key={table}
                    variant="destructive"
                    className="cursor-pointer"
                    onClick={() => removeFromBlacklist(table)}
                  >
                    {table} ×
                  </Badge>
                ))}
              </div>

              <div className="flex justify-end">
                <Button onClick={saveBlacklist} disabled={saving}>
                  {saving ? "保存中..." : "保存黑名单"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Schema 白名单 */}
        <TabsContent value="schemas">
          <Card>
            <CardHeader>
              <CardTitle>Schema 白名单</CardTitle>
              <CardDescription>
                允许访问整个 Schema 下的所有表（如 information_schema）
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="输入 Schema 名（如 public）"
                  value={newSchema}
                  onChange={(e) => setNewSchema(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addSchema()}
                />
                <Button onClick={addSchema}>添加</Button>
              </div>
              
              <div className="flex flex-wrap gap-2">
                {editedSchemas.map((schema) => (
                  <Badge
                    key={schema}
                    variant="outline"
                    className="cursor-pointer hover:bg-destructive hover:text-destructive-foreground"
                    onClick={() => removeSchema(schema)}
                  >
                    {schema} ×
                  </Badge>
                ))}
              </div>

              <div className="flex justify-end">
                <Button onClick={saveSchemas} disabled={saving}>
                  {saving ? "保存中..." : "保存 Schema 白名单"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* SQL 测试 */}
        <TabsContent value="test">
          <Card>
            <CardHeader>
              <CardTitle>SQL 权限测试</CardTitle>
              <CardDescription>
                测试 SQL 语句是否能通过权限检查（不实际执行）
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="输入 SQL 语句..."
                value={testSQL}
                onChange={(e) => setTestSQL(e.target.value)}
                rows={4}
                className="font-mono text-sm"
              />
              
              <Button onClick={handleTestSQL} disabled={testing}>
                {testing ? "检查中..." : "检查权限"}
              </Button>

              {testResult && (
                <div className="mt-4 p-4 rounded-lg border space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant={testResult.is_valid ? "default" : "destructive"}>
                      {testResult.is_valid ? "通过" : "拒绝"}
                    </Badge>
                    {testResult.error && (
                      <span className="text-sm text-destructive">{testResult.error}</span>
                    )}
                  </div>
                  
                  <div>
                    <p className="text-sm font-medium mb-1">检测到的表：</p>
                    <div className="flex flex-wrap gap-1">
                      {testResult.tables_found.map((table) => (
                        <Badge
                          key={table}
                          variant={testResult.tables_allowed.includes(table) ? "secondary" : "destructive"}
                        >
                          {table}
                        </Badge>
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
            <CardHeader>
              <CardTitle>业务数据库可用表</CardTitle>
              <CardDescription>
                点击表名可快速添加到白名单
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingTables ? (
                <div className="flex justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#A8D4D4] border-t-[#2F6868]" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Schema</TableHead>
                      <TableHead>表名</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {availableTables.map((table) => (
                      <TableRow key={table.full_name}>
                        <TableCell>{table.schema}</TableCell>
                        <TableCell className="font-mono">{table.table}</TableCell>
                        <TableCell>
                          {editedWhitelist.includes(table.table.toLowerCase()) ? (
                            <Badge variant="default">已加白名单</Badge>
                          ) : editedBlacklist.includes(table.table.toLowerCase()) ? (
                            <Badge variant="destructive">黑名单</Badge>
                          ) : (
                            <Badge variant="outline">未配置</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {!editedWhitelist.includes(table.table.toLowerCase()) && 
                           !editedBlacklist.includes(table.table.toLowerCase()) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => quickAddToWhitelist(table)}
                            >
                              加入白名单
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                    {availableTables.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center text-muted-foreground">
                          暂无数据，请先连接业务数据库
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
