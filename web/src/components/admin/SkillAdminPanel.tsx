/**
 * 技能管理面板（中文注释）
 * 
 * 功能：
 * - 技能列表展示
 * - 向量状态检查
 * - 向量重新生成
 * - 技能搜索测试
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
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
} from "@/components/ui/dialog";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import {
  Skill,
  SkillDetail,
  VectorStatus,
  SearchResult,
  getSkills,
  getSkillDetail,
  getVectorStatus,
  regenerateEmbeddings,
  regenerateSingleSkill,
  searchSkills,
} from "@/lib/skill-admin-api";

export function SkillAdminPanel() {
  // 状态
  const [skills, setSkills] = useState<Skill[]>([]);
  const [vectorStatus, setVectorStatus] = useState<VectorStatus | null>(null);
  const [loading, setLoading] = useState(true);
  
  // 筛选
  const [searchText, setSearchText] = useState("");
  const [filterEmbedding, setFilterEmbedding] = useState<"all" | "with" | "without">("all");
  
  // 详情对话框
  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);
  
  // 搜索测试
  const [testQuery, setTestQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  
  // 重新生成
  const [regenerating, setRegenerating] = useState(false);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 100 };
      if (searchText) params.search = searchText;
      if (filterEmbedding === "with") params.has_embedding = true;
      if (filterEmbedding === "without") params.has_embedding = false;
      
      const [skillsData, statusData] = await Promise.all([
        getSkills(params),
        getVectorStatus(),
      ]);
      setSkills(skillsData);
      setVectorStatus(statusData);
    } catch (e: any) {
      toast.error(e.message || "加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [searchText, filterEmbedding]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 查看详情
  const handleViewDetail = async (skillId: string) => {
    try {
      const detail = await getSkillDetail(skillId);
      setSelectedSkill(detail);
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // 重新生成单个
  const handleRegenerateSingle = async (skillId: string) => {
    try {
      await regenerateSingleSkill(skillId);
      toast.success("向量已重新生成");
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    }
  };

  // 重新生成全部
  const handleRegenerateAll = async () => {
    if (!confirm("确定要重新生成所有技能的向量吗？这可能需要一些时间。")) return;
    
    setRegenerating(true);
    try {
      const result = await regenerateEmbeddings();
      toast.success(result.message);
      loadData();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setRegenerating(false);
    }
  };

  // 搜索测试
  const handleSearch = async () => {
    if (!testQuery.trim()) return;
    
    setSearching(true);
    try {
      const result = await searchSkills(testQuery);
      setSearchResults(result.results);
      if (result.count === 0) {
        toast.info("未找到匹配的技能");
      }
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSearching(false);
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
          <h1 className="text-2xl font-bold">技能管理</h1>
          <p className="text-muted-foreground">管理 Agent 技能向量和配置</p>
        </div>
        <Button variant="outline" onClick={loadData}>
          刷新
        </Button>
      </div>

      {/* 向量状态警告 */}
      {vectorStatus?.dimension_mismatch && (
        <Alert variant="destructive">
          <AlertTitle>向量维度不匹配</AlertTitle>
          <AlertDescription>
            数据库中的向量维度 ({vectorStatus.embedding_dim}) 与当前 embedding 模型输出维度 ({vectorStatus.current_model_dim}) 不一致。
            请重新生成所有技能的向量。
          </AlertDescription>
        </Alert>
      )}

      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">技能总数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{vectorStatus?.total_skills || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">有向量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{vectorStatus?.with_embedding || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">无向量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{vectorStatus?.without_embedding || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">向量维度</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {vectorStatus?.embedding_dim || "-"}
              {vectorStatus?.dimension_mismatch && (
                <span className="text-sm text-red-500 ml-2">
                  (模型: {vectorStatus.current_model_dim})
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="list" className="space-y-4">
        <TabsList>
          <TabsTrigger value="list">技能列表</TabsTrigger>
          <TabsTrigger value="search">搜索测试</TabsTrigger>
        </TabsList>

        {/* 技能列表 */}
        <TabsContent value="list">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>技能列表</CardTitle>
                  <CardDescription>共 {skills.length} 个技能</CardDescription>
                </div>
                <div className="flex gap-2">
                  <Input
                    placeholder="搜索技能..."
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    className="w-[200px]"
                  />
                  <select
                    className="border rounded px-2 py-1 text-sm"
                    value={filterEmbedding}
                    onChange={(e) => setFilterEmbedding(e.target.value as any)}
                  >
                    <option value="all">全部</option>
                    <option value="with">有向量</option>
                    <option value="without">无向量</option>
                  </select>
                  <Button
                    variant="outline"
                    onClick={handleRegenerateAll}
                    disabled={regenerating}
                  >
                    {regenerating ? "生成中..." : "重新生成全部向量"}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>技能 ID</TableHead>
                    <TableHead>名称</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead>向量</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {skills.map((skill) => (
                    <TableRow key={skill.id}>
                      <TableCell className="font-mono text-xs">{skill.skill_id}</TableCell>
                      <TableCell>{skill.name}</TableCell>
                      <TableCell className="max-w-[300px] truncate text-sm text-muted-foreground">
                        {skill.description || "-"}
                      </TableCell>
                      <TableCell>
                        {skill.has_embedding ? (
                          <Badge variant="default">{skill.embedding_dim}维</Badge>
                        ) : (
                          <Badge variant="destructive">无</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewDetail(skill.skill_id)}
                          >
                            查看
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRegenerateSingle(skill.skill_id)}
                          >
                            重新生成
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 搜索测试 */}
        <TabsContent value="search">
          <Card>
            <CardHeader>
              <CardTitle>向量搜索测试</CardTitle>
              <CardDescription>测试技能向量检索效果</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="输入查询文本..."
                  value={testQuery}
                  onChange={(e) => setTestQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="flex-1"
                />
                <Button onClick={handleSearch} disabled={searching}>
                  {searching ? "搜索中..." : "搜索"}
                </Button>
              </div>

              {searchResults.length > 0 && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>技能 ID</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>相似度</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {searchResults.map((result) => (
                      <TableRow key={result.skill_id}>
                        <TableCell className="font-mono text-xs">{result.skill_id}</TableCell>
                        <TableCell>{result.name}</TableCell>
                        <TableCell>
                          <Badge variant={result.similarity > 0.5 ? "default" : "secondary"}>
                            {(result.similarity * 100).toFixed(1)}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 详情对话框 */}
      <Dialog open={!!selectedSkill} onOpenChange={() => setSelectedSkill(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedSkill?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">技能 ID</p>
              <code className="text-sm bg-muted px-2 py-1 rounded">{selectedSkill?.skill_id}</code>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">描述</p>
              <p>{selectedSkill?.description || "无描述"}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">向量状态</p>
              {selectedSkill?.has_embedding ? (
                <Badge variant="default">{selectedSkill.embedding_dim} 维</Badge>
              ) : (
                <Badge variant="destructive">无向量</Badge>
              )}
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">内容</p>
              <pre className="text-xs bg-muted p-4 rounded overflow-x-auto whitespace-pre-wrap">
                {selectedSkill?.content}
              </pre>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
