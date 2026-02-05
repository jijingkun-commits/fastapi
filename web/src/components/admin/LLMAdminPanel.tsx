/**
 * LLM 配置管理面板（中文注释）
 * 
 * 功能：
 * - 提供商管理
 * - 模型管理
 * - 默认模型设置
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
  LLMProvider,
  LLMModel,
  ModelType,
  getProviders,
  getModels,
  getModelTypes,
  updateProvider,
  updateProviderApiKey,
  setDefaultModel,
  toggleModelActive,
} from "@/lib/llm-admin-api";

export function LLMAdminPanel() {
  // 状态
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [modelTypes, setModelTypes] = useState<ModelType[]>([]);
  const [loading, setLoading] = useState(true);
  
  // 筛选
  const [selectedProvider, setSelectedProvider] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");
  
  // API Key 编辑
  const [editingApiKey, setEditingApiKey] = useState<LLMProvider | null>(null);
  const [newApiKey, setNewApiKey] = useState("");
  const [savingApiKey, setSavingApiKey] = useState(false);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [providersData, modelsData, typesData] = await Promise.all([
        getProviders(),
        getModels(),
        getModelTypes(),
      ]);
      setProviders(providersData);
      setModels(modelsData);
      setModelTypes(typesData);
    } catch (e: any) {
      toast.error(e.message || "加载数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 筛选模型
  const filteredModels = models.filter(m => {
    if (selectedProvider !== "all" && m.provider_code !== selectedProvider) return false;
    if (selectedType !== "all" && m.model_type !== selectedType) return false;
    return true;
  });

  // 切换提供商启用状态
  const handleToggleProvider = async (provider: LLMProvider) => {
    try {
      await updateProvider(provider.id, { is_active: !provider.is_active });
      toast.success(`提供商已${provider.is_active ? "禁用" : "启用"}`);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // 保存 API Key
  const handleSaveApiKey = async () => {
    if (!editingApiKey || !newApiKey.trim()) return;
    
    setSavingApiKey(true);
    try {
      await updateProviderApiKey(editingApiKey.id, newApiKey);
      toast.success("API Key 已更新");
      setEditingApiKey(null);
      setNewApiKey("");
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSavingApiKey(false);
    }
  };

  // 设置默认模型
  const handleSetDefault = async (model: LLMModel) => {
    try {
      await setDefaultModel(model.id);
      toast.success(`已设为 ${model.model_type} 类型默认模型`);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // 切换模型启用状态
  const handleToggleModel = async (model: LLMModel) => {
    try {
      await toggleModelActive(model.id);
      toast.success(`模型已${model.is_active ? "禁用" : "启用"}`);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
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
          <h1 className="text-2xl font-bold">LLM 模型配置</h1>
          <p className="text-muted-foreground">管理 AI 模型提供商和模型配置</p>
        </div>
        <Button variant="outline" onClick={loadData}>
          刷新
        </Button>
      </div>

      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">提供商</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{providers.length}</div>
            <p className="text-xs text-muted-foreground">
              {providers.filter(p => p.is_active).length} 个启用
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">模型总数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{models.length}</div>
            <p className="text-xs text-muted-foreground">
              {models.filter(m => m.is_active).length} 个启用
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">模型类型</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{modelTypes.length}</div>
            <p className="text-xs text-muted-foreground">
              {modelTypes.filter(t => t.default_model).length} 个有默认
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">默认 Chat 模型</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold truncate">
              {modelTypes.find(t => t.type === "chat")?.default_model || "未设置"}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="providers" className="space-y-4">
        <TabsList>
          <TabsTrigger value="providers">提供商</TabsTrigger>
          <TabsTrigger value="models">模型列表</TabsTrigger>
          <TabsTrigger value="types">模型类型</TabsTrigger>
        </TabsList>

        {/* 提供商 */}
        <TabsContent value="providers">
          <Card>
            <CardHeader>
              <CardTitle>LLM 提供商</CardTitle>
              <CardDescription>管理模型提供商的连接配置</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>代码</TableHead>
                    <TableHead>名称</TableHead>
                    <TableHead>Base URL</TableHead>
                    <TableHead>API Key</TableHead>
                    <TableHead>模型数</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {providers.map((provider) => (
                    <TableRow key={provider.id}>
                      <TableCell className="font-mono">{provider.code}</TableCell>
                      <TableCell>{provider.name}</TableCell>
                      <TableCell className="max-w-[200px] truncate text-xs">
                        {provider.base_url || "-"}
                      </TableCell>
                      <TableCell>
                        <code className="text-xs bg-muted px-1 rounded">
                          {provider.api_key_masked || "未设置"}
                        </code>
                      </TableCell>
                      <TableCell>{provider.model_count}</TableCell>
                      <TableCell>
                        <Switch
                          checked={provider.is_active}
                          onCheckedChange={() => handleToggleProvider(provider)}
                        />
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingApiKey(provider);
                            setNewApiKey("");
                          }}
                        >
                          更新密钥
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 模型列表 */}
        <TabsContent value="models">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>模型列表</CardTitle>
                  <CardDescription>管理各提供商的模型配置</CardDescription>
                </div>
                <div className="flex gap-2">
                  <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue placeholder="提供商" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部提供商</SelectItem>
                      {providers.map(p => (
                        <SelectItem key={p.code} value={p.code}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select value={selectedType} onValueChange={setSelectedType}>
                    <SelectTrigger className="w-[120px]">
                      <SelectValue placeholder="类型" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部类型</SelectItem>
                      {modelTypes.map(t => (
                        <SelectItem key={t.type} value={t.type}>{t.type}</SelectItem>
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
                    <TableHead>模型代码</TableHead>
                    <TableHead>显示名称</TableHead>
                    <TableHead>提供商</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>能力</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredModels.map((model) => (
                    <TableRow key={model.id}>
                      <TableCell className="font-mono text-sm">{model.model_code}</TableCell>
                      <TableCell>{model.model_name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{model.provider_name}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{model.model_type}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {model.supports_thinking && (
                            <Badge variant="default" className="text-xs">思考</Badge>
                          )}
                          {model.supports_tool_call && (
                            <Badge variant="outline" className="text-xs">工具</Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={model.is_active}
                            onCheckedChange={() => handleToggleModel(model)}
                          />
                          {model.is_default && (
                            <Badge>默认</Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {!model.is_default && model.is_active && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleSetDefault(model)}
                          >
                            设为默认
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 模型类型 */}
        <TabsContent value="types">
          <Card>
            <CardHeader>
              <CardTitle>模型类型概览</CardTitle>
              <CardDescription>各类型模型的配置情况</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {modelTypes.map((type) => (
                  <Card key={type.type}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg">{type.type}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">可用模型</span>
                          <span>{type.count} 个</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">默认模型</span>
                          <span className="font-mono text-xs">
                            {type.default_model || "未设置"}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* API Key 编辑对话框 */}
      <Dialog open={!!editingApiKey} onOpenChange={() => setEditingApiKey(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>更新 API Key - {editingApiKey?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>当前 API Key（脱敏）</Label>
              <code className="block p-2 bg-muted rounded text-sm">
                {editingApiKey?.api_key_masked || "未设置"}
              </code>
            </div>
            <div className="space-y-2">
              <Label>新 API Key</Label>
              <Input
                type="password"
                placeholder="输入新的 API Key"
                value={newApiKey}
                onChange={(e) => setNewApiKey(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingApiKey(null)}>
              取消
            </Button>
            <Button onClick={handleSaveApiKey} disabled={savingApiKey || !newApiKey.trim()}>
              {savingApiKey ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
