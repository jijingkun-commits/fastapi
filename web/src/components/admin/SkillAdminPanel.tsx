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

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  getAllSkills,
  getSkillDetail,
  getVectorStatus,
  regenerateEmbeddings,
  regenerateSingleSkill,
  searchSkills,
  type SearchResult,
  type Skill,
  type SkillDetail,
  type VectorStatus,
} from "@/lib/skill-admin-api";

function getErrorMessage(error: unknown, fallback = "操作失败"): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return fallback;
}

export function SkillAdminPanel() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [vectorStatus, setVectorStatus] = useState<VectorStatus | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [listLoading, setListLoading] = useState(false);

  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterEmbedding, setFilterEmbedding] = useState<"all" | "with" | "without">("all");

  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);

  const [testQuery, setTestQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  const [regenerating, setRegenerating] = useState(false);

  const hasInitializedRef = useRef(false);
  const requestIdRef = useRef(0);

  const loadData = useCallback(async () => {
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    const shouldShowInitialLoading = !hasInitializedRef.current;
    if (shouldShowInitialLoading) {
      setInitialLoading(true);
    } else {
      setListLoading(true);
    }

    try {
      const params: { search?: string; has_embedding?: boolean } = {};
      const normalizedSearch = searchQuery.trim();

      if (normalizedSearch) {
        params.search = normalizedSearch;
      }

      if (filterEmbedding === "with") {
        params.has_embedding = true;
      }

      if (filterEmbedding === "without") {
        params.has_embedding = false;
      }

      const [skillsData, statusData] = await Promise.all([getAllSkills(params), getVectorStatus()]);

      if (requestId !== requestIdRef.current) {
        return;
      }

      setSkills(skillsData);
      setVectorStatus(statusData);
    } catch (error: unknown) {
      if (requestId !== requestIdRef.current) {
        return;
      }

      toast.error(getErrorMessage(error, "加载数据失败"));
    } finally {
      if (requestId !== requestIdRef.current) {
        return;
      }

      if (shouldShowInitialLoading) {
        hasInitializedRef.current = true;
        setInitialLoading(false);
      }

      setListLoading(false);
    }
  }, [filterEmbedding, searchQuery]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleApplySearch = () => {
    const normalized = searchInput.trim();

    if (normalized === searchQuery) {
      void loadData();
      return;
    }

    setSearchQuery(normalized);
  };

  const handleViewDetail = async (skillId: string) => {
    try {
      const detail = await getSkillDetail(skillId);
      setSelectedSkill(detail);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "获取技能详情失败"));
    }
  };

  const handleRegenerateSingle = async (skillId: string) => {
    try {
      await regenerateSingleSkill(skillId);
      toast.success("向量已重新生成");
      await loadData();
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "重新生成向量失败"));
    }
  };

  const handleRegenerateAll = async () => {
    if (!confirm("确定要重新生成所有技能的向量吗？这可能需要一些时间。")) {
      return;
    }

    setRegenerating(true);

    try {
      const result = await regenerateEmbeddings();
      toast.success(result.message);
      await loadData();
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "重新生成向量失败"));
    } finally {
      setRegenerating(false);
    }
  };

  const handleSearch = async () => {
    const query = testQuery.trim();
    if (!query) {
      return;
    }

    setSearching(true);

    try {
      const result = await searchSkills(query);
      setSearchResults(result.results);

      if (result.count === 0) {
        toast.info("未找到匹配的技能");
      }
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "搜索技能失败"));
    } finally {
      setSearching(false);
    }
  };

  if (initialLoading) {
    return (
      <div className="admin-page-content">
        <div className="flex h-72 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#A8D4D4] border-t-[#2F6868]" />
        </div>
      </div>
    );
  }

  const hasFiltersApplied = Boolean(searchQuery) || filterEmbedding !== "all";
  const listCountText = hasFiltersApplied ? `当前条件命中 ${skills.length} 个技能` : `共 ${skills.length} 个技能`;

  return (
    <div className="admin-page-content space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">技能管理</h1>
          <p className="text-sm text-muted-foreground">管理 Agent 技能向量和配置</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void loadData()} disabled={listLoading}>
          {listLoading ? "刷新中..." : "刷新"}
        </Button>
      </div>

      {vectorStatus?.dimension_mismatch ? (
        <Alert variant="destructive">
          <AlertTitle>向量维度不匹配</AlertTitle>
          <AlertDescription>
            数据库中的向量维度 ({vectorStatus.embedding_dim}) 与当前 embedding 模型输出维度 (
            {vectorStatus.current_model_dim}) 不一致。请重新生成所有技能的向量。
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Card className="py-4">
          <CardHeader className="px-4 pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">技能总数</CardTitle>
          </CardHeader>
          <CardContent className="px-4">
            <div className="text-3xl font-semibold leading-none">{vectorStatus?.total_skills || 0}</div>
          </CardContent>
        </Card>

        <Card className="py-4">
          <CardHeader className="px-4 pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">有向量</CardTitle>
          </CardHeader>
          <CardContent className="px-4">
            <div className="text-3xl font-semibold leading-none text-green-600">
              {vectorStatus?.with_embedding || 0}
            </div>
          </CardContent>
        </Card>

        <Card className="py-4">
          <CardHeader className="px-4 pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">无向量</CardTitle>
          </CardHeader>
          <CardContent className="px-4">
            <div className="text-3xl font-semibold leading-none text-red-600">
              {vectorStatus?.without_embedding || 0}
            </div>
          </CardContent>
        </Card>

        <Card className="py-4">
          <CardHeader className="px-4 pb-1">
            <CardTitle className="text-sm font-medium text-muted-foreground">向量维度</CardTitle>
          </CardHeader>
          <CardContent className="px-4">
            <div className="text-3xl font-semibold leading-none">
              {vectorStatus?.embedding_dim || "-"}
              {vectorStatus?.dimension_mismatch ? (
                <span className="ml-1.5 text-xs text-red-500">(模型: {vectorStatus.current_model_dim})</span>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="list" className="space-y-3">
        <TabsList className="h-8 p-0.5">
          <TabsTrigger value="list" className="h-7 px-2.5 text-xs">
            技能列表
          </TabsTrigger>
          <TabsTrigger value="search" className="h-7 px-2.5 text-xs">
            搜索测试
          </TabsTrigger>
        </TabsList>

        <TabsContent value="list" className="mt-0">
          <Card className="py-4">
            <CardHeader className="px-4 pb-2">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-base">技能列表</CardTitle>
                  <CardDescription className="text-xs">{listCountText}</CardDescription>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    placeholder="搜索技能..."
                    value={searchInput}
                    onChange={(event) => setSearchInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        handleApplySearch();
                      }
                    }}
                    className="h-9 w-[180px] text-sm sm:w-[220px]"
                  />

                  <Button variant="outline" size="sm" onClick={handleApplySearch} disabled={listLoading}>
                    搜索
                  </Button>

                  <select
                    value={filterEmbedding}
                    onChange={(event) => setFilterEmbedding(event.target.value as "all" | "with" | "without")}
                    className="h-9 rounded-[var(--ds-radius-sm)] border border-input bg-background px-2.5 text-sm shadow-[var(--ds-shadow-1)] outline-none transition-[border-color,box-shadow] duration-[var(--ds-motion-fast)] focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
                  >
                    <option value="all">全部</option>
                    <option value="with">有向量</option>
                    <option value="without">无向量</option>
                  </select>

                  <Button variant="outline" size="sm" onClick={handleRegenerateAll} disabled={regenerating}>
                    {regenerating ? "生成中..." : "重新生成全部向量"}
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent className="px-4 pt-1">
              {listLoading ? (
                <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#A8D4D4] border-t-[#2F6868]" />
                  <span>正在更新技能列表...</span>
                </div>
              ) : null}

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="h-10 px-3 text-xs">技能 ID</TableHead>
                    <TableHead className="h-10 px-3 text-xs">名称</TableHead>
                    <TableHead className="h-10 px-3 text-xs">描述</TableHead>
                    <TableHead className="h-10 px-3 text-xs">向量</TableHead>
                    <TableHead className="h-10 px-3 text-xs">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {skills.map((skill) => (
                    <TableRow key={skill.id}>
                      <TableCell className="px-3 py-2.5 font-mono text-xs">{skill.skill_id}</TableCell>
                      <TableCell className="px-3 py-2.5 text-sm">{skill.name}</TableCell>
                      <TableCell className="max-w-[260px] px-3 py-2.5 text-sm text-muted-foreground lg:max-w-[360px]">
                        <span className="block truncate">{skill.description || "-"}</span>
                      </TableCell>
                      <TableCell className="px-3 py-2.5">
                        {skill.has_embedding ? (
                          <Badge variant="default">{skill.embedding_dim}维</Badge>
                        ) : (
                          <Badge variant="destructive">无</Badge>
                        )}
                      </TableCell>
                      <TableCell className="px-3 py-2.5">
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            onClick={() => void handleViewDetail(skill.skill_id)}
                          >
                            查看
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            onClick={() => void handleRegenerateSingle(skill.skill_id)}
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

        <TabsContent value="search" className="mt-0">
          <Card className="py-4">
            <CardHeader className="px-4 pb-2">
              <CardTitle className="text-base">向量搜索测试</CardTitle>
              <CardDescription className="text-xs">测试技能向量检索效果</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 px-4">
              <div className="flex flex-wrap gap-2">
                <Input
                  placeholder="输入查询文本..."
                  value={testQuery}
                  onChange={(event) => setTestQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      void handleSearch();
                    }
                  }}
                  className="h-9 min-w-[220px] flex-1 text-sm"
                />
                <Button size="sm" onClick={() => void handleSearch()} disabled={searching}>
                  {searching ? "搜索中..." : "搜索"}
                </Button>
              </div>

              {searchResults.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="h-10 px-3 text-xs">技能 ID</TableHead>
                      <TableHead className="h-10 px-3 text-xs">名称</TableHead>
                      <TableHead className="h-10 px-3 text-xs">相似度</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {searchResults.map((result) => (
                      <TableRow key={result.skill_id}>
                        <TableCell className="px-3 py-2.5 font-mono text-xs">{result.skill_id}</TableCell>
                        <TableCell className="px-3 py-2.5 text-sm">{result.name}</TableCell>
                        <TableCell className="px-3 py-2.5">
                          <Badge variant={result.similarity > 0.5 ? "default" : "secondary"}>
                            {(result.similarity * 100).toFixed(1)}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={!!selectedSkill} onOpenChange={() => setSelectedSkill(null)}>
        <DialogContent className="max-h-[80vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedSkill?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <p className="mb-1 text-sm text-muted-foreground">技能 ID</p>
              <code className="rounded bg-muted px-2 py-1 text-sm">{selectedSkill?.skill_id}</code>
            </div>
            <div>
              <p className="mb-1 text-sm text-muted-foreground">描述</p>
              <p>{selectedSkill?.description || "无描述"}</p>
            </div>
            <div>
              <p className="mb-1 text-sm text-muted-foreground">向量状态</p>
              {selectedSkill?.has_embedding ? (
                <Badge variant="default">{selectedSkill.embedding_dim} 维</Badge>
              ) : (
                <Badge variant="destructive">无向量</Badge>
              )}
            </div>
            <div>
              <p className="mb-1 text-sm text-muted-foreground">内容</p>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-muted p-3 text-xs">
                {selectedSkill?.content}
              </pre>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
