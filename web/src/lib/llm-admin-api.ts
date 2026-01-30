/**
 * LLM 配置管理 API 客户端（中文注释）
 * 
 * 提供：
 * - 提供商管理
 * - 模型管理
 * - 默认模型设置
 */

import { apiFetch } from '@/lib/backend';

const API_BASE = '/api/v1/llm-admin';

// ==================== 类型定义 ====================

export interface LLMProvider {
  id: number;
  code: string;
  name: string;
  base_url: string | null;
  api_key_masked: string;
  is_active: boolean;
  sort_order: number;
  model_count: number;
}

export interface LLMModel {
  id: number;
  provider_id: number;
  provider_code: string;
  provider_name: string;
  model_code: string;
  model_name: string;
  model_type: string;
  supports_thinking: boolean;
  supports_tool_call: boolean;
  supports_streaming: boolean;
  max_output_tokens: number;
  context_window: number;
  default_temperature: number;
  is_default: boolean;
  is_active: boolean;
  sort_order: number;
  description: string | null;
}

export interface ModelType {
  type: string;
  count: number;
  default_model: string | null;
}

export interface ProviderCreateRequest {
  code: string;
  name: string;
  base_url?: string;
  api_key?: string;
  is_active?: boolean;
  sort_order?: number;
}

export interface ProviderUpdateRequest {
  name?: string;
  base_url?: string;
  api_key?: string;
  is_active?: boolean;
  sort_order?: number;
}

export interface ModelCreateRequest {
  provider_id: number;
  model_code: string;
  model_name: string;
  model_type?: string;
  supports_thinking?: boolean;
  supports_tool_call?: boolean;
  supports_streaming?: boolean;
  max_output_tokens?: number;
  context_window?: number;
  default_temperature?: number;
  thinking_budget?: number;
  is_default?: boolean;
  is_active?: boolean;
  sort_order?: number;
  description?: string;
}

export interface ModelUpdateRequest {
  model_name?: string;
  model_type?: string;
  supports_thinking?: boolean;
  supports_tool_call?: boolean;
  supports_streaming?: boolean;
  max_output_tokens?: number;
  context_window?: number;
  default_temperature?: number;
  thinking_budget?: number;
  is_default?: boolean;
  is_active?: boolean;
  sort_order?: number;
  description?: string;
}

// ==================== 提供商 API ====================

export async function getProviders(): Promise<LLMProvider[]> {
  const response = await apiFetch(`${API_BASE}/providers`);
  if (!response.ok) throw new Error('获取提供商列表失败');
  return response.json();
}

export async function getProvider(providerId: number): Promise<LLMProvider> {
  const response = await apiFetch(`${API_BASE}/providers/${providerId}`);
  if (!response.ok) throw new Error('获取提供商详情失败');
  return response.json();
}

export async function createProvider(data: ProviderCreateRequest): Promise<LLMProvider> {
  const response = await apiFetch(`${API_BASE}/providers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || '创建提供商失败');
  }
  return response.json();
}

export async function updateProvider(providerId: number, data: ProviderUpdateRequest): Promise<LLMProvider> {
  const response = await apiFetch(`${API_BASE}/providers/${providerId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || '更新提供商失败');
  }
  return response.json();
}

export async function deleteProvider(providerId: number): Promise<void> {
  const response = await apiFetch(`${API_BASE}/providers/${providerId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('删除提供商失败');
}

export async function updateProviderApiKey(providerId: number, apiKey: string): Promise<void> {
  const response = await apiFetch(`${API_BASE}/providers/${providerId}/api-key?api_key=${encodeURIComponent(apiKey)}`, {
    method: 'PUT',
  });
  if (!response.ok) throw new Error('更新 API Key 失败');
}

// ==================== 模型 API ====================

export async function getModels(params?: {
  provider_id?: number;
  model_type?: string;
  is_active?: boolean;
}): Promise<LLMModel[]> {
  const searchParams = new URLSearchParams();
  if (params?.provider_id !== undefined) searchParams.set('provider_id', String(params.provider_id));
  if (params?.model_type !== undefined) searchParams.set('model_type', params.model_type);
  if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active));
  
  const url = `${API_BASE}/models${searchParams.toString() ? '?' + searchParams : ''}`;
  const response = await apiFetch(url);
  if (!response.ok) throw new Error('获取模型列表失败');
  return response.json();
}

export async function getModel(modelId: number): Promise<LLMModel> {
  const response = await apiFetch(`${API_BASE}/models/${modelId}`);
  if (!response.ok) throw new Error('获取模型详情失败');
  return response.json();
}

export async function createModel(data: ModelCreateRequest): Promise<LLMModel> {
  const response = await apiFetch(`${API_BASE}/models`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || '创建模型失败');
  }
  return response.json();
}

export async function updateModel(modelId: number, data: ModelUpdateRequest): Promise<LLMModel> {
  const response = await apiFetch(`${API_BASE}/models/${modelId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || '更新模型失败');
  }
  return response.json();
}

export async function deleteModel(modelId: number): Promise<void> {
  const response = await apiFetch(`${API_BASE}/models/${modelId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('删除模型失败');
}

export async function setDefaultModel(modelId: number): Promise<void> {
  const response = await apiFetch(`${API_BASE}/models/${modelId}/set-default`, {
    method: 'PUT',
  });
  if (!response.ok) throw new Error('设置默认模型失败');
}

export async function toggleModelActive(modelId: number): Promise<{ is_active: boolean }> {
  const response = await apiFetch(`${API_BASE}/models/${modelId}/toggle-active`, {
    method: 'PUT',
  });
  if (!response.ok) throw new Error('切换模型状态失败');
  return response.json();
}

// ==================== 模型类型 ====================

export async function getModelTypes(): Promise<ModelType[]> {
  const response = await apiFetch(`${API_BASE}/model-types`);
  if (!response.ok) throw new Error('获取模型类型失败');
  return response.json();
}
