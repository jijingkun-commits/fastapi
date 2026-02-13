/**
 * 指标管理面板
 *
 * 功能：
 * - 指标模板统计仪表盘（饼图 + 数字卡片）
 * - 批量 ETL 转换操作面板
 * - 指标列表展示（支持搜索与分类筛选）
 * - 新建指标（手动 / AI 转换两种模式）
 * - 编辑和删除指标
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis,
} from "recharts";
import {
    MetricDef,
    MetricCreateRequest,
    MetricStats,
    ETLConvertResult,
    BatchConvertResult,
    getMetrics,
    getMetricStats,
    createMetric,
    updateMetric,
    deleteMetric,
    convertETL,
    batchConvertTemplates,
} from "@/lib/data-admin-api";

// 空表单默认值
const emptyForm: MetricCreateRequest = {
    metric_id: "",
    metric_name: "",
    aliases: "",
    description: "",
    sql_template: "",
    category: "",
    unit: "",
};

// 分类选项
const CATEGORIES = ["贷款", "存款", "综合", "其他"];
const UNITS = ["元", "户", "笔", "%", "其他"];

// 饼图配色
const PIE_COLORS = ["#2F6868", "#5BA3A3", "#F59E0B", "#D1D5DB"];
const SOURCE_LABELS: Record<string, string> = {
    manual: "手动 SELECT",
    result_lookup: "结果表查询",
    ai_extract: "AI 提取",
    none: "未处理",
};

// ==================== 统计仪表盘组件 ====================

function StatCard({ label, value, sub, accent }: {
    label: string; value: string | number; sub?: string; accent?: boolean;
}) {
    return (
        <Card className={accent ? "border-[#2F6868]/30 bg-[#F0F7F7]" : ""}>
            <CardContent className="py-4 px-5">
                <p className="text-xs text-muted-foreground mb-1">{label}</p>
                <p className={`text-2xl font-bold tabular-nums ${accent ? "text-[#2F6868]" : "text-foreground"}`}>
                    {value}
                </p>
                {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
            </CardContent>
        </Card>
    );
}

function StatsPanel({ stats, onRefresh }: { stats: MetricStats | null; onRefresh: () => void }) {
    if (!stats) return null;

    const sourceData = stats.by_template_source
        .map(s => ({ name: SOURCE_LABELS[s.source] || s.source, value: s.count }))
        .filter(s => s.value > 0);

    const categoryData = stats.by_category.slice(0, 6);

    return (
        <Card className="mb-6">
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-base">指标模板统计</CardTitle>
                <Button variant="ghost" size="sm" onClick={onRefresh} className="text-xs">
                    刷新统计
                </Button>
            </CardHeader>
            <CardContent>
                {/* 数字卡片 */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                    <StatCard label="总指标数" value={stats.total.toLocaleString()} />
                    <StatCard
                        label="可查询"
                        value={stats.query_ready.toLocaleString()}
                        sub={`${stats.query_ready_percent}%`}
                        accent
                    />
                    <StatCard
                        label="未处理"
                        value={(stats.total - stats.query_ready).toLocaleString()}
                        sub={`${(100 - stats.query_ready_percent).toFixed(1)}%`}
                    />
                    <StatCard
                        label="已向量化"
                        value={stats.embedding_ready.toLocaleString()}
                        sub={`${stats.embedding_ready_percent}%`}
                    />
                </div>

                {/* 图表区 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* 饼图: 模板来源分布 */}
                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">模板来源分布</p>
                        <div className="h-48">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={sourceData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={40}
                                        outerRadius={70}
                                        paddingAngle={2}
                                        dataKey="value"
                                    >
                                        {sourceData.map((_, i) => (
                                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        formatter={(value: number) => [value.toLocaleString(), "数量"]}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        {/* 图例 */}
                        <div className="flex flex-wrap gap-3 justify-center mt-1">
                            {sourceData.map((item, i) => (
                                <div key={item.name} className="flex items-center gap-1.5 text-xs">
                                    <span
                                        className="w-2.5 h-2.5 rounded-full inline-block"
                                        style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                                    />
                                    <span className="text-muted-foreground">{item.name}</span>
                                    <span className="font-medium">{item.value.toLocaleString()}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* 柱状图: 分类分布 */}
                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">指标分类分布</p>
                        <div className="h-48">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={categoryData} layout="vertical" margin={{ left: 60, right: 16 }}>
                                    <XAxis type="number" hide />
                                    <YAxis
                                        type="category"
                                        dataKey="category"
                                        tick={{ fontSize: 12 }}
                                        width={56}
                                    />
                                    <Tooltip formatter={(v: number) => [v.toLocaleString(), "数量"]} />
                                    <Bar dataKey="count" fill="#5BA3A3" radius={[0, 4, 4, 0]} barSize={18} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

                {/* 模板类型明细表格 */}
                <div className="mt-5 border rounded-md overflow-hidden">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-muted/50">
                                <th className="text-left px-4 py-2 font-medium">模板类型</th>
                                <th className="text-right px-4 py-2 font-medium">数量</th>
                                <th className="text-right px-4 py-2 font-medium">占比</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stats.by_template_type.map((item, i) => (
                                <tr key={i} className="border-t">
                                    <td className="px-4 py-2">{item.type}</td>
                                    <td className="text-right px-4 py-2 tabular-nums font-medium">
                                        {item.count.toLocaleString()}
                                    </td>
                                    <td className="text-right px-4 py-2 tabular-nums text-muted-foreground">
                                        {item.percent}%
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
}

// ==================== 批量操作面板 ====================

function BatchPanel({ onComplete }: { onComplete: () => void }) {
    const [mode, setMode] = useState<"result_lookup" | "ai_extract">("result_lookup");
    const [limit, setLimit] = useState(100);
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState<BatchConvertResult | null>(null);

    const handleRun = async (dryRun: boolean) => {
        setRunning(true);
        setResult(null);
        try {
            const res = await batchConvertTemplates({ mode, limit, dry_run: dryRun });
            setResult(res);
            if (!dryRun && res.success > 0) {
                toast.success(`成功转换 ${res.success} 条指标`);
                onComplete();
            }
        } catch (e: any) {
            toast.error(e.message || "操作失败");
        } finally {
            setRunning(false);
        }
    };

    return (
        <Card className="mb-6">
            <CardHeader className="pb-2">
                <CardTitle className="text-base">批量模板转换</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="flex flex-wrap items-end gap-4 mb-4">
                    <div>
                        <label className="text-xs font-medium mb-1 block">转换模式</label>
                        <Select value={mode} onValueChange={(v) => setMode(v as any)}>
                            <SelectTrigger className="w-48">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="result_lookup">
                                    结果表查询（快速，无需 AI）
                                </SelectItem>
                                <SelectItem value="ai_extract">
                                    AI 提取 SELECT（较慢）
                                </SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                        <label className="text-xs font-medium mb-1 block">每批数量</label>
                        <Input
                            type="number"
                            value={limit}
                            onChange={(e) => setLimit(Number(e.target.value) || 50)}
                            className="w-24"
                            min={1}
                            max={500}
                        />
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => handleRun(true)} disabled={running}>
                            预览
                        </Button>
                        <Button onClick={() => handleRun(false)} disabled={running}>
                            {running ? (
                                <span className="flex items-center gap-2">
                                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                    转换中...
                                </span>
                            ) : "执行转换"}
                        </Button>
                    </div>
                </div>

                {result && (
                    <div className="border rounded-md p-3 bg-muted/30 text-sm">
                        <p className="font-medium mb-1">{result.message}</p>
                        {result.dry_run && result.preview && (
                            <div className="mt-2 max-h-40 overflow-y-auto">
                                <p className="text-xs text-muted-foreground mb-1">
                                    待转换指标（前 {result.preview.length} 条）:
                                </p>
                                {result.preview.map(p => (
                                    <span key={p.metric_id} className="inline-block mr-2 mb-1 text-xs bg-white px-2 py-0.5 rounded border">
                                        {p.metric_id} {p.metric_name}
                                    </span>
                                ))}
                            </div>
                        )}
                        {result.errors && result.errors.length > 0 && (
                            <div className="mt-2 text-xs text-red-600">
                                <p>失败 {result.errors.length} 条:</p>
                                {result.errors.slice(0, 5).map(e => (
                                    <p key={e.metric_id}>{e.metric_id}: {e.error}</p>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// ==================== 主组件 ====================

export function MetricAdminPanel() {
    // 列表状态
    const [metrics, setMetrics] = useState<MetricDef[]>([]);
    const [loading, setLoading] = useState(true);
    const [keyword, setKeyword] = useState("");
    const [filterCategory, setFilterCategory] = useState<string>("all");

    // 统计数据
    const [stats, setStats] = useState<MetricStats | null>(null);
    const [showBatch, setShowBatch] = useState(false);

    // 对话框状态
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogMode, setDialogMode] = useState<"create" | "edit">("create");
    const [form, setForm] = useState<MetricCreateRequest>({ ...emptyForm });
    const [saving, setSaving] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);

    // AI 转换状态
    const [etlScript, setEtlScript] = useState("");
    const [converting, setConverting] = useState(false);
    const [activeTab, setActiveTab] = useState<string>("manual");

    // SQL 预览展开
    const [expandedSql, setExpandedSql] = useState<string | null>(null);

    // 删除确认
    const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

    // 加载统计数据
    const loadStats = useCallback(async () => {
        try {
            const data = await getMetricStats();
            setStats(data);
        } catch (e: any) {
            console.error("加载统计失败:", e);
        }
    }, []);

    // 加载指标列表
    const loadMetrics = useCallback(async () => {
        setLoading(true);
        try {
            const params: { category?: string; keyword?: string } = {};
            if (filterCategory !== "all") params.category = filterCategory;
            if (keyword.trim()) params.keyword = keyword.trim();
            const data = await getMetrics(params);
            setMetrics(data);
        } catch (e: any) {
            toast.error(e.message || "加载失败");
        } finally {
            setLoading(false);
        }
    }, [filterCategory, keyword]);

    useEffect(() => {
        loadMetrics();
        loadStats();
    }, [loadMetrics, loadStats]);

    // 打开新建对话框
    const openCreateDialog = () => {
        setForm({ ...emptyForm });
        setEtlScript("");
        setDialogMode("create");
        setEditingId(null);
        setActiveTab("manual");
        setDialogOpen(true);
    };

    // 打开编辑对话框
    const openEditDialog = (m: MetricDef) => {
        setForm({
            metric_id: m.metric_id,
            metric_name: m.metric_name,
            aliases: m.aliases || "",
            description: m.description || "",
            sql_template: m.sql_template || "",
            category: m.category || "",
            unit: m.unit || "",
        });
        setDialogMode("edit");
        setEditingId(m.metric_id);
        setActiveTab("manual");
        setDialogOpen(true);
    };

    // AI 转换
    const handleConvert = async () => {
        if (!etlScript.trim()) {
            toast.warning("请粘贴 ETL 脚本");
            return;
        }
        setConverting(true);
        try {
            const result: ETLConvertResult = await convertETL(etlScript);
            setForm({
                metric_id: result.metric_id || "",
                metric_name: result.metric_name || "",
                aliases: result.aliases || "",
                description: result.description || "",
                sql_template: result.sql_template || "",
                category: result.category || "",
                unit: result.unit || "",
            });
            setActiveTab("manual");
            toast.success("AI 提取完成，请检查并编辑后保存");
        } catch (e: any) {
            toast.error(e.message || "转换失败");
        } finally {
            setConverting(false);
        }
    };

    // 保存
    const handleSave = async () => {
        if (!form.metric_id || !form.metric_name || !form.description || !form.sql_template) {
            toast.warning("请填写必填字段：指标 ID、名称、描述、SQL 模板");
            return;
        }
        setSaving(true);
        try {
            if (dialogMode === "edit" && editingId) {
                await updateMetric(editingId, form);
                toast.success("更新成功");
            } else {
                await createMetric(form);
                toast.success("创建成功");
            }
            setDialogOpen(false);
            loadMetrics();
            loadStats();
        } catch (e: any) {
            toast.error(e.message || "保存失败");
        } finally {
            setSaving(false);
        }
    };

    // 删除
    const handleDelete = async () => {
        if (!deleteTarget) return;
        try {
            await deleteMetric(deleteTarget);
            toast.success("删除成功");
            setDeleteTarget(null);
            loadMetrics();
            loadStats();
        } catch (e: any) {
            toast.error(e.message || "删除失败");
        }
    };

    // 分类颜色
    const categoryColor = (cat: string | null) => {
        switch (cat) {
            case "贷款": return "bg-amber-100 text-amber-800";
            case "存款": return "bg-[#E8F4F4] text-[#2F6868]";
            case "综合": return "bg-purple-100 text-purple-800";
            default: return "bg-gray-100 text-gray-600";
        }
    };

    // 模板来源标签
    const sourceLabel = (src: string | null) => {
        if (!src || src === "none") return null;
        const labels: Record<string, { text: string; cls: string }> = {
            manual: { text: "手动", cls: "bg-blue-100 text-blue-700" },
            result_lookup: { text: "结果表", cls: "bg-emerald-100 text-emerald-700" },
            ai_extract: { text: "AI", cls: "bg-violet-100 text-violet-700" },
        };
        const info = labels[src];
        if (!info) return null;
        return <Badge className={`ml-1 text-[10px] px-1.5 py-0 ${info.cls}`}>{info.text}</Badge>;
    };

    return (
        <div className="admin-page-content space-y-6">
            {/* 页头 */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-foreground">指标管理</h1>
                    <p className="text-muted-foreground text-sm mt-1">
                        管理问数助手的指标定义，支持 AI 从 ETL 脚本提取 SELECT 模板
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        onClick={() => setShowBatch(!showBatch)}
                    >
                        {showBatch ? "收起批量操作" : "批量转换"}
                    </Button>
                    <Button variant="outline" onClick={() => { loadMetrics(); loadStats(); }} disabled={loading}>
                        刷新
                    </Button>
                    <Button onClick={openCreateDialog}>
                        新建指标
                    </Button>
                </div>
            </div>

            {/* 统计仪表盘 */}
            <StatsPanel stats={stats} onRefresh={loadStats} />

            {/* 批量操作面板 */}
            {showBatch && (
                <BatchPanel onComplete={() => { loadMetrics(); loadStats(); }} />
            )}

            {/* 筛选栏 */}
            <Card className="mb-6">
                <CardContent className="py-4">
                    <div className="flex items-center gap-4">
                        <Input
                            placeholder="搜索指标名称、别名或描述..."
                            value={keyword}
                            onChange={(e) => setKeyword(e.target.value)}
                            className="max-w-xs"
                        />
                        <Select value={filterCategory} onValueChange={setFilterCategory}>
                            <SelectTrigger className="w-32">
                                <SelectValue placeholder="分类" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">全部分类</SelectItem>
                                {CATEGORIES.map(c => (
                                    <SelectItem key={c} value={c}>{c}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <span className="text-sm text-muted-foreground ml-auto">
                            共 {metrics.length} 个指标
                        </span>
                    </div>
                </CardContent>
            </Card>

            {/* 指标列表 */}
            <Card>
                <CardHeader className="border-b py-4">
                    <CardTitle className="text-base">指标定义</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {loading ? (
                        <div className="flex items-center justify-center py-16">
                            <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#A8D4D4] border-t-[#2F6868]" />
                        </div>
                    ) : metrics.length === 0 ? (
                        <div className="text-center py-16 text-muted-foreground">
                            暂无指标，点击"新建指标"开始添加
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-28">指标 ID</TableHead>
                                    <TableHead>名称</TableHead>
                                    <TableHead className="w-20">分类</TableHead>
                                    <TableHead className="w-16">单位</TableHead>
                                    <TableHead className="w-20">模板</TableHead>
                                    <TableHead className="hidden lg:table-cell">描述</TableHead>
                                    <TableHead className="w-28 text-right">操作</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {metrics.map((m) => (
                                    <TableRow
                                        key={m.metric_id}
                                        className="group cursor-pointer"
                                        onClick={() => setExpandedSql(
                                            expandedSql === m.metric_id ? null : m.metric_id
                                        )}
                                    >
                                        <TableCell className="font-mono text-xs text-muted-foreground">
                                            {m.metric_id}
                                        </TableCell>
                                        <TableCell>
                                            <div className="font-medium">{m.metric_name}</div>
                                            {m.aliases && (
                                                <div className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                                                    {m.aliases}
                                                </div>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <Badge className={categoryColor(m.category)}>
                                                {m.category || "-"}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-sm">{m.unit || "-"}</TableCell>
                                        <TableCell>
                                            {m.query_template ? (
                                                <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">
                                                    可查询
                                                </Badge>
                                            ) : m.sql_template ? (
                                                <Badge className="bg-amber-100 text-amber-700 text-[10px]">
                                                    ETL
                                                </Badge>
                                            ) : (
                                                <Badge className="bg-gray-100 text-gray-500 text-[10px]">
                                                    无
                                                </Badge>
                                            )}
                                            {sourceLabel(m.template_source)}
                                        </TableCell>
                                        <TableCell className="hidden lg:table-cell text-sm text-muted-foreground line-clamp-2 max-w-xs">
                                            {m.description || "-"}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex justify-end gap-1" onClick={e => e.stopPropagation()}>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => openEditDialog(m)}
                                                >
                                                    编辑
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                    onClick={() => setDeleteTarget(m.metric_id)}
                                                >
                                                    删除
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}

                    {/* SQL 模板展开预览 */}
                    {expandedSql && (() => {
                        const target = metrics.find(m => m.metric_id === expandedSql);
                        return (
                            <div className="border-t bg-slate-50 p-4 space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-medium text-muted-foreground">
                                        {expandedSql} - {target?.metric_name}
                                    </span>
                                    <Button
                                        size="sm" variant="ghost"
                                        onClick={() => setExpandedSql(null)}
                                        className="h-6 px-2 text-xs"
                                    >
                                        收起
                                    </Button>
                                </div>
                                {target?.query_template && (
                                    <div>
                                        <p className="text-[10px] font-medium text-emerald-700 mb-1">
                                            query_template（可执行）
                                        </p>
                                        <pre className="text-xs bg-white p-3 rounded-md border overflow-x-auto whitespace-pre-wrap">
                                            {target.query_template}
                                        </pre>
                                    </div>
                                )}
                                <div>
                                    <p className="text-[10px] font-medium text-muted-foreground mb-1">
                                        sql_template（原始{target?.query_template ? "" : "，ETL 格式"}）
                                    </p>
                                    <pre className="text-xs bg-white p-3 rounded-md border overflow-x-auto whitespace-pre-wrap max-h-60 overflow-y-auto">
                                        {target?.sql_template || "(无)"}
                                    </pre>
                                </div>
                            </div>
                        );
                    })()}
                </CardContent>
            </Card>

            {/* 新建/编辑对话框 */}
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>
                            {dialogMode === "edit" ? "编辑指标" : "新建指标"}
                        </DialogTitle>
                    </DialogHeader>

                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="mb-4">
                            <TabsTrigger value="manual">手动填写</TabsTrigger>
                            {dialogMode === "create" && (
                                <TabsTrigger value="ai">AI 转换</TabsTrigger>
                            )}
                        </TabsList>

                        {/* AI 转换 Tab */}
                        {dialogMode === "create" && (
                            <TabsContent value="ai" className="space-y-4">
                                <div>
                                    <label className="text-sm font-medium mb-1 block">
                                        粘贴 ETL 脚本
                                    </label>
                                    <p className="text-xs text-muted-foreground mb-2">
                                        支持 DELETE + INSERT INTO ... SELECT 格式的 ETL 脚本，AI 将自动提取 SELECT 查询模板和指标元信息
                                    </p>
                                    <Textarea
                                        value={etlScript}
                                        onChange={(e) => setEtlScript(e.target.value)}
                                        placeholder={"/* 示例 */\nDELETE FROM ... WHERE ...;\nINSERT INTO ... SELECT ... FROM ...;"}
                                        className="font-mono text-xs min-h-[240px]"
                                    />
                                </div>
                                <Button
                                    onClick={handleConvert}
                                    disabled={converting || !etlScript.trim()}
                                    className="w-full"
                                >
                                    {converting ? (
                                        <span className="flex items-center gap-2">
                                            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                            AI 提取中...
                                        </span>
                                    ) : (
                                        "AI 提取 SELECT 模板"
                                    )}
                                </Button>
                            </TabsContent>
                        )}

                        {/* 手动填写 Tab */}
                        <TabsContent value="manual" className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-sm font-medium mb-1 block">
                                        指标 ID <span className="text-red-500">*</span>
                                    </label>
                                    <Input
                                        value={form.metric_id}
                                        onChange={(e) => setForm({ ...form, metric_id: e.target.value })}
                                        placeholder="AK000119"
                                        disabled={dialogMode === "edit"}
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium mb-1 block">
                                        指标名称 <span className="text-red-500">*</span>
                                    </label>
                                    <Input
                                        value={form.metric_name}
                                        onChange={(e) => setForm({ ...form, metric_name: e.target.value })}
                                        placeholder="各项贷款户数"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium mb-1 block">
                                    别名（逗号分隔）
                                </label>
                                <Input
                                    value={form.aliases || ""}
                                    onChange={(e) => setForm({ ...form, aliases: e.target.value })}
                                    placeholder="贷款户数,贷款客户数"
                                />
                            </div>

                            <div>
                                <label className="text-sm font-medium mb-1 block">
                                    描述 <span className="text-red-500">*</span>
                                </label>
                                <Textarea
                                    value={form.description}
                                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                                    placeholder="用自然语言描述指标口径..."
                                    className="min-h-[80px]"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-sm font-medium mb-1 block">分类</label>
                                    <Select
                                        value={form.category || ""}
                                        onValueChange={(v) => setForm({ ...form, category: v })}
                                    >
                                        <SelectTrigger>
                                            <SelectValue placeholder="选择分类" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {CATEGORIES.map(c => (
                                                <SelectItem key={c} value={c}>{c}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div>
                                    <label className="text-sm font-medium mb-1 block">单位</label>
                                    <Select
                                        value={form.unit || ""}
                                        onValueChange={(v) => setForm({ ...form, unit: v })}
                                    >
                                        <SelectTrigger>
                                            <SelectValue placeholder="选择单位" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {UNITS.map(u => (
                                                <SelectItem key={u} value={u}>{u}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium mb-1 block">
                                    SQL 模板 <span className="text-red-500">*</span>
                                </label>
                                <Textarea
                                    value={form.sql_template}
                                    onChange={(e) => setForm({ ...form, sql_template: e.target.value })}
                                    placeholder="SELECT ... FROM ... WHERE data_dt = '${data_dt}' ..."
                                    className="font-mono text-xs min-h-[160px]"
                                />
                            </div>
                        </TabsContent>
                    </Tabs>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialogOpen(false)}>
                            取消
                        </Button>
                        <Button
                            onClick={handleSave}
                            disabled={saving || !form.metric_id || !form.metric_name || !form.sql_template}
                        >
                            {saving ? "保存中..." : dialogMode === "edit" ? "更新" : "创建"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* 删除确认对话框 */}
            <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle>确认删除</DialogTitle>
                    </DialogHeader>
                    <p className="text-sm text-muted-foreground">
                        确定要删除指标 <span className="font-mono font-medium text-foreground">{deleteTarget}</span> 吗？此操作不可恢复。
                    </p>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteTarget(null)}>
                            取消
                        </Button>
                        <Button variant="destructive" onClick={handleDelete}>
                            删除
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
