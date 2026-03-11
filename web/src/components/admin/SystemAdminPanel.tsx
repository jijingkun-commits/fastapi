/**
 * 系统配置管理面板（中文注释）
 * 
 * 功能：
 * - 配置列表展示
 * - 配置编辑
 * - 分类筛选
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { AdminCompactStatCard } from "@/components/admin/shared/AdminCompactStatCard";
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
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  SystemConfig,
  ConfigCategory,
  getConfigs,
  getCategories,
  updateConfig,
  refreshCache,
} from "@/lib/system-admin-api";

export function SystemAdminPanel() {
  // 状态
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [categories, setCategories] = useState<ConfigCategory[]>([]);
  const [loading, setLoading] = useState(true);
  
  // 筛选
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchText, setSearchText] = useState("");
  
  // 编辑对话框
  const [editingConfig, setEditingConfig] = useState<SystemConfig | null>(null);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const category = selectedCategory === "all" ? undefined : selectedCategory;
      const [configsData, categoriesData] = await Promise.all([
        getConfigs(category),
        getCategories(),
      ]);
      setConfigs(configsData);
      setCategories(categoriesData);
    } catch (e: any) {
      toast.error(e.message || "加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 筛选配置
  const filteredConfigs = configs.filter(c => {
    if (searchText) {
      const search = searchText.toLowerCase();
      return (
        c.config_key.toLowerCase().includes(search) ||
        (c.description?.toLowerCase().includes(search))
      );
    }
    return true;
  });

  // 打开编辑
  const handleEdit = (config: SystemConfig) => {
    if (config.is_readonly) {
      toast.error("该配置为只读，无法修改");
      return;
    }
    setEditingConfig(config);
    setEditValue(config.is_secret ? "" : config.config_value);
  };

  // 保存编辑
  const handleSave = async () => {
    if (!editingConfig || !editValue.trim()) return;
    
    setSaving(true);
    try {
      await updateConfig(editingConfig.config_key, editValue);
      toast.success("配置已更新");
      setEditingConfig(null);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  // 刷新缓存
  const handleRefreshCache = async () => {
    try {
      const result = await refreshCache();
      toast.success(`缓存已刷新，共 ${result.count} 个配置`);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // 值类型标签
  const getTypeBadge = (type: string) => {
    const variants: Record<string, "default" | "secondary" | "outline"> = {
      string: "outline",
      number: "secondary",
      boolean: "default",
      json: "secondary",
    };
    return <Badge variant={variants[type] || "outline"}>{type}</Badge>;
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#A8D4D4] border-t-[#2F6868]" />
      </div>
    );
  }

  return (
    <div className="admin-page-content space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="app-page-title">系统配置</h1>
          <p className="app-page-subtitle">管理系统运行参数和配置项</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleRefreshCache}>
            刷新缓存
          </Button>
          <Button variant="outline" onClick={loadData}>
            刷新列表
          </Button>
        </div>
      </div>

      {/* 分类摘要 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground">分类摘要</h2>
            <p className="text-xs text-muted-foreground">点击分类即可筛选下方配置列表，摘要区保持紧凑展示。</p>
          </div>
          <Badge variant="outline">{categories.length} 个分类</Badge>
        </div>
        <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-6">
          {categories.map((cat) => {
            const targetCategory = cat.category === "未分类" ? "all" : cat.category;
            const isSelected = selectedCategory === targetCategory;

            return (
              <AdminCompactStatCard
                key={cat.category}
                label={cat.category}
                value={cat.count}
                hint="配置项"
                selected={isSelected}
                onClick={() => setSelectedCategory(targetCategory)}
                testId={`admin-system-summary-${cat.category}`}
              />
            );
          })}
        </div>
      </div>

      {/* 配置列表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>配置列表</CardTitle>
              <CardDescription>共 {filteredConfigs.length} 个配置</CardDescription>
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="搜索配置..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                className="w-[200px]"
              />
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="分类" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部分类</SelectItem>
                  {categories.map(cat => (
                    <SelectItem key={cat.category} value={cat.category}>
                      {cat.category}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>配置键</TableHead>
                <TableHead>配置值</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>分类</TableHead>
                <TableHead>说明</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredConfigs.map((config) => (
                <TableRow key={config.id}>
                  <TableCell className="font-mono text-sm">{config.config_key}</TableCell>
                  <TableCell className="max-w-[200px]">
                    <code className="text-xs bg-muted px-1 py-0.5 rounded truncate block">
                      {config.is_secret ? "******" : (
                        config.config_value.length > 50 
                          ? config.config_value.slice(0, 50) + "..." 
                          : config.config_value
                      )}
                    </code>
                  </TableCell>
                  <TableCell>{getTypeBadge(config.value_type)}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{config.category || "未分类"}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[200px] text-sm text-muted-foreground truncate">
                    {config.description || "-"}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {config.is_readonly ? (
                        <Badge variant="secondary">只读</Badge>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(config)}
                        >
                          编辑
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 编辑对话框 */}
      <Dialog open={!!editingConfig} onOpenChange={() => setEditingConfig(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑配置</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>配置键</Label>
              <code className="block p-2 bg-muted rounded text-sm">
                {editingConfig?.config_key}
              </code>
            </div>
            {editingConfig?.description && (
              <div className="space-y-2">
                <Label>说明</Label>
                <p className="text-sm text-muted-foreground">{editingConfig.description}</p>
              </div>
            )}
            <div className="space-y-2">
              <Label>配置值 ({editingConfig?.value_type})</Label>
              {editingConfig?.value_type === "json" || editingConfig?.config_value?.includes("\n") ? (
                <Textarea
                  placeholder={editingConfig?.is_secret ? "输入新值" : ""}
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  rows={6}
                  className="font-mono text-sm"
                />
              ) : (
                <Input
                  type={editingConfig?.is_secret ? "password" : "text"}
                  placeholder={editingConfig?.is_secret ? "输入新值（当前值已隐藏）" : ""}
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                />
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingConfig(null)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={saving || !editValue.trim()}>
              {saving ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
