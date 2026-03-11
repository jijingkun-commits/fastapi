"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
  createExamJob,
  getExamDownloadUrl,
  getExamJob,
  getExamTemplate,
  listExamJobs,
  type ExamJobSummary,
  type ExamTemplateResponse,
  type PaperTemplate,
} from '@/lib/exam-admin-api';

function formatTime(value?: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN');
}

export function ExamGenerationPanel() {
  const [templatePayload, setTemplatePayload] = useState<ExamTemplateResponse | null>(null);
  const [template, setTemplate] = useState<PaperTemplate | null>(null);
  const [selectedDatasets, setSelectedDatasets] = useState<string[]>([]);
  const [jobs, setJobs] = useState<ExamJobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const lastAutoDownloadedJobId = useRef<number | null>(null);

  const totalQuestionCount = useMemo(() => {
    if (!template) return 0;
    return (
      template.single_choice_count +
      template.multiple_choice_count +
      template.judge_count +
      template.short_answer_count
    );
  }, [template]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [templateData, jobData] = await Promise.all([getExamTemplate(), listExamJobs()]);
      setTemplatePayload(templateData);
      setTemplate(templateData.template);
      setJobs(jobData);
      setSelectedDatasets((prev) => prev.length > 0 ? prev : templateData.available_datasets.map((item) => item.dataset_id).slice(0, 1));
    } catch (error: any) {
      toast.error(error.message || '加载 AI 出题配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!activeJobId) return;
    const timer = window.setInterval(async () => {
      try {
        const detail = await getExamJob(activeJobId);
        if (detail.status === 'succeeded') {
          if (lastAutoDownloadedJobId.current !== detail.id) {
            lastAutoDownloadedJobId.current = detail.id;
            window.location.href = getExamDownloadUrl(detail.id);
            toast.success('试卷已生成，开始下载');
          }
          setActiveJobId(null);
          void loadData();
        }
        if (detail.status === 'failed') {
          toast.error(detail.error_message || '出题任务失败');
          setActiveJobId(null);
          void loadData();
        }
      } catch (error: any) {
        toast.error(error.message || '轮询任务状态失败');
        setActiveJobId(null);
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [activeJobId, loadData]);

  const toggleDataset = (datasetId: string, checked: boolean) => {
    setSelectedDatasets((prev) => {
      if (checked) return [...prev, datasetId];
      return prev.filter((item) => item !== datasetId);
    });
  };

  const updateTemplate = <K extends keyof PaperTemplate>(key: K, value: PaperTemplate[K]) => {
    setTemplate((prev) => prev ? { ...prev, [key]: value } : prev);
  };

  const handleGenerate = async () => {
    if (!template) return;
    if (selectedDatasets.length === 0) {
      toast.error('请至少选择一个知识库');
      return;
    }
    setSubmitting(true);
    try {
      const job = await createExamJob({ dataset_ids: selectedDatasets, template });
      toast.success('出题任务已创建，正在生成 PDF');
      setActiveJobId(job.id);
      await loadData();
    } catch (error: any) {
      toast.error(error.message || '创建出题任务失败');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !template || !templatePayload) {
    return <div className="flex h-96 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-[#A8D4D4] border-t-[#2F6868]" /></div>;
  }

  return (
    <div className="admin-page-content space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="app-page-title">AI 出题</h1>
          <p className="app-page-subtitle">选择知识库、调整模板、生成试卷与答案 PDF</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="outline">题量上限 {templatePayload.limits.max_total_questions}</Badge>
          <Badge variant="outline">并发上限 {templatePayload.limits.max_active_jobs_per_user}</Badge>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>知识库范围</CardTitle>
          <CardDescription>多选数据集按勾选顺序作为优先级；冲突时任务会失败。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {templatePayload.available_datasets.length === 0 ? (
            <p className="text-sm text-muted-foreground">当前未配置可用数据集，请先设置 `RAGFLOW_DATASET_IDS`。</p>
          ) : templatePayload.available_datasets.map((item) => (
            <label key={item.dataset_id} className="flex items-center gap-3 rounded-lg border p-3 text-sm">
              <Checkbox checked={selectedDatasets.includes(item.dataset_id)} onCheckedChange={(checked) => toggleDataset(item.dataset_id, Boolean(checked))} />
              <span>{item.label}</span>
            </label>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>组卷模板</CardTitle>
          <CardDescription>首期固定题型：单选 / 多选 / 判断 / 简答；答案区默认附简短解析。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="paper_title">试卷标题</Label>
            <Input id="paper_title" value={template.paper_title} onChange={(e) => updateTemplate('paper_title', e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>单选题数量</Label>
            <Input type="number" value={template.single_choice_count} onChange={(e) => updateTemplate('single_choice_count', Number(e.target.value) || 0)} />
          </div>
          <div className="space-y-2">
            <Label>多选题数量</Label>
            <Input type="number" value={template.multiple_choice_count} onChange={(e) => updateTemplate('multiple_choice_count', Number(e.target.value) || 0)} />
          </div>
          <div className="space-y-2">
            <Label>判断题数量</Label>
            <Input type="number" value={template.judge_count} onChange={(e) => updateTemplate('judge_count', Number(e.target.value) || 0)} />
          </div>
          <div className="space-y-2">
            <Label>简答题数量</Label>
            <Input type="number" value={template.short_answer_count} onChange={(e) => updateTemplate('short_answer_count', Number(e.target.value) || 0)} />
          </div>
          <div className="space-y-2">
            <Label>总题数</Label>
            <div className="rounded-lg border px-3 py-2 text-sm text-muted-foreground">{totalQuestionCount}</div>
          </div>
          <div className="space-y-2">
            <Label>答案解析模式</Label>
            <div className="rounded-lg border px-3 py-2 text-sm text-muted-foreground">short（固定）</div>
          </div>
          <div className="md:col-span-2 flex justify-end">
            <Button onClick={handleGenerate} disabled={submitting || selectedDatasets.length === 0}>
              {submitting ? '创建中...' : activeJobId ? '生成中...' : '生成并下载'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>历史记录</CardTitle>
          <CardDescription>生成成功的 PDF 会保存到当前 MinIO，并可重复下载。</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>标题</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>知识库</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">暂无生成记录</TableCell>
                </TableRow>
              ) : jobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell>{job.title}</TableCell>
                  <TableCell>
                    <Badge variant={job.status === 'succeeded' ? 'default' : job.status === 'failed' ? 'destructive' : 'secondary'}>{job.status}</Badge>
                  </TableCell>
                  <TableCell>{job.dataset_ids.join(', ')}</TableCell>
                  <TableCell>{formatTime(job.created_at)}</TableCell>
                  <TableCell>
                    {job.status === 'succeeded' ? (
                      <Button variant="outline" size="sm" onClick={() => { window.location.href = getExamDownloadUrl(job.id); }}>下载</Button>
                    ) : job.status === 'failed' ? (
                      <span className="text-xs text-destructive">{job.error_message || '生成失败'}</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">处理中</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
