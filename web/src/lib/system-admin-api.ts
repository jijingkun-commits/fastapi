/**
 * 系统配置管理 API 客户端（中文注释）
 * 
 * 提供：
 * - 配置列表查询
 * - 配置更新
 */

import { apiFetch } from '@/lib/backend';

const API_BASE = '/api/v1/system-admin';

// ==================== 类型定义 ====================

export interface SystemConfig {
  id: number;
  config_key: string;
  config_value: string;
  value_type: string;
  category: string | null;
  description: string | null;
  is_secret: boolean;
  is_readonly: boolean;
}

export interface ConfigCategory {
  category: string;
  count: number;
}

export interface ConfigCreateRequest {
  config_key: string;
  config_value: string;
  value_type?: string;
  category?: string;
  description?: string;
  is_secret?: boolean;
  is_readonly?: boolean;
}

// ==================== API ====================

export async function getConfigs(category?: string): Promise<SystemConfig[]> {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  const response = await apiFetch(`${API_BASE}/configs${params}`);
  if (!response.ok) throw new Error('获取配置列表失败');
  return response.json();
}

export async function getConfig(configKey: string): Promise<SystemConfig> {
  const response = await apiFetch(`${API_BASE}/configs/${encodeURIComponent(configKey)}`);
  if (!response.ok) throw new Error('获取配置详情失败');
  return response.json();
}

export async function updateConfig(configKey: string, configValue: string): Promise<{
  message: string;
  key: string;
  old_value: string;
  new_value: string;
}> {
  const response = await apiFetch(`${API_BASE}/configs/${encodeURIComponent(configKey)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config_value: configValue }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || '更新配置失败');
  }
  return response.json();
}

export async function createConfig(data: ConfigCreateRequest): Promise<SystemConfig> {
  const response = await apiFetch(`${API_BASE}/configs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || '创建配置失败');
  }
  return response.json();
}

export async function deleteConfig(configKey: string): Promise<void> {
  const response = await apiFetch(`${API_BASE}/configs/${encodeURIComponent(configKey)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || '删除配置失败');
  }
}

export async function getCategories(): Promise<ConfigCategory[]> {
  const response = await apiFetch(`${API_BASE}/categories`);
  if (!response.ok) throw new Error('获取分类列表失败');
  return response.json();
}

export async function refreshCache(): Promise<{ message: string; count: number }> {
  const response = await apiFetch(`${API_BASE}/refresh-cache`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('刷新缓存失败');
  return response.json();
}
