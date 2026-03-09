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
import { Switch } from "@/components/ui/switch";
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
  getBootstrapTemplate,
  getAllSkills,
  getSkillDetail,
  getVectorStatus,
  regenerateEmbeddings,
  regenerateSingleSkill,
  searchSkills,
  syncUserBootstrapTemplate,
  updateBootstrapTemplate,
  type BootstrapTemplate,
  type BootstrapTemplateSkill,
  type SearchResult,
  type Skill,
  type SkillDetail,
  type SyncTemplateResult,
  type VectorStatus,
} from "@/lib/skill-admin-api";

interface BootstrapTemplateDraftItem {
  row_id: string;
  skill_id: string;
  version: string;
  enabled: boolean;
  priority_override: string;
  config_override_text: string;
}

let bootstrapTemplateDraftRowSeq = 0;

function nextBootstrapTemplateDraftRowId(): string {
  bootstrapTemplateDraftRowSeq += 1;
  return `skill-template-row-${bootstrapTemplateDraftRowSeq}`;
}

function createBootstrapTemplateDraftItem(
  skill?: Partial<BootstrapTemplateSkill>,
): BootstrapTemplateDraftItem {
  const normalizedConfig = skill?.config_override ?? {};
  const normalizedConfigText =
    typeof normalizedConfig === "object" && normalizedConfig !== null
      ? JSON.stringify(normalizedConfig)
      : "{}";

  return {
    row_id: nextBootstrapTemplateDraftRowId(),
    skill_id: String(skill?.skill_id ?? ""),
    version: String(skill?.version ?? ""),
    enabled: Boolean(skill?.enabled ?? true),
    priority_override:
      skill?.priority_override === null || skill?.priority_override === undefined
        ? ""
        : String(skill.priority_override),
    config_override_text: normalizedConfigText || "{}",
  };
}

function buildBootstrapTemplateDraft(template: BootstrapTemplate): {
  defaultVersion: string;
  items: BootstrapTemplateDraftItem[];
} {
  const defaultVersion = String(template.default_version || "v1").trim() || "v1";
  return {
    defaultVersion,
    items: (template.skills || []).map((skill) => createBootstrapTemplateDraftItem(skill)),
  };
}

function buildBootstrapTemplatePayloadForSave(
  defaultVersionRaw: string,
  items: BootstrapTemplateDraftItem[],
): BootstrapTemplate {
  const defaultVersion = defaultVersionRaw.trim() || "v1";
  const dedupedSkills = new Map<string, BootstrapTemplateSkill>();

  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    const rowNo = index + 1;
    const skillId = item.skill_id.trim();
    if (!skillId) {
      continue;
    }

    const version = item.version.trim() || defaultVersion;
    const priorityText = item.priority_override.trim();
    let priorityOverride: number | null = null;
    if (priorityText.length > 0) {
      const parsed = Number.parseInt(priorityText, 10);
      if (!Number.isInteger(parsed) || parsed < 0 || parsed > 10000) {
        throw new Error(`第 ${rowNo} 行 priority_override 非法，需为 0~10000 的整数`);
      }
      priorityOverride = parsed;
    }

    const configText = item.config_override_text.trim();
    let configOverride: Record<string, unknown> = {};
    if (configText.length > 0) {
      let parsed: unknown;
      try {
        parsed = JSON.parse(configText);
      } catch {
        throw new Error(`第 ${rowNo} 行 config_override 不是合法 JSON`);
      }

      if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
        throw new Error(`第 ${rowNo} 行 config_override 必须是 JSON 对象`);
      }

      configOverride = parsed as Record<string, unknown>;
    }

    dedupedSkills.set(skillId, {
      skill_id: skillId,
      version,
      enabled: item.enabled,
      priority_override: priorityOverride,
      config_override: configOverride,
    });
  }

  return {
    default_version: defaultVersion,
    skills: Array.from(dedupedSkills.values()),
  };
}

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
  const [templateDefaultVersion, setTemplateDefaultVersion] = useState("v1");
  const [templateItems, setTemplateItems] = useState<BootstrapTemplateDraftItem[]>([]);
  const [templateLoading, setTemplateLoading] = useState(false);
  const [templateCatalogLoading, setTemplateCatalogLoading] = useState(false);
  const [templateSaving, setTemplateSaving] = useState(false);
  const [syncUserId, setSyncUserId] = useState("");
  const [syncingTemplate, setSyncingTemplate] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState<SyncTemplateResult | null>(null);

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
      const isLatestRequest = requestId === requestIdRef.current;
      if (isLatestRequest) {
        if (shouldShowInitialLoading) {
          hasInitializedRef.current = true;
          setInitialLoading(false);
        }

        setListLoading(false);
      }
    }
  }, [filterEmbedding, searchQuery]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const applyTemplateToDraft = useCallback((template: BootstrapTemplate) => {
    const draft = buildBootstrapTemplateDraft(template);
    setTemplateDefaultVersion(draft.defaultVersion);
    setTemplateItems(draft.items);
  }, []);

  const loadBootstrapTemplate = useCallback(async () => {
    setTemplateLoading(true);
    try {
      const template = await getBootstrapTemplate();
      applyTemplateToDraft(template);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "加载模板失败"));
    } finally {
      setTemplateLoading(false);
    }
  }, [applyTemplateToDraft]);

  useEffect(() => {
    void loadBootstrapTemplate();
  }, [loadBootstrapTemplate]);

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

  const handleAddTemplateSkill = () => {
    setTemplateItems((prev) => [...prev, createBootstrapTemplateDraftItem()]);
  };

  const handleTemplateSkillChange = (
    rowId: string,
    patch: Partial<Omit<BootstrapTemplateDraftItem, "row_id">>,
  ) => {
    setTemplateItems((prev) =>
      prev.map((item) => (item.row_id === rowId ? { ...item, ...patch } : item)),
    );
  };

  const handleRemoveTemplateSkill = (rowId: string) => {
    setTemplateItems((prev) => prev.filter((item) => item.row_id !== rowId));
  };

  const handleHydrateTemplateFromSkillCatalog = async () => {
    if (
      templateItems.length > 0 &&
      !confirm("将使用当前技能库重建模板清单，未保存的编辑会丢失，确认继续吗？")
    ) {
      return;
    }

    setTemplateCatalogLoading(true);
    try {
      const catalog = await getAllSkills();
      const fallbackVersion = templateDefaultVersion.trim() || "v1";
      setTemplateItems(
        catalog.map((skill) =>
          createBootstrapTemplateDraftItem({
            skill_id: skill.skill_id,
            version: fallbackVersion,
            enabled: true,
            priority_override: null,
            config_override: {},
          }),
        ),
      );
      toast.success(`已按当前技能库重建模板，共 ${catalog.length} 条`);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "按技能库重建模板失败"));
    } finally {
      setTemplateCatalogLoading(false);
    }
  };

  const handleSaveTemplate = async () => {
    let parsedTemplate: BootstrapTemplate;
    try {
      parsedTemplate = buildBootstrapTemplatePayloadForSave(templateDefaultVersion, templateItems);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "模板内容不合法"));
      return;
    }

    setTemplateSaving(true);
    try {
      const updatedTemplate = await updateBootstrapTemplate(parsedTemplate);
      applyTemplateToDraft(updatedTemplate);
      toast.success("模板已保存");
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "保存模板失败"));
    } finally {
      setTemplateSaving(false);
    }
  };

  const handleSyncTemplateToUser = async () => {
    const parsedUserId = Number.parseInt(syncUserId.trim(), 10);
    if (!Number.isInteger(parsedUserId) || parsedUserId <= 0) {
      toast.error("请输入有效用户编号");
      return;
    }

    setSyncingTemplate(true);
    try {
      const result = await syncUserBootstrapTemplate(parsedUserId);
      setLastSyncResult(result);
      toast.success(`模板同步完成：成功 ${result.synced_count}，跳过 ${result.skipped_count}`);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "同步模板失败"));
    } finally {
      setSyncingTemplate(false);
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
          <h1 className="app-page-title">技能管理</h1>
          <p className="app-page-subtitle">管理智能体技能向量和配置</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void loadData()} disabled={listLoading}>
          {listLoading ? "刷新中..." : "刷新"}
        </Button>
      </div>

      {vectorStatus?.dimension_mismatch ? (
        <Alert variant="destructive">
          <AlertTitle>向量维度不匹配</AlertTitle>
          <AlertDescription>
            数据库中的向量维度 ({vectorStatus.embedding_dim}) 与当前向量模型输出维度 (
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
          <TabsTrigger value="template" className="h-7 px-2.5 text-xs">
            模板治理
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
                    <TableHead className="h-10 px-3 text-xs">技能编号</TableHead>
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

        <TabsContent value="template" className="mt-0">
          <Card className="py-4">
            <CardHeader className="px-4 pb-2">
              <CardTitle className="text-base">统一模板治理</CardTitle>
              <CardDescription className="text-xs">
                编辑技能启动模板（`skill.user_bootstrap_template`），并按需同步到指定用户
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 px-4">
              <div className="flex flex-wrap items-end gap-3">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">默认版本</p>
                  <Input
                    className="h-9 w-[160px] font-mono text-sm"
                    value={templateDefaultVersion}
                    onChange={(event) => setTemplateDefaultVersion(event.target.value)}
                    placeholder="如: v1"
                  />
                </div>
                <p className="pb-1 text-xs text-muted-foreground">
                  模板技能数：{templateItems.length}（空技能编号行在保存时会自动忽略）
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadBootstrapTemplate()}
                  disabled={templateLoading}
                >
                  {templateLoading ? "读取中..." : "重新读取模板"}
                </Button>
                <Button variant="outline" size="sm" onClick={handleAddTemplateSkill}>
                  新增一行
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handleHydrateTemplateFromSkillCatalog()}
                  disabled={templateCatalogLoading}
                >
                  {templateCatalogLoading ? "重建中..." : "按当前技能库重建"}
                </Button>
                <Button
                  size="sm"
                  onClick={() => void handleSaveTemplate()}
                  disabled={templateSaving || templateLoading || templateCatalogLoading}
                >
                  {templateSaving ? "保存中..." : "保存模板"}
                </Button>
              </div>

              <div className="rounded border border-border/60">
                <div className="max-h-[380px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="h-9 px-3 text-xs">技能编号</TableHead>
                        <TableHead className="h-9 px-3 text-xs">版本</TableHead>
                        <TableHead className="h-9 px-3 text-xs">启用</TableHead>
                        <TableHead className="h-9 px-3 text-xs">优先级</TableHead>
                        <TableHead className="h-9 px-3 text-xs">配置覆盖（JSON）</TableHead>
                        <TableHead className="h-9 px-3 text-xs text-right">操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {templateItems.length > 0 ? (
                        templateItems.map((item) => (
                          <TableRow key={item.row_id}>
                            <TableCell className="px-3 py-2.5 align-top">
                              <Input
                                className="h-8 min-w-[220px] font-mono text-xs"
                                list="skill-template-skill-id-options"
                                value={item.skill_id}
                                onChange={(event) =>
                                  handleTemplateSkillChange(item.row_id, { skill_id: event.target.value })
                                }
                                placeholder="例如: sql-expert"
                              />
                            </TableCell>
                            <TableCell className="px-3 py-2.5 align-top">
                              <Input
                                className="h-8 w-[120px] font-mono text-xs"
                                value={item.version}
                                onChange={(event) =>
                                  handleTemplateSkillChange(item.row_id, { version: event.target.value })
                                }
                                placeholder={templateDefaultVersion || "v1"}
                              />
                            </TableCell>
                            <TableCell className="px-3 py-2.5 align-top">
                              <div className="flex h-8 items-center">
                                <Switch
                                  checked={item.enabled}
                                  onCheckedChange={(checked) =>
                                    handleTemplateSkillChange(item.row_id, { enabled: checked })
                                  }
                                />
                              </div>
                            </TableCell>
                            <TableCell className="px-3 py-2.5 align-top">
                              <Input
                                className="h-8 w-[110px] font-mono text-xs"
                                type="number"
                                value={item.priority_override}
                                onChange={(event) =>
                                  handleTemplateSkillChange(item.row_id, {
                                    priority_override: event.target.value,
                                  })
                                }
                                placeholder="默认"
                              />
                            </TableCell>
                            <TableCell className="px-3 py-2.5 align-top">
                              <Input
                                className="h-8 min-w-[240px] font-mono text-xs"
                                value={item.config_override_text}
                                onChange={(event) =>
                                  handleTemplateSkillChange(item.row_id, {
                                    config_override_text: event.target.value,
                                  })
                                }
                                placeholder='例如: {"scope":"data"}'
                              />
                            </TableCell>
                            <TableCell className="px-3 py-2.5 align-top text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2 text-xs text-red-600 hover:text-red-700"
                                onClick={() => handleRemoveTemplateSkill(item.row_id)}
                              >
                                删除
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={6} className="px-3 py-6 text-center text-xs text-muted-foreground">
                            当前模板暂无技能，点击“新增一行”或“按当前技能库重建”开始编辑
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>

              <datalist id="skill-template-skill-id-options">
                {skills.map((skill) => (
                  <option key={skill.skill_id} value={skill.skill_id} />
                ))}
              </datalist>

              <div className="rounded border border-border/60 p-3">
                <p className="mb-2 text-xs font-medium text-muted-foreground">同步模板到指定用户</p>
                <div className="flex flex-wrap gap-2">
                  <Input
                    className="h-9 w-[180px] text-sm"
                    placeholder="用户编号"
                    value={syncUserId}
                    onChange={(event) => setSyncUserId(event.target.value)}
                  />
                  <Button size="sm" onClick={() => void handleSyncTemplateToUser()} disabled={syncingTemplate}>
                    {syncingTemplate ? "同步中..." : "同步到该用户"}
                  </Button>
                </div>
                {lastSyncResult ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    最近一次同步：用户编号={lastSyncResult.user_id}，总计 {lastSyncResult.total}，成功{" "}
                    {lastSyncResult.synced_count}，跳过 {lastSyncResult.skipped_count}，失败 {lastSyncResult.failed_count}
                  </p>
                ) : null}
              </div>
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
                      <TableHead className="h-10 px-3 text-xs">技能编号</TableHead>
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
              <p className="mb-1 text-sm text-muted-foreground">技能编号</p>
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
