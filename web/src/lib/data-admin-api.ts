/**
 * 问数管理 API 客户端（中文注释）
 * 
 * 提供：
 * - 查询日志列表与详情
 * - SQL 修正与反馈
 * - 训练数据管理
 * - 指标管理（CRUD + AI ETL 转换）
 */

import { apiFetch } from '@/lib/backend';
import type {
  ResultEnrichmentRule,
  ResultEnrichmentRulePayload,
  ResultEnrichmentRuleTestRequest,
  ResultEnrichmentRuleTestResponse,
  ResultEnrichmentRuleRefreshResponse,
} from '@/types/result-enrichment-rule';

const API_BASE = '/api/v1/data-admin';

// ==================== 类型定义 ====================

export interface QueryLog {
  id: number;
  user_id: number | null;
  thread_id: string | null;
  question: string;
  generated_sql: string | null;
  sql_source: string | null;
  is_correct: boolean | null;
  corrected_sql: string | null;
  trained: boolean;
  is_ignored: boolean;
  created_at: string;
}

export interface SQLCorrectionRequest {
  log_id: number;
  corrected_sql: string;
  is_correct?: boolean;
}

// ==================== 查询日志 ====================

/**
 * 获取查询日志列表
 */
export async function getQueryLogs(params?: {
  skip?: number;
  limit?: number;
  is_correct?: boolean;
  trained?: boolean;
  include_ignored?: boolean;
}): Promise<QueryLog[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params?.is_correct !== undefined) searchParams.set('is_correct', String(params.is_correct));
  if (params?.trained !== undefined) searchParams.set('trained', String(params.trained));
  if (params?.include_ignored !== undefined) searchParams.set('include_ignored', String(params.include_ignored));

  const url = `${API_BASE}/query-logs${searchParams.toString() ? '?' + searchParams : ''}`;
  const response = await apiFetch(url);

  if (!response.ok) {
    throw new Error('获取查询日志失败');
  }

  return response.json();
}

/**
 * 获取单条日志详情
 */
export async function getQueryLogDetail(logId: number): Promise<QueryLog> {
  const response = await apiFetch(`${API_BASE}/query-logs/${logId}`);
  if (!response.ok) {
    throw new Error('获取日志详情失败');
  }
  return response.json();
}

// ==================== SQL 修正 ====================

/**
 * 提交 SQL 修正
 */
export async function correctSQL(request: SQLCorrectionRequest): Promise<{ message: string; log_id: number }> {
  const response = await apiFetch(`${API_BASE}/query-logs/correct`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '修正失败' }));
    throw new Error(error.detail || '修正失败');
  }

  return response.json();
}

/**
 * 提交反馈（标记正确/错误）
 */
export async function feedbackSQL(logId: number, isCorrect: boolean): Promise<void> {
  const response = await apiFetch(`${API_BASE}/query-logs/feedback/${logId}?is_correct=${isCorrect}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('反馈提交失败');
  }
}

/**
 * 批量忽略日志（软隐藏）
 */
export async function ignoreQueryLogs(logIds: number[]): Promise<{
  message: string;
  ignored_count: number;
  skipped_count: number;
  errors: string[] | null;
}> {
  const response = await apiFetch(`${API_BASE}/query-logs/ignore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ log_ids: logIds }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '忽略失败' }));
    throw new Error(error.detail || '忽略失败');
  }

  return response.json();
}

// ==================== 训练管理 ====================

/**
 * 训练选中的日志
 */
export async function trainLogs(logIds: number[]): Promise<{
  message: string;
  trained_count: number;
  errors: string[] | null;
}> {
  const response = await apiFetch(`${API_BASE}/train`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ log_ids: logIds }),
  });

  if (!response.ok) {
    throw new Error('训练请求失败');
  }

  return response.json();
}

/**
 * 训练所有待训练日志
 */
export async function trainAllPending(): Promise<{
  message: string;
  trained_count: number;
  total_pending: number;
  errors: string[] | null;
}> {
  const response = await apiFetch(`${API_BASE}/train/all-pending`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('训练请求失败');
  }

  return response.json();
}

// ==================== 指标管理 ====================

export interface MetricDef {
  metric_id: string;
  metric_name: string;
  aliases: string | null;
  description: string | null;
  sql_template: string | null;
  query_template: string | null;
  template_source: string | null;
  category: string | null;
  sub_category: string | null;
  unit: string | null;
  frequency: string | null;
  is_active: boolean | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface MetricStats {
  total: number;
  by_template_type: { type: string; count: number; percent: number }[];
  by_template_source: { source: string; count: number }[];
  by_category: { category: string; count: number }[];
  query_ready: number;
  query_ready_percent: number;
  embedding_ready: number;
  embedding_ready_percent: number;
}

export interface BatchConvertResult {
  message: string;
  processed: number;
  success: number;
  dry_run?: boolean;
  errors?: { metric_id: string; error: string }[] | null;
  preview?: { metric_id: string; metric_name: string; target_type?: string }[];
}

export interface MetricCreateRequest {
  metric_id: string;
  metric_name: string;
  aliases?: string;
  description: string;
  sql_template: string;
  category?: string;
  sub_category?: string;
  unit?: string;
  frequency?: string;
}

export interface ETLConvertResult {
  metric_id: string | null;
  metric_name: string | null;
  aliases: string | null;
  description: string | null;
  sql_template: string | null;
  category: string | null;
  unit: string | null;
}

/**
 * 获取指标列表
 */
export async function getMetrics(params?: {
  skip?: number;
  limit?: number;
  category?: string;
  keyword?: string;
}): Promise<MetricDef[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params?.category) searchParams.set('category', params.category);
  if (params?.keyword) searchParams.set('keyword', params.keyword);

  const qs = searchParams.toString();
  const response = await apiFetch(`${API_BASE}/metrics${qs ? '?' + qs : ''}`);

  if (!response.ok) {
    throw new Error('获取指标列表失败');
  }

  return response.json();
}

/**
 * 创建新指标
 */
export async function createMetric(data: MetricCreateRequest): Promise<MetricDef> {
  const response = await apiFetch(`${API_BASE}/metrics`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '创建失败' }));
    throw new Error(err.detail || '创建失败');
  }

  return response.json();
}

/**
 * 更新指标
 */
export async function updateMetric(metricId: string, data: MetricCreateRequest): Promise<MetricDef> {
  const response = await apiFetch(`${API_BASE}/metrics/${encodeURIComponent(metricId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '更新失败' }));
    throw new Error(err.detail || '更新失败');
  }

  return response.json();
}

/**
 * 删除指标
 */
export async function deleteMetric(metricId: string): Promise<void> {
  const response = await apiFetch(`${API_BASE}/metrics/${encodeURIComponent(metricId)}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('删除失败');
  }
}

/**
 * AI 转换：ETL 脚本 -> SELECT 模板
 */
export async function convertETL(etlScript: string): Promise<ETLConvertResult> {
  const response = await apiFetch(`${API_BASE}/metrics/convert-etl`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ etl_script: etlScript }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '转换失败' }));
    throw new Error(err.detail || '转换失败');
  }

  return response.json();
}

// ==================== 指标统计与批量操作 ====================

/**
 * 获取指标模板统计数据
 */
export async function getMetricStats(): Promise<MetricStats> {
  const response = await apiFetch(`${API_BASE}/metrics/stats`);
  if (!response.ok) {
    throw new Error('获取统计数据失败');
  }
  return response.json();
}

/**
 * 批量转换 ETL 模板
 */
export async function batchConvertTemplates(params: {
  mode: 'result_lookup' | 'ai_extract';
  limit?: number;
  dry_run?: boolean;
}): Promise<BatchConvertResult> {
  const response = await apiFetch(`${API_BASE}/metrics/batch-convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '批量转换失败' }));
    throw new Error(err.detail || '批量转换失败');
  }

  return response.json();
}

// ==================== 结果增强规则管理 ====================

/**
 * 获取结果增强规则列表
 */
export async function getEnrichmentRules(): Promise<ResultEnrichmentRule[]> {
  const response = await apiFetch(`${API_BASE}/enrichment-rules`);
  if (!response.ok) {
    throw new Error('获取结果增强规则失败');
  }
  return response.json();
}

/**
 * 创建结果增强规则
 */
export async function createEnrichmentRule(
  payload: ResultEnrichmentRulePayload,
): Promise<ResultEnrichmentRule> {
  const response = await apiFetch(`${API_BASE}/enrichment-rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '创建规则失败' }));
    throw new Error(err.detail || '创建规则失败');
  }

  return response.json();
}

/**
 * 更新结果增强规则
 */
export async function updateEnrichmentRule(
  ruleId: number,
  payload: ResultEnrichmentRulePayload,
): Promise<ResultEnrichmentRule> {
  const response = await apiFetch(`${API_BASE}/enrichment-rules/${ruleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '更新规则失败' }));
    throw new Error(err.detail || '更新规则失败');
  }

  return response.json();
}

/**
 * 启停结果增强规则
 */
export async function setEnrichmentRuleEnabled(
  ruleId: number,
  enabled: boolean,
): Promise<ResultEnrichmentRule> {
  const response = await apiFetch(`${API_BASE}/enrichment-rules/${ruleId}/enable`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '更新规则状态失败' }));
    throw new Error(err.detail || '更新规则状态失败');
  }

  return response.json();
}

/**
 * 更新结果增强规则优先级
 */
export async function updateEnrichmentRulePriority(
  ruleId: number,
  priority: number,
): Promise<ResultEnrichmentRule> {
  const response = await apiFetch(`${API_BASE}/enrichment-rules/${ruleId}/priority`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ priority }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '更新优先级失败' }));
    throw new Error(err.detail || '更新优先级失败');
  }

  return response.json();
}

/**
 * 测试结果增强规则
 */
export async function testEnrichmentRules(
  payload: ResultEnrichmentRuleTestRequest,
): Promise<ResultEnrichmentRuleTestResponse> {
  const response = await apiFetch(`${API_BASE}/enrichment-rules/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '规则测试失败' }));
    throw new Error(err.detail || '规则测试失败');
  }

  return response.json();
}

/**
 * 刷新结果增强规则缓存
 */
export async function refreshEnrichmentRuleCache(): Promise<ResultEnrichmentRuleRefreshResponse> {
  const response = await apiFetch(`${API_BASE}/enrichment-rules/refresh-cache`, {
    method: 'POST',
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: '刷新缓存失败' }));
    throw new Error(err.detail || '刷新缓存失败');
  }

  return response.json();
}
