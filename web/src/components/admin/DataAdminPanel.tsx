/**
 * 问数管理面板（中文注释）
 *
 * 功能：
 * - SQL 修正台（原有能力）
 * - 结果增强规则管理（新增）
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  QueryLog,
  getQueryLogs,
  correctSQL,
  feedbackSQL,
  ignoreQueryLogs,
  trainLogs,
  trainAllPending,
  getEnrichmentRules,
  createEnrichmentRule,
  updateEnrichmentRule,
  setEnrichmentRuleEnabled,
  updateEnrichmentRulePriority,
  testEnrichmentRules,
  refreshEnrichmentRuleCache,
} from "@/lib/data-admin-api";
import type {
  ResultEnrichmentRule,
  ResultEnrichmentRulePayload,
  ResultEnrichmentRuleTestResponse,
} from "@/types/result-enrichment-rule";

type RuleFormState = {
  rule_code: string;
  rule_name: string;
  enabled: boolean;
  priority: number;
  key_column_candidates: string;
  target_column: string;
  source_table: string;
  source_key_column: string;
  source_value_column: string;
  source_date_column: string;
  result_date_column_candidates: string;
  description: string;
};

const EMPTY_RULE_FORM: RuleFormState = {
  rule_code: "",
  rule_name: "",
  enabled: true,
  priority: 100,
  key_column_candidates: "",
  target_column: "",
  source_table: "",
  source_key_column: "",
  source_value_column: "",
  source_date_column: "data_dt",
  result_date_column_candidates: "data_dt",
  description: "",
};

function csvToList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function ruleToForm(rule: ResultEnrichmentRule): RuleFormState {
  return {
    rule_code: rule.rule_code,
    rule_name: rule.rule_name,
    enabled: rule.enabled,
    priority: rule.priority,
    key_column_candidates: rule.key_column_candidates.join(","),
    target_column: rule.target_column,
    source_table: rule.source_table,
    source_key_column: rule.source_key_column,
    source_value_column: rule.source_value_column,
    source_date_column: rule.source_date_column || "",
    result_date_column_candidates: rule.result_date_column_candidates.join(","),
    description: rule.description || "",
  };
}

function formToPayload(form: RuleFormState): ResultEnrichmentRulePayload {
  return {
    rule_code: form.rule_code.trim(),
    rule_name: form.rule_name.trim(),
    enabled: form.enabled,
    priority: Number(form.priority),
    key_column_candidates: csvToList(form.key_column_candidates),
    target_column: form.target_column.trim(),
    source_table: form.source_table.trim(),
    source_key_column: form.source_key_column.trim(),
    source_value_column: form.source_value_column.trim(),
    source_date_column: form.source_date_column.trim() || null,
    result_date_column_candidates: csvToList(form.result_date_column_candidates),
    description: form.description.trim() || null,
  };
}

export function DataAdminPanel() {
  const [activeTab, setActiveTab] = useState<"sql" | "rules">("sql");

  // ==================== SQL 修正台状态 ====================
  const [logs, setLogs] = useState<QueryLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [filter, setFilter] = useState<"all" | "correct" | "incorrect" | "pending">("all");

  const [editingLog, setEditingLog] = useState<QueryLog | null>(null);
  const [correctedSQL, setCorrectedSQL] = useState("");
  const [savingCorrection, setSavingCorrection] = useState(false);

  // ==================== 规则管理状态 ====================
  const [rules, setRules] = useState<ResultEnrichmentRule[]>([]);
  const [loadingRules, setLoadingRules] = useState(true);
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ResultEnrichmentRule | null>(null);
  const [ruleForm, setRuleForm] = useState<RuleFormState>(EMPTY_RULE_FORM);
  const [savingRule, setSavingRule] = useState(false);
  const [priorityDraftMap, setPriorityDraftMap] = useState<Record<number, string>>({});

  const [testColumnsInput, setTestColumnsInput] = useState("data_dt,ecif_cust_no,贷款余额");
  const [testRowsInput, setTestRowsInput] = useState(
    JSON.stringify([
      {
        data_dt: "20250630",
        ecif_cust_no: "2009001293",
        贷款余额: 123456.78,
      },
    ], null, 2),
  );
  const [testingRule, setTestingRule] = useState(false);
  const [testPreview, setTestPreview] = useState<ResultEnrichmentRuleTestResponse | null>(null);

  const loadLogs = useCallback(async () => {
    setLoadingLogs(true);
    try {
      const params: { is_correct?: boolean; trained?: boolean } = {};
      if (filter === "correct") params.is_correct = true;
      else if (filter === "incorrect") params.is_correct = false;
      else if (filter === "pending") params.trained = false;

      const data = await getQueryLogs({ ...params, limit: 50 });
      setLogs(data);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "加载失败";
      toast.error(message);
    } finally {
      setLoadingLogs(false);
    }
  }, [filter]);

  const loadRules = useCallback(async () => {
    setLoadingRules(true);
    try {
      const data = await getEnrichmentRules();
      setRules(data);
      const nextDraft: Record<number, string> = {};
      data.forEach((rule) => {
        nextDraft[rule.id] = String(rule.priority);
      });
      setPriorityDraftMap(nextDraft);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "加载规则失败";
      toast.error(message);
    } finally {
      setLoadingRules(false);
    }
  }, []);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  // ==================== SQL 修正台事件 ====================
  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === logs.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(logs.map((l) => l.id)));
    }
  };

  const handleFeedback = async (logId: number, isCorrect: boolean) => {
    try {
      await feedbackSQL(logId, isCorrect);
      toast.success(isCorrect ? "已标记为正确" : "已标记为错误");
      loadLogs();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "反馈失败";
      toast.error(message);
    }
  };

  const openCorrectDialog = (log: QueryLog) => {
    setEditingLog(log);
    setCorrectedSQL(log.corrected_sql || log.generated_sql || "");
  };

  const saveCorrection = async () => {
    if (!editingLog) return;
    setSavingCorrection(true);
    try {
      await correctSQL({
        log_id: editingLog.id,
        corrected_sql: correctedSQL,
        is_correct: true,
      });
      toast.success("修正已保存");
      setEditingLog(null);
      loadLogs();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "保存失败";
      toast.error(message);
    } finally {
      setSavingCorrection(false);
    }
  };

  const handleTrainSelected = async () => {
    if (selectedIds.size === 0) {
      toast.warning("请先选择要训练的记录");
      return;
    }
    try {
      const result = await trainLogs(Array.from(selectedIds));
      toast.success(result.message);
      if (result.errors?.length) {
        result.errors.forEach((err) => toast.warning(err));
      }
      setSelectedIds(new Set());
      loadLogs();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "训练失败";
      toast.error(message);
    }
  };

  const handleTrainAll = async () => {
    try {
      const result = await trainAllPending();
      toast.success(result.message);
      loadLogs();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "训练失败";
      toast.error(message);
    }
  };

  const handleIgnoreSelected = async () => {
    if (selectedIds.size === 0) {
      toast.warning("请先选择要忽略的记录");
      return;
    }
    try {
      const result = await ignoreQueryLogs(Array.from(selectedIds));
      toast.success(result.message);
      if (result.errors?.length) {
        result.errors.forEach((err) => toast.warning(err));
      }
      setSelectedIds(new Set());
      loadLogs();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "忽略失败";
      toast.error(message);
    }
  };

  const handleIgnoreSingle = async (logId: number) => {
    try {
      const result = await ignoreQueryLogs([logId]);
      toast.success(result.message);
      if (result.errors?.length) {
        result.errors.forEach((err) => toast.warning(err));
      }
      const newSet = new Set(selectedIds);
      newSet.delete(logId);
      setSelectedIds(newSet);
      loadLogs();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "忽略失败";
      toast.error(message);
    }
  };

  const renderStatusBadge = (log: QueryLog) => {
    if (log.trained) {
      return <Badge className="bg-green-100 text-green-700 border-green-300">已训练</Badge>;
    }
    if (log.is_correct === true) {
      return <Badge className="bg-blue-100 text-blue-700 border-blue-300">已确认正确</Badge>;
    }
    if (log.is_correct === false) {
      return <Badge className="bg-red-100 text-red-700 border-red-300">待修正</Badge>;
    }
    return <Badge variant="outline">待审核</Badge>;
  };

  // ==================== 规则管理事件 ====================
  const openCreateRuleDialog = () => {
    setEditingRule(null);
    setRuleForm(EMPTY_RULE_FORM);
    setRuleDialogOpen(true);
  };

  const openEditRuleDialog = (rule: ResultEnrichmentRule) => {
    setEditingRule(rule);
    setRuleForm(ruleToForm(rule));
    setRuleDialogOpen(true);
  };

  const saveRule = async () => {
    let payload: ResultEnrichmentRulePayload;
    try {
      payload = formToPayload(ruleForm);
    } catch {
      toast.error("规则输入格式错误，请检查后重试");
      return;
    }

    if (!payload.rule_code || !payload.rule_name) {
      toast.warning("规则编码和规则名称不能为空");
      return;
    }
    if (payload.key_column_candidates.length === 0) {
      toast.warning("至少填写一个键候选列");
      return;
    }
    if (payload.result_date_column_candidates.length === 0) {
      toast.warning("至少填写一个结果日期候选列");
      return;
    }

    setSavingRule(true);
    try {
      if (editingRule) {
        await updateEnrichmentRule(editingRule.id, payload);
        toast.success("规则已更新");
      } else {
        await createEnrichmentRule(payload);
        toast.success("规则已创建");
      }
      setRuleDialogOpen(false);
      await loadRules();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "保存规则失败";
      toast.error(message);
    } finally {
      setSavingRule(false);
    }
  };

  const toggleRuleEnabled = async (rule: ResultEnrichmentRule, nextEnabled: boolean) => {
    try {
      await setEnrichmentRuleEnabled(rule.id, nextEnabled);
      toast.success(nextEnabled ? "规则已启用" : "规则已禁用");
      loadRules();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "更新状态失败";
      toast.error(message);
    }
  };

  const saveRulePriority = async (rule: ResultEnrichmentRule) => {
    const draft = priorityDraftMap[rule.id];
    const nextPriority = Number(draft);
    if (!Number.isInteger(nextPriority) || nextPriority < 0) {
      toast.warning("优先级必须是大于等于 0 的整数");
      return;
    }

    try {
      await updateEnrichmentRulePriority(rule.id, nextPriority);
      toast.success("优先级已更新");
      loadRules();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "更新优先级失败";
      toast.error(message);
    }
  };

  const runRuleTestPreview = async () => {
    const columns = csvToList(testColumnsInput);
    if (columns.length === 0) {
      toast.warning("测试列不能为空");
      return;
    }

    let rows: Record<string, unknown>[] = [];
    try {
      const parsed = JSON.parse(testRowsInput);
      if (!Array.isArray(parsed)) {
        throw new Error("样例数据行必须是数组");
      }
      rows = parsed as Record<string, unknown>[];
    } catch {
      toast.error("测试样例数据行必须是合法 JSON 数组");
      return;
    }

    setTestingRule(true);
    try {
      const result = await testEnrichmentRules({ rows, columns });
      setTestPreview(result);
      toast.success(`测试完成：${result.summary_message}`);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "规则测试失败";
      toast.error(message);
    } finally {
      setTestingRule(false);
    }
  };

  const handleRefreshRuleCache = async () => {
    try {
      const result = await refreshEnrichmentRuleCache();
      toast.success(`${result.message}（${result.rule_count} 条生效规则）`);
      loadRules();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "刷新缓存失败";
      toast.error(message);
    }
  };

  return (
    <div className="admin-page-content space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="app-page-title">问数管理台</h1>
          <p className="app-page-subtitle mt-1">
            SQL 修正台与结果增强规则管理一体化运维
          </p>
        </div>
        <div className="flex gap-2">
          {activeTab === "sql" ? (
            <Button variant="outline" onClick={loadLogs} disabled={loadingLogs}>
              刷新日志
            </Button>
          ) : (
            <>
              <Button variant="outline" onClick={loadRules} disabled={loadingRules}>
                刷新规则
              </Button>
              <Button variant="outline" onClick={handleRefreshRuleCache}>
                刷新缓存
              </Button>
              <Button onClick={openCreateRuleDialog}>新建规则</Button>
            </>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "sql" | "rules")}> 
        <TabsList>
          <TabsTrigger value="sql">SQL 修正台</TabsTrigger>
          <TabsTrigger value="rules">结果增强规则</TabsTrigger>
        </TabsList>

        <TabsContent value="sql" className="space-y-6">
          <Card>
            <CardContent className="py-4">
              <div className="flex flex-wrap items-center gap-4">
                <span className="text-sm font-medium">筛选：</span>
                <Select value={filter} onValueChange={(v) => setFilter(v as "all" | "correct" | "incorrect" | "pending")}> 
                  <SelectTrigger className="w-44">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部</SelectItem>
                    <SelectItem value="correct">已标记正确</SelectItem>
                    <SelectItem value="incorrect">已标记错误</SelectItem>
                    <SelectItem value="pending">待训练</SelectItem>
                  </SelectContent>
                </Select>

                <Button variant="outline" onClick={handleTrainSelected} disabled={selectedIds.size === 0}>
                  训练选中 ({selectedIds.size})
                </Button>
                <Button variant="outline" onClick={handleIgnoreSelected} disabled={selectedIds.size === 0}>
                  忽略选中 ({selectedIds.size})
                </Button>
                <Button onClick={handleTrainAll}>训练全部待训练</Button>

                <span className="text-sm text-muted-foreground ml-auto">共 {logs.length} 条记录</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b">
              <div className="flex items-center gap-4">
                <Checkbox
                  checked={logs.length > 0 && selectedIds.size === logs.length}
                  onCheckedChange={toggleSelectAll}
                />
                <CardTitle className="text-base">查询日志</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {loadingLogs ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#A8D4D4] border-t-[#2F6868]" />
                </div>
              ) : logs.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">暂无记录</div>
              ) : (
                <div className="divide-y">
                  {logs.map((log) => (
                    <div key={log.id} className="p-4 hover:bg-muted/50 transition-colors">
                      <div className="flex items-start gap-4">
                        <Checkbox
                          checked={selectedIds.has(log.id)}
                          onCheckedChange={() => toggleSelect(log.id)}
                          className="mt-1"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            {renderStatusBadge(log)}
                            <span className="text-xs text-muted-foreground">
                              {new Date(log.created_at).toLocaleString("zh-CN")}
                            </span>
                          </div>
                          <p className="font-medium text-foreground mb-2 line-clamp-2">{log.question}</p>
                          {(log.corrected_sql || log.generated_sql) && (
                            <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-24">
                              {log.corrected_sql || log.generated_sql}
                            </pre>
                          )}
                        </div>
                        <div className="flex flex-col gap-2 shrink-0">
                          <Button size="sm" variant="outline" onClick={() => openCorrectDialog(log)}>
                            修正
                          </Button>
                          {!log.trained && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-amber-700 hover:text-amber-800 hover:bg-amber-50"
                              onClick={() => handleIgnoreSingle(log.id)}
                            >
                              忽略
                            </Button>
                          )}
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-green-600 hover:text-green-700 hover:bg-green-50"
                              onClick={() => handleFeedback(log.id, true)}
                              disabled={log.is_correct === true}
                            >
                              ✓
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleFeedback(log.id, false)}
                              disabled={log.is_correct === false}
                            >
                              ✗
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rules" className="space-y-6">
          <Card>
            <CardHeader className="border-b">
              <CardTitle className="text-base">规则列表</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {loadingRules ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#A8D4D4] border-t-[#2F6868]" />
                </div>
              ) : rules.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">暂无规则</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 border-b">
                      <tr>
                        <th className="text-left p-3">规则编码</th>
                        <th className="text-left p-3">规则名称</th>
                        <th className="text-left p-3">目标列</th>
                        <th className="text-left p-3">映射来源</th>
                        <th className="text-left p-3">启用</th>
                        <th className="text-left p-3">优先级</th>
                        <th className="text-left p-3">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rules.map((rule) => (
                        <tr key={rule.id} className="border-b align-top">
                          <td className="p-3 font-mono">{rule.rule_code}</td>
                          <td className="p-3">{rule.rule_name}</td>
                          <td className="p-3">{rule.target_column}</td>
                          <td className="p-3">
                            <div className="font-mono text-xs">{rule.source_table}</div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {rule.source_key_column} → {rule.source_value_column}
                            </div>
                          </td>
                          <td className="p-3">
                            <Switch
                              checked={rule.enabled}
                              onCheckedChange={(value) => toggleRuleEnabled(rule, value)}
                            />
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <Input
                                type="number"
                                min={0}
                                className="w-20"
                                value={priorityDraftMap[rule.id] ?? String(rule.priority)}
                                onChange={(e) =>
                                  setPriorityDraftMap((prev) => ({
                                    ...prev,
                                    [rule.id]: e.target.value,
                                  }))
                                }
                              />
                              <Button size="sm" variant="outline" onClick={() => saveRulePriority(rule)}>
                                保存
                              </Button>
                            </div>
                          </td>
                          <td className="p-3">
                            <Button size="sm" variant="outline" onClick={() => openEditRuleDialog(rule)}>
                              编辑
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">规则测试预览</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>列名（逗号分隔）</Label>
                <Input
                  value={testColumnsInput}
                  onChange={(e) => setTestColumnsInput(e.target.value)}
                  placeholder="data_dt,ecif_cust_no,贷款余额"
                />
              </div>
              <div className="space-y-2">
                <Label>样例行（JSON 数组）</Label>
                <Textarea
                  className="font-mono min-h-[180px]"
                  value={testRowsInput}
                  onChange={(e) => setTestRowsInput(e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={runRuleTestPreview} disabled={testingRule}>
                  {testingRule ? "测试中..." : "执行测试"}
                </Button>
                <Button variant="outline" onClick={() => setTestPreview(null)}>
                  清空结果
                </Button>
              </div>

              {testPreview && (
                <div className="space-y-2">
                  <div className="text-sm">摘要：{testPreview.summary_message}</div>
                  <div className="text-sm">
                    命中规则：
                    {testPreview.matched_rule_codes.length > 0
                      ? testPreview.matched_rule_codes.join(", ")
                      : "无"}
                  </div>
                  <div className="text-sm">
                    补齐成功规则：
                    {testPreview.applied_rule_codes.length > 0
                      ? testPreview.applied_rule_codes.join(", ")
                      : "无"}
                  </div>
                  <div className="text-sm">
                    命中但无数据规则：
                    {testPreview.no_data_rule_codes.length > 0
                      ? testPreview.no_data_rule_codes.join(", ")
                      : "无"}
                  </div>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-64">
{JSON.stringify(testPreview, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* SQL 修正对话框 */}
      <Dialog open={!!editingLog} onOpenChange={(open) => !open && setEditingLog(null)}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>SQL 修正</DialogTitle>
          </DialogHeader>
          {editingLog && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">用户问题</label>
                <p className="mt-1 p-3 bg-muted rounded-md">{editingLog.question}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">原始 SQL</label>
                <pre className="mt-1 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                  {editingLog.generated_sql || "(无)"}
                </pre>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">修正后 SQL</label>
                <Textarea
                  value={correctedSQL}
                  onChange={(e) => setCorrectedSQL(e.target.value)}
                  placeholder="输入正确的 SQL..."
                  className="mt-1 font-mono text-sm min-h-[150px]"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingLog(null)}>
              取消
            </Button>
            <Button onClick={saveCorrection} disabled={savingCorrection || !correctedSQL.trim()}>
              {savingCorrection ? "保存中..." : "保存修正"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 规则编辑对话框 */}
      <Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingRule ? "编辑结果增强规则" : "新建结果增强规则"}</DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>规则编码</Label>
              <Input
                value={ruleForm.rule_code}
                onChange={(e) => setRuleForm((prev) => ({ ...prev, rule_code: e.target.value }))}
                placeholder="customer_name"
                disabled={!!editingRule}
              />
            </div>
            <div className="space-y-2">
              <Label>规则名称</Label>
              <Input
                value={ruleForm.rule_name}
                onChange={(e) => setRuleForm((prev) => ({ ...prev, rule_name: e.target.value }))}
                placeholder="客户名称补齐"
              />
            </div>
            <div className="space-y-2">
              <Label>目标列</Label>
              <Input
                value={ruleForm.target_column}
                onChange={(e) => setRuleForm((prev) => ({ ...prev, target_column: e.target.value }))}
                placeholder="客户名称"
              />
            </div>
            <div className="space-y-2">
              <Label>优先级</Label>
              <Input
                type="number"
                min={0}
                value={ruleForm.priority}
                onChange={(e) =>
                  setRuleForm((prev) => ({ ...prev, priority: Number(e.target.value || "0") }))
                }
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>键候选列（逗号分隔）</Label>
              <Input
                value={ruleForm.key_column_candidates}
                onChange={(e) =>
                  setRuleForm((prev) => ({ ...prev, key_column_candidates: e.target.value }))
                }
                placeholder="ecif_cust_no"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>来源表（库模式.表名）</Label>
              <Input
                value={ruleForm.source_table}
                onChange={(e) => setRuleForm((prev) => ({ ...prev, source_table: e.target.value }))}
                placeholder="fdmdata.f_mid_dep_tb"
              />
            </div>
            <div className="space-y-2">
              <Label>来源键列</Label>
              <Input
                value={ruleForm.source_key_column}
                onChange={(e) =>
                  setRuleForm((prev) => ({ ...prev, source_key_column: e.target.value }))
                }
                placeholder="ecif_cust_no"
              />
            </div>
            <div className="space-y-2">
              <Label>来源值列</Label>
              <Input
                value={ruleForm.source_value_column}
                onChange={(e) =>
                  setRuleForm((prev) => ({ ...prev, source_value_column: e.target.value }))
                }
                placeholder="cust_acct_name"
              />
            </div>
            <div className="space-y-2">
              <Label>来源日期列</Label>
              <Input
                value={ruleForm.source_date_column}
                onChange={(e) =>
                  setRuleForm((prev) => ({ ...prev, source_date_column: e.target.value }))
                }
                placeholder="data_dt"
              />
            </div>
            <div className="space-y-2">
              <Label>结果日期候选列（逗号分隔）</Label>
              <Input
                value={ruleForm.result_date_column_candidates}
                onChange={(e) =>
                  setRuleForm((prev) => ({ ...prev, result_date_column_candidates: e.target.value }))
                }
                placeholder="data_dt"
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>规则说明</Label>
              <Textarea
                value={ruleForm.description}
                onChange={(e) => setRuleForm((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="规则用途与注意事项"
              />
            </div>
            <div className="flex items-center gap-3 md:col-span-2">
              <Switch
                checked={ruleForm.enabled}
                onCheckedChange={(value) => setRuleForm((prev) => ({ ...prev, enabled: value }))}
              />
              <span className="text-sm text-muted-foreground">启用规则</span>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setRuleDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={saveRule} disabled={savingRule}>
              {savingRule ? "保存中..." : "保存规则"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
