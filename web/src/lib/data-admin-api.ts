/**
 * 问数管理 API 客户端（中文注释）
 * 
 * 提供 SQL 修正台相关接口：
 * - 查询日志列表与详情
 * - SQL 修正与反馈
 * - 训练数据管理
 */

import { apiFetch } from '@/lib/backend';

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
}): Promise<QueryLog[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params?.is_correct !== undefined) searchParams.set('is_correct', String(params.is_correct));
  if (params?.trained !== undefined) searchParams.set('trained', String(params.trained));

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
